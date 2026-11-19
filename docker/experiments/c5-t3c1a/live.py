"""Stationary product-FM scenarios. No nonzero, release, APPLIED or braking claim."""
import argparse
from collections import defaultdict
from copy import deepcopy
import gzip
import json
import math
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4

import rclpy
from rclpy.parameter import Parameter
from rclpy.signals import SignalHandlerOptions
from std_msgs.msg import String
from fleet_config import load_config
from fleet_config.native_zero import verify,load_key,sha,STATUS_DOMAIN

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'docker/simulation-common'))
from live_processes import bridge_executable


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--case',choices=['worker-stop','worker-kill','ipc-loss','duplicate','wrong-context',
        'wrong-session','corrupt','delayed'],required=True)
    args=parser.parse_args();args.profile=args.profile.resolve();args.output=args.output.resolve()
    args.output.mkdir(parents=True,exist_ok=False);cfg=load_config(args.profile)
    # Match the existing T3A fixture: live WAL is local to Linux, then backed up.
    db=Path('/tmp')/('t3c1a-'+str(uuid4())+'.sqlite3')
    children=[];node=None;expected=set();writer=defaultdict(list);states={};signed_status=defaultdict(dict);offset=0;carry='';native=None
    def launch(name,command):
        with (args.output/(name+'.log')).open('w') as stream:
            child=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT)
        children.append((name,child));return child
    def save(name,value):
        path=args.output/name;temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)
    def pump():
        nonlocal offset,carry
        if node:rclpy.spin_once(node,timeout_sec=.01)
        else:time.sleep(.02)
        path=args.output/'writer.jsonl'
        if path.exists():
            with path.open() as file:file.seek(offset);text=file.read();offset=file.tell()
            lines=(carry+text).split('\n');carry=lines.pop()
            for line in lines:
                if line:
                    record=json.loads(line);writer[record['robot_id']].append(record)
    def until(predicate,timeout=12.):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            pump()
            if (args.output/'unsafe-contact').exists():raise RuntimeError('Contact guard stop')
            failed=[(n,c.returncode) for n,c in children if c.poll() is not None and n not in expected]
            if failed:raise RuntimeError('Unexpected child exit: '+str(failed))
            if predicate():return
        raise TimeoutError('Bounded '+args.case+' predicate unavailable')
    def rows(sql,params=()):
        if not db.exists():return []
        try:
            with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as connection:
                connection.row_factory=sqlite3.Row;return [dict(row) for row in connection.execute(sql,params)]
        except sqlite3.OperationalError:return []
    def decisions(prefix):return [json.loads(r['decision']) for r in rows('SELECT decision FROM traffic_decisions WHERE event_id LIKE ?',(prefix+'%',))]
    try:
        launch('simulation',[sys.executable,str(Path(__file__).with_name('world.py')),str(args.profile),str(args.output/'generated'),'routes'])
        launch('observer',[sys.executable,'docker/simulation-warehouse-grid/stage1_observer.py',str(args.profile),str(args.output),'--database',str(db)])
        until(lambda:(args.output/'reset-verified.json').exists() and (args.output/'startup-readiness.json').exists()
              and json.loads((args.output/'startup-readiness.json').read_text())['current_status']=='READY',180.)
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        node=rclpy.create_node('t3c1a_stationary_probe',parameter_overrides=[Parameter('use_sim_time',value=True)])
        native=gzip.open(args.output/'native-verifier.jsonl.gz','wt')
        def observe(rid,message):
            value=json.loads(message.data);states[rid]=value;native.write(json.dumps(dict(robot_id=rid,**value))+'\n')
            status=verify(value['native_status'],load_key('/run/c5-b6b7/'+rid+'.json'),domain=STATUS_DOMAIN)
            signed_status[rid][status['command_sha256']]=status
        for robot in cfg.robots:
            node.create_subscription(String,robot.namespace+'/native_actuator',lambda m,r=robot.id:observe(r,m),1)
            launch('battery_'+robot.id,[sys.executable,'-c','from fleet_battery_simulator.node import main; main()',
                '--fleet-config',str(args.profile),'--robot-id',robot.id])
            launch('executor_'+robot.id,[sys.executable,'docker/experiments/c5-t3a/executor.py',str(args.profile),str(args.output),robot.id,'--initial'])
        launch('command_bridge',[bridge_executable()]+[r.namespace+'/authorized_zero@std_msgs/msg/String]ignition.msgs.StringMsg' for r in cfg.robots])
        manager=launch('manager',[sys.executable,'docker/experiments/c5-t3a/manager.py',str(args.profile),str(args.output),str(db)])
        until(lambda:len(rows('SELECT snapshot FROM robots'))==len(cfg.robots) and
            all(json.loads(r['snapshot'])['initial_status_verified'] for r in rows('SELECT snapshot FROM robots')))
        robots={r['robot_id']:json.loads(r['snapshot']) for r in rows('SELECT robot_id,snapshot FROM robots')}
        point=deepcopy(robots[cfg.robots[0].id]['pose']);point['x']-=.6;drop=deepcopy(point);drop['x']-=.6
        save('tasks.json',[dict(task_id='t3c1a-task',pickup=point,dropoff=drop)])
        until(lambda:any(a['status']=='NATIVE_ZERO_VERIFIED' for a in decisions('native-ack:')))
        acks=decisions('native-ack:');ack=next(a for a in acks if a['status']=='NATIVE_ZERO_VERIFIED');rid=ack['identity']['robot_id']
        until(lambda:writer[rid] and writer[rid][-1]['selection_reason']=='VERIFIED_ZERO')
        until(lambda:writer[rid][-1]['command_sha256'] in signed_status[rid])
        manifests=json.loads((args.output/'workers.json').read_text());pid=manifests[rid]['pid'];mappings=[]
        for path in Path('/proc').glob('[0-9]*/maps'):
            try:lines=path.read_text().splitlines()
            except (OSError,PermissionError):continue
            loaded=[line for line in lines if '/b6b7-native/' in line or 'physics-system.so' in line or 'dartsim-plugin.so' in line]
            if loaded:mappings.append(dict(pid=int(path.parent.name),mappings=loaded))
        save('loaded-mappings.json',mappings)
        gazebo=next(m['pid'] for m in mappings if any('libc5-authorized-zero-drive.so' in v for v in m['mappings']))
        assert pid!=gazebo
        transfer=next(t for t in decisions('native-transfer:') if t['transfer_id']==ack['transfer_id'])
        signed=json.loads(rows('SELECT payload FROM traffic_decisions WHERE event_id=?',('native-ack:'+ack['transfer_id'],))[0]['payload'])['payload']['native_status']
        assert verify(signed,load_key('/run/c5-b6b7/'+rid+'.json'),domain=STATUS_DOMAIN)==ack['native_status']
        assert ack['native_status']['command_sha256']==sha(transfer['body'])
        assert not ack['movement_authorized'] and not ack['ownership_release']
        selection=deepcopy(writer[rid][-1]);observed=signed_status[rid][selection['command_sha256']]
        selected_transfer=next(t for t in decisions('native-transfer:') if t['command_sha256']==selection['command_sha256'])
        assert selected_transfer['identity']==ack['identity']
        assert observed['receiver_session']==selection['native_session']
        assert observed['context_sha256']==selection['context_sha256']
        assert observed['sequence']==selection['command_sequence']
        save('writer-committed-binding.json',dict(selection=selection,native_status=observed,committed_transfer=selected_transfer))
        for row in rows('SELECT d.decision,o.payload FROM traffic_decisions d JOIN traffic_outbox o ON d.event_id=o.event_id'):
            assert row['decision']==row['payload']
        request=json.loads(transfer['body'])['command_context']['permit_event_id'][7:]
        save('release-request.json',dict(request_id=request))
        until(lambda:(args.output/'release-response.json').exists())
        assert json.loads((args.output/'release-response.json').read_text())['reason']=='RELEASE_THRESHOLDS_UNVERIFIED'
        before=deepcopy(writer[rid][-1]);started=time.monotonic_ns();start_index=len(writer[rid]);held=False
        process_evidence={}
        def process_status(process):
            path=Path('/proc')/str(process)/'status'
            return path.read_text() if path.exists() else 'PROCESS_ABSENT'
        try:
            if args.case=='worker-stop':
                os.kill(pid,signal.SIGSTOP);held=True
                until(lambda:'State:\tT' in process_status(pid))
            elif args.case=='worker-kill':os.kill(pid,signal.SIGKILL)
            else:save(rid+'-worker-fault.json',dict(mode={'ipc-loss':'ipc_close','wrong-context':'wrong_context','wrong-session':'wrong_session'}.get(args.case,args.case)))
            until(lambda:writer[rid][-1]['latched'])
            first_latched=deepcopy(writer[rid][-1]);until(lambda:writer[rid][-1]['post_completed_physics_updates']>first_latched['post_completed_physics_updates']+20)
            during=deepcopy(writer[rid][-1]);assert during['post_completed_physics_updates']>before['post_completed_physics_updates']
            assert during['sim_ns']>before['sim_ns']
            process_evidence=dict(worker_status_during=process_status(pid),gazebo_status_during=process_status(gazebo))
            if args.case=='worker-stop':assert 'State:\tT' in process_evidence['worker_status_during']
        finally:
            if held:os.kill(pid,signal.SIGCONT)
        if args.case=='worker-kill':
            save('worker-restart-request.json',dict(robot_id=rid))
            until(lambda:'restart_pid' in json.loads((args.output/'workers.json').read_text())[rid])
        previous=writer[rid][-1]['post_completed_physics_updates'];until(lambda:writer[rid][-1]['post_completed_physics_updates']>previous+20)
        after=deepcopy(writer[rid][-1]);assert after['latched'] and after['accepted']==first_latched['accepted']
        assert all(v['latched'] and v['pre_selected_joint_targets']==[0.,0.] for v in writer[rid][start_index:] if v['writer_steady_ns']>=first_latched['writer_steady_ns'])
        for samples in writer.values():assert all(v['pre_selected_joint_targets']==[0.,0.] for v in samples)
        spans={r:max(math.dist(v['post_world_position'][:2],samples[0]['post_world_position'][:2]) for v in samples) for r,samples in writer.items() if samples}
        assert all(span<.001 for span in spans.values())
        assert any(v['post_actual_velocity_known'] for v in writer[rid][start_index:])
        save('summary.json',dict(result='PASS_STATIONARY_SPLIT_ZERO_ONLY',case=args.case,robot_id=rid,worker_pid=pid,gazebo_pid=gazebo,
            fault_started_observer_monotonic_ns=started,before=before,first_latched=first_latched,during=during,after=after,
            committed_ack=ack,writer_samples={r:len(v) for r,v in writer.items()},max_stationary_displacement_m=spans,
            process_evidence=process_evidence,
            physics_counter_semantics='Completed stock Physics::Update, unpaused positive dt; not an external clock timer',
            nonzero_enabled=False,movement_authorized=False,physical_stop='UNKNOWN',ownership_release=False))
    finally:
        if native:native.close()
        exits={};quiet=False
        def priority(item):
            name=item[0]
            if name=='manager':return 0
            if name.startswith('executor'):return 1
            if name.startswith('battery'):return 2
            if 'bridge' in name:return 3
            if name=='observer':return 4
            return 5
        for name,child in sorted(reversed(children),key=priority):
            if 'bridge' in name and not quiet:
                # Stop this fixture's IGN command subscribers while physics/trace
                # still run. No producer or receiver is left racing bridge teardown.
                save('workers-stop-request.json',dict(reason='ORDERED_FIXTURE_SHUTDOWN'))
                deadline=time.monotonic()+6.
                while not (args.output/'workers-stopped.json').exists() and time.monotonic()<deadline:time.sleep(.02)
                if not (args.output/'workers-stopped.json').exists():exits['workers_stop_timeout']=True
                time.sleep(cfg.fleet.perception_safety.transport_sec);quiet=True
            if child.poll() is None:child.send_signal(signal.SIGTERM if name=='simulation' else signal.SIGINT)
            try:child.wait(timeout=50 if name=='simulation' else 10)
            except subprocess.TimeoutExpired:child.kill();child.wait();exits[name+'_forced']=True
            exits[name]=child.returncode
        save('shutdown.json',exits)
        if db.exists():
            with sqlite3.connect(db) as source,sqlite3.connect(args.output/'fleet.sqlite3') as target:source.backup(target)
        worker_exits=args.output/'worker-shutdown.json'
        if worker_exits.exists():
            found=json.loads(worker_exits.read_text())
            allowed=locals().get('rid') if args.case=='worker-kill' else None
            assert all(v==0 or (k==allowed and v==-9) for k,v in found.items()),found
        if node:node.destroy_node();rclpy.try_shutdown()
        if any(value!=0 for value in exits.values()):raise RuntimeError('Unclean scenario exit: '+str(exits))


if __name__=='__main__':main()
