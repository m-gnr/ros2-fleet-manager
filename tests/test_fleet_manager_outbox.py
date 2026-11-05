"""SQLite failure boundaries and real asyncio producer interleavings."""
import asyncio
from contextlib import asynccontextmanager, closing
import json
import sqlite3

import pytest

from backend.fleet_manager.adapters.route_cache import CachedRouteDistanceProvider, RouteCache
from backend.fleet_manager.domain import (
    FleetManagerCore, Pose2D, ReservationState, RobotState, StationType, TaskResultStatus,
)
from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
from backend.fleet_manager.persistence import SQLiteStore, ScenarioResetRequired


class Routes:
    def get_path_distance(self, robot_id, start, goal):
        return 1.0


@pytest.fixture
def runtime(tmp_path):
    store = SQLiteStore(tmp_path / "scenario.db")
    core = FleetManagerCore(Routes(), Pose2D())
    core.register_robot("r1")
    core.register_robot("r2")
    core.register_station("dock", StationType.CHARGING, Pose2D())
    loop = FleetEventLoop(store, core)
    yield loop
    store.close()


def status(robot="r1", seq=1, epoch=0, task=None, state=1, phase=0, pose=None, timestamp=10, session=None,
           **source):
    return Event("ROBOT_STATUS", dict(robot_id=robot, status_seq=seq, current_epoch=epoch,
        current_task_id=task, state=state, current_phase=phase, is_loaded=False,
        pose=pose or Pose2D(), battery_soc_percent=100, battery_energy_wh=100,
        timestamp_sec=timestamp, publisher_session_id=session, **source))


def submit(task="t1", priority=3, created_at=1):
    return Event("SUBMIT_TASK", dict(task_id=task, pickup_pose=Pose2D(1, 0),
        dropoff_pose=Pose2D(2, 0), priority=priority, created_at=created_at))


def action(loop, kind="ACTION_RESULT", **changes):
    task = loop.core._active_tasks_by_robot["r1"]
    payload = dict(robot_id="r1", task_id=task.task_id, assignment_epoch=task.assignment_epoch,
                   goal_uuid=task.goal_uuid)
    if kind == "ACTION_RESULT":
        payload.update(result_status=1, completed_epoch=task.assignment_epoch)
    elif kind == "ACTION_FEEDBACK":
        payload.update(status_seq=1, current_phase=1)
    else:
        payload["accepted"] = True
        payload["cancel_command_id"] = [r for r in rows(loop, "outbox_events") if r["kind"] == "CANCEL_TASK"][-1]["command_id"]
    payload.update(changes)
    return Event(kind, payload)


def rows(loop, table):
    return [dict(row) for row in loop.store.connection.execute(f"SELECT * FROM {table}")]


async def assign(loop):
    await loop.submit(status())
    await loop.submit(submit())
    await loop.submit(Event("TICK", {"current_time": 10}))


def test_atomic_assignment_reservation_and_outbox(runtime):
    async def scenario():
        await runtime.start()
        await runtime.submit(status())
        await runtime.submit(Event("RESERVE", dict(station_id="dock", robot_id="r1")))
        await runtime.submit(Event("OCCUPIED", dict(station_id="dock", robot_id="r1")))
        await runtime.submit(submit())
        await runtime.submit(Event("TICK", {"current_time": 10}))
        assert rows(runtime, "tasks")[0]["status"] == "ASSIGNED"
        assert rows(runtime, "reservations")[0]["state"] == "RELEASING"
        command = rows(runtime, "outbox_events")[0]
        assert command["state"] == "PENDING"
        assert json.loads(command["payload"])["goal_uuid"] == runtime.core._active_tasks["t1"].goal_uuid
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("kind, initial_state", [
    ("RESERVE", ReservationState.FREE),
    ("OCCUPIED", ReservationState.RESERVED),
    ("RELEASE", ReservationState.RESERVED),
    ("RELEASE", ReservationState.OCCUPIED),
])
def test_blocked_session_rejects_station_events(runtime, kind, initial_state):
    async def scenario():
        await runtime.start()
        station = {"station_id": "dock", "robot_id": "r1"}
        assert await runtime.submit(status(session="original")) == "APPLIED"
        assert await runtime.submit(status("r2", session="other")) == "APPLIED"
        if initial_state != ReservationState.FREE:
            assert await runtime.submit(Event("RESERVE", station)) == "APPLIED"
        if initial_state == ReservationState.OCCUPIED:
            assert await runtime.submit(Event("OCCUPIED", station)) == "APPLIED"
        await runtime.submit(submit())
        tables = ("robots", "tasks", "reservations", "outbox_events")
        initial_reservations = rows(runtime, "reservations")
        assert await runtime.submit(status(session="restart", pose=Pose2D(5, 0))) == "SESSION_BLOCKED"
        assert await runtime.submit(status(seq=2, session="restart")) == "SESSION_BLOCKED"
        assert await runtime.submit(status(seq=3, session="original")) == "SESSION_BLOCKED"
        assert runtime.core.tracker.get_robot("r1").session_id == "original"
        assert rows(runtime, "reservations") == initial_reservations
        before = {name: rows(runtime, name) for name in tables}
        event = Event(kind, station)
        assert await runtime.submit(event) == "REJECTED"
        assert await runtime.submit(event) == "DUPLICATE"
        assert [row["outcome"] for row in rows(runtime, "processed_events")
                if row["event_id"] == event.event_id] == ["REJECTED"]
        if initial_state != ReservationState.FREE:
            assert await runtime.submit(Event("RESERVE", {**station, "robot_id": "r2"})) == "REJECTED"
        assert {name: rows(runtime, name) for name in tables} == before
        assert runtime.core.reservations.get_station("dock").state == initial_state
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("through_consumer", [True, False], ids=["consumer", "domain"])
def test_blocked_session_cannot_apply_departure(runtime, through_consumer):
    async def scenario():
        await runtime.start()
        station = {"station_id": "dock", "robot_id": "r1"}
        await runtime.submit(status(session="original"))
        await runtime.submit(Event("RESERVE", station))
        await runtime.submit(Event("OCCUPIED", station))
        assert await runtime.submit(Event("RELEASE", station)) == "APPLIED"
        restart = status(session="restart", pose=Pose2D(5, 0))
        if through_consumer:
            assert await runtime.submit(restart) == "SESSION_BLOCKED"
            anonymous = status(seq=2, pose=Pose2D(5, 0))
            assert await runtime.submit(anonymous) == "SESSION_BLOCKED"
            assert rows(runtime, "reservations")[0]["state"] == "RELEASING"
            core = runtime.core
        else:
            core = runtime.core
            payload = {key: value for key, value in restart.payload.items() if key != "status_seq"}
            core.handle_robot_status(**payload)
        record = core.reservations.get_station("dock")
        assert record.state == ReservationState.RELEASING
        assert record.reserved_by_robot_id == record.occupied_by_robot_id == "r1"
        assert core.tracker.get_robot("r1").pose == Pose2D()
        await runtime.close()
    asyncio.run(scenario())


