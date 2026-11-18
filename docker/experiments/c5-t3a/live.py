"""Real Gazebo, FM, Executor and bridge processes; immutable zero-only actuation."""
import argparse
from collections import defaultdict
from copy import deepcopy
import gzip
import hashlib
import json
import math
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4

import rclpy
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from fleet_config import load_config
from fleet_config.native_zero import compact,strict,sign,verify,sha,STATUS_DOMAIN,load_key

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'docker/simulation-common'))
from live_processes import bridge_executable


def main():
    p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--case',choices=['negative','replan','executor-loss','bridge-loss','fm-loss',
                                  'startup-missing','startup-delayed'],required=True)
    args=p.parse_args();args.profile=args.profile.resolve();args.output=args.output.resolve()
    args.output.mkdir(parents=True,exist_ok=False);cfg=load_config(args.profile)
    database=Path('/tmp')/('t3a-'+str(uuid4())+'.sqlite3')
    children=[];expected_dead=set();node=None;native_log=None
    states={};history=defaultdict(list);positions=defaultdict(list);publishers={};cases={}
    def launch(name,command):
        with (args.output/(name+'.log')).open('w') as log:
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        children.append((name,child));return child
    def pump(seconds=.01):
        if node:rclpy.spin_once(node,timeout_sec=seconds)
        else:time.sleep(seconds)
    def until(predicate,seconds=12.):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            pump()
            if (args.output/'unsafe-contact').exists():raise RuntimeError('Contact guard stop')
            failed=[(n,c.returncode) for n,c in children if c.poll() is not None and n not in expected_dead]
            if failed:raise RuntimeError('Unexpected child exit: '+str(failed))
            if predicate():return
        raise TimeoutError('Bounded '+args.case+' condition unavailable')
    def rows(sql,params=()):
        if not database.exists():return []
        try:
            with sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True) as db:
                db.row_factory=sqlite3.Row
                return [dict(r) for r in db.execute(sql,params)]
        except sqlite3.OperationalError:return []
    def acks():
        return [json.loads(r['decision']) for r in rows("SELECT decision FROM traffic_decisions WHERE event_id LIKE 'native-ack:%'")]
    def transfers():
        return [json.loads(r['decision']) for r in rows("SELECT decision FROM traffic_decisions WHERE event_id LIKE 'native-transfer:%'")]
    def stop_child(name,child,signum):
        expected_dead.add(name);child.send_signal(signum)
        end=time.monotonic()+8
        while child.poll() is None and time.monotonic()<end:pump()
        assert child.poll() is not None
    def command_bridge(name):
        return launch(name,[bridge_executable()]+[r.namespace+'/authorized_zero@std_msgs/msg/String]ignition.msgs.StringMsg' for r in cfg.robots])
    def publish_fixture(path,value):
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)
    def negative(robot,kind,expected):
        rid=robot.id
        key=load_key('/run/c5-b6b7/'+rid+'.json')
        original=next(t for t in transfers() if t['identity']['robot_id']==rid)
        before=len(history[rid]);end=time.monotonic()+2.
        packet=None;sent={}
        while time.monotonic()<end:
            body=json.loads(original['body']);current=states[rid]
            if kind=='duplicate':
                packet=sign(original['body'],key)
            else:
                body['actuator_session']=current['actuator_session'];body['ticket']=current['ticket']
                body['command_sequence']=current['sequence']+1000
                if kind=='generation':body['permit_generation']+=1
                if kind=='fm_session':body['source_session']=str(uuid4())
                if kind=='nonzero':body['velocity'][0]=.2
                if kind in ('epoch','child_uuid','path_hash','executor_session'):
                    ctx=body['command_context']
                    for label in ('permit','child'):
                        d=json.loads(ctx[label+'_decision'])
                        d['identity'][kind]=(d['identity'][kind]+1 if kind=='epoch' else
                                             'f'*64 if kind=='path_hash' else str(uuid4()))
                        # Use the same altered identity in both durable-record copies.
                        if label=='permit':replacement=d['identity'][kind]
                        else:d['identity'][kind]=replacement
                        ctx[label+'_decision']=json.dumps(d,sort_keys=True)
                        ctx[label+'_decision_sha256']=sha(ctx[label+'_decision'])
                packet=sign(compact(body),b'wrong-key' if kind=='signature' else key)
            sent[sha(strict(packet)['body'])]=packet
            publishers[rid].publish(String(data=packet));pump(.01)
            found=[s for s in history[rid][before:] if s['reason']==expected or
                   (kind=='nonzero' and s.get('inhibition_reason')==expected and
                    s.get('inhibited_command_sha256') in sent)]
            if found:
                if kind=='nonzero':packet=sent.get(found[-1].get('inhibited_command_sha256'),packet)
                cases[kind]=dict(expected=expected,observed=found[-1],wire=packet,movement_authorized=False)
                return
        raise AssertionError('Native did not reject '+kind+' as '+expected)
    try:
        simulation=launch('simulation',[sys.executable,str(Path(__file__).with_name('world.py')),str(args.profile),str(args.output/'generated'),'routes'])
        observer=launch('observer',[sys.executable,'docker/simulation-warehouse-grid/stage1_observer.py',str(args.profile),
                                  str(args.output),'--database',str(database)])
        def ready():
            path=args.output/'startup-readiness.json'
            return ((args.output/'reset-verified.json').exists() and path.exists()
                    and json.loads(path.read_text()).get('current_status')=='READY')
        until(ready,180.)
        mappings=[]
        for path in Path('/proc').glob('[0-9]*/maps'):
            try:entries=path.read_text()
            except (OSError,PermissionError):continue
            loaded=[line for line in entries.splitlines() if '/b6b7-native/libc5-authorized-zero-drive.so' in line]
            if loaded:mappings.append(dict(pid=int(path.parent.name),mappings=loaded))
        assert mappings, 'Actual native library mapping required'
        (args.output/'native-loaded-mappings.json').write_text(json.dumps(mappings,indent=2)+'\n')
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        node=rclpy.create_node('t3a_independent_native_probe',parameter_overrides=[Parameter('use_sim_time',value=True)])
        native_log=gzip.open(args.output/'native.jsonl.gz','wt')
        def record(rid,msg):
            value=strict(msg.data);states[rid]=value;history[rid].append(value)
            native_log.write(json.dumps(dict(robot=rid,**value))+'\n')
        delayed=cfg.robots[-1] if args.case.startswith('startup-') else None
        def executor_command(robot):
            return [sys.executable,str(Path(__file__).with_name('executor.py')),str(args.profile),str(args.output),
                    robot.id,'--initial']+(['--replan'] if args.case=='replan' else [])
        for robot in cfg.robots:
            node.create_subscription(String,robot.namespace+'/native_actuator',lambda m,r=robot.id:record(r,m),16)
            node.create_subscription(PoseStamped,robot.namespace+'/physical_pose',
                lambda m,r=robot.id:positions[r].append((m.pose.position.x,m.pose.position.y)),qos_profile_sensor_data)
            publishers[robot.id]=node.create_publisher(String,robot.namespace+'/authorized_zero',16)
            launch('battery_'+robot.id,[sys.executable,'-c','from fleet_battery_simulator.node import main; main()',
                                        '--fleet-config',str(args.profile),'--robot-id',robot.id])
            if robot!=delayed:launch('executor_'+robot.id,executor_command(robot))
        bridge=command_bridge('command_bridge')
        manager_command=[sys.executable,str(Path(__file__).with_name('manager.py')),str(args.profile),str(args.output),str(database)]
        manager=launch('manager',manager_command)
        if delayed:
            until(lambda: len(rows('SELECT robot_id FROM robots'))==len(cfg.robots))
            before=rows('SELECT robot_id,snapshot FROM robots')
            assert not next(json.loads(r['snapshot'])['initial_status_verified'] for r in before if r['robot_id']==delayed.id)
            assert rows('SELECT count(*) AS n FROM traffic_state')[0]['n']==0
            (args.output/'startup-held.json').write_text(json.dumps(dict(missing_robot=delayed.id,
                geometry_created=False,robot_snapshots=before),indent=2)+'\n')
            if args.case=='startup-missing':
                expected_dead.add('manager')
                until(lambda:manager.poll() is not None,20.)
                assert manager.returncode!=0 and 'Fresh actual RobotStatus required' in (args.output/'manager.log').read_text()
                assert rows('SELECT count(*) AS n FROM traffic_state')[0]['n']==0
                assert not transfers() and not acks() and not rows('SELECT * FROM outbox_events')
                assert all(s['target_linear']==s['target_angular']==0 and all(v is None or v==[0.] for v in s['joint_commands'])
                           for samples in history.values() for s in samples)
                (args.output/'summary.json').write_text(json.dumps(dict(result='PASS_SAFE_STARTUP_REFUSAL',case=args.case,
                    missing_robot=delayed.id,geometry_created=False,transfers=0,acks=0,
                    native_samples={r:len(v) for r,v in history.items()},movement_authorized=False,
                    physical_stop='UNKNOWN',ownership_release=False),indent=2)+'\n')
                return
            end=time.monotonic()+2.5
            while time.monotonic()<end:pump()
            assert rows('SELECT count(*) AS n FROM traffic_state')[0]['n']==0
            launch('executor_'+delayed.id,executor_command(delayed))
            cases['delayed_start']=dict(robot_id=delayed.id,delay_sec=2.5,geometry_before_status=False)
        def robot_ready():
            found=rows('SELECT snapshot FROM robots')
            return len(found)==len(cfg.robots) and all(json.loads(r['snapshot'])['initial_status_verified'] for r in found)
        until(robot_ready)
        records={r['robot_id']:json.loads(r['snapshot']) for r in rows('SELECT robot_id,snapshot FROM robots')}
        selected=cfg.robots[:1]
        tasks=[]
        for robot in selected:
            point=deepcopy(records[robot.id]['pose']);point['x']-=.6
            drop=deepcopy(point);drop['x']-=.6
            tasks.append(dict(task_id='t3a-'+robot.id,pickup=point,dropoff=drop))
        publish_fixture(args.output/'tasks.json',tasks)
        until(lambda:any(a['status']=='NATIVE_ZERO_VERIFIED' for a in acks()))
        initial_acks=deepcopy(acks())
        actual=next(a['identity']['robot_id'] for a in initial_acks if a['status']=='NATIVE_ZERO_VERIFIED')
        first=next(r for r in cfg.robots if r.id==actual)
        first_transfer=next(t for t in transfers() if t['identity']['robot_id']==first.id)
        publish_fixture(args.output/'release-request.json',dict(request_id=json.loads(first_transfer['body'])['command_context']['permit_event_id'][7:]))
        until(lambda:(args.output/'release-response.json').exists())
        assert json.loads((args.output/'release-response.json').read_text())['reason']=='RELEASE_THRESHOLDS_UNVERIFIED'
        cases['real_permit_native_ack']=dict(records=initial_acks,source='Real FM COMMIT/Outbox; actual native signed status')
        if args.case=='replan':
            until(lambda:any(a['status']=='NATIVE_ZERO_REVOKED' for a in acks()))
            until(lambda:states[first.id]['state']=='BLOCKED_REARM')
            old=states[first.id]['accepted'];publishers[first.id].publish(String(data=sign(first_transfer['body'],load_key('/run/c5-b6b7/'+first.id+'.json'))))
            until(lambda:states[first.id]['reason']=='BLOCKED_REARM')
            assert states[first.id]['accepted']==old
            cases['replan']=dict(native_revocation=[a for a in acks() if a['status']=='NATIVE_ZERO_REVOKED'],old_context_reopened=False)
        elif args.case=='negative':
            for kind,expected in [('signature','UNAUTHENTICATED'),('generation','PERMIT'),('fm_session','SESSION'),
                                  ('epoch','CONTEXT'),('child_uuid','CONTEXT'),('path_hash','CONTEXT'),
                                  ('executor_session','CONTEXT'),('duplicate','REPLAY'),('nonzero','NONZERO_DISABLED')]:
                negative(first,kind,expected)
        elif args.case=='executor-loss':
            child=next(c for n,c in children if n=='executor_'+first.id)
            stop_child('executor_'+first.id,child,signal.SIGKILL)
            until(lambda:states[first.id]['state']=='TIMED_OUT')
            cases['executor_loss']=deepcopy(states[first.id])
            launch('executor_restart',[sys.executable,str(Path(__file__).with_name('executor.py')),str(args.profile),str(args.output),first.id])
            until(lambda:(args.output/(first.id+'-restart-session.json')).exists())
            assert json.loads((args.output/(first.id+'-restart-session.json')).read_text())['blocked_on_start']
            until(lambda:any(json.loads(r['snapshot'])['session_blocked'] for r in rows('SELECT snapshot FROM robots WHERE robot_id=?',(first.id,))))
        elif args.case=='bridge-loss':
            stop_child('command_bridge',bridge,signal.SIGKILL)
            until(lambda:states[first.id]['state']=='TIMED_OUT')
            cases['bridge_loss']=deepcopy(states[first.id])
            command_bridge('bridge_restart')
            old=next(t for t in transfers() if t['identity']['robot_id']==first.id)
            end=time.monotonic()+4.;before=states[first.id]['rejected']
            while time.monotonic()<end and states[first.id]['rejected']==before:
                publishers[first.id].publish(String(data=sign(old['body'],load_key('/run/c5-b6b7/'+first.id+'.json'))));pump(.03)
            assert states[first.id]['rejected']>before and states[first.id]['state']=='BLOCKED_REARM'
            cases['bridge_restart']=dict(native=deepcopy(states[first.id]),reopened=False)
        elif args.case=='fm-loss':
            stop_child('manager',manager,signal.SIGKILL)
            until(lambda:states[first.id]['state']=='TIMED_OUT')
            cases['fm_loss']=deepcopy(states[first.id])
        # Restarting the actual manager with the same durable DB must fail closed.
        if manager.poll() is None:stop_child('manager',manager,signal.SIGINT)
        expected_dead.add('manager_restart')
        restarted=launch('manager_restart',manager_command)
        until(lambda:restarted.poll() is not None)
        assert restarted.returncode!=0 and 'ScenarioResetRequired' in (args.output/'manager_restart.log').read_text()
        cases['fm_restart']=dict(exit_code=restarted.returncode,scenario_reset_required=True)
        for robot,samples in history.items():
            assert all(s['target_linear']==s['target_angular']==0 and all(v is None or v==[0.] for v in s['joint_commands']) for s in samples)
        spans={rid:max(math.hypot(x-points[0][0],y-points[0][1]) for x,y in points) for rid,points in positions.items()}
        assert all(v<.001 for v in spans.values()) and not (args.output/'unsafe-contact').exists()
        # MAC and exact durable body validation independent of the FM's stage labels.
        for ack in acks():
            row=rows('SELECT payload FROM traffic_decisions WHERE event_id=?',('native-ack:'+ack['transfer_id'],))[0]
            signed=json.loads(row['payload'])['payload']['native_status']
            assert verify(signed,load_key('/run/c5-b6b7/'+ack['identity']['robot_id']+'.json'),domain=STATUS_DOMAIN)==ack['native_status']
            transfer=next(t for t in transfers() if t['transfer_id']==ack['transfer_id'])
            assert ack['native_status']['command_sha256']==sha(transfer['body'])
            assert not ack['movement_authorized'] and not ack['ownership_release']
        report=dict(result='PASS_REAL_FM_NATIVE_ZERO_ONLY',case=args.case,cases=cases,
            native_samples={r:len(v) for r,v in history.items()},max_stationary_displacement_m=spans,
            native_library_sha256=hashlib.sha256(Path('/b6b7-native/libc5-authorized-zero-drive.so').read_bytes()).hexdigest(),
            movement_authorized=False,physical_stop='UNKNOWN',ownership_release=False)
        (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:
        if native_log:native_log.close()
        exits={}
        for name,child in reversed(children):
            if child.poll() is None:child.send_signal(signal.SIGTERM if name=='simulation' else signal.SIGINT)
            try:child.wait(timeout=50 if name=='simulation' else 10)
            except subprocess.TimeoutExpired:child.kill();child.wait();exits[name+'_forced']=True
            exits[name]=child.returncode
        if database.exists():
            with sqlite3.connect(database) as source,sqlite3.connect(args.output/'fleet.sqlite3') as target:source.backup(target)
        (args.output/'shutdown.json').write_text(json.dumps(exits,indent=2)+'\n')
        if node:node.destroy_node();rclpy.try_shutdown()
        unexpected={k:v for k,v in exits.items() if v!=0 and k not in expected_dead}
        if unexpected:raise RuntimeError('Unexpected shutdown: '+str(unexpected))


if __name__=='__main__':main()
