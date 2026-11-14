"""C4.2 assignment and transaction boundaries for battery measurements."""

import asyncio
import time
from contextlib import closing
from uuid import uuid4

from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain import Pose2D, RobotState, TaskPhase, TaskPriority
from backend.fleet_manager.event_loop import Event, FleetEventLoop
from backend.fleet_manager.persistence.store import SQLiteStore


class Routes:
    def get_path_distance(self, robot_id, start, goal):
        return 1.0


def test_configured_manager_does_not_assign_without_battery():
    async def scenario():
        core, _ = build_fleet_manager_from_config(route_provider=Routes())
        with closing(SQLiteStore(":memory:")) as store:
            consumer = FleetEventLoop(store, core)
            await consumer.start()
            try:
                await consumer.submit(Event("ROBOT_STATUS", {
                    "robot_id": "robot_1", "state": RobotState.STATE_IDLE,
                    "current_phase": TaskPhase.PHASE_NONE, "is_loaded": False,
                    "pose": Pose2D(), "battery_soc_percent": 100.0, "battery_energy_wh": 100.0,
                    "current_epoch": 0, "current_task_id": None, "timestamp_sec": time.monotonic(),
                    "status_seq": 1, "publisher_session_id": str(uuid4()),
                }))
                await consumer.submit(Event("SUBMIT_TASK", {
                    "task_id": "waiting", "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
                    "priority": TaskPriority.PRIORITY_LOW, "created_at": 1.0,
                }))
                await consumer.submit(Event("TICK", {"current_time": time.monotonic()}))
                assert store.connection.execute("SELECT status FROM tasks").fetchone()[0] == "QUEUED"
                assert store.connection.execute("SELECT count(*) FROM outbox_events").fetchone()[0] == 0
            finally:
                await consumer.close()

    asyncio.run(scenario())


def status(seq, now, session, *, battery_ns=0, energy=95.0, soc=None, epoch=0,
           task_id=None, state=RobotState.STATE_IDLE, phase=TaskPhase.PHASE_NONE):
    return Event("ROBOT_STATUS", {
        "robot_id": "robot_1", "state": state, "current_phase": phase, "is_loaded": False,
        "pose": Pose2D(), "battery_soc_percent": energy if soc is None else soc, "battery_energy_wh": energy,
        "current_epoch": epoch, "current_task_id": task_id, "timestamp_sec": now,
        "status_seq": seq, "publisher_session_id": session,
        "battery_sample_ns": battery_ns, "battery_valid_until": now + 2.0 if battery_ns else 0.0,
    })


def submit(task_id, priority=TaskPriority.PRIORITY_LOW, created_at=1.0):
    return Event("SUBMIT_TASK", {
        "task_id": task_id, "pickup_pose": Pose2D(1, 0), "dropoff_pose": Pose2D(2, 0),
        "priority": priority, "created_at": created_at,
    })


def tick(now):
    return Event("TICK", {"current_time": now})


def commands(store):
    return [tuple(row) for row in store.connection.execute(
        "SELECT kind, task_id, assignment_epoch FROM outbox_events ORDER BY sequence"
    )]


def test_remaining_wh_controls_threshold_and_session_change_blocks():
    async def scenario():
        core, _ = build_fleet_manager_from_config(route_provider=Routes())
        # Keep this precision check above the C4.3 low-SoC routing threshold.
        core.scheduler.safety_margin_wh = 50.0
        with closing(SQLiteStore(":memory:")) as store:
            consumer = FleetEventLoop(store, core, clock=lambda: 10.0)
            await consumer.start()
            try:
                session = str(uuid4())
                # The three metre legs plus the test margin cost 50.6 Wh.
                # float32 SoC can round this sample to the threshold.
                await consumer.submit(status(1, 10.0, session, battery_ns=10**9, energy=58.599999, soc=58.6))
                await consumer.submit(submit("waiting"))
                await consumer.submit(tick(10.0))
                assert consumer.core.queue.get("waiting").created_at == 1.0
                assert not commands(store)
                assert await consumer.submit(status(2, 10.0, str(uuid4()), battery_ns=2 * 10**9)) == "SESSION_BLOCKED"
                robot = consumer.core.tracker.get_robot("robot_1")
                assert robot.session_blocked
                assert robot.battery_energy_wh == 58.599999
                await consumer.submit(tick(10.0))
                assert not commands(store)
            finally:
                await consumer.close()

    asyncio.run(scenario())


def test_fleet_tracker_accepts_only_matching_one_shot_control_proof():
    from backend.fleet_manager.domain.fleet_tracker import FleetTracker

    core, _ = build_fleet_manager_from_config(route_provider=Routes())
    robot = core.tracker.get_robot("robot_1")
    assert robot.requires_battery_telemetry
    capacity = robot.specs.usable_capacity_wh
    FleetTracker._update_battery(robot, 20.0, capacity * .2, 10**9, 3.0, 1.0, "")
    assert robot.battery_valid_until == 3.0
    # Plain RobotStatus battery rise remains fenced.
    FleetTracker._update_battery(robot, 100.0, capacity, 2 * 10**9, 4.0, 2.0, "")
    assert robot.battery_valid_until == 0.0

    # A fresh controlled scenario baseline accepts its exact one-shot proof.
    FleetTracker._update_battery(robot, 20.0, capacity * .2, 3 * 10**9, 5.0, 3.0, "")
    request_id = str(uuid4())
    FleetTracker._update_battery(
        robot, 100.0, capacity, 4 * 10**9, 6.0, 4.0, "",
        "battery-session", request_id, 100.0, capacity, 4 * 10**9,
    )
    assert robot.battery_energy_wh == capacity
    assert robot.battery_valid_until == 6.0
    # After a normal decrease, replay cannot authorize another upward jump.
    FleetTracker._update_battery(robot, 20.0, capacity * .2, 5 * 10**9, 7.0, 5.0, "")
    FleetTracker._update_battery(
        robot, 100.0, capacity, 6 * 10**9, 8.0, 6.0, "",
        "battery-session", request_id, 100.0, capacity, 4 * 10**9,
    )
    assert robot.battery_valid_until == 0.0
    FleetTracker._update_battery(robot, 20.0, capacity * .2, 7 * 10**9, 9.0, 7.0, "")
    assert robot.battery_energy_wh == capacity * .2


