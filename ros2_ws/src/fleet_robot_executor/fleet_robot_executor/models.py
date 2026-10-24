"""Pure Python data models for the Robot Executor state machine.

These models provide complete decoupling from ROS 2 middleware packages,
enabling pure Python testing while strictly mirroring IDL message structures.
"""

from dataclasses import dataclass, field
from typing import Optional

from .constants import (
    DEFAULT_ANGULAR_STOP_THRESHOLD_RAD_S,
    DEFAULT_CANCEL_STOP_TIMEOUT_SEC,
    DEFAULT_LINEAR_STOP_THRESHOLD_M_S,
    DEFAULT_LOADING_DURATION_SEC,
    DEFAULT_ODOMETRY_FRESHNESS_SEC,
    DEFAULT_UNLOADING_DURATION_SEC,
    RobotState,
    TaskPhase,
    TaskPriority,
)


@dataclass(frozen=True)
class Pose2D:
    """Represents a 2D planar pose (x, y, yaw)."""

    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    frame_id: str = "map"


@dataclass(frozen=True)
class PoseStamped:
    """Represents a 2D pose with timestamp and frame."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    frame_id: str = "map"
    timestamp_sec: float = 0.0


@dataclass(frozen=True)
class TaskGoal:
    """Represents the Goal definition of ExecuteTask.action."""

    task_id: str
    assignment_epoch: int
    pickup_pose: PoseStamped
    dropoff_pose: PoseStamped
    priority: int = TaskPriority.PRIORITY_LOW
    goal_uuid: str = ""


@dataclass(frozen=True)
class TaskFeedback:
    """Represents the Feedback definition of ExecuteTask.action."""

    current_phase: int
    current_pose: PoseStamped
    distance_to_goal: float = 0.0
    battery_soc: float = 100.0


@dataclass(frozen=True)
class TaskResult:
    """Represents the Result definition of ExecuteTask.action."""

    status: int
    completed_epoch: int
    completion_stamp_sec: float
    error_reason: str = ""


@dataclass(frozen=True)
class RobotStatusSnapshot:
    """Represents the data payload of RobotStatus.msg."""

    robot_id: str
    current_epoch: int
    state: int
    current_phase: int
    is_loaded: bool
    pose: PoseStamped
    battery_soc_percent: float
    battery_energy_wh: float
    current_task_id: str
    timestamp_sec: float


@dataclass(frozen=True)
class OdometryReading:
    """Represents an odometry measurement for motion and stop validation."""

    timestamp_sec: float
    linear_velocity: float
    angular_velocity: float
    pose: Optional[PoseStamped] = None


@dataclass(frozen=True)
class ClearErrorResult:
    """Represents the service response of ClearRobotError.srv."""

    accepted: bool
    reason: str
    resulting_state: int


@dataclass
class ExecutorConfig:
    """Configurable executor thresholds and durations.

    Note: These parameters are configurable and remain uncalibrated proposals.
    """

    linear_stop_threshold_m_s: float = DEFAULT_LINEAR_STOP_THRESHOLD_M_S
    angular_stop_threshold_rad_s: float = DEFAULT_ANGULAR_STOP_THRESHOLD_RAD_S
    odometry_freshness_sec: float = DEFAULT_ODOMETRY_FRESHNESS_SEC
    cancel_stop_timeout_sec: float = DEFAULT_CANCEL_STOP_TIMEOUT_SEC
    loading_duration_sec: float = DEFAULT_LOADING_DURATION_SEC
    unloading_duration_sec: float = DEFAULT_UNLOADING_DURATION_SEC
