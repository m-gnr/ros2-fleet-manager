"""Unit tests for Nav2 route caching and async route resolver.

Verifies C3.3.2-DEC-01 & C3.3.2-DEC-02:
- Grid snapping (0.20m)
- Cache hit, monotonic TTL (30.0s), and invalidation triggers
- Euclidean fallback ban (strictly returns None on failure/miss)
- AsyncRouteResolver success, planner failures and cancellation
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
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
from backend.fleet_manager.domain.models import Pose2D


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
    assert cache.get("r1", start, goal, now=130.0) is None


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
    provider = CachedRouteDistanceProvider(cache=cache, clock=lambda: 50.0)

    p1 = Pose2D(0.0, 0.0)
    p2 = Pose2D(3.0, 4.0)  # Euclidean distance would be 5.0m

    # Must return None, never 5.0m!
    assert provider.get_path_distance("r1", p1, p2) is None

    # After update_cache
    cache.put("r1", p1, p2, distance=7.5, now=50.0)
    assert provider.get_path_distance("r1", p1, p2) == 7.5


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


def path(*coords):
    return SimpleNamespace(
        header=SimpleNamespace(frame_id="map"),
        poses=[SimpleNamespace(pose=SimpleNamespace(position=SimpleNamespace(x=x, y=y)))
               for x, y in coords],
    )


@pytest.mark.parametrize("coords", [
    (), ((0, 0),), ((0, 0), (float("nan"), 1)), ((0, 0), (0, float("inf"))),
    ((-1e308, 0), (1e308, 0)),
])
def test_invalid_paths(coords):
    assert calculate_path_length(path(*coords)) is None
    assert calculate_path_length(None) is None


@pytest.fixture
def resolver(monkeypatch):
    monkeypatch.setattr(
        "backend.fleet_manager.adapters.route_resolver._make_goal",
        lambda start, goal, planner_id, use_start: (start, goal, planner_id, use_start),
    )
    return AsyncRouteResolver(RouteCache())


def test_query_uses_only_registered_ready_client_and_requires_success(resolver):
    async def scenario():
        loop = asyncio.get_running_loop()
        start, goal = Pose2D(), Pose2D(1, 0)
        client = Mock()
        client.server_is_ready.return_value = False
        resolver.register_robot_client("r1", client)
        assert await resolver.query_route("", start, goal) is None
        assert await resolver.query_route("r2", start, goal) is None
        assert await resolver.query_route("r1", start, goal) is None
        client.send_goal_async.assert_not_called()

        client.server_is_ready.return_value = True
        send_future = loop.create_future()
        result_future = loop.create_future()
        client.send_goal_async.return_value = send_future
        handle = Mock(accepted=True)
        handle.get_result_async.return_value = result_future
        send_future.set_result(handle)
        response = SimpleNamespace(status=6, result=SimpleNamespace(path=path((0, 0), (3, 4))))
        result_future.set_result(response)
        assert await resolver.query_route("r1", start, goal) is None
        assert len(resolver.cache) == 0

        response.status = 4
        assert await resolver.query_route("r1", start, goal) == 5.0
        assert await resolver.query_route("r1", start, goal) == 5.0
        assert resolver.cache.get("r2", start, goal) is None
        assert client.send_goal_async.call_count == 2
        assert client.send_goal_async.call_args.args[0] == (start, goal, "GridBased", True)
    asyncio.run(scenario())


@pytest.mark.parametrize("stage", ["acceptance", "result"])
def test_async_route_resolver_discards_timeout_and_cancels_late_acceptance(resolver, stage):
    async def scenario():
        loop = asyncio.get_running_loop()
        now = [100.0]
        resolver.clock = lambda: now[0]
        client = Mock()
        send_future = loop.create_future()
        result_future = loop.create_future()
        handle = Mock(accepted=True)
        handle.get_result_async.return_value = result_future
        client.send_goal_async.return_value = send_future
        resolver.register_robot_client("r1", client)
        if stage == "result":
            send_future.set_result(handle)

        task = asyncio.create_task(resolver.query_route("r1", Pose2D(), Pose2D(1, 0)))
        await asyncio.sleep(0)
        now[0] += 2.0
        assert await task is None
        if stage == "acceptance":
            handle.cancel_goal_async.assert_not_called()
            send_future.set_result(handle)
        result_future.set_result(SimpleNamespace(
            status=4, result=SimpleNamespace(path=path((0, 0), (1, 0))),
        ))
        await asyncio.sleep(0)
        handle.cancel_goal_async.assert_called_once()
        assert len(resolver.cache) == 0
    asyncio.run(scenario())


def test_route_cache_does_not_find_another_robot_for_missing_identity():
    cache = RouteCache()
    start, goal = Pose2D(), Pose2D(1, 0)
    cache.put("r1", start, goal, 1.0)
    assert cache.get("", start, goal) is None
    assert cache.get("r2", start, goal) is None
    cache.put("r2", start, goal, 4.0)
    provider = CachedRouteDistanceProvider(cache)
    assert provider.get_path_distance("r1", start, goal) == 1.0
    assert provider.get_path_distance("r2", start, goal) == 4.0
    assert provider.get_path_distance("", start, goal) is None


@pytest.mark.parametrize("bad_distance", [float("nan"), float("inf"), -1.0])
def test_route_cache_rejects_invalid_distance(bad_distance):
    cache = RouteCache()
    start, goal = Pose2D(), Pose2D(1, 0)
    cache.put("r1", start, goal, bad_distance)
    assert cache.get("r1", start, goal) is None
