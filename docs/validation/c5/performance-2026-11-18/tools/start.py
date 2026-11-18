import sys,os,json,uuid,datetime
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'scripts'));import c5_demo_start as start;import start_demo
name='c5-perf-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8];domain=start_demo.choose_domain(root)
Path('/tmp/c5-perf-active.json').write_text(json.dumps(dict(name=name,domain=domain,root=str(root))))
os.environ.update(C5_SESSION_ID=name,ROS_DOMAIN_ID=str(domain),C5_API_PORT='21720',C5_UI_PORT='21722')
old=start.run
instrumented='--instrumented' in sys.argv
if instrumented:
 def run(cmd,*a,**k):
  if cmd[:2]==['docker','run']:
   i=cmd.index(start.IMAGE);cmd[i:i]=['--volume','/tmp/c5-perf-tools:/perf-tools:ro']
   cmd[-1]=cmd[-1].replace('exec python3 docker/simulation-warehouse-grid/stage1_run.py','exec python3 /perf-tools/supervisor_probe.py')
  return old(cmd,*a,**k)
 start.run=run
print(name,flush=True);sys.argv=[sys.argv[0],str(root)];sys.exit(start.main())
