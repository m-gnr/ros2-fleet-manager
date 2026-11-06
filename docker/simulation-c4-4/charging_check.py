"""Verify two real robots use the same physical dock in queue order."""

import asyncio
from contextlib import closing
import json
import logging
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import threading
import time

from dock_world import dock_bridge_arguments, install_docks
from geometry_msgs.msg import PoseStamped
import rclpy
from lifecycle_msgs.srv import GetState
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from ros_gz_interfaces.msg import Contacts
import yaml

from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
from backend.fleet_manager.persistence.store import SQLiteStore
from battery_check import battery_commands
from check import emit, load_config as load_test_config, simulation
from fleet_config.loader import load_config
from integration_check import LiveBatteryCheck, wait_for

INITIAL_SOC = (22.0, 24.0)
TEST_CHARGE_POWER_W = 21600.0


async def validate(config_path, fleet, executor):
    probe = LiveBatteryCheck(fleet, executor)
    await probe.verify_graph()
    for namespace in probe.namespaces.values():
        client = probe.probe.create_client(GetState, f"{namespace}/bt_navigator/get_state")
        await wait_for(client.service_is_ready, f"Navigator service unavailable for {namespace}")

        for _ in range(30):
            result = client.call_async(GetState.Request())
            await wait_for(result.done, f"Navigator state missing for {namespace}")
            if result.result().current_state.label == "active":
                break
            await asyncio.sleep(0.25)
        else:
            raise AssertionError(f"Navigator inactive for {namespace}")
    core, robots = build_fleet_manager_from_config(config_path)
    first, second = robots
    dock = fleet.stations.charging_stations[0]
    park = fleet.stations.parking_stations[0]
    contacts = {}
    poses = {}

    def observe_contacts(msg):
        for contact in msg.contacts:
            for collision in (contact.collision1, contact.collision2):
                robot = collision.name.split("::", 1)[0]
                if robot in robots:
                    contacts[robot] = (collision.name, msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec)

    probe.probe.create_subscription(Contacts, f"/dock/{dock.id}/contacts", observe_contacts, 10)
    for robot_id, namespace in probe.namespaces.items():
        probe.probe.create_subscription(PoseStamped, f"{namespace}/physical_pose",
                                       lambda msg, rid=robot_id: poses.__setitem__(rid, msg.pose.position), 10)
    node = rclpy.create_node("c44_fleet_manager", parameter_overrides=[Parameter("use_sim_time", value=True)])
    executor.add_node(node)
    with closing(SQLiteStore("/evidence/c44.sqlite3")) as store:
        consumer = FleetEventLoop(store, core)
        adapter = FleetROS2Adapter(node, consumer, asyncio.get_running_loop(), robots,
                                   robot_namespaces=probe.namespaces, enable_live_routing=False)
        dispatcher = OutboxDispatcher(consumer, adapter.outbox_sender, clock=time.monotonic, retry_delay=1.0)
        await consumer.start()
        worker = None
        record = {"charging": set(), "first_below_target": False, "departure": False}
        try:
            initial = await wait_for(
                lambda: probe.verify_snapshot(consumer, store, event="C44_INITIAL_BATTERY"),
                "Initial battery telemetry mismatch",
            )
            assert initial[first].battery_soc_percent < initial[second].battery_soc_percent
            consumer.enable_live_routing(adapter.route_resolver.compute_route)

            async def drive():
                while True:
                    await consumer.submit(Event("TICK", {"current_time": time.monotonic()}))
                    await dispatcher.send_one()
                    await asyncio.sleep(0.05)

            worker = asyncio.create_task(drive())

            def accepted():
                if worker.done():
                    worker.result()
                snapshot = consumer.core
                station = snapshot.reservations.get_station(dock.id)
                robots_by_id = {r.robot_id: r for r in snapshot.tracker.list_robots()}
                for robot_id, robot in robots_by_id.items():
                    if robot.charging_station_id == dock.id and robot_id not in record["charging"]:
                        assert station.has_owner(robot_id) and robot_id in contacts
                        record["charging"].add(robot_id)
                        emit("C44_PHYSICAL_CHARGE", robot_id=robot_id, station_id=dock.id,
                             collision=contacts[robot_id], wh=robot.battery_energy_wh)
                moves = list(store.connection.execute("SELECT * FROM station_moves ORDER BY rowid"))
                assert all(m["status"] not in ("FAILED", "HELD_FOR_REVIEW") for m in moves), [
                    dict(m) for m in moves
                ]
                if moves:
                    assert moves[0]["robot_id"] == first and moves[0]["station_id"] == dock.id
                if station.has_owner(first) and robots_by_id[first].charging_station_id:
                    if robots_by_id[first].battery_soc_percent < fleet.policies.charge_target_soc_percent:
                        assert not any(m["station_id"] == park.id for m in moves)
                        record["first_below_target"] = True
                if not record["departure"] and (station.state == "FREE" or station.has_owner(second)) and len(moves) >= 2:
                    from math import hypot
                    position = poses[first]
                    distance = hypot(position.x - dock.pose.x, position.y - dock.pose.y)
                    assert distance > dock.tolerance_radius + station.departure_margin
                    assert robots_by_id[first].charging_station_id == ""
                    record["departure"] = True
                    emit("C44_DOCK_DEPARTURE", robot_id=first, station_id=dock.id, distance_m=distance,
                         wh=robots_by_id[first].battery_energy_wh)
                return (record["departure"] and record["first_below_target"] and record["charging"] == set(robots)
                        and station.has_owner(second) and robots_by_id[second].battery_energy_wh == 100.0
                        and len(moves) == 3 and all(m["status"] == "ARRIVED" for m in moves))

            await wait_for(accepted, "Charging, departure or transfer did not complete", timeout=140)
            commands = list(store.connection.execute("SELECT * FROM outbox_events"))
            assert len(commands) == 3 and all(row["state"] == "SENT" and row["attempts"] == 1 for row in commands)
            assert {json.loads(row["payload"])["station_id"] for row in commands} == {dock.id, park.id}
            assert store.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert not store.connection.execute("PRAGMA foreign_key_check").fetchall()
            emit("ALL_C4_4_TESTS_PASSED", token=os.environ["DDS_TEST_PAYLOAD"], outbox_commands=len(commands))
        finally:
            if worker is not None:
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)
            await consumer.close()


