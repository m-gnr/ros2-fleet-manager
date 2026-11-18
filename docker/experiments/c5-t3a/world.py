"""Only this experiment loads live-permit zero receivers. No stock Twist mapping."""
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('t2_world',ROOT/'docker/experiments/c5-t2/world.py')
t2=importlib.util.module_from_spec(spec);spec.loader.exec_module(t2)
original=t2.native.server.generate
original_run=t2.native.server.run_simulation


def generate(*args,**kwargs):
    cfg=original(*args,**kwargs)
    public={}
    for robot in cfg.robots:
        path=Path('/run/c5-b6b7')/(robot.id+'.json')
        data=json.loads(path.read_text())
        data.update(live_permits=True,robot_id=robot.id,source_session='',context={},permit_id='',generation=0,permit_sec=10.)
        path.write_text(json.dumps(data))  # New 0600 fixture file, before Gazebo loads it.
        public[robot.id]={k:v for k,v in data.items() if k!='key_hex'}
    (args[1].parent/'native-fixtures-public.json').write_text(json.dumps(public,indent=2)+'\n')
    return cfg


def run(commands,namespaces,emit):
    for name,command in commands:
        if name=='bridge':
            command[:]=[v for v in command if '@geometry_msgs/msg/Twist]' not in v]
    return original_run(commands,namespaces,emit)


t2.native.server.generate=generate
t2.native.server.run_simulation=run
if __name__=='__main__':raise SystemExit(t2.native.server.main())
