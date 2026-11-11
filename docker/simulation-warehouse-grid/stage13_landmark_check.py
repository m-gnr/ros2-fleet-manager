"""Verify the experimental notch was actually visible in recorded lidar returns."""
import json
from math import cos,sin,isfinite
from pathlib import Path
import sys
from fleet_config import load_config
from stage12_scan_analysis import raycast,rotate,summary
from stage12_analyze import stamp
from stage13_server import original_obstacles,landmark_obstacles


def main():
    root=Path(sys.argv[1]);cfg=load_config('config/fleet.warehouse-30x18.yaml')
    boxes=lambda source:[[(b.x_min,b.x_max),(b.y_min,b.y_max),(0,h)] for _,b,h in source(cfg.warehouse)]
    before,after=boxes(original_obstacles),boxes(landmark_obstacles)
    offset=json.loads(Path('config/simulation-c3-3-3.json').read_text())['sensor']['pose'][:3]
    results=[]
    for folder in sorted((root/'b-landmark').glob('pickup-*')):
        if not (folder/'shutdown.json').exists():continue
        initial=json.loads((folder/'localization.json').read_text())['initial']['sim_ns']
        full={};scans=[]
        for line in (folder/'localization.jsonl').open():
            row=json.loads(line);m=row.get('message',{})
            if row['kind']=='PHYSICAL' and row['robot']=='robot_beta':full[stamp(m['header']['stamp'])]=m['pose']
            elif row['kind']=='SCAN' and stamp(m['header']['stamp'])<=initial:scans.append(m)
        matched=[]
        for scan in scans:
            ns=stamp(scan['header']['stamp']);p=full.get(ns)
            if p is None:continue
            delta=rotate(p['orientation'],offset);origin=[p['position'][k]+delta[i] for i,k in enumerate(('x','y','z'))]
            for index,reading in enumerate(scan['ranges']):
                if reading is None:continue
                a=scan['angle_min']+index*scan['angle_increment'];direction=rotate(p['orientation'],[cos(a),sin(a),0])
                b,c=raycast(origin,direction,before),raycast(origin,direction,after)
                if isfinite(b) and isfinite(c) and abs(b-c)>.1:
                    matched.append(dict(stamp_ns=ns,beam=index,observed_m=reading,original_prediction_m=b,notch_prediction_m=c,
                        original_residual_m=abs(reading-b),notch_residual_m=abs(reading-c)))
        result=dict(run=folder.name,changed_beam_observations=len(matched),original_residual=summary([m['original_residual_m'] for m in matched]),
            notch_residual=summary([m['notch_residual_m'] for m in matched]),observations=matched)
        results.append(result)
    (root/'landmark-lidar-visibility.json').write_text(json.dumps(results,indent=2))
    for r in results:print(r['run'],r['changed_beam_observations'],r['original_residual'],r['notch_residual'])

if __name__=='__main__':main()