def test_trusted_session_release_requires_ordered_physical_departure(runtime):
    async def scenario():
        await runtime.start()
        station = {"station_id": "dock", "robot_id": "r1"}
        await runtime.submit(status(seq=2, session="original"))
        reserve = Event("RESERVE", station)
        assert await runtime.submit(reserve) == "APPLIED"
        assert await runtime.submit(Event("OCCUPIED", station)) == "APPLIED"
        assert await runtime.submit(Event("RELEASE", station)) == "APPLIED"
        for seq in (1, 2):
            late = status(seq=seq, session="original", pose=Pose2D(5, 0))
            assert await runtime.submit(late) == "STALE"
        assert rows(runtime, "reservations")[0]["state"] == "RELEASING"
        assert await runtime.submit(status(seq=3, session="original", pose=Pose2D(5, 0))) == "APPLIED"
        assert await runtime.submit(reserve) == "DUPLICATE"
        assert rows(runtime, "reservations")[0]["state"] == "FREE"
        await runtime.close()
    asyncio.run(scenario())


def recovery_status(seq, pose, *, state=RobotState.STATE_IDLE, session="original",
                    timestamp=10, source_ns=None, valid_until=12):
    source_ns = seq * 10**9 if source_ns is None else source_ns
    event = status(seq=seq, state=state, pose=pose, session=session, timestamp=timestamp,
                   source_status_ns=source_ns, pose_sample_ns=source_ns, pose_valid_until=valid_until)
    event.payload["pose"] = pose
    return event


async def block_dock(runtime, *, session="original", occupied=True):
    station = {"station_id": "dock", "robot_id": "r1"}
    assert await runtime.submit(recovery_status(1, Pose2D(), session=session)) == "APPLIED"
    assert await runtime.submit(Event("RESERVE", station)) == "APPLIED"
    if occupied:
        assert await runtime.submit(Event("OCCUPIED", station)) == "APPLIED"
    assert await runtime.submit(
        recovery_status(2, Pose2D(), state=RobotState.STATE_ERROR, session=session)
    ) == "APPLIED"
    assert rows(runtime, "reservations")[0]["state"] == "BLOCKED"
    return station


@pytest.mark.parametrize("pose, accepted", [
    (Pose2D(), False),
    (Pose2D(0.30), False),
    (Pose2D(0.34), False),
    (Pose2D(0.35), False),
    (Pose2D(0.35001), True),
    (None, False),
    (Pose2D(float("nan")), False),
    (Pose2D(float("inf")), False),
    (Pose2D(1, float("-inf")), False),
    (Pose2D("invalid"), False),
    (Pose2D(1, frame_id="odom"), False),
    (Pose2D(1, frame_id=""), False),
])
def test_unblock_requires_physical_departure_and_preserves_ownership(runtime, monkeypatch, pose, accepted):
    monkeypatch.setattr(runtime, "_clock", lambda: 11)

    async def scenario():
        await runtime.start()
        station = await block_dock(runtime)
        before = rows(runtime, "reservations")
        assert await runtime.submit(Event("RELEASE", station)) == "REJECTED"
        assert await runtime.submit(recovery_status(3, pose)) == "APPLIED"
        assert rows(runtime, "reservations") == before  # Status never unblocks by itself.
        event = Event("UNBLOCK", station)
        outcome = "APPLIED" if accepted else "REJECTED"
        assert await runtime.submit(event) == outcome
        assert rows(runtime, "processed_events")[-1]["outcome"] == outcome
        assert await runtime.submit(event) == "DUPLICATE"
        if accepted:
            record = runtime.core.reservations.get_station("dock")
            assert record.state == ReservationState.FREE
            assert record.reserved_by_robot_id is record.occupied_by_robot_id is None
        else:
            assert rows(runtime, "reservations") == before
            record = runtime.core.reservations.get_station("dock")
            assert record.state == ReservationState.BLOCKED
            assert record.reserved_by_robot_id == record.occupied_by_robot_id == "r1"
        assert await runtime.submit(Event("RESERVE", {**station, "robot_id": "r2"})) == outcome
        await runtime.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("case", [
    "stale_receipt", "expired_pose", "still_error", "session_change", "unbound_owner",
    "other_robot", "duplicate", "old_seq", "old_receipt", "replayed_sample", "anonymous",
    "older_sample",
])
def test_unblock_rejects_untrusted_evidence(runtime, monkeypatch, case):
    now = [11.0]
    monkeypatch.setattr(runtime, "_clock", lambda: now[0])

    async def scenario():
        await runtime.start()
        station = await block_dock(runtime, session=None if case == "unbound_owner" else "original",
                                   occupied=False)
        before = rows(runtime, "reservations")
        departed = recovery_status(3, Pose2D(1))
        expected_status = "APPLIED"
        if case == "stale_receipt":
            # Apply while fresh, then age out before the operator event.
            now[0] = 10.5
        elif case == "expired_pose":
            departed.payload["pose_valid_until"] = 10.5
        elif case == "still_error":
            departed.payload["state"] = RobotState.STATE_ERROR
        elif case == "session_change":
            # Even a previously valid sample cannot be used after session change.
            assert await runtime.submit(departed) == "APPLIED"
            departed = recovery_status(4, Pose2D(1), session="restart")
            expected_status = "SESSION_BLOCKED"
        elif case == "other_robot":
            departed.payload["robot_id"] = "r2"
        elif case in ("duplicate", "old_seq"):
            departed.payload["status_seq"] = 2 if case == "duplicate" else 1
            expected_status = "STALE"
        elif case == "old_receipt":
            departed.payload["timestamp_sec"] = 9
            expected_status = "STALE"
        elif case == "replayed_sample":
            departed.payload["pose_sample_ns"] = 2 * 10**9
        elif case == "older_sample":
            departed.payload["pose_sample_ns"] = 10**9
        elif case == "anonymous":
            departed.payload["publisher_session_id"] = None
        assert await runtime.submit(departed) == expected_status
        if case == "stale_receipt":
            now[0] = 12.01
        if case == "other_robot":
            assert await runtime.submit(Event("UNBLOCK", {**station, "robot_id": "r2"})) == "REJECTED"
        assert await runtime.submit(Event("UNBLOCK", station)) == "REJECTED"
        assert await runtime.submit(Event("RESERVE", {**station, "robot_id": "r2"})) == "REJECTED"
        assert rows(runtime, "reservations")[0]["state"] == "BLOCKED"
        assert rows(runtime, "reservations")[0]["reserved_by"] == "r1"
        assert rows(runtime, "reservations")[0]["occupied_by"] is None
        if case != "still_error":
            assert rows(runtime, "reservations") == before
        await runtime.close()

    asyncio.run(scenario())


def test_unblock_commit_failure_preserves_state_and_can_retry(runtime, monkeypatch):
    monkeypatch.setattr(runtime, "_clock", lambda: 11)

    async def scenario():
        await runtime.start()
        station = await block_dock(runtime)
        assert await runtime.submit(recovery_status(3, Pose2D(1))) == "APPLIED"
        event = Event("UNBLOCK", station)
        tables = ("reservations", "robots", "processed_events", "outbox_events")
        before = {table: rows(runtime, table) for table in tables}
        connection = runtime.store.connection
        deny = True

        def deny_commit(operation, argument, *_):
            if deny and operation == sqlite3.SQLITE_TRANSACTION and argument == "COMMIT":
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        connection.set_authorizer(deny_commit)
        with pytest.raises(sqlite3.DatabaseError):
            await runtime.submit(event)
        deny = False
        assert {table: rows(runtime, table) for table in tables} == before
        assert runtime.core.reservations.get_station("dock").state == ReservationState.BLOCKED
        assert await runtime.submit(event) == "APPLIED"
        assert rows(runtime, "reservations")[0]["state"] == "FREE"
        await runtime.close()

    asyncio.run(scenario())


