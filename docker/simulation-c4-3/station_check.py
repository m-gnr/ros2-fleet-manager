"""Live C4.3 delivery, parking and low-SoC dock approach in Fortress."""

import asyncio
from contextlib import closing
import json
import logging
from math import hypot
import os
import sys
import threading
import time

import rclpy
from lifecycle_msgs.srv import GetState
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from tf2_msgs.msg import TFMessage

from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain import TaskPriority
from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
from backend.fleet_manager.persistence.store import SQLiteStore
from battery_check import battery_commands
from check import emit, load_config as load_test_config, simulation
from fleet_config.loader import load_config
from integration_check import DROPOFF, PICKUP, LiveBatteryCheck, wait_for

INITIAL_LOW_SOC = 24.0


async def validate(config_path, fleet, executor):
    probe = LiveBatteryCheck(fleet, executor)
    gazebo_poses = {}
    amcl_poses = {}

    def observe_gazebo(message):
        for transform in message.transforms:
            gazebo_poses[transform.child_frame_id] = transform.transform.translation

    probe.probe.create_subscription(
        TFMessage, "/world/c3_3_3_validation_world/dynamic_pose/info", observe_gazebo, 10,
    )
    for robot_id, namespace in probe.namespaces.items():
        probe.probe.create_subscription(
            PoseWithCovarianceStamped, f"{namespace}/amcl_pose",
            lambda msg, rid=robot_id: amcl_poses.__setitem__(rid, msg.pose.pose.position), 10,
        )
    await probe.verify_graph()
    for namespace in probe.namespaces.values():
        client = probe.probe.create_client(GetState, f"{namespace}/bt_navigator/get_state")
        await wait_for(client.service_is_ready, f"Navigator service unavailable for {namespace}")
        for _ in range(30):
            result = client.call_async(GetState.Request())
            await wait_for(result.done, f"Navigator state not received for {namespace}")
            if result.result().current_state.label == "active":
                break
            await asyncio.sleep(0.25)
        else:
            raise AssertionError(f"Navigator inactive for {namespace}")
    core, robots = build_fleet_manager_from_config(config_path)
    delivering, low = robots
    charge = fleet.stations.charging_stations[0]
    park = fleet.stations.parking_stations[0]
    node = rclpy.create_node("c43_fleet_manager", parameter_overrides=[Parameter("use_sim_time", value=True)])
    executor.add_node(node)
    with closing(SQLiteStore("/evidence/c43.sqlite3")) as store:
        consumer = FleetEventLoop(store, core)
        adapter = FleetROS2Adapter(
            node, consumer, asyncio.get_running_loop(), robots, robot_namespaces=probe.namespaces,
        )
        dispatcher = OutboxDispatcher(consumer, adapter.outbox_sender, clock=time.monotonic, retry_delay=1.0)
        await consumer.start()

        async def drive():
            while True:
                await consumer.submit(Event("TICK", {"current_time": time.monotonic()}))
                await dispatcher.send_one()
                await asyncio.sleep(0.05)

        worker = None
        try:
            start = await wait_for(
                lambda: probe.verify_snapshot(consumer, store, event="C43_BATTERY_VERIFIED"),
                "Missing measurement agreement",
            )
            assert start[low].battery_soc_percent <= INITIAL_LOW_SOC
            assert start[delivering].battery_soc_percent > fleet.policies.low_soc_percent
            await consumer.submit(Event("SUBMIT_TASK", {
                "task_id": "delivery", "pickup_pose": PICKUP, "dropoff_pose": DROPOFF,
                "priority": TaskPriority.PRIORITY_LOW, "created_at": time.monotonic(),
            }))
            worker = asyncio.create_task(drive())

            def completed():
                moves = list(store.connection.execute("SELECT * FROM station_moves"))
                assert all(move["status"] not in ("FAILED", "HELD_FOR_REVIEW") for move in moves), [
                    dict(move) for move in moves
                ]
                assert "delivery" not in consumer.core._failed_tasks
                if worker.done():
                    worker.result()
                snapshot = consumer.core
                return (len(moves) == 2 and all(move["status"] == "ARRIVED" for move in moves)
                        and "delivery" in snapshot._completed_tasks
                        and all(snapshot.tracker.get_robot(move["robot_id"]).last_pose_sample_ns
                                >= snapshot.reservations.get_station(move["station_id"]).departure_after_ns
                                for move in moves))

            await wait_for(completed, "Live transport, parking or charge approach did not finish", timeout=120)
            snapshot = consumer.core
            expected = ((delivering, park.id, 2), (low, charge.id, 1))
            for robot_id, station_id, epoch in expected:
                station = snapshot.reservations.get_station(station_id)
                robot = snapshot.tracker.get_robot(robot_id)
                assert station.state == "OCCUPIED" and station.has_owner(robot_id)
                assert station.departure_after_ns > 0
                assert robot.current_epoch == epoch and not robot.is_loaded
                assert robot.pose.frame_id == station.pose.frame_id
                error = hypot(robot.pose.x - station.pose.x, robot.pose.y - station.pose.y)
                assert error <= station.tolerance_radius
                actual = gazebo_poses[robot_id]
                actual_error = hypot(actual.x - station.pose.x, actual.y - station.pose.y)
                assert actual_error <= station.tolerance_radius
                assert robot.battery_energy_wh < start[robot_id].battery_energy_wh
                emit("C43_STATION_ARRIVED", robot_id=robot_id, station_id=station_id, epoch=epoch,
                     stop_stamp_ns=station.departure_after_ns, position_error_m=error,
                     gazebo_position_error_m=actual_error, energy_wh=robot.battery_energy_wh)
            assert snapshot._completed_tasks["delivery"].assigned_robot_id == delivering
            commands = list(store.connection.execute("SELECT * FROM outbox_events"))
            assert len(commands) == 3 and len({row["goal_uuid"] for row in commands}) == 3
            assert all(row["state"] == "SENT" and row["attempts"] == 1 for row in commands)
            assert {(json.loads(row["payload"])["assigned_robot_id"], row["kind"]) for row in commands} == {
                (delivering, "EXECUTE_TASK"), (delivering, "NAVIGATE_TO_STATION"), (low, "NAVIGATE_TO_STATION"),
            }
            assert store.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert not store.connection.execute("PRAGMA foreign_key_check").fetchall()
            emit("ALL_C4_3_TESTS_PASSED", token=os.environ["DDS_TEST_PAYLOAD"], outbox_commands=len(commands))
        finally:
            if not worker or not completed_without_failure(store):
                emit("C43_TERMINAL_DIAGNOSTICS",
                     amcl={rid: (p.x, p.y) for rid, p in amcl_poses.copy().items()},
                     gazebo={key: (p.x, p.y) for key, p in gazebo_poses.copy().items()},
                     robot_status={r.robot_id: (r.pose.x, r.pose.y)
                                   for r in consumer.core.tracker.list_robots()})
            if worker is not None:
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)
            await consumer.close()


def completed_without_failure(store):
    return store.connection.execute("SELECT count(*) FROM station_moves WHERE status='ARRIVED'").fetchone()[0] == 2


def main():
    config, fleet_data, _ = load_test_config()
    fleet = load_config(config["fleet_config_path"])
    if os.environ["SIM_CHECK_ROLE"] == "simulation":
        commands = battery_commands(config, fleet)
        label, low_command = commands[1]
        commands[1] = (label, ["python3", "/opt/simulation-c4-3/battery_entry.py",
                               *low_command[1:], "--initial-soc", str(INITIAL_LOW_SOC)])
        return simulation(config, fleet_data, executor_entry="/opt/simulation-c4-2/executor_test_entry.py",
                          battery_commands=commands)
    logging.basicConfig(level=logging.INFO)
    rclpy.init()
    executor = MultiThreadedExecutor(num_threads=4)
    worker = threading.Thread(target=executor.spin)
    worker.start()
    try:
        asyncio.run(validate(config["fleet_config_path"], fleet, executor))
    finally:
        executor.shutdown()
        worker.join()
        for node in executor.get_nodes():
            node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
