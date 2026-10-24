"""Constants and definitions for the Robot Executor state machine.

These constants match the approved ROS 2 IDL definitions in fleet_interfaces:
- ExecuteTask.action (Goal priority, Result status, Feedback current_phase)
- RobotStatus.msg (state, current_phase)
- ClearRobotError.srv
"""

from enum import IntEnum


class RobotState(IntEnum):
    """High-level state of the mobile robot."""

    STATE_IDLE = 1
    STATE_EXECUTING_TASK = 2
    STATE_CHARGING = 3
    STATE_RETURNING_TO_CHARGE = 4
    STATE_RETURNING_TO_PARK = 5
    STATE_ERROR = 6


class TaskPhase(IntEnum):
    """Internal phase of task execution.

    Corresponds to feedback.current_phase and RobotStatus.current_phase.
    """

    PHASE_NONE = 0
    PHASE_MOVING_TO_PICKUP = 1
    PHASE_LOADING = 2
    PHASE_MOVING_TO_DROPOFF = 3
    PHASE_UNLOADING = 4


class TaskPriority(IntEnum):
    """Task priority values defined in ExecuteTask.action."""

    PRIORITY_HIGH = 1
    PRIORITY_MEDIUM = 2
    PRIORITY_LOW = 3


class TaskResultStatus(IntEnum):
    """Terminal result status values defined in ExecuteTask.action."""

    STATUS_SUCCEEDED = 1
    STATUS_FAILED = 2
    STATUS_PREEMPTED = 3


class ErrorReason:
    """Standardized error and rejection reason codes."""

    # Navigation & Execution errors
    NAV2_ABORTED = "NAV2_ABORTED"
    NAV2_CANCELED = "NAV2_CANCELED"
    NAV2_FAILED = "NAV2_FAILED"
    NAV2_CANCEL_FAILED = "NAV2_CANCEL_FAILED"
    CANCEL_STOP_TIMEOUT = "CANCEL_STOP_TIMEOUT"
    LOADING_FAILED = "LOADING_FAILED"
    UNLOADING_FAILED = "UNLOADING_FAILED"
    HARDWARE_FAULT = "HARDWARE_FAULT"

    # Goal rejection reasons
    REJECTED_ROBOT_NOT_IDLE = "REJECTED_ROBOT_NOT_IDLE"
    REJECTED_ROBOT_IS_LOADED = "REJECTED_ROBOT_IS_LOADED"
    REJECTED_INVALID_TASK_ID = "REJECTED_INVALID_TASK_ID"
    REJECTED_STALE_EPOCH = "REJECTED_STALE_EPOCH"
    REJECTED_INVALID_PRIORITY = "REJECTED_INVALID_PRIORITY"
    REJECTED_MISSING_GOAL_UUID = "REJECTED_MISSING_GOAL_UUID"
    REJECTED_MISSING_POSE = "REJECTED_MISSING_POSE"

    # Preemption / Cancel rejection reasons
    CANCEL_REJECTED_HIGH_PRIORITY = "CANCEL_REJECTED_HIGH_PRIORITY"
    CANCEL_REJECTED_NOT_PICKUP_PHASE = "CANCEL_REJECTED_NOT_PICKUP_PHASE"
    CANCEL_REJECTED_ROBOT_LOADED = "CANCEL_REJECTED_ROBOT_LOADED"
    CANCEL_REJECTED_NOT_EXECUTING = "CANCEL_REJECTED_NOT_EXECUTING"
    CANCEL_REJECTED_UUID_MISMATCH = "CANCEL_REJECTED_UUID_MISMATCH"

    # ClearRobotError rejection reasons
    CLEAR_REJECTED_NOT_IN_ERROR = "CLEAR_REJECTED_NOT_IN_ERROR"
    CLEAR_REJECTED_ROBOT_ID_MISMATCH = "CLEAR_REJECTED_ROBOT_ID_MISMATCH"
    CLEAR_REJECTED_EPOCH_MISMATCH = "CLEAR_REJECTED_EPOCH_MISMATCH"
    CLEAR_REJECTED_ROBOT_IS_LOADED = "CLEAR_REJECTED_ROBOT_IS_LOADED"
    CLEAR_REJECTED_ROBOT_NOT_STOPPED = "CLEAR_REJECTED_ROBOT_NOT_STOPPED"


# Note: The following values are configurable parameter defaults and recommendations
# (marked as unconfirmed proposals in architecture documentation, awaiting empirical calibration).
DEFAULT_LINEAR_STOP_THRESHOLD_M_S = 0.01
DEFAULT_ANGULAR_STOP_THRESHOLD_RAD_S = 0.01
DEFAULT_ODOMETRY_FRESHNESS_SEC = 1.0
DEFAULT_CANCEL_STOP_TIMEOUT_SEC = 3.0
DEFAULT_LOADING_DURATION_SEC = 2.0
DEFAULT_UNLOADING_DURATION_SEC = 2.0
