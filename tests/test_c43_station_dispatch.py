"""Station movement ownership and transaction regression tests."""

import asyncio
from contextlib import closing
import sqlite3
from uuid import uuid4

import pytest

from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain import Pose2D, RobotState, TaskPhase
from backend.fleet_manager.event_loop import Event, FleetEventLoop
from backend.fleet_manager.persistence.store import SQLiteStore


class Routes:
    def __init__(self, distance=1.0):
        self.distance = distance

    def get_path_distance(self, robot_id, start, goal):
        return self.distance


def status(robot_id, now, *, seq=1, energy=24.0, loaded=False, battery=True,
           epoch=0, task=None, pose=Pose2D(), state=RobotState.STATE_IDLE, session=None):
    sample = seq * 10**8
    return Event("ROBOT_STATUS", {
        "robot_id": robot_id, "state": state, "current_phase": TaskPhase.PHASE_NONE,
        "is_loaded": loaded, "pose": pose, "battery_soc_percent": energy,
        "battery_energy_wh": energy, "current_epoch": epoch, "current_task_id": task,
        "timestamp_sec": now, "status_seq": seq, "publisher_session_id": session or str(uuid4()),
        "source_status_ns": sample, "pose_sample_ns": sample, "pose_valid_until": now + 2,
        "battery_sample_ns": sample if battery else 0,
        "battery_valid_until": now + 2 if battery else 0,
    })


def commands(store):
    return [dict(row) for row in store.connection.execute("SELECT * FROM outbox_events ORDER BY sequence")]


@pytest.mark.parametrize("obstacle", [None, "OCCUPIED", "BLOCKED", "NO_ROUTE", "STALE_BATTERY",
                                      "STALE_STATUS", "LOADED", "ACTIVE_TRANSPORT", "RESERVE_WH"])
def test_low_energy_station_dispatch(obstacle):
    async def scenario():
        now = 10.0
        core, _ = build_fleet_manager_from_config(route_provider=Routes(None if obstacle == "NO_ROUTE" else 1.0))
        if obstacle == "OCCUPIED":
            core.reservations.mark_occupied("dock_1", "robot_2")
        if obstacle == "BLOCKED":
            core.reservations.mark_blocked("dock_1", "robot_2")
        with closing(SQLiteStore(":memory:")) as store:
            consumer = FleetEventLoop(store, core, clock=lambda: now)
            await consumer.start()
            try:
                session = str(uuid4())
                if obstacle == "ACTIVE_TRANSPORT":
                    await consumer.submit(status("robot_1", now, energy=95, session=session))
                    await consumer.submit(Event("SUBMIT_TASK", {
                        "task_id": "transport", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
                    }))
                    await consumer.submit(Event("TICK", {"current_time": now}))
                await consumer.submit(status(
                    "robot_1", now - 3 if obstacle == "STALE_STATUS" else now,
                    loaded=obstacle == "LOADED", battery=obstacle != "STALE_BATTERY",
                    epoch=1 if obstacle == "ACTIVE_TRANSPORT" else 0, seq=2, session=session,
                    energy=8 if obstacle == "RESERVE_WH" else 24,
                ))
                await consumer.submit(Event("TICK", {"current_time": now}))
                await consumer.submit(status(
                    "robot_2", now, pose=Pose2D(0.5, -2.0) if obstacle == "OCCUPIED" else Pose2D(),
                ))
                await consumer.submit(Event("TICK", {"current_time": now}))
                moves = [row for row in commands(store) if row["kind"] == "NAVIGATE_TO_STATION"]
                station = consumer.core.reservations.get_station("dock_1")
                if obstacle is None:
                    assert len(moves) == 1
                    assert station.state == "RESERVED" and station.reserved_by_robot_id == "robot_1"
                elif obstacle in ("OCCUPIED", "BLOCKED"):
                    assert not moves
                    assert station.state == obstacle and station.reserved_by_robot_id == "robot_2"
                elif obstacle == "ACTIVE_TRANSPORT":
                    assert [row["kind"] for row in commands(store)] == ["EXECUTE_TASK", "NAVIGATE_TO_STATION"]
                    assert station.reserved_by_robot_id == "robot_2"
                elif obstacle == "NO_ROUTE":
                    assert not moves and station.state == "FREE"
                else:
                    assert len(moves) == 1 and station.reserved_by_robot_id == "robot_2"
            finally:
                await consumer.close()

    asyncio.run(scenario())


