"""Compare retained Chrome, independent ROS results, and the closed SQLite database."""
import argparse
from collections import defaultdict
from datetime import datetime
import json
from math import atan2, hypot, sin, cos
from pathlib import Path
import sqlite3
from uuid import UUID


def stamp(value):
    return value['sec']*10**9+value['nanosec']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario',type=Path)
    parser.add_argument('chrome',type=Path)
    args=parser.parse_args()
    ros=[json.loads(line) for line in (args.scenario/'ros.jsonl').open()]
    chrome=[json.loads(line) for line in (args.chrome/'chrome-ws.jsonl').open()]
    browser=json.loads((args.chrome/'chrome-evidence.json').read_text())
    db=sqlite3.connect(f'file:{args.scenario}/fleet.sqlite3?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    tables={table:[dict(r) for r in db.execute('SELECT * FROM '+table)]
            for table in ('tasks','outbox_events','processed_events','reservations','task_review_holds','robots','station_moves')}
    report=dict(result='doğrulanamadı',checks={},tasks=[],robots={},collisions=[r for r in ros if r['kind']=='UNSAFE_CONTACT'],
                browser_result=browser['result'],integrity=db.execute('PRAGMA integrity_check').fetchall()[0][0],
                foreign_key_errors=[list(r) for r in db.execute('PRAGMA foreign_key_check')])
    (args.scenario/'sqlite-export.json').write_text(json.dumps(tables,indent=2))
    checks=report['checks']
    checks['sqlite_integrity']=report['integrity']=='ok' and not report['foreign_key_errors']
    checks['no_review_holds']=not tables['task_review_holds']
    checks['no_observed_collision']=not report['collisions']
    checks['chrome_scenario_passed']=browser['result']=='geçti'
    checks['one_task_per_browser_request']=len(tables['tasks'])==len(browser['responses'])
    checks['http_and_idempotency']=all(r['status']==201 and r['retry']['status']==200 and
        r['retry']['body']['outcome']=='DUPLICATE' and r['retry']['body']['task_id']==r['body']['task_id'] for r in browser['responses'])
    product=[r for r in chrome if 'type' not in r['packet']]
    all_status=[r for r in ros if r['kind']=='ROBOT_STATUS']
    for row in tables['tasks']:
        tid,rid,epoch,goal=row['task_id'],row['robot_id'],row['assignment_epoch'],row['goal_uuid']
        saved=json.loads(row['snapshot'])
        commands=[r for r in tables['outbox_events'] if r['task_id']==tid and r['kind']=='EXECUTE_TASK']
        results=[r for r in ros if r['kind']=='ACTION_RESULT' and r['action']=='execute_task'
                 and r['robot']==rid and r['uuid']==UUID(goal).hex]
        states=[r for r in all_status if r['message']['current_task_id']==tid]
        phases=[]
        for r in states:
            m=r['message']; phase=(m['current_phase'],m['is_loaded'])
            if not phases or tuple(phases[-1]['phase_loaded'])!=phase:
                phases.append(dict(utc=r['utc'],sim_ns=r['sim_ns'],phase_loaded=phase,status_seq=m['status_seq'],
                                   current_epoch=m['current_epoch']))
        nav=[r for r in ros if r['kind']=='ACTION_RESULT' and r['robot']==rid and r['action']=='navigate_to_pose'
             and states and states[0]['monotonic']<=r['monotonic']<=results[-1]['monotonic']] if results else []
        endpoints=[]
        for target,result in zip(('pickup_pose','dropoff_pose'),nav):
            poses=[r for r in ros if r['kind']=='PHYSICAL_POSE' and r['robot']==rid]
            p=min(poses,key=lambda r:abs(r['sim_ns']-result['sim_ns']))
            position=p['message']['pose']['position']; q=p['message']['pose']['orientation']
            yaw=atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
            target_pose=saved[target]
            endpoints.append(dict(target=target,utc=result['utc'],nav2_uuid=result['uuid'],
                terminal=result['message']['status'],physical_sample_sim_ns=p['sim_ns'],
                position_error_m=hypot(position['x']-target_pose['x'],position['y']-target_pose['y']),
                yaw_error_rad=abs(atan2(sin(yaw-target_pose['yaw']),cos(yaw-target_pose['yaw'])))))
        observed_payloads={r['payload'] for record in ros if record['kind']=='SQLITE'
                           for r in record['tables']['outbox_events'] if r['task_id']==tid and r['kind']=='EXECUTE_TASK'}
        browser_task=[r for p in product for r in p['packet']['tasks'] if r['task_id']==tid]
        unloaded=[r for r in all_status if r['robot']==rid and results and r['monotonic']>=results[0]['monotonic']
                  and r['message']['current_epoch']==epoch and not r['message']['current_task_id']
                  and not r['message']['is_loaded'] and r['message']['current_phase']==0]
        batteries=[r for r in ros if r['kind']=='BATTERY' and r['robot']==rid]
        task_energy=None
        if states and results and batteries:
            first=min(batteries,key=lambda r:abs(r['sim_ns']-states[0]['sim_ns']))
            last=min(batteries,key=lambda r:abs(r['sim_ns']-results[0]['sim_ns']))
            task_energy=dict(first_utc=first['utc'],last_utc=last['utc'],
                first_wh=first['message']['battery_energy_wh'],last_wh=last['message']['battery_energy_wh'],
                consumption_wh=first['message']['battery_energy_wh']-last['message']['battery_energy_wh'])
        taskchecks=dict(completed=row['status']=='COMPLETED',one_execute_command=len(commands)==1,
            executing_progress_persisted=any(r['stream'] and r['stream'].startswith('feedback:')
                                            and r['task_id']==tid for r in tables['processed_events']) and
                any(t['status']=='EXECUTING' for record in ros if record['kind']=='SQLITE'
                    for t in record['tables']['tasks'] if t['task_id']==tid),
            command_identity=bool(commands) and all(r['assignment_epoch']==epoch and r['goal_uuid']==goal and
                json.loads(r['payload'])['assigned_robot_id']==rid for r in commands),
            command_sent=bool(commands) and all(r['state']=='SENT' for r in commands),
            immutable_command_payload=len(observed_payloads)==1,
            actual_result_epoch=len(results)==1 and results[0]['message']['status']==4 and
                results[0]['message']['result']['status']==1 and results[0]['message']['result']['completed_epoch']==epoch,
            phases_and_cargo=[tuple(p['phase_loaded']) for p in phases]==[(1,False),(2,False),(3,True),(4,True)],
            unloaded_after_result=bool(unloaded),
            task_battery_consumption=task_energy is not None and task_energy['consumption_wh']>0,
            ros_identity=bool(states) and all(r['robot']==rid and r['message']['current_epoch']==epoch for r in states),
            two_nav2_successes=len(nav)==2 and all(r['message']['status']==4 for r in nav),
            physical_endpoint_acceptance=len(endpoints)==2 and all(p['position_error_m']<=.35 for p in endpoints),
            chrome_completed=bool(browser_task) and browser_task[-1]['status']=='COMPLETED' and browser_task[-1]['assigned_robot_id']==rid,
            one_submit_event=len([r for r in tables['processed_events'] if r['event_id']=='dashboard-'+tid.removeprefix('web-')])==1)
        report['tasks'].append(dict(task_id=tid,robot_id=rid,assignment_epoch=epoch,goal_uuid=goal,
            checks=taskchecks,phases=phases,nav2=endpoints,execute_results=results,commands=commands,
            unloaded_confirmation=unloaded[0] if unloaded else None,task_energy=task_energy,
            product_transitions=[r for r in browser['transitions'] if r['task']['task_id']==tid]))
    battery={}
    for r in ros:
        if r['kind']=='BATTERY':battery[(r['robot'],stamp(r['message']['battery_stamp']))]=r['message']
    for rid in {r['robot'] for r in all_status}:
        statuses=[r for r in all_status if r['robot']==rid]
        values=[r for r in ros if r['kind']=='BATTERY' and r['robot']==rid]
        energy=[r['message']['battery_energy_wh'] for r in values]
        matched=0;bad=0
        for product_row in product:
            for robot in product_row['packet']['robots']:
                if robot['robot_id']==rid and robot['battery_reliability']=='LIVE':
                    raw=battery.get((rid,int(robot['battery_sim_ns'])))
                    if raw:
                        matched+=1
                        bad+=abs(raw['battery_energy_wh']-robot['battery_energy_wh'])>1e-9
        tf_packets=[r for r in chrome if r['packet'].get('type')=='scene' and
                    r['packet']['packet'].get('type')=='robot_pose' and r['packet']['packet'].get('robot_id')==rid]
        status_index={(stamp(r['message']['pose']['header']['stamp'])):r['message']['pose']['pose']['position'] for r in statuses}
        tf_match=[]
        for r in tf_packets:
            p=r['packet']['packet'];match=status_index.get(int(p['stamp_ns']))
            if match:tf_match.append(hypot(p['x']-match['x'],p['y']-match['y']))
        report['robots'][rid]=dict(battery_first_wh=energy[0],battery_last_wh=energy[-1],consumption_wh=energy[0]-energy[-1],
            matched_chrome_battery_samples=matched,battery_mismatch_count=bad,tf_packets=len(tf_packets),
            matched_tf_status_stamps=len(tf_match),max_tf_status_error_m=max(tf_match,default=None),
            publisher_sessions=len({tuple(r['message']['publisher_session_id']['uuid']) for r in statuses}),
            status_sequence_strictly_increasing=all(a['message']['status_seq']<b['message']['status_seq'] for a,b in zip(statuses,statuses[1:])))
    checks['telemetry_consistency']=all(r['matched_chrome_battery_samples']>5 and r['battery_mismatch_count']==0
        and r['matched_tf_status_stamps']>5 and r['max_tf_status_error_m']<1e-6 and r['publisher_sessions']==1
        and r['status_sequence_strictly_increasing'] and r['consumption_wh']>0 for r in report['robots'].values())
    rendered=json.loads((args.chrome/'rendered.json').read_text())
    scene_poses={(p['robot_id'],p['stamp_ns']):p for r in chrome if r['packet'].get('type')=='scene'
                 for p in [r['packet']['packet']] if p.get('type')=='robot_pose'}
    draws=defaultdict(list)
    for row in rendered:
        detail=row['detail']; source=scene_poses.get((detail['robot_id'],detail['stamp_ns']))
        if source:
            draws[detail['robot_id']].append(hypot(detail['x']-source['x'],detail['z']+source['y']))
    report['rendered_tf_comparison']={rid:dict(samples=len(values),max_error_m=max(values)) for rid,values in draws.items()}
    checks['chrome_rendered_tf_matches']=len(draws)==2 and all(len(v)>5 and max(v)<1e-6 for v in draws.values())
    checks['reservation_single_owner']=all(not (s['reserved_by'] and s['occupied_by'] and s['reserved_by']!=s['occupied_by'])
        and not (s['state']=='FREE' and (s['reserved_by'] or s['occupied_by'])) for record in ros if record['kind']=='SQLITE'
        for s in record['tables']['reservations'])
    if browser['scenario']=='b':
        checks['different_robots']=len({r['robot_id'] for r in tables['tasks']})==2
        windows=[]
        for task in report['tasks']:
            s=[r for r in all_status if r['message']['current_task_id']==task['task_id']]
            if s:windows.append((s[0]['monotonic'],s[-1]['monotonic']))
        report['parallel_overlap_seconds']=min(w[1] for w in windows)-max(w[0] for w in windows) if len(windows)==2 else 0
        checks['parallel_execution']=report['parallel_overlap_seconds']>0
    report['result']='geçti' if all(checks.values()) and all(all(t['checks'].values()) for t in report['tasks']) else 'başarısız veya doğrulanamadı'
    (args.scenario/'comparison.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(result=report['result'],checks=checks,tasks=[dict(task_id=t['task_id'],checks=t['checks']) for t in report['tasks']],robots=report['robots']),indent=2))
    return 0 if report['result']=='geçti' else 1


if __name__=='__main__':
    raise SystemExit(main())
