"""Nav2 ComputePathToPose asynchronous route query resolver.

Conforms strictly to:
- C3.3.2-DEC-01: 2.0s monotonic timeout for Nav2 route queries.
- C3.3.2-DEC-02: Route caching, cell snapping (0.20m), Euclidean fallback ban.
- C3.3.2-DEC-06: Asynchronous queries executed outside SQLite transactions.
"""

import asyncio
import logging
import math
import time
from typing import Any, Callable, Optional, Tuple

from ..domain.constants import NAV2_ROUTE_TIMEOUT_SEC
from ..domain.models import Pose2D
from ..event_loop import Event
from .action_client import yaw_to_quaternion
from .route_cache import RouteCache

logger = logging.getLogger(__name__)


def calculate_path_length(path_msg: Any) -> float:
    """Calculate Euclidean path distance from nav_msgs/Path poses."""
    poses = path_msg.poses
    if len(poses) < 2:
        return 0.0
    total = 0.0
    for i in range(len(poses) - 1):
        p1 = poses[i].pose.position
        p2 = poses[i + 1].pose.position
        total += math.hypot(p2.x - p1.x, p2.y - p1.y)
    return total


class AsyncRouteResolver:
    """Asynchronous resolver for Nav2 ComputePathToPose actions."""

    def __init__(
        self,
        cache: RouteCache,
        consumer: Optional[Any] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        clock: Callable[[], float] = time.monotonic,
        timeout_sec: float = NAV2_ROUTE_TIMEOUT_SEC,
    ) -> None:
        self.cache = cache
        self.consumer = consumer
        self.loop = loop
        self.clock = clock
        self.timeout_sec = timeout_sec
        self._action_clients: dict[str, Any] = {}

    def register_robot_client(self, robot_id: str, client: Any) -> None:
        self._action_clients[robot_id] = client

    async def query_route(
        self,
        robot_id: str,
        start_pose: Pose2D,
        goal_pose: Pose2D,
        map_revision: str = "v1.0",
        planner_id: str = "GridBased",
        use_start: bool = True,
    ) -> Optional[float]:
        """Query Nav2 ComputePathToPose action asynchronously.
        
        Awaits result up to self.timeout_sec (2.0s monotonic).
        Returns calculated path length in metres, or None on failure/timeout.
        Strictly NO Euclidean fallback (C3.3.2-DEC-02).
        """
        # First check cache
        cached = self.cache.get(robot_id, start_pose, goal_pose, map_revision, now=self.clock())
        if cached is not None:
            return cached

        client = self._action_clients.get(robot_id)
        if client is None:
            # Client unavailable -> strictly None
            return None

        try:
            from geometry_msgs.msg import PoseStamped
            from nav2_msgs.action import ComputePathToPose
            goal = ComputePathToPose.Goal()
            goal.planner_id = planner_id
            goal.use_start = use_start

            # Start pose
            s_pose = PoseStamped()
            s_pose.header.frame_id = start_pose.frame_id or "map"
            s_pose.pose.position.x = float(start_pose.x)
            s_pose.pose.position.y = float(start_pose.y)
            qx, qy, qz, qw = yaw_to_quaternion(start_pose.yaw)
            s_pose.pose.orientation.x = qx
            s_pose.pose.orientation.y = qy
            s_pose.pose.orientation.z = qz
            s_pose.pose.orientation.w = qw
            goal.start = s_pose

            # Goal pose
            g_pose = PoseStamped()
            g_pose.header.frame_id = goal_pose.frame_id or "map"
            g_pose.pose.position.x = float(goal_pose.x)
            g_pose.pose.position.y = float(goal_pose.y)
            qx, qy, qz, qw = yaw_to_quaternion(goal_pose.yaw)
            g_pose.pose.orientation.x = qx
            g_pose.pose.orientation.y = qy
            g_pose.pose.orientation.z = qz
            g_pose.pose.orientation.w = qw
            goal.goal = g_pose
        except ImportError:
            class MockGoal:
                pass
            goal = MockGoal()
            goal.planner_id = planner_id
            goal.use_start = use_start
            goal.start = start_pose
            goal.goal = goal_pose

        send_future = client.send_goal_async(goal)
        start_t = self.clock()

        # Wait for goal acceptance
        while not send_future.done():
            if (self.clock() - start_t) > self.timeout_sec:
                logger.warning("Nav2 route goal send timed out after %.1fs", self.timeout_sec)
                return None
            await asyncio.sleep(0.02)

        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            logger.warning("Nav2 route goal was rejected by planner")
            return None

        # Wait for route result
        res_future = goal_handle.get_result_async()
        while not res_future.done():
            if (self.clock() - start_t) > self.timeout_sec:
                logger.warning("Nav2 route query timed out after %.1fs; cancelling query", self.timeout_sec)
                goal_handle.cancel_goal_async()
                return None
            await asyncio.sleep(0.02)

        wrapped_res = res_future.result()
        if wrapped_res is None or not hasattr(wrapped_res, "result"):
            return None

        path_msg = wrapped_res.result.path
        dist = calculate_path_length(path_msg)
        if dist <= 0.0 and len(path_msg.poses) <= 1:
            # Empty or invalid path
            return None

        # Cache valid route result
        now_monotonic = self.clock()
        self.cache.put(
            robot_id=robot_id,
            start_pose=start_pose,
            goal_pose=goal_pose,
            distance=dist,
            map_revision=map_revision,
            now=now_monotonic,
        )

        # Forward ROUTE_RESOLVED event to consumer if wired
        if self.consumer is not None and self.loop is not None:
            event = Event(
                kind="ROUTE_RESOLVED",
                payload={
                    "robot_id": robot_id,
                    "start_pose": start_pose,
                    "goal_pose": goal_pose,
                    "distance": dist,
                    "map_revision": map_revision,
                    "timestamp": now_monotonic,
                },
            )
            asyncio.run_coroutine_threadsafe(self.consumer.submit(event), self.loop)

        return dist
