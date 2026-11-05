"""One asyncio consumer owns domain transitions and every SQLite write.

Producers submit values, never callbacks. Network sends happen outside transactions.
The route provider must be a synchronous, read-only distance lookup.
"""
import asyncio
from copy import copy, deepcopy
from dataclasses import dataclass, field
import math
import logging
import time
from uuid import uuid4

from .domain import TaskResultStatus
from .domain.constants import ROBOT_STATUS_STALE_TIMEOUT_SEC
from .persistence.store import SQLiteStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    kind: str
    payload: dict = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))


class FleetEventLoop:
    def __init__(self, store: SQLiteStore, core, *, clock=time.monotonic):
        self.store = store
        self._clock = clock
        self._core = deepcopy(core, {id(core.scheduler): core.scheduler})
        self._queue = asyncio.Queue()
        self._worker = None
        self._closed = False
        self._route_planning = None
        with store.transaction():
            store.require_empty()
            store.persist_core(self._core)
            # Also fence an empty fleet against accidental reuse.
            store.connection.execute(
                "INSERT INTO processed_events(event_id,outcome) VALUES (?, 'STARTED')", (str(uuid4()),)
            )

    @property
    def core(self):
        """Return a detached snapshot; producers cannot mutate the consumer state."""
        return deepcopy(self._core, {id(self._core.scheduler): self._core.scheduler})

    def bind_battery_clock(self, clock_ns):
        if self._core.scheduler.battery_clock_ns is not None or self._closed:
            raise RuntimeError("Consumer cannot attach a second battery clock or attach after close")
        self._core.scheduler = copy(self._core.scheduler)
        self._core.scheduler.battery_clock_ns = clock_ns

    def enable_live_routing(self, query):
        from .adapters.route_cache import CachedRouteDistanceProvider
        from .adapters.route_planning import LiveRoutePlanning

        if self._route_planning is not None or self._closed:
            raise RuntimeError("Consumer cannot attach a second planner or attach after close")
        provider = self._core.scheduler.route_provider
        if not isinstance(provider, CachedRouteDistanceProvider):
            raise ValueError("Live routing requires a robot-specific cache provider")
        self._route_planning = LiveRoutePlanning(self, provider.cache, query, self._clock)

    async def start(self):
        if self._closed:
            raise RuntimeError("Consumer is closed")
        if self._worker is not None:
            raise RuntimeError("Consumer already started")
        self._worker = asyncio.create_task(self._run())

    async def submit(self, event: Event):
        if self._worker is None or self._worker.done() or self._closed:
            raise RuntimeError("Consumer is not accepting events")
        future = asyncio.get_running_loop().create_future()
        self._queue.put_nowait((deepcopy(event), future))
        # Caller cancellation does not retract an accepted command.
        return await asyncio.shield(future)

    async def close(self):
        if self._closed:
            if self._worker is not None:
                await self._worker
            return
        self._closed = True
        if self._route_planning is not None:
            await self._route_planning.close()
        if self._worker is not None:
            self._queue.put_nowait(None)
            await self._worker

    async def _run(self):
        while True:
            item = await self._queue.get()
            try:
                if item is None:
                    return
                event, future = item
                try:
                    result = self._process(event)
                except Exception as exc:
                    future.set_exception(exc)
                else:
                    future.set_result(result)
            finally:
                self._queue.task_done()

    def _process(self, event):
        db = self.store.connection
        routes = self._route_planning
        plan = resolved_route = None
        previous_dispatch = self._core.station_dispatch
        with self.store.transaction():
            if event.kind == "OUTBOX_CLAIM":
                command = self.store.claim(**event.payload)
                if command is not None and command["kind"] in ("NAVIGATE_TO_STATION", "CANCEL_STATION_MOVE"):
                    if not self._station_send_allowed(command, event.payload["now"]):
                        self.store.finish(command["command_id"], command["attempts"],
                                          "Station ownership or telemetry unavailable", 0, held_for_review=True)
                        return None
                return command
            if event.kind == "OUTBOX_FINISH":
                p = event.payload
                row = db.execute("SELECT * FROM outbox_events WHERE command_id=?", (p["command_id"],)).fetchone()
                if row is not None and not self._command_current(row):
                    return db.execute(
                        "UPDATE outbox_events SET state='SUPERSEDED' WHERE command_id=? AND attempts=? AND state='SENDING'",
                        (p["command_id"], p["attempt"]),
                    ).rowcount == 1
                return self.store.finish(**p)
            if not event.event_id:
                raise ValueError("event_id is required")
            if db.execute("SELECT 1 FROM processed_events WHERE event_id=?", (event.event_id,)).fetchone():
                return "DUPLICATE"
            candidate = deepcopy(self._core, {id(self._core.scheduler): self._core.scheduler})
            if event.kind == "ROUTE_RESOLVED":
                if routes is not None:
                    resolved_route = routes.current_result(candidate, event)
                outcome, stream, seq = ("ROUTE_APPLIED" if resolved_route else "STALE", None, None)
            else:
                outcome, stream, seq = self._apply(candidate, event)
            if outcome == "APPLIED" and routes is not None and event.kind in (
                "TICK", "SUBMIT_TASK", "ROBOT_STATUS", "ACTION_RESULT", "CLEAR_REVIEW_HOLD", "STATION_RESULT",
            ):
                if len(candidate.queue) or candidate.station_dispatch is not None:
                    now = self._clock()
                    plan = routes.planning_pass(now)
                    scheduler = candidate.scheduler
                    candidate.scheduler = copy(scheduler)
                    candidate.scheduler.route_lookup = plan.lookup
                    candidate.scheduler.pending_route_tasks = plan.pending
                    candidate.schedule_tick(current_time=now, station_lookup=plan.lookup_station)
                    candidate.scheduler = scheduler
            if outcome in ("APPLIED", "SESSION_BLOCKED"):
                self.store.persist_core(candidate)
                if outcome == "APPLIED":
                    self._commands(candidate)
            p = event.payload
            db.execute(
                "INSERT INTO processed_events(event_id,outcome,stream,status_seq,task_id,assignment_epoch,goal_uuid) "
                "VALUES (?,?,?,?,?,?,?)",
                (event.event_id, outcome, stream, seq, p.get("task_id"),
                 p.get("assignment_epoch", p.get("current_epoch")), p.get("goal_uuid")),
            )
        # Publish memory only after COMMIT; failed writes leave both states unchanged.
        if outcome in ("APPLIED", "SESSION_BLOCKED"):
            self._core = candidate
            if candidate.station_dispatch is not None:
                for robot_id, reason in candidate.station_dispatch.wait_reasons.items():
                    if previous_dispatch.wait_reasons.get(robot_id) != reason:
                        logger.warning("STATION_DISPATCH_WAIT robot=%s reason=%s", robot_id, reason)
            if routes is not None:
                moved_robot = (candidate.tracker.get_robot(event.payload["robot_id"])
                               if event.kind == "ROBOT_STATUS" and outcome == "APPLIED" else None)
                routes.after_commit(candidate, plan, moved_robot)
            if event.kind == "TICK":
                for robot_id, severity, elapsed in candidate.tracker.check_communication_health(event.payload["current_time"]):
                    if (robot_id in candidate._active_tasks_by_robot
                            or (candidate.station_dispatch and robot_id in candidate.station_dispatch.active)):
                        logger.warning("COMMUNICATION_WARNING robot=%s severity=%s elapsed=%s", robot_id, severity, elapsed)
        if resolved_route is not None:
            routes.publish_result(resolved_route, event.payload["distance"], event.payload["timestamp"])
        return outcome

    def _apply(self, core, event):
        p = deepcopy(event.payload)
        kind = event.kind
        stream = seq = None
        if kind in ("ROBOT_STATUS", "ACTION_FEEDBACK"):
            seq = p.pop("status_seq")
            if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
                raise ValueError("status_seq must be a nonnegative integer")
            stream = (f"status:{p['robot_id']}" if kind == "ROBOT_STATUS"
                      else f"feedback:{p['robot_id']}:{p['goal_uuid']}")
            if kind == "ROBOT_STATUS":
                robot = core.tracker.get_robot(p["robot_id"])
                if robot is None:
                    raise ValueError("Unknown robot")
                if not core.check_status_session(robot, p.get("publisher_session_id")):
                    return "SESSION_BLOCKED", stream, seq
            previous = self.store.connection.execute(
                "SELECT MAX(status_seq) FROM processed_events WHERE stream=? AND outcome='APPLIED'", (stream,)
            ).fetchone()[0]
            if previous is not None and seq <= previous:
                return "STALE", stream, seq
        if kind == "SUBMIT_TASK":
            if self.store.connection.execute("SELECT 1 FROM tasks WHERE task_id=?", (p["task_id"],)).fetchone():
                raise ValueError("task_id already exists in this scenario")
            core.submit_task(**p)
        elif kind == "TICK":
            if self._route_planning is None:
                core.schedule_tick(**p)
        elif kind == "ROBOT_STATUS":
            robot = core.tracker.get_robot(p["robot_id"])
            if robot is None:
                raise ValueError("Unknown robot")
            active = core._active_tasks_by_robot.get(robot.robot_id)
            move = core.station_dispatch.active.get(robot.robot_id) if core.station_dispatch else None
            # RobotStatus has no goal UUID. Active ownership must remain intact
            # until a separately matched action result arrives, even if IDLE arrives first.
            if p["current_epoch"] < robot.current_epoch or (
                active and (p["current_epoch"] != active.assignment_epoch
                            or p["current_task_id"] not in (None, active.task_id))
            ) or (
                move and (p["current_epoch"] != move.assignment_epoch
                          or p["current_task_id"] not in (None, move.task_id))
            ):
                return "STALE", stream, seq
            if p["timestamp_sec"] < robot.last_status_received_at:
                return "STALE", stream, seq
            if p.get("pose_valid_until") is not None:
                now = self._clock()
                if seq == 0 or not 0 <= now - p["timestamp_sec"] <= ROBOT_STATUS_STALE_TIMEOUT_SEC:
                    p["source_status_ns"] = 0
                    p["pose_valid_until"] = 0.0
                elif now > p["pose_valid_until"]:
                    p["pose_valid_until"] = 0.0
            if robot.requires_battery_telemetry:
                now = self._clock()
                if seq == 0 or not p["timestamp_sec"] <= now <= p.get("battery_valid_until", 0.0):
                    p["battery_valid_until"] = 0.0
            core.handle_robot_status(**p)
            if active:
                robot.current_task_id = active.task_id
        elif kind in ("ACTION_FEEDBACK", "ACTION_RESULT", "CANCEL_RESPONSE"):
            task = core._active_tasks_by_robot.get(p["robot_id"])
            if task is None or (task.task_id, task.assignment_epoch, task.goal_uuid) != (
                p["task_id"], p["assignment_epoch"], p["goal_uuid"]
            ):
                return "STALE", stream, seq
            if kind == "ACTION_FEEDBACK":
                core.handle_action_feedback(**p)
            elif kind == "CANCEL_RESPONSE":
                pending = core._pending_preemption_assignments.get(p["robot_id"])
                latest = self.store.connection.execute(
                    "SELECT command_id FROM outbox_events WHERE kind='CANCEL_TASK' AND goal_uuid=? ORDER BY sequence DESC LIMIT 1",
                    (p["goal_uuid"],),
                ).fetchone()
                if pending is None or latest is None or p["cancel_command_id"] != latest[0]:
                    return "STALE", stream, seq
                if not p["accepted"]:
                    core._pending_preemption_assignments.pop(p["robot_id"])
                    core.queue.enqueue(pending)
            else:
                TaskResultStatus(p["result_status"])  # Reject invalid results before mutation.
                completed_epoch = p.get("completed_epoch")
                if type(completed_epoch) is not int or completed_epoch != task.assignment_epoch:
                    logger.warning(
                        "ACTION_RESULT completed_epoch invalid or mismatched for task %s: got %r, expected %d",
                        task.task_id, completed_epoch, task.assignment_epoch
                    )
                    return "STALE", stream, seq
                del p["assignment_epoch"]
                accepted, _ = core.handle_action_result(**p)
                if not accepted:
                    return "STALE", stream, seq
                # A natural completion/failure during cancellation must not strand HIGH.
                pending = core._pending_preemption_assignments.pop(p["robot_id"], None)
                if pending is not None:
                    core.queue.enqueue(pending)
        elif kind == "GOAL_REJECTED":
            task = core._active_tasks_by_robot.get(p["robot_id"])
            if task is None or (task.task_id, task.assignment_epoch, task.goal_uuid) != (
                p["task_id"], p["assignment_epoch"], p["goal_uuid"]
            ):
                return "STALE", stream, seq
            core.add_review_hold(
                task_id=p["task_id"],
                robot_id=p["robot_id"],
                assignment_epoch=p["assignment_epoch"],
                goal_uuid=p["goal_uuid"],
                reason=p.get("reason", "GoalResponse.REJECT"),
                held_at=p.get("held_at", 0.0),
            )
            core._active_tasks_by_robot.pop(p["robot_id"], None)
            core._active_tasks.pop(p["task_id"], None)
            core.queue.enqueue(task)
            self.store.connection.execute(
                "UPDATE outbox_events SET state='HELD_FOR_REVIEW', last_error=? WHERE goal_uuid=? AND state IN ('PENDING','SENDING','RETRY')",
                (p.get("reason", "GoalResponse.REJECT"), p["goal_uuid"]),
            )
            self.store.put_review_hold(
                task_id=p["task_id"],
                robot_id=p["robot_id"],
                assignment_epoch=p["assignment_epoch"],
                goal_uuid=p["goal_uuid"],
                reason=p.get("reason", "GoalResponse.REJECT"),
                held_at=p.get("held_at", 0.0),
            )
        elif kind in ("STATION_RESULT", "STATION_GOAL_REJECTED", "STATION_CANCEL_RESPONSE"):
            if not self._station_event(core, kind, p):
                return "STALE", stream, seq
        elif kind == "CLEAR_REVIEW_HOLD":
            core.clear_review_hold(p["task_id"])
            self.store.clear_review_hold(p["task_id"])
        elif kind == "UNBLOCK":
            robot = core.tracker.get_robot(p["robot_id"])
            if not core.reservations.unblock(p["station_id"], robot, now=self._clock()):
                return "REJECTED", stream, seq
        elif kind in ("RESERVE", "OCCUPIED", "RELEASE"):
            robot = core.tracker.get_robot(p["robot_id"])
            if robot is None and kind == "RESERVE":
                raise ValueError("Unknown robot")
            if robot is None or robot.session_blocked:
                return "REJECTED", stream, seq
            if core.station_dispatch is not None and robot.robot_id in core.station_dispatch.active:
                return "REJECTED", stream, seq
            if kind == "RESERVE":
                applied = core.reservations.reserve(**p)
            elif kind == "RELEASE":
                applied = core.reservations.initiate_release(**p)
            else:
                station = core.reservations.get_station(p["station_id"])
                if (station is None
                        or station.reserved_by_robot_id not in (None, robot.robot_id)
                        or station.occupied_by_robot_id not in (None, robot.robot_id)
                        or not station.is_physically_occupied(robot.pose)):
                    return "REJECTED", stream, seq
                applied = core.reservations.mark_occupied(**p)
            if not applied:
                return "REJECTED", stream, seq
        else:
            raise ValueError(f"Unknown event kind: {kind}")
        return "APPLIED", stream, seq

    def _command_current(self, command):
        if command["kind"] in ("NAVIGATE_TO_STATION", "CANCEL_STATION_MOVE"):
            return any(
                (move.task_id, move.assignment_epoch, move.goal_uuid) ==
                (command["task_id"], command["assignment_epoch"], command["goal_uuid"])
                and (command["kind"] != "CANCEL_STATION_MOVE" or move.cancel_for_task is not None)
                for move in self._core.station_dispatch.active.values()
            )
        task = self._core._active_tasks.get(command["task_id"])
        return bool(task and task.goal_uuid == command["goal_uuid"]
                    and task.assignment_epoch == command["assignment_epoch"]
                    and (command["kind"] != "CANCEL_TASK"
                         or task.assigned_robot_id in self._core._pending_preemption_assignments))

    def _station_send_allowed(self, command, now):
        from json import loads

        if not self._command_current(command):
            return False
        robot = self._core.tracker.get_robot(loads(command["payload"])["assigned_robot_id"])
        if robot.session_blocked:
            return False
        if command["kind"] == "CANCEL_STATION_MOVE" or command["attempts"] > 1:
            return True
        clock = self._core.scheduler.battery_clock_ns
        return (not robot.is_stale(now) and now <= robot.route_pose_valid_until
                and robot.has_fresh_battery(now, clock() if clock else None)
                and not robot.is_loaded)

    def _commands(self, candidate):
        for robot_id in self._core._pending_preemption_assignments.keys() - candidate._pending_preemption_assignments.keys():
            old_task = self._core._active_tasks_by_robot[robot_id]
            self.store.connection.execute(
                "UPDATE outbox_events SET state='SUPERSEDED' WHERE goal_uuid=? AND kind='CANCEL_TASK' "
                "AND state IN ('PENDING','RETRY')", (old_task.goal_uuid,),
            )
        old_goals = {t.goal_uuid for t in self._core._active_tasks.values()}
        active_goals = {t.goal_uuid for t in candidate._active_tasks.values()}
        for goal in old_goals - active_goals:
            self.store.connection.execute(
                "UPDATE outbox_events SET state='SUPERSEDED' WHERE goal_uuid=? "
                "AND state IN ('PENDING','RETRY')", (goal,),
            )
        for task in candidate._active_tasks.values():
            if task.goal_uuid not in old_goals:
                self.store.add_command("EXECUTE_TASK", task)
        for robot_id in candidate._pending_preemption_assignments:
            if robot_id not in self._core._pending_preemption_assignments:
                self.store.add_command("CANCEL_TASK", candidate._active_tasks_by_robot[robot_id])
        if candidate.station_dispatch is not None:
            self._station_commands(self._core.station_dispatch, candidate.station_dispatch)

    def _station_event(self, core, kind, payload):
        dispatch = core.station_dispatch
        robot_id = payload["robot_id"]
        robot = core.tracker.get_robot(robot_id)
        move = dispatch.active.get(robot_id) if dispatch is not None else None
        if (move is None or robot.session_blocked or robot.session_id != move.session_id
                or (move.task_id, move.station_id, move.assignment_epoch, move.goal_uuid) !=
                (payload["task_id"], payload["station_id"], payload["assignment_epoch"], payload["goal_uuid"])):
            return False
        db = self.store.connection
        if kind == "STATION_RESULT":
            status = TaskResultStatus(payload["result_status"])
            epoch = payload.get("completed_epoch")
            proof = payload.get("proof_ns")
            if type(epoch) is not int or epoch != move.assignment_epoch:
                return False
            if status != TaskResultStatus.STATUS_FAILED and (type(proof) is not int or proof <= 0):
                return False
            return dispatch.result(core, move, status, proof, payload.get("error_reason", ""))
        if kind == "STATION_GOAL_REJECTED":
            dispatch.reject(move)
            db.execute(
                "UPDATE outbox_events SET state='HELD_FOR_REVIEW', last_error='Station goal rejected' "
                "WHERE goal_uuid=? AND kind='NAVIGATE_TO_STATION' AND state IN ('PENDING','SENDING','RETRY')",
                (move.goal_uuid,),
            )
            return True
        latest = db.execute(
            "SELECT command_id FROM outbox_events WHERE goal_uuid=? AND kind='CANCEL_STATION_MOVE' "
            "ORDER BY sequence DESC LIMIT 1", (move.goal_uuid,),
        ).fetchone()
        if move.cancel_for_task is None or latest is None or latest[0] != payload["cancel_command_id"]:
            return False
        if not payload["accepted"]:
            move.cancel_declined = True
        return True

    def _station_commands(self, previous, dispatch):
        db = self.store.connection
        for robot_id, move in previous.active.items():
            if robot_id not in dispatch.active:
                db.execute(
                    "UPDATE outbox_events SET state='SUPERSEDED' WHERE goal_uuid=? AND state IN ('PENDING','RETRY')",
                    (move.goal_uuid,),
                )
        for robot_id, move in dispatch.active.items():
            old = previous.active.get(robot_id)
            if old is None:
                self.store.add_command("NAVIGATE_TO_STATION", move)
            elif old.cancel_for_task is None and move.cancel_for_task is not None:
                self.store.add_command("CANCEL_STATION_MOVE", move)


class OutboxDispatcher:
    """Transport-neutral sender. A successful send is not task completion.

The injected sender must deduplicate command_id/goal UUID at its boundary.
Retry scheduling uses the caller's monotonic clock, not battery simulation time.
"""
    def __init__(self, consumer, sender, *, clock, retry_delay):
        if not math.isfinite(retry_delay) or retry_delay <= 0:
            raise ValueError("retry_delay must be finite and positive")
        self.consumer = consumer
        self.sender = sender
        self.clock = clock
        self.retry_delay = retry_delay

    async def send_one(self):
        command = await self.consumer.submit(Event("OUTBOX_CLAIM", {"now": self.clock()}))
        if command is None:
            return False
        error = None
        cancelled = False
        try:
            await self.sender(command)
        except asyncio.CancelledError:
            error = "Send cancelled; delivery may have occurred"
            cancelled = True
        except Exception as exc:
            error = str(exc) or type(exc).__name__
        await self.consumer.submit(Event("OUTBOX_FINISH", {
            "command_id": command["command_id"], "attempt": command["attempts"],
            "error": error, "retry_at": self.clock() + self.retry_delay if error is not None else 0,
        }))
        if cancelled:
            raise asyncio.CancelledError
        return True
