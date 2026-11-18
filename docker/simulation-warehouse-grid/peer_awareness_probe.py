"""Read-only evidence for peer costmap experiments; never sends movement goals.

Uses the existing verified TF/observed-plan reader. The observed plan does not
carry a child UUID binding, so neither it nor this report authorizes traffic.
"""
import argparse
import base64
from dataclasses import asdict
import json
import math
from pathlib import Path
import signal
import sys
import time
import zlib

import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import String

from fleet_config import load_config

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "fleet-visualizer/bridge"))
from ros_reader import RosReader
from telemetry import Telemetry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--duration", type=float, required=True)
    args = parser.parse_args()
    cfg = load_config(args.profile)
    context = Context()
    rclpy.init(context=context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stream = args.output.open("w")
    previous = {}
    stopping = False

    def emit(kind, **values):
        stream.write(json.dumps(dict(kind=kind, monotonic=time.monotonic(),
                                     utc=time.time(), **values), allow_nan=False) + "\n")

    def snapshot(robot, state):
        # Record advancing poses/plans and validity changes, bounded to 5 Hz.
        value = asdict(state)
        if previous.get(robot) != value:
            previous[robot] = value
            emit("OBSERVED", robot=robot, **value)

    node = RosReader([(r.namespace, Telemetry(r.id, cfg.warehouse.frame_id, "tf",
                       cfg.fleet.perception_safety.odometry_freshness_sec)) for r in cfg.robots],
                     5, snapshot, context=context,
                     plan_topics={r.id: r.namespace + "/plan" for r in cfg.robots})
    for robot in cfg.robots:
        def physical(message, rid=robot.id):
            p, q = message.pose.position, message.pose.orientation
            emit("PHYSICAL", robot=rid,
                 stamp_ns=message.header.stamp.sec*10**9+message.header.stamp.nanosec,
                 frame=message.header.frame_id, x=p.x, y=p.y,
                 yaw=math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z)))
        node.create_subscription(PoseStamped, robot.namespace + "/physical_pose", physical,
                                 qos_profile_sensor_data)
        for layer in ("local_costmap", "global_costmap"):
            def health(message, rid=robot.id, layer=layer):
                emit("PEER_LAYER", robot=rid, layer=layer, report=json.loads(message.data))
            node.create_subscription(String, robot.namespace + "/" + layer + "/peer_observations",
                                     health, 1)
            # Preserve the grid, not an inferred mark, for independent replay.
            def grid(message, rid=robot.id, layer=layer):
                emit("GRID", robot=rid, layer=layer, frame=message.header.frame_id,
                     stamp_ns=message.header.stamp.sec*10**9+message.header.stamp.nanosec,
                     resolution=message.info.resolution, width=message.info.width,
                     height=message.info.height,
                     origin=[message.info.origin.position.x, message.info.origin.position.y],
                     orientation=[message.info.origin.orientation.x, message.info.origin.orientation.y,
                                  message.info.origin.orientation.z, message.info.origin.orientation.w],
                     data_int8_zlib=base64.b64encode(zlib.compress(message.data.tobytes(), 1)).decode())
            node.create_subscription(OccupancyGrid, robot.namespace + "/" + layer + "/costmap", grid, 1)
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(node)

    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    deadline = time.monotonic() + args.duration
    try:
        while not stopping and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.1)
            stream.flush()
    finally:
        emit("END", stopped=stopping)
        stream.close()
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown(context=context)


if __name__ == "__main__":
    main()
