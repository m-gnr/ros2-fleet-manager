"""Real FM/SQLite/Outbox process, with optional B6B.7 zero-only transport."""
import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import signal
import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.signals import SignalHandlerOptions
from fleet_config import load_config
from fleet_config.native_zero import load_key
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.event_loop import FleetEventLoop,Event,OutboxDispatcher
from backend.fleet_manager.persistence.store import SQLiteStore
from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
from backend.fleet_manager.adapters.native_zero import NativeZeroROSBridge,traffic_start_ready
from backend.fleet_manager.domain import Pose2D
from backend.fleet_manager.domain.traffic import Box,PermitIdentity,ReleaseEvidence
import yaml


async def run(args,node):
    cfg=load_config(args.profile);core,robots=build_fleet_manager_from_config(args.profile)
    store=SQLiteStore(args.database)
    # An existing DB raises ScenarioResetRequired, including on deliberate restart.
    consumer=FleetEventLoop(store,core)
    params=yaml.safe_load((args.output/'generated'/('nav2-'+robots[0]+'.yaml')).read_text())
    radius=params['local_costmap']['local_costmap']['ros__parameters']['robot_radius']
    consumer.enable_traffic_protocol_test(enclosing_radius=radius)
    consumer.enable_native_zero_test(keys={r:load_key('/run/c5-b6b7/'+r+'.json') for r in robots},ack_timeout=.5)
    stop=asyncio.Event();loop=asyncio.get_running_loop()
    for sig in (signal.SIGTERM,signal.SIGINT):loop.add_signal_handler(sig,stop.set)
    await consumer.start()
    try:
        mapping={r.id:r.namespace for r in cfg.robots}
        adapter=FleetROS2Adapter(node,consumer,loop,robots,robot_namespaces=mapping,traffic_protocol_test=True)
        native=NativeZeroROSBridge(node,consumer,loop,mapping)
        deadline=time.monotonic()+15.
        while not traffic_start_ready(consumer.core,time.monotonic()):
            if time.monotonic()>=deadline:raise TimeoutError('Fresh actual RobotStatus required before traffic configure')
            if stop.is_set():return
            await asyncio.sleep(.02)
        initial=consumer.core
        (args.output/'traffic-start-proof.json').write_text(json.dumps(dict(
            receipt_monotonic=time.monotonic(),robots=[dict(robot_id=r.robot_id,session_id=r.session_id,
                status_received_at=r.last_status_received_at,initial_status_verified=r.initial_status_verified,
                session_blocked=r.session_blocked) for r in initial.tracker.list_robots()]),indent=2)+'\n')
        bounds=cfg.warehouse.bounds
        await consumer.submit(Event('TRAFFIC_CONFIGURE',dict(revision='t3a-map',frame=cfg.warehouse.frame_id,
            geometry_revision='t3a-geometry',managed=[asdict(Box(bounds.x_min,bounds.y_min,bounds.x_max,bounds.y_max))])))
        dispatch=OutboxDispatcher(consumer,adapter.outbox_sender,clock=time.monotonic,retry_delay=1.)
        (args.output/'manager-info.json').write_text(json.dumps(dict(fm_session=consumer._traffic_protocol_session,
            database=str(args.database),native_keys_in_fm_only=True),indent=2)+'\n')
        submitted=False;released=False
        while not stop.is_set():
            trigger=args.output/'tasks.json'
            if trigger.exists() and not submitted:
                for task in json.loads(trigger.read_text()):
                    await consumer.submit(Event('SUBMIT_TASK',dict(task_id=task['task_id'],
                        pickup_pose=Pose2D(**task['pickup']),dropoff_pose=Pose2D(**task['dropoff']),
                        priority=3,created_at=time.monotonic())))
                submitted=True
            release=args.output/'release-request.json'
            if release.exists() and not released:
                request=json.loads(release.read_text())
                row=store.connection.execute('SELECT decision FROM traffic_decisions WHERE event_id=?',
                    ('permit:'+request['request_id'],)).fetchone()
                identity=PermitIdentity(**json.loads(row[0])['identity'])
                evidence=ReleaseEvidence(identity,(identity.permit_id,))
                result=await consumer.submit(Event('TRAFFIC_RELEASE',dict(evidence=asdict(evidence))))
                response=args.output/'release-response.tmp'
                response.write_text(json.dumps(result,indent=2)+'\n')
                response.replace(args.output/'release-response.json')
                released=True
            await consumer.submit(Event('TICK',dict(current_time=time.monotonic())))
            await dispatch.send_one()
            await asyncio.sleep(.03)
        snapshot=consumer.core
        for robot,bridge in adapter.action_bridges.items():
            record=snapshot.tracker.get_robot(robot)
            if record and record.session_blocked:continue
            for handle in list(bridge._active_goal_handles.values()):
                if not handle.get_result_async().done():handle.cancel_goal_async()
        await asyncio.sleep(.6)
    finally:
        await consumer.close();store.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('database',type=Path);args=parser.parse_args()
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node=rclpy.create_node('t3a_real_fm',parameter_overrides=[Parameter('use_sim_time',value=True)])
    pool=MultiThreadedExecutor(num_threads=6);pool.add_node(node)
    thread=threading.Thread(target=pool.spin,daemon=True);thread.start()
    try:asyncio.run(run(args,node))
    finally:
        pool.shutdown(timeout_sec=5.);thread.join(timeout=5.);node.destroy_node();rclpy.try_shutdown()


if __name__=='__main__':main()