def test_failed_result_requires_observed_error_before_recovery(runtime, monkeypatch):
    monkeypatch.setattr(runtime, "_clock", lambda: 11)

    async def scenario():
        await runtime.start()
        station = {"station_id": "dock", "robot_id": "r1"}
        await runtime.submit(recovery_status(1, Pose2D()))
        await runtime.submit(Event("RESERVE", station))
        await runtime.submit(submit())
        await runtime.submit(Event("TICK", {"current_time": 10}))
        assert await runtime.submit(action(runtime, result_status=2)) == "APPLIED"
        for seq, state, expected in [
            (2, RobotState.STATE_IDLE, "REJECTED"),
            (3, RobotState.STATE_ERROR, "REJECTED"),
            (4, RobotState.STATE_IDLE, "APPLIED"),
        ]:
            telemetry = recovery_status(seq, Pose2D(1), state=state)
            telemetry.payload["current_epoch"] = 1
            assert await runtime.submit(telemetry) == "APPLIED"
            assert await runtime.submit(Event("UNBLOCK", station)) == expected
        assert rows(runtime, "tasks")[0]["status"] == "FAILED"
        await runtime.close()

    asyncio.run(scenario())


def test_blocked_session_pending_preemption_does_not_start_resource_release(runtime):
    async def scenario():
        await runtime.start()
        await runtime.submit(status(session="original"))
        await preempt(runtime)
        station = {"station_id": "dock", "robot_id": "r1"}
        await runtime.submit(Event("RESERVE", station))
        await runtime.submit(Event("OCCUPIED", station))
        restart = status(session="restart", epoch=1, task="t1")
        assert await runtime.submit(restart) == "SESSION_BLOCKED"
        assert await runtime.submit(action(runtime, result_status=3)) == "APPLIED"
        assert rows(runtime, "reservations")[0]["state"] == "OCCUPIED"
        assert runtime.core.queue.get("high") is not None
        assert not runtime.core._active_tasks_by_robot
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("table", ["tasks", "reservations", "outbox_events", "processed_events"])
def test_sqlite_failure_rolls_back_memory_and_all_tables(runtime, table):
    async def scenario():
        await runtime.start()
        await runtime.submit(status())
        await runtime.submit(Event("RESERVE", dict(station_id="dock", robot_id="r1")))
        await runtime.submit(submit())
        before = {name: rows(runtime, name) for name in ("robots", "tasks", "reservations", "outbox_events", "processed_events")}
        runtime.store.connection.execute(
            f"CREATE TRIGGER fail_write BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT, 'injected'); END"
        )
        event = Event("TICK", {"current_time": 10})
        with pytest.raises(sqlite3.IntegrityError, match="injected"):
            await runtime.submit(event)
        assert not runtime.core._active_tasks
        assert {name: rows(runtime, name) for name in before} == before
        runtime.store.connection.execute("DROP TRIGGER fail_write")
        assert await runtime.submit(event) == "APPLIED"
        assert len(rows(runtime, "outbox_events")) == 1
        await runtime.close()
    asyncio.run(scenario())


def test_duplicate_ids_and_terminal_identity(runtime):
    async def scenario():
        await runtime.start()
        await assign(runtime)
        result = action(runtime)
        assert await runtime.submit(result) == "APPLIED"
        assert await runtime.submit(result) == "DUPLICATE"
        assert await runtime.submit(Event(result.kind, result.payload)) == "STALE"
        with pytest.raises(ValueError, match="already exists"):
            await runtime.submit(submit())
        assert rows(runtime, "tasks")[0]["status"] == "COMPLETED"
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("change", [{"task_id": "old"}, {"assignment_epoch": 0}, {"goal_uuid": "old"}])
def test_each_assignment_identity_component_is_required(runtime, change):
    async def scenario():
        await runtime.start()
        await assign(runtime)
        assert await runtime.submit(action(runtime, **change)) == "STALE"
        assert runtime.core._active_tasks["t1"].status == "ASSIGNED"
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("result_status", [1, 2, 3], ids=["succeeded", "failed", "preempted"])
def test_invalid_terminal_epochs_preserve_ownership_and_sqlite(runtime, result_status, caplog):
    async def scenario():
        await runtime.start()
        await runtime.submit(status())
        await runtime.submit(Event("RESERVE", dict(station_id="dock", robot_id="r1")))
        await preempt(runtime)
        valid = action(runtime, result_status=result_status)
        missing_epoch = dict(valid.payload)
        del missing_epoch["completed_epoch"]
        invalid_payloads = [missing_epoch] + [
            dict(valid.payload, completed_epoch=epoch)
            for epoch in (None, 0, -1, 99, "1", True, 1.0, 2**64)
        ]
        before = {table: rows(runtime, table) for table in ("tasks", "robots", "reservations", "outbox_events")}
        processed = rows(runtime, "processed_events")
        for payload in invalid_payloads:
            event = Event("ACTION_RESULT", payload)
            assert await runtime.submit(event) == "STALE"
            entry = rows(runtime, "processed_events")[-1]
            assert (entry["event_id"], entry["outcome"]) == (event.event_id, "STALE")
            assert (entry["task_id"], entry["assignment_epoch"], entry["goal_uuid"]) == (
                payload["task_id"], payload["assignment_epoch"], payload["goal_uuid"],
            )
            active = runtime.core._active_tasks_by_robot["r1"]
            assert (active.task_id, active.assignment_epoch, active.goal_uuid) == (
                payload["task_id"], payload["assignment_epoch"], payload["goal_uuid"],
            )
            assert active.preemption_count == 0
            assert runtime.core._pending_preemption_assignments["r1"].task_id == "high"
            assert {table: rows(runtime, table) for table in before} == before
        assert rows(runtime, "processed_events")[:len(processed)] == processed
        assert "ACTION_RESULT completed_epoch" in caplog.text
        assert await runtime.submit(valid) == "APPLIED"
        await runtime.close()
    asyncio.run(scenario())


def test_status_sequence_epoch_and_feedback_order(runtime):
    async def scenario():
        await runtime.start()
        await assign(runtime)
        assert await runtime.submit(status(seq=2, epoch=1, task="t1", state=2, phase=2)) == "APPLIED"
        assert await runtime.submit(status(seq=1, epoch=1, task="t1", state=2, phase=1)) == "STALE"
        assert await runtime.submit(status(seq=3, epoch=0)) == "STALE"
        assert runtime.core.tracker.get_robot("r1").current_phase == 2
        assert await runtime.submit(action(runtime, "ACTION_FEEDBACK", status_seq=9)) == "APPLIED"
        assert await runtime.submit(action(runtime, "ACTION_FEEDBACK", status_seq=8)) == "STALE"
        assert await runtime.submit(action(runtime)) == "APPLIED"
        await runtime.close()
    asyncio.run(scenario())


def test_idle_before_terminal_cannot_double_assign(runtime):
    async def scenario():
        await runtime.start()
        await assign(runtime)
        await runtime.submit(status(seq=2, epoch=1))
        await runtime.submit(submit("t2"))
        await runtime.submit(Event("TICK", {"current_time": 10}))
        assert list(runtime.core._active_tasks) == ["t1"]
        await runtime.submit(action(runtime))
        await runtime.submit(Event("TICK", {"current_time": 10}))
        assert list(runtime.core._active_tasks) == ["t2"]
        await runtime.close()
    asyncio.run(scenario())


async def preempt(loop):
    await assign(loop)
    await loop.submit(status(seq=2, epoch=1, task="t1", state=2, phase=1))
    await loop.submit(submit("high", 1))
    await loop.submit(Event("TICK", {"current_time": 10}))