def main():
    config, _, _ = load_test_config()
    source = Path(config["fleet_config_path"])
    with TemporaryDirectory(prefix="c44-") as directory:
        variant = shutil.copytree(source.parent, Path(directory) / "config") / source.name
        data = yaml.safe_load(variant.read_text())
        for model in data["fleet"]["battery_models"].values():
            model["charge_power_w"] = TEST_CHARGE_POWER_W
        variant.write_text(yaml.safe_dump(data))
        config["fleet_config_path"] = str(variant)
        fleet = load_config(variant)
        if os.environ["SIM_CHECK_ROLE"] == "simulation":
            commands = [
                (label, ["python3", "/opt/simulation-c4-3/battery_entry.py",
                         *command[1:], "--initial-soc", str(soc)])
                for (label, command), soc in zip(battery_commands(config, fleet), INITIAL_SOC)
            ]
            docks = fleet.stations.charging_stations
            return simulation(config, fleet.model_dump(), executor_entry="/opt/simulation-c4-2/executor_test_entry.py",
                              battery_commands=commands, world_modifier=lambda path: install_docks(path, docks, fleet.robots),
                              bridge_arguments=dock_bridge_arguments(docks, fleet.robots))
        logging.basicConfig(level=logging.INFO)
        rclpy.init()
        executor = MultiThreadedExecutor(num_threads=4)
        worker = threading.Thread(target=executor.spin)
        worker.start()
        try:
            asyncio.run(validate(variant, fleet, executor))
        finally:
            executor.shutdown()
            worker.join()
            for node in executor.get_nodes():
                node.destroy_node()
            rclpy.try_shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
