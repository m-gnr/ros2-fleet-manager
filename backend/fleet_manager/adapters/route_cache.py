"""Nav2 global route cache with cell snapping, TTL, and invalidation rules.

Conforms strictly to C3.3.2-DEC-02:
- Grid resolution: 0.20m cells (round(x / 0.20) * 0.20)
- Cache key: (robot_id, cell_start_x, cell_start_y, cell_goal_x, cell_goal_y, map_revision)
- TTL: 30.0s monotonic time
- Invalidation triggers:
  1. Robot current pose departs > 0.20m from start cell
  2. Goal pose or map revision changes
  3. Task assigned / cancelled / dequeued
  4. Monotonic TTL expires
- Euclidean ban: Missing / failed / expired route returns strictly None.
"""

from dataclasses import dataclass
import math
import time
from typing import Dict, Optional, Tuple

from ..domain.constants import (
    NAV2_ROUTE_TIMEOUT_SEC,
    ROUTE_CACHE_GRID_RESOLUTION_M,
    ROUTE_CACHE_POSITION_TOLERANCE_M,
    ROUTE_CACHE_TTL_SEC,
)
from ..domain.models import Pose2D
from ..domain.scheduler import RouteDistanceProvider


def snap_coordinate(value: float, resolution: float = ROUTE_CACHE_GRID_RESOLUTION_M) -> float:
    """Snap coordinate to nearest grid cell resolution."""
    return round(round(value / resolution) * resolution, 4)


@dataclass(frozen=True)
class RouteCacheKey:
    robot_id: str
    cell_start_x: float
    cell_start_y: float
    cell_goal_x: float
    cell_goal_y: float
    map_revision: str


@dataclass(frozen=True)
class RouteCacheEntry:
    distance: float
    timestamp: float
    cell_start_x: float
    cell_start_y: float
    map_revision: str


class RouteCache:
    """Thread-safe route cache with geometric snapping and monotonic TTL."""

    def __init__(self, ttl_sec: float = ROUTE_CACHE_TTL_SEC) -> None:
        self.ttl_sec = ttl_sec
        self._entries: Dict[RouteCacheKey, RouteCacheEntry] = {}

    def get(
        self,
        robot_id: str,
        start_pose: Pose2D,
        goal_pose: Pose2D,
        map_revision: str = "v1.0",
        now: Optional[float] = None,
    ) -> Optional[float]:
        """Lookup cached route distance.
        
        Returns distance in metres if valid, or None if missing / expired / invalid.
        Strictly enforces NO Euclidean fallback (C3.3.2-DEC-02).
        """
        current_now = time.monotonic() if now is None else now
        cell_sx = snap_coordinate(start_pose.x)
        cell_sy = snap_coordinate(start_pose.y)
        cell_gx = snap_coordinate(goal_pose.x)
        cell_gy = snap_coordinate(goal_pose.y)

        key = RouteCacheKey(
            robot_id=robot_id,
            cell_start_x=cell_sx,
            cell_start_y=cell_sy,
            cell_goal_x=cell_gx,
            cell_goal_y=cell_gy,
            map_revision=map_revision,
        )

        entry = self._entries.get(key)
        if entry is None and not robot_id:
            for k, v in self._entries.items():
                if (
                    k.cell_start_x == cell_sx
                    and k.cell_start_y == cell_sy
                    and k.cell_goal_x == cell_gx
                    and k.cell_goal_y == cell_gy
                    and k.map_revision == map_revision
                ):
                    entry = v
                    key = k
                    break

        if entry is None:
            return None

        # Check Monotonic TTL
        if (current_now - entry.timestamp) > self.ttl_sec:
            del self._entries[key]
            return None

        # Check displacement from start cell (> 0.20m triggers invalidation)
        disp = math.hypot(start_pose.x - entry.cell_start_x, start_pose.y - entry.cell_start_y)
        if disp > ROUTE_CACHE_POSITION_TOLERANCE_M:
            del self._entries[key]
            return None

        return entry.distance

    def put(
        self,
        robot_id: str,
        start_pose: Pose2D,
        goal_pose: Pose2D,
        distance: float,
        map_revision: str = "v1.0",
        now: Optional[float] = None,
    ) -> None:
        """Store route calculation result in cache."""
        current_now = time.monotonic() if now is None else now
        cell_sx = snap_coordinate(start_pose.x)
        cell_sy = snap_coordinate(start_pose.y)
        cell_gx = snap_coordinate(goal_pose.x)
        cell_gy = snap_coordinate(goal_pose.y)

        key = RouteCacheKey(
            robot_id=robot_id,
            cell_start_x=cell_sx,
            cell_start_y=cell_sy,
            cell_goal_x=cell_gx,
            cell_goal_y=cell_gy,
            map_revision=map_revision,
        )

        self._entries[key] = RouteCacheEntry(
            distance=distance,
            timestamp=current_now,
            cell_start_x=cell_sx,
            cell_start_y=cell_sy,
            map_revision=map_revision,
        )

    def invalidate_for_robot_movement(self, robot_id: str, current_pose: Pose2D) -> int:
        """Invalidate entries where robot has departed > 0.20m from start cell."""
        to_remove = []
        for key, entry in self._entries.items():
            if key.robot_id == robot_id:
                disp = math.hypot(current_pose.x - entry.cell_start_x, current_pose.y - entry.cell_start_y)
                if disp > ROUTE_CACHE_POSITION_TOLERANCE_M:
                    to_remove.append(key)
        for k in to_remove:
            del self._entries[k]
        return len(to_remove)

    def invalidate_map_revision(self, current_map_revision: str) -> int:
        """Invalidate all entries with different map revision."""
        to_remove = [k for k, v in self._entries.items() if v.map_revision != current_map_revision]
        for k in to_remove:
            del self._entries[k]
        return len(to_remove)

    def invalidate_all(self) -> None:
        """Clear entire cache."""
        self._entries.clear()

    def prune_expired(self, now: Optional[float] = None) -> int:
        """Prune TTL-expired entries."""
        current_now = time.monotonic() if now is None else now
        to_remove = [k for k, v in self._entries.items() if (current_now - v.timestamp) > self.ttl_sec]
        for k in to_remove:
            del self._entries[k]
        return len(to_remove)


class CachedRouteDistanceProvider(RouteDistanceProvider):
    """Synchronous read-only distance provider backed by RouteCache."""

    def __init__(
        self,
        cache: RouteCache,
        robot_id: str = "",
        map_revision: str = "v1.0",
        clock=time.monotonic,
    ) -> None:
        self.cache = cache
        self.robot_id = robot_id
        self.map_revision = map_revision
        self.clock = clock

    def get_path_distance(self, start: Pose2D, goal: Pose2D) -> Optional[float]:
        """Query cache synchronously without side-effects or network calls.
        
        Returns distance in metres, or None if not cached / expired.
        Strictly NO Euclidean fallback.
        """
        return self.cache.get(
            robot_id=self.robot_id,
            start_pose=start,
            goal_pose=goal,
            map_revision=self.map_revision,
            now=self.clock(),
        )

    def update_cache(
        self,
        robot_id: str,
        start_pose: Pose2D,
        goal_pose: Pose2D,
        distance: float,
        map_revision: str = "v1.0",
        timestamp: Optional[float] = None,
    ) -> None:
        """Update cache from ROUTE_RESOLVED event."""
        self.cache.put(
            robot_id=robot_id,
            start_pose=start_pose,
            goal_pose=goal_pose,
            distance=distance,
            map_revision=map_revision,
            now=timestamp,
        )