def test_active_transport_and_post_preemption_require_fresh_battery():
    from backend.fleet_manager.domain import TaskResultStatus

    async def scenario():
        core, _ = build_fleet_manager_from_config(route_provider=Routes())
        with closing(SQLiteStore(":memory:")) as store:
            consumer = FleetEventLoop(store, core, clock=lambda: 10.0)
            await consumer.start()
            try:
                session = str(uuid4())
                await consumer.submit(status(1, 10.0, session, battery_ns=10**9))
                await consumer.submit(submit("low"))
                await consumer.submit(tick(10.0))
                victim = consumer.core._active_tasks["low"]
                running = dict(epoch=1, task_id="low", state=RobotState.STATE_EXECUTING_TASK,
                               phase=TaskPhase.PHASE_MOVING_TO_PICKUP)
                await consumer.submit(status(2, 10.0, session, **running))
                await consumer.submit(submit("high", priority=TaskPriority.PRIORITY_HIGH, created_at=2.0))
                await consumer.submit(tick(10.0))
                assert not consumer.core._failed_tasks
                assert consumer.core._active_tasks["low"].goal_uuid == victim.goal_uuid
                assert commands(store) == [("EXECUTE_TASK", "low", 1)]
                await consumer.submit(status(3, 10.0, session, battery_ns=2 * 10**9, energy=94.0, **running))
                await consumer.submit(tick(10.0))
                assert commands(store)[-1] == ("CANCEL_TASK", "low", 1)

                await consumer.submit(status(4, 10.0, session, epoch=1))
                await consumer.submit(Event("ACTION_RESULT", dict(
                    robot_id="robot_1", task_id="low", assignment_epoch=1, completed_epoch=1,
                    goal_uuid=victim.goal_uuid, result_status=TaskResultStatus.STATUS_PREEMPTED,
                )))
                await consumer.submit(tick(10.0))
                assert len(commands(store)) == 2
                assert [t.task_id for t in consumer.core.queue.iter_assignable_tasks()] == ["high", "low"]
                assert consumer.core.queue.get("low").created_at == 1.0
                await consumer.submit(status(5, 10.0, session, battery_ns=3 * 10**9, energy=93.0, epoch=1))
                await consumer.submit(tick(10.0))
                assert commands(store)[-1] == ("EXECUTE_TASK", "high", 2)
            finally:
                await consumer.close()

    asyncio.run(scenario())


def test_late_route_rechecks_battery_and_fresh_status_commits_atomically():
    import sqlite3
    import pytest

    async def scenario():
        core, _ = build_fleet_manager_from_config()
        with closing(SQLiteStore(":memory:")) as store:
            now = 10.0
            session = str(uuid4())
            third_route = asyncio.Event()
            release = asyncio.Event()
            calls = 0

            async def query(robot_id, start, goal):
                nonlocal calls
                calls += 1
                if calls == 3:
                    third_route.set()
                    await release.wait()
                return 1.0

            consumer = FleetEventLoop(store, core, clock=lambda: now)
            consumer.enable_live_routing(query)
            await consumer.start()
            try:
                await consumer.submit(status(1, now, session, battery_ns=10**9))
                await consumer.submit(submit("waiting"))
                await asyncio.wait_for(third_route.wait(), 2.0)
                now = 11.5
                await consumer.submit(status(2, now, session, battery_ns=10**9))
                assert consumer.core.tracker.get_robot("robot_1").battery_valid_until == 12.0
                now = 12.1
                release.set()
                async def wait_for_result():
                    while store.connection.execute(
                        "SELECT count(*) FROM processed_events WHERE outcome='ROUTE_APPLIED'"
                    ).fetchone()[0] < 3:
                        await asyncio.sleep(0.01)
                await asyncio.wait_for(wait_for_result(), 2.0)
                await consumer.submit(tick(now))
                assert not commands(store)

                fresh = status(3, now, session, battery_ns=2 * 10**9, energy=94.0)
                before = list(store.connection.iterdump())

                def deny_commit(operation, argument, *_):
                    if operation == sqlite3.SQLITE_TRANSACTION and argument == "COMMIT":
                        return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK

                store.connection.set_authorizer(deny_commit)
                try:
                    with pytest.raises(sqlite3.DatabaseError):
                        await consumer.submit(fresh)
                finally:
                    store.connection.set_authorizer(lambda *_: sqlite3.SQLITE_OK)
                assert list(store.connection.iterdump()) == before
                assert consumer.core.tracker.get_robot("robot_1").battery_sample_ns == 10**9
                assert await consumer.submit(fresh) == "APPLIED"
                assert await consumer.submit(fresh) == "DUPLICATE"
                assert commands(store) == [("EXECUTE_TASK", "waiting", 1)]
            finally:
                await consumer.close()

    asyncio.run(scenario())
