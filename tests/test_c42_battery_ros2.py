"""Humble/CycloneDDS checks of the product Executor battery path."""

from uuid import uuid4
import time

import pytest

rclpy = pytest.importorskip("rclpy")
pytest.importorskip("fleet_interfaces.msg")

from fleet_interfaces.action import ExecuteTask
from fleet_interfaces.msg import BatteryState, RobotStatus
from rclpy.action import GoalResponse
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock
from unique_identifier_msgs.msg import UUID

from fleet_robot_executor.node import RobotExecutorNode

NS = 10**9


def sample(robot_id, stamp_ns, session, energy=95.0, **fields):
    msg = BatteryState(
        robot_id=robot_id, battery_capacity_wh=100.0, battery_energy_wh=float(energy),
        battery_soc_percent=float(energy), publisher_session_id=UUID(uuid=list(session.bytes)),
    )
    msg.battery_stamp.sec, msg.battery_stamp.nanosec = divmod(stamp_ns, NS)
    for key, value in fields.items():
        setattr(msg, key, value)
    return msg


class Rig:
    def __init__(self):
        self.executor = SingleThreadedExecutor()
        self.probe = rclpy.create_node("c42_battery_probe")
        self.executor.add_node(self.probe)
        self.clock = self.probe.create_publisher(Clock, "/clock", 1)
        self.status = {}
        self.nodes = {}
        self.sources = {}
        for robot in ("robot_1", "robot_2"):
            self.nodes[robot] = self.make_executor(robot)
            self.probe.create_subscription(
                RobotStatus, f"/{robot}/robot_status",
                lambda msg, rid=robot: self.status.__setitem__(rid, msg), 10,
            )

    def make_executor(self, robot, *, reset=True):
        node = RobotExecutorNode(
            node_name=f"c42_executor_{robot}",
            parameter_overrides=[
                Parameter("use_sim_time", value=True),
                Parameter("robot_id", value=robot),
                Parameter("duplicate_record_capacity", value=32),
            ],
            _test_reset_verified=reset,
        )
        self.executor.add_node(node)
        return node

    def add_source(self, robot):
        source = rclpy.create_node("battery_simulator", namespace=f"/{robot}")
        self.executor.add_node(source)
        self.sources[robot] = source
        publisher = source.create_publisher(BatteryState, "battery_state", 10)
        self.spin_until(lambda: publisher.get_subscription_count() == 1)
        # Matching alone does not establish publisher identity in the receiver graph.
        # One-shot samples are intentionally rejected until that independent discovery completes.
        def receiver_identified():
            endpoints = self.nodes[robot].get_publishers_info_by_topic(f"/{robot}/battery_state")
            return (len(endpoints) == 1 and endpoints[0].node_name == "battery_simulator"
                    and endpoints[0].node_namespace == f"/{robot}")
        self.spin_until(receiver_identified)
        return publisher

    def spin_until(self, condition, seconds=3.0):
        deadline = time.monotonic() + seconds
        while not condition():
            assert time.monotonic() < deadline, "DDS condition timed out"
            self.executor.spin_once(timeout_sec=0.02)

    def spin_for(self, seconds):
        end = time.monotonic() + seconds
        self.spin_until(lambda: time.monotonic() >= end, seconds=seconds + 1)

    def set_clock(self, seconds):
        msg = Clock()
        msg.clock.sec = seconds
        self.clock.publish(msg)
        self.spin_until(lambda: all(n.get_clock().now().nanoseconds == seconds * NS for n in self.nodes.values()))

    def destroy(self, node):
        self.executor.remove_node(node)
        node.destroy_node()

    def close(self):
        for node in self.executor.get_nodes():
            self.destroy(node)
        self.executor.shutdown()


@pytest.fixture
def rig():
    rclpy.init()
    case = Rig()
    try:
        case.spin_until(lambda: case.clock.get_subscription_count() == 2)
        case.set_clock(10)
        yield case
    finally:
        case.close()
        rclpy.try_shutdown()


def task():
    return ExecuteTask.Goal(task_id="delivery", assignment_epoch=1, priority=ExecuteTask.Goal.PRIORITY_LOW)


