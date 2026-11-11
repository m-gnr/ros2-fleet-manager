"""Derive YAML measurements from the retained SDF; evaluate clearance without changing fleet parameters."""
import argparse
import hashlib
import json
from math import hypot
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

from fleet_config import load_config


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path)
    parser.add_argument('generated',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    cfg=load_config(args.profile)
    world=args.generated/'warehouse.sdf'
    tree=ET.parse(world)
    measurements={}
    for robot in cfg.robots:
        model=tree.getroot().find(f".//model[@name='{robot.id}']")
        body=[float(v) for v in model.find("link[@name='base_link']/collision/geometry/box/size").text.split()]
        wheels=[]
        for linkname in ('left_wheel','right_wheel'):
            link=model.find(f"link[@name='{linkname}']")
            pose=[float(v) for v in link.find('pose').text.split()]
            # This audit supports the retained validation model's horizontal axle only.
            assert abs(pose[3]-1.57079632679)<1e-9 and pose[4:]==[0.,0.]
            cylinder=link.find('collision/geometry/cylinder')
            wheels.append(dict(center_y_m=pose[1],radius_m=float(cylinder.find('radius').text),
                               width_m=float(cylinder.find('length').text)))
        caster=model.find("link[@name='caster']")
        supports=[]
        for collision in caster.findall('collision'):
            supports.append(dict(name=collision.get('name'),radius_m=float(collision.find('geometry/sphere/radius').text),
                link_pose=[float(v) for v in caster.find('pose').text.split()],
                collision_pose=[float(v) for v in collision.findtext('pose','0 0 0 0 0 0').split()]))
        params=yaml.safe_load((args.generated/f'nav2-{robot.id}.yaml').read_text())
        measurements[robot.id]=dict(body_length_m=body[0],body_width_m=body[1],wheels=wheels,supports=supports,
            nav2={name:{k:params[name][name]['ros__parameters'][k] for k in ('robot_radius','inflation_layer')}
                  for name in ('local_costmap','global_costmap')})
    artifact=dict(status='DERIVED_EVIDENCE_ONLY',world_sha256=hashlib.sha256(world.read_bytes()).hexdigest(),robots=measurements)
    args.output.mkdir(parents=True,exist_ok=True)
    measurement_path=args.output/'physical-measurements.yaml'
    measurement_path.write_text(yaml.safe_dump(artifact,sort_keys=False))
    # Calculations consume the generated YAML measurements. It is evidence, not another fleet configuration.
    loaded=yaml.safe_load(measurement_path.read_text())
    aisle=next(a for a in cfg.warehouse.aisles if a.id=='aisle_a').bounds
    point=next(p for p in cfg.warehouse.transfer_points if p.id=='pick_A1')
    corridor_width=aisle.y_max-aisle.y_min
    rack_distance=aisle.y_max-point.pose.y
    clearance=corridor_width-rack_distance-cfg.warehouse.approach_clearance_m
    results={}
    for rid,m in loaded['robots'].items():
        width=max(m['body_width_m'],max(w['center_y_m']+w['width_m']/2 for w in m['wheels'])-
                  min(w['center_y_m']-w['width_m']/2 for w in m['wheels']))
        length=m['body_length_m']
        for s in m['supports']:
            assert s['link_pose'][3:]==[0.,0.,0.] and s['collision_pose'][3:]==[0.,0.,0.]
            x=s['link_pose'][0]+s['collision_pose'][0]
            y=s['link_pose'][1]+s['collision_pose'][1]
            assert abs(x)+s['radius_m']<=length/2+1e-12
            assert abs(y)+s['radius_m']<=width/2+1e-12
        radial_lower_bound=hypot(length/2,m['body_width_m']/2)
        results[rid]=dict(physical_width_m=width,physical_length_m=length,
            conservative_aabb_rotation_diameter_m=hypot(length,width),
            body_corner_radius_m=radial_lower_bound,
            configured_approach_envelope_diameter_m=2*cfg.warehouse.approach_clearance_m,
            remaining_straight_tolerance_m=clearance-width,
            remaining_configured_envelope_tolerance_m=clearance-2*cfg.warehouse.approach_clearance_m,
            nav2_circle_covers_body_corners=m['nav2']['local_costmap']['robot_radius']>=radial_lower_bound,
            center_band_outside_inflation_m=clearance-2*m['nav2']['global_costmap']['inflation_layer']['inflation_radius'])
    inventory=([dict(id=p.id,type='TRANSFER',pose=p.pose.model_dump()) for p in cfg.warehouse.transfer_points]+
               [dict(id=p.id,type=kind,pose=p.pose.model_dump()) for kind,items in
                [('DOCK',cfg.stations.charging_stations),('PARK',cfg.stations.parking_stations)] for p in items])
    result=dict(status='STATIC_PRECHECK_NOT_TRAFFIC_ACCEPTANCE',corridor_width_m=corridor_width,
        rack_approach_distance_m=rack_distance,remaining_pickup_lane_m=clearance,robots=results,
        station_count=len(inventory),inventory=inventory,
        nominal_burger_source='https://emanual.robotis.com/docs/en/platform/turtlebot3/features/',
        nominal_burger_width_m=.178,
        formulas=['C = aisle_width - rack_approach_distance - configured_approach_radius',
                  'W = max(body_width, outer_wheel_extent)',
                  'D_rotation_bound = sqrt(body_length**2 + W**2)',
                  'T = C - E; E is the selected documented envelope diameter'])
    (args.output/'clearance-precheck.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='inventory'},indent=2))


if __name__=='__main__':
    main()
