"""Real ROS 2 Humble integration tests for Fleet Manager adapters.

Requires ROS 2 Humble runtime and fleet_interfaces installed (runs in docker).
Verifies:
- RobotStatus subscriber with status_seq and publisher_session_id
- ExecuteTask ActionClient with identical goal UUID, feedback, and completed_epoch matching
- ClearRobotError service call with expected_epoch
- Session change transition to SESSION_BLOCKED
"""

import asyncio
import os
import threading
import time
import uuid
import pytest

try:
    import rclpy
    from rclpy.action import ActionServer, CancelResponse, GoalResponse
    from rclpy.node import Node
    from rclpy.executors import SingleThreadedExecutor

    from fleet_interfaces.action import ExecuteTask
    from fleet_interfaces.msg import RobotStatus
    from fleet_interfaces.srv import ClearRobotError
    from geometry_msgs.msg import PoseStamped
    from unique_identifier_msgs.msg import UUID as RosUUID
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False

pytestmark = pytest.mark.skipif(not HAS_ROS2, reason="Requires ROS 2 Humble runtime and fleet_interfaces installed")

if HAS_ROS2:
    from backend.fleet_manager.adapters.action_client import ExecuteTaskActionClientBridge
    from backend.fleet_manager.adapters.outbox_sender import ROS2OutboxSender
    from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
    from backend.fleet_manager.adapters.service_client import ClearRobotErrorServiceClient
    from backend.fleet_manager.adapters.status_subscriber import RobotStatusSubscriberBridge
    from backend.fleet_manager.domain.constants import RobotState, TaskPriority, TaskResultStatus
    from backend.fleet_manager.domain.fleet_manager_core import FleetManagerCore
    from backend.fleet_manager.domain.models import Pose2D
    from backend.fleet_manager.domain.scheduler import RouteDistanceProvider
    from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
    from backend.fleet_manager.persistence.store import SQLiteStore

    class MockRoutes(RouteDistanceProvider):
        def get_path_distance(self, start: Pose2D, goal: Pose2D):
            return 10.0


def test_ros2_status_subscription_and_session_blocked(tmp_path):
    """Verify real ROS 2 RobotStatus pub/sub and session change detection."""
    rclpy.init()
    node = Node("test_fm_status_node")
    pub_node = Node("test_robot_publisher_node")

    db_path = str(tmp_path / "test_ros2_status.db")
    store = SQLiteStore(db_path)
    core = FleetManagerCore(MockRoutes(), Pose2D())
    core.register_robot("robot_1")

    async def scenario():
        loop = FleetEventLoop(store, core)
        await loop.start()

        bridge = RobotStatusSubscriberBridge(
            consumer=loop,
            loop=asyncio.get_running_loop(),
        )

        sub = node.create_subscription(
            RobotStatus,
            "/robot_1/robot_status",
            bridge.handle_status_msg,
            10,
        )

        pub = pub_node.create_publisher(RobotStatus, "/robot_1/robot_status", 10)

        # Background thread to spin pub_node and node
        executor = SingleThreadedExecutor()
        executor.add_node(node)
        executor.add_node(pub_node)

        spin_thread = threading.Thread(target=executor.spin, daemon=True)
        spin_thread.start()

        # Send initial status
        sess_1 = uuid.uuid4()
        msg1 = RobotStatus()
        msg1.robot_id = "robot_1"
        msg1.status_seq = 1
        msg1.publisher_session_id = RosUUID(uuid=list(sess_1.bytes))
        msg1.current_epoch = 0
        msg1.state = RobotState.STATE_IDLE
        msg1.current_phase = 0
        msg1.is_loaded = False
        msg1.pose.header.frame_id = "map"
        msg1.battery_soc_percent = 90.0
        msg1.battery_energy_wh = 90.0
        msg1.current_task_id = ""
        msg1.header.stamp = pub_node.get_clock().now().to_msg()

        pub.publish(msg1)
        await asyncio.sleep(0.3)

        # Verify initial status received in FM
        r_rec = loop.core.tracker.get_robot("robot_1")
        assert r_rec.session_id == str(sess_1)
        assert r_rec.initial_status_verified is True
        assert r_rec.session_blocked is False

        # Send second message with changed session UUID (Executor restart!)
        sess_2 = uuid.uuid4()
        msg2 = RobotStatus()
        msg2.robot_id = "robot_1"
        msg2.status_seq = 1
        msg2.publisher_session_id = RosUUID(uuid=list(sess_2.bytes))
        msg2.current_epoch = 0
        msg2.state = RobotState.STATE_IDLE
        msg2.current_phase = 0
        msg2.is_loaded = False
        msg2.pose.header.frame_id = "map"
        msg2.battery_soc_percent = 90.0
        msg2.battery_energy_wh = 90.0
        msg2.current_task_id = ""
        msg2.header.stamp = pub_node.get_clock().now().to_msg()

        pub.publish(msg2)
        await asyncio.sleep(0.3)

        # Verify robot entered SESSION_BLOCKED
        r_rec2 = loop.core.tracker.get_robot("robot_1")
        assert r_rec2.session_blocked is True

        await loop.close()
        executor.shutdown()
        node.destroy_node()
        pub_node.destroy_node()
        store.close()

    try:
        asyncio.run(scenario())
    finally:
        rclpy.shutdown()


