import subprocess,sys,json,time,os,urllib.request,uuid
from pathlib import Path
m=json.loads(Path('/tmp/c5-perf-active.json').read_text());assert Path(m['root']).resolve()==Path.cwd().resolve(), 'Foreign workspace manifest';name=m['name'];session=Path('/tmp')/name
ports=json.loads((session/'session.json').read_text());api_port=ports['api_port'];ui_port=ports['ui_port']
label=sys.argv[1];seconds=float(sys.argv[2]);mode=sys.argv[3];out=session/label;out.mkdir(exist_ok=False)
(session/'tools').mkdir(exist_ok=True)
env=os.environ.copy();env['PYTHONPATH']=str(Path.cwd())
commands=[['docker','exec',name,'python3','/tmp/perf-tools/sample.py','/evidence/'+label,str(seconds)]]
if mode!='minimal':
 commands.append(['docker','exec',name,'bash','-c',f'source /opt/ros/humble/setup.bash; python3 /tmp/perf-tools/ros.py /evidence/{label}/ros-probe.jsonl {seconds}'])
 commands.append([sys.executable,'scripts/c5_telemetry_probe.py',str(session),str(out/'api-ws.jsonl'),'--seconds',str(seconds)])
if mode=='chrome':commands.append(['node','/tmp/c5-perf-tools/chrome.mjs',f'http://127.0.0.1:{ui_port}/',str(out/'chrome.jsonl'),str(seconds-3)])
children=[]
for i,command in enumerate(commands):
 log=(out/f'probe-{i}.log').open('w');children.append(subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env));log.close()
(out/'window.json').write_text(json.dumps(dict(start_utc=time.time(),label=label,mode=mode,commands=commands),indent=2))
if len(sys.argv)>4 and sys.argv[4]=='submit':
 time.sleep(15)
 with urllib.request.urlopen(f'http://127.0.0.1:{api_port}/api/task-catalog',timeout=3) as r:catalog=json.load(r)
 (out/'catalog.json').write_text(json.dumps(catalog,indent=2))
 requests=[dict(request_id=str(uuid.uuid4()),source_session_id=catalog['source_session_id'],profile_digest=catalog['profile_digest'],pickup_id=pickup,dropoff_id=dropoff,priority='MEDIUM') for pickup,dropoff in [('pick_A1','packing_1'),('pick_B2','delivery-01'),('pick_D1','shipping_2')]]
 pending=requests[:]
 for attempt in range(20):
  for request in pending[:]:
   req=urllib.request.Request(f'http://127.0.0.1:{api_port}/api/tasks',data=json.dumps(request).encode(),headers={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{ui_port}'},method='POST')
   try:
    with urllib.request.urlopen(req,timeout=8) as r:response=json.load(r)
   except Exception as e:response=dict(error=str(e))
   with (out/'submissions.jsonl').open('a') as f:f.write(json.dumps(dict(utc=time.time(),request=request,response=response,attempt=attempt))+'\n')
   print(response,flush=True)
   if 'task_id' in response:pending.remove(request)
  if not pending:break
  time.sleep(1)
while any(p.poll() is None for p in children):time.sleep(1)
print([(p.pid,p.returncode) for p in children],flush=True)
