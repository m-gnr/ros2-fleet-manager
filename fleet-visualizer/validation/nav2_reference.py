"""Test-only read-side observation of the existing C4.5 Nav2 graph."""
import json
import sys
from time import monotonic

import rclpy
from action_msgs.msg import GoalStatusArray
from nav_msgs.msg import Path
from rclpy.qos import QoSProfile, DurabilityPolicy

rclpy.init()
node = rclpy.create_node("viz4_discovery", enable_rosout=False, start_parameter_services=False)
for publisher in list(node.publishers):
    node.destroy_publisher(publisher)
states = {}
started = monotonic()

def emit(topic, **data):
    print(json.dumps(dict(t=round(monotonic()-started, 4), topic=topic, **data)), flush=True)

def path_callback(topic):
    def callback(msg):
        stamp = msg.header.stamp
        frames = {p.header.frame_id for p in msg.poses}
        stamps = {p.header.stamp.sec * 10**9 + p.header.stamp.nanosec for p in msg.poses}
        points = [[p.pose.position.x, p.pose.position.y] for p in msg.poses[:1] + msg.poses[-1:]]
        emit(topic, frame=msg.header.frame_id, stamp=stamp.sec * 10**9 + stamp.nanosec, pose_frames=sorted(frames),
             pose_stamp_range=[min(stamps), max(stamps)] if stamps else [], count=len(msg.poses), endpoints=points,
             points=[[p.pose.position.x, p.pose.position.y] for p in msg.poses] if topic.endswith("/plan") else None)
    return callback

def status_callback(topic):
    def callback(msg):
        current = {bytes(row.goal_info.goal_id.uuid).hex(): row.status for row in msg.status_list}
        if states.get(topic) != current:
            states[topic] = current
            emit(topic, goals=current)
    return callback

for ns in ('/robot_1', '/robot_2'):
    for suffix in ('plan','received_global_plan','transformed_global_plan','local_plan','plan_smoothed'):
        topic = ns+'/'+suffix
        node.create_subscription(Path, topic, path_callback(topic), 5)
    for suffix in ('navigate_to_pose','compute_path_to_pose','follow_path','execute_task'):
        topic = ns+'/'+suffix+'/_action/status'
        node.create_subscription(GoalStatusArray, topic, status_callback(topic),
                                 QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
while rclpy.ok() and monotonic() - started < int(sys.argv[1]):
    rclpy.spin_once(node,timeout_sec=0.1)
node.destroy_node()
rclpy.shutdown()
