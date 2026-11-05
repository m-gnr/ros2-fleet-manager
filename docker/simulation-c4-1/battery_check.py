"""Isolated dual-robot Fortress validation of C4.1 battery telemetry."""

from copy import deepcopy
from math import hypot, isclose
import os
import sys
import time

import rclpy
from fleet_interfaces.msg import BatteryState
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock

from check import emit, gazebo_command, load_config as load_test_config, prepare_world
from fleet_battery_simulator.node import CLOCK_QOS, stamp_ns
from fleet_config.loader import load_config
from live_processes import bridge_executable, run_simulation

NS_PER_SEC = 1_000_000_000
INJECTED_COVARIANCE = -123.0


def simulation(test_config, fleet):
    world_path = prepare_world(test_config, fleet.model_dump())
    bridge = [bridge_executable(), "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock"]
    for robot in fleet.robots:
        bridge.extend([
            f"{robot.namespace}/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry",
            f"{robot.namespace}/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist",
        ])

    commands = [("gazebo", gazebo_command(world_path)), ("bridge", bridge)]
    battery_executable = ("/workspace/install/fleet_battery_simulator/lib/"
                          "fleet_battery_simulator/battery_simulator")
    commands.extend(
        (f"battery_{robot.id}", [battery_executable,
                                "--fleet-config", test_config["fleet_config_path"],
                                "--robot-id", robot.id])
        for robot in fleet.robots
    )
    return run_simulation(commands, (), emit)


