import json,urllib.request,uuid,time,sys
from pathlib import Path
root=Path('/tmp')/sys.argv[1]; s=json.loads((root/'session.json').read_text()); base=f"http://127.0.0.1:{s['api_port']}"
with urllib.request.urlopen(base+'/api/task-catalog') as r:c=json.load(r)
rows=[]
for pickup,dropoff in [('pick_A1','packing_1'),('pick_B2','delivery-01'),('pick_D1','shipping_2')]:
 data=dict(request_id=str(uuid.uuid4()),source_session_id=c['source_session_id'],profile_digest=c['profile_digest'],pickup_id=pickup,dropoff_id=dropoff,priority='MEDIUM')
 for attempt in range(5):
  try:
   req=urllib.request.Request(base+'/api/tasks',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':f"http://127.0.0.1:{s['ui_port']}"},method='POST')
   with urllib.request.urlopen(req,timeout=8) as r:response=json.load(r)
  except Exception as e:response=dict(error=str(e))
  rows.append(dict(utc=time.time(),request=data,response=response,attempt=attempt)); print(response,flush=True)
  if 'task_id' in response:break
  time.sleep(1)
(root/'submissions.json').write_text(json.dumps(rows,indent=2)+'\n')
