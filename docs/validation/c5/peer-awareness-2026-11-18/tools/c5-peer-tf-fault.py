import json,subprocess,time,urllib.request
from pathlib import Path
name='c5-demo-20261118T070545Z-8e1f5186661d';root=Path('/tmp')/name;s=json.loads((root/'session.json').read_text());base=f"http://127.0.0.1:{s['api_port']}"
snap={}
for route in ['robots','stations','tasks']:
 with urllib.request.urlopen(base+'/api/'+route,timeout=3) as r:snap[route]=json.load(r)
assert all(r['state']=='CHARGING' and r['charging']=='CHARGING' for r in snap['robots']['robots'])
assert not(root/'live/unsafe-contact').exists()
(root/'charge-arrived.json').write_text(json.dumps(dict(utc=time.time(),snapshot=snap,unsafe_contact=False),indent=2)+'\n')
ps=subprocess.check_output(['docker','exec',name,'ps','-eo','pid,args'],text=True)
rows=[line.split(None,1) for line in ps.splitlines() if '/workspace/docker/simulation-warehouse-grid/tf.py ' in line and 'python3' in line]
assert len(rows)==1,rows
pid=int(rows[0][0]);events=[]
def signal(sig):
 code=f'import json,os,signal,time; os.kill({pid},signal.SIG{sig}); print(json.dumps(dict(utc=time.time(),monotonic=time.monotonic(),signal="{sig}",pid={pid})))'
 event=json.loads(subprocess.check_output(['docker','exec',name,'python3','-c',code],text=True));events.append(event)
try:
 signal('STOP');time.sleep(4)
finally:
 signal('CONT')
time.sleep(3)
(root/'tf-fault.json').write_text(json.dumps(dict(target=rows[0][1],events=events,scope='stationary while charging; TF odometry source only'),indent=2)+'\n')
print(events)
