"""Fleet Manager Domain Package.

Pure Python domain models, algorithms, and contracts decoupled from ROS 2 middleware.
"""

from .constants import (
    COMMUNICATION_ALERT_SEC,
    COMMUNICATION_WARNING_SEC,
    DEFAULT_CHARGE_TARGET_SOC,
    DEFAULT_DEPARTURE_MARGIN_M,
    DEFAULT_EMERGENCY_SOC,
    DEFAULT_LOW_SOC,
    DEFAULT_SAFETY_MARGIN_WH,
    DEFAULT_STATION_TOLERANCE_RADIUS_M,
    DISTANCE_TIE_EPSILON,
    MAX_PREEMPTIONS,
    ROBOT_STATUS_STALE_TIMEOUT_SEC,
    ReservationState,
    RobotState,
    StationType,
    TaskPhase,
    TaskPriority,
    TaskResultStatus,
    TaskStatus,
)
from .energy import (
    EnergyEligibilityResult,
    calculate_available_energy,
    calculate_emergency_reserve,
    calculate_escape_energy,
    calculate_remaining_energy,
    calculate_required_energy,
    check_energy_eligibility,
)
from .fleet_manager_core import FleetManagerCore
from .fleet_tracker import FleetTracker
from .models import (
    Assignment,
    Pose2D,
    PreemptionDecision,
    RobotBatterySpecs,
    RobotRecord,
    StationRecord,
    Task,
)
from .reservations import ReservationManager
from .scheduler import CandidateEvaluation, RouteDistanceProvider, Scheduler
from .task_queue import TaskQueue

__all__ = [
    # Constants
    "COMMUNICATION_ALERT_SEC",
    "COMMUNICATION_WARNING_SEC",
    "DEFAULT_CHARGE_TARGET_SOC",
    "DEFAULT_DEPARTURE_MARGIN_M",
    "DEFAULT_EMERGENCY_SOC",
    "DEFAULT_LOW_SOC",
    "DEFAULT_SAFETY_MARGIN_WH",
    "DEFAULT_STATION_TOLERANCE_RADIUS_M",
    "DISTANCE_TIE_EPSILON",
    "MAX_PREEMPTIONS",
    "ROBOT_STATUS_STALE_TIMEOUT_SEC",
    "ReservationState",
    "RobotState",
    "StationType",
    "TaskPhase",
    "TaskPriority",
    "TaskResultStatus",
    "TaskStatus",
    # Energy
    "EnergyEligibilityResult",
    "calculate_available_energy",
    "calculate_emergency_reserve",
    "calculate_escape_energy",
    "calculate_remaining_energy",
    "calculate_required_energy",
    "check_energy_eligibility",
    # Models
    "Assignment",
    "Pose2D",
    "PreemptionDecision",
    "RobotBatterySpecs",
    "RobotRecord",
    "StationRecord",
    "Task",
    # Domain Components
    "FleetManagerCore",
    "FleetTracker",
    "ReservationManager",
    "Scheduler",
    "RouteDistanceProvider",
    "CandidateEvaluation",
    "TaskQueue",
]
