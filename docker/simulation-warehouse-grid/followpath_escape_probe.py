"""Exercise and record a real Nav2 no-progress abort in a fresh C5 demo."""
import argparse
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen
from uuid import uuid4

from action_msgs.msg import GoalStatusArray
from geometry_msgs.msg import PoseStamped
from nav2_msgs.msg import SpeedLimit
from nav_msgs.msg import Path as RosPath
from rcl_interfaces.msg import Log
import rclpy
from rclpy.logging import LoggingSeverity
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict

from fleet_config import load_config


def xy(pose):
    return [pose.position.x, pose.position.y]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--api-port", required=True, type=int)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--robot", required=True)
    parser.add_argument("--pickup", required=True)
    parser.add_argument("--dropoff", required=True)
    args = parser.parse_args()
    config = load_config(args.profile)
    robot = next(r for r in config.robots if r.id == args.robot)

    def api(path, data=None):
        req = Request(f"http://127.0.0.1:{args.api_port}/api/{path}", data=data, headers={
            "Origin": args.origin, "Content-Type": "application/json",
        })
        with urlopen(req, timeout=7) as reply:
            return reply.status, json.load(reply)

    _, catalog = api("task-catalog")
    _, tasks = api("tasks")
    if not catalog["enabled"] or tasks["task_counts"]["total"]:
        raise RuntimeError("The probe requires a ready, empty demo")

    rclpy.init()
    node = rclpy.create_node("followpath_escape_probe")
    speed = node.create_publisher(SpeedLimit, robot.namespace + "/speed_limit", 10)
    log = args.output.open("x", buffering=1)
    seen = set()
    injected = False
    stall_seen = False

    def emit(event, **fields):
        log.write(json.dumps(dict(event=event, monotonic=time.monotonic(), **fields)) + "\n")

    def limit(value):
        speed.publish(SpeedLimit(speed_limit=value, percentage=False))

    def action_status(action, msg):
        for row in msg.status_list:
            goal_id = bytes(row.goal_info.goal_id.uuid).hex()
            key = (action, goal_id, row.status)
            if key in seen:
                continue
            seen.add(key)
            emit("action", action=action, goal_id=goal_id, status=row.status,
                 stamp=message_to_ordereddict(row.goal_info.stamp))

    def controller_log(msg):
        nonlocal stall_seen
        if (injected and not stall_seen and msg.name == f"{robot.namespace.strip('/')}.controller_server"
                and msg.level >= LoggingSeverity.ERROR
                and msg.msg in {"Failed to make progress", "Controller patience exceeded"}):
            limit(0.0)
            stall_seen = True
            emit("speed_restored", controller_error=msg.msg, stamp=message_to_ordereddict(msg.stamp))

    status_qos = QoSProfile(depth=20, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    for action in ("follow_path", "navigate_to_pose", "execute_task"):
        node.create_subscription(GoalStatusArray, f"{robot.namespace}/{action}/_action/status",
                                 lambda msg, name=action: action_status(name, msg), status_qos)
    node.create_subscription(Log, "/rosout", controller_log, status_qos)
    node.create_subscription(
        RosPath, robot.namespace + "/received_global_plan",
        lambda msg: emit("controller_plan", stamp=message_to_ordereddict(msg.header.stamp),
                         first=xy(msg.poses[0].pose), last=xy(msg.poses[-1].pose),
                         poses=len(msg.poses)) if msg.poses else None, 10)

    last_sample = 0.0

    def physical(msg):
        nonlocal last_sample
        now = time.monotonic()
        if now - last_sample >= 0.1:
            last_sample = now
            emit("gazebo_pose", stamp=message_to_ordereddict(msg.header.stamp), xy=xy(msg.pose))

    node.create_subscription(PoseStamped, robot.namespace + "/physical_pose", physical, qos_profile_sensor_data)
    try:
        deadline = time.monotonic() + 8
        while not speed.get_subscription_count() or not last_sample:
            if time.monotonic() > deadline:
                raise TimeoutError("Controller speed limit or Gazebo pose unavailable")
            rclpy.spin_once(node, timeout_sec=0.1)
        injected = True
        limit(0.001)
        emit("speed_limited", robot=robot.id, speed_m_s=0.001)
        request = dict(request_id=str(uuid4()), source_session_id=catalog["source_session_id"],
                       profile_digest=catalog["profile_digest"], pickup_id=args.pickup,
                       dropoff_id=args.dropoff, priority="HIGH")
        status, response = api("tasks", json.dumps(request).encode())
        emit("task_submitted", http=status, request=request, response=response)
        task_id = "web-" + request["request_id"]
        deadline = time.monotonic() + 210
        next_poll = time.monotonic() + 1
        last_task = None
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if time.monotonic() < next_poll:
                continue
            next_poll = time.monotonic() + 1
            _, snapshot = api("tasks")
            task = next((row for row in snapshot["tasks"] if row["task_id"] == task_id), None)
            if task and task != last_task:
                emit("task", row=task)
                last_task = task
            if task and task["status"] in {"COMPLETED", "FAILED"}:
                emit("terminal", status=task["status"], stall_seen=stall_seen)
                return 0 if task["status"] == "COMPLETED" and stall_seen else 1
        emit("timeout", stall_seen=stall_seen)
        return 1
    finally:
        limit(0.0)
        node.destroy_node()
        rclpy.shutdown()
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())