def test_namespaced_measurement_and_heartbeat(rig):
    robot1, robot2 = "robot_1", "robot_2"
    exec1 = rig.nodes[robot1]
    rig.spin_until(lambda: len(rig.status) == 2)
    assert rig.status[robot1].battery_energy_wh == 0
    assert rig.status[robot1].battery_stamp.sec == 0
    assert exec1._goal_callback(task()) == GoalResponse.REJECT

    wrong_pub = rig.probe.create_publisher(BatteryState, "/foreign/battery_state", 10)
    pub2 = rig.add_source(robot2)
    pub1 = rig.add_source(robot1)
    assert wrong_pub.get_subscription_count() == 0
    pub2.publish(sample(robot1, 10 * NS, uuid4()))
    rig.spin_for(0.25)
    assert rig.status[robot1].battery_stamp.sec == rig.status[robot2].battery_stamp.sec == 0
    session1 = uuid4()
    pub1.publish(sample(robot1, 10 * NS, session1, energy=98.25))
    pub2.publish(sample(robot2, 10 * NS, uuid4(), energy=87.5))
    rig.spin_until(lambda: rig.status[robot1].battery_stamp.sec == rig.status[robot2].battery_stamp.sec == 10)
    assert (rig.status[robot1].battery_energy_wh, rig.status[robot1].battery_soc_percent) == (98.25, 98.25)
    assert rig.status[robot2].battery_energy_wh == 87.5

    rig.set_clock(11)
    rig.spin_until(lambda: rig.status[robot1].header.stamp.sec == 11)
    assert rig.status[robot1].battery_stamp.sec == 10
    assert exec1._goal_callback(task()) == GoalResponse.ACCEPT

    received_at = exec1._battery.received_at
    pub1.publish(sample(robot1, 10 * NS, session1, energy=98.25))
    rig.spin_for(0.25)
    assert exec1._battery.received_at == received_at
    rig.spin_until(lambda: rig.status[robot1].battery_stamp.sec == 0)
    assert rig.status[robot1].header.stamp.sec == 11  # Gazebo clock paused.
    assert rig.status[robot1].battery_energy_wh == 98.25
    pub1.publish(sample(robot1, 11 * NS, session1, energy=98.0))
    rig.spin_until(lambda: rig.status[robot1].battery_stamp.sec == 11)


def test_clock_rewind_latches_even_after_clock_catches_up(rig):
    robot = "robot_1"
    pub = rig.add_source(robot)
    session = uuid4()
    pub.publish(sample(robot, 10 * NS, session))
    rig.spin_until(lambda: rig.status.get(robot) and rig.status[robot].battery_stamp.sec == 10)
    rig.set_clock(2)
    rig.set_clock(11)
    pub.publish(sample(robot, 11 * NS, session, energy=94))
    rig.spin_until(lambda: rig.status[robot].header.stamp.sec == 11)
    assert rig.status[robot].battery_stamp.sec == 0
    assert rig.status[robot].battery_energy_wh == 95
    assert rig.nodes[robot]._goal_callback(task()) == GoalResponse.REJECT


@pytest.mark.parametrize("replacement", ["session", "endpoint", "duplicate", "legacy_type"])
def test_source_change_fences_assignment(rig, replacement):
    robot = "robot_1"
    pub = rig.add_source(robot)
    session = uuid4()
    pub.publish(sample(robot, 10 * NS, session))
    rig.spin_until(lambda: rig.status.get(robot) and rig.status[robot].battery_stamp.sec == 10)
    rig.set_clock(11)
    if replacement == "session":
        # New process identity arrives before endpoint discovery catches up.
        pub.publish(sample(robot, 11 * NS, uuid4(), energy=100))
    elif replacement == "endpoint":
        rig.destroy(rig.sources[robot])
        pub = rig.add_source(robot)
        pub.publish(sample(robot, 11 * NS, uuid4(), energy=100))
    else:
        message_type = RobotStatus if replacement == "legacy_type" else BatteryState
        rig.probe.create_publisher(message_type, f"/{robot}/battery_state", 10)
        rig.spin_until(lambda: len(rig.nodes[robot].get_publishers_info_by_topic(f"/{robot}/battery_state")) == 2)
    rig.spin_until(lambda: bool(rig.nodes[robot]._battery.blocked_reason))
    rig.spin_until(lambda: rig.status[robot].battery_stamp.sec == 0)
    assert rig.status[robot].battery_energy_wh == 95
    assert rig.nodes[robot]._goal_callback(task()) == GoalResponse.REJECT


def test_executor_restart_keeps_reset_gate(rig):
    robot = "robot_1"
    pub = rig.add_source(robot)
    session = uuid4()
    pub.publish(sample(robot, 10 * NS, session))
    rig.spin_until(lambda: rig.status.get(robot) and rig.status[robot].battery_stamp.sec == 10)
    previous = bytes(rig.status[robot].publisher_session_id.uuid)
    rig.destroy(rig.nodes[robot])
    rig.nodes[robot] = rig.make_executor(robot, reset=False)
    rig.spin_until(lambda: bytes(rig.status[robot].publisher_session_id.uuid) != previous)
    rig.spin_until(lambda: rig.clock.get_subscription_count() == 2)
    rig.set_clock(11)
    pub.publish(sample(robot, 11 * NS, session, energy=94))
    rig.spin_until(lambda: rig.status[robot].battery_stamp.sec == 11)
    assert rig.nodes[robot]._goal_callback(task()) == GoalResponse.REJECT


