"""Continuous-box surrogate of endpoint likelihood; not the binary AMCL scorer."""
import json
from math import cos,sin,hypot,exp
from pathlib import Path
import sys
from fleet_config import load_config
from stage12_analyze import stamp,pose
from stage13_analyze import interpolate,compose


def main():
    root=Path(sys.argv[1]);cfg=load_config('config/fleet.warehouse-30x18.yaml')
    boxes=[b for _,b,_ in cfg.warehouse.obstacles()];results=[]
    def score(scan,p):
        ds=[];score=1.;step=max(1,(len(scan['ranges'])-1)//59)
        for i in range(0,len(scan['ranges']),step):
            r=scan['ranges'][i]
            if r is None or r>=scan['range_max'] or r<scan['range_min']:continue
            a=p[2]+scan['angle_min']+i*scan['angle_increment'];x=p[0]+r*cos(a);y=p[1]+r*sin(a)
            d=min(hypot(max(b.x_min-x,0,x-b.x_max),max(b.y_min-y,0,y-b.y_max)) for b in boxes)
            ds.append(d);score+=(.5*exp(-min(d,2.)**2/(2*.2**2))+.5/scan['range_max'])**3
        return dict(score=score,rays=len(ds),inside_fraction=sum(d==0 for d in ds)/len(ds) if ds else None)
    for folder in sorted((root/'a-baseline').glob('pickup-*')):
        truth={};scans=[]
        sync=json.loads((folder/'synchronized.json').read_text());maps=[(r['stamp_ns'],r['map_pose']) for r in sync]
        for line in (folder/'localization.jsonl').open():
            row=json.loads(line);m=row.get('message',{})
            if row['kind']=='PHYSICAL' and row['robot']=='robot_beta':truth[stamp(m['header']['stamp'])]=pose(m['pose'])
            elif row['kind']=='SCAN':scans.append(m)
        rows=[]
        for scan in scans:
            t=stamp(scan['header']['stamp']);p=truth.get(t);m=interpolate(maps,t)
            if p is None or m is None:continue
            actual=score(scan,p);estimate=score(scan,m)
            rows.append(dict(stamp_ns=t,physical=actual,map_estimate=estimate,map_to_true_score_ratio=estimate['score']/actual['score']))
        results.append(dict(run=folder.name,method='Continuous occupied-box endpoint surrogate; raster quantization and exact AMCL particle updates are not reproduced.',samples=rows))
    (root/'endpoint-likelihood-surrogate.json').write_text(json.dumps(results,indent=2))
    for r in results:
        print(r['run'],'last',r['samples'][-1] if r['samples'] else None)

if __name__=='__main__':main()
