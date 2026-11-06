"""Collect independent root-TF measurements inside the existing test container."""
import argparse
import json
import math
import sys

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformException, TransformListener

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("base_frames", nargs="+")
parser.add_argument("--namespace", help="Observe one robot directly, without the combined TF relay")
parser.add_argument("--edges", action="store_true", help="Log raw dynamic TF edges to stderr")
args = parser.parse_args()
base_frames = args.base_frames
rclpy.init(args=[])
tf_remaps = []
if args.namespace:
    tf_remaps = ["--ros-args", "-r", f"/tf:={args.namespace}/tf",
                 "-r", f"/tf_static:={args.namespace}/tf_static"]
node = Node("visualizer_validation_reference", cli_args=tf_remaps, namespace=args.namespace or "/",
            enable_rosout=False, start_parameter_services=False)
for publisher in list(node.publishers):
    node.destroy_publisher(publisher)
buffer = Buffer()
listener = TransformListener(buffer, node)
last_stamps = dict.fromkeys(base_frames, 0)


def record_edges(message):
    for transform in message.transforms:
        header = transform.header
        position, q = transform.transform.translation, transform.transform.rotation
        print(json.dumps({
            "parent": header.frame_id, "child": transform.child_frame_id,
            "stamp_ns": header.stamp.sec * 10**9 + header.stamp.nanosec,
            "x": position.x, "y": position.y,
            "yaw": math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)),
        }), file=sys.stderr, flush=True)


if args.edges:
    node.create_subscription(TFMessage, "/tf", record_edges, 50)


def sample_frame(base_frame):
    try:
        transform = buffer.lookup_transform("map", base_frame, Time())
    except TransformException:
        return
    header = transform.header
    stamp = header.stamp.sec * 10**9 + header.stamp.nanosec
    if stamp <= last_stamps[base_frame]:
        return
    last_stamps[base_frame] = stamp
    position, q = transform.transform.translation, transform.transform.rotation
    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
    print(json.dumps(dict(stamp_ns=str(stamp), frame_id=header.frame_id,
                          base_frame=transform.child_frame_id, x=position.x, y=position.y, yaw=yaw)),
          flush=True)


def sample():
    for base_frame in base_frames:
        sample_frame(base_frame)


node.create_timer(0.01, sample)
try:
    rclpy.spin(node)
except (KeyboardInterrupt, ExternalShutdownException):
    pass
finally:
    listener.unregister()
    node.destroy_node()
    rclpy.try_shutdown()
