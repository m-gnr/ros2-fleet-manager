"""Comprehensive ROS 2 decoupled unit tests for the Robot Executor State Machine.

Tests cover:
- State machine lifecycle and phase transitions
- Goal acceptance, validation, and epoch monotonicity
- UUID and task matching (preventing stale results)
- Cancel eligibility (HIGH task locked, pre-pickup restriction, load restriction)
- Safe cancellation multi-criteria stop confirmation (Nav2 terminal cancel + fresh zero-velocity odom)
- Cancel timeout fail-safe behavior (transition to STATE_ERROR)
- ClearRobotError validation, refusal if loaded, and epoch preservation (Option A)
- Telemetry snapshots and feedback generation
"""

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
    """Helper to create a valid TaskGoal."""
    return TaskGoal(
        task_id=task_id,
        assignment_epoch=assignment_epoch,
        priority=priority,
        goal_uuid=goal_uuid,
        pickup_pose=PoseStamped(x=pickup_x, y=pickup_y, frame_id="map"),
        dropoff_pose=PoseStamped(x=dropoff_x, y=dropoff_y, frame_id="map"),
    )


# =============================================================================
# 1. StopDetector Tests
# =============================================================================

class TestStopDetector:
    def test_stopped_with_fresh_odometry(self):
        odom = OdometryReading(timestamp_sec=10.0, linear_velocity=0.005, angular_velocity=0.002)
        stopped, reason = StopDetector.verify_stopped(odom, current_sim_time=10.2)
        assert stopped is True
        assert reason == ""

    def test_stale_odometry_rejected(self):
        odom = OdometryReading(timestamp_sec=10.0, linear_velocity=0.0, angular_velocity=0.0)
        # Default freshness is 1.0s, delta is 1.5s
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


# =============================================================================
# 2. State Machine Initialization & Snapshots
# =============================================================================

class TestStateMachineInitialization:
    def test_initial_state(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=0)
        assert sm.robot_id == "robot_1"
        assert sm.state == RobotState.STATE_IDLE
        assert sm.current_phase == TaskPhase.PHASE_NONE
        assert sm.is_loaded is False
        assert sm.current_epoch == 0
        assert sm.current_task_id == ""
        assert sm.active_goal is None
        assert sm.active_goal_uuid is None
        assert sm.is_cancelling is False

    def test_status_snapshot_and_feedback(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=5)
        sm.update_battery(soc_percent=85.5, energy_wh=85.5)
        sm.update_odometry(OdometryReading(
            timestamp_sec=10.0,
            linear_velocity=0.0,
            angular_velocity=0.0,
            pose=PoseStamped(x=1.5, y=-2.0, yaw=0.5, timestamp_sec=10.0),
        ))

        snapshot = sm.get_status_snapshot(timestamp_sec=10.0)
        assert snapshot.robot_id == "robot_1"
        assert snapshot.current_epoch == 5
        assert snapshot.state == RobotState.STATE_IDLE
        assert snapshot.current_phase == TaskPhase.PHASE_NONE
        assert snapshot.is_loaded is False
        assert snapshot.battery_soc_percent == 85.5
        assert snapshot.battery_energy_wh == 85.5
        assert snapshot.pose.x == 1.5
        assert snapshot.pose.y == -2.0
        assert snapshot.current_task_id == ""

        feedback = sm.get_feedback(distance_to_goal=3.2)
        assert feedback.current_phase == TaskPhase.PHASE_NONE
        assert feedback.distance_to_goal == 3.2
        assert feedback.battery_soc == 85.5


# =============================================================================
# 3. Goal Acceptance & Preconditions
# =============================================================================

