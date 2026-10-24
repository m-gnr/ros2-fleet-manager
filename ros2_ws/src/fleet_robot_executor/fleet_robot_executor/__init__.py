"""Fleet Robot Executor Package.

Provides a testable, ROS 2 decoupled pure Python state machine
for logistics task execution, lifecycle management, and preemption,
along with the ROS 2 RobotExecutorNode adapter.
"""

from .config_loader import (
    RobotConfig,
    load_all_robots_from_fleet,
    load_robot_fleet_config,
)
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

# RobotExecutorNode requires rclpy; conditionally export
try:
    from .node import RobotExecutorNode
except (ImportError, ModuleNotFoundError):
    RobotExecutorNode = None

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
    "RobotConfig",
    "load_robot_fleet_config",
    "load_all_robots_from_fleet",
    "RobotExecutorNode",
]