def test_ros2_execute_task_action_client_happy_path(tmp_path):
    """Verify real ExecuteTask ActionClient lifecycle with identical goal UUID and completed_epoch."""
    rclpy.init()
    fm_node = Node("test_fm_action_node")
    server_node = Node("test_executor_server_node")

    db_path = str(tmp_path / "test_ros2_action.db")
    store = SQLiteStore(db_path)
    core = FleetManagerCore(MockRoutes(), Pose2D())
    core.register_robot("robot_1")

    # Set up mock ActionServer on server_node
    received_goal_uuids = []
    
    def goal_callback(goal_request):
        return GoalResponse.ACCEPT

    def cancel_callback(goal_handle):
        return CancelResponse.ACCEPT

    async def execute_callback(goal_handle):
        u_str = str(uuid.UUID(bytes=bytes(goal_handle.goal_id.uuid)))
        received_goal_uuids.append(u_str)

        # Send feedback
        fb = ExecuteTask.Feedback()
        fb.current_phase = 1
        fb.distance_to_goal = 5.0
        fb.battery_soc = 89.0
        goal_handle.publish_feedback(fb)

        # Return terminal result with completed_epoch matching request
        res = ExecuteTask.Result()
        res.status = int(TaskResultStatus.STATUS_SUCCEEDED)
        res.completed_epoch = goal_handle.request.assignment_epoch
        res.error_reason = ""
        goal_handle.succeed()
        return res

    act_server = ActionServer(
        server_node,
        ExecuteTask,
        "/robot_1/execute_task",
        execute_callback=execute_callback,
        goal_callback=goal_callback,
        cancel_callback=cancel_callback,
    )

    async def scenario():
        loop = FleetEventLoop(store, core)
        await loop.start()

        # Initial status
        await loop.submit(Event("ROBOT_STATUS", {
            "robot_id": "robot_1", "status_seq": 1, "publisher_session_id": str(uuid.uuid4()),
            "current_epoch": 0, "state": 1, "current_phase": 0, "is_loaded": False,
            "pose": Pose2D(), "battery_soc_percent": 100, "battery_energy_wh": 100,
            "current_task_id": None, "timestamp_sec": 10.0,
        }))

        # Submit and assign task
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "task_ros2", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
            "priority": TaskPriority.PRIORITY_MEDIUM, "created_at": 10.0,
        }))
        await loop.submit(Event("TICK", {"current_time": 10.0}))

        task = loop.core._active_tasks["task_ros2"]
        target_uuid = task.goal_uuid

        adapter = FleetROS2Adapter(
            node=fm_node,
            consumer=loop,
            loop=asyncio.get_running_loop(),
            robot_ids=["robot_1"],
        )

        executor = SingleThreadedExecutor()
        executor.add_node(fm_node)
        executor.add_node(server_node)

        spin_thread = threading.Thread(target=executor.spin, daemon=True)
        spin_thread.start()

        # Outbox dispatcher dispatches EXECUTE_TASK
        dispatcher = OutboxDispatcher(
            consumer=loop,
            sender=adapter.outbox_sender,
            clock=time.monotonic,
            retry_delay=2.0,
        )

        sent = await dispatcher.send_one()
        assert sent is True

        # Wait for action execution and terminal result processing in consumer
        await asyncio.sleep(0.5)

        # 1. Verify ActionServer received the EXACT SAME goal UUID!
        assert len(received_goal_uuids) == 1
        assert received_goal_uuids[0] == target_uuid

        # 2. Verify task is completed in FM!
        assert "task_ros2" not in loop.core._active_tasks
        assert "task_ros2" in loop.core._completed_tasks

        await loop.close()
        executor.shutdown()
        act_server.destroy()
        fm_node.destroy_node()
        server_node.destroy_node()
        store.close()

    try:
        asyncio.run(scenario())
    finally:
        rclpy.shutdown()


def test_ros2_clear_robot_error_service_call(tmp_path):
    """Verify real ClearRobotError service communication."""
    rclpy.init()
    fm_node = Node("test_fm_srv_node")
    server_node = Node("test_executor_srv_node")

    received_requests = []

    def clear_srv_cb(request, response):
        received_requests.append((request.robot_id, request.expected_epoch))
        response.accepted = True
        response.reason = "Cleared by test operator"
        response.resulting_state = RobotState.STATE_IDLE
        return response

    srv = server_node.create_service(ClearRobotError, "/robot_1/clear_robot_error", clear_srv_cb)

    async def scenario():
        client_bridge = ClearRobotErrorServiceClient(
            robot_id="robot_1",
            service_client=fm_node.create_client(ClearRobotError, "/robot_1/clear_robot_error"),
        )

        executor = SingleThreadedExecutor()
        executor.add_node(fm_node)
        executor.add_node(server_node)

        spin_thread = threading.Thread(target=executor.spin, daemon=True)
        spin_thread.start()

        resp = await client_bridge.clear_error(expected_epoch=7)
        assert resp.accepted is True
        assert resp.reason == "Cleared by test operator"
        assert len(received_requests) == 1
        assert received_requests[0] == ("robot_1", 7)

        executor.shutdown()
        srv.destroy()
        fm_node.destroy_node()
        server_node.destroy_node()

    try:
        asyncio.run(scenario())
    finally:
        rclpy.shutdown()
