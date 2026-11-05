"""Two-robot Fortress acceptance with real Battery Simulator, Executor and Fleet Manager."""

import asyncio
from contextlib import closing, contextmanager
import json
import logging
from math import hypot
import os
from pathlib import Path
import shutil
import signal
import sys
from tempfile import TemporaryDirectory
import threading
import time

import rclpy
from fleet_interfaces.msg import BatteryState, RobotStatus
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import Odometry
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
import yaml

from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain import Pose2D, TaskPriority
from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
from backend.fleet_manager.persistence.store import SQLiteStore
from battery_check import battery_commands
from check import emit, load_config as load_test_config, simulation
from fleet_battery_simulator.node import stamp_ns
from fleet_config.loader import load_config

PICKUP = Pose2D(-1.5, -0.5)
DROPOFF = Pose2D(-1.0, -0.5)


async def wait_for(condition, description, timeout=30.0):
    deadline = time.monotonic() + timeout
    while True:
        value = condition()
        if value:
            return value
        if time.monotonic() >= deadline:
            raise TimeoutError(description)
        await asyncio.sleep(0.05)


@contextmanager
def pause_battery_processes(robot_ids):
    """Keep the DDS writers and in-memory energy state across a short outage."""
    pids = {}
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            args = path.read_bytes().split(b"\0")
        except (FileNotFoundError, ProcessLookupError):
            continue
        if b"--robot-id" in args and any(arg.endswith(b"/battery_simulator") for arg in args):
            robot_id = args[args.index(b"--robot-id") + 1].decode()
            assert robot_id not in pids
            pids[robot_id] = int(path.parent.name)
    assert set(pids) == set(robot_ids), pids
    paused = []
    try:
        for pid in pids.values():
            os.kill(pid, signal.SIGSTOP)
            paused.append(pid)
        yield
    finally:
        for pid in paused:
            os.kill(pid, signal.SIGCONT)


