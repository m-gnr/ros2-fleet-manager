"""Asynchronous, monotonic-time Nav2 ComputePathToPose queries."""

import asyncio
import logging
import math
import time
from typing import Any, Callable

from ..domain.constants import NAV2_ROUTE_TIMEOUT_SEC
from ..domain.models import Pose2D
from .action_client import yaw_to_quaternion
from .route_cache import RouteCache, valid_distance

logger = logging.getLogger(__name__)
ROS_GOAL_SUCCEEDED = 4  # action_msgs/msg/GoalStatus.STATUS_SUCCEEDED


def calculate_path_length(path_msg: Any) -> float | None:
    """Measure a valid multi-pose planar path in metres."""
    try:
        points = [(pose.pose.position.x, pose.pose.position.y) for pose in path_msg.poses]
        if len(points) < 2 or not all(math.isfinite(x) and math.isfinite(y) for x, y in points):
            return None
        distance = sum(math.hypot(bx - ax, by - ay) for (ax, ay), (bx, by) in zip(points, points[1:]))
        return distance if valid_distance(distance) else None
    except (AttributeError, TypeError, OverflowError):
        return None


def _make_goal(start: Pose2D, goal: Pose2D, planner_id: str, use_start: bool):
    from geometry_msgs.msg import PoseStamped
    from nav2_msgs.action import ComputePathToPose

    def stamped(pose):
        message = PoseStamped()
        message.header.frame_id = pose.frame_id
        message.pose.position.x = float(pose.x)
        message.pose.position.y = float(pose.y)
        orientation = message.pose.orientation
        orientation.x, orientation.y, orientation.z, orientation.w = yaw_to_quaternion(pose.yaw)
        return message

    request = ComputePathToPose.Goal()
    request.start = stamped(start)
    request.goal = stamped(goal)
    request.planner_id = planner_id
    request.use_start = use_start
    return request


def _cancel_if_accepted(send_future):
    try:
        handle = send_future.result()
        if handle is not None and handle.accepted:
            handle.cancel_goal_async()
    except Exception:
        logger.debug("Could not cancel late Nav2 goal", exc_info=True)


class AsyncRouteResolver:
    def __init__(
        self,
        cache: RouteCache,
        clock: Callable[[], float] = time.monotonic,
        timeout_sec: float = NAV2_ROUTE_TIMEOUT_SEC,
    ) -> None:
        self.cache = cache
        self.clock = clock
        self.timeout_sec = timeout_sec
        self._action_clients: dict[str, Any] = {}

    def register_robot_client(self, robot_id: str, client: Any) -> None:
        self._action_clients[robot_id] = client

    async def _wait_until(self, future, deadline):
        while not future.done() and self.clock() < deadline:
            await asyncio.sleep(0.02)
        if self.clock() >= deadline:
            raise TimeoutError
        return future.result()

    async def compute_route(
        self, robot_id: str, start_pose: Pose2D, goal_pose: Pose2D,
        *, planner_id: str = "GridBased", use_start: bool = True,
    ) -> float | None:
        """Query one robot's planner. The caller owns any cache publication."""
        client = self._action_clients.get(robot_id)
        if client is None or self.cache.key(robot_id, start_pose, goal_pose) is None:
            return None
        send_future = None
        try:
            if not client.server_is_ready():
                return None
            request = _make_goal(start_pose, goal_pose, planner_id, use_start)
            deadline = self.clock() + self.timeout_sec
            send_future = client.send_goal_async(request)
            handle = await self._wait_until(send_future, deadline)
            if handle is None or not handle.accepted:
                return None
            response = await self._wait_until(handle.get_result_async(), deadline)
            if response is None or response.status != ROS_GOAL_SUCCEEDED:
                return None
            path = response.result.path
            if path.header.frame_id != goal_pose.frame_id:
                return None
            return calculate_path_length(path)
        except (TimeoutError, asyncio.CancelledError) as exc:
            if send_future is not None:
                # Goal acceptance can arrive after the original query deadline.
                send_future.add_done_callback(_cancel_if_accepted)
            if isinstance(exc, asyncio.CancelledError):
                raise
            logger.warning("Nav2 route query timed out robot=%s after %.1fs", robot_id, self.timeout_sec)
        except Exception:
            logger.warning("Nav2 route query failed robot=%s", robot_id, exc_info=True)
        return None

    async def query_route(
        self, robot_id: str, start_pose: Pose2D, goal_pose: Pose2D,
        map_revision: str | None = None, planner_id: str = "GridBased", use_start: bool = True,
    ) -> float | None:
        """Standalone planner probe used without a FleetEventLoop."""
        if robot_id not in self._action_clients:
            return None
        revision = self.cache.map_revision if map_revision is None else map_revision
        if revision != self.cache.map_revision:
            return None
        generation = self.cache.map_generation
        cached = self.cache.get(robot_id, start_pose, goal_pose, revision, now=self.clock())
        if cached is not None:
            return cached
        distance = await self.compute_route(
            robot_id, start_pose, goal_pose, planner_id=planner_id, use_start=use_start,
        )
        if generation != self.cache.map_generation or revision != self.cache.map_revision:
            return None
        self.cache.put(robot_id, start_pose, goal_pose, distance, revision, now=self.clock())
        return distance
