"""Station and parking slot reservation manager.

Implements strict single ownership, physical departure confirmation,
and BLOCKED containment rules (DOC-ARCH Sec 9, C3-DEC Sec 2.2).
"""

from typing import Dict, List, Optional

from .constants import (
    DEFAULT_DEPARTURE_MARGIN_M,
    DEFAULT_STATION_TOLERANCE_RADIUS_M,
    ReservationState,
    StationType,
)
from .models import Pose2D, StationRecord


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

        if station.state == ReservationState.RESERVED and station.reserved_by_robot_id != robot_id:
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

        if station.occupied_by_robot_id != robot_id and station.reserved_by_robot_id != robot_id:
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

        if not station.is_physically_occupied(robot_pose):
            # Robot has physically departed!
            station.state = ReservationState.FREE
            station.reserved_by_robot_id = None
            station.occupied_by_robot_id = None
            return True

        # Still physically occupied within tolerance
        return False

    def mark_blocked(self, station_id: str, robot_id: str) -> bool:
        """Mark station as BLOCKED due to an error on the occupying/reserving robot.
        
        STRICT CONTRACT (C3-DEC §2.2):
        When a robot enters STATE_ERROR, its physical resource is BLOCKED
        and cannot be allocated to another robot until operator intervention.
        """
        station = self._stations.get(station_id)
        if station is None:
            return False

        station.state = ReservationState.BLOCKED
        station.reserved_by_robot_id = robot_id
        station.occupied_by_robot_id = robot_id
        return True

    def unblock(self, station_id: str) -> bool:
        """Operator action to unblock a station after clearing error."""
        station = self._stations.get(station_id)
        if station is None:
            return False

        if station.state == ReservationState.BLOCKED:
            station.state = ReservationState.FREE
            station.reserved_by_robot_id = None
            station.occupied_by_robot_id = None
            return True
        return False

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