class LiveBatteryCheck:
    def __init__(self, fleet, executor):
        self.fleet = fleet
        self.executor = executor
        self.namespaces = {robot.id: robot.namespace for robot in fleet.robots}
        self.states = {robot_id: {} for robot_id in self.namespaces}
        self.status = {robot_id: {} for robot_id in self.namespaces}
        self.odom = {}
        self.probe = rclpy.create_node("c42_live_probe")
        executor.add_node(self.probe)
        for robot_id, ns in self.namespaces.items():
            self.probe.create_subscription(
                BatteryState, f"{ns}/battery_state",
                lambda msg, rid=robot_id: self.states[rid].__setitem__(stamp_ns(msg.battery_stamp), msg), 10,
            )
            self.probe.create_subscription(
                RobotStatus, f"{ns}/robot_status",
                lambda msg, rid=robot_id: self.status[rid].__setitem__(stamp_ns(msg.battery_stamp), msg), 10,
            )
            self.probe.create_subscription(
                Odometry, f"{ns}/odom",
                lambda msg, rid=robot_id: self.odom.__setitem__(rid, msg.pose.pose.position), qos_profile_sensor_data,
            )

    async def verify_graph(self):
        for robot_id, ns in self.namespaces.items():
            topic = f"{ns}/battery_state"
            def expected_publisher():
                endpoints = self.probe.get_publishers_info_by_topic(topic)
                assert len(endpoints) <= 1, endpoints
                if endpoints:
                    endpoint = endpoints[0]
                    if (endpoint.node_name, endpoint.node_namespace, endpoint.topic_type) == (
                        "battery_simulator", ns, "fleet_interfaces/msg/BatteryState",
                    ):
                        return endpoint
                return None

            endpoint = await wait_for(expected_publisher, f"Battery publisher identity unresolved on {topic}")
            await wait_for(
                lambda: any(e.node_name == f"robot_executor_{robot_id}" and e.topic_type == endpoint.topic_type
                            for e in self.probe.get_subscriptions_info_by_topic(topic)),
                f"Executor subscription missing on {topic}",
            )
            client = self.probe.create_client(GetState, f"{ns}/planner_server/get_state")
            await wait_for(client.service_is_ready, f"Planner service missing for {robot_id}", timeout=60)
            for _ in range(30):
                result = client.call_async(GetState.Request())
                await wait_for(result.done, "Planner state request did not return")
                if result.result().current_state.label == "active":
                    break
                await asyncio.sleep(0.25)
            else:
                raise AssertionError(f"Planner inactive for {robot_id}")
        assert self.probe.count_publishers("/clock") == 1
        assert not any("mock_battery_feeder" in name for name, _ in self.probe.get_node_names_and_namespaces())
        emit("C42_GRAPH_VERIFIED", battery_topics=[f"{ns}/battery_state" for ns in self.namespaces.values()])

    def verify_snapshot(self, consumer, store, *, event):
        matched = {}
        now = time.monotonic()
        for robot in consumer.core.tracker.list_robots():
            if not robot.has_fresh_battery(now):
                return None
            robot_id, stamp = robot.robot_id, robot.battery_sample_ns
            battery, status = self.states[robot_id].get(stamp), self.status[robot_id].get(stamp)
            if battery is None or status is None:
                return None
            row = store.connection.execute("SELECT snapshot FROM robots WHERE robot_id=?", (robot_id,)).fetchone()
            saved = json.loads(row["snapshot"])
            assert battery.robot_id == status.robot_id == robot_id
            assert battery.battery_energy_wh == status.battery_energy_wh == robot.battery_energy_wh == saved["battery_energy_wh"]
            assert battery.battery_soc_percent == status.battery_soc_percent == robot.battery_soc_percent == saved["battery_soc_percent"]
            assert saved["battery_sample_ns"] == stamp
            assert stamp <= stamp_ns(status.header.stamp)
            matched[robot_id] = battery
        emit(event, robots={rid: {"stamp_ns": stamp_ns(msg.battery_stamp), "energy_wh": msg.battery_energy_wh,
                                 "soc_percent": msg.battery_soc_percent} for rid, msg in matched.items()})
        return matched

    async def run_case(self, config_path, db_path, *, insufficient):
        case = "insufficient" if insufficient else "outage"
        core, robot_ids = build_fleet_manager_from_config(config_path)
        node = rclpy.create_node(f"c42_fleet_{case}", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.executor.add_node(node)
        try:
            with closing(SQLiteStore(db_path)) as store:
                consumer = FleetEventLoop(store, core)
                adapter = FleetROS2Adapter(
                    node, consumer, asyncio.get_running_loop(), robot_ids, robot_namespaces=self.namespaces,
                )
                await consumer.start()
                try:
                    before = await wait_for(
                        lambda: self.verify_snapshot(consumer, store, event="C42_SNAPSHOT_VERIFIED"),
                        "BatteryState, RobotStatus and SQLite do not agree",
                    )
                    submission = Event("SUBMIT_TASK", dict(
                        task_id="delivery", pickup_pose=PICKUP, dropoff_pose=DROPOFF,
                        priority=TaskPriority.PRIORITY_LOW, created_at=time.monotonic(),
                    ))
                    if insufficient:
                        await self.verify_insufficient(consumer, store, adapter, submission, config_path)
                    else:
                        await self.verify_outage_and_delivery(consumer, store, adapter, submission, before)
                finally:
                    await consumer.close()
        finally:
            self.executor.remove_node(node)
            node.destroy_node()

    @staticmethod
    def assert_queued(store):
        assert store.connection.execute("SELECT status FROM tasks").fetchone()[0] == "QUEUED"
        assert store.connection.execute("SELECT count(*) FROM outbox_events").fetchone()[0] == 0

    async def verify_insufficient(self, consumer, store, adapter, submission, config_path):
        await consumer.submit(submission)
        fleet = load_config(config_path)
        escape = consumer.core.scheduler.safe_charge_station_pose

        def observed_distances():
            now = time.monotonic()
            result = {}
            for robot in consumer.core.tracker.list_robots():
                legs = ((robot.pose, PICKUP), (PICKUP, DROPOFF), (DROPOFF, escape))
                distances = [adapter.route_cache.get(robot.robot_id, start, goal, now=now) for start, goal in legs]
                if not robot.has_fresh_battery(now) or any(distance is None for distance in distances):
                    return None
                result[robot.robot_id] = (robot, distances)
            return result

        records = await wait_for(observed_distances, "Real Nav2 route legs missing", timeout=50)
        await consumer.submit(Event("TICK", {"current_time": time.monotonic()}))
        self.assert_queued(store)
        for robot_id, (robot, distances) in records.items():
            required = robot.specs.consumption_wh_per_meter * sum(distances) + fleet.policies.safety_margin_wh
            available = robot.battery_energy_wh - robot.specs.usable_capacity_wh * fleet.policies.emergency_soc_percent / 100
            assert required > available
            emit("C42_ENERGY_INSUFFICIENT", robot_id=robot_id, distances_m=distances,
                 required_wh=required, available_wh=available, execute_commands=0)

    async def verify_outage_and_delivery(self, consumer, store, adapter, submission, before):
        with pause_battery_processes(self.namespaces):
            def battery_lost():
                now = time.monotonic()
                return all(not robot.is_stale(now) and not robot.has_fresh_battery(now)
                           for robot in consumer.core.tracker.list_robots())
            await wait_for(battery_lost, "Battery outage did not invalidate both fresh RobotStatus streams", timeout=5)
            await consumer.submit(submission)
            await consumer.submit(Event("TICK", {"current_time": time.monotonic()}))
            self.assert_queued(store)
            emit("C42_OUTAGE_BLOCKED", robots=list(self.namespaces), execute_commands=0)

        after = await wait_for(
            lambda: self.verify_snapshot(consumer, store, event="C42_TELEMETRY_RECOVERED"),
            "Same publisher did not resume assignment-quality telemetry", timeout=10,
        )
        for robot_id, msg in after.items():
            assert bytes(msg.publisher_session_id.uuid) == bytes(before[robot_id].publisher_session_id.uuid)
            assert msg.battery_energy_wh <= before[robot_id].battery_energy_wh

        start_positions = self.odom.copy()
        dispatcher = OutboxDispatcher(consumer, adapter.outbox_sender, clock=time.monotonic, retry_delay=1.0)

        def assignment():
            return store.connection.execute(
                "SELECT robot_id, assignment_epoch FROM tasks WHERE task_id='delivery' AND status='ASSIGNED'"
            ).fetchone()

        assigned = await wait_for(assignment, "Fresh battery and live route did not produce assignment", timeout=50)
        moving = self.fleet.robots[0].id
        assert assigned["robot_id"] == moving and assigned["assignment_epoch"] == 1
        route_count = store.connection.execute(
            "SELECT count(*) FROM processed_events WHERE outcome='ROUTE_APPLIED'"
        ).fetchone()[0]
        # The other robot can recover a heartbeat later. Its three routes are
        # already required in the insufficient-energy case.
        assert route_count >= 3
        assert await dispatcher.send_one()

        def complete():
            snapshot = consumer.core
            assert "delivery" not in snapshot._failed_tasks, "Active Nav2 transport failed"
            return "delivery" in snapshot._completed_tasks

        await wait_for(complete, "Real Nav2 delivery did not finish", timeout=120)
        end = await wait_for(
            lambda: self.verify_snapshot(consumer, store, event="C42_AFTER_DELIVERY"),
            "End-of-delivery energy not verified",
        )
        for robot_id, msg in end.items():
            start = after[robot_id]
            model_id = next(robot.battery_model for robot in self.fleet.robots if robot.id == robot_id)
            model = self.fleet.fleet.battery_models[model_id]
            start_pos, end_pos = start_positions[robot_id], self.odom[robot_id]
            displacement = hypot(end_pos.x - start_pos.x, end_pos.y - start_pos.y)
            elapsed = (stamp_ns(msg.battery_stamp) - stamp_ns(start.battery_stamp)) / 10**9
            motion_wh = start.battery_energy_wh - msg.battery_energy_wh - model.idle_power_w * elapsed / 3600
            if robot_id == moving:
                assert displacement > 0.5
                assert motion_wh > 0.1
            else:
                assert displacement < 0.001
                assert abs(motion_wh) < 0.0001
            emit("C42_INDEPENDENT_CONSUMPTION", robot_id=robot_id, elapsed_sim_sec=elapsed,
                 displacement_m=displacement, motion_wh=motion_wh)
        emit("C42_DELIVERY_COMPLETED", robot_id=moving, live_route_results=route_count)


async def validate(config_path, fleet, executor):
    check = LiveBatteryCheck(fleet, executor)
    await check.verify_graph()
    source = Path(config_path)
    with TemporaryDirectory(prefix="c42-") as directory:
        work = Path(directory)
        variant = shutil.copytree(source.parent, work / "config") / source.name
        data = yaml.safe_load(variant.read_text())
        # Drive the inequality with a test-only margin while preserving the real battery model.
        data["policies"]["safety_margin_wh"] = 91.99
        variant.write_text(yaml.safe_dump(data))
        await check.run_case(variant, work / "insufficient.db", insufficient=True)
        await check.run_case(source, work / "delivery.db", insufficient=False)
    emit("ALL_C4_2_TESTS_PASSED", token=os.environ["DDS_TEST_PAYLOAD"])


def main():
    config, fleet_data, _ = load_test_config()
    fleet = load_config(config["fleet_config_path"])
    if os.environ["SIM_CHECK_ROLE"] == "simulation":
        return simulation(
            config, fleet_data, executor_entry="/opt/simulation-c4-2/executor_test_entry.py",
            battery_commands=battery_commands(config, fleet),
        )
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
