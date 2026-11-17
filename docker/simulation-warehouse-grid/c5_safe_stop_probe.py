#!/usr/bin/env python3
"""Cancel active Nav2 goals and prove all configured robots are stationary."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from action_msgs.msg import GoalStatusArray
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


ACTIVE = {1, 2, 3}  # accepted, executing, canceling
ZERO_TOLERANCE = 1e-3
POSE_TOLERANCE = 1e-4


class Probe:
    def __init__(self, robot_ids: list[str]):
        self.node = rclpy.create_node("c5_safe_stop_probe")
        self.robots = robot_ids
        self.cmd_samples = {robot: [] for robot in robot_ids}
        self.odom_samples = {robot: [] for robot in robot_ids}
        self.status_seen = {robot: False for robot in robot_ids}
        self.statuses = {robot: set() for robot in robot_ids}
        self.subscriptions = []
        self.cancel_clients = {}
        for robot in robot_ids:
            namespace = f"/{robot}"
            self.subscriptions.extend([
                self.node.create_subscription(
                    Twist, f"{namespace}/cmd_vel",
                    lambda msg, name=robot: self.cmd_samples[name].append(
                        (time.monotonic(), msg.linear.x, msg.linear.y, msg.angular.z)),
                    qos_profile_sensor_data),
                self.node.create_subscription(
                    Odometry, f"{namespace}/odom",
                    lambda msg, name=robot: self.odom_samples[name].append(
                        (time.monotonic(), msg.pose.pose.position.x,
                         msg.pose.pose.position.y, self.yaw(msg),
                         msg.twist.twist.linear.x, msg.twist.twist.linear.y,
                         msg.twist.twist.angular.z)), qos_profile_sensor_data),
                self.node.create_subscription(
                    GoalStatusArray, f"{namespace}/navigate_to_pose/_action/status",
                    lambda msg, name=robot: self.on_status(name, msg), qos_profile_sensor_data),
            ])
            self.cancel_clients[robot] = self.node.create_client(
                CancelGoal, f"{namespace}/navigate_to_pose/_action/cancel_goal")

    @staticmethod
    def yaw(msg: Odometry) -> float:
        q = msg.pose.pose.orientation
        return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))

    def on_status(self, robot: str, message: GoalStatusArray) -> None:
        self.status_seen[robot] = True
        self.statuses[robot] = {item.status for item in message.status_list}

    def spin(self, seconds: float = 0.05) -> None:
        rclpy.spin_once(self.node, timeout_sec=seconds)

    def wait(self, predicate, timeout: float, description: str) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.spin()
            if predicate():
                return
        raise RuntimeError(f"timeout: {description}")

    def cancel_active(self, timeout: float) -> list[str]:
        canceled = []
        for robot in self.robots:
            client = self.cancel_clients[robot]
            if not client.wait_for_service(timeout_sec=min(timeout, 5)):
                raise RuntimeError(f"Nav2 cancel service unavailable for {robot}")
            future = client.call_async(CancelGoal.Request())  # all-zero goal_info means cancel all
            deadline = time.monotonic() + timeout
            while not future.done() and time.monotonic() < deadline:
                self.spin()
            if not future.done():
                raise RuntimeError(f"Nav2 cancel response timeout for {robot}")
            response = future.result()
            if response.return_code != CancelGoal.Response.ERROR_NONE:
                raise RuntimeError(f"Nav2 cancel request rejected for {robot}: {response.return_code}")
            if response.goals_canceling:
                canceled.append(robot)
        if canceled:
            self.wait(lambda: all(self.status_seen[name] and not (self.statuses[name] & ACTIVE)
                                  for name in canceled), timeout,
                      "Nav2 goal terminal state after cancel")
        return canceled

    def verify_stationary(self, duration: float, timeout: float) -> dict:
        start = time.monotonic()
        self.wait(lambda: all(len(self.odom_samples[name]) >= 5 for name in self.robots),
                  timeout, "odometry samples for every robot")
        while time.monotonic() - start < duration:
            self.spin()
        result = {}
        for robot in self.robots:
            cmd = self.cmd_samples[robot]
            odom = self.odom_samples[robot]
            if not odom:
                raise RuntimeError(f"missing motion telemetry for {robot}")
            first, last = odom[0], odom[-1]
            displacement = math.hypot(last[1] - first[1], last[2] - first[2])
            yaw_delta = abs(math.atan2(math.sin(last[3] - first[3]), math.cos(last[3] - first[3])))
            max_odom_speed = max(max(abs(vx), abs(vy), abs(wz)) for _, _, _, _, vx, vy, wz in odom)
            max_cmd_speed = max((max(abs(x), abs(y), abs(w)) for _, x, y, w in cmd), default=0.0)
            if (max_odom_speed > ZERO_TOLERANCE or max_cmd_speed > ZERO_TOLERANCE or
                    displacement > POSE_TOLERANCE or yaw_delta > POSE_TOLERANCE):
                raise RuntimeError(
                    f"robot {robot} not stationary: odom_speed={max_odom_speed:.6g}, "
                    f"cmd_speed={max_cmd_speed:.6g}, "
                    f"displacement={displacement:.6g}, yaw_delta={yaw_delta:.6g}")
            if self.status_seen[robot] and self.statuses[robot] & ACTIVE:
                raise RuntimeError(f"active Nav2 goal remains for {robot}")
            result[robot] = {
                "cmd_samples": len(cmd), "odom_samples": len(odom),
                "max_abs_command_velocity": max_cmd_speed,
                "max_abs_odometry_velocity": max_odom_speed,
                "odom_displacement_m": displacement,
                "odom_yaw_delta_rad": yaw_delta, "nav2_active_goals": 0,
            }
        return result

    def close(self) -> None:
        self.node.destroy_node()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot-ids", required=True, help="comma-separated configured robot IDs")
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    robots = [item for item in args.robot_ids.split(",") if item]
    if not robots or any("/" in item for item in robots):
        print("invalid robot IDs", file=sys.stderr)
        return 2
    rclpy.init()
    probe = Probe(robots)
    try:
        canceled = probe.cancel_active(args.timeout)
        stationary = probe.verify_stationary(args.duration, args.timeout)
        print(json.dumps({"result": "SAFE_STOP_CONFIRMED", "canceled_robots": canceled,
                          "robots": stationary}, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"result": "SAFE_STOP_UNCONFIRMED", "error": str(error)}), file=sys.stderr)
        return 1
    finally:
        probe.close()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
