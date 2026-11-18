import json,sys,bisect,math,collections
from pathlib import Path
sys.path.insert(0,'/tmp/c5-perf-tools')
namespace={}
exec(Path('/tmp/c5-perf-tools/summary.py').read_text().split('report={}')[0],namespace)
summary,read=namespace['summary'],namespace['read']
root=Path(sys.argv[1]);timing=read(root/'manager-timing.jsonl');original=read(root/'live/ros.jsonl');result={}
for d in root.iterdir():
 if not (d/'system.jsonl').exists():continue
 s=read(d/'system.jsonl');lo=min(x['mono'] for x in s);hi=max(x['mono'] for x in s);ts=[x for x in timing if lo<=x['mono']<=hi];ros=read(d/'ros-probe.jsonl');out={}
 out['sqlite_commit_s']=summary([x['duration_s'] for x in ts if x['kind']=='sqlite_statement' and x['sql']=='COMMIT'])
 out['sqlite_transaction_s']=summary([x['duration_s'] for x in ts if x['kind']=='sqlite_transaction'])
 out['event_loop_lag_s']=summary([x['lag_s'] for x in ts if x['kind']=='event_loop_lag'])
 out['event_duration_s']=summary([x['duration_s'] for x in ts if x['kind']=='event'])
 events=[x for x in ts if x['kind']=='event'];end_times=[x['mono'] for x in events];commits_by_kind=collections.defaultdict(list)
 for statement in ts:
  if statement['kind']!='sqlite_statement' or statement['sql']!='COMMIT':continue
  index=bisect.bisect_left(end_times,statement['mono'])
  if index<len(events) and events[index]['mono']-events[index]['duration_s']<=statement['mono']:
   commits_by_kind[events[index]['event']].append(statement['duration_s'])
 out['sqlite_commit_by_event_s']={kind:summary(values) for kind,values in commits_by_kind.items()}

 out['queue_depth']=summary([x['queue'] for x in ts if x['kind']=='event'])
 out['publisher_write_s']=summary([x['duration_s'] for x in ts if x['kind']=='publisher_write'])
 writes=[x['mono'] for x in ts if x['kind']=='publisher_write']
 out['publisher_actual_intervals_s']=summary([b-a for a,b in zip(writes,writes[1:])])
 out['publisher_right_censored_gap_s']=hi-writes[-1] if writes else None
 out['nav2_query_s']=summary([x['duration_s'] for x in ts if x['kind']=='nav2_query']);out['nav2_query_outcomes']=dict(collections.Counter('success' if x['success'] else 'no_route' for x in ts if x['kind']=='nav2_query'))
 tasks=[x for x in original if x['kind']=='SQLITE' and lo<=x['monotonic']<=hi]
 out['max_executing']=max([sum(t['status']=='EXECUTING' for t in x['tables']['tasks']) for x in tasks],default=0)
 out['task_states_last']=[dict(task=t['task_id'],state=t['status'],robot=t['robot_id']) for t in tasks[-1]['tables']['tasks']] if tasks else []
 out['action_results']=[dict(robot=x['robot'],action=x['action'],message=x['message']) for x in original if x['kind']=='ACTION_RESULT' and lo<=x['monotonic']<=hi]
 bins={}
 for r in s:
  if r['kind']!='gazebo':continue
  bins.setdefault(int((r['mono']-lo)//5),[]).append(r)
 windows=[]
 def ns(stamp):return int(stamp.get('sec',0))*10**9+int(stamp.get('nsec',0))
 for index,rs in bins.items():
  if len(rs)<2:continue
  seconds=rs[-1]['mono']-rs[0]['mono']
  windows.append(dict(start_utc=rs[0]['utc'],duration_s=seconds,samples=len(rs),rtf_by_received_sim_progress=(ns(rs[-1]['data']['simTime'])-ns(rs[0]['data']['simTime']))/1e9/seconds,reported_rtf_mean=sum(r['data']['realTimeFactor'] for r in rs)/len(rs)))
 out['worst_5s_simulation_windows']=sorted(windows,key=lambda x:x['rtf_by_received_sim_progress'])[:5]
 latest={};max_moving=0;triple=[]
 for r in ros:
  if r['kind']!='odom':continue
  latest[r['robot']]=r
  moving=[v for v in latest.values() if abs(r['stamp']-v['stamp'])<=100000000 and (abs(v['v'])>.01 or abs(v['w'])>.01)]
  max_moving=max(max_moving,len(moving))
  if len(moving)==3:triple.append(r['stamp'])
 out['max_simultaneous_odom_moving']=max_moving
 out['three_moving_source_stamp_span_s']=(max(triple)-min(triple))/1e9 if triple else None
 ordered=sorted(set(triple));segments=[]
 for stamp in ordered:
  if not segments or stamp-segments[-1][-1]>100000000:segments.append([stamp])
  else:segments[-1].append(stamp)
 segment=max(segments,key=lambda v:v[-1]-v[0]) if segments else []
 out['longest_three_moving_sample_segment_s']=(segment[-1]-segment[0])/1e9 if segment else None
 out['three_moving_segment_physical_displacement_m']={}
 for rid in ('robot_alpha','robot_beta','robot_gamma'):
  physical=[r for r in ros if r['kind']=='physical' and r['robot']==rid and segment and segment[0]<=r['stamp']<=segment[-1]]
  if len(physical)>1:
   out['three_moving_segment_physical_displacement_m'][rid]=math.hypot(physical[-1]['pose'][0]-physical[0]['pose'][0],physical[-1]['pose'][1]-physical[0]['pose'][1])

 out['unsafe_contacts']=[x for x in original if x['kind']=='UNSAFE_CONTACT' and lo<=x['monotonic']<=hi]
 out['observer_relative_callback_delay_s']={};out['amcl_xy_error_m']={};out['amcl_yaw_error_rad']={};out['physical_distance_m']={}
 for rid in ('robot_alpha','robot_beta','robot_gamma'):
  for kind,other in [('physical','PHYSICAL_POSE'),('odom','ODOMETRY')]:
   probes={x['stamp']:x['mono'] for x in ros if x['kind']==kind and x['robot']==rid};v=[]
   for x in original:
    if x['kind']!=other or x['robot']!=rid or not lo<=x['monotonic']<=hi:continue
    stamp=x['message']['header']['stamp'];ns=stamp['sec']*10**9+stamp['nanosec']
    if ns in probes:v.append(x['monotonic']-probes[ns])
   out['observer_relative_callback_delay_s'][kind+':'+rid]=summary(v)
  phys=sorted((x['stamp'],x['pose']) for x in ros if x['kind']=='physical' and x['robot']==rid);stamps=[x[0] for x in phys];v=[];yaw_errors=[]
  for x in ros:
   if x['kind']!='amcl' or x['robot']!=rid:continue
   i=bisect.bisect_left(stamps,x['stamp'])
   if i==0 or i>=len(phys):continue
   a,b=phys[i-1],phys[i]
   if b[0]-a[0]>150000000:continue
   k=(x['stamp']-a[0])/(b[0]-a[0]);p=[a[1][j]+k*(b[1][j]-a[1][j]) for j in (0,1)]
   v.append(math.hypot(x['pose'][0]-p[0],x['pose'][1]-p[1]))
   turn=math.atan2(math.sin(b[1][2]-a[1][2]),math.cos(b[1][2]-a[1][2]));truth_yaw=a[1][2]+k*turn
   yaw_errors.append(abs(math.atan2(math.sin(x['pose'][2]-truth_yaw),math.cos(x['pose'][2]-truth_yaw))))
  out['amcl_xy_error_m'][rid]=summary(v)
  out['amcl_yaw_error_rad'][rid]=summary(yaw_errors)
  out['physical_distance_m'][rid]=sum(math.hypot(b[1][0]-a[1][0],b[1][1]-a[1][1]) for a,b in zip(phys,phys[1:]))
 out['completed_task_physical_errors']=[]
 last_tasks=next((x['tables']['tasks'] for x in reversed(original) if x['kind']=='SQLITE'),[])
 by_uuid={t['goal_uuid'].replace('-',''):t for t in last_tasks if t.get('goal_uuid')}
 for action in original:
  if action['kind']!='ACTION_RESULT' or action['action']!='execute_task' or not lo<=action['monotonic']<=hi:continue
  task=by_uuid.get(action['uuid'].replace('-',''))
  if task is None:continue
  terminal=action['message']['result'];completion=terminal.get('completion_stamp')
  if not completion:continue
  ns=completion['sec']*10**9+completion['nanosec'];rid=action['robot']
  physical=sorted((x['stamp'],x['pose']) for x in ros if x['kind']=='physical' and x['robot']==rid)
  stamps=[x[0] for x in physical];i=bisect.bisect_left(stamps,ns)
  if i==0 or i>=len(physical):continue
  a,b=physical[i-1],physical[i]
  if b[0]-a[0]>150000000:continue
  k=(ns-a[0])/(b[0]-a[0]);pose=[a[1][j]+k*(b[1][j]-a[1][j]) for j in (0,1)];target=json.loads(task['snapshot'])['dropoff_pose']
  out['completed_task_physical_errors'].append(dict(task=task['task_id'],robot=rid,status=action['message']['status'],result_status=terminal['status'],assignment_epoch=task['assignment_epoch'],actual_completed_epoch=terminal['completed_epoch'],completion_stamp_ns=ns,physical_target_error_m=math.hypot(pose[0]-target['x'],pose[1]-target['y'])))
 result[d.name]=out
(root/'details.json').write_text(json.dumps(result,indent=2))
for name,x in result.items():print(name,json.dumps({k:x[k] for k in ['sqlite_commit_s','event_loop_lag_s','queue_depth','max_executing','nav2_query_s','task_states_last']}))
