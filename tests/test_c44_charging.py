"""Dock evidence, Wh accounting and Fleet Manager charging policy."""

from dataclasses import replace

import pytest

from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain import Pose2D, RobotState
from fleet_battery_simulator.consumption import BatteryConsumption
from fleet_battery_simulator.docking import DockGate, Ownership
from fleet_config.loader import load_config

SECOND = 10**9
PAIR = ("dock_1::pad::surface", "robot_1::left_wheel::wheel")


def dock_gate():
    gate = DockGate("robot_1", {"dock_1": (0.0, 0.0, 0.3), "dock_2": (1.0, 0.0, 0.3)})
    owner = Ownership(SECOND, "robot_1", "dock_1", b"session", 2)
    gate.observe_lease(owner)
    gate.observe_status(owner, 1)
    gate.observe_pose(SECOND, 0, 0)
    gate.observe_velocity(SECOND, 0, 0)
    return gate, owner


@pytest.mark.parametrize("fault", [
    "no_contact", "motion", "rotation", "out_of_radius", "other_robot", "other_station", "wrong_owner",
    "epoch", "session", "stale", "expired_lease", "revoked",
])
def test_dock_requires_independent_current_evidence(fault):
    gate, owner = dock_gate()
    stamp = SECOND + 50_000_000
    if fault != "no_contact":
        pair = PAIR
        if fault == "other_robot":
            pair = (PAIR[0], "robot_2::left_wheel::wheel")
        gate.observe_contact("dock_2" if fault == "other_station" else "dock_1", stamp, [pair])
    if fault == "motion":
        gate.observe_velocity(stamp, 0.012, 0)
    if fault == "rotation":
        gate.observe_velocity(stamp, 0, 0.012)
    if fault == "out_of_radius":
        gate.observe_pose(stamp, 0.3001, 0)
    if fault == "wrong_owner":
        gate.lease = None
        gate.observe_lease(replace(owner, robot_id="robot_2"))
    if fault == "epoch":
        gate.observe_lease(replace(owner, stamp_ns=stamp, epoch=3))
    if fault == "session":
        gate.observe_status(replace(owner, stamp_ns=stamp, session_id=b"new-session"), 2)
        gate.observe_status(replace(owner, stamp_ns=stamp, session_id=b"session"), 3)
    if fault == "revoked":
        gate.observe_lease(replace(owner, stamp_ns=stamp, station_id=""))
    if fault == "stale":
        stamp += 400_000_000
    if fault == "expired_lease":
        stamp = SECOND + 510_000_000
        gate.observe_pose(stamp, 0, 0)
        gate.observe_velocity(stamp, 0, 0)
        gate.observe_status(replace(owner, stamp_ns=stamp), 2)
        gate.observe_contact("dock_1", stamp, [PAIR])
    assert gate.station(stamp) == ""


def test_valid_contact_duplicate_loss_and_charge_math():
    gate, _ = dock_gate()
    stamp = SECOND + 10_000_000
    gate.observe_contact("dock_1", stamp, [PAIR[::-1]])
    assert gate.station(stamp) == "dock_1"
    gate.observe_contact("dock_1", stamp + 1, [])
    gate.observe_contact("dock_1", stamp, [PAIR])
    assert gate.station(stamp + 1) == ""
    gate.observe_contact("dock_1", stamp + 2, [PAIR])
    assert gate.station(stamp + 2) == "dock_1"

    fleet = load_config("config/fleet.yaml")
    model = next(iter(fleet.fleet.battery_models.values()))
    battery = BatteryConsumption(model)
    battery.remaining_wh = 80.0
    battery.update_clock(SECOND)
    battery.update_clock(3601 * SECOND, charging=True)
    assert battery.remaining_wh == 98.0  # 20 W input and 2 W base draw for an hour.
    assert not battery.update_clock(3601 * SECOND, charging=True)
    battery.update_clock(2 * SECOND, charging=True)
    assert battery.remaining_wh == 98.0
    battery.update_clock(3602 * SECOND, charging=True)
    assert battery.remaining_wh == 100.0


def test_old_status_and_lease_cannot_restore_dock_after_departure():
    gate, owner = dock_gate()
    stamp = SECOND + 100_000_000
    gate.observe_contact("dock_1", stamp, [PAIR])
    assert gate.station(stamp) == "dock_1"
    gate.observe_status(replace(owner, stamp_ns=stamp, station_id="", epoch=3), 2)
    gate.observe_status(replace(owner, stamp_ns=stamp - 1), 3)
    gate.observe_status(replace(owner, stamp_ns=stamp + 1), 4)
    gate.observe_lease(replace(owner, stamp_ns=stamp + 2))
    assert gate.station(stamp + 2) == ""


class Routes:
    def get_path_distance(self, robot_id, start, goal):
        return 1.0


def ready(core, robot_id, soc, *, dock="", state=RobotState.STATE_IDLE):
    robot = core.tracker.get_robot(robot_id)
    robot.initial_status_verified = True
    robot.session_id = robot_id
    robot.last_status_received_at = 10.0
    robot.route_pose_valid_until = 12.0
    robot.last_pose_sample_ns = 1
    robot.battery_valid_until = 12.0
    robot.battery_sample_ns = 1
    robot.battery_energy_wh = robot.battery_soc_percent = soc
    robot.state = state
    robot.dock_station_id = dock
    return robot


