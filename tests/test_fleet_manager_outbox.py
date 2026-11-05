"""SQLite failure boundaries and real asyncio producer interleavings."""
import asyncio
import json
import sqlite3

import pytest

from backend.fleet_manager.domain import FleetManagerCore, Pose2D, ReservationState, StationType
from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
from backend.fleet_manager.persistence import SQLiteStore, ScenarioResetRequired


class Routes:
    def get_path_distance(self, start, goal):
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


def status(robot="r1", seq=1, epoch=0, task=None, state=1, phase=0, pose=None, timestamp=10, session=None):
    return Event("ROBOT_STATUS", dict(robot_id=robot, status_seq=seq, current_epoch=epoch,
        current_task_id=task, state=state, current_phase=phase, is_loaded=False,
        pose=pose or Pose2D(), battery_soc_percent=100, battery_energy_wh=100,
        timestamp_sec=timestamp, publisher_session_id=session))


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


def test_preemption_waits_for_terminal_and_records_new_assignment(runtime):
    async def scenario():
        await runtime.start()
        await preempt(runtime)
        assert [r["kind"] for r in rows(runtime, "outbox_events")] == ["EXECUTE_TASK", "CANCEL_TASK"]
        await runtime.submit(action(runtime, "CANCEL_RESPONSE"))
        assert list(runtime.core._active_tasks) == ["t1"]
        await runtime.submit(action(runtime, result_status=3))
        assert list(runtime.core._active_tasks) == ["high"]
        assert runtime.core.queue.get("t1").preemption_count == 1
        assert runtime.core.queue.get("t1").created_at == 1
        assert len(rows(runtime, "outbox_events")) == 3
        assert rows(runtime, "outbox_events")[-1]["task_id"] == "high"
        await runtime.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("result", [1, 2])
def test_terminal_during_cancel_does_not_strand_high(runtime, result):
    async def scenario():
        await runtime.start()
        await preempt(runtime)
        await runtime.submit(action(runtime, result_status=result))
        assert runtime.core.queue.get("high") is not None
        assert not runtime.core._pending_preemption_assignments
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
