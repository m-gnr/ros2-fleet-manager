"""Stage planner demands during scheduling and execute them after COMMIT."""

import asyncio
from dataclasses import dataclass, field
import logging
from uuid import uuid4

from ..domain.constants import NAV2_ROUTE_TIMEOUT_SEC
from ..domain.models import Pose2D
from ..event_loop import Event
from .route_cache import RouteCacheKey, valid_distance

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RouteContext:
    task_id: str
    session_id: str | None
    epoch: int
    leg: int


@dataclass
class RouteDemand:
    key: RouteCacheKey
    start: Pose2D
    goal: Pose2D
    contexts: set[RouteContext] = field(default_factory=set)


@dataclass
class RouteQuery:
    demand: RouteDemand
    generation: int
    request_id: str = field(default_factory=lambda: str(uuid4()))


class RoutePlanningPass:
    """Read cache and collect planner work without changing shared state."""

    def __init__(self, cache, cooldowns, now):
        self.cache = cache
        self.cooldowns = cooldowns
        self.now = now
        self.references: dict[str, set[RouteCacheKey]] = {}
        self.demands: dict[RouteCacheKey, RouteDemand] = {}
        self.pending: set[str] = set()

    def lookup(self, robot, task, legs):
        if self.now > robot.route_pose_valid_until:
            return None
        keys = [self.cache.key(robot.robot_id, start, goal) for start, goal in legs]
        if any(key is None for key in keys):
            return None
        self.references.setdefault(task.task_id, set()).update(keys)
        distances = tuple(
            self.cache.get(robot.robot_id, start, goal, now=self.now) for start, goal in legs
        )
        missing = [
            (index, key, start, goal)
            for index, (key, (start, goal), distance) in enumerate(zip(keys, legs, distances))
            if distance is None
        ]
        if any(self.now < self.cooldowns.get(key, 0) for _, key, _, _ in missing):
            return None
        if missing:
            self.pending.add(task.task_id)
            for leg, key, start, goal in missing:
                demand = self.demands.setdefault(key, RouteDemand(key, start, goal))
                demand.contexts.add(RouteContext(task.task_id, robot.session_id, robot.current_epoch, leg))
        return distances


class LiveRoutePlanning:
    """Owns planner work on the same asyncio loop as the single consumer."""

    def __init__(self, consumer, cache, query, clock):
        self.consumer = consumer
        self.cache = cache
        self.query = query
        self.clock = clock
        self.cooldowns: dict[RouteCacheKey, float] = {}
        self.references: dict[str, set[RouteCacheKey]] = {}
        self.inflight: dict[str, RouteQuery] = {}
        self.workers: set[asyncio.Task] = set()
        self.closed = False
        self.generation = cache.map_generation

    def planning_pass(self, now):
        cooldowns = self.cooldowns if self.generation == self.cache.map_generation else {}
        return RoutePlanningPass(self.cache, cooldowns, now)

    @staticmethod
    def _current_context(core, demand, context, now):
        robot = core.tracker.get_robot(demand.key.robot_id)
        return (
            robot is not None
            and not robot.session_blocked
            and not robot.is_stale(now)
            and now <= robot.route_pose_valid_until
            and robot.session_id == context.session_id
            and robot.current_epoch == context.epoch
            and core.queue.get(context.task_id) is not None
            and not core.has_review_hold(context.task_id)
            and (context.leg != 0 or demand.key.matches_start(robot.pose))
        )

    def after_commit(self, core, plan, moved_robot=None):
        now = self.clock()
        if self.generation != self.cache.map_generation:
            self.generation = self.cache.map_generation
            self.cooldowns.clear()
            self.references.clear()
        if moved_robot is not None:
            self.cache.invalidate_for_robot_movement(moved_robot.robot_id, moved_robot.pose)
        self.cache.prune_expired(now)
        self.cooldowns = {key: until for key, until in self.cooldowns.items() if now < until}

        if plan is not None:
            for task_id, keys in plan.references.items():
                self.references.setdefault(task_id, set()).update(keys)
        for task_id in list(self.references):
            if core.queue.get(task_id) is None or core.has_review_hold(task_id):
                self.cache.discard(self.references.pop(task_id))
            else:
                self.references[task_id] = self.cache.stored_keys(self.references[task_id])

        for request in self.inflight.values():
            demand = request.demand
            demand.contexts = {
                context for context in demand.contexts
                if self._current_context(core, demand, context, now)
            }

        if plan is None or self.closed:
            return
        for demand in plan.demands.values():
            robot_id = demand.key.robot_id
            if robot_id in self.inflight:
                continue
            demand.contexts = {
                context for context in demand.contexts
                if self._current_context(core, demand, context, now)
            }
            if not demand.contexts:
                continue
            request = RouteQuery(demand, self.cache.map_generation)
            self.inflight[robot_id] = request
            worker = asyncio.create_task(self._resolve(request))
            self.workers.add(worker)
            worker.add_done_callback(self.workers.discard)

    def current_result(self, core, event):
        request = self.inflight.get(event.payload["robot_id"])
        now = self.clock()
        if (request is None or event.event_id != request.request_id
                or request.generation != self.cache.map_generation
                or request.demand.key.map_revision != self.cache.map_revision
                or not 0 <= now - event.payload["timestamp"] < self.cache.ttl_sec):
            return None
        if not any(self._current_context(core, request.demand, context, now)
                   for context in request.demand.contexts):
            return None
        return request

    def publish_result(self, request, distance, timestamp):
        demand = request.demand
        if valid_distance(distance):
            self.cache.put(
                demand.key.robot_id, demand.start, demand.goal, distance,
                demand.key.map_revision, now=timestamp,
                starts_at_robot=any(context.leg == 0 for context in demand.contexts),
            )
            for context in demand.contexts:
                self.references.setdefault(context.task_id, set()).add(demand.key)
            logger.info("NAV2_ROUTE_RESOLVED robot=%s revision=%s legs=%s distance_m=%.3f",
                        demand.key.robot_id, demand.key.map_revision,
                        sorted({(context.task_id, context.leg) for context in demand.contexts}), distance)
        else:
            self.cooldowns[demand.key] = timestamp + NAV2_ROUTE_TIMEOUT_SEC

    async def _resolve(self, request):
        demand = request.demand
        robot_id = demand.key.robot_id
        try:
            logger.debug("NAV2_ROUTE_REQUEST robot=%s key=%s", robot_id, demand.key)
            try:
                distance = await self.query(robot_id, demand.start, demand.goal)
            except Exception:
                logger.warning("Planner query failed robot=%s", robot_id, exc_info=True)
                distance = None
            await self.consumer.submit(Event("ROUTE_RESOLVED", {
                "robot_id": robot_id, "distance": distance, "timestamp": self.clock(),
            }, event_id=request.request_id))
        except Exception:
            logger.exception("Could not commit Nav2 route result robot=%s", robot_id)
            return
        finally:
            self.inflight.pop(robot_id, None)
        try:
            await self.consumer.submit(Event("TICK", {"current_time": self.clock()}))
        except Exception:
            logger.exception("Could not reschedule after Nav2 route result robot=%s", robot_id)

    async def close(self):
        self.closed = True
        workers = list(self.workers)
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
