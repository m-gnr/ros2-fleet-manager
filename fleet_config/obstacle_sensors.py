"""Finite obstacle sensor geometry and one-source SDF/TF/Nav2 contracts."""
from itertools import product
import math
from xml.etree import ElementTree as ET


def rotation(roll, pitch, yaw):
    cr, sr, cp, sp, cy, sy = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    return [[cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
            [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr], [-sp, cp*sr, cp*cr]]


def mv(matrix, vector):
    return [sum(a*b for a,b in zip(row,vector)) for row in matrix]


def compose(a, b):
    ra, rb = rotation(*a[3:]), rotation(*b[3:])
    center = [v+w for v,w in zip(a[:3], mv(ra,b[:3]))]
    matrix = [[sum(ra[i][k]*rb[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return center, matrix


def pose(element):
    value=element.find('pose')
    if value is not None and value.attrib:
        raise ValueError('Unsupported relative/typed SDF pose in envelope proof')
    return list(map(float, element.findtext('pose', '0 0 0 0 0 0').split()))


def shape_bound(geometry, center, matrix):
    """Analytic enclosing sphere about base_link, and a conservative base-frame AABB."""
    if (box := geometry.find('box')) is not None:
        size = list(map(float, box.findtext('size').split()))
        points = [[a+b for a,b in zip(center,mv(matrix,v))] for v in product(*[(-d/2,d/2) for d in size])]
        radius = max(math.sqrt(sum(x*x for x in p)) for p in points)
        half = [sum(abs(matrix[i][j])*size[j]/2 for j in range(3)) for i in range(3)]
    elif (sphere := geometry.find('sphere')) is not None:
        r = float(sphere.findtext('radius')); radius = math.sqrt(sum(v*v for v in center))+r; half = [r]*3
    elif (cylinder := geometry.find('cylinder')) is not None:
        r, h = float(cylinder.findtext('radius')), float(cylinder.findtext('length'))/2
        axis = [row[2] for row in matrix]; along = sum(a*b for a,b in zip(center,axis))
        perpendicular = math.sqrt(max(0.,sum(v*v for v in center)-along*along))
        radius = math.hypot(abs(along)+h,perpendicular+r)
        half = [abs(v)*h+math.sqrt(max(0.,1-v*v))*r for v in axis]
    else:
        raise ValueError('Unproved collision geometry in obstacle sensor envelope')
    return radius, [(v-h,v+h) for v,h in zip(center,half)]


def sensor_contracts(cfg, robot):
    if robot.obstacle_sensor_model is None:
        return []
    model = cfg.fleet.obstacle_sensor_models[robot.obstacle_sensor_model]
    result = []
    for mount in model.mounts:
        beam = mv(rotation(0,0,mount.yaw_rad), model.beam_origin_m)
        result.append(dict(id=mount.id, link='obstacle_'+mount.id, topic=robot.namespace+'/obstacle_'+mount.id,
            frame=robot.id+'/obstacle_'+mount.id+'/lidar',
            base_pose=[a+b for a,b in zip(mount.position_m,beam)]+[0.,0.,mount.yaw_rad]))
    return result


def contact_links(cfg, robot):
    return ['base_link','left_wheel','right_wheel','caster']+[s['link'] for s in sensor_contracts(cfg,robot)]


def install_sensors(tree, cfg, robot, radius):
    model = tree.find(f'.//model[@name="{robot.id}"]')
    if pose(model.find('link[@name="base_link"]')) != [0.]*6:
        raise ValueError('Envelope proof requires the declared base_link origin')
    old = []
    for link in model.findall('link'):
        for collision in link.findall('collision'):
            center, matrix = compose(pose(link),pose(collision))
            bound, aabb = shape_bound(collision.find('geometry'), center,matrix)
            if bound > radius+1e-12:
                raise ValueError(f'{robot.id}: existing {link.get("name")}/{collision.get("name")} exceeds navigation sphere')
            old.append((link.get('name')+'/'+collision.get('name'),aabb,bound))
    if robot.obstacle_sensor_model is None:
        return []
    assembly = cfg.fleet.obstacle_sensor_models[robot.obstacle_sensor_model]
    evidence = [dict(robot=robot.id,existing_collision=name,sphere_radius_m=bound,clearance_m=radius-bound) for name,_,bound in old]
    for mount, contract in zip(assembly.mounts,sensor_contracts(cfg,robot),strict=True):
        link = ET.SubElement(model,'link',name=contract['link'])
        ET.SubElement(link,'pose').text=' '.join(map(str,mount.position_m+[0.,0.,mount.yaw_rad]))
        inertial = ET.SubElement(link,'inertial')
        mass = assembly.case_mass_kg+assembly.head_mass_kg
        com = [assembly.head_mass_kg*v/mass for v in assembly.head_center_m]
        ET.SubElement(inertial,'mass').text=str(mass)
        ET.SubElement(inertial,'pose').text=' '.join(map(str,com+[0.,0.,0.]))
        inertia = ET.SubElement(inertial,'inertia');sx,sy,sz=assembly.case_size_m
        r,h=assembly.head_radius_m,assembly.head_height_m
        case_i=[(sy*sy+sz*sz)/12,(sx*sx+sz*sz)/12,(sx*sx+sy*sy)/12]
        head_i=[(3*r*r+h*h)/12,(3*r*r+h*h)/12,r*r/2]
        tensor=[[0.]*3 for _ in range(3)]
        for m,position,diagonal in [(assembly.case_mass_kg,[0.,0.,0.],case_i),
                                    (assembly.head_mass_kg,assembly.head_center_m,head_i)]:
            d=[v-c for v,c in zip(position,com)]
            for i in range(3):
                for j in range(3):
                    tensor[i][j]+=m*((diagonal[i]+sum(v*v for v in d) if i==j else 0.)-d[i]*d[j])
        for key,i,j in [('ixx',0,0),('iyy',1,1),('izz',2,2),('ixy',0,1),('ixz',0,2),('iyz',1,2)]:
            ET.SubElement(inertia,key).text=str(tensor[i][j])
        pieces = [('case',[0.,0.,0.], 'box'),('head',assembly.head_center_m,'cylinder')]
        for name,offset,kind in pieces:
            collision = None
            for tag in ('collision','visual'):
                element = ET.SubElement(link,tag,name=name)
                ET.SubElement(element,'pose').text=' '.join(map(str,offset+[0.,0.,0.]))
                shape = ET.SubElement(ET.SubElement(element,'geometry'),kind)
                if kind=='box':ET.SubElement(shape,'size').text=' '.join(map(str,assembly.case_size_m))
                else:
                    ET.SubElement(shape,'radius').text=str(assembly.head_radius_m)
                    ET.SubElement(shape,'length').text=str(assembly.head_height_m)
                if tag=='collision':collision=element
            center,matrix=compose(pose(link),pose(collision));bound,aabb=shape_bound(collision.find('geometry'),center,matrix)
            if bound > radius+1e-12:
                raise ValueError(f'{robot.id}/{mount.id}/{name}: finite housing exceeds navigation sphere')
            # Disjoint conservative AABBs prove no positive-volume penetration into old geometry.
            overlaps = [oid for oid,other,_ in old if all(min(a[1],b[1])-max(a[0],b[0])>1e-10 for a,b in zip(aabb,other))]
            if overlaps:raise ValueError(f'{robot.id}/{mount.id}/{name}: housing overlap with {overlaps}')
            evidence.append(dict(robot=robot.id,mount=mount.id,piece=name,sphere_radius_m=bound,clearance_m=radius-bound))
            old.append((contract['link']+'/'+name,aabb,bound))
        sensor=ET.SubElement(link,'sensor',name='lidar',type='gpu_lidar')
        ET.SubElement(sensor,'pose').text=' '.join(map(str,assembly.beam_origin_m+[0.,0.,0.]))
        ET.SubElement(sensor,'topic').text=contract['topic'];ET.SubElement(sensor,'update_rate').text=str(assembly.update_rate_hz)
        ET.SubElement(sensor,'always_on').text='true'
        lidar=ET.SubElement(sensor,'lidar');horizontal=ET.SubElement(ET.SubElement(lidar,'scan'),'horizontal')
        for key,value in [('samples',assembly.samples),('resolution',1),('min_angle',assembly.horizontal_min_rad),('max_angle',assembly.horizontal_max_rad)]:ET.SubElement(horizontal,key).text=str(value)
        ranges=ET.SubElement(lidar,'range')
        for key,value in [('min',assembly.min_range_m),('max',assembly.max_range_m),('resolution',assembly.range_resolution_m)]:ET.SubElement(ranges,key).text=str(value)
        joint=ET.SubElement(model,'joint',name=contract['link']+'_joint',type='fixed')
        ET.SubElement(joint,'parent').text='base_link';ET.SubElement(joint,'child').text=contract['link']
    return evidence


def configure_observations(params,cfg,robot):
    sensors = sensor_contracts(cfg, robot)
    obstacle=params['local_costmap']['local_costmap']['ros__parameters']['obstacle_layer']
    names=obstacle['observation_sources'].split()
    if sensors:
        obstacle['plugin'] = 'fleet_perception::ObservedObstacleLayer'
    for sensor in sensors:
        name='obstacle_'+sensor['id'];names.append(name)
        obstacle[name]=dict(obstacle['scan'],topic=sensor['topic'])
    obstacle['observation_sources']=' '.join(names)


def ray_box(origin, direction, bounds):
    near,far=0.,float('inf')
    for o,d,(lo,hi) in zip(origin,direction,bounds):
        if abs(d)<1e-14:
            if o<lo or o>hi:return False
        else:
            a,b=sorted(((lo-o)/d,(hi-o)/d));near=max(near,a);far=min(far,b)
            if far<near:return False
    return far>=near


def validate_clear_fov(tree,cfg,robot):
    """Reject any continuous horizontal FOV intersecting a conservative own-collision AABB."""
    model=tree.find(f'.//model[@name="{robot.id}"]')
    boxes=[]
    for link in model.findall('link'):
        for collision in link.findall('collision'):
            center,matrix=compose(pose(link),pose(collision))
            _,aabb=shape_bound(collision.find('geometry'),center,matrix)
            boxes.append((link.get('name')+'/'+collision.get('name'),aabb))
    if robot.obstacle_sensor_model is None:return
    assembly=cfg.fleet.obstacle_sensor_models[robot.obstacle_sensor_model]
    for sensor in sensor_contracts(cfg,robot):
        origin=sensor['base_pose'][:3];yaw=sensor['base_pose'][5]
        lo,hi=assembly.horizontal_min_rad,assembly.horizontal_max_rad
        for name,bounds in boxes:
            if not bounds[2][0]<=origin[2]<=bounds[2][1]:continue
            angles=[lo,hi]
            for x,y in product(bounds[0],bounds[1]):
                a=math.atan2(y-origin[1],x-origin[0])-yaw
                a=math.atan2(math.sin(a),math.cos(a))
                if lo<=a<=hi:angles.append(a)
            if any(ray_box(origin,[math.cos(yaw+a),math.sin(yaw+a),0.],bounds) for a in angles):
                raise ValueError(f'{robot.id}/{sensor["id"]}: physical FOV intersects own {name}; range clipping is not a filter')