def test_station_reservation_and_outbox_roll_back_together():
    async def scenario():
        core, _ = build_fleet_manager_from_config(route_provider=Routes())
        with closing(SQLiteStore(":memory:")) as store:
            consumer = FleetEventLoop(store, core, clock=lambda: 10.0)
            await consumer.start()
            try:
                await consumer.submit(status("robot_1", 10.0))
                tick = Event("TICK", {"current_time": 10.0})
                before = list(store.connection.iterdump())

                def deny_commit(operation, argument, *_):
                    return (sqlite3.SQLITE_DENY if operation == sqlite3.SQLITE_TRANSACTION and argument == "COMMIT"
                            else sqlite3.SQLITE_OK)

                store.connection.set_authorizer(deny_commit)
                try:
                    with pytest.raises(sqlite3.DatabaseError):
                        await consumer.submit(tick)
                finally:
                    store.connection.set_authorizer(lambda *_: sqlite3.SQLITE_OK)
                assert list(store.connection.iterdump()) == before
                assert consumer.core.reservations.get_station("dock_1").state == "FREE"
                assert await consumer.submit(tick) == "APPLIED"
                assert await consumer.submit(tick) == "DUPLICATE"
                assert len(commands(store)) == 1
                assert consumer.core.reservations.get_station("dock_1").state == "RESERVED"
            finally:
                await consumer.close()

    asyncio.run(scenario())


def terminal(move, *, result_status=1, proof_ns=5 * 10**8, **fields):
    return Event("STATION_RESULT", {
        "robot_id": move.assigned_robot_id, "task_id": move.task_id, "station_id": move.station_id,
        "assignment_epoch": move.assignment_epoch, "goal_uuid": move.goal_uuid,
        "completed_epoch": move.assignment_epoch, "result_status": result_status,
        "proof_ns": proof_ns, **fields,
    })


@pytest.mark.parametrize("park_available", [True, False])
def test_transport_then_park_or_wait_and_ignore_duplicate_terminal(park_available):
    async def scenario():
        from backend.fleet_manager.domain.constants import StationType

        core, _ = build_fleet_manager_from_config(route_provider=Routes())
        if not park_available:
            core.reservations.mark_blocked("park_1", "robot_2")
        core.register_station("wait_1", StationType.SAFE_WAITING, Pose2D(-1.8, -2.0))
        target = "park_1" if park_available else "wait_1"
        with closing(SQLiteStore(":memory:")) as store:
            consumer = FleetEventLoop(store, core, clock=lambda: 10.0)
            await consumer.start()
            try:
                session = str(uuid4())
                await consumer.submit(status("robot_1", 10.0, energy=95, session=session))
                await consumer.submit(Event("SUBMIT_TASK", {
                    "task_id": "transport", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
                }))
                tick = Event("TICK", {"current_time": 10.0})
                await consumer.submit(tick)
                transport = consumer.core._active_tasks["transport"]
                await consumer.submit(status("robot_1", 10.0, seq=2, energy=94, epoch=1, session=session))
                await consumer.submit(Event("ACTION_RESULT", {
                    "robot_id": "robot_1", "task_id": "transport", "assignment_epoch": 1, "completed_epoch": 1,
                    "goal_uuid": transport.goal_uuid, "result_status": 1,
                }))
                await consumer.submit(Event(tick.kind, tick.payload))
                move = consumer.core.station_dispatch.active["robot_1"]
                assert (move.station_id, move.assignment_epoch) == (target, 2)
                assert await consumer.submit(terminal(move, completed_epoch=1)) == "STALE"
                assert await consumer.submit(terminal(move, station_id="dock_1")) == "STALE"
                result = terminal(move)
                assert await consumer.submit(result) == "APPLIED"
                assert await consumer.submit(result) == "DUPLICATE"
                assert await consumer.submit(terminal(move)) == "STALE"
                assert len(commands(store)) == 2
                assert consumer.core.reservations.get_station(target).state == "OCCUPIED"

                # A pose older than terminal stop proof cannot release an occupied resource.
                await consumer.submit(status("robot_1", 10.0, seq=3, energy=93, epoch=2, session=session))
                assert consumer.core.reservations.get_station(target).state == "OCCUPIED"
                await consumer.submit(status("robot_1", 10.0, seq=6, energy=93, epoch=2, session=session))
                assert consumer.core.reservations.get_station(target).state == "FREE"
                assert store.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            finally:
                await consumer.close()

    asyncio.run(scenario())


