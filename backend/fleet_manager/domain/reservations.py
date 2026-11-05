"""Station and parking slot reservation manager.

Implements strict single ownership, physical departure confirmation,
and BLOCKED containment rules (DOC-ARCH Sec 9, C3-DEC Sec 2.2).
"""

import logging
import math
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_DEPARTURE_MARGIN_M,
    DEFAULT_STATION_TOLERANCE_RADIUS_M,
    ReservationState,
    RobotState,
    StationType,
)
from .models import Pose2D, RobotRecord, StationRecord

logger = logging.getLogger(__name__)
_RECOVERED_STATES = set(RobotState) - {RobotState.STATE_ERROR}


class ReservationManager:
    """Manages charging station, parking slot, and safe waiting area reservations."""

    def __init__(self) -> None:
        self._stations: Dict[str, StationRecord] = {}

    def register_station(
        self,
        station_id: str,
        station_type: StationType,
        pose: Pose2D,
        tolerance_radius: float = DEFAULT_STATION_TOLERANCE_RADIUS_M,
        departure_margin: float = DEFAULT_DEPARTURE_MARGIN_M,
    ) -> StationRecord:
        """Register a new station in the fleet configuration."""
        if station_id in self._stations:
            raise ValueError(f"Station {station_id} already registered")
        record = StationRecord(
            station_id=station_id,
            station_type=station_type,
            pose=pose,
            tolerance_radius=tolerance_radius,
            departure_margin=departure_margin,
            state=ReservationState.FREE,
            reserved_by_robot_id=None,
            occupied_by_robot_id=None,
        )
        self._stations[station_id] = record
        return record

    def get_station(self, station_id: str) -> Optional[StationRecord]:
        """Get station record by id."""
        return self._stations.get(station_id)

    def list_stations(self, station_type: Optional[StationType] = None) -> List[StationRecord]:
        """List stations, optionally filtered by station_type."""
        if station_type is None:
            return list(self._stations.values())
        return [s for s in self._stations.values() if s.station_type == station_type]

    def get_station_by_robot(self, robot_id: str) -> Optional[StationRecord]:
        """Find station currently reserved or occupied by a given robot."""
        for station in self._stations.values():
            if station.reserved_by_robot_id == robot_id or station.occupied_by_robot_id == robot_id:
                return station
        return None

    def reserve(self, station_id: str, robot_id: str) -> bool:
        """Reserve a station for a robot.
        
        Requires station state to be FREE.
        Enforces single ownership.
        """
        station = self._stations.get(station_id)
        if station is None:
            return False

        # Can only reserve if strictly FREE
        if station.state != ReservationState.FREE:
            return False

        station.state = ReservationState.RESERVED
        station.reserved_by_robot_id = robot_id
        return True

    def mark_occupied(self, station_id: str, robot_id: str) -> bool:
        """Mark station as OCCUPIED when robot arrives/docks.
        
        Robot must be the one who reserved it or station must be free.
        """
        station = self._stations.get(station_id)
        if station is None:
            return False

        if station.state == ReservationState.BLOCKED:
            return False

        if station.state != ReservationState.FREE and not station.has_owner(robot_id):
            return False

        station.state = ReservationState.OCCUPIED
        station.reserved_by_robot_id = robot_id
        station.occupied_by_robot_id = robot_id
        return True

    def initiate_release(self, station_id: str, robot_id: str) -> bool:
        """Initiate release of a station (e.g. robot departing to execute a task).
        
        Transitions state to RELEASING.
        Does NOT set station to FREE yet; physical departure must be verified.
        """
        station = self._stations.get(station_id)
        if station is None:
            return False

        if station.state == ReservationState.BLOCKED:
            return False

        if not station.has_owner(robot_id):
            return False

        # Transition to RELEASING
        station.state = ReservationState.RELEASING
        return True

    def update_physical_departure(self, station_id: str, robot_pose: Pose2D) -> bool:
        """Check and update station physical departure.
        
        STRICT CONTRACT (C3-DEC §2.2):
        The station CANNOT be declared FREE until the robot has physically departed
        beyond tolerance radius plus margin:
        dist > tolerance_radius + departure_margin
        
        Returns True if station transitioned to FREE.
        """
        station = self._stations.get(station_id)
        if station is None:
            return False

        if station.state == ReservationState.BLOCKED:
            return False

        if station.state not in (ReservationState.RELEASING, ReservationState.OCCUPIED, ReservationState.RESERVED):
            return False

        if station.is_physically_departed(robot_pose):
            self._free(station)
            return True

        # Still physically occupied within tolerance
        return False

    def mark_blocked(
        self, station_id: str, robot_id: str, *,
        session_id: Optional[str] = None, error_status_ns: Optional[int] = None,
    ) -> bool:
        """Mark station as BLOCKED due to an error on the occupying/reserving robot.
        
        STRICT CONTRACT (C3-DEC §2.2):
        When a robot enters STATE_ERROR, its physical resource is BLOCKED
        and cannot be allocated to another robot until operator intervention.
        A zero error timestamp discards the recovery fence; None preserves it.
        """
        station = self._stations.get(station_id)
        if station is None:
            return False
        if station.state == ReservationState.FREE:
            station.reserved_by_robot_id = station.occupied_by_robot_id = robot_id
        elif not station.has_owner(robot_id):
            return False

        if station.state != ReservationState.BLOCKED:
            station.blocked_session_id = session_id
        if error_status_ns == 0:
            station.blocked_after_ns = 0
        elif error_status_ns is not None and session_id and station.blocked_session_id == session_id:
            station.blocked_after_ns = max(station.blocked_after_ns, error_status_ns)
        station.state = ReservationState.BLOCKED
        return True

    def unblock(
        self, station_id: str, robot: Optional[RobotRecord] = None, *, now: float = 0.0,
    ) -> bool:
        """Recover a blocked station using its owner's accepted RobotStatus."""
        station = self._stations.get(station_id)
        if station is None or station.state != ReservationState.BLOCKED:
            reason = "station is not blocked"
        elif robot is None or not station.has_owner(robot.robot_id):
            reason = "station owner is required"
        elif robot.session_blocked or not robot.session_id or robot.session_id != station.blocked_session_id:
            reason = "owner session cannot be verified"
        elif (robot.state not in _RECOVERED_STATES or not station.blocked_after_ns
              or robot.last_pose_sample_ns <= station.blocked_after_ns
              or not math.isfinite(now)
              or not robot.last_status_received_at <= now <= robot.station_pose_valid_until
              or robot.is_stale(now)):
            reason = "fresh pose after owner error recovery is required"
        elif not station.is_physically_departed(robot.pose):
            reason = "physical departure could not be verified"
        else:
            self._free(station)
            return True
        logger.warning("UNBLOCK rejected station=%s reason=%s", station_id, reason)
        return False

    @staticmethod
    def _free(station: StationRecord) -> None:
        station.state = ReservationState.FREE
        station.reserved_by_robot_id = None
        station.occupied_by_robot_id = None
        station.blocked_session_id = None
        station.blocked_after_ns = 0

    def find_nearest_free_station(
        self,
        current_pose: Pose2D,
        station_type: StationType,
    ) -> Optional[StationRecord]:
        """Find nearest strictly FREE station of the specified type."""
        candidates = [
            s for s in self._stations.values()
            if s.station_type == station_type and s.state == ReservationState.FREE
        ]
        if not candidates:
            return None

        candidates.sort(key=lambda s: current_pose.distance_to(s.pose))
        return candidates[0]