@pytest.mark.parametrize("idle_first", [False, True], ids=["terminal-first", "idle-first"])
def test_preemption_waits_for_terminal_and_records_new_assignment(runtime, idle_first):
    async def scenario():
        await runtime.start()
        await preempt(runtime)
        await runtime.submit(submit("younger-low", created_at=2))
        tick = Event("TICK", {"current_time": 10})
        assert [r["kind"] for r in rows(runtime, "outbox_events")] == ["EXECUTE_TASK", "CANCEL_TASK"]
        await runtime.submit(action(runtime, "CANCEL_RESPONSE"))
        idle = status(seq=3, epoch=1, session="original")
        if idle_first:
            await runtime.submit(idle)
        await runtime.submit(tick)
        assert list(runtime.core._active_tasks) == ["t1"]

        terminal = action(runtime, result_status=TaskResultStatus.STATUS_PREEMPTED)
        assert await runtime.submit(terminal) == "APPLIED"
        assert not runtime.core._pending_preemption_assignments
        assert not runtime.core._active_tasks
        assert len(rows(runtime, "outbox_events")) == 2
        assert runtime.core.queue.get("high").created_at == 1
        assert [t.task_id for t in runtime.core.queue.iter_assignable_tasks()] == [
            "high", "t1", "younger-low",
        ]
        assert runtime.core.queue.get("t1").preemption_count == 1
        assert runtime.core.queue.get("t1").created_at == 1
        if not idle_first:
            await runtime.submit(Event(tick.kind, tick.payload))
            assert not runtime.core._active_tasks
            await runtime.submit(idle)

        await runtime.submit(Event(tick.kind, tick.payload))
        assert list(runtime.core._active_tasks) == ["high"]
        command = rows(runtime, "outbox_events")[-1]
        assert (command["kind"], command["task_id"], command["assignment_epoch"]) == (
            "EXECUTE_TASK", "high", terminal.payload["assignment_epoch"] + 1,
        )
        assert command["goal_uuid"] != terminal.payload["goal_uuid"]
        assert await runtime.submit(terminal) == "DUPLICATE"
        assert await runtime.submit(Event(terminal.kind, terminal.payload)) == "STALE"
        assert len(rows(runtime, "outbox_events")) == 3
        assert runtime.core.queue.get("t1").preemption_count == 1
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("blocker", [
    "session", "stale", "low-energy", "invalid-soc", "missing-pickup", "missing-dropoff",
    "missing-escape", "expired", "invalidated", "negative-pickup", "nonfinite-dropoff",
    "other-task", "loaded", "error",
])
def test_preempted_high_rechecks_assignment_eligibility(tmp_path, blocker):
    async def scenario():
        now = [10.0]
        cache = RouteCache()
        core = FleetManagerCore(CachedRouteDistanceProvider(cache, clock=lambda: now[0]), Pose2D())
        core.register_robot("r1")
        core.register_station("dock", StationType.CHARGING, Pose2D())
        legs = [(Pose2D(), Pose2D(1, 0)), (Pose2D(1, 0), Pose2D(2, 0)), (Pose2D(2, 0), Pose2D())]
        for leg in legs:
            cache.put("r1", *leg, 1.0, now=now[0])
        store = SQLiteStore(tmp_path / "eligibility.db")
        loop = FleetEventLoop(store, core)
        await loop.start()
        try:
            await loop.submit(status(session="original"))
            await preempt(loop)
            terminal = action(loop, result_status=TaskResultStatus.STATUS_PREEMPTED)
            assert "r1" in loop.core._pending_preemption_assignments
            station = {"station_id": "dock", "robot_id": "r1"}
            await loop.submit(Event("RESERVE", station))
            await loop.submit(Event("OCCUPIED", station))

            if blocker == "stale":
                now[0] += 2.1
            if blocker == "expired":
                now[0] += cache.ttl_sec + 0.1
            if blocker == "invalidated":
                cache.invalidate_map_revision("new-map")

            # A changed pose invalidates the original pickup lookup. The other
            # two missing-leg cases keep the remaining cached legs available.
            if blocker in ("missing-dropoff", "missing-escape"):
                cache.invalidate_all()
                missing_index = 1 if blocker == "missing-dropoff" else 2
                for i, leg in enumerate(legs):
                    if i != missing_index:
                        cache.put("r1", *leg, 1.0, now=now[0])
            if blocker == "negative-pickup":
                cache.put("r1", *legs[0], -0.1, now=now[0])
            if blocker == "nonfinite-dropoff":
                cache.put("r1", *legs[1], float("nan"), now=now[0])

            timestamp = 10.0 if blocker == "stale" else now[0]
            update = status(seq=3, epoch=1, timestamp=timestamp, session="original")
            if blocker == "session":
                await loop.submit(status(seq=3, epoch=1, timestamp=timestamp, session="original"))
                update = status(seq=4, epoch=1, timestamp=timestamp, session="restart")
            if blocker == "missing-pickup":
                update.payload["pose"] = Pose2D(0.2, 0)
            if blocker == "low-energy":
                update.payload.update(battery_soc_percent=8.0, battery_energy_wh=8.0)
            if blocker == "invalid-soc":
                update.payload.update(battery_soc_percent=101.0, battery_energy_wh=101.0)
            if blocker == "loaded":
                update.payload["is_loaded"] = True
            if blocker == "error":
                update.payload["state"] = RobotState.STATE_ERROR

            if blocker != "other-task":
                expected = "SESSION_BLOCKED" if blocker == "session" else "APPLIED"
                assert await loop.submit(update) == expected
            before = rows(loop, "reservations")
            assert await loop.submit(terminal) == "APPLIED"
            if blocker == "other-task":
                # Report ownership unknown to FM after the victim has closed.
                update.payload.update(current_task_id="other", current_epoch=2)
                assert await loop.submit(update) == "APPLIED"
            await loop.submit(Event("TICK", {"current_time": now[0]}))
            assert not loop.core._pending_preemption_assignments
            assert not loop.core._active_tasks
            assert not loop.core._failed_tasks
            assert loop.core.queue.get("high").created_at == 1
            assert loop.core.queue.get("t1").preemption_count == 1
            assert rows(loop, "reservations") == before
            assert [r["state"] for r in rows(loop, "outbox_events")] == ["SUPERSEDED", "SUPERSEDED"]
            if blocker == "other-task":
                assert loop.core.tracker.get_robot("r1").current_task_id == "other"
        finally:
            await loop.close()
            store.close()
    asyncio.run(scenario())


