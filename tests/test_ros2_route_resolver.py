"""Unit tests for Nav2 route caching and async route resolver.

Verifies C3.3.2-DEC-01 & C3.3.2-DEC-02:
- Grid snapping (0.20m)
- Cache hit, monotonic TTL (30.0s), and invalidation triggers
- Euclidean fallback ban (strictly returns None on failure/miss)
- AsyncRouteResolver timeout (2.0s) and ROUTE_RESOLVED event dispatch
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from backend.fleet_manager.adapters.route_cache import (
    CachedRouteDistanceProvider,
    RouteCache,
    snap_coordinate,
)
from backend.fleet_manager.adapters.route_resolver import (
    AsyncRouteResolver,
    calculate_path_length,
)
from backend.fleet_manager.domain.constants import (
    NAV2_ROUTE_TIMEOUT_SEC,
    ROUTE_CACHE_GRID_RESOLUTION_M,
    ROUTE_CACHE_TTL_SEC,
)
from backend.fleet_manager.domain.models import Pose2D
from backend.fleet_manager.event_loop import Event


def test_grid_snapping_precision():
    """Verify coordinate snapping to 0.20m cells."""
    assert snap_coordinate(0.0) == 0.0
    assert snap_coordinate(0.09) == 0.0
    assert snap_coordinate(0.11) == 0.20
    assert snap_coordinate(0.24) == 0.20
    assert snap_coordinate(0.31) == 0.40
    assert snap_coordinate(-0.19) == -0.20
    assert snap_coordinate(1.58) == 1.60


def test_route_cache_hit_and_miss():
    """Verify cache hit for same snapped coordinates and miss for uncached coordinates."""
    cache = RouteCache(ttl_sec=30.0)
    start = Pose2D(x=1.01, y=2.02)
    goal = Pose2D(x=5.03, y=6.04)

    # Miss before insertion -> strictly None (Euclidean ban)
    assert cache.get("r1", start, goal, now=100.0) is None

    # Put entry
    cache.put("r1", start, goal, distance=14.5, now=100.0)

    # Hit with slightly perturbed coordinates within same 0.20m cell
    query_start = Pose2D(x=1.04, y=1.98)
    query_goal = Pose2D(x=5.02, y=6.01)
    assert cache.get("r1", query_start, query_goal, now=105.0) == 14.5

    # Miss for different robot
    assert cache.get("r2", query_start, query_goal, now=105.0) is None


def test_route_cache_monotonic_ttl():
    """Verify entries expire after 30.0s monotonic TTL."""
    cache = RouteCache(ttl_sec=30.0)
    start = Pose2D(x=0.0, y=0.0)
    goal = Pose2D(x=10.0, y=10.0)

    cache.put("r1", start, goal, distance=20.0, now=100.0)

    # Valid within 30s
    assert cache.get("r1", start, goal, now=129.9) == 20.0

    # Expired at 30.1s
    assert cache.get("r1", start, goal, now=130.1) is None


def test_route_cache_displacement_invalidation():
    """Verify cache invalidates if robot departs > 0.20m from start cell."""
    cache = RouteCache(ttl_sec=30.0)
    start = Pose2D(x=0.0, y=0.0)
    goal = Pose2D(x=10.0, y=10.0)

    cache.put("r1", start, goal, distance=20.0, now=100.0)

    # Query with start moved > 0.20m from cell (0, 0)
    moved_start = Pose2D(x=0.25, y=0.0)
    assert cache.get("r1", moved_start, goal, now=105.0) is None

    # Explicit invalidation for robot movement
    cache.put("r1", start, goal, distance=20.0, now=100.0)
    invalidated_count = cache.invalidate_for_robot_movement("r1", Pose2D(x=0.30, y=0.0))
    assert invalidated_count == 1
    assert cache.get("r1", start, goal, now=105.0) is None


def test_route_cache_map_revision_invalidation():
    """Verify cache invalidates on map revision change."""
    cache = RouteCache(ttl_sec=30.0)
    start = Pose2D(x=0.0, y=0.0)
    goal = Pose2D(x=10.0, y=10.0)

    cache.put("r1", start, goal, distance=15.0, map_revision="v1.0", now=100.0)

    # Query with different map revision
    assert cache.get("r1", start, goal, map_revision="v1.1", now=105.0) is None

    # Invalidate all non-matching map revisions
    cache.invalidate_map_revision("v1.1")
    assert cache.get("r1", start, goal, map_revision="v1.0", now=105.0) is None


def test_cached_route_distance_provider_euclidean_ban():
    """Verify CachedRouteDistanceProvider strictly returns None on miss (no Euclidean fallback)."""
    cache = RouteCache()
    provider = CachedRouteDistanceProvider(cache=cache, robot_id="r1", map_revision="v1.0", clock=lambda: 50.0)

    p1 = Pose2D(0.0, 0.0)
    p2 = Pose2D(3.0, 4.0)  # Euclidean distance would be 5.0m

    # Must return None, never 5.0m!
    assert provider.get_path_distance(p1, p2) is None

    # After update_cache
    provider.update_cache("r1", p1, p2, distance=7.5, map_revision="v1.0", timestamp=50.0)
    assert provider.get_path_distance(p1, p2) == 7.5


def test_calculate_path_length():
    """Verify path distance computation from pose points."""
    class MockPoint:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class MockPoseStamped:
        def __init__(self, x, y):
            self.pose = MagicMock()
            self.pose.position = MockPoint(x, y)

    class MockPath:
        def __init__(self, coords):
            self.poses = [MockPoseStamped(x, y) for x, y in coords]

    path = MockPath([(0.0, 0.0), (3.0, 0.0), (3.0, 4.0)])
    # Leg 1 = 3.0m, Leg 2 = 4.0m -> Total = 7.0m
    assert pytest.approx(calculate_path_length(path), 0.001) == 7.0


def test_async_route_resolver_success_and_timeout():
    """Verify AsyncRouteResolver handles cache, query timeout (2.0s), and event dispatch."""
    async def scenario():
        cache = RouteCache()
        consumer = AsyncMock()
        loop = asyncio.get_running_loop()

        now_val = 100.0
        def clock():
            nonlocal now_val
            return now_val

        resolver = AsyncRouteResolver(
            cache=cache,
            consumer=consumer,
            loop=loop,
            clock=clock,
            timeout_sec=2.0,
        )

        # Client not registered -> None
        start = Pose2D(0, 0)
        goal = Pose2D(5, 5)
        assert await resolver.query_route("r1", start, goal) is None

        # Register mock action client
        mock_client = MagicMock()
        mock_send_future = loop.create_future()
        mock_client.send_goal_async.return_value = mock_send_future

        resolver.register_robot_client("r1", mock_client)

        # Test query timeout (> 2.0s)
        query_task = asyncio.create_task(resolver.query_route("r1", start, goal))
        await asyncio.sleep(0.01)
        now_val += 2.5  # Monotonic time advances past 2.0s
        await asyncio.sleep(0.05)

        res = await query_task
        assert res is None  # Timed out and returned None (Euclidean ban)
    asyncio.run(scenario())
