"""Humble DDS regressions for station action ownership and cancellation."""

import asyncio
import threading
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest

rclpy = pytest.importorskip("rclpy")
from action_msgs.msg import GoalStatus
from fleet_interfaces.action import ExecuteTask, NavigateToStation
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient, ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock
from unique_identifier_msgs.msg import UUID

from backend.fleet_manager.adapters import station_client
from fleet_robot_executor.node import RobotExecutorNode


def wait(future):
    deadline = time.monotonic() + 5
    while not future.done():
        assert time.monotonic() < deadline, "DDS future timed out"
        time.sleep(0.01)
    return future.result()


@pytest.mark.parametrize("charging", [False, True])
def test_station_and_transport_share_admission_and_terminal_gate(monkeypatch, charging):
    rclpy.init()
    node = RobotExecutorNode(parameter_overrides=[
        Parameter("duplicate_record_capacity", value=10), Parameter("use_sim_time", value=True),
    ], _test_reset_verified=True)
    # Isolate movement ownership. C4.2 and Fortress validate the battery source.
    monkeypatch.setattr(node, "_fresh_battery_stamp", lambda _: 1)
    peer = rclpy.create_node("c43_station_peer")
    executor = MultiThreadedExecutor(num_threads=8)
    executor.add_node(node)
    executor.add_node(peer)
    clock_pub = peer.create_publisher(Clock, "/clock", 10)
    odom_pub = peer.create_publisher(Odometry, "/robot_1/odom", 10)
    release = threading.Event()
    nav_started = threading.Event()
    nav_cancelled = threading.Event()
    nav_goals = []
    start = time.monotonic()

    def publish():
        ns = int((5 + time.monotonic() - start) * 10**9)
        tick = Clock()
        tick.clock.sec, tick.clock.nanosec = divmod(ns, 10**9)
        clock_pub.publish(tick)
        odometry = Odometry()
        odometry.header.stamp = tick.clock
        odometry.header.frame_id = "map"
        odometry.pose.pose.orientation.w = 1.0
        odom_pub.publish(odometry)

    def cancel(_):
        nav_cancelled.set()
        return CancelResponse.ACCEPT

    def execute(handle):
        nav_goals.append(handle.request)
        nav_started.set()
        assert release.wait(8)
        if handle.is_cancel_requested:
            handle.canceled()
        else:
            handle.succeed()
        return NavigateToPose.Result()

    peer.create_timer(0.02, publish)
    nav_server = ActionServer(peer, NavigateToPose, "/robot_1/navigate_to_pose",
                              execute_callback=execute, cancel_callback=cancel,
                              callback_group=ReentrantCallbackGroup())
    station = ActionClient(peer, NavigateToStation, "/robot_1/navigate_to_station")
    transport = ActionClient(peer, ExecuteTask, "/robot_1/execute_task")
    thread = threading.Thread(target=executor.spin)
    thread.start()
    try:
        assert station.wait_for_server(timeout_sec=5)
        deadline = time.monotonic() + 5
        while node.state_machine.last_odometry is None or node.get_clock().now().nanoseconds == 0:
            assert time.monotonic() < deadline
            time.sleep(0.02)
        goal = NavigateToStation.Goal(
            move_id="movement", robot_id="robot_2", station_id="dock_1" if charging else "park_1",
            expected_session_id=UUID(uuid=list(node.safety.session_id.bytes)), assignment_epoch=1,
            tolerance_radius=0.3, charging_station=charging,
        )
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.pose.orientation.w = 1.0
        assert not wait(station.send_goal_async(goal)).accepted
        goal.robot_id = "robot_1"
        handle = wait(station.send_goal_async(goal))
        assert handle.accepted and nav_started.wait(5)
        future = handle.get_result_async()
        assert not wait(station.send_goal_async(goal)).accepted
        task = ExecuteTask.Goal(task_id="delivery", assignment_epoch=2, priority=ExecuteTask.Goal.PRIORITY_LOW)
        assert not wait(transport.send_goal_async(task)).accepted
        response = wait(handle.cancel_goal_async())
        assert bool(response.goals_canceling) == (not charging)
        if not charging:
            assert nav_cancelled.wait(5)
        assert not future.done()
        release.set()
        result = wait(future)
        assert result.status == (GoalStatus.STATUS_SUCCEEDED if charging else GoalStatus.STATUS_CANCELED)
        assert result.result.completed_epoch == goal.assignment_epoch
        assert result.result.station_id == goal.station_id
        assert result.result.move_id == goal.move_id
        assert result.result.stationary_stamp.sec > 0
        assert len(nav_goals) == 1
        assert not wait(station.send_goal_async(goal)).accepted
    finally:
        release.set()
        node._stopping.set()
        executor.shutdown(timeout_sec=5)
        thread.join(timeout=5)
        nav_server.destroy()
        node.destroy_node()
        peer.destroy_node()
        rclpy.try_shutdown()


def test_station_outbox_retry_reuses_pending_goal_response(monkeypatch):
    async def scenario():
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        sends = []
        events = []

        class Consumer:
            async def submit(self, event):
                events.append(event)

        def send_goal(goal, *, goal_uuid):
            sends.append((goal, goal_uuid))
            return future

        monkeypatch.setattr(station_client, "GOAL_ACCEPT_TIMEOUT_SEC", 0.01)
        bridge = station_client.StationActionClient(SimpleNamespace(send_goal_async=send_goal), Consumer(), loop)
        command = {
            "kind": "NAVIGATE_TO_STATION", "task_id": "move", "assignment_epoch": 1, "goal_uuid": str(uuid4()),
        }
        payload = {
            "assigned_robot_id": "robot_1", "station_id": "park_1", "station_type": "PARKING",
            "session_id": str(uuid4()), "tolerance_radius": 0.3,
            "pose": {"frame_id": "map", "x": 1, "y": 0, "yaw": 0.0},
        }
        with pytest.raises(TimeoutError):
            await bridge.send(command, payload)
        with pytest.raises(TimeoutError):
            await bridge.send(command, payload)
        assert len(sends) == 1 and not events
        future.set_result(SimpleNamespace(accepted=False))
        await bridge.send(command, payload)
        assert len(sends) == 1
        assert events[0].kind == "STATION_GOAL_REJECTED"

    asyncio.run(scenario())