def validate(node, fleet, timeout):
    robots = fleet.robots
    moving = robots[0]
    assert len(robots) >= 2
    clock = None
    states = {}
    odometry = {robot.id: {} for robot in robots}

    def on_clock(msg):
        nonlocal clock
        clock = stamp_ns(msg.clock)

    def on_odom(robot_id, msg):
        if msg.pose.covariance[0] != INJECTED_COVARIANCE:
            odometry[robot_id][stamp_ns(msg.header.stamp)] = msg

    def on_battery(robot, msg):
        model = fleet.fleet.battery_models[robot.battery_model]
        assert msg.robot_id == robot.id
        assert msg.battery_capacity_wh == model.usable_capacity_wh
        assert 0.0 <= msg.battery_energy_wh <= msg.battery_capacity_wh
        assert isclose(msg.battery_soc_percent, 100 * (msg.battery_energy_wh / msg.battery_capacity_wh),
                       rel_tol=0, abs_tol=5e-6)
        assert not msg.is_charging
        previous = states.get(robot.id)
        if previous is not None:
            assert stamp_ns(msg.battery_stamp) > stamp_ns(previous.battery_stamp)
            assert msg.battery_energy_wh <= previous.battery_energy_wh
        states[robot.id] = msg

    node.create_subscription(Clock, "/clock", on_clock, CLOCK_QOS)
    for robot in robots:
        node.create_subscription(
            Odometry, f"{robot.namespace}/odom",
            lambda msg, r=robot: on_odom(r.id, msg), qos_profile_sensor_data,
        )
        node.create_subscription(
            BatteryState, f"{robot.namespace}/battery_state",
            lambda msg, r=robot: on_battery(r, msg), 10,
        )
    motor = node.create_publisher(Twist, f"{moving.namespace}/cmd_vel", 10)
    deadline = time.monotonic() + min(timeout, 90.0)

    def spin_until(condition):
        while not condition():
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for C4.1 Gazebo observations")
            rclpy.spin_once(node, timeout_sec=0.05)

    spin_until(lambda: clock is not None and len(states) == len(robots) and all(odometry.values())
               and motor.get_subscription_count() == 1
               and all(node.count_publishers(f"{robot.namespace}/odom") == 1 for robot in robots))
    assert node.count_publishers("/clock") == 1
    battery_topics = {f"{robot.namespace}/battery_state" for robot in robots}
    assert {topic for topic, _ in node.get_topic_names_and_types()
            if topic.endswith("/battery_state")} == battery_topics
    for robot in robots:
        topic = f"{robot.namespace}/battery_state"
        publisher, = node.get_publishers_info_by_topic(topic)
        assert publisher.node_namespace == robot.namespace
        assert publisher.node_name == "battery_simulator"
        assert publisher.topic_type == "fleet_interfaces/msg/BatteryState"
    emit("C41_GRAPH_VERIFIED", battery_topics=sorted(battery_topics), clock_publishers=1)

    fault_publisher = node.create_publisher(Odometry, f"{moving.namespace}/odom", 10)
    spin_until(lambda: fault_publisher.get_subscription_count() >= 2)
    velocity = Twist()
    velocity.linear.x = 0.18

    def inject_faults():
        records = odometry[moving.id]
        latest = records[max(records)]
        fault_publisher.publish(latest)
        jump = deepcopy(latest)
        jump.header.stamp.sec, jump.header.stamp.nanosec = divmod(clock + 1_000_000, NS_PER_SEC)
        jump.pose.covariance[0] = INJECTED_COVARIANCE
        jump.pose.pose.position.x += 1000.0
        fault_publisher.publish(jump)
        invalid = deepcopy(jump)
        invalid.header.stamp.sec, invalid.header.stamp.nanosec = divmod(clock + 2_000_000, NS_PER_SEC)
        invalid.pose.pose.position.x = float("nan")
        fault_publisher.publish(invalid)

    def measure(label, duration, drive=False, faults=False):
        before = states.copy()
        target = clock + duration * NS_PER_SEC
        next_command = clock
        count = 0

        def tick():
            nonlocal next_command, count
            if clock >= target:
                return True
            if clock >= next_command:
                if drive:
                    motor.publish(velocity)
                if faults:
                    inject_faults()
                    count += 1
                next_command = clock + NS_PER_SEC // 10
            return False

        spin_until(tick)
        if drive:
            motor.publish(Twist())
            target += NS_PER_SEC  # Include deceleration before comparing the window.
        spin_until(lambda: all(stamp_ns(states[r.id].battery_stamp) >= target for r in robots))
        if faults:
            assert count >= 10
        for robot in robots:
            start, end = before[robot.id], states[robot.id]
            start_ns, end_ns = stamp_ns(start.battery_stamp), stamp_ns(end.battery_stamp)
            spin_until(lambda: max(odometry[robot.id]) >= end_ns and clock >= end_ns)
            points = [
                (msg.pose.pose.position.x, msg.pose.pose.position.y)
                for stamp, msg in sorted(odometry[robot.id].items()) if start_ns <= stamp <= end_ns
            ]
            assert len(points) >= 2
            distance = sum(hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(points, points[1:]))
            if drive and robot == moving:
                assert distance > 0.5, f"Insufficient actual motion: {distance} m"
            else:
                assert distance < 0.001, f"{robot.id} should be stationary: {distance} m"

            model = fleet.fleet.battery_models[robot.battery_model]
            elapsed = (end_ns - start_ns) / NS_PER_SEC
            idle_wh = model.idle_power_w * elapsed / 3600
            motion_wh = model.consumption_wh_per_meter * distance
            measured = start.battery_energy_wh - end.battery_energy_wh
            emit("C41_ENERGY_MEASUREMENT", phase=label, robot_id=robot.id, simulated_seconds=elapsed,
                 distance_m=distance, idle_wh=idle_wh, motion_wh=motion_wh, consumed_wh=measured,
                 remaining_wh=end.battery_energy_wh, soc_percent=end.battery_soc_percent,
                 end_stamp_ns=end_ns, injected_batches=count)
            # Cross-topic DDS timing can omit a sample at each measurement boundary.
            tolerance = 0.002 if drive and robot == moving else 0.0001
            assert isclose(measured, idle_wh + motion_wh, rel_tol=0, abs_tol=tolerance), robot.id

    try:
        measure("idle", 3)
        measure("motion", 6, drive=True)
        measure("faults", 3, faults=True)
    finally:
        motor.publish(Twist())
    emit("ALL_C4_1_TESTS_PASSED", token=os.environ["DDS_TEST_PAYLOAD"])


def main():
    test_config, _, timeout = load_test_config()
    fleet = load_config(test_config["fleet_config_path"])
    if os.environ["SIM_CHECK_ROLE"] == "simulation":
        return simulation(test_config, fleet)

    rclpy.init()
    node = rclpy.create_node("c4_1_live_check")
    try:
        validate(node, fleet, timeout)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
