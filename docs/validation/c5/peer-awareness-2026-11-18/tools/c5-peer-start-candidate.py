import datetime,json,os,sys,uuid,secrets
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'scripts'))
import c5_demo_start as start
import start_demo
name='c5-demo-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:12]
domain=start_demo.choose_domain(root)
Path('/tmp/c5-peer-candidate-active.json').write_text(json.dumps(dict(name=name,domain=domain,root=str(root))))
os.environ.update(C5_SESSION_ID=name,ROS_DOMAIN_ID=str(domain),C5_API_PORT='21830',C5_UI_PORT='21832')
battery="--battery" in sys.argv
token=secrets.token_hex(32) if battery else None
if battery:
 token_path=Path("/tmp/c5-peer-battery-token"); token_path.write_text(token); token_path.chmod(0o600)
original=start.run
def run(cmd,*args,**kwargs):
 if cmd[:2]==['docker','run']:
  cmd[-1]=cmd[-1]+' --peer-awareness-experiment'
  if battery:
   index=cmd.index(start.IMAGE)
   cmd[index:index]=['--env','FLEET_SIM_BATTERY_CONTROL=1','--env','FLEET_SIM_BATTERY_TOKEN='+token]
  safe=[('FLEET_SIM_BATTERY_TOKEN=<redacted>' if str(v).startswith('FLEET_SIM_BATTERY_TOKEN=') else v) for v in cmd]
  Path('/tmp/c5-peer-candidate-command.json').write_text(json.dumps(safe,indent=2)+'\n')
 return original(cmd,*args,**kwargs)
start.run=run
print(name,flush=True);sys.argv=[sys.argv[0],str(root)];sys.exit(start.main())
