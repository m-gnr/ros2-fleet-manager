"""Actual product Outbox/ExecuteTask/Nav2 identity test, stationary zero-only world.

No moving safety acceptance. Raw Nav2 commands may be nonzero, but the world
has only B6B.7 immutable zero-only joint writers. No APPLIED or release is sent.
"""
import argparse
import asyncio
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
import json
import gzip
import hashlib
import math
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from uuid import uuid4

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rosidl_runtime_py.convert import message_to_ordereddict
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from fleet_interfaces.msg import TrafficChildObservation
import yaml

from fleet_config import load_config
from fleet_robot_executor.node import RobotExecutorNode
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.event_loop import FleetEventLoop, Event, OutboxDispatcher
from backend.fleet_manager.persistence.store import SQLiteStore
from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
from backend.fleet_manager.domain import Pose2D
from backend.fleet_manager.domain.traffic import Box, PermitIdentity, ReleaseEvidence


async def until(predicate, seconds=45.):
    end = time.monotonic()+seconds
    while time.monotonic()<end:
        if predicate(): return
        await asyncio.sleep(.025)
    raise TimeoutError('Bounded identity fixture condition unavailable')


async def case(args, cfg, node, pool, nodes, positions, native_states, sample_lock):
    from fleet_robot_executor.node import RobotExecutorNode
    core, robot_ids = build_fleet_manager_from_config(args.profile)
    store = SQLiteStore(args.database)
    consumer = FleetEventLoop(store, core)
    selected = cfg.robots[0]
    params = yaml.safe_load((args.output/'generated'/('nav2-'+selected.id+'.yaml')).read_text())
    radius = params['local_costmap']['local_costmap']['ros__parameters']['robot_radius']
    consumer.enable_traffic_protocol_test(enclosing_radius=radius)
    await consumer.start()
    adapter = FleetROS2Adapter(node, consumer, asyncio.get_running_loop(), robot_ids,
        robot_namespaces={r.id:r.namespace for r in cfg.robots}, traffic_protocol_test=True, enable_live_routing=False)
    async def query(robot, start, goal, **kwargs):
        result = await adapter.route_resolver.compute_route(robot,start,goal,**kwargs)
        with (args.output/'route-queries.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(robot=robot,start=asdict(start),goal=asdict(goal),distance=result))+'\n')
        return result
    consumer.enable_live_routing(query)
    settings = json.loads(Path('config/simulation-c3-3-3.json').read_text())
    for robot in cfg.robots:
        profile = None
        if robot.id == selected.id:
            profile = dict(template='/opt/ros/humble/share/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml',
                output_dir=str(args.output/'trees'/robot.id), map_revision='t2-map', geometry_revision='t2-geometry',
                frame=cfg.warehouse.frame_id, radius=radius, timeout=30.)
        executor = RobotExecutorNode('t2_executor_'+robot.id, _test_reset_verified=True,
            parameter_overrides=[Parameter('fleet_config_path',value=str(args.profile)),Parameter('robot_id',value=robot.id),
                Parameter('robot_namespace',value=robot.namespace),Parameter('use_sim_time',value=True),
                Parameter('duplicate_record_capacity',value=settings['executor_duplicate_record_capacity'])],
            _traffic_child_test_profile=profile)
        pool.add_node(executor);nodes.append(executor)
    observer = nodes[0]._traffic_child_observer
    child_messages=[]
    node.create_subscription(TrafficChildObservation,selected.namespace+'/traffic_child_observation',
        lambda message:child_messages.append(message_to_ordereddict(message)),32)
    dispatch = OutboxDispatcher(consumer,adapter.outbox_sender,clock=time.monotonic,retry_delay=1.)
    stopping = asyncio.Event()
    async def drive():
        while not stopping.is_set():
            await consumer.submit(Event('TICK',{'current_time':time.monotonic()}))
            await dispatch.send_one()
            await asyncio.sleep(.05)
    worker = asyncio.create_task(drive())
    try:
        await until(lambda: all(r.initial_status_verified and not r.session_blocked and not r.is_stale(time.monotonic())
                              for r in consumer.core.tracker.list_robots()))
        b=cfg.warehouse.bounds
        await consumer.submit(Event('TRAFFIC_CONFIGURE', dict(revision='t2-map',frame=cfg.warehouse.frame_id,
            geometry_revision='t2-geometry',managed=[asdict(Box(b.x_min,b.y_min,b.x_max,b.y_max))])))
        await until(lambda: all(native_states[r.id] for r in cfg.robots))
        pose = consumer.core.tracker.get_robot(selected.id).pose
        # A short real Nav2 path, held at rest by the native zero writer, exposes
        # the stock 1 Hz replanner. This is not a successful physical transport.
        target = Pose2D(pose.x-.6,pose.y,pose.yaw)
        dropoff = Pose2D(pose.x-1.2,pose.y,pose.yaw)
        await consumer.submit(Event('SUBMIT_TASK',dict(task_id='t2-real-task',pickup_pose=target,dropoff_pose=dropoff,
            priority=3,created_at=time.monotonic())))
        await until(lambda: any(p['child_provenance']['kind']==1 for p in observer.events))
        await until(lambda: any(d.status=='RESERVED' for d in observer.decisions))
        await until(lambda: observer.binding.closed)
        owner = consumer.core._active_tasks_by_robot[selected.id]
        actual = observer.events[0]
        assert actual['execute_uuid']==owner.goal_uuid
        assert len({actual['execute_uuid'],observer.binding.nav_uuid,actual['child_uuid']})==3
        assert actual['task_id']==owner.task_id and actual['epoch']==owner.assignment_epoch
        assert actual['executor_session']==str(nodes[0].safety.session_id)
        decision = next(d for d in observer.decisions if d.status=='RESERVED')
        assert bytes(decision.identity.child_uuid.uuid)==__import__('uuid').UUID(actual['child_uuid']).bytes
        # Stop dispatch before cancellation can legitimately requeue the task.
        # Domain scheduling is unchanged; a new PENDING Outbox item is not sent.
        stopping.set();await worker
        # Real parent cancellation; no synthetic PREEMPTED, child terminal or stop proof.
        handle = adapter.action_bridges[selected.id]._active_goal_handles[owner.goal_uuid]
        cancel = handle.cancel_goal_async()
        await until(cancel.done)
        result_future = handle.get_result_async()
        await until(result_future.done)
        result=result_future.result()
        assert result.status==5 and result.result.completed_epoch==owner.assignment_epoch
        evidence=ReleaseEvidence(PermitIdentity(**{k:(str(__import__('uuid').UUID(bytes=bytes(getattr(decision.identity,k).uuid)))
            if hasattr(getattr(decision.identity,k),'uuid') else getattr(decision.identity,k))
            for k in decision.identity.get_fields_and_field_types()}),
            (str(__import__('uuid').UUID(bytes=bytes(decision.identity.permit_id.uuid))),),child_terminal='STATUS_CANCELED')
        release=await consumer.submit(Event('TRAFFIC_RELEASE',{'evidence':asdict(evidence)}))
        assert release['reason']=='RELEASE_THRESHOLDS_UNVERIFIED'
        assert not observer.gate.send(lambda: (_ for _ in ()).throw(AssertionError('Nonzero gate opened')))
        await asyncio.sleep(.5)
        # One immutable sample boundary for validation, raw archive and summary.
        # ROS callbacks otherwise keep appending while the report is written.
        with sample_lock:
            native_states = deepcopy(native_states)
            positions = deepcopy(positions)
        snapshot=json.loads(store.connection.execute('SELECT snapshot FROM traffic_state').fetchone()[0])
        assert snapshot['state']['claims'] and all(v['state']=='BLOCKED' for v in snapshot['state']['claims'].values())
        assert not (args.output/'unsafe-contact').exists()
        assert all(s['target_linear']==s['target_angular']==0 and
                   all(j is None or j==[0.] for j in s['joint_commands'])
                   for states in native_states.values() for s in states)
        spans={r.id:max(math.hypot(x-positions[r.id][0][0],y-positions[r.id][0][1])
                       for x,y in positions[r.id]) for r in cfg.robots}
        assert all(v<.001 for v in spans.values())
        library=Path('/b6b7-native/libc5-authorized-zero-drive.so')
        mapped=[]
        for process in Path('/proc').iterdir():
            if not process.name.isdigit():continue
            try:
                if str(library) in (process/'maps').read_text():mapped.append(process.name)
            except (OSError,PermissionError):pass
        assert len(mapped)==1
        (args.output/'child-observations.json').write_text(json.dumps(child_messages,indent=2)+'\n')
        with gzip.open(args.output/'native-samples.jsonl.gz','wt') as stream:
            for robot,samples in native_states.items():
                for sample in samples:stream.write(json.dumps(dict(robot=robot,**sample))+'\n')
        report=dict(result='PASS_PRODUCT_CHILD_METADATA_ONLY',selected_robot=selected.id,
            parent_execute_uuid=owner.goal_uuid,events=observer.events,
            decisions=[message_to_ordereddict(d) for d in observer.decisions],
            parent_result=message_to_ordereddict(result),release=release,traffic_snapshot=snapshot,
            outbox=[dict(row) for row in store.connection.execute('SELECT * FROM outbox_events')],
            native_samples={k:len(v) for k,v in native_states.items()},max_stationary_displacement_m=spans,
            native_library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),native_mapped_pids=mapped,
            moving_safety_acceptance=False,movement_authorized=False,physical_stop='UNKNOWN',ownership_release=False)
        (args.output/'identity-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:
        stopping.set();await worker
        for n in nodes:n._stopping.set()
        await asyncio.to_thread(pool.shutdown,timeout_sec=5.)
        await consumer.close();store.close()
        with sqlite3.connect(args.database) as source, sqlite3.connect(args.output/'fleet.sqlite3') as target:
            source.backup(target)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();args.profile=args.profile.resolve();args.output=args.output.resolve()
    args.output.mkdir(parents=True,exist_ok=False)
    args.database=Path('/tmp')/('c5-t2-'+str(uuid4())+'.sqlite3')
    cfg=load_config(args.profile);children=[];nodes=[]
    def launch(name,command):
        with (args.output/(name+'.log')).open('w') as log:
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        children.append((name,child));return child
    pool=None;thread=None
    try:
        launch('simulation',[sys.executable,str(Path(__file__).with_name('world.py')),str(args.profile),str(args.output/'generated'),'routes'])
        launch('observer',[sys.executable,'docker/simulation-warehouse-grid/stage1_observer.py',str(args.profile),
                           str(args.output),'--database',str(args.database)])
        end=time.monotonic()+180
        while True:
            ready=args.output/'startup-readiness.json'
            if ((args.output/'reset-verified.json').exists() and ready.exists()
                    and json.loads(ready.read_text()).get('current_status')=='READY'): break
            if time.monotonic()>end or any(p.poll() is not None for _,p in children):
                raise RuntimeError('Independent reset / AMCL / Nav2 / TF prerequisite failed')
            time.sleep(.1)
        for robot in cfg.robots:
            launch('battery_'+robot.id,[sys.executable,'-c','from fleet_battery_simulator.node import main; main()',
                                       '--fleet-config',str(args.profile),'--robot-id',robot.id])
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        node=rclpy.create_node('t2_product_manager',parameter_overrides=[Parameter('use_sim_time',value=True)])
        pool=MultiThreadedExecutor(num_threads=12);pool.add_node(node)
        positions=defaultdict(list);states=defaultdict(list)
        sample_lock=threading.Lock()
        def position(robot,message):
            with sample_lock:positions[robot].append((message.pose.position.x,message.pose.position.y))
        def native_state(robot,message):
            with sample_lock:states[robot].append(json.loads(message.data))
        for robot in cfg.robots:
            node.create_subscription(PoseStamped,robot.namespace+'/physical_pose',
                lambda m,r=robot.id: position(r,m),qos_profile_sensor_data)
            node.create_subscription(String,robot.namespace+'/native_actuator',
                lambda m,r=robot.id: native_state(r,m),10)
        thread=threading.Thread(target=pool.spin,daemon=True);thread.start()
        asyncio.run(case(args,cfg,node,pool,nodes,positions,states,sample_lock))
    finally:
        for n in nodes:n._stopping.set()
        if pool:
            pool.shutdown(timeout_sec=5.);thread.join(timeout=5.)
            for n in nodes:n.destroy_node()
            node.destroy_node();rclpy.try_shutdown()
        exits={}
        for name,child in reversed(children):
            if child.poll() is None:child.send_signal(signal.SIGTERM if name=='simulation' else signal.SIGINT)
            try:child.wait(timeout=50 if name=='simulation' else 10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
            exits[name]=child.returncode
        (args.output/'shutdown.json').write_text(json.dumps(exits,indent=2)+'\n')
        if any(exits.values()):raise RuntimeError('Unclean fixture shutdown: '+str(exits))


if __name__=='__main__':main()
