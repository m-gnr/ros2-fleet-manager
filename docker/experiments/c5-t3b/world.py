"""Reuse T3A zero-only world; split only the odometry transport fault boundary."""
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('t3a_world',ROOT/'docker/experiments/c5-t3a/world.py')
t3a = importlib.util.module_from_spec(spec);spec.loader.exec_module(t3a)
original_run = t3a.t2.native.server.run_simulation
original_generate = t3a.t2.native.server.generate


def generate(*args,**kwargs):
    cfg=original_generate(*args,**kwargs)
    public={}
    for robot in cfg.robots:
        path=Path('/run/c5-b6b7')/(robot.id+'.json')
        provision=json.loads(path.read_text())
        provision['health_period_sec']=cfg.fleet.perception_safety.timer_period_sec
        path.write_text(json.dumps(provision))
        public[robot.id]={k:v for k,v in provision.items() if k!='key_hex'}
    (args[1].parent/'native-fixtures-public.json').write_text(json.dumps(public,indent=2)+'\n')
    return cfg


def run(commands,namespaces,emit):
    mappings = []
    for name, command in commands:
        if name == 'bridge':
            mappings = [v for v in command if '@nav_msgs/msg/Odometry[' in v]
            if '--ros-args' not in command:command.append('--ros-args')
            for mapping in mappings:
                topic=mapping.split('@')[0]
                command.extend(['-r',topic+':='+topic.rsplit('/',1)[0]+'/t3b_raw_odom'])
    assert len(mappings)==len(namespaces)
    output = Path(sys.argv[2]).parent
    for name,command in commands:
        if name=='tf_helper':
            original=list(command)
            # Reuse the existing supervisor slot: both read-only transports stay
            # up for Nav2 shutdown and stop BEFORE the main bridge and Gazebo.
            command[:]=[sys.executable,str(Path(__file__).with_name('transports.py')),str(output),
                        json.dumps([sys.executable,str(Path(__file__).with_name('odometry_link.py')),sys.argv[1]]),json.dumps(original)]
    return original_run(commands,namespaces,emit)


t3a.t2.native.server.run_simulation=run
t3a.t2.native.server.generate=generate
if __name__=='__main__':raise SystemExit(t3a.t2.native.server.main())
