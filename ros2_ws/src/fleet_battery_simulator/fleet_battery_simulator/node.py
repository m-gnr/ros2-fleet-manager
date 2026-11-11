"""ROS 2 adapter for the per-robot battery consumption core."""

import argparse
import signal
from math import hypot
from uuid import uuid4

import rclpy
from fleet_interfaces.msg import BatteryState, DockLease, RobotStatus
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rosgraph_msgs.msg import Clock
from ros_gz_interfaces.msg import Contacts
from unique_identifier_msgs.msg import UUID

from fleet_config.loader import load_config
from fleet_config.models import BatteryModel, Robot

from .consumption import BatteryConsumption, NANOSECONDS_PER_SECOND, OdometrySample
from .docking import DOCK_EVIDENCE_MAX_AGE_NS, DockGate, Ownership

PUBLISH_PERIOD_NS = 200_000_000
CLOCK_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)


def stamp_ns(stamp):
    if stamp.sec < 0 or not 0 <= stamp.nanosec < NANOSECONDS_PER_SECOND:
        return -1
    return stamp.sec * NANOSECONDS_PER_SECOND + stamp.nanosec


class BatterySimulatorNode(Node):
    def __init__(self, robot: Robot, model: BatteryModel, *, docks=()):
        super().__init__(
            "battery_simulator",
            namespace=robot.namespace,
            parameter_overrides=[Parameter("use_sim_time", value=True)],
            use_global_arguments=False,
        )
        self._robot_id = robot.id
        self._session_id = UUID(uuid=list(uuid4().bytes))
        self._battery = BatteryConsumption(model)
        self._dock = DockGate(robot.id, {dock.id: (dock.pose.x, dock.pose.y, dock.tolerance_radius) for dock in docks})
        self._charging_station = ""
        self._last_published_ns = None
        self._publisher = self.create_publisher(BatteryState, "battery_state", 10)
        self.create_subscription(Clock, "/clock", self._on_clock, CLOCK_QOS)
        self.create_subscription(Odometry, "odom", self._on_odometry, qos_profile_sensor_data)
        if docks:
            self.create_subscription(DockLease, "dock_lease", self._on_lease, 10)
            self.create_subscription(RobotStatus, "robot_status", self._on_status, 10)
            self.create_subscription(PoseStamped, "physical_pose", self._on_physical_pose, qos_profile_sensor_data)
            for dock in docks:
                self.create_subscription(
                    Contacts, f"/dock/{dock.id}/contacts",
                    lambda msg, station_id=dock.id: self._dock.observe_contact(
                        station_id, stamp_ns(msg.header.stamp),
                        ((c.collision1.name, c.collision2.name) for c in msg.contacts),
                    ), qos_profile_sensor_data,
                )

    @classmethod
    def from_config(cls, fleet_config_path, robot_id):
        config = load_config(fleet_config_path)
        for robot in config.robots:
            if robot.id == robot_id:
                return cls(robot, config.fleet.battery_models[robot.battery_model],
                           docks=config.stations.charging_stations)
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
        if msg.header.frame_id.lstrip("/") == f"{self._robot_id}/odom":
            self._dock.observe_velocity(stamp_ns(msg.header.stamp), hypot(linear.x, linear.y, linear.z),
                                        hypot(angular.x, angular.y, angular.z))

    def _on_lease(self, msg):
        self._dock.observe_lease(Ownership(
            stamp_ns(msg.stamp), msg.robot_id, msg.station_id,
            bytes(msg.executor_session_id.uuid), msg.assignment_epoch,
        ))

    def _on_status(self, msg):
        stationary = (msg.state in (RobotStatus.STATE_IDLE, RobotStatus.STATE_CHARGING)
                      and not msg.is_loaded and not msg.current_task_id)
        self._dock.observe_status(Ownership(
            stamp_ns(msg.header.stamp), msg.robot_id, msg.dock_station_id if stationary else "",
            bytes(msg.publisher_session_id.uuid), msg.current_epoch,
        ), msg.status_seq)

    def _on_physical_pose(self, msg):
        if msg.header.frame_id:
            p = msg.pose.position
            self._dock.observe_pose(stamp_ns(msg.header.stamp), p.x, p.y)

    def _on_clock(self, msg):
        now_ns = stamp_ns(msg.clock)
        previous_clock_ns = self._battery.clock_ns
        if now_ns < 0 or now_ns == previous_clock_ns:
            return
        if previous_clock_ns is not None and now_ns < previous_clock_ns:
            self._dock.session_blocked = True
        station = self._dock.station(now_ns)
        charging = (bool(station) and station == self._charging_station and previous_clock_ns is not None
                    and 0 < now_ns - previous_clock_ns <= DOCK_EVIDENCE_MAX_AGE_NS)
        self._battery.update_clock(now_ns, charging=charging)
        changed = station != self._charging_station
        self._charging_station = station
        if (self._last_published_ns is not None and now_ns >= previous_clock_ns
                and not changed and now_ns - self._last_published_ns < PUBLISH_PERIOD_NS):
            return

        self._publisher.publish(BatteryState(
            robot_id=self._robot_id,
            publisher_session_id=self._session_id,
            battery_energy_wh=self._battery.remaining_wh,
            battery_soc_percent=self._battery.soc_percent,
            battery_capacity_wh=self._battery.capacity_wh,
            is_charging=bool(station),
            charging_station_id=station,
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
    executor = SingleThreadedExecutor()
    stopping = False

    def request_stop(*_):
        nonlocal stopping
        stopping = True

    # Do not inject KeyboardInterrupt while a native subscription take is active.
    # Finish the current callback before destroying entities or the ROS context.
    previous_handlers = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        node = BatterySimulatorNode.from_config(args.fleet_config, args.robot_id)
        executor.add_node(node)
        while rclpy.ok() and not stopping:
            executor.spin_once(timeout_sec=0.2)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Battery Simulator configuration error: {exc}\n")
    finally:
        executor.shutdown()
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