def test_low_task_cancels_parking_only_after_safe_terminal():
    async def scenario():
        from backend.fleet_manager.domain import TaskPriority

        core, _ = build_fleet_manager_from_config(route_provider=Routes())
        core.station_dispatch.park_due.add("robot_1")
        with closing(SQLiteStore(":memory:")) as store:
            consumer = FleetEventLoop(store, core, clock=lambda: 10.0)
            await consumer.start()
            try:
                session = str(uuid4())
                await consumer.submit(status("robot_1", 10.0, energy=95, session=session))
                await consumer.submit(Event("TICK", {"current_time": 10.0}))
                move = consumer.core.station_dispatch.active["robot_1"]
                await consumer.submit(status("robot_1", 10.0, seq=2, energy=94, epoch=1, session=session,
                                             state=RobotState.STATE_RETURNING_TO_PARK, task=move.task_id))
                await consumer.submit(Event("SUBMIT_TASK", {
                    "task_id": "low", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
                    "priority": TaskPriority.PRIORITY_LOW,
                }))
                await consumer.submit(Event("TICK", {"current_time": 10.0}))
                original, cancel = commands(store)
                assert cancel["kind"] == "CANCEL_STATION_MOVE"
                assert cancel["goal_uuid"] == original["goal_uuid"] == move.goal_uuid
                response = terminal(move).payload
                await consumer.submit(Event("STATION_CANCEL_RESPONSE", {
                    **response, "cancel_command_id": cancel["command_id"], "accepted": True,
                }))
                await consumer.submit(status("robot_1", 10.0, seq=3, energy=94, epoch=1, session=session))
                await consumer.submit(Event("TICK", {"current_time": 10.0}))
                assert len(commands(store)) == 2
                assert await consumer.submit(terminal(move, result_status=3, proof_ns=0)) == "STALE"
                assert await consumer.submit(terminal(move, result_status=3)) == "APPLIED"
                await consumer.submit(Event("TICK", {"current_time": 10.0}))
                task = consumer.core._active_tasks["low"]
                assert task.assignment_epoch == 2 and task.preemption_count == 0
                assert consumer.core.reservations.get_station("park_1").state == "RELEASING"
            finally:
                await consumer.close()

    asyncio.run(scenario())


def test_changed_executor_session_keeps_station_ownership():
    async def scenario():
        core, _ = build_fleet_manager_from_config(route_provider=Routes())
        with closing(SQLiteStore(":memory:")) as store:
            consumer = FleetEventLoop(store, core, clock=lambda: 10.0)
            await consumer.start()
            try:
                await consumer.submit(status("robot_1", 10.0))
                await consumer.submit(Event("TICK", {"current_time": 10.0}))
                move = consumer.core.station_dispatch.active["robot_1"]
                assert await consumer.submit(status("robot_1", 10.0, epoch=1)) == "SESSION_BLOCKED"
                assert await consumer.submit(terminal(move)) == "STALE"
                assert await consumer.submit(Event("OUTBOX_CLAIM", {"now": 10.0})) is None
                assert commands(store)[0]["state"] == "HELD_FOR_REVIEW"
                station = consumer.core.reservations.get_station("dock_1")
                assert station.state == "RESERVED" and station.reserved_by_robot_id == "robot_1"
            finally:
                await consumer.close()

    asyncio.run(scenario())


def test_low_robot_waits_at_its_existing_safe_berth():
    async def scenario():
        from backend.fleet_manager.domain.constants import StationType

        core, _ = build_fleet_manager_from_config(route_provider=Routes())
        current_berth = Pose2D(-2, 1)
        core.register_station("wait_1", StationType.SAFE_WAITING, Pose2D(-1.8, -2.0))
        core.reservations.mark_occupied("park_1", "robot_1")
        core.reservations.mark_occupied("dock_1", "robot_2")
        with closing(SQLiteStore(":memory:")) as store:
            consumer = FleetEventLoop(store, core, clock=lambda: 10.0)
            await consumer.start()
            try:
                await consumer.submit(status("robot_1", 10.0, pose=current_berth))
                await consumer.submit(Event("TICK", {"current_time": 10.0}))
                assert not commands(store)
                assert consumer.core.reservations.get_station("park_1").state == "OCCUPIED"
                assert "robot_1" in consumer.core.station_dispatch.wait_reasons
            finally:
                await consumer.close()

    asyncio.run(scenario())
