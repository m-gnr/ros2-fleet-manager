"""Constants and enumerations for Fleet Manager domain.

These definitions strictly adhere to approved architecture decisions:
- DOC-ARCH-2026-10-23-FINAL (DOC-ARCH Section 6, 7, 9, 11)
- C3-DEC-01..04 (docs/c3-fleet-manager-decisions-2026-10-24.md)
- Interfaces: ExecuteTask.action, RobotStatus.msg, ClearRobotError.srv
"""

from enum import Enum, IntEnum


class TaskPriority(IntEnum):
    """Task priority values strictly mirroring ExecuteTask.action."""

    PRIORITY_HIGH = 1
    PRIORITY_MEDIUM = 2
    PRIORITY_LOW = 3


class RobotState(IntEnum):
    """Robot operational states strictly mirroring RobotStatus.msg."""

    STATE_IDLE = 1
    STATE_EXECUTING_TASK = 2
    STATE_CHARGING = 3
    STATE_RETURNING_TO_CHARGE = 4
    STATE_RETURNING_TO_PARK = 5
    STATE_ERROR = 6


class TaskPhase(IntEnum):
    """Task execution phases reported by Robot Executor via action feedback."""

    PHASE_NONE = 0
    PHASE_MOVING_TO_PICKUP = 1
    PHASE_LOADING = 2
    PHASE_MOVING_TO_DROPOFF = 3
    PHASE_UNLOADING = 4


class TaskResultStatus(IntEnum):
    """Terminal action result statuses matching ExecuteTask.action."""

    STATUS_SUCCEEDED = 1
    STATUS_FAILED = 2
    STATUS_PREEMPTED = 3


class TaskStatus(str, Enum):
    """Lifecycle states of a task in Fleet Manager domain."""

    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PREEMPTED = "PREEMPTED"
    CANCELED = "CANCELED"


class ReservationState(str, Enum):
    """Lifecycle states of station and parking slot reservations."""

    FREE = "FREE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    RELEASING = "RELEASING"
    BLOCKED = "BLOCKED"


class StationType(str, Enum):
    """Station classification matching fleet configuration."""

    CHARGING = "CHARGING"
    PARKING = "PARKING"
    SAFE_WAITING = "SAFE_WAITING"


# Architectural limits and locked policy thresholds
MAX_PREEMPTIONS = 2  # N=2 preemption protection limit (Karar 08, DOC-ARCH Sec 6.2)
ROBOT_STATUS_STALE_TIMEOUT_SEC = 2.0  # C3-DEC-01 locked stale threshold
COMMUNICATION_WARNING_SEC = 5.0  # C3-DEC-02 warning threshold
COMMUNICATION_ALERT_SEC = 10.0  # C3-DEC-02 notice threshold (no automatic FAILED/ERROR)
DISTANCE_TIE_EPSILON = 1e-4  # C3-DEC-03 tie-break delta threshold (metres)
DEFAULT_CHARGE_TARGET_SOC = 80.0  # Politika P11 (80% target SOC)
DEFAULT_EMERGENCY_SOC = 8.0  # Section 7 emergency reserve threshold (%)
DEFAULT_LOW_SOC = 25.0  # Section 10 representative low battery threshold (%)
DEFAULT_SAFETY_MARGIN_WH = 10.0  # Section 7 representative energy safety margin (Wh)
DEFAULT_STATION_TOLERANCE_RADIUS_M = 0.30  # Station dock tolerance radius (metres)
DEFAULT_DEPARTURE_MARGIN_M = 0.05  # Departure verification buffer margin (metres)

# C3.3.2 approved timeouts and cache specifications (C3.3.2-DEC-01 & DEC-02)
GOAL_ACCEPT_TIMEOUT_SEC = 5.0  # Monotonic timeout for ExecuteTask goal acceptance
CANCEL_RESPONSE_TIMEOUT_SEC = 3.0  # Monotonic timeout for preemption cancel response
NAV2_ROUTE_TIMEOUT_SEC = 2.0  # Monotonic timeout for Nav2 ComputePathToPose query
ROUTE_CACHE_GRID_RESOLUTION_M = 0.20  # Coordinate grid snapping cell size (metres)
ROUTE_CACHE_TTL_SEC = 30.0  # Route cache maximum monotonic time-to-live (seconds)
ROUTE_CACHE_POSITION_TOLERANCE_M = 0.20  # Robot displacement invalidation threshold (metres)
OUTBOX_STATE_HELD_FOR_REVIEW = "HELD_FOR_REVIEW"

