"""Compare the first twenty sim seconds with three tasks EXECUTING, separately from whole-run data."""
import sys,json,bisect,math,statistics
from pathlib import Path

def read(p):return [json.loads(x) for x in p.read_text().splitlines()]
def stats(v):
 v=sorted(v)
 return dict(n=len(v),mean=statistics.mean(v),p50=v[(len(v)-1)//2],p95=v[min(len(v)-1,math.ceil(.95*len(v))-1)],max=max(v)) if v else None
result={}
for root_str,case in [('c5-perf-20261117T222323Z-0f9e7fb0','fairness-wal'),('c5-perf-20261117T223516Z-175dc2e9','composition')]:
 root=Path('/tmp')/root_str;original=read(root/'live/ros.jsonl');ros=read(root/case/'ros-probe.jsonl');system=read(root/case/'system.jsonl')
 three=next(r for r in original if r['kind']=='SQLITE' and sum(t['status']=='EXECUTING' for t in r['tables']['tasks'])==3)
 first=next(r for r in ros if r['kind']=='clock' and r['mono']>=three['monotonic'])
 last=next(r for r in ros if r['kind']=='clock' and r['stamp']>=first['stamp']+20_000_000_000)
 lo,hi=first['mono'],last['mono'];ss=[r for r in system if lo<=r['mono']<=hi];ps=[r for r in ss if r['kind']=='proc'];sc=[r['data']['realTimeFactor'] for r in ss if r['kind']=='gazebo']
 nav=[];rss=[];ctx=[];cpu=[]
 for r in ps:
  group=[p for p in r['rows'] if p['cmd'].startswith(('/opt/ros/humble/lib/nav2_','/opt/ros/humble/lib/rclcpp_components/component_container_isolated'))]
  nav.append(sum(p['cpu'] or 0 for p in group));rss.append(sum(p['rss'] for p in group));ctx.append(sum(p['ctx_s'] or 0 for p in group));cpu.append(sum(p['cpu'] or 0 for p in r['rows']))
 data=dict(start_source_ns=first['stamp'],end_source_ns=last['stamp'],wall_duration_s=hi-lo,clock_rate=(last['stamp']-first['stamp'])/1e9/(hi-lo),gazebo_reported_rtf=stats(sc),nav2_cpu_percent=stats(nav),nav2_sum_rss_bytes=stats(rss),nav2_context_switches_s=stats(ctx),container_proc_cpu_percent=stats(cpu),container_cgroup_memory_bytes=stats([int(r['cgroup']['memory.current']) for r in ps]),amcl_xy={},amcl_yaw={})
 for rid in ('robot_alpha','robot_beta','robot_gamma'):
  physical=sorted((r['stamp'],r['pose']) for r in ros if r['kind']=='physical' and r['robot']==rid);stamps=[r[0] for r in physical];xy=[];yaw=[]
  for r in ros:
   if r['kind']!='amcl' or r['robot']!=rid or not first['stamp']<=r['stamp']<=last['stamp']:continue
   i=bisect.bisect_left(stamps,r['stamp'])
   if i==0 or i>=len(physical):continue
   a,b=physical[i-1],physical[i]
   if b[0]-a[0]>150000000:continue
   k=(r['stamp']-a[0])/(b[0]-a[0]);p=[a[1][j]+k*(b[1][j]-a[1][j]) for j in (0,1)];xy.append(math.hypot(r['pose'][0]-p[0],r['pose'][1]-p[1]))
   delta=math.atan2(math.sin(b[1][2]-a[1][2]),math.cos(b[1][2]-a[1][2]));angle=r['pose'][2]-a[1][2]-k*delta;yaw.append(abs(math.atan2(math.sin(angle),math.cos(angle))))
  data['amcl_xy'][rid]=stats(xy);data['amcl_yaw'][rid]=stats(yaw)
 result[case]=data
out=Path('docs/validation/c5/performance-2026-11-18/matched-three-executing.json');out.write_text(json.dumps(result,indent=2)+'\n')
for case,data in result.items():print(case,json.dumps(data))
