"""Full ROS 2 integration tests for RobotExecutorNode with Nav2 Action Server simulation.

Tests the complete end-to-end action lifecycle:
1. Happy path: Pickup navigation -> Loading -> Dropoff navigation -> Unloading -> STATUS_SUCCEEDED
2. Safe preemption: Pickup navigation -> Cancel request -> Nav2 abort -> Braking -> Stopped odom -> STATUS_PREEMPTED
3. Nav2 abort: Aborted navigation -> STATUS_FAILED -> STATE_ERROR -> ClearRobotError recovery (Option A)
"""

import math
import threading
import time
from pathlib import Path
import pytest

try:
    import rclpy
    from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import MultiThreadedExecutor
    from action_msgs.msg import GoalStatus
    from nav_msgs.msg import Odometry
    from fleet_interfaces.action import ExecuteTask
    from fleet_interfaces.msg import RobotStatus
    from fleet_interfaces.srv import ClearRobotError
    from nav2_msgs.action import NavigateToPose
    from fleet_robot_executor.constants import RobotState, TaskPhase, TaskPriority, TaskResultStatus
    from fleet_robot_executor.node import RobotExecutorNode
    HAS_ROS2_RUNTIME = True
except (ImportError, ModuleNotFoundError):
    HAS_ROS2_RUNTIME = False


pytestmark = pytest.mark.skipif(
    not HAS_ROS2_RUNTIME,
    reason="Requires ROS 2 Humble runtime and fleet_interfaces installed",
)


class MockNav2Server:
    """Mock Nav2 NavigateToPose action server for deterministic testing."""

    def __init__(self, node: rclpy.node.Node, action_name: str) -> None:
        self.node = node
        self.action_name = action_name
        self.cb_group = ReentrantCallbackGroup()
        self.goals_received = []
        self.cancel_requested = False
        self.should_succeed = True
        self.navigation_delay = 0.2

        self._server = ActionServer(
            self.node,
            NavigateToPose,
            self.action_name,
            execute_callback=self._execute_callback,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
            callback_group=self.cb_group,
        )

    def _goal_callback(self, goal_request):
        self.cancel_requested = False
        self.goals_received.append(goal_request)
        return GoalResponse.ACCEPT

    def _cancel_callback(self, goal_handle):
        self.cancel_requested = True
        return CancelResponse.ACCEPT

    def _execute_callback(self, goal_handle):
        start = time.time()
        while time.time() - start < self.navigation_delay:
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return NavigateToPose.Result()
            time.sleep(0.02)

        if self.should_succeed:
            goal_handle.succeed()
        else:
            goal_handle.abort()
        return NavigateToPose.Result()

    def destroy(self):
        self._server.destroy()


@pytest.fixture(scope="module")
def ros_env():
    """Manage rclpy init and shutdown for the module."""
    if not rclpy.ok():
        rclpy.init()
    yield
    if rclpy.ok():
        rclpy.shutdown()


