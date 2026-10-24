"""ROS 2 Node integration and lifecycle tests for fleet_robot_executor."""

import math
from pathlib import Path
import pytest

# Skip if ROS 2 runtime dependencies are not installed in the current environment
try:
    import rclpy
    from rclpy.parameter import Parameter
    from rclpy.action import CancelResponse, GoalResponse
    from action_msgs.msg import GoalInfo
    from geometry_msgs.msg import PoseStamped as RosPoseStamped, Point, Quaternion
    from nav_msgs.msg import Odometry
    from fleet_interfaces.action import ExecuteTask
    from fleet_interfaces.msg import RobotStatus
    from fleet_interfaces.srv import ClearRobotError
    from fleet_robot_executor.node import RobotExecutorNode, quaternion_to_yaw, yaw_to_quaternion
    from fleet_robot_executor.constants import RobotState, TaskPhase, TaskPriority, TaskResultStatus
    HAS_ROS2_RUNTIME = True
except (ImportError, ModuleNotFoundError):
    HAS_ROS2_RUNTIME = False


pytestmark = pytest.mark.skipif(
    not HAS_ROS2_RUNTIME,
    reason="Requires ROS 2 Humble runtime and fleet_interfaces installed",
)


@pytest.fixture(scope="module")
def ros_context():
    """Manage rclpy init and shutdown lifecycle for test module."""
    if not rclpy.ok():
        rclpy.init()
    yield
    if rclpy.ok():
        rclpy.shutdown()


@pytest.fixture
def executor_node(ros_context):
    """Instantiate RobotExecutorNode with test fleet config."""
    fleet_path = str(Path("config/fleet.yaml").resolve())
    node = RobotExecutorNode(node_name="test_executor_node", parameter_overrides=[Parameter("duplicate_record_capacity", value=32)], _test_reset_verified=True)
    # Explicitly set test parameters
    node.robot_id = "robot_1"
    node.robot_namespace = "/robot_1"
    node.nav2_action_name = "/robot_1/navigate_to_pose"
    yield node
    node.destroy_node()


def test_quaternion_yaw_conversions():
    # 0 degrees
    qx, qy, qz, qw = yaw_to_quaternion(0.0)
    assert math.isclose(quaternion_to_yaw(qx, qy, qz, qw), 0.0, abs_tol=1e-5)

    # 90 degrees (pi/2)
    qx, qy, qz, qw = yaw_to_quaternion(math.pi / 2.0)
    assert math.isclose(quaternion_to_yaw(qx, qy, qz, qw), math.pi / 2.0, abs_tol=1e-5)

    # 180 degrees (pi)
    qx, qy, qz, qw = yaw_to_quaternion(math.pi)
    assert math.isclose(abs(quaternion_to_yaw(qx, qy, qz, qw)), math.pi, abs_tol=1e-5)


def test_node_configuration_loading(executor_node):
    assert executor_node.robot_id == "robot_1"
    assert executor_node.robot_namespace == "/robot_1"
    assert executor_node.nav2_action_name == "/robot_1/navigate_to_pose"
    assert executor_node.state_machine.state == RobotState.STATE_IDLE
    assert executor_node.state_machine.current_epoch == 0


def test_odometry_callback_updates_state_machine(executor_node):
    odom_msg = Odometry()
    odom_msg.header.stamp.sec = 100
    odom_msg.header.stamp.nanosec = 0
    odom_msg.pose.pose.position = Point(x=1.5, y=-2.5, z=0.0)
    qx, qy, qz, qw = yaw_to_quaternion(1.57)
    odom_msg.pose.pose.orientation = Quaternion(x=qx, y=qy, z=qz, w=qw)
    odom_msg.twist.twist.linear.x = 0.002
    odom_msg.twist.twist.linear.y = 0.001
    odom_msg.twist.twist.angular.z = 0.003

    executor_node._odom_callback(odom_msg)

    with executor_node._lock:
        curr_pose = executor_node.state_machine.current_pose
        odom = executor_node.state_machine.last_odometry

    assert curr_pose.x == 1.5
    assert curr_pose.y == -2.5
    assert math.isclose(curr_pose.yaw, 1.57, abs_tol=1e-2)
    assert odom is not None
    assert math.isclose(odom.linear_velocity, math.hypot(0.002, 0.001), abs_tol=1e-4)


def test_status_publishing(executor_node):
    published_msgs = []

    def mock_publish(msg):
        published_msgs.append(msg)

    executor_node._status_pub.publish = mock_publish
    executor_node._status_timer_callback()

    assert len(published_msgs) == 1
    msg = published_msgs[0]
    assert msg.robot_id == "robot_1"
    assert msg.current_epoch == 0
    assert msg.state == int(RobotState.STATE_IDLE)
    assert msg.current_phase == int(TaskPhase.PHASE_NONE)
    assert msg.is_loaded is False
    assert msg.battery_soc_percent == 100.0


