"""Read-only ROS/SQLite evidence and physical-reset gate for C5 stage 1.1."""
import argparse
from datetime import datetime, timezone
import json
from math import atan2, hypot
from pathlib import Path
import signal
import sqlite3
import time

from action_msgs.msg import GoalStatusArray
from fleet_interfaces.action import ExecuteTask
from fleet_interfaces.msg import BatteryState, RobotStatus
from geometry_msgs.msg import PoseStamped
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
import rclpy
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from ros_gz_interfaces.msg import Contacts
from rosidl_runtime_py.convert import message_to_ordereddict

from fleet_config import load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--database', type=Path, required=True)
    args = parser.parse_args()
    cfg = load_config(args.profile)
    args.output.mkdir(parents=True, exist_ok=True)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('stage1_independent_observer', parameter_overrides=[Parameter('use_sim_time', value=True)])
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    physical, velocity, lifecycle, seen, pending, throttles = {}, {}, {}, set(), [], {}
    handles = []
    stream = (args.output / 'ros.jsonl').open('w')
    def emit(kind, **data):
        row = dict(utc=datetime.now(timezone.utc).isoformat(), monotonic=time.monotonic(),
                   sim_ns=node.get_clock().now().nanoseconds, kind=kind, **data)
        stream.write(json.dumps(row, allow_nan=False) + '\n')
        stream.flush()
    def record(kind, robot, msg, interval=0):
        key = kind, robot
        now = time.monotonic()
        if now - throttles.get(key, 0) >= interval:
            throttles[key] = now
            emit(kind, robot=robot, message=message_to_ordereddict(msg))
    qos = QoSProfile(depth=20, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    for robot in cfg.robots:
        rid, ns = robot.id, robot.namespace
        def pose(msg, rid=rid):
            physical[rid] = msg
            record('PHYSICAL_POSE', rid, msg, .1)
        def odom(msg, rid=rid):
            velocity[rid] = msg
            record('ODOMETRY', rid, msg, .2)
        def contacts(msg, rid=rid):
            for contact in msg.contacts:
                names = [contact.collision1.name, contact.collision2.name]
                if any(part.startswith(('rack_', 'wall_')) or part in {r.id for r in cfg.robots} - {rid}
                       for name in names for part in name.split('::')):
                    emit('UNSAFE_CONTACT', robot=rid, names=names)
                    (args.output/'unsafe-contact').write_text(json.dumps(names))
        node.create_subscription(PoseStamped, ns+'/physical_pose', pose, qos_profile_sensor_data)
        node.create_subscription(Odometry, ns+'/odom', odom, qos_profile_sensor_data)
        node.create_subscription(ExecuteTask.Impl.FeedbackMessage, ns+'/execute_task/_action/feedback', lambda m,r=rid: record('RAW_EXECUTE_FEEDBACK',r,m), 50)
        node.create_subscription(RobotStatus, ns+'/robot_status', lambda m,r=rid: record('ROBOT_STATUS',r,m), 30)
        node.create_subscription(BatteryState, ns+'/battery_state', lambda m,r=rid: record('BATTERY',r,m), 30)
        for link in ('base_link', 'left_wheel', 'right_wheel', 'caster'):
            node.create_subscription(Contacts, ns+'/contact_'+link, contacts, 10)
        for name, action in [('execute_task', ExecuteTask), ('navigate_to_pose', NavigateToPose)]:
            service = action.Impl.GetResultService
            client = node.create_client(service, ns+'/'+name+'/_action/get_result')
            handles.append(client)
            def status(msg, rid=rid, name=name, service=service, client=client):
                for row in msg.status_list:
                    uuid = bytes(row.goal_info.goal_id.uuid).hex()
                    key = rid, name, uuid, row.status
                    if key in seen:
                        continue
                    seen.add(key)
                    emit('ACTION_STATUS', robot=rid, action=name, uuid=uuid, status=row.status,
                         goal_stamp=message_to_ordereddict(row.goal_info.stamp))
                    if row.status in (4,5,6):
                        req = service.Request(goal_id=row.goal_info.goal_id)
                        pending.append((rid, name, uuid, client.call_async(req)))
            node.create_subscription(GoalStatusArray, ns+'/'+name+'/_action/status', status, qos)
        client = node.create_client(GetState, ns+'/bt_navigator/get_state')
        lifecycle[rid] = client
        handles.append(client)
    reset_since, deadline, last_db, last_sample = None, time.monotonic()+150, None, 0
    active = set()
    lifecycle_requests = {}
    try:
        while not stopping:
            rclpy.spin_once(node, timeout_sec=.01)
            for rid,name,uuid,future in list(pending):
                if future.done():
                    emit('ACTION_RESULT', robot=rid, action=name, uuid=uuid,
                         message=message_to_ordereddict(future.result()))
                    pending.remove((rid,name,uuid,future))
            if not (args.output/'reset-verified.json').exists():
                for rid, client in lifecycle.items():
                    if rid not in active and rid not in lifecycle_requests and client.service_is_ready():
                        lifecycle_requests[rid] = client.call_async(GetState.Request())
                for rid, future in list(lifecycle_requests.items()):
                    if future.done():
                        if future.result().current_state.label == 'active':
                            active.add(rid)
                        del lifecycle_requests[rid]
                reset = len(active) == len(cfg.robots) and node.get_clock().now().nanoseconds > 0
                evidence = {}
                for robot in cfg.robots:
                    p, v = physical.get(robot.id), velocity.get(robot.id)
                    if p is None or v is None:
                        reset = False
                        continue
                    q = p.pose.orientation
                    yaw = atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
                    error = hypot(p.pose.position.x-robot.initial_pose.x, p.pose.position.y-robot.initial_pose.y)
                    speed = hypot(v.twist.twist.linear.x, v.twist.twist.linear.y)
                    angular = abs(v.twist.twist.angular.z)
                    age = node.get_clock().now().nanoseconds - (v.header.stamp.sec*10**9+v.header.stamp.nanosec)
                    yaw_error = abs(atan2(__import__('math').sin(yaw-robot.initial_pose.yaw),
                                         __import__('math').cos(yaw-robot.initial_pose.yaw)))
                    reset &= error <= .05 and yaw_error <= .05 and speed <= .01 and angular <= .01 and 0 <= age <= 500_000_000
                    evidence[robot.id] = dict(position_error_m=error,yaw_error_rad=yaw_error,speed_m_s=speed,
                                              angular_rad_s=angular,odom_age_ns=age,physical=message_to_ordereddict(p))
                if reset:
                    reset_since = reset_since or time.monotonic()
                    if time.monotonic()-reset_since >= 1:
                        emit('PHYSICAL_RESET_VERIFIED', robots=evidence)
                        (args.output/'reset-verified.json').write_text(json.dumps(evidence,indent=2))
                else:
                    reset_since = None
                if time.monotonic() > deadline:
                    raise TimeoutError('Independent physical reset / active Nav2 could not be verified')
            if time.monotonic()-last_sample >= .2:
                last_sample = time.monotonic()
                db = args.database
                if db.exists():
                    with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as conn:
                        conn.row_factory = sqlite3.Row
                        if conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone()[0] == 0:
                            continue
                        conn.execute('BEGIN')
                        tables = {table:[dict(row) for row in conn.execute('SELECT * FROM '+table)]
                                  for table in ('tasks','outbox_events','reservations','task_review_holds')}
                    serialized = json.dumps(tables,sort_keys=True)
                    if serialized != last_db:
                        emit('SQLITE', tables=tables)
                        last_db = serialized
                snapshot = Path('/tmp/stage1/latest.json')
                if snapshot.exists():
                    emit('PRODUCT_SNAPSHOT', snapshot=json.loads(snapshot.read_text()))
    finally:
        stream.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
