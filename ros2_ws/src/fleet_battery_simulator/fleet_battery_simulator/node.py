"""ROS 2 adapter for the per-robot battery consumption core."""

import argparse
from math import hypot
from uuid import uuid4

import rclpy
from fleet_interfaces.msg import BatteryState
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rosgraph_msgs.msg import Clock
from unique_identifier_msgs.msg import UUID

from fleet_config.loader import load_config
from fleet_config.models import BatteryModel, Robot

from .consumption import BatteryConsumption, NANOSECONDS_PER_SECOND, OdometrySample

PUBLISH_PERIOD_NS = 200_000_000
CLOCK_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)


def stamp_ns(stamp):
    if stamp.sec < 0 or not 0 <= stamp.nanosec < NANOSECONDS_PER_SECOND:
        return -1
    return stamp.sec * NANOSECONDS_PER_SECOND + stamp.nanosec


class BatterySimulatorNode(Node):
    def __init__(self, robot: Robot, model: BatteryModel):
        super().__init__(
            "battery_simulator",
            namespace=robot.namespace,
            parameter_overrides=[Parameter("use_sim_time", value=True)],
            use_global_arguments=False,
        )
        self._robot_id = robot.id
        self._session_id = UUID(uuid=list(uuid4().bytes))
        self._battery = BatteryConsumption(model)
        self._last_published_ns = None
        self._publisher = self.create_publisher(BatteryState, "battery_state", 10)
        self.create_subscription(Clock, "/clock", self._on_clock, CLOCK_QOS)
        self.create_subscription(Odometry, "odom", self._on_odometry, qos_profile_sensor_data)

    @classmethod
    def from_config(cls, fleet_config_path, robot_id):
        config = load_config(fleet_config_path)
        for robot in config.robots:
            if robot.id == robot_id:
                return cls(robot, config.fleet.battery_models[robot.battery_model])
        raise ValueError(f"{fleet_config_path}: unknown robot ID {robot_id!r}")

    def _on_odometry(self, msg):
        position = msg.pose.pose.position
        linear, angular = msg.twist.twist.linear, msg.twist.twist.angular
        self._battery.observe_odometry(OdometrySample(
            stamp_ns(msg.header.stamp),
            (msg.header.frame_id, msg.child_frame_id),
            (position.x, position.y, position.z),
            hypot(linear.x, linear.y, linear.z),
            hypot(angular.x, angular.y, angular.z),
        ))

    def _on_clock(self, msg):
        now_ns = stamp_ns(msg.clock)
        previous_clock_ns = self._battery.clock_ns
        if not self._battery.update_clock(now_ns):
            return
        if (self._last_published_ns is not None and now_ns >= previous_clock_ns
                and now_ns - self._last_published_ns < PUBLISH_PERIOD_NS):
            return

        self._publisher.publish(BatteryState(
            robot_id=self._robot_id,
            publisher_session_id=self._session_id,
            battery_energy_wh=self._battery.remaining_wh,
            battery_soc_percent=self._battery.soc_percent,
            battery_capacity_wh=self._battery.capacity_wh,
            is_charging=False,
            battery_stamp=msg.clock,
        ))
        self._last_published_ns = now_ns


def main():
    parser = argparse.ArgumentParser(description="Simulate battery consumption for one fleet robot")
    parser.add_argument("--fleet-config", required=True)
    parser.add_argument("--robot-id", required=True)
    args = parser.parse_args()

    rclpy.init(args=[], signal_handler_options=SignalHandlerOptions.NO)
    node = None
    try:
        node = BatterySimulatorNode.from_config(args.fleet_config, args.robot_id)
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Battery Simulator configuration error: {exc}\n")
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