def test_requeued_high_cannot_replace_another_active_owner(runtime):
    async def scenario():
        await runtime.start()
        await preempt(runtime)
        await runtime.submit(submit("older-high", priority=1, created_at=0))
        await runtime.submit(action(runtime, result_status=TaskResultStatus.STATUS_PREEMPTED))
        await runtime.submit(status(seq=3, epoch=1))
        await runtime.submit(Event("TICK", {"current_time": 10}))
        other = runtime.core._active_tasks_by_robot["r1"]
        assert other.task_id == "older-high"

        # IDLE can arrive before the other assignment's matching terminal result.
        await runtime.submit(status(seq=4, epoch=other.assignment_epoch))
        before = rows(runtime, "outbox_events")
        await runtime.submit(Event("TICK", {"current_time": 10}))
        assert runtime.core._active_tasks_by_robot["r1"] == other
        assert runtime.core.queue.get("high").created_at == 1
        assert rows(runtime, "outbox_events") == before
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["ACTION_RESULT", "TICK"])
def test_commit_failure_after_preemption_preserves_domain_and_outbox(runtime, kind):
    async def scenario():
        await runtime.start()
        await preempt(runtime)
        station = {"station_id": "dock", "robot_id": "r1"}
        await runtime.submit(Event("RESERVE", station))
        await runtime.submit(Event("OCCUPIED", station))
        await runtime.submit(status(seq=3, epoch=1))
        terminal = action(runtime, result_status=TaskResultStatus.STATUS_PREEMPTED)
        event = terminal
        if kind == "TICK":
            assert await runtime.submit(terminal) == "APPLIED"
            event = Event("TICK", {"current_time": 10})

        tables = ("robots", "tasks", "reservations", "outbox_events", "processed_events")
        before = {table: rows(runtime, table) for table in tables}
        before_core = runtime.core
        connection = runtime.store.connection

        def deny_commit(operation, argument, *_):
            if operation == sqlite3.SQLITE_TRANSACTION and argument == "COMMIT":
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        connection.set_authorizer(deny_commit)
        try:
            with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
                await runtime.submit(event)
        finally:
            # Python 3.10 does not support disabling the authorizer with None.
            connection.set_authorizer(lambda *_: sqlite3.SQLITE_OK)
        assert {table: rows(runtime, table) for table in tables} == before
        assert runtime.core._active_tasks == before_core._active_tasks
        assert runtime.core._pending_preemption_assignments == before_core._pending_preemption_assignments
        assert list(runtime.core.queue.iter_assignable_tasks()) == list(before_core.queue.iter_assignable_tasks())
        assert await runtime.submit(event) == "APPLIED"
        if kind == "ACTION_RESULT":
            assert runtime.core.queue.get("t1").preemption_count == 1
            assert runtime.core.queue.get("high").created_at == 1
        else:
            assert list(runtime.core._active_tasks) == ["high"]
            assert len(rows(runtime, "outbox_events")) == 3
            assert rows(runtime, "reservations")[0]["state"] == "RELEASING"
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("result, status_name", [
    (TaskResultStatus.STATUS_SUCCEEDED, "COMPLETED"),
    (TaskResultStatus.STATUS_FAILED, "FAILED"),
])
def test_terminal_during_cancel_does_not_strand_high(runtime, result, status_name):
    async def scenario():
        await runtime.start()
        await preempt(runtime)
        await runtime.submit(action(runtime, "CANCEL_RESPONSE"))
        assert await runtime.submit(action(runtime, result_status=result)) == "APPLIED"
        assert runtime.core.queue.get("high").created_at == 1
        assert runtime.core.queue.get("t1") is None
        assert not runtime.core._pending_preemption_assignments
        assert not runtime.core._active_tasks
        victim = next(row for row in rows(runtime, "tasks") if row["task_id"] == "t1")
        assert victim["status"] == status_name
        assert json.loads(victim["snapshot"])["preemption_count"] == 0
        assert [row["state"] for row in rows(runtime, "outbox_events")] == ["SUPERSEDED", "SUPERSEDED"]
        await runtime.close()
    asyncio.run(scenario())


def test_rejected_cancel_can_be_requested_again(runtime):
    async def scenario():
        await runtime.start()
        await preempt(runtime)
        old_response = action(runtime, "CANCEL_RESPONSE", accepted=False)
        await runtime.submit(old_response)
        await runtime.submit(Event("TICK", {"current_time": 10}))
        assert await runtime.submit(Event(old_response.kind, old_response.payload)) == "STALE"
        cancels = [r for r in rows(runtime, "outbox_events") if r["kind"] == "CANCEL_TASK"]
        assert len(cancels) == 2
        assert cancels[0]["state"] == "SUPERSEDED"
        assert cancels[1]["state"] == "PENDING"
        await runtime.close()
    asyncio.run(scenario())


def test_retry_preserves_identity_and_blocks_later_send(runtime):
    async def scenario():
        await runtime.start()
        await assign(runtime)
        await runtime.submit(status("r2"))
        await runtime.submit(submit("t2"))
        await runtime.submit(Event("TICK", {"current_time": 10}))
        seen = []
        now = [20.0]
        async def sender(command):
            seen.append(command["command_id"])
            if len(seen) == 1:
                raise OSError("delivery uncertain")
        dispatcher = OutboxDispatcher(runtime, sender, clock=lambda: now[0], retry_delay=2)
        assert await dispatcher.send_one()
        assert rows(runtime, "outbox_events")[0]["state"] == "RETRY"
        assert not await dispatcher.send_one()
        now[0] = 22
        assert await dispatcher.send_one()
        assert await dispatcher.send_one()
        assert seen[0] == seen[1] != seen[2]
        assert [r["state"] for r in rows(runtime, "outbox_events")] == ["SENT", "SENT"]
        assert [r["attempts"] for r in rows(runtime, "outbox_events")] == [2, 1]
        await runtime.close()
    asyncio.run(scenario())


def test_sending_does_not_block_consumer_and_late_failure_is_superseded(runtime):
    async def scenario():
        await runtime.start()
        await assign(runtime)
        entered, release = asyncio.Event(), asyncio.Event()
        async def sender(command):
            entered.set()
            await release.wait()
            raise OSError("late failure")
        dispatcher = OutboxDispatcher(runtime, sender, clock=lambda: 10, retry_delay=1)
        sending = asyncio.create_task(dispatcher.send_one())
        await entered.wait()
        assert not await dispatcher.send_one()
        await runtime.submit(action(runtime))
        release.set()
        await sending
        assert rows(runtime, "outbox_events")[0]["state"] == "SUPERSEDED"
        assert not await dispatcher.send_one()
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("state", ["PENDING", "SENDING", "RETRY", "SENT"])
def test_restart_preserves_evidence_but_refuses_resume(runtime, tmp_path, state):
    async def scenario():
        await runtime.start()
        await assign(runtime)
        runtime.store.connection.execute("UPDATE outbox_events SET state=?", (state,))
        await runtime.close()
    asyncio.run(scenario())
    reopened = SQLiteStore(tmp_path / "scenario.db")
    try:
        with pytest.raises(ScenarioResetRequired):
            FleetEventLoop(reopened, FleetManagerCore(Routes(), Pose2D()))
        assert reopened.connection.execute("SELECT state FROM outbox_events").fetchone()[0] == state
        assert reopened.connection.execute("SELECT status FROM tasks").fetchone()[0] == "ASSIGNED"
    finally:
        reopened.close()


def test_concurrent_producers_single_consumer_fifo_and_unique_assignment(runtime):
    async def scenario():
        await runtime.start()
        with pytest.raises(RuntimeError, match="already started"):
            await runtime.start()
        await runtime.submit(status())
        await runtime.submit(status("r2"))
        events = [submit(f"t{i}", created_at=i + 1) for i in range(30)]
        results = await asyncio.gather(*(runtime.submit(e) for e in events + events))
        assert results.count("APPLIED") == results.count("DUPLICATE") == 30
        await asyncio.gather(*(runtime.submit(Event("TICK", {"current_time": 10})) for _ in range(20)))
        assert set(runtime.core._active_tasks) == {"t0", "t1"}
        assert len(rows(runtime, "outbox_events")) == 2
        ids = [r["event_id"] for r in rows(runtime, "processed_events") if r["event_id"] in {e.event_id for e in events}]
        assert ids == [e.event_id for e in events]
        await runtime.close()
        with pytest.raises(RuntimeError):
            await runtime.submit(submit("late"))
    asyncio.run(scenario())


