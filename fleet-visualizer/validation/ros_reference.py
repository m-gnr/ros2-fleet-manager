"""Collect independent root-TF measurements inside the existing test container."""
import json
import math
import sys

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener

base_frames = sys.argv[1:]
rclpy.init(args=[])
node = Node("visualizer_validation_reference", enable_rosout=False, start_parameter_services=False)
for publisher in list(node.publishers):
    node.destroy_publisher(publisher)
buffer = Buffer()
listener = TransformListener(buffer, node)
last_stamps = dict.fromkeys(base_frames, 0)


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
