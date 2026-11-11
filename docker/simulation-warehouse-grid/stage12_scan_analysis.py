"""Independent ray/box scan alignment with synchronized SE(2) TF and full physical quaternion."""
import json
from math import atan2,cos,sin,isfinite
from pathlib import Path
import sys
from fleet_config import load_config
from stage12_analyze import at,stamp,pose


def rotate(q,v):
    u=[q['x'],q['y'],q['z']];w=q['w']
    cross=lambda a,b:[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    uv=cross(u,v);uuv=cross(u,uv)
    return [v[i]+2*(w*uv[i]+uuv[i]) for i in range(3)]

def raycast(origin,direction,boxes):
    best=float('inf')
    for box in boxes:
        near,far=0.,float('inf')
        for axis,(lo,hi) in enumerate(box):
            if abs(direction[axis])<1e-12:
                if not lo<=origin[axis]<=hi:near,far=1.,0.;break
            else:
                first,last=sorted(((lo-origin[axis])/direction[axis],(hi-origin[axis])/direction[axis]))
                near=max(near,first);far=min(far,last)
        if far>=near and far>=0:best=min(best,near)
    return best

def summary(values):
    values=sorted(values)
    return dict(count=len(values),median_m=values[len(values)//2],p90_m=values[int(.9*(len(values)-1))],
        within_10cm=sum(v<=.1 for v in values)/len(values)) if values else None

def analyze(folder,profile):
    cfg=load_config(profile)
    sensor=json.loads(Path('config/simulation-c3-3-3.json').read_text())['sensor']['pose']
    assert sensor[3:]==[0.,0.,0.], 'Rotated lidar requires a sensor-frame quaternion composition'
    boxes=[[(b.x_min,b.x_max),(b.y_min,b.y_max),(0.,h)] for _,b,h in cfg.warehouse.obstacles()]
    poses=[];physical_full={};odom_tf={};corrections={};scans=[]
    for line in (folder/'localization.jsonl').open():
        r=json.loads(line);m=r.get('message',{})
        if r['kind']=='PHYSICAL' and r['robot']=='robot_beta':
            ns=stamp(m['header']['stamp']);poses.append((ns,pose(m['pose'])));physical_full[ns]=m['pose']
        if r['kind']=='TF':
            for t in m['transforms']:
                ns=stamp(t['header']['stamp']);v=t['transform'];q=v['rotation'];p=v['translation']
                value=[p['x'],p['y'],atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))]
                if t['header']['frame_id']=='map':corrections[ns]=value
                else:odom_tf[ns]=value
        if r['kind']=='SCAN':scans.append(m)
    poses.sort();ot=sorted(odom_tf.items());ct=sorted(corrections.items());rows=[]
    terminal_ns=json.loads((folder/'localization.json').read_text())['stopped']['sim_ns']
    for scan in scans:
        ns=stamp(scan['header']['stamp'])
        if ns>terminal_ns:continue
        p,bracket=at(poses,ns);o,_=at(ot,ns);c,_=at(ct,ns)
        # Map corrections can be sparse during stationary periods. TF interpolation
        # remains valid between bracketing transforms; never extrapolate.
        if c is None:
            from bisect import bisect_left
            i=bisect_left([x[0] for x in ct],ns)
            if 0<i<len(ct):
                a,b=ct[i-1],ct[i];r=(ns-a[0])/(b[0]-a[0]);from stage12_analyze import angle
                c=[a[1][0]+r*(b[1][0]-a[1][0]),a[1][1]+r*(b[1][1]-a[1][1]),a[1][2]+r*angle(b[1][2]-a[1][2])]
        if p is None or o is None or c is None:continue
        estimate=[c[0]+cos(c[2])*o[0]-sin(c[2])*o[1],c[1]+sin(c[2])*o[0]+cos(c[2])*o[1],c[2]+o[2]]
        # Quaternion observations are used only at exact physical timestamps; missing
        # matches are excluded rather than borrowing another orientation in motion.
        full=physical_full.get(ns)
        if full is None:continue
        delta=rotate(full['orientation'],sensor[:3]);xyz=full['position'];origin=[xyz[k]+delta[i] for i,k in enumerate(('x','y','z'))]
        truth_errors=[];map_errors=[];missing=0
        for i,value in enumerate(scan['ranges']):
            if value is None or not scan['range_min']<=value<=scan['range_max']:continue
            a=scan['angle_min']+i*scan['angle_increment']
            actual=raycast(origin,rotate(full['orientation'],[cos(a),sin(a),0.]),boxes)
            predicted=raycast([estimate[0]+cos(estimate[2])*sensor[0]-sin(estimate[2])*sensor[1],
                estimate[1]+sin(estimate[2])*sensor[0]+cos(estimate[2])*sensor[1],sensor[2]],[cos(a+estimate[2]),sin(a+estimate[2]),0.],boxes)
            if isfinite(actual) and isfinite(predicted):truth_errors.append(abs(actual-value));map_errors.append(abs(predicted-value))
            else:missing+=1
        rows.append(dict(stamp_ns=ns,physical_bracket_ns=bracket,physical=summary(truth_errors),map=summary(map_errors),unmatched_rays=missing))
    (folder/'raycast-alignment.json').write_text(json.dumps(rows,indent=2))
    return rows

if __name__=='__main__':
    root=Path(sys.argv[1]);profile=sys.argv[2]
    for folder in sorted(root.glob('pickup-*')):
        if (folder/'localization.json').exists():
            rows=analyze(folder,profile);print(folder.name,'samples',len(rows),'last',rows[-1] if rows else None)