def test_communication_loss_no_automatic_failure_and_reservation_ownership(runtime, caplog):
    async def scenario():
        await runtime.start()
        await runtime.submit(status())
        assert await runtime.submit(Event("RESERVE", dict(station_id="dock", robot_id="r1"))) == "APPLIED"
        assert await runtime.submit(Event("RESERVE", dict(station_id="dock", robot_id="r2"))) == "REJECTED"
        assert await runtime.submit(Event("OCCUPIED", dict(station_id="dock", robot_id="r2"))) == "REJECTED"
        await runtime.submit(submit())
        await runtime.submit(Event("TICK", {"current_time": 10}))
        await runtime.submit(Event("TICK", {"current_time": 30}))
        assert runtime.core._active_tasks["t1"].status == "ASSIGNED"
        assert runtime.core.tracker.get_robot("r1").state != 6
        assert runtime.core.tracker.check_communication_health(30)[0][1] == "ALERT"
        assert "COMMUNICATION_WARNING" in caplog.text
        assert rows(runtime, "reservations")[0]["state"] == "RELEASING"
        await runtime.submit(status(seq=2, epoch=1, task="t1", state=2, pose=Pose2D(1, 0), timestamp=31))
        assert rows(runtime, "reservations")[0]["state"] == "FREE"
        await runtime.close()
    asyncio.run(scenario())


def test_commit_failure_rolls_back_published_state(runtime, monkeypatch):
    async def scenario():
        await runtime.start()
        await runtime.submit(status())
        await runtime.submit(submit())
        original = runtime.store.persist_core
        def invalid_reference(core):
            original(core)
            runtime.store.connection.execute("PRAGMA defer_foreign_keys=ON")
            runtime.store.connection.execute("UPDATE tasks SET robot_id='missing'")
        monkeypatch.setattr(runtime.store, "persist_core", invalid_reference)
        event = Event("TICK", {"current_time": 10})
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            await runtime.submit(event)
        assert rows(runtime, "tasks")[0]["status"] == "QUEUED"
        assert not rows(runtime, "outbox_events")
        assert not runtime.core._active_tasks
        monkeypatch.setattr(runtime.store, "persist_core", original)
        assert await runtime.submit(event) == "APPLIED"
        await runtime.close()
    asyncio.run(scenario())


def test_database_lock_failure_can_be_retried(runtime, tmp_path):
    async def scenario():
        await runtime.start()
        runtime.store.connection.execute("PRAGMA busy_timeout=1")
        other = sqlite3.connect(tmp_path / "scenario.db", isolation_level=None)
        try:
            other.execute("BEGIN IMMEDIATE")
            event = submit()
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                await runtime.submit(event)
            assert len(runtime.core.queue) == 0
            other.execute("ROLLBACK")
            assert await runtime.submit(event) == "APPLIED"
        finally:
            other.close()
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("result_status", [1, 2, 3], ids=["succeeded", "failed", "preempted"])
def test_old_result_after_next_assignment_and_invalid_result(runtime, result_status):
    async def scenario():
        await runtime.start()
        await assign(runtime)
        old = action(runtime)
        with pytest.raises(ValueError):
            await runtime.submit(action(runtime, result_status=99))
        assert "t1" in runtime.core._active_tasks
        await runtime.submit(old)
        await runtime.submit(status(seq=2, epoch=1))
        await runtime.submit(submit("t2"))
        await runtime.submit(Event("TICK", {"current_time": 10}))
        before = {table: rows(runtime, table) for table in ("tasks", "robots", "reservations", "outbox_events")}
        delayed = Event(old.kind, dict(old.payload, result_status=result_status))
        assert await runtime.submit(delayed) == "STALE"
        assert rows(runtime, "processed_events")[-1]["outcome"] == "STALE"
        assert {table: rows(runtime, table) for table in before} == before
        assert runtime.core._active_tasks["t2"].assignment_epoch == 2
        detached = runtime.core
        detached._active_tasks.clear()
        assert "t2" in runtime.core._active_tasks
        await runtime.close()
    asyncio.run(scenario())


def test_failed_result_blocks_resource_and_never_requeues(runtime):
    async def scenario():
        await runtime.start()
        await runtime.submit(status())
        await runtime.submit(Event("RESERVE", dict(station_id="dock", robot_id="r1")))
        await runtime.submit(submit())
        await runtime.submit(Event("TICK", {"current_time": 10}))
        await runtime.submit(action(runtime, result_status=2))
        await runtime.submit(status(seq=2, epoch=1, state=6))
        await runtime.submit(Event("TICK", {"current_time": 50}))
        assert rows(runtime, "tasks")[0]["status"] == "FAILED"
        assert rows(runtime, "reservations")[0]["state"] == "BLOCKED"
        assert len(runtime.core.queue) == 0
        await runtime.close()
    asyncio.run(scenario())


def test_cancelled_sender_records_uncertain_delivery_for_retry(runtime):
    async def scenario():
        await runtime.start()
        await assign(runtime)
        entered = asyncio.Event()
        async def sender(command):
            entered.set()
            await asyncio.Event().wait()
        dispatcher = OutboxDispatcher(runtime, sender, clock=lambda: 10, retry_delay=1)
        task = asyncio.create_task(dispatcher.send_one())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert rows(runtime, "outbox_events")[0]["state"] == "RETRY"
        await runtime.close()
    asyncio.run(scenario())


def test_process_crash_rolls_back_uncommitted_write(tmp_path):
    import subprocess
    import sys
    path = tmp_path / "crash.db"
    store = SQLiteStore(path)
    store.close()
    script = """
import os, sqlite3, sys
connection = sqlite3.connect(sys.argv[1], isolation_level=None)
connection.execute('BEGIN IMMEDIATE')
connection.execute("INSERT INTO processed_events(event_id,outcome) VALUES ('uncommitted','APPLIED')")
os._exit(17)
"""
    result = subprocess.run([sys.executable, "-c", script, str(path)], check=False)
    assert result.returncode == 17
    reopened = SQLiteStore(path)
    try:
        assert reopened.connection.execute("SELECT COUNT(*) FROM processed_events").fetchone()[0] == 0
        assert reopened.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        reopened.close()


def test_live_routes_resolve_before_selecting_nearest_robot(tmp_path):
    async def scenario():
        cache = RouteCache()
        provider = CachedRouteDistanceProvider(cache, clock=lambda: 10.0)
        core = FleetManagerCore(provider, Pose2D(3, 0))
        core.register_robot("r1")
        core.register_robot("r2")
        with closing(SQLiteStore(tmp_path / "live-routes.db")) as store:
            loop = FleetEventLoop(store, core, clock=lambda: 10.0)
            calls = []
            release_r2 = asyncio.Event()

            async def query(robot_id, start, goal):
                assert not store.connection.in_transaction
                calls.append((robot_id, start.x, goal.x))
                if robot_id == "r2":
                    await release_r2.wait()
                return 4.0 if robot_id == "r1" else 1.0

            loop.enable_live_routing(query)
            await loop.start()
            try:
                await loop.submit(status(session="r1-session"))
                await loop.submit(status("r2", session="r2-session"))
                await loop.submit(submit())
                await wait_for_routes(lambda: len(calls) == 4)
                assert loop.core.queue.get("t1") is not None
                assert not rows(loop, "outbox_events")
                release_r2.set()
                await wait_for_routes(lambda: bool(rows(loop, "outbox_events")))
                assert loop.core._active_tasks["t1"].assigned_robot_id == "r2"
                assert len(rows(loop, "outbox_events")) == 1
                assert sorted(calls) == [(robot, start, start + 1) for robot in ("r1", "r2") for start in range(3)]
            finally:
                await loop.close()
    asyncio.run(scenario())


