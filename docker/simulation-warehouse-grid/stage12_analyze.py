"""Recompute synchronized odometry error from immutable timestamped experiment data."""
from bisect import bisect_left
import json
from math import atan2,cos,hypot,sin
from pathlib import Path
import sys


def angle(a):return atan2(sin(a),cos(a))
def stamp(s):return s['sec']*10**9+s['nanosec']
def pose(p):
    q=p['orientation'];v=p['position']
    return [v['x'],v['y'],atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))]
def at(rows,t):
    times=[x[0] for x in rows];i=bisect_left(times,t)
    if i<len(rows) and times[i]==t:return rows[i][1],0
    if 0<i<len(rows) and times[i]-times[i-1]<=100_000_000:
        a,b=rows[i-1],rows[i];r=(t-a[0])/(b[0]-a[0])
        return [a[1][0]+r*(b[1][0]-a[1][0]),a[1][1]+r*(b[1][1]-a[1][1]),a[1][2]+r*angle(b[1][2]-a[1][2])],b[0]-a[0]
    return None,None

def analyze(folder):
    report=json.loads((folder/'localization.json').read_text())
    if not report.get('stopped') or not report.get('terminal'):return {'name':folder.name,'error':report.get('error'),'result':'doğrulanamadı'}
    truth=[];odoms=[];particles=[];corrections=[];first=None;last=None
    for line in (folder/'localization.jsonl').open():
        row=json.loads(line);m=row.get('message',{})
        if first is None:first=row
        last=row
        if row['kind']=='PHYSICAL' and row['robot']=='robot_beta':truth.append((stamp(m['header']['stamp']),pose(m['pose'])))
        if row['kind']=='ODOMETRY':odoms.append(m)
        if row['kind']=='TF':
            for transform in m['transforms']:
                if transform['header']['frame_id']=='map':
                    t=transform['transform'];q=t['rotation']
                    corrections.append(dict(stamp_ns=stamp(transform['header']['stamp']),
                        x=t['translation']['x'],y=t['translation']['y'],yaw=atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))))
        if row['kind']=='PARTICLES':
            ps=m['particles'];xs=[p['pose']['position']['x'] for p in ps];ys=[p['pose']['position']['y'] for p in ps]
            particles.append(dict(stamp_ns=stamp(m['header']['stamp']),count=len(ps),x_range=[min(xs),max(xs)],y_range=[min(ys),max(ys)]))
    truth.sort();aligned=[]
    for o in odoms:
        ns=stamp(o['header']['stamp']);p,bracket=at(truth,ns)
        if p is not None:aligned.append((ns,p,pose(o['pose']['pose']),bracket,o['twist']['twist']))
    if len(aligned)<2:raise ValueError('Not enough synchronized samples')
    initial=report['initial'];yaw=initial['physical'][2]-initial['odom_pose'][2]
    start=next(r for r in aligned if r[0]>=initial['sim_ns']);end=min(aligned,key=lambda row:abs(row[0]-report['stopped']['sim_ns']))
    relevant=[r for r in aligned if start[0]<=r[0]<=end[0]]
    def distance(index):return sum(hypot(b[index][0]-a[index][0],b[index][1]-a[index][1]) for a,b in zip(relevant,relevant[1:]))
    def rotation(index):return sum(angle(b[index][2]-a[index][2]) for a,b in zip(relevant,relevant[1:]))
    dx=end[2][0]-start[2][0];dy=end[2][1]-start[2][1]
    metrics=dict(name=folder.name,motion=report.get('motion'),nav2_terminal=report.get('nav2_terminal'),result=report['result'],
        initial=initial,terminal=report['terminal'],stopped=report['stopped'],
        synchronized_samples=len(relevant),max_interpolation_bracket_ns=max(r[3] for r in relevant),
        simulation_duration_s=(end[0]-start[0])/1e9,
        wall_duration_s=last['monotonic']-first['monotonic'],
        physical_distance_m=distance(1),odometry_distance_m=distance(2),
        physical_rotation_rad=rotation(1),odometry_rotation_rad=rotation(2),
        endpoint_error_m=hypot(dx*cos(yaw)-dy*sin(yaw)-(end[1][0]-start[1][0]),dx*sin(yaw)+dy*cos(yaw)-(end[1][1]-start[1][1])),
        yaw_drift_rad=angle(rotation(2)-rotation(1)),
        odom_max_linear_m_s=max(hypot(r[4]['linear']['x'],r[4]['linear']['y']) for r in relevant),
        odom_max_angular_rad_s=max(abs(r[4]['angular']['z']) for r in relevant),
        physical_max_linear_m_s=max(hypot(b[1][0]-a[1][0],b[1][1]-a[1][1])/((b[0]-a[0])/1e9) for a,b in zip(relevant,relevant[1:]) if b[0]>a[0]),
        physical_max_angular_rad_s=max(abs(angle(b[1][2]-a[1][2]))/((b[0]-a[0])/1e9) for a,b in zip(relevant,relevant[1:]) if b[0]>a[0]),
        map_odom_corrections=corrections,particle_samples=particles,scan_last=report['scan_map_samples'][-1] if report['scan_map_samples'] else None,
        unsafe_contacts=report['contacts'])
    (folder/'metrics.json').write_text(json.dumps(metrics,indent=2))
    return metrics

if __name__=='__main__':
    root=Path(sys.argv[1]);rows=[analyze(p.parent) for p in sorted(root.glob('*/localization.json'))]
    (root/'summary.json').write_text(json.dumps(rows,indent=2))
    for r in rows:
        if 'error' in r:print(r);continue
        print(r['name'],*[f'{r[k]:.6f}' for k in ('physical_distance_m','odometry_distance_m','physical_rotation_rad','odometry_rotation_rad','endpoint_error_m','yaw_drift_rad')])
