"""Domain models for ROS 2 Fleet Manager core.

These models are completely decoupled from ROS 2 middleware and UI dependencies,
allowing pure Python verification, deterministic test execution, and strict
conformance to DOC-ARCH-2026-10-23-FINAL and C3 decisions.
"""

from dataclasses import dataclass, field
import math
from typing import Optional

from .constants import (
    DEFAULT_DEPARTURE_MARGIN_M,
    DEFAULT_STATION_TOLERANCE_RADIUS_M,
    MAX_PREEMPTIONS,
    ROBOT_STATUS_STALE_TIMEOUT_SEC,
    ReservationState,
    RobotState,
    StationType,
    TaskPhase,
    TaskPriority,
    TaskStatus,
)


@dataclass(frozen=True)
class Pose2D:
    """Planar 2D pose in map coordinate frame."""

    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0
    frame_id: str = "map"

    def distance_to(self, other: "Pose2D") -> float:
        """Calculate Euclidean straight-line distance (for departure/proximity only)."""
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass
class Task:
    """Fleet transport task representation."""

    task_id: str
    pickup_pose: Pose2D
    dropoff_pose: Pose2D
    priority: int = TaskPriority.PRIORITY_LOW
    created_at: float = 0.0
    status: TaskStatus = TaskStatus.QUEUED
    preemption_count: int = 0
    assigned_robot_id: Optional[str] = None
    assignment_epoch: Optional[int] = None
    goal_uuid: Optional[str] = None

    def can_be_preempted(self) -> bool:
        """Check whether task can be preempted under safe preemption rules.
        
        Rules:
        - Only LOW and MEDIUM tasks can be preempted.
        - HIGH tasks can NEVER be preempted.
        - If preemption_count >= MAX_PREEMPTIONS (N=2), task is protected!
        """
        if self.priority == TaskPriority.PRIORITY_HIGH:
            return False
        if self.preemption_count >= MAX_PREEMPTIONS:
            return False
        return True


@dataclass(frozen=True)
class RobotBatterySpecs:
    """Robot physical battery characteristics from fleet.yaml."""

    usable_capacity_wh: float = 100.0
    consumption_wh_per_meter: float = 0.20
    idle_power_w: float = 2.0
    charge_power_w: float = 20.0


@dataclass
class RobotRecord:
    """Fleet Manager's internal replica of robot state and telemetry.
    
    The physical robot state authority belongs strictly to Robot Executor.
    Fleet Manager stores this record as an updated reflection of RobotStatus messages.
    """

    robot_id: str
    specs: RobotBatterySpecs = field(default_factory=RobotBatterySpecs)
    state: int = RobotState.STATE_IDLE
    current_phase: int = TaskPhase.PHASE_NONE
    is_loaded: bool = False
    pose: Pose2D = field(default_factory=Pose2D)
    battery_soc_percent: float = 100.0
    battery_energy_wh: float = 100.0
    current_epoch: int = 0
    current_task_id: Optional[str] = None
    active_goal_uuid: Optional[str] = None
    last_status_received_at: float = 0.0
    idle_start_timestamp: float = 0.0

    def is_stale(self, current_time: float, threshold: float = ROBOT_STATUS_STALE_TIMEOUT_SEC) -> bool:
        """Return True if robot status has not been updated within threshold seconds (C3-DEC-01)."""
        if self.last_status_received_at <= 0.0:
            return True
        return (current_time - self.last_status_received_at) > threshold

    def idle_duration(self, current_time: float) -> float:
        """Return elapsed seconds robot has been continuously in STATE_IDLE."""
        if self.state != RobotState.STATE_IDLE or self.idle_start_timestamp <= 0.0:
            return 0.0
        return max(0.0, current_time - self.idle_start_timestamp)

    def is_eligible_for_new_assignment(self, current_time: float) -> bool:
        """Basic operational eligibility check before route and energy evaluations."""
        if self.is_stale(current_time):
            return False
        if self.state == RobotState.STATE_ERROR:
            return False
        if self.is_loaded:
            return False
        # Can be assigned if IDLE or RETURNING_TO_PARK
        if self.state in (RobotState.STATE_IDLE, RobotState.STATE_RETURNING_TO_PARK):
            return True
        return False


@dataclass
class StationRecord:
    """Charging station or parking slot reservation tracking."""

    station_id: str
    station_type: StationType
    pose: Pose2D
    tolerance_radius: float = DEFAULT_STATION_TOLERANCE_RADIUS_M
    departure_margin: float = DEFAULT_DEPARTURE_MARGIN_M
    state: ReservationState = ReservationState.FREE
    reserved_by_robot_id: Optional[str] = None
    occupied_by_robot_id: Optional[str] = None

    def is_physically_occupied(self, robot_pose: Pose2D) -> bool:
        """Check whether robot is within tolerance radius plus margin of the station."""
        dist = self.pose.distance_to(robot_pose)
        return dist <= (self.tolerance_radius + self.departure_margin)


@dataclass(frozen=True)
class Assignment:
    """Represents a dispatch assignment contract between FM and Executor."""

    task_id: str
    robot_id: str
    assignment_epoch: int
    goal_uuid: str
    pickup_pose: Pose2D
    dropoff_pose: Pose2D
    priority: int
    assigned_at: float


@dataclass(frozen=True)
class PreemptionDecision:
    """Represents a preemption action decision."""

    high_task: Task
    victim_task: Task
    robot_id: str
    victim_goal_uuid: str
    target_epoch: int
    reason: str
