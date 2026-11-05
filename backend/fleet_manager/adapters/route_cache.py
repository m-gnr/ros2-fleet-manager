"""Consumer-owned Nav2 route cache (C3.3.2-DEC-02)."""

from dataclasses import dataclass
import math
import time

from ..domain.constants import (
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

    def matches_start(self, pose: Pose2D) -> bool:
        return (
            pose.frame_id == "map"
            and pose.has_finite_coordinates()
            and self.start_displacement(pose) <= ROUTE_CACHE_POSITION_TOLERANCE_M
            and snap_coordinate(pose.x) == self.cell_start_x
            and snap_coordinate(pose.y) == self.cell_start_y
        )

    def start_displacement(self, pose: Pose2D) -> float:
        return math.hypot(pose.x - self.cell_start_x, pose.y - self.cell_start_y)


@dataclass(frozen=True)
class RouteCacheEntry:
    distance: float
    timestamp: float
    starts_at_robot: bool


def valid_distance(distance: float | None) -> bool:
    try:
        return type(distance) in (int, float) and math.isfinite(distance) and distance >= 0
    except OverflowError:
        return False


class RouteCache:
    def __init__(self, ttl_sec: float = ROUTE_CACHE_TTL_SEC) -> None:
        self.ttl_sec = ttl_sec
        self.map_revision = "v1.0"
        self.map_generation = 0
        self._entries: dict[RouteCacheKey, RouteCacheEntry] = {}

    def __len__(self) -> int:
        return len(self._entries)

    def key(self, robot_id: str, start: Pose2D, goal: Pose2D, map_revision: str | None = None):
        if (not robot_id or start.frame_id != "map" or goal.frame_id != "map"
                or not start.has_finite_coordinates() or not goal.has_finite_coordinates()):
            return None
        if map_revision is not None and map_revision != self.map_revision:
            return None
        try:
            return RouteCacheKey(
                robot_id,
                snap_coordinate(start.x), snap_coordinate(start.y),
                snap_coordinate(goal.x), snap_coordinate(goal.y),
                self.map_revision,
            )
        except OverflowError:
            return None

    def get(self, robot_id, start_pose, goal_pose, map_revision=None, now=None):
        """Read a valid distance without mutating the cache during scheduling."""
        key = self.key(robot_id, start_pose, goal_pose, map_revision)
        entry = self._entries.get(key)
        current_time = time.monotonic() if now is None else now
        if entry is None or not 0 <= current_time - entry.timestamp < self.ttl_sec:
            return None
        if not key.matches_start(start_pose):
            return None
        return entry.distance

    def put(self, robot_id, start_pose, goal_pose, distance, map_revision=None, now=None,
            *, starts_at_robot=True):
        key = self.key(robot_id, start_pose, goal_pose, map_revision)
        timestamp = time.monotonic() if now is None else now
        if key is None or not math.isfinite(timestamp):
            return
        previous = self._entries.get(key)
        if previous is not None and timestamp < previous.timestamp:
            return
        if valid_distance(distance):
            self._entries[key] = RouteCacheEntry(distance, timestamp, starts_at_robot)
        else:
            self._entries.pop(key, None)

    def stored_keys(self, keys):
        return self._entries.keys() & keys

    def discard(self, keys) -> int:
        removed = 0
        for key in keys:
            if self._entries.pop(key, None) is not None:
                removed += 1
        return removed

    def invalidate_for_robot_movement(self, robot_id: str, current_pose: Pose2D) -> int:
        """Discard robot-origin entries when the start-cell displacement exceeds tolerance."""
        return self.discard([
            key for key, entry in self._entries.items()
            if key.robot_id == robot_id and entry.starts_at_robot
            and key.start_displacement(current_pose) > ROUTE_CACHE_POSITION_TOLERANCE_M
        ])

    def invalidate_map_revision(self, current_map_revision: str) -> int:
        if current_map_revision != self.map_revision:
            self.map_revision = current_map_revision
            self.map_generation += 1
        return self.discard([key for key in self._entries if key.map_revision != current_map_revision])

    def invalidate_all(self) -> None:
        self.map_generation += 1
        self._entries.clear()

    def prune_expired(self, now=None) -> int:
        current_time = time.monotonic() if now is None else now
        return self.discard([
            key for key, entry in self._entries.items()
            if current_time - entry.timestamp >= self.ttl_sec
        ])


class CachedRouteDistanceProvider(RouteDistanceProvider):
    """Synchronous robot-specific lookup. A cache miss has no fallback."""

    def __init__(self, cache: RouteCache, clock=time.monotonic) -> None:
        self.cache = cache
        self.clock = clock

    def get_path_distance(self, robot_id: str, start: Pose2D, goal: Pose2D) -> float | None:
        return self.cache.get(robot_id, start, goal, now=self.clock())
