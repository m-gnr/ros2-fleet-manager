import datetime,json,os,sys,uuid
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'scripts'))
import c5_demo_start as start
import start_demo
name='c5-native-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:12]
domain=start_demo.choose_domain(root)
Path('/tmp/c5-b6b7-active.json').write_text(json.dumps(dict(name=name,domain=domain,root=str(root))))
os.environ.update(C5_SESSION_ID=name,ROS_DOMAIN_ID=str(domain),C5_API_PORT='21920',C5_UI_PORT='21922')
start.IMAGE='c5-b6b5-build:local'
original=start.run
def run(cmd,*args,**kwargs):
 if cmd[:2]==['docker','run']:
  i=cmd.index(start.IMAGE);cmd[i:i]=['--volume','/tmp/c5-b6b7-build:/b6b7-native:ro']
  cmd[-1]=cmd[-1].replace('exec python3 docker/simulation-warehouse-grid/stage1_run.py','exec python3 docker/experiments/c5-b6b7/supervisor.py')+' --peer-awareness-experiment'
  Path('/tmp/c5-b6b7-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
 return original(cmd,*args,**kwargs)
start.run=run
print(name,flush=True);sys.argv=[sys.argv[0],str(root)];sys.exit(start.main())