async def wait_for_routes(condition):
    async def wait():
        while not condition():
            await asyncio.sleep(0.001)
    await asyncio.wait_for(wait(), timeout=2)


@asynccontextmanager
async def live_routing_runtime(tmp_path, query, now):
    cache = RouteCache()
    core = FleetManagerCore(CachedRouteDistanceProvider(cache, clock=lambda: now[0]), Pose2D(3, 0))
    core.register_robot("r1")
    with closing(SQLiteStore(tmp_path / "routing.db")) as store:
        loop = FleetEventLoop(store, core, clock=lambda: now[0])
        loop.enable_live_routing(query)
        await loop.start()
        try:
            await loop.submit(status(session="original"))
            yield loop, cache
        finally:
            await loop.close()


@pytest.mark.parametrize("missing_leg", [0, 1, 2])
def test_live_route_failure_keeps_task_queued_and_retries_on_later_tick(tmp_path, missing_leg):
    async def scenario():
        now = [10.0]
        calls = []
        available = False

        async def query(robot_id, start, goal):
            calls.append(start.x)
            return None if start.x == missing_leg and not available else 1.0

        async with live_routing_runtime(tmp_path, query, now) as (loop, cache):
            await loop.submit(submit())
            await wait_for_routes(lambda: len(calls) == missing_leg + 1)
            await wait_for_routes(lambda: sum(
                row["outcome"] == "ROUTE_APPLIED" for row in rows(loop, "processed_events")
            ) == missing_leg + 1)
            for _ in range(3):
                await loop.submit(Event("TICK", {"current_time": now[0]}))
            assert calls.count(missing_leg) == 1
            assert rows(loop, "tasks")[0]["status"] == "QUEUED"
            assert not rows(loop, "outbox_events")
            assert not loop.core._failed_tasks

            available = True
            now[0] += 2.0
            await loop.submit(Event("TICK", {"current_time": now[0]}))
            await wait_for_routes(lambda: bool(rows(loop, "outbox_events")))
            assert calls.count(missing_leg) == 2
            assert loop.core._active_tasks["t1"].assigned_robot_id == "r1"
            assert len(cache) == 0  # Assignment invalidates the task's route keys.
    asyncio.run(scenario())


def test_live_route_uses_escape_distance_and_latest_soc(tmp_path):
    async def scenario():
        now = [10.0]
        release = asyncio.Event()

        async def query(robot_id, start, goal):
            if start.x == 2:
                await release.wait()
                return 15.0
            return 1.0

        async with live_routing_runtime(tmp_path, query, now) as (loop, cache):
            await loop.submit(submit())
            await wait_for_routes(lambda: len(cache) == 2)
            update = status(seq=2, session="original")
            update.payload.update(battery_soc_percent=20.0, battery_energy_wh=20.0)
            await loop.submit(update)
            release.set()
            await wait_for_routes(lambda: len(cache) == 3)
            assert not rows(loop, "outbox_events")  # 12 Wh available, 13.4 Wh required.
            assert loop.core.queue.get("t1") is not None
            await loop.submit(status(seq=3, session="original"))
            assert len(rows(loop, "outbox_events")) == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("change", ["cell", "map", "session", "stale", "pose-sample"])
def test_live_route_drops_results_from_old_context(tmp_path, change):
    async def scenario():
        now = [10.0]
        started, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def query(robot_id, start, goal):
            calls.append(start)
            started.set()
            if len(calls) == 1:
                await release.wait()
                return 99.0
            return 1.0

        async with live_routing_runtime(tmp_path, query, now) as (loop, cache):
            await loop.submit(submit())
            await asyncio.wait_for(started.wait(), timeout=2)
            if change == "cell":
                await loop.submit(status(seq=2, pose=Pose2D(0.21, 0), session="original"))
            elif change == "map":
                cache.invalidate_map_revision("updated")
                cache.invalidate_map_revision("v1.0")
            elif change == "session":
                assert await loop.submit(status(seq=2, session="restarted")) == "SESSION_BLOCKED"
            elif change == "pose-sample":
                await loop.submit(status(seq=2, session="original", pose_valid_until=0.0))
            else:
                now[0] += 2.1
            release.set()

            await wait_for_routes(lambda: any(
                row["outcome"] == "STALE" and row["stream"] is None
                for row in rows(loop, "processed_events")
            ))
            assert cache.get("r1", Pose2D(), Pose2D(1, 0), now=now[0]) != 99.0
            if change in ("cell", "map"):
                await wait_for_routes(lambda: len(rows(loop, "outbox_events")) == 1)
                expected = Pose2D(0.21, 0) if change == "cell" else Pose2D()
                assert calls[1] == expected
            else:
                assert not rows(loop, "outbox_events")
                assert loop.core.queue.get("t1") is not None
                assert calls == [Pose2D()]
    asyncio.run(scenario())


def test_live_route_commit_failure_publishes_neither_cache_nor_assignment(tmp_path, caplog):
    async def scenario():
        now = [10.0]
        started, release = asyncio.Event(), asyncio.Event()

        async def query(robot_id, start, goal):
            started.set()
            await release.wait()
            return 1.0

        async with live_routing_runtime(tmp_path, query, now) as (loop, cache):
            await loop.submit(submit())
            await asyncio.wait_for(started.wait(), timeout=2)
            before = rows(loop, "processed_events")
            connection = loop.store.connection

            def deny_commit(operation, argument, *_):
                if operation == sqlite3.SQLITE_TRANSACTION and argument == "COMMIT":
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK

            connection.set_authorizer(deny_commit)
            try:
                release.set()
                await wait_for_routes(lambda: "Could not commit Nav2 route result" in caplog.text)
                assert rows(loop, "processed_events") == before
                assert len(cache) == 0
                assert not rows(loop, "outbox_events")
                assert loop.core.queue.get("t1") is not None
            finally:
                connection.set_authorizer(lambda *_: sqlite3.SQLITE_OK)

            await loop.submit(Event("TICK", {"current_time": now[0]}))
            await wait_for_routes(lambda: bool(rows(loop, "outbox_events")))
            applied = [row for row in rows(loop, "processed_events") if row["outcome"] == "ROUTE_APPLIED"]
            assert len(applied) == 3
            replay = {"robot_id": "r1", "distance": 99.0, "timestamp": now[0]}
            assert await loop.submit(Event("ROUTE_RESOLVED", replay, applied[0]["event_id"])) == "DUPLICATE"
            assert await loop.submit(Event("ROUTE_RESOLVED", replay)) == "STALE"
            assert len(rows(loop, "outbox_events")) == 1
    asyncio.run(scenario())


def test_live_routes_deduplicate_shared_legs_and_concurrent_ticks(tmp_path):
    async def scenario():
        now = [10.0]
        started, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def query(robot_id, start, goal):
            calls.append((start.x, goal.x))
            started.set()
            await release.wait()
            return 1.0

        async with live_routing_runtime(tmp_path, query, now) as (loop, _):
            await loop.submit(submit())
            await asyncio.wait_for(started.wait(), timeout=2)
            await loop.submit(submit("second"))
            await asyncio.gather(*(
                loop.submit(Event("TICK", {"current_time": now[0]})) for _ in range(5)
            ))
            assert calls == [(0.0, 1)]
            release.set()
            await wait_for_routes(lambda: bool(rows(loop, "outbox_events")))
            assert calls == [(0.0, 1), (1, 2), (2, 3)]
            assert loop.core.queue.get("second") is not None
    asyncio.run(scenario())


