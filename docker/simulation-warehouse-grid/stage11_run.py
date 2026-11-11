"""Fresh isolated stage-1.1 world; no task injection, parameter overrides, or policy changes."""
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time

from fleet_config import load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--api-port', required=True)
    parser.add_argument('--scene-port', required=True)
    parser.add_argument('--origin', required=True)
    args = parser.parse_args()
    cfg = load_config(args.profile)
    args.output.mkdir(parents=True,exist_ok=True)
    database=Path('/var/lib/fleet')/(args.output.name+'.sqlite3')
    database.parent.mkdir(parents=True,exist_ok=True)
    if database.exists():
        raise FileExistsError('A fresh database is required')
    children = []
    stop = False
    def stopping(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGINT, stopping)
    def launch(name, cmd):
        log = (args.output/(name+'.log')).open('w')
        child = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        log.close()
        children.append((name,child))
    try:
        launch('simulation',[sys.executable,'docker/simulation-warehouse-grid/serve.py',str(args.profile),
                             str(args.output/'generated'),'routes'])
        launch('observer',[sys.executable,'docker/simulation-warehouse-grid/stage11_observer.py',str(args.profile),str(args.output),
                           '--database',str(database)])
        deadline = time.monotonic()+160
        while not (args.output/'reset-verified.json').exists():
            if stop or time.monotonic()>deadline or any(p.poll() is not None for _,p in children):
                raise RuntimeError('Reset gate unavailable')
            time.sleep(.1)
        # Existing test-only reset seam is opened only after the separate physical gate.
        # No session/epoch, dock, battery, cancellation, or runtime safety gate is modified.
        settings=json.loads(Path('config/simulation-c3-3-3.json').read_text())
        for robot in cfg.robots:
            launch('battery_'+robot.id,[sys.executable,'-c','from fleet_battery_simulator.node import main; main()',
                   '--fleet-config',str(args.profile),'--robot-id',robot.id])
            launch('executor_'+robot.id,[sys.executable,'docker/simulation-c4-2/executor_test_entry.py',
                   '--ros-args','-r','__node:=executor_'+robot.id,'-r','__ns:='+robot.namespace,
                   '-p','fleet_config_path:='+str(args.profile),'-p','robot_id:='+robot.id,
                   '-p','use_sim_time:=true','-p','duplicate_record_capacity:='+str(settings['executor_duplicate_record_capacity'])])
        launch('scene',[sys.executable,'fleet-visualizer/bridge/run.py','--fleet',str(args.profile),
                        '--bind','127.0.0.1','--port',args.scene_port,'--origin','http://scene','--observed-nav2-plans'])
        launch('manager',[sys.executable,'docker/simulation-warehouse-grid/stage11_runtime.py','--fleet',str(args.profile),
                          '--database',str(database),'--snapshot','/tmp/stage1/latest.json'])
        launch('api',[sys.executable,'-m','backend.dashboard.api','--fleet',str(args.profile),
                      '--snapshot','/tmp/stage1/latest.json','--task-socket','/tmp/stage1/latest.tasks.sock',
                      '--container-bind','--port',args.api_port,'--origin',args.origin,'--scene-port',args.scene_port])
        while not stop:
            for name, child in children:
                if child.poll() is not None:
                    raise RuntimeError(f'{name} exited {child.returncode}')
            if (args.output/'unsafe-contact').exists():
                raise RuntimeError('Contact safety stop')
            time.sleep(.1)
    finally:
        exits={}
        # Finish the manager/API before the robots; the world supervisor owns Nav2 shutdown.
        order=['api','manager','scene']+[n for n,_ in children if n.startswith(('executor_','battery_'))]+['observer','simulation']
        for name in order:
            for current, child in children:
                if name != current:
                    continue
                child.send_signal(signal.SIGINT if name!='simulation' else signal.SIGTERM)
                try:
                    child.wait(timeout=35 if name=='simulation' else 10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL)
                    child.wait()
                exits[name]=child.returncode
        (args.output/'shutdown.json').write_text(json.dumps(exits,indent=2))
        if database.exists():
            with sqlite3.connect(database) as source, sqlite3.connect(args.output/'fleet.sqlite3') as target:
                source.backup(target)


if __name__ == '__main__':
    main()
