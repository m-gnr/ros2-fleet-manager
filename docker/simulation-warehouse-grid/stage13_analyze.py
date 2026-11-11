"""Reconcile diagnostics by message stamp; never extrapolate missing transforms."""
from bisect import bisect_left
from collections import Counter
import json
from math import cos, sin, hypot
from pathlib import Path
import statistics
import sys
from stage12_analyze import at, stamp, pose, angle, analyze as odom_analyze


def interpolate(rows,t,unbounded=False):
    if not rows:return None
    i=bisect_left([r[0] for r in rows],t)
    if i<len(rows) and rows[i][0]==t:return rows[i][1]
    if 0<i<len(rows) and (unbounded or rows[i][0]-rows[i-1][0]<=100_000_000):
        a,b=rows[i-1],rows[i];f=(t-a[0])/(b[0]-a[0])
        return [a[1][0]+f*(b[1][0]-a[1][0]),a[1][1]+f*(b[1][1]-a[1][1]),a[1][2]+f*angle(b[1][2]-a[1][2])]
    return None


def compose(a,b):
    return [a[0]+cos(a[2])*b[0]-sin(a[2])*b[1],a[1]+sin(a[2])*b[0]+cos(a[2])*b[1],angle(a[2]+b[2])]


def inverse(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    return [cos(a[2])*dx+sin(a[2])*dy,-sin(a[2])*dx+cos(a[2])*dy,angle(b[2]-a[2])]


def cell(msg,p):
    info=msg['info'];origin=pose(info['origin']);v=inverse(origin,p);r=info['resolution']
    x,y=int(v[0]//r),int(v[1]//r)
    if 0<=x<info['width'] and 0<=y<info['height']:
        return msg['data'][y*info['width']+x]
    return None


def distribution(values):
    if not values:return None
    return dict(count=len(values),min=min(values),median=statistics.median(values),max=max(values),mean=statistics.mean(values))


def analyze(folder):
    report=json.loads((folder/'localization.json').read_text())
    if report.get('error') or not all(report.get(key) for key in ('initial','terminal','stopped')):
        result=dict(folder=str(folder),measurement_valid=False,error=report.get('error','missing synchronized sample'),
            nav2_terminal=report.get('nav2_terminal'),physical_error_m=report.get('stopped',{}).get('physical_target_error_m'),
            passed=False,physical_criteria_passed=False,shutdown=json.loads((folder/'shutdown.json').read_text()))
        (folder/'analysis.json').write_text(json.dumps(result,indent=2));return result
    truth={};physical_receipts={};odometry={};corrections={};amcl=[];particle_messages=[];freq={};tf_lag=[]
    def addfreq(kind,t):freq.setdefault(kind,set()).add(t)
    for line in (folder/'localization.jsonl').open():
        row=json.loads(line);msg=row.get('message',{});kind=row['kind']
        if kind=='PHYSICAL' and row['robot']=='robot_beta':
            t=stamp(msg['header']['stamp']);truth[t]=pose(msg['pose']);physical_receipts[t]=row['monotonic']
        elif kind=='ODOMETRY':
            t=stamp(msg['header']['stamp']);odometry[t]=pose(msg['pose']['pose']);addfreq(kind,t)
        elif kind=='SCAN':addfreq(kind,stamp(msg['header']['stamp']))
        elif kind=='PARTICLES':particle_messages.append(msg)
        elif kind=='AMCL':amcl.append(dict(stamp_ns=stamp(msg['header']['stamp']),pose=pose(msg['pose']['pose']),covariance=msg['pose']['covariance']))
        elif kind=='TF':
            for tf in msg['transforms']:
                t=stamp(tf['header']['stamp']);v=tf['transform'];q=v['rotation']
                p=[v['translation']['x'],v['translation']['y'],pose(dict(position=v['translation'],orientation=q))[2]]
                if tf['header']['frame_id']=='map':corrections[t]=p
                else:
                    addfreq('ODOM_TF',t);tf_lag.append((row['sim_ns']-t)/1e9)
    tr=sorted(truth.items());ot=sorted(odometry.items());ct=sorted(corrections.items());synchronized=[]
    start=report['initial']['sim_ns'];end=report['stopped']['sim_ns']
    for t,o in ot:
        if not start<=t<=end:continue
        p=interpolate(tr,t);c=interpolate(ct,t,True)
        if p is None or c is None:continue
        m=compose(c,o)
        synchronized.append(dict(stamp_ns=t,physical=p,odom=o,map_odom=c,map_pose=m,
            error_x_m=m[0]-p[0],error_y_m=m[1]-p[1],error_m=hypot(m[0]-p[0],m[1]-p[1]),yaw_error_rad=angle(m[2]-p[2]),
            rack_A2_physical_distance_m=hypot(max(.25-p[0],0,p[0]-4.25),max(6.5-p[1],0,p[1]-7.5)),
            rack_A2_map_distance_m=hypot(max(.25-m[0],0,m[0]-4.25),max(6.5-m[1],0,m[1]-7.5))))
    (folder/'synchronized.json').write_text(json.dumps(synchronized,indent=2))
    costs=[];counts=Counter();recoveries=[];reasons=Counter();candidate_count=0;rejected=0;plan_lengths=[]
    for line in (folder/'diagnostics.jsonl').open():
        row=json.loads(line);kind=row['kind'];counts[kind]+=1;msg=row['message']
        if kind=='NAV_FEEDBACK':recoveries.append(msg['feedback']['number_of_recoveries'])
        elif kind=='CANDIDATES':
            candidate_count+=msg['count'];rejected+=msg['rejected'];reasons.update(msg['reasons'])
        elif kind in ('GLOBAL_PLAN','LOCAL_PLAN'):
            ps=[pose(p['pose']) for p in msg['poses']]
            length=sum(hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(ps,ps[1:]))
            plan_lengths.append(dict(kind=kind,stamp_ns=stamp(msg['header']['stamp']),frame=msg['header']['frame_id'],length_m=length,points=len(ps)))
        elif kind in ('LOCAL_COSTMAP','GLOBAL_COSTMAP'):
            t=stamp(msg['header']['stamp']);p=interpolate(tr,t);o=interpolate(ot,t);c=interpolate(ct,t,True)
            if p is None or o is None or c is None:continue
            m=compose(c,o)
            # Ground truth is in the desired map/world frame. Transform it to the
            # published grid frame at this exact stamp before sampling a grid cell.
            frame=msg['header']['frame_id']
            if frame=='map':estimate,actual=m,p
            elif frame=='robot_beta/odom':estimate,actual=o,inverse(c,p)
            else:continue
            costs.append(dict(kind=kind,stamp_ns=t,frame=frame,estimated_center_cost=cell(msg,estimate),
                true_center_projected_cost=cell(msg,actual),physical=p,map_pose=m))
    amcl_error=[]
    for item in amcl:
        p=interpolate(tr,item['stamp_ns'])
        if p is not None:amcl_error.append(dict(**item,physical=p,error_m=hypot(p[0]-item['pose'][0],p[1]-item['pose'][1])))
    particle_summaries=[]
    for msg in particle_messages:
        t=stamp(msg['header']['stamp']);p=interpolate(tr,t)
        if p is None:continue
        particles=msg['particles'];weights=[v['weight'] for v in particles];total=sum(weights)
        if total<=0:continue
        poses=[pose(v['pose']) for v in particles]
        distances=[hypot(v[0]-p[0],v[1]-p[1]) for v in poses]
        particle_summaries.append(dict(stamp_ns=t,count=len(particles),
            x_range=[min(v[0] for v in poses),max(v[0] for v in poses)],
            y_range=[min(v[1] for v in poses),max(v[1] for v in poses)],
            weighted_true_center_error_m=hypot(sum(w*v[0] for w,v in zip(weights,poses))/total-p[0],sum(w*v[1] for w,v in zip(weights,poses))/total-p[1]),
            weight_within_10cm=sum(w for w,d in zip(weights,distances) if d<=.1)/total,
            weight_within_35cm=sum(w for w,d in zip(weights,distances) if d<=.35)/total,
            effective_sample_size=total*total/sum(w*w for w in weights)))
    suffix=[]
    for item in reversed(synchronized):
        if item['error_m']>.1:break
        suffix.append(item['stamp_ns'])
    convergence_suffix_s=(max(suffix)-min(suffix))/1e9 if len(suffix)>1 else 0.
    frequency={k:(len(ts)-1)/((max(ts)-min(ts))/1e9) if len(ts)>1 else None for k,ts in freq.items()}
    performance=[]
    start_mono=physical_receipts.get(start);end_mono=physical_receipts.get(end)
    for line in (folder/'performance.jsonl').open():
        perf_row=json.loads(line)
        if start_mono is None or end_mono is None or not start_mono<=perf_row['monotonic']<=end_mono:continue
        for process in perf_row['processes']:
            if '/amcl ' in process['command'] and '/robot_beta' in process['command'] and process['cpu_percent'] is not None:performance.append(process['cpu_percent'])
    shutdown=json.loads((folder/'shutdown.json').read_text())
    metrics=odom_analyze(folder)
    stop_rows=[v for t,v in tr if end-1_000_000_000<=t<=end]
    terminal=report['terminal']
    stop_displacement=hypot(report['stopped']['physical'][0]-terminal['physical'][0],report['stopped']['physical'][1]-terminal['physical'][1])
    stationary_span=max((hypot(b[0]-a[0],b[1]-a[1]) for a in stop_rows for b in stop_rows),default=None)
    safe_stop=(report['stopped']['linear_speed_m_s']<=.01 and report['stopped']['angular_speed_rad_s']<=.01 and stationary_span is not None and stationary_span<=.01)
    result=dict(folder=str(folder),measurement_valid=True,nav2_terminal=report.get('nav2_terminal'),physical_error_m=report['stopped']['physical_target_error_m'],
        yaw_error_rad=report['stopped']['physical_target_yaw_error_rad'],map_physical_m=report['stopped']['map_physical_error_m'],
        physical_criteria_passed=report.get('nav2_terminal')==4 and report['stopped']['physical_target_error_m']<=.35 and not report['contacts'] and safe_stop,
        passed=report.get('nav2_terminal')==4 and report['stopped']['physical_target_error_m']<=.35 and not report['contacts'] and safe_stop and shutdown['simulation_exit']==0 and shutdown['probe_exit']==0,
        physical_post_terminal_displacement_m=stop_displacement,physical_last_second_span_m=stationary_span,safe_stop=safe_stop,
        terminal_to_stopped_sim_s=(end-terminal['sim_ns'])/1e9,contacts=report['contacts'],stopped_linear_m_s=report['stopped']['linear_speed_m_s'],stopped_angular_rad_s=report['stopped']['angular_speed_rad_s'],
        covariance_stamp_ns=report['stopped']['amcl_stamp_ns'],covariance_age_s=report['stopped']['amcl_age_ns']/1e9,
        covariance=[report['stopped']['amcl_covariance'][i] for i in (0,7,35)],max_recoveries=max(recoveries,default=None),
        diagnostics_counts=dict(counts),candidate_samples=candidate_count,candidate_rejected=rejected,reasons=dict(reasons),
        synchronized_map_error=distribution([x['error_m'] for x in synchronized]),amcl_measurement_error=distribution([x['error_m'] for x in amcl_error]),
        beta_amcl_cpu_percent=distribution(performance),observed_rtf=(end-start)/1e9/(end_mono-start_mono) if end_mono and start_mono and end_mono>start_mono else None,
        goal_window_sim_s=(report['terminal_received_sim_ns']-start)/1e9,
        frequencies_hz=frequency,odom_tf_receipt_lag_s=distribution(tf_lag),aligned_odom_endpoint_error_m=metrics['endpoint_error_m'],
        convergence_10cm_final_suffix_s=convergence_suffix_s,particle_summaries=particle_summaries,
        shutdown=shutdown,costmap_samples=costs,plans=plan_lengths,amcl_measurements=amcl_error)
    (folder/'analysis.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    root=Path(sys.argv[1]);results=[]
    for file in sorted(root.glob('*/pickup-*/shutdown.json')):
        results.append(analyze(file.parent))
    (root/'experiment-results.json').write_text(json.dumps([{k:v for k,v in r.items() if k not in ('costmap_samples','plans','amcl_measurements','particle_summaries')} for r in results],indent=2))
    for r in results:print(r['folder'],r.get('nav2_terminal'),r.get('physical_error_m'),r.get('map_physical_m'),r.get('passed'))
