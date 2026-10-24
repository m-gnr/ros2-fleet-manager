"""Fleet Robot Executor Package.

Provides a testable, ROS 2 decoupled pure Python state machine
for logistics task execution, lifecycle management, and preemption.
"""

from .constants import (
    DEFAULT_ANGULAR_STOP_THRESHOLD_RAD_S,
    DEFAULT_CANCEL_STOP_TIMEOUT_SEC,
    DEFAULT_LINEAR_STOP_THRESHOLD_M_S,
    DEFAULT_LOADING_DURATION_SEC,
    DEFAULT_ODOMETRY_FRESHNESS_SEC,
    DEFAULT_UNLOADING_DURATION_SEC,
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
    Pose2D,
    PoseStamped,
    RobotStatusSnapshot,
    TaskFeedback,
    TaskGoal,
    TaskResult,
)
from .state_machine import RobotExecutorStateMachine
from .stop_detector import StopDetector

__all__ = [
    "RobotState",
    "TaskPhase",
    "TaskPriority",
    "TaskResultStatus",
    "ErrorReason",
    "DEFAULT_LINEAR_STOP_THRESHOLD_M_S",
    "DEFAULT_ANGULAR_STOP_THRESHOLD_RAD_S",
    "DEFAULT_ODOMETRY_FRESHNESS_SEC",
    "DEFAULT_CANCEL_STOP_TIMEOUT_SEC",
    "DEFAULT_LOADING_DURATION_SEC",
    "DEFAULT_UNLOADING_DURATION_SEC",
    "Pose2D",
    "PoseStamped",
    "TaskGoal",
    "TaskFeedback",
    "TaskResult",
    "RobotStatusSnapshot",
    "OdometryReading",
    "ClearErrorResult",
    "ExecutorConfig",
    "StopDetector",
    "RobotExecutorStateMachine",
]
