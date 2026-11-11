"""Run isolated variants sequentially; never overwrite evidence or product profiles."""
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
    cli.add_argument('--trials',type=int,default=3)
    cli.add_argument('--amcl',help='Single key=value override')
    cli.add_argument('--heading',type=float)
    cli.add_argument('--landmark',action='store_true')
    cli.add_argument('--target',default='pick_A2')
    cli.add_argument('--collect-after-shutdown-failure',action='store_true',help='Collect remaining independent worlds but return nonzero if any shutdown failed')
    args=cli.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    override={}
    if args.amcl:
        key,value=args.amcl.split('=',1);override['amcl']={key:yaml.safe_load(value)}
    if args.landmark:override['landmark']=True
    original=load_config(args.profile.resolve())
    unclean=[]
    for i in range(1,args.trials+1):
        out=args.output/f'pickup-{i}';out.mkdir()
        data=original.model_dump(mode='json')
        for robot in data['robots']:
            robot['nav2_params_path']=str((args.profile.resolve().parent/robot['nav2_params_path']).resolve())
            if args.heading is not None and robot['id']=='robot_beta':robot['initial_pose']['yaw']=args.heading
        profile=out/'experiment-profile.yaml';profile.write_text(yaml.safe_dump(data,sort_keys=False))
        load_config(profile)
        env={**os.environ,'STAGE13_OVERRIDE':json.dumps(override)}
        with (out/'simulation.log').open('w') as log:
            server=subprocess.Popen([sys.executable,'docker/simulation-warehouse-grid/stage13_server.py',str(profile),str(out/'generated'),'routes'],
                stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env)
        perf=subprocess.Popen([sys.executable,'docker/simulation-warehouse-grid/stage12_performance.py',str(out/'performance.jsonl')])
        started=time.monotonic();code=None
        try:
            with (out/'probe.log').open('w') as log:
                run=subprocess.run([sys.executable,'docker/simulation-warehouse-grid/stage13_probe.py',str(profile),str(out),'--target',args.target],
                    stdout=log,stderr=subprocess.STDOUT,timeout=330)
                code=run.returncode
            if code:raise RuntimeError(f'Probe failed: {code}; evidence preserved')
            if i==args.trials:
                with (out/'routes.log').open('w') as log:
                    subprocess.run([sys.executable,'docker/simulation-warehouse-grid/stage12_routes.py',str(profile),str(out/'routes.json')],
                        stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True)
        finally:
            perf.send_signal(signal.SIGTERM);perf.wait(timeout=5)
            server.send_signal(signal.SIGTERM);server.wait(timeout=45)
            (out/'shutdown.json').write_text(json.dumps(dict(simulation_exit=server.returncode,probe_exit=code,wall_duration_s=time.monotonic()-started),indent=2))
        print(json.dumps(dict(run=str(out),probe_exit=code,simulation_exit=server.returncode)),flush=True)
        if server.returncode:
            unclean.append(str(out))
            if not args.collect_after_shutdown_failure:raise RuntimeError('Unclean simulation shutdown')
    (args.output/'collection.json').write_text(json.dumps(dict(unclean_worlds=unclean,all_clean=not unclean),indent=2))
    if unclean:raise SystemExit(1)

if __name__=='__main__':main()
