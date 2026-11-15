"""Fresh isolated stage-1 world; no task injection, parameter overrides, or policy changes."""
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
from stage1_preflight import preflight


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--api-port', required=True)
    parser.add_argument('--scene-port', required=True)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--ros-overlay', type=Path,
                        help='Isolated colcon install prefix containing fleet_perception and fleet_interfaces')
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    args.profile = args.profile.resolve()
    args.output = args.output.resolve()
    if args.ros_overlay is not None:
        setup = args.ros_overlay.resolve() / 'local_setup.bash'
        if not setup.is_file():
            raise FileNotFoundError(f'ROS overlay setup unavailable: {setup}')
        # Source the Humble underlay first; all children inherit the plugin index,
        # shared-library paths and generated message bindings from this overlay.
        environment = subprocess.check_output([
            'bash', '-ec',
            'source /opt/ros/humble/setup.bash; source "$1"; env -0',
            'stage1-overlay', str(setup)])
        os.environ.update(os.fsdecode(entry).split('=', 1)
                          for entry in environment.split(b'\0') if entry)
        subprocess.run(['ros2', 'pkg', 'prefix', 'fleet_perception'], check=True)
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
    commands = []
    def plan(name, cmd):
        commands.append((name, cmd))
    plan('simulation',[sys.executable,'docker/simulation-warehouse-grid/serve.py',str(args.profile),
                             str(args.output/'generated'),'routes'])
    plan('observer',[sys.executable,'docker/simulation-warehouse-grid/stage1_observer.py',str(args.profile),str(args.output),
                           '--database',str(database)])
    settings=json.loads(Path('config/simulation-c3-3-3.json').read_text())
    for robot in cfg.robots:
        plan('battery_'+robot.id,[sys.executable,'-c','from fleet_battery_simulator.node import main; main()',
                   '--fleet-config',str(args.profile),'--robot-id',robot.id])
        plan('executor_'+robot.id,[sys.executable,'docker/simulation-c4-2/executor_test_entry.py',
                   '--ros-args','-r','__node:=executor_'+robot.id,'-r','__ns:='+robot.namespace,
                   '-p','fleet_config_path:='+str(args.profile),'-p','robot_id:='+robot.id,
                   '-p','use_sim_time:=true','-p','duplicate_record_capacity:='+str(settings['executor_duplicate_record_capacity'])])
    plan('scene',[sys.executable,'fleet-visualizer/bridge/run.py','--fleet',str(args.profile),
                        '--schema',str(Path('config/fleet.schema.json').resolve()),
                        '--bind','127.0.0.1','--port',args.scene_port,'--origin','http://scene','--observed-nav2-plans'])
    plan('manager',[sys.executable,'-m','backend.dashboard.runtime','--fleet',str(args.profile),
                          '--database',str(database),'--snapshot','/tmp/stage1/latest.json'])
    plan('api',[sys.executable,'-m','backend.dashboard.api','--fleet',str(args.profile),
                      '--schema',str(Path('config/fleet.schema.json').resolve()),
                      '--snapshot','/tmp/stage1/latest.json','--task-socket','/tmp/stage1/latest.tasks.sock',
                      '--container-bind','--port',args.api_port,'--origin',args.origin,'--scene-port',args.scene_port])
    preflight(args, commands)
    if args.preflight_only:
        return
    try:
        for name, cmd in commands[:2]:
            launch(name, cmd)
        deadline = time.monotonic()+160
        while not (args.output/'reset-verified.json').exists():
            if stop or time.monotonic()>deadline or any(p.poll() is not None for _,p in children):
                raise RuntimeError('Reset gate unavailable')
            time.sleep(.1)
        # Existing physical reset gate remains mandatory for Executor startup.
        for name, cmd in commands[2:]:
            launch(name, cmd)
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
