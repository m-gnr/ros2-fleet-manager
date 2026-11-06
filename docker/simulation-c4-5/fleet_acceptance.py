"""Two-robot C4 acceptance using only product telemetry and live Nav2 routes."""

import asyncio
from collections import deque
from contextlib import closing
import json
import os
import time

from nav_msgs.msg import Odometry
from rcl_interfaces.msg import Log
from rclpy import create_node
from rclpy.parameter import Parameter

from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain import Pose2D, RobotState, TaskPhase, TaskPriority, TaskResultStatus
from backend.fleet_manager.domain.energy import check_energy_eligibility
from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
from backend.fleet_manager.persistence.store import SQLiteStore
from charging_check import main, validate as validate_charging, verify_navigators
from check import emit
from integration_check import LiveBatteryCheck, pause_battery_processes, wait_for
from preemption_e2e_check import sample

VICTIM = "c45-low"
URGENT = "c45-urgent"
PARALLEL = "c45-parallel"


def outbox(store, task_id, kind):
    return store.connection.execute(
        "SELECT * FROM outbox_events WHERE task_id=? AND kind=? ORDER BY sequence", (task_id, kind),
    ).fetchall()


def submit(task_id, priority, pickup, dropoff):
    return Event("SUBMIT_TASK", dict(
        task_id=task_id, priority=priority, pickup_pose=pickup, dropoff_pose=dropoff, created_at=time.monotonic(),
    ))


def check_database(store):
    assert store.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not store.connection.execute("PRAGMA foreign_key_check").fetchall()
    assert not store.connection.execute(
        "SELECT goal_uuid FROM outbox_events WHERE kind IN ('EXECUTE_TASK','NAVIGATE_TO_STATION') "
        "GROUP BY goal_uuid HAVING count(*) > 1",
    ).fetchall()


async def completed(consumer, *task_ids):
    def terminal():
        core = consumer.core
        assert not core._failed_tasks
        return all(task_id in core._completed_tasks for task_id in task_ids)

    await wait_for(terminal, f"Live tasks did not complete: {task_ids}", timeout=100)


class PreemptionObserver(FleetEventLoop):
    victim_result = None

    def _process(self, event):
        victim_terminal = event.kind == "ACTION_RESULT" and event.payload["task_id"] == VICTIM
        if victim_terminal and self.victim_result is None:
            assert not outbox(self.store, URGENT, "EXECUTE_TASK")
        outcome = super()._process(event)
        if victim_terminal and outcome == "APPLIED":
            self.victim_result = event.payload
        return outcome


async def validate_energy(config_path, fleet, executor):
    probe = LiveBatteryCheck(fleet, executor)
    await verify_navigators(probe)
    core, robot_ids = build_fleet_manager_from_config(config_path)
    node = create_node("c45_energy_fleet", parameter_overrides=[Parameter("use_sim_time", value=True)])
    executor.add_node(node)
    with closing(SQLiteStore("/evidence/c45-energy.sqlite3")) as store:
        consumer = FleetEventLoop(store, core)
        adapter = FleetROS2Adapter(node, consumer, asyncio.get_running_loop(), robot_ids,
                                   robot_namespaces=probe.namespaces, enable_live_routing=False)
        dispatcher = OutboxDispatcher(consumer, adapter.outbox_sender, clock=time.monotonic, retry_delay=1.0)
        await consumer.start()
        try:
            def snapshots():
                result = probe.verify_snapshot(consumer, store, event="C45_ENERGY_BASELINE")
                if result and all(r.last_pose_sample_ns for r in consumer.core.tracker.list_robots()):
                    return result
                return None

            initial = await wait_for(snapshots, "Measured Wh/SoC and physical pose unavailable")
            pickup = Pose2D(1.0, 2.0, -1.57)
            dropoff = Pose2D(1.0, 1.4, -1.57)
            task = submit("c45-energy", TaskPriority.PRIORITY_MEDIUM, pickup, dropoff)
            escape = consumer.core.scheduler.safe_charge_station_pose
            decisions = {}
            for robot in consumer.core.tracker.list_robots():
                distances = [
                    await adapter.route_resolver.compute_route(robot.robot_id, start, end)
                    for start, end in ((robot.pose, pickup), (pickup, dropoff), (dropoff, escape))
                ]
                assert all(distance is not None for distance in distances), (robot.robot_id, distances)
                eligibility = check_energy_eligibility(
                    specs=robot.specs, battery_soc_percent=robot.battery_soc_percent,
                    d_total_m=sum(distances[:2]), d_escape_m=distances[2],
                    emergency_soc_percent=fleet.policies.emergency_soc_percent,
                    safety_margin_wh=fleet.policies.safety_margin_wh, battery_energy_wh=robot.battery_energy_wh,
                )
                assert robot.battery_soc_percent >= fleet.policies.low_soc_percent
                decisions[robot.robot_id] = eligibility.is_eligible
                emit("C45_ROBOT_ENERGY", robot_id=robot.robot_id, distances_m=distances,
                     required_wh=eligibility.required_wh, available_wh=eligibility.available_wh,
                     eligible=eligibility.is_eligible)
            assert decisions == {robot_ids[0]: False, robot_ids[1]: True}

            consumer.enable_live_routing(adapter.route_resolver.compute_route)
            with pause_battery_processes(robot_ids, executable=b"/battery_entry.py"):
                await wait_for(lambda: all(not r.is_stale(time.monotonic()) and
                                           not r.has_fresh_battery(time.monotonic())
                                           for r in consumer.core.tracker.list_robots()),
                               "Real battery outage did not invalidate telemetry", timeout=8)
                assert await consumer.submit(task) == "APPLIED"
                assert store.connection.execute("SELECT count(*) FROM outbox_events").fetchone()[0] == 0
                assert consumer.core.queue.get("c45-energy") is not None
                emit("C45_STALE_BATTERY_BLOCKED", robots=robot_ids)

            records = await wait_for(lambda: outbox(store, "c45-energy", "EXECUTE_TASK"),
                                     "Task not assigned after fresh battery telemetry resumed")
            assert len(records) == 1 and json.loads(records[0]["payload"])["assigned_robot_id"] == robot_ids[1]
            assert await dispatcher.send_one()
            await completed(consumer, "c45-energy")
            final = await wait_for(lambda: probe.verify_snapshot(consumer, store, event="C45_ENERGY_END"),
                                   "Post-delivery Wh/SoC not verified")
            assert final[robot_ids[1]].battery_energy_wh < initial[robot_ids[1]].battery_energy_wh - 0.05
            assert final[robot_ids[0]].battery_energy_wh < initial[robot_ids[0]].battery_energy_wh
            assert outbox(store, "c45-energy", "EXECUTE_TASK")[0]["state"] == "SENT"
            check_database(store)
            emit("ALL_C4_5_ENERGY_TESTS_PASSED", robot_id=robot_ids[1])
        finally:
            await consumer.close()


