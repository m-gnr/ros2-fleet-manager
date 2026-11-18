"""Real stationary FollowPath response vs committed fixture reservation.

The isolated consumer below has no ROS adapter or Outbox dispatcher. Its parent
assignment is a domain fixture, not a delivered ExecuteTask. Physical movement
is inhibited by the already-tested native zero-only drivers. This is component
provenance evidence, not end-to-end traffic authority or task completion.
"""
import argparse
import asyncio
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import threading
import time
from uuid import UUID, uuid4

import rclpy
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.serialization import serialize_message
from rclpy.time import Time
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path as ROSPath
from nav2_msgs.action import FollowPath
from tf2_ros import Buffer, TransformListener
from unique_identifier_msgs.msg import UUID as ROSUUID
import yaml

from fleet_config import load_config
from fleet_robot_executor.traffic import MovementGate, observe_follow_path_acceptance
from backend.fleet_manager.domain import FleetManagerCore, Pose2D, StationType
from backend.fleet_manager.domain.traffic import Box, PermitIdentity, ReleaseEvidence, sweep
from backend.fleet_manager.event_loop import FleetEventLoop, Event
from backend.fleet_manager.persistence.store import SQLiteStore
from backend.fleet_manager.persistence.traffic_protocol import digest


class FixtureRoutes:
    def get_path_distance(self, *_):
        return 0.  # Explicit zero-length domain fixture, never a product planner.


async def wait(future, seconds=5.):
    end = time.monotonic()+seconds
    while not future.done():
        if time.monotonic() >= end:raise TimeoutError("Actual FollowPath response unavailable")
        await asyncio.sleep(.01)
    return future.result()


