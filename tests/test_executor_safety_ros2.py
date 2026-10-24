"""Real DDS/action tests with controlled Nav2 terminal delivery."""
import threading
import time
import pytest

rclpy = pytest.importorskip('rclpy')
from rclpy.action import ActionClient, ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from action_msgs.msg import GoalStatus
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from fleet_interfaces.action import ExecuteTask
from fleet_robot_executor.node import RobotExecutorNode
from fleet_robot_executor.constants import RobotState


def wait(future, seconds=8):
    deadline = time.monotonic() + seconds
    while not future.done() and time.monotonic() < deadline:
        time.sleep(.01)
    assert future.done(), 'DDS future did not complete within test deadline'
    return future.result()


class ControlledNav2:
    def __init__(self, node, outcome):
        self.outcome = outcome
        self.cancel_seen = threading.Event()
        self.release = threading.Event()
        self.started = threading.Event()
        self.count = 0
        self.server = ActionServer(node, NavigateToPose, '/robot_1/navigate_to_pose',
            execute_callback=self.execute, cancel_callback=self.cancel,
            callback_group=ReentrantCallbackGroup())

    def cancel(self, handle):
        self.cancel_seen.set()
        return CancelResponse.ACCEPT

    def execute(self, handle):
        self.count += 1
        self.started.set()
        assert self.release.wait(12), 'Test harness did not release Nav2'
        if self.outcome == 'cancel' and handle.is_cancel_requested:
            handle.canceled()
        elif self.outcome == 'abort':
            handle.abort()
        else:
            handle.succeed()
        return NavigateToPose.Result()


@pytest.fixture
def rig():
    rclpy.init()
    node = RobotExecutorNode(parameter_overrides=[Parameter('duplicate_record_capacity', value=2)],
                             _test_reset_verified=True)
    node.executor_config.loading_duration_sec = .05
    node.executor_config.unloading_duration_sec = .05
    peer = rclpy.create_node('safety_peer')
    ex = MultiThreadedExecutor(num_threads=8)
    ex.add_node(node)
    ex.add_node(peer)
    thread = threading.Thread(target=ex.spin, daemon=True)
    thread.start()
    client = ActionClient(peer, ExecuteTask, '/robot_1/execute_task')
    assert client.wait_for_server(timeout_sec=5)
    servers = []
    yield node, peer, client, servers
    for server in servers:
        server.release.set()
    node._stopping.set()
    ex.shutdown(timeout_sec=3)
    for server in servers:
        server.server.destroy()
    node.destroy_node()
    peer.destroy_node()
    rclpy.shutdown()
    thread.join(timeout=3)


def goal(epoch=9):
    msg = ExecuteTask.Goal()
    msg.task_id = 'safety-task'
    msg.assignment_epoch = epoch
    msg.priority = ExecuteTask.Goal.PRIORITY_MEDIUM
    msg.pickup_pose.pose.position.x = 1.
    msg.dropoff_pose.pose.position.x = 2.
    return msg


@pytest.mark.parametrize('outcome', ['cancel', 'success', 'abort'])
def test_cancel_acceptance_is_not_terminal_and_real_race_result_wins(rig, outcome):
    node, peer, client, servers = rig
    nav = ControlledNav2(peer, outcome)
    servers.append(nav)
    odom_pub = peer.create_publisher(Odometry, '/robot_1/odom', 10)
    def publish_stopped():
        odom = Odometry()
        odom.header.stamp = peer.get_clock().now().to_msg()
        odom_pub.publish(odom)
    timer = peer.create_timer(.02, publish_stopped)
    request = goal()
    handle = wait(client.send_goal_async(request))
    assert handle.accepted
    assert nav.started.wait(5)
    result_future = handle.get_result_async()
    assert wait(handle.cancel_goal_async()).goals_canceling
    assert nav.cancel_seen.wait(5)
    time.sleep(.15)
    assert not result_future.done()
    assert node.state_machine.current_task_id == request.task_id
    assert not wait(client.send_goal_async(goal(10))).accepted
    nav.release.set()
    result = wait(result_future)
    expected = {'cancel': (GoalStatus.STATUS_CANCELED, 3),
                'success': (GoalStatus.STATUS_SUCCEEDED, 1),
                'abort': (GoalStatus.STATUS_ABORTED, 2)}[outcome]
    assert (result.status, result.result.status) == expected
    assert result.result.completed_epoch == 9
    assert nav.count == (2 if outcome == 'success' else 1)
    # New DDS UUID cannot replay the same task/epoch or changed payload.
    request.pickup_pose.pose.position.x = 99.
    assert not wait(client.send_goal_async(request)).accepted
    assert len(node.safety.records) == 1
    assert next(iter(node.safety.records.values())).terminal[1] == 9
    peer.destroy_timer(timer)


def test_terminal_cancel_waits_for_fresh_stopped_odometry(rig):
    node, peer, client, servers = rig
    nav = ControlledNav2(peer, 'cancel'); servers.append(nav)
    handle = wait(client.send_goal_async(goal()))
    assert nav.started.wait(5)
    wait(handle.cancel_goal_async())
    assert nav.cancel_seen.wait(5)
    nav.release.set()
    future = handle.get_result_async()
    time.sleep(.15)
    assert not future.done()
    stale = Odometry(); stale.header.stamp.sec = 1
    node._odom_callback(stale)
    time.sleep(.1)
    assert not future.done()
    moving = Odometry(); moving.header.stamp = node.get_clock().now().to_msg()
    moving.twist.twist.linear.x = .5
    node._odom_callback(moving)
    time.sleep(.1)
    assert not future.done()
    assert not wait(client.send_goal_async(goal(10))).accepted
    stopped = Odometry(); stopped.header.stamp = node.get_clock().now().to_msg()
    node._odom_callback(stopped)
    assert wait(future).result.status == 3


def test_startup_session_and_overflow_gate(rig):
    node, peer, client, servers = rig
    from fleet_robot_executor.safety import ExecutorSafety, UINT64_MAX
    first = node.safety.session_id
    # A fresh process has exactly this new, empty, blocked safety state.
    node.safety = ExecutorSafety(2)
    assert node.safety.session_id != first
    assert not wait(client.send_goal_async(goal())).accepted
    messages = []
    node._status_timer.cancel()
    node._status_pub.publish = messages.append
    node._status_timer_callback(); node._status_timer_callback()
    assert [m.status_seq for m in messages] == [1, 2]
    assert bytes(messages[0].publisher_session_id.uuid) == node.safety.session_id.bytes
    node.safety.blocked = False  # Test-only reset evidence.
    node.safety.status_seq = UINT64_MAX
    node._status_timer_callback()
    assert len(messages) == 2
    assert not wait(client.send_goal_async(goal())).accepted
