"""Sequential fresh-world experiments; generated variants never alter product configuration."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import yaml
from fleet_config import load_config


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('profile',type=Path);cli.add_argument('output',type=Path)
    cli.add_argument('--motions',action='store_true');cli.add_argument('--trials',type=int,default=0)
    cli.add_argument('--only',nargs='+');cli.add_argument('--variant',default='baseline')
    cli.add_argument('--access',action='store_true');cli.add_argument('--routes',action='store_true');cli.add_argument('--lifecycle',type=int,default=0)
    args=cli.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    runs=list(('forward','reverse','turn90','turn180','turn_forward','corridor')) if args.motions else []
    runs += [f'pickup-{i}' for i in range(1,args.trials+1)]
    if args.only:runs=args.only
    for name in runs:
        out=args.output/name;out.mkdir(exist_ok=False)
        profile=args.profile.resolve()
        if name in ('forward','reverse','turn90','turn180','turn_forward','corridor'):
            data=load_config(profile).model_dump(mode='json')
            for robot in data['robots']:
                robot['nav2_params_path']=str((profile.parent/robot['nav2_params_path']).resolve())
                if robot['id']=='robot_beta':
                    robot['initial_pose']=dict(x=-7. if name=='corridor' else 12.,y=5.25 if name=='corridor' else 0.,yaw=0.)
            profile=out/'experiment-profile.yaml'
            profile.write_text(yaml.safe_dump(data,sort_keys=False))
            load_config(profile)
        with (out/'simulation.log').open('w') as log:
            server=subprocess.Popen([sys.executable,'docker/simulation-warehouse-grid/stage12_variant_server.py',str(profile),
                str(out/'generated'),'routes'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'STAGE12_VARIANT':args.variant})
        started=time.monotonic()
        try:
            command=[sys.executable,'docker/simulation-warehouse-grid/stage12_probe.py',str(profile),str(out)]
            if name.startswith('target-'):command+=['--target',name.removeprefix('target-')]
            elif not name.startswith('pickup'):command+=['--motion',name]
            if name==runs[-1] and args.access:command+=['--access']
            with (out/'probe.log').open('w') as log:
                result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=1000 if args.access else 330)
            if result.returncode:raise RuntimeError(f'{name} probe exited {result.returncode}')
            if name==runs[-1] and args.routes:
                subprocess.run([sys.executable,'docker/simulation-warehouse-grid/stage12_routes.py',str(profile),str(out/'routes.json')],check=True,timeout=180)
            if name==runs[-1] and args.lifecycle:
                subprocess.run([sys.executable,'docker/simulation-warehouse-grid/stage12_lifecycle.py',str(profile),str(out/'lifecycle'),'--count',str(args.lifecycle)],check=True,timeout=400)
        finally:
            server.send_signal(signal.SIGTERM)
            server.wait(timeout=40)
            (out/'shutdown.json').write_text(json.dumps(dict(simulation_exit=server.returncode,
                wall_duration_s=time.monotonic()-started)))
        print(json.dumps(dict(run=name,exit=result.returncode)),flush=True)

if __name__=='__main__':main()