async def case(node, tf, robot, cfg, output):
    endpoint = robot.namespace+"/follow_path"
    client = ActionClient(node, FollowPath, endpoint)
    if not client.wait_for_server(timeout_sec=8.):raise TimeoutError(endpoint)
    stamp = node.get_clock().now().nanoseconds-100_000_000
    transform = tf.lookup_transform(cfg.warehouse.frame_id, robot.id+"/base_link", Time(nanoseconds=stamp),
                                    timeout=Duration(seconds=0))
    # Both path poses coincide with the measured stationary position/orientation.
    pose = PoseStamped();pose.header.frame_id=cfg.warehouse.frame_id
    pose.header.stamp=node.get_clock().now().to_msg()
    pose.pose.position.x=transform.transform.translation.x
    pose.pose.position.y=transform.transform.translation.y
    pose.pose.orientation=deepcopy(transform.transform.rotation)
    route=ROSPath();route.header=deepcopy(pose.header);route.poses=[deepcopy(pose),deepcopy(pose)]
    raw=bytes(serialize_message(route));child=str(uuid4())
    params=yaml.safe_load((output.parent/"generated"/f"nav2-{robot.id}.yaml").read_text())
    radius=params['local_costmap']['local_costmap']['ros__parameters']['robot_radius']
    store=SQLiteStore(output/(robot.id+".sqlite3"))
    core=FleetManagerCore(FixtureRoutes(),Pose2D())
    core.register_robot(robot.id);core.register_station('fixture_safe',StationType.CHARGING,Pose2D())
    consumer=FleetEventLoop(store,core,clock=lambda:10.)
    consumer.enable_traffic_protocol_test(enclosing_radius=radius)
    await consumer.start()
    try:
        q=pose.pose.orientation
        session=str(uuid4());point=Pose2D(pose.pose.position.x,pose.pose.position.y,
            math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))
        await consumer.submit(Event('ROBOT_STATUS',dict(robot_id=robot.id,status_seq=1,current_epoch=0,
            current_task_id=None,state=1,current_phase=0,is_loaded=False,pose=point,battery_soc_percent=100.,
            battery_energy_wh=100.,timestamp_sec=10.,publisher_session_id=session)))
        await consumer.submit(Event('SUBMIT_TASK',dict(task_id='stationary-fixture-'+robot.id,
            pickup_pose=point,dropoff_pose=point,priority=2,created_at=1.)))
        await consumer.submit(Event('TICK',{'current_time':10.}))
        b=cfg.warehouse.bounds
        await consumer.submit(Event('TRAFFIC_CONFIGURE',dict(revision='zero-fixture-map',frame=cfg.warehouse.frame_id,
            geometry_revision='zero-fixture-geometry',managed=[asdict(Box(b.x_min,b.y_min,b.x_max,b.y_max))])))
        owner=consumer.core._active_tasks_by_robot[robot.id]
        boxes=[asdict(v) for v in sweep([(point.x,point.y),(point.x,point.y)],radius)]
        p=dict(request_id=str(uuid4()),robot_id=robot.id,task_id=owner.task_id,epoch=owner.assignment_epoch,
            execute_uuid=owner.goal_uuid,child_uuid=child,executor_session=session,movement_kind='PICKUP',station_id='',
            path_bytes=raw.hex(),path_hash=hashlib.sha256(raw).hexdigest(),points=[(point.x,point.y),(point.x,point.y)],
            geometry=boxes,geometry_digest=digest(boxes),map_revision='zero-fixture-map',
            geometry_revision='zero-fixture-geometry',frame=cfg.warehouse.frame_id)
        decision=await consumer.submit(Event('TRAFFIC_PROTOCOL_REQUEST',p,'permit:'+p['request_id']))
        assert not store.connection.in_transaction and decision['status']=='RESERVED'
        gate=MovementGate();gate.prepare(p,5.);assert gate.receive(dict(decision,committed=True))
        goal=FollowPath.Goal(path=deepcopy(route),controller_id='FollowPath',goal_checker_id='general_goal_checker')
        handle=await wait(client.send_goal_async(goal,goal_uuid=ROSUUID(uuid=list(UUID(child).bytes))))
        assert handle.accepted
        observed=observe_follow_path_acceptance(gate,handle,goal,expected_action_name=endpoint)
        assert observed and observed['actual_child_uuid']==child and observed['actual_path_hash']==p['path_hash']
        result=await wait(handle.get_result_async())
        assert gate.observe_child_terminal(str(UUID(bytes=bytes(handle.goal_id.uuid))),result.status)
        assert not gate.send(lambda: (_ for _ in ()).throw(AssertionError('Movement must remain inhibited')))
        evidence=ReleaseEvidence(PermitIdentity(**decision['identity']),(decision['identity']['permit_id'],),
                                 child_terminal='STATUS_'+str(result.status))
        released=await consumer.submit(Event('TRAFFIC_RELEASE',{'evidence':asdict(evidence)}))
        assert released['reason']=='RELEASE_THRESHOLDS_UNVERIFIED'
        altered=deepcopy(goal.path);altered.header.frame_id='changed'
        assert gate.observe_child_accepted(child,bytes(serialize_message(altered))) is None
        assert gate.observe_child_accepted(child,raw) is None
        record=dict(robot_id=robot.id,endpoint=endpoint,observation=observed,terminal_status=result.status,
            fixture_parent_execute_task_sent=False,outbox_dispatcher_started=False,release=released,
            changed_path_gate_state=gate.state,goal_path_sha256=p['path_hash'],
            path_bytes=raw.hex(),physical_stop='UNKNOWN',movement_authorized=False)
        (output/(robot.id+'.json')).write_text(json.dumps(record,indent=2)+'\n')
        return record
    finally:
        await consumer.close();store.close();client.destroy()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();cfg=load_config(args.profile)
    matrix=json.loads((args.output.parent/'native-matrix/summary.json').read_text())
    assert matrix['result']=='PASS_ZERO_ONLY' and not matrix['movement_authorized']
    args.output.mkdir(exist_ok=False)
    rclpy.init();node=rclpy.create_node('stationary_follow_path_binding',parameter_overrides=[Parameter('use_sim_time',value=True)])
    tf=Buffer();listener=TransformListener(tf,node)
    executor=MultiThreadedExecutor();executor.add_node(node)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    try:
        time.sleep(1.5)  # Bounded history for exact-time TF interpolation.
        async def run():
            return [await case(node,tf,r,cfg,args.output) for r in cfg.robots]
        rows=asyncio.run(run())
        (args.output/'summary.json').write_text(json.dumps(dict(result='PASS_METADATA_ONLY',robots=rows,
            limits='Real stationary FollowPath; fixture parent assignment, no ExecuteTask delivery, no motion/release authority'),indent=2)+'\n')
    finally:
        executor.shutdown(timeout_sec=5.);thread.join(timeout=5.);node.destroy_node();rclpy.try_shutdown()


if __name__=='__main__':main()