def test_complete_task_lifecycle_happy_path(ros_env):
    """Test full logistics lifecycle: Moving to pickup -> Loading -> Moving to dropoff -> Unloading."""
    mock_nav2_node = rclpy.create_node("mock_nav2_node")
    mock_nav2 = MockNav2Server(mock_nav2_node, "/robot_1/navigate_to_pose")

    executor_node = RobotExecutorNode(node_name="test_robot_1_executor")
    executor_node.robot_id = "robot_1"
    executor_node.robot_namespace = "/robot_1"
    executor_node.nav2_action_name = "/robot_1/navigate_to_pose"
    executor_node.executor_config.loading_duration_sec = 0.1
    executor_node.executor_config.unloading_duration_sec = 0.1

    test_client_node = rclpy.create_node("test_client_node")
    execute_task_client = ActionClient(
        test_client_node,
        ExecuteTask,
        "/robot_1/execute_task",
    )

    executor = MultiThreadedExecutor()
    executor.add_node(mock_nav2_node)
    executor.add_node(executor_node)
    executor.add_node(test_client_node)

    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()

    try:
        assert execute_task_client.wait_for_server(timeout_sec=5.0)

        # Publish odometry
        odom_pub = test_client_node.create_publisher(Odometry, "/robot_1/odom", 10)
        odom = Odometry()
        odom.header.stamp = test_client_node.get_clock().now().to_msg()
        odom.pose.pose.position.x = 0.0
        odom.pose.pose.position.y = 0.0
        odom_pub.publish(odom)
        time.sleep(0.05)

        # Send ExecuteTask Goal
        goal = ExecuteTask.Goal()
        goal.task_id = "task_integration_001"
        goal.assignment_epoch = 1
        goal.priority = ExecuteTask.Goal.PRIORITY_MEDIUM
        goal.pickup_pose.pose.position.x = 2.0
        goal.pickup_pose.pose.position.y = 3.0
        goal.dropoff_pose.pose.position.x = 8.0
        goal.dropoff_pose.pose.position.y = 9.0

        feedback_phases = []

        def feedback_cb(feedback_msg):
            feedback_phases.append(feedback_msg.feedback.current_phase)

        send_future = execute_task_client.send_goal_async(goal, feedback_callback=feedback_cb)
        t0 = time.time()
        while not send_future.done() and (time.time() - t0 < 5.0):
            time.sleep(0.02)

        goal_handle = send_future.result()
        assert goal_handle.accepted is True

        # Wait for terminal result
        res_future = goal_handle.get_result_async()
        t0 = time.time()
        while not res_future.done() and (time.time() - t0 < 8.0):
            time.sleep(0.05)

        assert res_future.done() is True
        result_wrapper = res_future.result()
        assert result_wrapper.status == GoalStatus.STATUS_SUCCEEDED

        result = result_wrapper.result
        assert result.status == TaskResultStatus.STATUS_SUCCEEDED
        assert result.completed_epoch == 1
        assert result.error_reason == ""

        assert len(mock_nav2.goals_received) == 2
        assert mock_nav2.goals_received[0].pose.pose.position.x == 2.0
        assert mock_nav2.goals_received[1].pose.pose.position.x == 8.0

        assert TaskPhase.PHASE_MOVING_TO_PICKUP in feedback_phases
        assert TaskPhase.PHASE_LOADING in feedback_phases
        assert TaskPhase.PHASE_MOVING_TO_DROPOFF in feedback_phases
        assert TaskPhase.PHASE_UNLOADING in feedback_phases

        with executor_node._lock:
            assert executor_node.state_machine.state == RobotState.STATE_IDLE
            assert executor_node.state_machine.is_loaded is False

    finally:
        executor.shutdown()
        mock_nav2.destroy()
        mock_nav2_node.destroy_node()
        executor_node.destroy_node()
        test_client_node.destroy_node()


def test_safe_preemption_lifecycle(ros_env):
    """Test safe preemption: Cancel requested during pickup -> Nav2 cancel -> Braking -> PREEMPTED."""
    mock_nav2_node = rclpy.create_node("mock_nav2_preempt_node")
    mock_nav2 = MockNav2Server(mock_nav2_node, "/robot_1/navigate_to_pose")
    mock_nav2.navigation_delay = 2.0  # Slow navigation to allow cancel

    executor_node = RobotExecutorNode(node_name="test_robot_1_preempt")
    executor_node.robot_id = "robot_1"
    executor_node.robot_namespace = "/robot_1"
    executor_node.nav2_action_name = "/robot_1/navigate_to_pose"
    executor_node.executor_config.cancel_stop_timeout_sec = 2.0

    test_client_node = rclpy.create_node("test_client_preempt_node")
    execute_task_client = ActionClient(
        test_client_node,
        ExecuteTask,
        "/robot_1/execute_task",
    )

    odom_pub = test_client_node.create_publisher(Odometry, "/robot_1/odom", 10)

    executor = MultiThreadedExecutor()
    executor.add_node(mock_nav2_node)
    executor.add_node(executor_node)
    executor.add_node(test_client_node)

    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()

    try:
        assert execute_task_client.wait_for_server(timeout_sec=5.0)

        # Send initial stopped odom
        odom = Odometry()
        odom.header.stamp = test_client_node.get_clock().now().to_msg()
        odom_pub.publish(odom)

        # Send Medium priority task
        goal = ExecuteTask.Goal()
        goal.task_id = "task_preempt_002"
        goal.assignment_epoch = 2
        goal.priority = ExecuteTask.Goal.PRIORITY_MEDIUM
        goal.pickup_pose.pose.position.x = 5.0
        goal.dropoff_pose.pose.position.x = 10.0

        send_future = execute_task_client.send_goal_async(goal)
        t0 = time.time()
        while not send_future.done() and (time.time() - t0 < 5.0):
            time.sleep(0.02)

        goal_handle = send_future.result()
        assert goal_handle.accepted is True

        # Wait until robot starts MOVING_TO_PICKUP
        time.sleep(0.1)

        # Request cancellation
        cancel_future = goal_handle.cancel_goal_async()
        t0 = time.time()
        while not cancel_future.done() and (time.time() - t0 < 5.0):
            time.sleep(0.02)

        cancel_resp = cancel_future.result()
        assert cancel_resp is not None
        assert cancel_resp.return_code == 0  # CancelGoal_Response.ERROR_NONE

        # Send stopped odometry to satisfy StopDetector
        time.sleep(0.1)
        stopped_odom = Odometry()
        stopped_odom.header.stamp = test_client_node.get_clock().now().to_msg()
        stopped_odom.twist.twist.linear.x = 0.0
        stopped_odom.twist.twist.angular.z = 0.0
        odom_pub.publish(stopped_odom)

        # Wait for terminal result
        res_future = goal_handle.get_result_async()
        t0 = time.time()
        while not res_future.done() and (time.time() - t0 < 5.0):
            stopped_odom.header.stamp = test_client_node.get_clock().now().to_msg()
            odom_pub.publish(stopped_odom)
            time.sleep(0.05)

        assert res_future.done() is True
        result_wrapper = res_future.result()
        assert result_wrapper.status == GoalStatus.STATUS_CANCELED

        result = result_wrapper.result
        assert result.status == TaskResultStatus.STATUS_PREEMPTED
        assert result.completed_epoch == 2

        with executor_node._lock:
            assert executor_node.state_machine.state == RobotState.STATE_IDLE
            assert executor_node.state_machine.is_loaded is False

    finally:
        executor.shutdown()
        mock_nav2.destroy()
        mock_nav2_node.destroy_node()
        executor_node.destroy_node()
        test_client_node.destroy_node()


