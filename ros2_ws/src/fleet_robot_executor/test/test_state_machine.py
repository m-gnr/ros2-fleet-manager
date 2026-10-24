"""ROS 2 package unit tests for fleet_robot_executor."""

import pytest

from fleet_robot_executor import (
    ClearErrorResult,
    ErrorReason,
    ExecutorConfig,
    OdometryReading,
    PoseStamped,
    RobotExecutorStateMachine,
    RobotState,
    StopDetector,
    TaskFeedback,
    TaskGoal,
    TaskPhase,
    TaskPriority,
    TaskResultStatus,
)


def create_goal(
    task_id: str = "task_001",
    assignment_epoch: int = 1,
    priority: int = TaskPriority.PRIORITY_MEDIUM,
    goal_uuid: str = "uuid-1234",
    pickup_x: float = 1.0,
    pickup_y: float = 2.0,
    dropoff_x: float = 5.0,
    dropoff_y: float = 6.0,
) -> TaskGoal:
    return TaskGoal(
        task_id=task_id,
        assignment_epoch=assignment_epoch,
        priority=priority,
        goal_uuid=goal_uuid,
        pickup_pose=PoseStamped(x=pickup_x, y=pickup_y, frame_id="map"),
        dropoff_pose=PoseStamped(x=dropoff_x, y=dropoff_y, frame_id="map"),
    )


class TestStopDetector:
    def test_stopped_with_fresh_odometry(self):
        odom = OdometryReading(timestamp_sec=10.0, linear_velocity=0.005, angular_velocity=0.002)
        stopped, reason = StopDetector.verify_stopped(odom, current_sim_time=10.2)
        assert stopped is True
        assert reason == ""

    def test_stale_odometry_rejected(self):
        odom = OdometryReading(timestamp_sec=10.0, linear_velocity=0.0, angular_velocity=0.0)
        stopped, reason = StopDetector.verify_stopped(odom, current_sim_time=11.5)
        assert stopped is False
        assert "ODOMETRY_STALE" in reason

    def test_future_odometry_rejected(self):
        odom = OdometryReading(timestamp_sec=15.0, linear_velocity=0.0, angular_velocity=0.0)
        stopped, reason = StopDetector.verify_stopped(odom, current_sim_time=10.0)
        assert stopped is False
        assert "ODOMETRY_IN_FUTURE" in reason

    def test_linear_velocity_exceeded(self):
        odom = OdometryReading(timestamp_sec=10.0, linear_velocity=0.05, angular_velocity=0.001)
        stopped, reason = StopDetector.verify_stopped(odom, current_sim_time=10.1)
        assert stopped is False
        assert "LINEAR_VELOCITY_EXCEEDED" in reason

    def test_angular_velocity_exceeded(self):
        odom = OdometryReading(timestamp_sec=10.0, linear_velocity=0.001, angular_velocity=0.08)
        stopped, reason = StopDetector.verify_stopped(odom, current_sim_time=10.1)
        assert stopped is False
        assert "ANGULAR_VELOCITY_EXCEEDED" in reason


class TestStateMachineCore:
    def test_initial_state(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=0)
        assert sm.robot_id == "robot_1"
        assert sm.state == RobotState.STATE_IDLE
        assert sm.current_phase == TaskPhase.PHASE_NONE
        assert sm.is_loaded is False
        assert sm.current_epoch == 0
        assert sm.current_task_id == ""

    def test_accept_valid_goal_when_idle(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=0)
        goal = create_goal(task_id="task_1", assignment_epoch=1)
        assert sm.accept_goal(goal) is True
        assert sm.state == RobotState.STATE_EXECUTING_TASK
        assert sm.current_phase == TaskPhase.PHASE_MOVING_TO_PICKUP
        assert sm.current_epoch == 1

    def test_happy_path_execution(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=1)
        goal = create_goal(task_id="task_alpha", assignment_epoch=2)
        assert sm.accept_goal(goal) is True
        assert sm.start_loading(goal.goal_uuid) is True
        assert sm.finish_loading(goal.goal_uuid) is True
        assert sm.is_loaded is True
        assert sm.start_unloading(goal.goal_uuid) is True
        result = sm.finish_unloading(goal.goal_uuid, current_sim_time=10.0)
        assert result is not None
        assert result.status == TaskResultStatus.STATUS_SUCCEEDED
        assert sm.state == RobotState.STATE_IDLE
        assert sm.is_loaded is False

    def test_preemption_stop_confirmation(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=1)
        goal = create_goal(priority=TaskPriority.PRIORITY_MEDIUM, goal_uuid="task-p1")
        sm.accept_goal(goal)

        accepted, _ = sm.request_cancel("task-p1", current_sim_time=1.0)
        assert accepted is True
        assert sm.is_cancelling is True

        # Moving odom
        moving_odom = OdometryReading(timestamp_sec=1.1, linear_velocity=0.2, angular_velocity=0.0)
        sm.update_odometry(moving_odom)
        assert sm.notify_nav2_cancel_result("task-p1", success=True, current_sim_time=1.1) is None

        # Stopped odom
        stopped_odom = OdometryReading(timestamp_sec=1.5, linear_velocity=0.0, angular_velocity=0.0)
        result = sm.update_odometry_and_check_cancel(stopped_odom, current_sim_time=1.5)
        assert result is not None
        assert result.status == TaskResultStatus.STATUS_PREEMPTED
        assert sm.state == RobotState.STATE_IDLE

    def test_clear_robot_error_preserves_epoch(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=4)
        sm.accept_goal(create_goal(assignment_epoch=4))
        sm.report_task_error(sm.active_goal_uuid, ErrorReason.NAV2_ABORTED, 2.0)
        assert sm.state == RobotState.STATE_ERROR

        stopped_odom = OdometryReading(timestamp_sec=3.0, linear_velocity=0.0, angular_velocity=0.0)
        res = sm.clear_robot_error("robot_1", expected_epoch=4, odometry=stopped_odom, current_sim_time=3.1)
        assert res.accepted is True
        assert res.resulting_state == RobotState.STATE_IDLE
        assert sm.current_epoch == 4  # Preserved, NOT incremented
