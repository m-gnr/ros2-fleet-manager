import json,sys,statistics,collections,math
from pathlib import Path
root=Path(sys.argv[1])
def read(p):
 if not p.exists():return []
 return [json.loads(l) for l in p.read_text().splitlines() if l]
def summary(v):
 v=sorted(v)
 if not v:return None
 def q(p):return v[min(len(v)-1,math.ceil(len(v)*p)-1)]
 return dict(n=len(v),mean=statistics.mean(v),p50=q(.5),p95=q(.95),min=min(v),max=max(v))
def delta(rows,key='mono'):
 return [b[key]-a[key] for a,b in zip(rows,rows[1:])]
report={}
for directory in sorted(root.iterdir()):
 if not directory.is_dir() or not (directory/'system.jsonl').exists():continue
 s=read(directory/'system.jsonl');ros=read(directory/'ros-probe.jsonl');api=read(directory/'api-ws.jsonl');chrome=read(directory/'chrome.jsonl')
 stats=[r for r in s if r['kind']=='gazebo'];snaps=[r for r in s if r['kind']=='snapshot'];procs=[r for r in s if r['kind']=='proc'];pub=[r for r in snaps if r['changed']]
 x=dict(rtf=summary([r['data']['realTimeFactor'] for r in stats]),worst_rtf=sorted(stats,key=lambda r:r['data']['realTimeFactor'])[:5],snapshot_age=summary([r['age'] for r in snaps]),publisher_intervals=summary(delta(pub)),api_counts=dict(collections.Counter(r['kind'] for r in api)),api_success_duration_ms=summary([r['duration_ms'] for r in api if r['kind']=='api']))
 clocks=[r for r in ros if r['kind']=='clock'];x['clock_receive_intervals']=summary(delta(clocks));x['clock_rate']=(clocks[-1]['stamp']-clocks[0]['stamp'])/1e9/(clocks[-1]['mono']-clocks[0]['mono']) if len(clocks)>1 else None
 x['worst_clock_gaps']=sorted([dict(wall_s=b['mono']-a['mono'],sim_s=(b['stamp']-a['stamp'])/1e9,utc=a['utc']) for a,b in zip(clocks,clocks[1:])],key=lambda r:-r['wall_s'])[:5]
 x['ros']={}
 for kind in ('odom','tf','scan','physical','amcl'):
  for rid in ('robot_alpha','robot_beta','robot_gamma'):
   rows=[r for r in ros if r['kind']==kind and r.get('robot')==rid and (kind!='tf' or r.get('parent')!='map')]
   if not rows:continue
   x['ros'][kind+':'+rid]=dict(receive_s=summary(delta(rows)),source_stamp_s=summary([v/1e9 for v in delta(rows,'stamp')]),sim_age_s=summary([(r['clock']-r['stamp'])/1e9 for r in rows]))
 x['ws']={}
 for kind in ('ws_product','heartbeat'):
  x['ws'][kind]=summary(delta([r for r in api if r['kind']==kind]))
 for rid in ('robot_alpha','robot_beta','robot_gamma'):
  rows=[r for r in api if r['kind']=='scene' and r.get('robot_id')==rid and r.get('packet_type')=='robot_pose'];x['ws'][rid]=summary(delta(rows))
 x['ws']['stale_packets']=dict(collections.Counter(r.get('robot_id') for r in api if r['kind']=='scene' and r.get('status')=='STALE'))
 x['chrome']=dict(counts=dict(collections.Counter(r['kind'] for r in chrome)),renderer=next((r for r in chrome if r['kind']=='page_loaded'),None),long_tasks_ms=summary([v for r in chrome for v in r.get('longTasks',[])]),loop_lag_ms=summary([v for r in chrome for v in r.get('loopLagMs',[])]))
 dom=[r for r in chrome if r['kind']=='dom'];x['chrome']['tf']={}
 for rid in ('robot_alpha','robot_beta','robot_gamma'):
  states=[(r, next((v.get('status') for v in r.get('robots',[]) if v['id']==rid),None)) for r in dom]
  events=[];start=None
  for row,status in states:
   if status=='stale' and start is None:start=row['utc']
   if status!='stale' and start is not None:events.append([start,row['utc']]);start=None
  if start and states:events.append([start,states[-1][0]['utc']])
  from datetime import datetime
  durations=[(datetime.fromisoformat(b.replace('Z','+00:00'))-datetime.fromisoformat(a.replace('Z','+00:00'))).total_seconds() for a,b in events]
  x['chrome']['tf'][rid]=dict(stale_sample_count=sum(st=='stale' for r,st in states),total_samples=len(states),events=len(events),observed_durations_s=durations)
 d=collections.defaultdict(list);mem=[];total=[];ctx=[]
 for r in procs:
  mem.append(int(r['cgroup'].get('memory.current','0')))
  total.append(sum(p['cpu'] or 0 for p in r['rows']))
  ctx.append(sum(p['ctx_s'] or 0 for p in r['rows']))
  for p in r['rows']:
   if p['cpu'] is not None:d[p['cmd']].append(p['cpu'])
 x['cpu_processes']=sorted([dict(cmd=k,cpu=summary(v)) for k,v in d.items()],key=lambda r:-r['cpu']['mean'])
 x['container_memory_bytes']=summary(mem);x['container_proc_cpu']=summary(total[1:]);x['container_ctx_s']=summary(ctx[1:])
 report[directory.name]=x
(root/'summary.json').write_text(json.dumps(report,indent=2))
for k,v in report.items():print(k,json.dumps({q:v[q] for q in ('rtf','clock_rate','snapshot_age','publisher_intervals','api_counts','container_proc_cpu')}))
