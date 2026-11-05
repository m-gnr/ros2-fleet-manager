"""Compare YAML margins using identical real Nav2 distances and live RobotStatus."""
import asyncio
from contextlib import closing
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import time

import rclpy
from rclpy.parameter import Parameter
import yaml

from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
from backend.fleet_manager.adapters.route_cache import CachedRouteDistanceProvider, RouteCache
from backend.fleet_manager.adapters.route_resolver import AsyncRouteResolver
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain import Pose2D, TaskPriority
from backend.fleet_manager.event_loop import Event, FleetEventLoop
from backend.fleet_manager.persistence.store import SQLiteStore


async def check_energy_policy(fleet_path, robot_namespaces, executor, path_clients, emit):
    test = "YAML-ENERGY-POLICY"
    emit("SCENARIO_START", test=test)
    cache = RouteCache()
    provider = CachedRouteDistanceProvider(cache)
    resolver = AsyncRouteResolver(cache)
    for robot_id, client in path_clients.items():
        resolver.register_robot_client(robot_id, client)

    pickup = Pose2D(-1.5, -0.5)
    dropoff = Pose2D(-1.0, -0.5)
    source = Path(fleet_path)
    data = yaml.safe_load(source.read_text())
    reserve = data["policies"]["emergency_soc_percent"]
    observed_routes = {}
    with TemporaryDirectory(prefix="c334-energy-policy-") as temp:
        work = Path(temp)
        variant = shutil.copytree(source.parent, work / "config") / source.name
        for case, margin, expected_commands in [
            ("high", 91.99, []),
            ("low", 10.0, [("delivery", "robot_1", "PENDING")]),
        ]:
            data["policies"]["safety_margin_wh"] = margin
            variant.write_text(yaml.safe_dump(data))
            core, robot_ids = build_fleet_manager_from_config(variant, provider)
            assert len(robot_ids) == 2
            node = rclpy.create_node(
                f"fm_energy_policy_{case}",
                parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)],
            )
            executor.add_node(node)
            try:
                with closing(SQLiteStore(work / f"{case}.db")) as store:
                    loop = FleetEventLoop(store, core)
                    await loop.start()
                    try:
                        FleetROS2Adapter(
                            node, loop, asyncio.get_running_loop(), robot_ids,
                            robot_namespaces=robot_namespaces, enable_live_routing=False,
                        )
                        deadline = time.monotonic() + 10.0
                        while True:
                            robots = loop.core.tracker.list_robots()
                            if all(robot.is_eligible_for_new_assignment(time.monotonic()) for robot in robots):
                                break
                            assert time.monotonic() < deadline, "Both live robots must report fresh IDLE status"
                            await asyncio.sleep(0.1)

                        escape = core.scheduler.safe_charge_station_pose
                        if case == "high":
                            for robot in robots:
                                legs = ((robot.pose, pickup), (pickup, dropoff), (dropoff, escape))
                                observed_routes[robot.robot_id] = [
                                    await resolver.query_route(robot.robot_id, start, goal) for start, goal in legs
                                ]
                        await loop.submit(Event("SUBMIT_TASK", {
                            "task_id": "delivery", "pickup_pose": pickup, "dropoff_pose": dropoff,
                            "priority": TaskPriority.PRIORITY_LOW, "created_at": 1,
                        }))
                        # Read the same cache legs at the currently accepted poses.
                        now = time.monotonic()
                        for robot in loop.core.tracker.list_robots():
                            assert robot.is_eligible_for_new_assignment(now)
                            assert robot.battery_soc_percent == 100.0
                            legs = ((robot.pose, pickup), (pickup, dropoff), (dropoff, escape))
                            distances = [cache.get(robot.robot_id, start, goal, now=now) for start, goal in legs]
                            assert all(distance is not None for distance in distances), (robot.robot_id, distances)
                            assert distances == observed_routes[robot.robot_id]
                            required = robot.specs.consumption_wh_per_meter * sum(distances) + margin
                            available = robot.specs.usable_capacity_wh * (robot.battery_soc_percent - reserve) / 100
                            assert (required <= available) == bool(expected_commands)
                            emit("ENERGY_POLICY_INPUT", case=case, robot_id=robot.robot_id, distances_m=distances,
                                 soc_percent=robot.battery_soc_percent, reserve_percent=reserve,
                                 margin_wh=margin, required_wh=required, available_wh=available)

                        await loop.submit(Event("TICK", {"current_time": now}))
                        commands = store.connection.execute(
                            "SELECT task_id, json_extract(payload, '$.assigned_robot_id'), state "
                            "FROM outbox_events WHERE kind='EXECUTE_TASK' ORDER BY task_id"
                        ).fetchall()
                        commands = [tuple(row) for row in commands]
                        status = store.connection.execute("SELECT status FROM tasks").fetchone()[0]
                        assert status == ("ASSIGNED" if expected_commands else "QUEUED")
                        assert commands == expected_commands
                        emit("ENERGY_POLICY_SQLITE", case=case, status=status, commands=commands)
                    finally:
                        await loop.close()
            finally:
                executor.remove_node(node)
                node.destroy_node()
    emit("SCENARIO_PASSED", test=test)
