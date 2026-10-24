"""Pure Python State Machine for Robot Executor.

This module models the logistics task lifecycle, phase transitions,
cargo loading state, assignment_epoch/UUID matching, safe preemption
multi-criteria stop confirmation, and operator-driven error recovery.
It has zero ROS 2 runtime dependencies.
"""

from typing import Optional, Tuple

from .constants import (
    ErrorReason,
    RobotState,
    TaskPhase,
    TaskPriority,
    TaskResultStatus,
)
from .models import (
    ClearErrorResult,
    ExecutorConfig,
    OdometryReading,
    PoseStamped,
    RobotStatusSnapshot,
    TaskFeedback,
    TaskGoal,
    TaskResult,
)
from .stop_detector import StopDetector


class RobotExecutorStateMachine:
    """Manages the robot execution lifecycle and physical state authority."""

    def __init__(
        self,
        robot_id: str,
        config: Optional[ExecutorConfig] = None,
        initial_epoch: int = 0,
    ) -> None:
        self.robot_id = robot_id
        self.config = config or ExecutorConfig()

        # Physical and logistics state
        self.state: RobotState = RobotState.STATE_IDLE
        self.current_phase: TaskPhase = TaskPhase.PHASE_NONE
        self.is_loaded: bool = False
        self.current_epoch: int = initial_epoch
        self.current_task_id: str = ""

        # Active goal tracking
        self.active_goal: Optional[TaskGoal] = None
        self.active_goal_uuid: Optional[str] = None

        # Preemption and cancellation tracking
        self.is_cancelling: bool = False
        self.cancel_requested_at: Optional[float] = None
        self.nav2_cancel_confirmed: bool = False

        # Odometry and Telemetry
        self.current_pose: PoseStamped = PoseStamped()
        self.battery_soc_percent: float = 100.0
        self.battery_energy_wh: float = 100.0
        self.last_odometry: Optional[OdometryReading] = None
        self.last_error_reason: str = ""

    # =========================================================================
    # Task Acceptance & Goal Evaluation
    # =========================================================================

    def can_accept_goal(self, goal: TaskGoal) -> Tuple[bool, str]:
        """Evaluate if an incoming ExecuteTask goal can be accepted.

        Conditions:
        - Robot must be IDLE (or RETURNING_TO_PARK, which can be preempted for any task)
        - Robot must not be loaded (is_loaded == False)
        - Task ID must be non-empty
        - assignment_epoch must be >= current_epoch (stale epoch rejected)
        - Priority must be valid (HIGH, MEDIUM, LOW)
        - Goal UUID must be non-empty
        - pickup_pose and dropoff_pose must be defined
        """
        # Robot state verification
        if self.state not in (RobotState.STATE_IDLE, RobotState.STATE_RETURNING_TO_PARK):
            return False, ErrorReason.REJECTED_ROBOT_NOT_IDLE

        # Load check
        if self.is_loaded:
            return False, ErrorReason.REJECTED_ROBOT_IS_LOADED

        # Task ID validity
        if not goal.task_id or not goal.task_id.strip():
            return False, ErrorReason.REJECTED_INVALID_TASK_ID

        # Monotonic assignment epoch check (FM authority)
        if goal.assignment_epoch < self.current_epoch:
            return False, ErrorReason.REJECTED_STALE_EPOCH

        # Priority validity
        if goal.priority not in (
            TaskPriority.PRIORITY_HIGH,
            TaskPriority.PRIORITY_MEDIUM,
            TaskPriority.PRIORITY_LOW,
        ):
            return False, ErrorReason.REJECTED_INVALID_PRIORITY

        # Goal UUID validity
        if not goal.goal_uuid or not goal.goal_uuid.strip():
            return False, ErrorReason.REJECTED_MISSING_GOAL_UUID

        # Pose existence
        if goal.pickup_pose is None or goal.dropoff_pose is None:
            return False, ErrorReason.REJECTED_MISSING_POSE

        return True, ""

    def accept_goal(self, goal: TaskGoal) -> bool:
        """Accept an incoming ExecuteTask goal and transition to MOVING_TO_PICKUP."""
        can_accept, _ = self.can_accept_goal(goal)
        if not can_accept:
            return False

        self.state = RobotState.STATE_EXECUTING_TASK
        self.current_phase = TaskPhase.PHASE_MOVING_TO_PICKUP
        self.current_epoch = goal.assignment_epoch
        self.current_task_id = goal.task_id
        self.active_goal = goal
        self.active_goal_uuid = goal.goal_uuid
        self.is_loaded = False
        self.is_cancelling = False
        self.cancel_requested_at = None
        self.nav2_cancel_confirmed = False
        self.last_error_reason = ""

        return True

    # =========================================================================
    # Task Phase Transitions
    # =========================================================================

    def start_loading(self, goal_uuid: str) -> bool:
        """Called when robot arrives at pickup location and starts loading.

        Once loading starts, the task enters a locked phase and CANNOT be cancelled.
        """
        if goal_uuid != self.active_goal_uuid:
            return False
        if self.state != RobotState.STATE_EXECUTING_TASK:
            return False
        if self.current_phase != TaskPhase.PHASE_MOVING_TO_PICKUP:
            return False
        if self.is_cancelling:
            return False

        self.current_phase = TaskPhase.PHASE_LOADING
        return True

    def finish_loading(self, goal_uuid: str) -> bool:
        """Called when cargo loading completes. Marks cargo onboard and begins dropoff navigation."""
        if goal_uuid != self.active_goal_uuid:
            return False
        if self.current_phase != TaskPhase.PHASE_LOADING:
            return False

        self.is_loaded = True
        self.current_phase = TaskPhase.PHASE_MOVING_TO_DROPOFF
        return True

    def start_unloading(self, goal_uuid: str) -> bool:
        """Called when robot arrives at dropoff location and starts unloading."""
        if goal_uuid != self.active_goal_uuid:
            return False
        if self.current_phase != TaskPhase.PHASE_MOVING_TO_DROPOFF:
            return False

        self.current_phase = TaskPhase.PHASE_UNLOADING
        return True

    def finish_unloading(
        self,
        goal_uuid: str,
        current_sim_time: float,
    ) -> Optional[TaskResult]:
        """Called when cargo unloading completes. Transitions robot to IDLE and produces SUCCEEDED result."""
        if goal_uuid != self.active_goal_uuid:
            return None
        if self.current_phase != TaskPhase.PHASE_UNLOADING:
            return None

        self.is_loaded = False
        self.state = RobotState.STATE_IDLE
        self.current_phase = TaskPhase.PHASE_NONE

        result = TaskResult(
            status=TaskResultStatus.STATUS_SUCCEEDED,
            completed_epoch=self.current_epoch,
            completion_stamp_sec=current_sim_time,
            error_reason="",
        )

        self.current_task_id = ""
        self.active_goal = None
        self.active_goal_uuid = None

        return result

    # =========================================================================
    # Safe Cancellation & Preemption Lifecycle
    # =========================================================================

    def can_cancel_goal(self, goal_uuid: str) -> Tuple[bool, str]:
        """Evaluate if an active task can be cancelled/preempted.

        Rules:
        - Goal UUID must match active goal
        - Robot must be in STATE_EXECUTING_TASK
        - Active task priority must NOT be HIGH (HIGH tasks cannot be preempted)
        - Robot must be in PHASE_MOVING_TO_PICKUP (once loading starts, preemption is locked)
        - Robot must not be loaded (is_loaded == False)
        """
        if not self.active_goal or self.active_goal_uuid != goal_uuid:
            return False, ErrorReason.CANCEL_REJECTED_UUID_MISMATCH

        if self.state != RobotState.STATE_EXECUTING_TASK:
            return False, ErrorReason.CANCEL_REJECTED_NOT_EXECUTING

        if self.active_goal.priority == TaskPriority.PRIORITY_HIGH:
            return False, ErrorReason.CANCEL_REJECTED_HIGH_PRIORITY

        if self.current_phase != TaskPhase.PHASE_MOVING_TO_PICKUP:
            return False, ErrorReason.CANCEL_REJECTED_NOT_PICKUP_PHASE

        if self.is_loaded:
            return False, ErrorReason.CANCEL_REJECTED_ROBOT_LOADED

        return True, ""

    def request_cancel(
        self,
        goal_uuid: str,
        current_sim_time: float,
    ) -> Tuple[bool, str]:
        """Request cancellation of an active task.

        If accepted, enters cancelling state. The task will NOT be declared
        PREEMPTED until Nav2 cancellation AND physical stop via fresh odometry
        are confirmed.
        """
        can_cancel, reason = self.can_cancel_goal(goal_uuid)
        if not can_cancel:
            return False, reason

        if self.is_cancelling:
            return True, "ALREADY_CANCELLING"

        self.is_cancelling = True
        self.cancel_requested_at = current_sim_time
        self.nav2_cancel_confirmed = False

        return True, ""

    def notify_nav2_cancel_result(
        self,
        goal_uuid: str,
        success: bool,
        current_sim_time: float,
    ) -> Optional[TaskResult]:
        """Receive evidence of the matching Nav2 terminal cancellation.

        Missing evidence retains ownership without selecting an error policy.
        If Nav2 cancel succeeds, checks if odometry already confirmed physical stop.
        """
        if goal_uuid != self.active_goal_uuid or not self.is_cancelling:
            return None

        if not success:
            return None

        self.nav2_cancel_confirmed = True
        return self._try_complete_cancel(current_sim_time)

    def update_odometry_and_check_cancel(
        self,
        odometry: OdometryReading,
        current_sim_time: float,
    ) -> Optional[TaskResult]:
        """Update odometry and, if cancelling, verify stop criteria."""
        self.update_odometry(odometry)

        if self.is_cancelling:
            return self._try_complete_cancel(current_sim_time)
        return None

    def check_cancel_timeout(
        self,
        current_sim_time: float,
    ) -> Optional[TaskResult]:
        """Periodic check for cancellation stop timeout."""
        if not self.is_cancelling:
            return None
        return self._try_complete_cancel(current_sim_time)

    def _try_complete_cancel(
        self,
        current_sim_time: float,
    ) -> Optional[TaskResult]:
        """Verify the 3 simultaneous criteria for safe preemption:

        1. Ownership remains held while terminal evidence is absent
        2. Nav2 terminal cancellation confirmed
        3. Odometry is fresh and zero-velocity thresholds are met
        """
        if not self.is_cancelling:
            return None

        # 2. Nav2 terminal cancellation check
        if not self.nav2_cancel_confirmed:
            return None

        # 3. Odometry stop check
        if self.last_odometry is None:
            return None

        is_stopped, _ = StopDetector.verify_stopped(
            self.last_odometry,
            current_sim_time=current_sim_time,
            linear_threshold=self.config.linear_stop_threshold_m_s,
            angular_threshold=self.config.angular_stop_threshold_rad_s,
            freshness_sec=self.config.odometry_freshness_sec,
        )
        if not is_stopped:
            return None

        # Safe preemption confirmed!
        result = TaskResult(
            status=TaskResultStatus.STATUS_PREEMPTED,
            completed_epoch=self.current_epoch,
            completion_stamp_sec=current_sim_time,
            error_reason="",
        )

        self.state = RobotState.STATE_IDLE
        self.current_phase = TaskPhase.PHASE_NONE
        self.is_cancelling = False
        self.cancel_requested_at = None
        self.nav2_cancel_confirmed = False
        self.current_task_id = ""
        self.active_goal = None
        self.active_goal_uuid = None

        return result

    # =========================================================================
    # Error Handling & Fail-Safe Transitions
    # =========================================================================

    def report_task_error(
        self,
        goal_uuid: str,
        reason: str,
        current_sim_time: float,
    ) -> Optional[TaskResult]:
        """Report a terminal task error (e.g. Nav2 abort, hardware fault).

        Transitions robot to STATE_ERROR and produces STATUS_FAILED result.
        """
        if goal_uuid != self.active_goal_uuid:
            return None

        return self._transition_to_error(reason, current_sim_time)

    def _transition_to_error(
        self,
        reason: str,
        current_sim_time: float,
    ) -> TaskResult:
        """Internal helper to transition robot into STATE_ERROR."""
        result = TaskResult(
            status=TaskResultStatus.STATUS_FAILED,
            completed_epoch=self.current_epoch,
            completion_stamp_sec=current_sim_time,
            error_reason=reason,
        )

        self.state = RobotState.STATE_ERROR
        self.current_phase = TaskPhase.PHASE_NONE
        self.last_error_reason = reason
        self.is_cancelling = False
        self.cancel_requested_at = None
        self.nav2_cancel_confirmed = False

        # Retain current_task_id and current_epoch for diagnosis until ClearRobotError
        return result

    # =========================================================================
    # Manual Error Clearing (ClearRobotError.srv)
    # =========================================================================

    def clear_robot_error(
        self,
        robot_id: str,
        expected_epoch: int,
        odometry: Optional[OdometryReading] = None,
        current_sim_time: Optional[float] = None,
    ) -> ClearErrorResult:
        """Execute conditional manual error recovery.

        Criteria:
        1. robot_id matches
        2. Robot is in STATE_ERROR
        3. expected_epoch == current_epoch
        4. is_loaded == False (if loaded, operator cannot clear error via service)
        5. Robot is physically stopped (if odometry & time provided)

        Note (C2-DEC Option A):
        assignment_epoch IS NOT INCREMENTED during error clearing.
        FM maintains sole authority over assignment_epoch progression.
        """
        if robot_id != self.robot_id:
            return ClearErrorResult(
                accepted=False,
                reason=ErrorReason.CLEAR_REJECTED_ROBOT_ID_MISMATCH,
                resulting_state=int(self.state),
            )

        if self.state != RobotState.STATE_ERROR:
            return ClearErrorResult(
                accepted=False,
                reason=ErrorReason.CLEAR_REJECTED_NOT_IN_ERROR,
                resulting_state=int(self.state),
            )

        if expected_epoch != self.current_epoch:
            return ClearErrorResult(
                accepted=False,
                reason=ErrorReason.CLEAR_REJECTED_EPOCH_MISMATCH,
                resulting_state=int(self.state),
            )

        if self.is_loaded:
            return ClearErrorResult(
                accepted=False,
                reason=ErrorReason.CLEAR_REJECTED_ROBOT_IS_LOADED,
                resulting_state=int(self.state),
            )

        # Verify stop if telemetry provided
        if odometry is not None and current_sim_time is not None:
            is_stopped, stop_reason = StopDetector.verify_stopped(
                odometry,
                current_sim_time=current_sim_time,
                linear_threshold=self.config.linear_stop_threshold_m_s,
                angular_threshold=self.config.angular_stop_threshold_rad_s,
                freshness_sec=self.config.odometry_freshness_sec,
            )
            if not is_stopped:
                return ClearErrorResult(
                    accepted=False,
                    reason=f"{ErrorReason.CLEAR_REJECTED_ROBOT_NOT_STOPPED}: {stop_reason}",
                    resulting_state=int(self.state),
                )

        # Successful error clear
        self.state = RobotState.STATE_IDLE
        self.current_phase = TaskPhase.PHASE_NONE
        self.current_task_id = ""
        self.active_goal = None
        self.active_goal_uuid = None
        self.last_error_reason = ""
        # IMPORTANT: current_epoch remains unchanged (Option A)

        return ClearErrorResult(
            accepted=True,
            reason="",
            resulting_state=int(RobotState.STATE_IDLE),
        )

    # =========================================================================
    # Non-Task State Transitions (Charge & Park)
    # =========================================================================

    def start_returning_to_charge(self) -> bool:
        """Transition from IDLE to RETURNING_TO_CHARGE."""
        if self.state != RobotState.STATE_IDLE or self.is_loaded:
            return False
        self.state = RobotState.STATE_RETURNING_TO_CHARGE
        return True

    def start_charging(self) -> bool:
        """Transition to CHARGING."""
        if self.state not in (RobotState.STATE_RETURNING_TO_CHARGE, RobotState.STATE_IDLE):
            return False
        self.state = RobotState.STATE_CHARGING
        return True

    def stop_charging(self) -> bool:
        """Transition from CHARGING to IDLE."""
        if self.state != RobotState.STATE_CHARGING:
            return False
        self.state = RobotState.STATE_IDLE
        return True

    def start_returning_to_park(self) -> bool:
        """Transition from IDLE to RETURNING_TO_PARK."""
        if self.state != RobotState.STATE_IDLE or self.is_loaded:
            return False
        self.state = RobotState.STATE_RETURNING_TO_PARK
        return True

    def arrived_at_park(self) -> bool:
        """Transition from RETURNING_TO_PARK to IDLE."""
        if self.state != RobotState.STATE_RETURNING_TO_PARK:
            return False
        self.state = RobotState.STATE_IDLE
        return True

    # =========================================================================
    # Telemetry, Odometry & Snapshots
    # =========================================================================

    def update_odometry(self, odometry: OdometryReading) -> None:
        """Update cached odometry and current pose."""
        self.last_odometry = odometry
        if odometry.pose is not None:
            self.current_pose = odometry.pose

    def update_battery(self, soc_percent: float, energy_wh: float) -> None:
        """Update battery state of charge."""
        self.battery_soc_percent = soc_percent
        self.battery_energy_wh = energy_wh

    def get_status_snapshot(self, timestamp_sec: float) -> RobotStatusSnapshot:
        """Generate a snapshot matching RobotStatus.msg fields."""
        return RobotStatusSnapshot(
            robot_id=self.robot_id,
            current_epoch=self.current_epoch,
            state=int(self.state),
            current_phase=int(self.current_phase),
            is_loaded=self.is_loaded,
            pose=self.current_pose,
            battery_soc_percent=self.battery_soc_percent,
            battery_energy_wh=self.battery_energy_wh,
            current_task_id=self.current_task_id,
            timestamp_sec=timestamp_sec,
        )

    def get_feedback(self, distance_to_goal: float = 0.0) -> TaskFeedback:
        """Generate feedback matching ExecuteTask.action Feedback fields."""
        return TaskFeedback(
            current_phase=int(self.current_phase),
            current_pose=self.current_pose,
            distance_to_goal=distance_to_goal,
            battery_soc=self.battery_soc_percent,
        )