def test_clear_robot_error_service(executor_node):
    # 1. Not in error -> rejected
    req = ClearRobotError.Request()
    req.robot_id = "robot_1"
    req.expected_epoch = 0
    resp = ClearRobotError.Response()
    resp = executor_node._clear_error_callback(req, resp)
    assert resp.accepted is False
    assert "CLEAR_REJECTED_NOT_IN_ERROR" in resp.reason

    # 2. Transition robot to ERROR state at epoch 5
    with executor_node._lock:
        executor_node.state_machine.state = RobotState.STATE_ERROR
        executor_node.state_machine.current_epoch = 5

    # 3. Epoch mismatch -> rejected
    req.expected_epoch = 4
    resp = ClearRobotError.Response()
    resp = executor_node._clear_error_callback(req, resp)
    assert resp.accepted is False
    assert "CLEAR_REJECTED_EPOCH_MISMATCH" in resp.reason

    # 4. Correct epoch and stopped robot -> accepted
    req.expected_epoch = 5
    resp = ClearRobotError.Response()
    resp = executor_node._clear_error_callback(req, resp)
    assert resp.accepted is True
    assert resp.resulting_state == int(RobotState.STATE_IDLE)

    # 5. Check Option A: assignment_epoch remains 5 (NOT incremented)
    with executor_node._lock:
        assert executor_node.state_machine.current_epoch == 5
        assert executor_node.state_machine.state == RobotState.STATE_IDLE


def test_goal_validation_callback(executor_node):
    goal_req = ExecuteTask.Goal()
    goal_req.task_id = "task_ros_1"
    goal_req.assignment_epoch = 1
    goal_req.priority = ExecuteTask.Goal.PRIORITY_MEDIUM
    goal_req.pickup_pose.pose.position.x = 1.0
    goal_req.dropoff_pose.pose.position.x = 2.0

    # Valid goal when IDLE -> ACCEPT
    resp = executor_node._goal_callback(goal_req)
    assert resp == GoalResponse.ACCEPT

    # Stale epoch -> REJECT
    with executor_node._lock:
        executor_node.state_machine.current_epoch = 10
    resp = executor_node._goal_callback(goal_req)
    assert resp == GoalResponse.REJECT


def test_cancel_callback_preemption_rules(executor_node):
    class MockGoalId:
        def __init__(self, uuid_bytes):
            self.uuid = list(uuid_bytes)

    class MockGoalHandle:
        def __init__(self, goal_id_bytes):
            self.goal_id = MockGoalId(goal_id_bytes)

    test_uuid_bytes = b"0123456789abcdef"
    test_uuid_str = RobotExecutorNode._uuid_to_str(test_uuid_bytes)
    mock_handle = MockGoalHandle(test_uuid_bytes)

    # 1. Not executing -> REJECT
    assert executor_node._cancel_callback(mock_handle) == CancelResponse.REJECT

    # 2. Executing HIGH priority task -> REJECT
    from fleet_robot_executor.models import TaskGoal, PoseStamped
    high_goal = TaskGoal(
        task_id="high_task",
        assignment_epoch=1,
        priority=TaskPriority.PRIORITY_HIGH,
        goal_uuid=test_uuid_str,
        pickup_pose=PoseStamped(),
        dropoff_pose=PoseStamped(),
    )
    with executor_node._lock:
        executor_node.state_machine.accept_goal(high_goal)
    assert executor_node._cancel_callback(mock_handle) == CancelResponse.REJECT

    # 3. Executing MEDIUM priority task in PICKUP phase -> ACCEPT
    med_goal = TaskGoal(
        task_id="med_task",
        assignment_epoch=2,
        priority=TaskPriority.PRIORITY_MEDIUM,
        goal_uuid=test_uuid_str,
        pickup_pose=PoseStamped(),
        dropoff_pose=PoseStamped(),
    )
    with executor_node._lock:
        executor_node.state_machine.state = RobotState.STATE_IDLE
        executor_node.state_machine.accept_goal(med_goal)
    assert executor_node._cancel_callback(mock_handle) == CancelResponse.ACCEPT

    # 4. Executing after loading has started -> REJECT
    with executor_node._lock:
        assert not executor_node.state_machine.start_loading(test_uuid_str)
        executor_node.state_machine.current_phase = TaskPhase.PHASE_LOADING
    assert executor_node._cancel_callback(mock_handle) == CancelResponse.REJECT
