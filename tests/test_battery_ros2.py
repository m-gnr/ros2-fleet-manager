from pathlib import Path
from time import monotonic

import pytest

rclpy = pytest.importorskip("rclpy")
from fleet_interfaces.msg import BatteryState
from nav_msgs.msg import Odometry
from rclpy.executors import SingleThreadedExecutor
from rosgraph_msgs.msg import Clock

from fleet_battery_simulator.node import BatterySimulatorNode, stamp_ns

FLEET_PATH = Path(__file__).resolve().parents[1] / "config/fleet.yaml"


def test_battery_topics_use_configured_namespaces_and_simulation_stamp():
    rclpy.init(args=[])
    executor = SingleThreadedExecutor()
    probe = rclpy.create_node("battery_probe")
    nodes = [BatterySimulatorNode.from_config(FLEET_PATH, robot_id) for robot_id in ("robot_1", "robot_2")]
    clock_pub = probe.create_publisher(Clock, "/clock", 10)
    odom_pub = probe.create_publisher(Odometry, "/robot_1/odom", 10)
    snapshots = [[], []]
    for node in [probe, *nodes]:
        executor.add_node(node)
    for node, messages in zip(nodes, snapshots):
        probe.create_subscription(BatteryState, f"{node.get_namespace()}/battery_state", messages.append, 10)

    def wait_for(condition):
        deadline = monotonic() + 5
        while not condition() and monotonic() < deadline:
            executor.spin_once(timeout_sec=0.02)
        assert condition()

    def publish_clock(nanosec):
        msg = Clock()
        msg.clock.sec = 1
        msg.clock.nanosec = nanosec
        clock_pub.publish(msg)

    def publish_odom(nanosec, x):
        msg = Odometry()
        msg.header.stamp.sec = 1
        msg.header.stamp.nanosec = nanosec
        msg.header.frame_id = "robot_1/odom"
        msg.child_frame_id = "robot_1/base_link"
        msg.pose.pose.position.x = x
        msg.twist.twist.linear.x = 0.5
        odom_pub.publish(msg)

    try:
        wait_for(lambda: clock_pub.get_subscription_count() >= 2
                 and odom_pub.get_subscription_count() == 1
                 and all(probe.count_publishers(f"{node.get_namespace()}/battery_state") == 1 for node in nodes))
        assert all(node.get_parameter("use_sim_time").value is True for node in nodes)
        assert not any(snapshots)
        publish_clock(0)
        wait_for(lambda: all(snapshots))
        assert all(records[-1].battery_energy_wh == 100.0 for records in snapshots)
        publish_odom(0, 12.0)
        publish_odom(250_000_000, 12.125)
        wait_for(lambda: len(nodes[0]._battery._pending) == 2)
        for _ in range(3):
            publish_clock(0)
            executor.spin_once(timeout_sec=0.02)
        assert [len(records) for records in snapshots] == [1, 1]
        publish_clock(250_000_000)
        wait_for(lambda: all(len(records) == 2 for records in snapshots))
        assert probe.count_publishers("/battery_state") == 0
        for index, records in enumerate(snapshots):
            msg = records[-1]
            assert msg.robot_id == f"robot_{index + 1}"
            assert stamp_ns(msg.battery_stamp) == 1_250_000_000
            assert msg.battery_capacity_wh == 100.0
            assert msg.is_charging is False
            expected = 100.0 - 2.0 * 0.25 / 3600 - (0.025 if index == 0 else 0.0)
            assert msg.battery_energy_wh == pytest.approx(expected, abs=1e-10)
            assert msg.battery_soc_percent == pytest.approx(expected, abs=5e-6)

        before_rewind = [records[-1].battery_energy_wh for records in snapshots]
        publish_clock(0)
        wait_for(lambda: all(len(records) == 3 for records in snapshots))
        assert all(stamp_ns(records[-1].battery_stamp) == 1_000_000_000 for records in snapshots)
        assert [records[-1].battery_energy_wh for records in snapshots] == before_rewind
    finally:
        executor.shutdown()
        for node in [probe, *nodes]:
            node.destroy_node()
        rclpy.try_shutdown()


def test_missing_battery_parameter_fails_before_start(tmp_path):
    config_path = tmp_path / "fleet.yaml"
    config_path.write_text(FLEET_PATH.read_text().replace("      idle_power_w: 2.0\n", ""))
    with pytest.raises(ValueError, match="idle_power_w"):
        BatterySimulatorNode.from_config(config_path, "robot_1")
    with pytest.raises(ValueError, match="unknown robot ID"):
        BatterySimulatorNode.from_config(FLEET_PATH, "unknown")