def test_nav2_failure_and_clear_error_recovery(ros_env):
    """Test Nav2 abort -> STATUS_FAILED -> STATE_ERROR -> ClearRobotError recovery."""
    mock_nav2_node = rclpy.create_node("mock_nav2_fail_node")
    mock_nav2 = MockNav2Server(mock_nav2_node, "/robot_1/navigate_to_pose")
    mock_nav2.should_succeed = False  # Simulate Nav2 failure
    mock_nav2.navigation_delay = 0.1

    executor_node = RobotExecutorNode(node_name="test_robot_1_fail")
    executor_node.robot_id = "robot_1"
    executor_node.robot_namespace = "/robot_1"
    executor_node.nav2_action_name = "/robot_1/navigate_to_pose"

    test_client_node = rclpy.create_node("test_client_fail_node")
    execute_task_client = ActionClient(
        test_client_node,
        ExecuteTask,
        "/robot_1/execute_task",
    )
    clear_error_client = test_client_node.create_client(
        ClearRobotError,
        "/robot_1/clear_robot_error",
    )

    odom_pub = test_client_node.create_publisher(Odometry, "/robot_1/odom", 10)

    executor = MultiThreadedExecutor()
    executor.add_node(mock_nav2_node)
    executor.add_node(executor_node)
    executor.add_node(test_client_node)

    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()

    try:
        assert execute_task_client.wait_for_server(timeout_sec=5.0)
        assert clear_error_client.wait_for_service(timeout_sec=5.0)

        # Send stopped odom
        stopped_odom = Odometry()
        stopped_odom.header.stamp = test_client_node.get_clock().now().to_msg()
        odom_pub.publish(stopped_odom)

        # Send Goal
        goal = ExecuteTask.Goal()
        goal.task_id = "task_fail_003"
        goal.assignment_epoch = 3
        goal.priority = ExecuteTask.Goal.PRIORITY_HIGH
        goal.pickup_pose.pose.position.x = 1.0
        goal.dropoff_pose.pose.position.x = 2.0

        send_future = execute_task_client.send_goal_async(goal)
        t0 = time.time()
        while not send_future.done() and (time.time() - t0 < 5.0):
            time.sleep(0.02)

        goal_handle = send_future.result()
        assert goal_handle.accepted is True

        # Wait for terminal failure
        res_future = goal_handle.get_result_async()
        t0 = time.time()
        while not res_future.done() and (time.time() - t0 < 5.0):
            time.sleep(0.02)

        assert res_future.done() is True
        result_wrapper = res_future.result()
        assert result_wrapper.status == GoalStatus.STATUS_ABORTED
        assert result_wrapper.result.status == TaskResultStatus.STATUS_FAILED

        # Verify robot state is STATE_ERROR
        with executor_node._lock:
            assert executor_node.state_machine.state == RobotState.STATE_ERROR
            assert executor_node.state_machine.current_epoch == 3

        # Call ClearRobotError
        clear_req = ClearRobotError.Request()
        clear_req.robot_id = "robot_1"
        clear_req.expected_epoch = 3

        clear_future = clear_error_client.call_async(clear_req)
        t0 = time.time()
        while not clear_future.done() and (time.time() - t0 < 5.0):
            time.sleep(0.02)

        clear_resp = clear_future.result()
        assert clear_resp.accepted is True
        assert clear_resp.resulting_state == int(RobotState.STATE_IDLE)

        # Verify Option A: current_epoch is preserved at 3
        with executor_node._lock:
            assert executor_node.state_machine.state == RobotState.STATE_IDLE
            assert executor_node.state_machine.current_epoch == 3

    finally:
        executor.shutdown()
        mock_nav2.destroy()
        mock_nav2_node.destroy_node()
        executor_node.destroy_node()
        test_client_node.destroy_node()
