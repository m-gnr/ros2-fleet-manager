"""ROS 2 package unit/integration tests for RobotExecutorNode."""

import math
from pathlib import Path
import pytest

try:
    import rclpy
    from rclpy.action import CancelResponse, GoalResponse
    from geometry_msgs.msg import Point, PoseStamped as RosPoseStamped, Quaternion
    from nav_msgs.msg import Odometry
    from fleet_interfaces.action import ExecuteTask
    from fleet_interfaces.msg import RobotStatus
    from fleet_interfaces.srv import ClearRobotError
    from fleet_robot_executor.constants import RobotState, TaskPhase, TaskPriority, TaskResultStatus
    from fleet_robot_executor.node import RobotExecutorNode, quaternion_to_yaw, yaw_to_quaternion
    HAS_ROS2_RUNTIME = True
except (ImportError, ModuleNotFoundError):
    HAS_ROS2_RUNTIME = False


pytestmark = pytest.mark.skipif(
    not HAS_ROS2_RUNTIME,
    reason="Requires ROS 2 Humble runtime and fleet_interfaces installed",
)


@pytest.fixture(scope="module")
def ros_context():
    """Manage rclpy init and shutdown lifecycle."""
    if not rclpy.ok():
        rclpy.init()
    yield
    if rclpy.ok():
        rclpy.shutdown()


@pytest.fixture
def executor_node(ros_context):
    """Instantiate RobotExecutorNode with test robot parameters."""
    node = RobotExecutorNode(node_name="test_executor_node")
    node.robot_id = "robot_1"
    node.robot_namespace = "/robot_1"
    node.nav2_action_name = "/robot_1/navigate_to_pose"
    yield node
    node.destroy_node()


def test_quaternion_conversions():
    qx, qy, qz, qw = yaw_to_quaternion(0.0)
    assert math.isclose(quaternion_to_yaw(qx, qy, qz, qw), 0.0, abs_tol=1e-5)

    qx, qy, qz, qw = yaw_to_quaternion(math.pi / 2.0)
    assert math.isclose(quaternion_to_yaw(qx, qy, qz, qw), math.pi / 2.0, abs_tol=1e-5)


def test_node_initialization(executor_node):
    assert executor_node.robot_id == "robot_1"
    assert executor_node.robot_namespace == "/robot_1"
    assert executor_node.state_machine.state == RobotState.STATE_IDLE
    assert executor_node.state_machine.current_epoch == 0


def test_odom_callback(executor_node):
    odom_msg = Odometry()
    odom_msg.header.stamp.sec = 200
    odom_msg.header.stamp.nanosec = 0
    odom_msg.pose.pose.position = Point(x=3.0, y=4.0, z=0.0)
    qx, qy, qz, qw = yaw_to_quaternion(0.5)
    odom_msg.pose.pose.orientation = Quaternion(x=qx, y=qy, z=qz, w=qw)
    odom_msg.twist.twist.linear.x = 0.001
    odom_msg.twist.twist.angular.z = 0.001

    executor_node._odom_callback(odom_msg)

    with executor_node._lock:
        curr_pose = executor_node.state_machine.current_pose
        odom = executor_node.state_machine.last_odometry

    assert curr_pose.x == 3.0
    assert curr_pose.y == 4.0
    assert math.isclose(curr_pose.yaw, 0.5, abs_tol=1e-2)
    assert odom is not None


def test_status_timer_publisher(executor_node):
    published_msgs = []
    executor_node._status_pub.publish = lambda msg: published_msgs.append(msg)
    executor_node._status_timer_callback()

    assert len(published_msgs) == 1
    msg = published_msgs[0]
    assert msg.robot_id == "robot_1"
    assert msg.state == int(RobotState.STATE_IDLE)
    assert msg.current_phase == int(TaskPhase.PHASE_NONE)


def test_clear_error_option_a(executor_node):
    with executor_node._lock:
        executor_node.state_machine.state = RobotState.STATE_ERROR
        executor_node.state_machine.current_epoch = 7

    req = ClearRobotError.Request()
    req.robot_id = "robot_1"
    req.expected_epoch = 7
    resp = ClearRobotError.Response()
    resp = executor_node._clear_error_callback(req, resp)

    assert resp.accepted is True
    assert resp.resulting_state == int(RobotState.STATE_IDLE)
    with executor_node._lock:
        assert executor_node.state_machine.current_epoch == 7  # Option A preserved
