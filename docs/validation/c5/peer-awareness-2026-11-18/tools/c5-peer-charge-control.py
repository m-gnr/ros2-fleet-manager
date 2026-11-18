import json,time,urllib.request,uuid
from pathlib import Path
name='c5-demo-20261118T070545Z-8e1f5186661d';root=Path('/tmp')/name;s=json.loads((root/'session.json').read_text())
token=Path('/tmp/c5-peer-battery-token').read_text(); base=f"http://127.0.0.1:{s['api_port']}"
headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Origin':f"http://127.0.0.1:{s['ui_port']}"}
req=urllib.request.Request(base+'/api/sim/batteries',headers=headers)
with urllib.request.urlopen(req,timeout=10) as r:inventory=json.load(r)
assert inventory['enabled'] and all(r['available'] for r in inventory['robots'])
data=dict(request_id=str(uuid.uuid4()),all_robots=True,confirm_bulk_soc=True,safe_test_environment=True,soc_percent=24.0,mode='NORMAL',sessions={r['robot_id']:r['state']['session_id'] for r in inventory['robots']})
req=urllib.request.Request(base+'/api/sim/batteries',data=json.dumps(data).encode(),headers=headers,method='POST')
with urllib.request.urlopen(req,timeout=15) as r:result=json.load(r)
(root/'battery-control.json').write_text(json.dumps(dict(utc=time.time(),inventory=inventory,command=data,result=result),indent=2)+'\n')
print(result)
assert result['all_verified']