class TestGoalAcceptance:
    def test_accept_valid_goal_when_idle(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=0)
        goal = create_goal(task_id="task_1", assignment_epoch=1)

        can_accept, reason = sm.can_accept_goal(goal)
        assert can_accept is True
        assert reason == ""

        accepted = sm.accept_goal(goal)
        assert accepted is True
        assert sm.state == RobotState.STATE_EXECUTING_TASK
        assert sm.current_phase == TaskPhase.PHASE_MOVING_TO_PICKUP
        assert sm.current_epoch == 1
        assert sm.current_task_id == "task_1"
        assert sm.active_goal_uuid == goal.goal_uuid
        assert sm.is_loaded is False

    def test_accept_goal_when_returning_to_park(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=2)
        sm.start_returning_to_park()
        assert sm.state == RobotState.STATE_RETURNING_TO_PARK

        goal = create_goal(task_id="task_urgent", assignment_epoch=3, priority=TaskPriority.PRIORITY_LOW)
        can_accept, _ = sm.can_accept_goal(goal)
        assert can_accept is True

        accepted = sm.accept_goal(goal)
        assert accepted is True
        assert sm.state == RobotState.STATE_EXECUTING_TASK
        assert sm.current_phase == TaskPhase.PHASE_MOVING_TO_PICKUP

    def test_reject_when_already_executing_task(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        sm.accept_goal(create_goal(task_id="task_1", assignment_epoch=1))

        goal_2 = create_goal(task_id="task_2", assignment_epoch=2)
        can_accept, reason = sm.can_accept_goal(goal_2)
        assert can_accept is False
        assert reason == ErrorReason.REJECTED_ROBOT_NOT_IDLE

    def test_reject_when_charging_or_returning_to_charge(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        sm.start_returning_to_charge()
        assert sm.state == RobotState.STATE_RETURNING_TO_CHARGE
        assert sm.can_accept_goal(create_goal())[0] is False

        sm.start_charging()
        assert sm.state == RobotState.STATE_CHARGING
        assert sm.can_accept_goal(create_goal())[0] is False

    def test_reject_when_in_error_state(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        sm.accept_goal(create_goal())
        sm.report_task_error(sm.active_goal_uuid, reason=ErrorReason.NAV2_ABORTED, current_sim_time=1.0)
        assert sm.state == RobotState.STATE_ERROR

        can_accept, reason = sm.can_accept_goal(create_goal(assignment_epoch=10))
        assert can_accept is False
        assert reason == ErrorReason.REJECTED_ROBOT_NOT_IDLE

    def test_reject_when_robot_is_loaded(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        sm.is_loaded = True
        can_accept, reason = sm.can_accept_goal(create_goal())
        assert can_accept is False
        assert reason == ErrorReason.REJECTED_ROBOT_IS_LOADED

    def test_reject_stale_epoch(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=5)
        goal = create_goal(assignment_epoch=4)
        can_accept, reason = sm.can_accept_goal(goal)
        assert can_accept is False
        assert reason == ErrorReason.REJECTED_STALE_EPOCH

    def test_reject_invalid_task_id(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        goal = create_goal(task_id="")
        can_accept, reason = sm.can_accept_goal(goal)
        assert can_accept is False
        assert reason == ErrorReason.REJECTED_INVALID_TASK_ID

    def test_reject_invalid_priority(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        goal = create_goal(priority=99)
        can_accept, reason = sm.can_accept_goal(goal)
        assert can_accept is False
        assert reason == ErrorReason.REJECTED_INVALID_PRIORITY

    def test_reject_missing_uuid(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        goal = create_goal(goal_uuid="")
        can_accept, reason = sm.can_accept_goal(goal)
        assert can_accept is False
        assert reason == ErrorReason.REJECTED_MISSING_GOAL_UUID


# =============================================================================
# 4. Full Happy Path Lifecycle & Phase Transitions
# =============================================================================

class TestTaskExecutionLifecycle:
    def test_complete_task_happy_path(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=1)
        goal = create_goal(task_id="task_alpha", assignment_epoch=2, priority=TaskPriority.PRIORITY_HIGH)

        # 1. Accept Goal
        assert sm.accept_goal(goal) is True
        assert sm.state == RobotState.STATE_EXECUTING_TASK
        assert sm.current_phase == TaskPhase.PHASE_MOVING_TO_PICKUP
        assert sm.is_loaded is False

        # Feedback in moving to pickup
        fb = sm.get_feedback(distance_to_goal=10.0)
        assert fb.current_phase == TaskPhase.PHASE_MOVING_TO_PICKUP

        # 2. Arrived at pickup -> Start loading
        assert sm.start_loading(goal.goal_uuid) is True
        assert sm.current_phase == TaskPhase.PHASE_LOADING
        assert sm.is_loaded is False

        # 3. Finish loading -> Cargo onboard -> Moving to dropoff
        assert sm.finish_loading(goal.goal_uuid) is True
        assert sm.current_phase == TaskPhase.PHASE_MOVING_TO_DROPOFF
        assert sm.is_loaded is True

        # 4. Arrived at dropoff -> Start unloading
        assert sm.start_unloading(goal.goal_uuid) is True
        assert sm.current_phase == TaskPhase.PHASE_UNLOADING
        assert sm.is_loaded is True

        # 5. Finish unloading -> Complete task
        result = sm.finish_unloading(goal.goal_uuid, current_sim_time=42.5)
        assert result is not None
        assert result.status == TaskResultStatus.STATUS_SUCCEEDED
        assert result.completed_epoch == 2
        assert result.completion_stamp_sec == 42.5
        assert result.error_reason == ""

        # Post-completion state
        assert sm.state == RobotState.STATE_IDLE
        assert sm.current_phase == TaskPhase.PHASE_NONE
        assert sm.is_loaded is False
        assert sm.current_task_id == ""
        assert sm.active_goal is None
        assert sm.active_goal_uuid is None


# =============================================================================
# 5. Phase Locks & UUID Matching
# =============================================================================

class TestPhaseLocksAndUUIDMatching:
    def test_uuid_mismatch_prevents_transitions(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        goal = create_goal(goal_uuid="valid-uuid")
        sm.accept_goal(goal)

        # Mismatched UUID ignored
        assert sm.start_loading("wrong-uuid") is False
        assert sm.current_phase == TaskPhase.PHASE_MOVING_TO_PICKUP

        # Advance with valid UUID
        assert sm.start_loading("valid-uuid") is True
        assert sm.finish_loading("wrong-uuid") is False
        assert sm.current_phase == TaskPhase.PHASE_LOADING

        assert sm.finish_loading("valid-uuid") is True
        assert sm.start_unloading("wrong-uuid") is False
        assert sm.current_phase == TaskPhase.PHASE_MOVING_TO_DROPOFF

        assert sm.start_unloading("valid-uuid") is True
        assert sm.finish_unloading("wrong-uuid", current_sim_time=1.0) is None
        assert sm.current_phase == TaskPhase.PHASE_UNLOADING

    def test_out_of_order_phase_transitions_rejected(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        goal = create_goal(goal_uuid="u1")
        sm.accept_goal(goal)

        # Cannot skip to finish_loading
        assert sm.finish_loading("u1") is False
        # Cannot skip to start_unloading
        assert sm.start_unloading("u1") is False
        # Cannot finish unloading before loading
        assert sm.finish_unloading("u1", 1.0) is None


# =============================================================================
# 6. Preemption & Cancellation Eligibility
# =============================================================================

class TestCancellationEligibility:
    def test_cannot_cancel_high_priority_task(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        goal = create_goal(priority=TaskPriority.PRIORITY_HIGH, goal_uuid="high-task")
        sm.accept_goal(goal)

        can_cancel, reason = sm.can_cancel_goal("high-task")
        assert can_cancel is False
        assert reason == ErrorReason.CANCEL_REJECTED_HIGH_PRIORITY

        accepted, _ = sm.request_cancel("high-task", current_sim_time=1.0)
        assert accepted is False
        assert sm.is_cancelling is False

    def test_can_cancel_medium_or_low_before_pickup(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        goal = create_goal(priority=TaskPriority.PRIORITY_MEDIUM, goal_uuid="med-task")
        sm.accept_goal(goal)

        can_cancel, reason = sm.can_cancel_goal("med-task")
        assert can_cancel is True
        assert reason == ""

    def test_cannot_cancel_during_or_after_loading(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        goal = create_goal(priority=TaskPriority.PRIORITY_LOW, goal_uuid="low-task")
        sm.accept_goal(goal)

        # In PHASE_MOVING_TO_PICKUP -> cancel ok
        assert sm.can_cancel_goal("low-task")[0] is True

        # Begin loading -> cancel LOCKED
        sm.start_loading("low-task")
        assert sm.current_phase == TaskPhase.PHASE_LOADING
        can_cancel, reason = sm.can_cancel_goal("low-task")
        assert can_cancel is False
        assert reason == ErrorReason.CANCEL_REJECTED_NOT_PICKUP_PHASE

        # Finish loading -> Moving to dropoff (loaded)
        sm.finish_loading("low-task")
        assert sm.can_cancel_goal("low-task")[0] is False

        # In unloading
        sm.start_unloading("low-task")
        assert sm.can_cancel_goal("low-task")[0] is False

    def test_cannot_cancel_with_mismatched_uuid_or_not_executing(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        assert sm.can_cancel_goal("any-uuid")[0] is False

        goal = create_goal(goal_uuid="real-uuid")
        sm.accept_goal(goal)
        can_cancel, reason = sm.can_cancel_goal("other-uuid")
        assert can_cancel is False
        assert reason == ErrorReason.CANCEL_REJECTED_UUID_MISMATCH


# =============================================================================
# 7. Safe Cancellation Multi-Criteria Stop Confirmation
# =============================================================================

class TestSafeCancellationLifecycle:
    def test_cancellation_requires_both_nav2_and_odometry_stop(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=3)
        goal = create_goal(assignment_epoch=3, priority=TaskPriority.PRIORITY_MEDIUM, goal_uuid="task-c1")
        assert sm.accept_goal(goal) is True

        # 1. Request cancel
        accepted, reason = sm.request_cancel("task-c1", current_sim_time=10.0)
        assert accepted is True
        assert sm.is_cancelling is True
        # Robot MUST NOT be declared PREEMPTED yet!
        assert sm.state == RobotState.STATE_EXECUTING_TASK

        # 2. Nav2 reports successful terminal cancel, BUT odometry shows robot still in motion
        moving_odom = OdometryReading(timestamp_sec=10.2, linear_velocity=0.25, angular_velocity=0.05)
        sm.update_odometry(moving_odom)
        result = sm.notify_nav2_cancel_result("task-c1", success=True, current_sim_time=10.2)
        assert result is None  # Cannot complete preemption while robot is moving!
        assert sm.state == RobotState.STATE_EXECUTING_TASK

        # 3. Odometry updates with zero velocity and fresh timestamp
        stopped_odom = OdometryReading(timestamp_sec=10.5, linear_velocity=0.002, angular_velocity=0.001)
        result = sm.update_odometry_and_check_cancel(stopped_odom, current_sim_time=10.6)

        # 4. Now both conditions met -> PREEMPTED!
        assert result is not None
        assert result.status == TaskResultStatus.STATUS_PREEMPTED
        assert result.completed_epoch == 3
        assert result.completion_stamp_sec == 10.6
        assert result.error_reason == ""

        # Robot returned to IDLE
        assert sm.state == RobotState.STATE_IDLE
        assert sm.current_phase == TaskPhase.PHASE_NONE
        assert sm.is_cancelling is False
        assert sm.current_task_id == ""

    def test_odometry_stop_first_then_nav2_cancel(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=1)
        goal = create_goal(priority=TaskPriority.PRIORITY_LOW, goal_uuid="task-c2")
        sm.accept_goal(goal)

        sm.request_cancel("task-c2", current_sim_time=5.0)

        # Robot is already stopped
        stopped_odom = OdometryReading(timestamp_sec=5.1, linear_velocity=0.0, angular_velocity=0.0)
        result = sm.update_odometry_and_check_cancel(stopped_odom, current_sim_time=5.2)
        assert result is None  # Waiting for Nav2 cancel confirmation

        # Nav2 confirms cancel
        result = sm.notify_nav2_cancel_result("task-c2", success=True, current_sim_time=5.3)
        assert result is not None
        assert result.status == TaskResultStatus.STATUS_PREEMPTED
        assert sm.state == RobotState.STATE_IDLE

    def test_nav2_cancel_failure_triggers_fail_safe_error(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=1)
        goal = create_goal(priority=TaskPriority.PRIORITY_MEDIUM, goal_uuid="task-c3")
        sm.accept_goal(goal)

        sm.request_cancel("task-c3", current_sim_time=1.0)
        # Nav2 fails to cancel
        result = sm.notify_nav2_cancel_result("task-c3", success=False, current_sim_time=1.5)

        assert result is not None
        assert result.status == TaskResultStatus.STATUS_FAILED
        assert result.error_reason == ErrorReason.NAV2_CANCEL_FAILED
        assert sm.state == RobotState.STATE_ERROR

    def test_cancel_stop_timeout_triggers_fail_safe_error(self):
        config = ExecutorConfig(cancel_stop_timeout_sec=2.0)
        sm = RobotExecutorStateMachine(robot_id="robot_1", config=config, initial_epoch=1)
        goal = create_goal(priority=TaskPriority.PRIORITY_MEDIUM, goal_uuid="task-c4")
        sm.accept_goal(goal)

        sm.request_cancel("task-c4", current_sim_time=10.0)
        sm.notify_nav2_cancel_result("task-c4", success=True, current_sim_time=10.5)

        # Robot keeps moving past timeout (10.0 + 2.0 = 12.0)
        moving_odom = OdometryReading(timestamp_sec=12.5, linear_velocity=0.15, angular_velocity=0.0)
        result = sm.update_odometry_and_check_cancel(moving_odom, current_sim_time=12.5)

        # Must NOT be preempted, must be fail-safe ERROR!
        assert result is not None
        assert result.status == TaskResultStatus.STATUS_FAILED
        assert result.error_reason == ErrorReason.CANCEL_STOP_TIMEOUT
        assert sm.state == RobotState.STATE_ERROR


# =============================================================================
# 8. Terminal Task Errors
# =============================================================================

class TestTaskErrors:
    def test_report_task_error(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=7)
        goal = create_goal(task_id="err-task", assignment_epoch=7, goal_uuid="u-err")
        sm.accept_goal(goal)

        result = sm.report_task_error("u-err", reason=ErrorReason.NAV2_ABORTED, current_sim_time=20.0)
        assert result is not None
        assert result.status == TaskResultStatus.STATUS_FAILED
        assert result.error_reason == ErrorReason.NAV2_ABORTED
        assert result.completed_epoch == 7
        assert sm.state == RobotState.STATE_ERROR
        assert sm.current_phase == TaskPhase.PHASE_NONE
        # current_task_id retained for inspection until ClearRobotError
        assert sm.current_task_id == "err-task"

    def test_report_task_error_mismatched_uuid_ignored(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        goal = create_goal(goal_uuid="u-real")
        sm.accept_goal(goal)

        result = sm.report_task_error("u-stale", reason=ErrorReason.NAV2_ABORTED, current_sim_time=20.0)
        assert result is None
        assert sm.state == RobotState.STATE_EXECUTING_TASK


# =============================================================================
# 9. ClearRobotError & Epoch Preservation (C2-DEC Option A)
# =============================================================================

class TestClearRobotError:
    def test_clear_error_rejected_if_not_in_error(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=1)
        res = sm.clear_robot_error(robot_id="robot_1", expected_epoch=1)
        assert res.accepted is False
        assert res.reason == ErrorReason.CLEAR_REJECTED_NOT_IN_ERROR

    def test_clear_error_rejected_if_robot_id_mismatch(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=1)
        sm.accept_goal(create_goal(assignment_epoch=1))
        sm.report_task_error(sm.active_goal_uuid, ErrorReason.NAV2_ABORTED, 1.0)

        res = sm.clear_robot_error(robot_id="robot_2", expected_epoch=1)
        assert res.accepted is False
        assert res.reason == ErrorReason.CLEAR_REJECTED_ROBOT_ID_MISMATCH

    def test_clear_error_rejected_if_epoch_mismatch(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=5)
        sm.accept_goal(create_goal(assignment_epoch=5))
        sm.report_task_error(sm.active_goal_uuid, ErrorReason.NAV2_ABORTED, 1.0)

        res = sm.clear_robot_error(robot_id="robot_1", expected_epoch=4)
        assert res.accepted is False
        assert res.reason == ErrorReason.CLEAR_REJECTED_EPOCH_MISMATCH

    def test_clear_error_rejected_if_robot_is_loaded(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=2)
        goal = create_goal(assignment_epoch=2)
        sm.accept_goal(goal)
        sm.start_loading(goal.goal_uuid)
        sm.finish_loading(goal.goal_uuid)
        assert sm.is_loaded is True

        # Error occurs while loaded (e.g. dropoff nav aborted)
        sm.report_task_error(goal.goal_uuid, ErrorReason.NAV2_ABORTED, 10.0)
        assert sm.state == RobotState.STATE_ERROR
        assert sm.is_loaded is True

        # Operator CANNOT clear error via service while cargo is onboard!
        res = sm.clear_robot_error(robot_id="robot_1", expected_epoch=2)
        assert res.accepted is False
        assert res.reason == ErrorReason.CLEAR_REJECTED_ROBOT_IS_LOADED
        assert sm.state == RobotState.STATE_ERROR

    def test_clear_error_rejected_if_robot_not_stopped(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=1)
        sm.accept_goal(create_goal(assignment_epoch=1))
        sm.report_task_error(sm.active_goal_uuid, ErrorReason.NAV2_ABORTED, 1.0)

        moving_odom = OdometryReading(timestamp_sec=2.0, linear_velocity=0.1, angular_velocity=0.0)
        res = sm.clear_robot_error(robot_id="robot_1", expected_epoch=1, odometry=moving_odom, current_sim_time=2.1)
        assert res.accepted is False
        assert ErrorReason.CLEAR_REJECTED_ROBOT_NOT_STOPPED in res.reason

    def test_successful_clear_error_preserves_assignment_epoch(self):
        """CRITICAL: ClearRobotError must NOT increment assignment_epoch (Option A)."""
        sm = RobotExecutorStateMachine(robot_id="robot_1", initial_epoch=8)
        sm.accept_goal(create_goal(assignment_epoch=8))
        sm.report_task_error(sm.active_goal_uuid, ErrorReason.NAV2_ABORTED, 1.0)

        stopped_odom = OdometryReading(timestamp_sec=5.0, linear_velocity=0.0, angular_velocity=0.0)
        res = sm.clear_robot_error(
            robot_id="robot_1",
            expected_epoch=8,
            odometry=stopped_odom,
            current_sim_time=5.1,
        )

        assert res.accepted is True
        assert res.reason == ""
        assert res.resulting_state == RobotState.STATE_IDLE

        assert sm.state == RobotState.STATE_IDLE
        assert sm.current_phase == TaskPhase.PHASE_NONE
        assert sm.current_task_id == ""
        assert sm.active_goal is None
        assert sm.active_goal_uuid is None
        # Epoch MUST be preserved as 8, NOT incremented to 9!
        assert sm.current_epoch == 8

        # Verify next task with epoch 8 or 9 can be accepted
        next_goal = create_goal(task_id="task_after_err", assignment_epoch=9)
        assert sm.accept_goal(next_goal) is True


# =============================================================================
# 10. Non-Task State Transitions (Charge & Park)
# =============================================================================

class TestAuxiliaryStates:
    def test_charging_lifecycle(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        assert sm.start_returning_to_charge() is True
        assert sm.state == RobotState.STATE_RETURNING_TO_CHARGE

        assert sm.start_charging() is True
        assert sm.state == RobotState.STATE_CHARGING

        assert sm.stop_charging() is True
        assert sm.state == RobotState.STATE_IDLE

    def test_parking_lifecycle(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        assert sm.start_returning_to_park() is True
        assert sm.state == RobotState.STATE_RETURNING_TO_PARK

        assert sm.arrived_at_park() is True
        assert sm.state == RobotState.STATE_IDLE

    def test_cannot_charge_or_park_while_executing_or_loaded(self):
        sm = RobotExecutorStateMachine(robot_id="robot_1")
        sm.accept_goal(create_goal())

        assert sm.start_returning_to_charge() is False
        assert sm.start_returning_to_park() is False