@pytest.mark.parametrize("soc1,soc2,expected", [(24.0, 22.0, "robot_2"), (24.0, 24.0, "robot_1")])
def test_charge_queue_prioritizes_lowest_soc_then_fifo(soc1, soc2, expected):
    core, _ = build_fleet_manager_from_config(route_provider=Routes())
    assert core.reservations.mark_blocked("dock_1", "robot_2")
    first = ready(core, "robot_1", soc1)
    core.schedule_tick(10.0)
    assert first.charge_request_order == 1
    # Release the fixture block before it can affect the second robot's eligibility.
    core.reservations._free(core.reservations.get_station("dock_1"))
    ready(core, "robot_2", soc2)
    core.schedule_tick(10.0)
    assert core.reservations.get_station("dock_1").reserved_by_robot_id == expected


@pytest.mark.parametrize("soc,waiter,task,expected", [
    (79.0, True, False, None),
    (80.0, True, False, "park_1"),
    (100.0, False, False, None),
    (60.0, False, True, "transport"),
])
def test_charge_exit_policy_keeps_ownership_until_departure(soc, waiter, task, expected):
    core, _ = build_fleet_manager_from_config(route_provider=Routes())
    assert core.reservations.mark_occupied("dock_1", "robot_1")
    ready(core, "robot_1", soc, dock="dock_1", state=RobotState.STATE_CHARGING)
    if waiter:
        ready(core, "robot_2", 22.0)
    if task:
        core.submit_task("delivery", Pose2D(1, 0), Pose2D(2, 0))
    core.schedule_tick(10.0)
    dock = core.reservations.get_station("dock_1")
    assert dock.has_owner("robot_1")
    if expected is None:
        assert dock.state == "OCCUPIED"
    elif expected == "transport":
        assert core._active_tasks_by_robot["robot_1"].task_id == "delivery"
        assert dock.state == "RELEASING"
    else:
        assert core.station_dispatch.active["robot_1"].station_id == expected
        assert dock.state == "RELEASING"


def test_blocked_session_cannot_release_occupied_dock():
    core, _ = build_fleet_manager_from_config(route_provider=Routes())
    assert core.reservations.mark_occupied("dock_1", "robot_1")
    owner = ready(core, "robot_1", 80.0, dock="dock_1", state=RobotState.STATE_CHARGING)
    owner.session_blocked = True
    ready(core, "robot_2", 22.0)
    core.schedule_tick(10.0)
    assert not core.station_dispatch.active
    dock = core.reservations.get_station("dock_1")
    assert dock.state == "OCCUPIED" and dock.has_owner("robot_1")


def test_charge_exit_and_park_outbox_roll_back_together():
    import asyncio
    from contextlib import closing
    import sqlite3

    from backend.fleet_manager.event_loop import Event, FleetEventLoop
    from backend.fleet_manager.persistence.store import SQLiteStore

    async def scenario():
        core, _ = build_fleet_manager_from_config(route_provider=Routes())
        assert core.reservations.mark_occupied("dock_1", "robot_1")
        ready(core, "robot_1", 80.0, dock="dock_1", state=RobotState.STATE_CHARGING)
        ready(core, "robot_2", 22.0)
        with closing(SQLiteStore(":memory:")) as store:
            consumer = FleetEventLoop(store, core, clock=lambda: 10.0)
            await consumer.start()
            try:
                before = list(store.connection.iterdump())
                tick = Event("TICK", {"current_time": 10.0})
                store.connection.set_authorizer(
                    lambda op, name, *_: sqlite3.SQLITE_DENY if
                    (op, name) == (sqlite3.SQLITE_TRANSACTION, "COMMIT") else sqlite3.SQLITE_OK,
                )
                try:
                    with pytest.raises(sqlite3.DatabaseError):
                        await consumer.submit(tick)
                finally:
                    store.connection.set_authorizer(lambda *_: sqlite3.SQLITE_OK)
                assert list(store.connection.iterdump()) == before
                assert consumer.core.reservations.get_station("dock_1").state == "OCCUPIED"
                assert await consumer.submit(tick) == "APPLIED"
                assert consumer.core.reservations.get_station("dock_1").state == "RELEASING"
                assert store.connection.execute("SELECT count(*) FROM outbox_events").fetchone()[0] == 1
            finally:
                await consumer.close()

    asyncio.run(scenario())


def test_dock_handoff_needs_independent_physical_departure():
    core, _ = build_fleet_manager_from_config(route_provider=Routes())
    assert core.reservations.mark_occupied("dock_1", "robot_1")
    dock = core.reservations.get_station("dock_1")
    dock.departure_after_ns = 100
    assert core.reservations.initiate_release("dock_1", "robot_1")

    def report(stamp, physical, physical_stamp, valid_until=10.3):
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=0, is_loaded=False,
            pose=Pose2D(0.9, -2.0), battery_soc_percent=80.0, battery_energy_wh=80.0,
            current_epoch=2, current_task_id=None, timestamp_sec=10.0,
            publisher_session_id="robot-1-session", pose_sample_ns=stamp, pose_valid_until=12.0,
            physical_pose=physical, physical_sample_ns=physical_stamp, physical_valid_until=valid_until,
        )

    report(110, None, 0)
    report(120, Pose2D(0.8, -2.0), 120)
    report(130, Pose2D(0.9, -2.0), 95)
    report(140, Pose2D(0.9, -2.0), 140, valid_until=9.9)
    assert dock.state == "RELEASING" and dock.has_owner("robot_1")
    report(150, Pose2D(0.9, -2.0), 150)
    assert dock.state == "FREE"