async def validate_post_charge(fleet, probe, node, consumer, store, dispatcher):
    first, second = [robot.id for robot in fleet.robots]
    dock_id = fleet.stations.charging_stations[0].id
    recent_odom = {rid: deque(maxlen=512) for rid in (first, second)}
    proofs = {}

    def observe_log(msg):
        prefix = "PREEMPTION_STOP_PROOF "
        if msg.msg.startswith(prefix):
            proof = json.loads(msg.msg[len(prefix):])
            proofs[proof["goal_uuid"]] = proof

    node.create_subscription(Log, "/rosout", observe_log, 100)
    for robot_id, namespace in probe.namespaces.items():
        node.create_subscription(
            Odometry, f"{namespace}/odom",
            lambda msg, rid=robot_id: recent_odom[rid].append(sample(msg)), 100,
        )

    initial = await wait_for(lambda: probe.verify_snapshot(consumer, store, event="C45_AFTER_CHARGE"),
                             "Post-charge telemetry not verified")
    assert initial[second].charging_station_id == dock_id

    async def assign(task, expected_robot):
        task_id = task.payload["task_id"]
        assert await consumer.submit(task) == "APPLIED"
        rows = await wait_for(lambda: outbox(store, task_id, "EXECUTE_TASK"), f"No assignment for {task_id}")
        assert len(rows) == 1 and json.loads(rows[0]["payload"])["assigned_robot_id"] == expected_robot
        assert await dispatcher.send_one()
        return rows[0]

    low = await assign(submit(VICTIM, TaskPriority.PRIORITY_LOW,
                              Pose2D(-3.7, 3.2), Pose2D(-3.2, 3.3)), first)
    parallel = await assign(submit(PARALLEL, TaskPriority.PRIORITY_HIGH,
                                   Pose2D(2.3, -2.5), Pose2D(2.5, -1.0)), second)

    def moving_to_pickup(robot_id):
        robot = consumer.core.tracker.get_robot(robot_id)
        return (robot.state == RobotState.STATE_EXECUTING_TASK
                and robot.current_phase == TaskPhase.PHASE_MOVING_TO_PICKUP
                and not robot.is_loaded and recent_odom[robot_id] and recent_odom[robot_id][-1][2] > 0.01)

    await wait_for(lambda: moving_to_pickup(first) and moving_to_pickup(second),
                   "Both charged robots did not enter the transport motion window", timeout=15)
    assert await consumer.submit(submit(URGENT, TaskPriority.PRIORITY_HIGH,
                                        Pose2D(-2.2, 1.8), Pose2D(-1.5, 1.8))) == "APPLIED"
    cancel = await wait_for(lambda: outbox(store, VICTIM, "CANCEL_TASK"), "Live LOW preemption not selected")
    assert len(cancel) == 1 and cancel[0]["goal_uuid"] == low["goal_uuid"]
    assert not outbox(store, URGENT, "EXECUTE_TASK") and not outbox(store, PARALLEL, "CANCEL_TASK")
    assert await dispatcher.send_one()
    terminal = await wait_for(lambda: consumer.victim_result, "LOW terminal not received")
    assert terminal["result_status"] == TaskResultStatus.STATUS_PREEMPTED
    assert terminal["goal_uuid"] == low["goal_uuid"] and terminal["completed_epoch"] == low["assignment_epoch"]
    proof = await wait_for(lambda: proofs.get(low["goal_uuid"]), "Executor stop proof missing")
    final_stamp = proof["odometry_ns"]
    first_stamp = proof["stop_window_start_ns"]
    await wait_for(lambda: recent_odom[first] and recent_odom[first][-1][0] >= proof["decision_ns"] + 200_000_000,
                   "Independent stop telemetry after terminal unavailable", timeout=5)
    observed = [row for row in recent_odom[first]
                if first_stamp <= row[0] <= proof["decision_ns"] + 200_000_000]
    assert proof["nav2_terminal_ns"] < first_stamp <= final_stamp - 200_000_000
    assert (final_stamp, proof["frame_id"], proof["linear_m_s"], abs(proof["angular_rad_s"])) in observed
    assert all(row[2] <= 0.01 and row[3] <= 0.01 for row in observed)
    assert any(row[0] == first_stamp for row in observed)
    assert sum(row[0] >= proof["decision_ns"] for row in observed) >= 2
    emit("C45_CHARGED_PREEMPTION", proof=proof, independent_samples=len(observed))

    high = await wait_for(lambda: outbox(store, URGENT, "EXECUTE_TASK"), "HIGH not assigned after stop")
    assert len(high) == 1 and high[0]["assignment_epoch"] == low["assignment_epoch"] + 1
    assert json.loads(high[0]["payload"])["assigned_robot_id"] == first
    assert await dispatcher.send_one()
    await completed(consumer, URGENT, PARALLEL)
    assert outbox(store, PARALLEL, "EXECUTE_TASK")[0]["goal_uuid"] == parallel["goal_uuid"]
    assert not outbox(store, PARALLEL, "CANCEL_TASK")
    assert consumer.core.reservations.get_station(dock_id).state == "FREE"
    for task_id in (URGENT, PARALLEL):
        rows = outbox(store, task_id, "EXECUTE_TASK")
        assert len(rows) == 1 and rows[0]["state"] == "SENT" and rows[0]["attempts"] == 1
    replay = Event("ACTION_RESULT", terminal)
    assert await consumer.submit(replay) == "STALE"
    assert await consumer.submit(replay) == "DUPLICATE"
    assert store.connection.execute(
        "SELECT count(*) FROM outbox_events WHERE goal_uuid=? AND kind='EXECUTE_TASK'", (low["goal_uuid"],),
    ).fetchone()[0] == 1
    emit("C45_LATE_TERMINAL_BLOCKED", goal_uuid=low["goal_uuid"], epoch=low["assignment_epoch"])

    # The interrupted LOW returns to the normal scheduler. Continue sending
    # committed commands so all robots can report the new epochs in the snapshot.
    async def drain():
        while True:
            await consumer.submit(Event("TICK", {"current_time": time.monotonic()}))
            await dispatcher.send_one()
            core = consumer.core
            assert not core._failed_tasks and not core.station_dispatch.held
            if VICTIM in core._completed_tasks and not core.station_dispatch.active:
                measurements = probe.verify_snapshot(consumer, store, event="C45_AFTER_TRANSPORT")
                if measurements:
                    return core._completed_tasks[VICTIM], measurements
            await asyncio.sleep(0.05)

    resumed, final = await asyncio.wait_for(drain(), timeout=120)
    assert resumed.preemption_count == 1 and resumed.assignment_epoch > low["assignment_epoch"]
    assert resumed.created_at == json.loads(low["payload"])["created_at"]
    victim_commands = outbox(store, VICTIM, "EXECUTE_TASK")
    assert len(victim_commands) == 2 and all(row["state"] == "SENT" and row["attempts"] == 1
                                             for row in victim_commands)
    emit("C45_LOW_RESUMED", epoch=resumed.assignment_epoch, original_epoch=low["assignment_epoch"])
    for robot_id in (first, second):
        assert final[robot_id].battery_energy_wh < initial[robot_id].battery_energy_wh - 0.05
        assert final[robot_id].charging_station_id == ""
    check_database(store)
    emit("ALL_C4_5_CHARGING_TESTS_PASSED", terminal_epoch=terminal["completed_epoch"])


async def validate_charge_and_transport(config_path, fleet, executor):
    await validate_charging(config_path, fleet, executor, consumer_type=PreemptionObserver,
                            after_charging=validate_post_charge, database_path="/evidence/c45-charging.sqlite3")


if __name__ == "__main__":
    profile = os.environ["C45_PROFILE"]
    if profile == "energy":
        raise SystemExit(main(check=validate_energy, initial_soc=(26.0, 100.0),
                              charge_power_w=None, safety_margin_wh=25.0))
    if profile == "charging":
        raise SystemExit(main(check=validate_charge_and_transport))
    raise ValueError(f"Unsupported C4.5 validation profile: {profile!r}")