def test_live_route_replans_after_terminal_preemption_at_stopped_pose(tmp_path):
    async def scenario():
        now = [10.0]
        calls = []
        release = asyncio.Event()

        async def query(robot_id, start, goal):
            calls.append((start.x, goal.x))
            if start.x == 0.4:
                await release.wait()
            return 1.0

        async with live_routing_runtime(tmp_path, query, now) as (loop, _):
            await loop.submit(submit())
            await wait_for_routes(lambda: len(rows(loop, "outbox_events")) == 1)
            await loop.submit(status(seq=2, epoch=1, task="t1", state=2, phase=1, session="original"))
            await loop.submit(submit("high", priority=1))
            await wait_for_routes(lambda: len(rows(loop, "outbox_events")) == 2)
            victim = loop.core._active_tasks["t1"]
            assert rows(loop, "outbox_events")[-1]["kind"] == "CANCEL_TASK"
            await loop.submit(status(seq=3, epoch=1, pose=Pose2D(0.4, 0), session="original"))
            assert len(rows(loop, "outbox_events")) == 2

            terminal = action(loop, result_status=TaskResultStatus.STATUS_PREEMPTED)
            assert await loop.submit(terminal) == "APPLIED"
            await wait_for_routes(lambda: (0.4, 1) in calls)
            assert len(rows(loop, "outbox_events")) == 2
            release.set()
            await wait_for_routes(lambda: len(rows(loop, "outbox_events")) == 3)
            high = loop.core._active_tasks["high"]
            assert high.assignment_epoch == victim.assignment_epoch + 1
            assert high.goal_uuid != victim.goal_uuid
            assert loop.core.queue.get("t1").preemption_count == 1
    asyncio.run(scenario())


@pytest.fixture
def energy_policy_yaml(tmp_path):
    import shutil
    import yaml

    path = shutil.copytree("config", tmp_path / "config") / "fleet.yaml"
    data = yaml.safe_load(path.read_text())
    data["policies"].update(emergency_soc_percent=12.5, safety_margin_wh=22.0)
    models = data["fleet"]["battery_models"]
    models["turtlebot3_burger"]["consumption_wh_per_meter"] = 0.25
    models["large"] = dict(models["turtlebot3_burger"], usable_capacity_wh=200.0)
    data["robots"][1]["battery_model"] = "large"
    path.write_text(yaml.safe_dump(data))
    return path


def energy_status(robot="robot_1", soc=100.0, **kwargs):
    event = status(robot=robot, session=f"{robot}-session", **kwargs)
    event.payload["battery_soc_percent"] = soc
    return event


def test_yaml_policy_rechecks_preemption_and_commits_one_assignment(energy_policy_yaml, tmp_path):
    from backend.fleet_manager.builder import build_fleet_manager_from_config

    class Routes:
        def get_path_distance(self, robot_id, start, goal):
            return 4.0

    async def scenario():
        core, _ = build_fleet_manager_from_config(energy_policy_yaml, Routes(), _legacy_test_battery=True)
        with closing(SQLiteStore(tmp_path / "policy.db")) as store:
            loop = FleetEventLoop(store, core)
            await loop.start()
            try:
                def tick():
                    return Event("TICK", {"current_time": 10})

                await loop.submit(energy_status())
                await loop.submit(submit())
                await loop.submit(tick())
                victim = loop.core._active_tasks["t1"]
                await loop.submit(energy_status(soc=37.49, seq=2, epoch=1, task="t1", state=2, phase=1))
                await loop.submit(submit("high", priority=1, created_at=2))
                await loop.submit(submit("younger-high", priority=1, created_at=3))
                await loop.submit(tick())
                assert [r["kind"] for r in rows(loop, "outbox_events")] == ["EXECUTE_TASK"]

                await loop.submit(energy_status(seq=3, epoch=1, task="t1", state=2, phase=1))
                await loop.submit(tick())
                assert [r["kind"] for r in rows(loop, "outbox_events")] == ["EXECUTE_TASK", "CANCEL_TASK"]
                await loop.submit(Event("ACTION_RESULT", dict(
                    robot_id="robot_1", task_id=victim.task_id, assignment_epoch=victim.assignment_epoch,
                    goal_uuid=victim.goal_uuid, result_status=TaskResultStatus.STATUS_PREEMPTED,
                    completed_epoch=victim.assignment_epoch,
                )))
                await loop.submit(energy_status(soc=37.49, seq=4, epoch=1))
                assert await loop.submit(energy_status(seq=4, epoch=1)) == "STALE"
                await loop.submit(tick())
                assert [t.task_id for t in loop.core.queue.iter_assignable_tasks()] == ["high", "younger-high", "t1"]
                assert loop.core.queue.get("high").created_at == 2
                assert not loop.core._failed_tasks
                assert len(rows(loop, "outbox_events")) == 2

                await loop.submit(energy_status(soc=37.5, seq=5, epoch=1))
                tables = ("tasks", "robots", "reservations", "processed_events", "outbox_events")
                before = {table: rows(loop, table) for table in tables}

                def deny_commit(operation, argument, *_):
                    if operation == sqlite3.SQLITE_TRANSACTION and argument == "COMMIT":
                        return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK

                event = tick()
                store.connection.set_authorizer(deny_commit)
                try:
                    with pytest.raises(sqlite3.DatabaseError):
                        await loop.submit(event)
                finally:
                    store.connection.set_authorizer(lambda *_: sqlite3.SQLITE_OK)
                assert {table: rows(loop, table) for table in tables} == before
                assert not loop.core._active_tasks
                assert loop.core.tracker.get_robot("robot_1").current_epoch == 1
                assert loop.core.queue.get("high").created_at == 2

                assert await loop.submit(event) == "APPLIED"
                assert await loop.submit(event) == "DUPLICATE"
                await loop.submit(tick())
                assert list(loop.core._active_tasks) == ["high"]
                commands = [(row["kind"], row["task_id"], row["assignment_epoch"]) for row in rows(loop, "outbox_events")]
                assert commands == [
                    ("EXECUTE_TASK", "t1", 1), ("CANCEL_TASK", "t1", 1), ("EXECUTE_TASK", "high", 2),
                ]
            finally:
                await loop.close()
    asyncio.run(scenario())


def test_yaml_energy_policy_and_robot_models_after_automatic_routes(energy_policy_yaml, tmp_path):
    from backend.fleet_manager.builder import build_fleet_manager_from_config

    async def scenario():
        core, _ = build_fleet_manager_from_config(energy_policy_yaml, _legacy_test_battery=True)
        with closing(SQLiteStore(tmp_path / "policy.db")) as store:
            loop = FleetEventLoop(store, core, clock=lambda: 10.0)

            async def query(robot_id, start, goal):
                return 4.0 if robot_id == "robot_1" else 5.0

            loop.enable_live_routing(query)
            await loop.start()
            try:
                await loop.submit(energy_status(soc=37.49))
                await loop.submit(energy_status(robot="robot_2", soc=37.49, pose=Pose2D(0, 1)))
                await loop.submit(submit())
                await wait_for_routes(lambda: bool(rows(loop, "outbox_events")))
                assert sum(row["outcome"] == "ROUTE_APPLIED" for row in rows(loop, "processed_events")) == 6
                # The closer 100 Wh robot falls just short. The 200 Wh robot
                # has enough energy even though its three paths are longer.
                assert loop.core._active_tasks["t1"].assigned_robot_id == "robot_2"
                assert [row["kind"] for row in rows(loop, "outbox_events")] == ["EXECUTE_TASK"]
            finally:
                await loop.close()
    asyncio.run(scenario())