def test_fleet_adapter_uses_battery_stamp_and_latches_clock_rewind(rig):
    import asyncio
    from contextlib import closing

    from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
    from backend.fleet_manager.builder import build_fleet_manager_from_config
    from backend.fleet_manager.event_loop import FleetEventLoop
    from backend.fleet_manager.persistence.store import SQLiteStore

    class Routes:
        def get_path_distance(self, robot_id, start, goal):
            return 1.0

    async def scenario():
        core, robot_ids = build_fleet_manager_from_config(route_provider=Routes())
        fm_node = rclpy.create_node("c42_manager_clock", parameter_overrides=[Parameter("use_sim_time", value=True)])
        rig.executor.add_node(fm_node)
        with closing(SQLiteStore(":memory:")) as store:
            now = time.monotonic()
            consumer = FleetEventLoop(store, core, clock=lambda: now)
            adapter = FleetROS2Adapter(
                fm_node, consumer, asyncio.get_running_loop(), robot_ids,
                robot_namespaces={robot_id: f"/probe_{robot_id}" for robot_id in robot_ids},
            )
            bridge = adapter.status_bridges["robot_1"]
            bridge.clock = lambda: now
            await consumer.start()
            try:
                rig.spin_until(lambda: rig.clock.get_subscription_count() == 3)
                rig.set_clock(11)
                rig.spin_until(lambda: fm_node.get_clock().now().nanoseconds == 11 * NS)
                msg = RobotStatus(
                    robot_id="robot_1", publisher_session_id=UUID(uuid=list(uuid4().bytes)),
                    status_seq=1, state=RobotStatus.STATE_IDLE, battery_energy_wh=95.0, battery_soc_percent=95.0,
                )
                msg.header.stamp.sec = 11
                msg.pose.header.stamp.sec = 9
                msg.battery_stamp.sec = 10
                assert await asyncio.wrap_future(bridge.handle_status_msg(msg)) == "APPLIED"
                robot = consumer.core.tracker.get_robot("robot_1")
                assert robot.battery_sample_ns == 10 * NS
                assert robot.last_pose_sample_ns == 9 * NS
                assert robot.battery_valid_until == now + 1.0

                msg.status_seq = 2
                msg.robot_id = "robot_2"
                assert bridge.handle_status_msg(msg) is None
                msg.robot_id = "robot_1"
                msg.battery_stamp.sec = 12
                assert await asyncio.wrap_future(bridge.handle_status_msg(msg)) == "APPLIED"
                robot = consumer.core.tracker.get_robot("robot_1")
                assert not robot.has_fresh_battery(now)
                assert robot.battery_energy_wh == 95.0

                msg.status_seq = 3
                msg.battery_stamp.sec = 11
                msg.battery_soc_percent = 12.0
                assert await asyncio.wrap_future(bridge.handle_status_msg(msg)) == "APPLIED"
                assert not consumer.core.tracker.get_robot("robot_1").has_fresh_battery(now)

                msg.status_seq = 4
                msg.battery_soc_percent = 94.0
                msg.battery_energy_wh = 94.0
                assert await asyncio.wrap_future(bridge.handle_status_msg(msg)) == "APPLIED"
                assert consumer.core.tracker.get_robot("robot_1").has_fresh_battery(now)

                rig.set_clock(2)
                rig.spin_until(lambda: fm_node.get_clock().now().nanoseconds == 2 * NS)
                rig.set_clock(12)
                rig.spin_until(lambda: fm_node.get_clock().now().nanoseconds == 12 * NS)
                assert consumer.core.scheduler.battery_clock_ns() == 0
                msg.status_seq = 5
                msg.header.stamp.sec = msg.battery_stamp.sec = 12
                assert await asyncio.wrap_future(bridge.handle_status_msg(msg)) == "APPLIED"
                assert not consumer.core.tracker.get_robot("robot_1").has_fresh_battery(now)
            finally:
                await consumer.close()
                rig.destroy(fm_node)

    asyncio.run(scenario())


def test_discovery_waits_for_ros_node_identity(rig, monkeypatch):
    from types import SimpleNamespace

    robot = "robot_1"
    pub = rig.add_source(robot)
    node = rig.nodes[robot]
    # Subscription matching and the receiving node graph are asynchronous DDS observations.
    rig.spin_until(lambda: len(node.get_publishers_info_by_topic(f"/{robot}/battery_state")) == 1)
    endpoint, = node.get_publishers_info_by_topic(f"/{robot}/battery_state")
    unknown = SimpleNamespace(
        endpoint_gid=endpoint.endpoint_gid, topic_type=endpoint.topic_type,
        node_name="_NODE_NAME_UNKNOWN_", node_namespace="_NODE_NAMESPACE_UNKNOWN_",
    )
    session = uuid4()
    with monkeypatch.context() as discovery:
        discovery.setattr(node, "get_publishers_info_by_topic", lambda topic: [unknown])
        pub.publish(sample(robot, 10 * NS, session))
        rig.spin_for(0.3)
        assert rig.status[robot].battery_stamp.sec == 0
        assert node._battery.session_id is None
        assert not node._battery.blocked_reason

    pub.publish(sample(robot, 10 * NS, session))
    rig.spin_until(lambda: rig.status[robot].battery_stamp.sec == 10)
