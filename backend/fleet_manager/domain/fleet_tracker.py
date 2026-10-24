"""Robot fleet telemetry tracking and freshness monitor.

Adheres strictly to:
- C3-DEC-01: RobotStatus 2.0s stale threshold and immediate exclusion from assignment.
- C3-DEC-02: Communication loss monitoring without automatic FAILED/ERROR.
- Executor physical state authority: Fleet Manager holds an updated replica.
"""

from typing import Dict, List, Optional, Tuple

from .constants import (
    COMMUNICATION_ALERT_SEC,
    COMMUNICATION_WARNING_SEC,
    ROBOT_STATUS_STALE_TIMEOUT_SEC,
    RobotState,
)
from .models import Pose2D, RobotBatterySpecs, RobotRecord


class FleetTracker:
    """Tracks robot status telemetry and maintains the fleet operational registry."""

    def __init__(self) -> None:
        self._robots: Dict[str, RobotRecord] = {}

    def register_robot(
        self,
        robot_id: str,
        specs: Optional[RobotBatterySpecs] = None,
        initial_pose: Optional[Pose2D] = None,
    ) -> RobotRecord:
        """Register a robot from fleet configuration."""
        if robot_id in self._robots:
            raise ValueError(f"Robot {robot_id} already registered")

        record = RobotRecord(
            robot_id=robot_id,
            specs=specs or RobotBatterySpecs(),
            pose=initial_pose or Pose2D(),
            state=RobotState.STATE_IDLE,
            idle_start_timestamp=0.0,
        )
        self._robots[robot_id] = record
        return record

    def get_robot(self, robot_id: str) -> Optional[RobotRecord]:
        """Lookup robot record by id."""
        return self._robots.get(robot_id)

    def list_robots(self) -> List[RobotRecord]:
        """List all registered robot records."""
        return list(self._robots.values())

    def update_robot_status(
        self,
        robot_id: str,
        state: int,
        current_phase: int,
        is_loaded: bool,
        pose: Pose2D,
        battery_soc_percent: float,
        battery_energy_wh: float,
        current_epoch: int,
        current_task_id: Optional[str],
        timestamp_sec: float,
    ) -> Optional[RobotRecord]:
        """Update robot record from incoming RobotStatus message (5 Hz).
        
        The physical state authority belongs to Robot Executor.
        Fleet Manager updates its replica and tracks idle timestamps.
        """
        robot = self._robots.get(robot_id)
        if robot is None:
            return None

        # Track idle transition for tie-breaking
        if state == RobotState.STATE_IDLE and robot.state != RobotState.STATE_IDLE:
            robot.idle_start_timestamp = timestamp_sec
        elif state != RobotState.STATE_IDLE:
            robot.idle_start_timestamp = 0.0

        robot.state = state
        robot.current_phase = current_phase
        robot.is_loaded = is_loaded
        robot.pose = pose
        robot.battery_soc_percent = battery_soc_percent
        robot.battery_energy_wh = battery_energy_wh
        robot.current_epoch = current_epoch
        robot.current_task_id = current_task_id
        robot.last_status_received_at = timestamp_sec

        return robot

    def is_stale(
        self,
        robot_id: str,
        current_time: float,
        threshold: float = ROBOT_STATUS_STALE_TIMEOUT_SEC,
    ) -> bool:
        """Return True if robot telemetry has not been updated within threshold."""
        robot = self._robots.get(robot_id)
        if robot is None:
            return True
        return robot.is_stale(current_time, threshold=threshold)

    def get_eligible_idle_robots(self, current_time: float) -> List[RobotRecord]:
        """Return idle robots that are fresh and ready for task evaluation.
        
        STRICT CONTRACT (C3-DEC-01):
        Robots not updated within 2.0 seconds are STALE and must be excluded.
        """
        eligible = []
        for robot in self._robots.values():
            if robot.is_eligible_for_new_assignment(current_time):
                eligible.append(robot)
        return eligible

    def check_communication_health(
        self,
        current_time: float,
    ) -> List[Tuple[str, str, float]]:
        """Check communication delays for all robots.
        
        Returns list of (robot_id, severity, elapsed_time_sec).
        Severity can be:
        - "WARNING" (>= 5.0s, C3-DEC-02)
        - "ALERT" (>= 10.0s, C3-DEC-02 notice)
        
        STRICT CONTRACT (C3-DEC-02):
        Communication loss at 10.0s DOES NOT automatically fail the active task
        or mark the robot as ERROR.
        """
        notices = []
        for r_id, robot in self._robots.items():
            if robot.last_status_received_at <= 0.0:
                continue
            dt = current_time - robot.last_status_received_at
            if dt >= COMMUNICATION_ALERT_SEC:
                notices.append((r_id, "ALERT", dt))
            elif dt >= COMMUNICATION_WARNING_SEC:
                notices.append((r_id, "WARNING", dt))
        return notices
