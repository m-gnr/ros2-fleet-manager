"""One asyncio consumer owns domain transitions and every SQLite write.

Producers submit values, never callbacks. Network sends happen outside transactions.
The route provider must be a synchronous, read-only distance lookup.
"""
import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
import math
import logging
from uuid import uuid4

from .domain import TaskResultStatus
from .persistence.store import SQLiteStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    kind: str
    payload: dict = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))


class FleetEventLoop:
    def __init__(self, store: SQLiteStore, core):
        self.store = store
        self._core = deepcopy(core, {id(core.scheduler): core.scheduler})
        self._queue = asyncio.Queue()
        self._worker = None
        self._closed = False
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
        with self.store.transaction():
            if event.kind == "OUTBOX_CLAIM":
                return self.store.claim(**event.payload)
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
            outcome, stream, seq = self._apply(candidate, event)
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
            if event.kind == "TICK":
                for robot_id, severity, elapsed in candidate.tracker.check_communication_health(event.payload["current_time"]):
                    if robot_id in candidate._active_tasks_by_robot:
                        logger.warning("COMMUNICATION_WARNING robot=%s severity=%s elapsed=%s", robot_id, severity, elapsed)
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
                session_id = p.get("publisher_session_id")
                if session_id is not None:
                    if robot.session_id is not None and robot.session_id != session_id:
                        robot.session_blocked = True
                        return "SESSION_BLOCKED", stream, seq
                    if robot.session_blocked:
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
            core.schedule_tick(**p)
        elif kind == "ROBOT_STATUS":
            robot = core.tracker.get_robot(p["robot_id"])
            if robot is None:
                raise ValueError("Unknown robot")
            active = core._active_tasks_by_robot.get(robot.robot_id)
            # RobotStatus has no goal UUID. Active ownership must remain intact
            # until a separately matched action result arrives, even if IDLE arrives first.
            if p["current_epoch"] < robot.current_epoch or (
                active and (p["current_epoch"] != active.assignment_epoch
                            or p["current_task_id"] not in (None, active.task_id))
            ):
                return "STALE", stream, seq
            if p["timestamp_sec"] < robot.last_status_received_at:
                return "STALE", stream, seq
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
                if completed_epoch is None:
                    completed_epoch = p.pop("assignment_epoch", None)
                else:
                    p.pop("assignment_epoch", None)
                if completed_epoch != task.assignment_epoch:
                    logger.warning(
                        "ACTION_RESULT completed_epoch mismatch for task %s: got %s, expected %s",
                        task.task_id, completed_epoch, task.assignment_epoch
                    )
                    return "STALE", stream, seq
                p["completed_epoch"] = completed_epoch
                core.handle_action_result(**p)
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
        elif kind == "CLEAR_REVIEW_HOLD":
            core.clear_review_hold(p["task_id"])
            self.store.clear_review_hold(p["task_id"])
        elif kind == "ROUTE_RESOLVED":
            provider = core.scheduler.route_provider
            if hasattr(provider, "update_cache"):
                provider.update_cache(**p)
        elif kind == "RESERVE":
            if core.tracker.get_robot(p["robot_id"]) is None:
                raise ValueError("Unknown robot")
            if not core.reservations.reserve(**p):
                return "REJECTED", stream, seq
        elif kind == "OCCUPIED":
            station = core.reservations.get_station(p["station_id"])
            robot = core.tracker.get_robot(p["robot_id"])
            if (station is None or robot is None
                    or station.reserved_by_robot_id not in (None, robot.robot_id)
                    or station.occupied_by_robot_id not in (None, robot.robot_id)
                    or not station.is_physically_occupied(robot.pose)):
                return "REJECTED", stream, seq
            if not core.reservations.mark_occupied(**p):
                return "REJECTED", stream, seq
        elif kind == "RELEASE":
            if not core.reservations.initiate_release(**p):
                return "REJECTED", stream, seq
        else:
            raise ValueError(f"Unknown event kind: {kind}")
        return "APPLIED", stream, seq

    def _command_current(self, command):
        task = self._core._active_tasks.get(command["task_id"])
        return bool(task and task.goal_uuid == command["goal_uuid"]
                    and task.assignment_epoch == command["assignment_epoch"]
                    and (command["kind"] != "CANCEL_TASK"
                         or task.assigned_robot_id in self._core._pending_preemption_assignments))

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
