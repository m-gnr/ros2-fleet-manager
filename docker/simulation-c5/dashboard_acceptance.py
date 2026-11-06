"""Add the optional snapshot producer to the existing C4.5 charging acceptance."""
import asyncio
import json
from contextlib import AsyncExitStack
import os
from pathlib import Path
import time

from backend.dashboard.api import read_source
from backend.dashboard.publisher import publish_fleet
from backend.fleet_manager.adapters.status_subscriber import quaternion_to_yaw
from backend.fleet_manager.event_loop import Event
from charging_check import main, validate
from check import emit
from fleet_acceptance import PreemptionObserver, validate_post_charge
from integration_check import stamp_ns, wait_for


class DashboardObserver(PreemptionObserver):
    async def start(self):
        self.dashboard_stack = AsyncExitStack()
        await self.dashboard_stack.enter_async_context(
            publish_fleet(self, Path(os.environ["C5_SNAPSHOT_PATH"]))
        )
        try:
            await super().start()
        except BaseException:
            await self.dashboard_stack.aclose()
            raise

    async def close(self):
        try:
            await self.dashboard_stack.aclose()
        finally:
            await super().close()


async def measure(consumer, dispatcher, label, duration=8):
    emit("C5_MEASURE_START", mode=label)
    delays = []
    cpu = time.process_time()
    start = time.monotonic()
    period = 0.05
    while time.monotonic() - start < duration:
        scheduled = time.monotonic()
        await consumer.submit(Event("TICK", {"current_time": scheduled}))
        await dispatcher.send_one()
        await asyncio.sleep(max(0, scheduled + period - time.monotonic()))
        delays.append(max(0, time.monotonic() - scheduled - period) * 1000)
    elapsed = time.monotonic() - start
    rss = int(Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    emit("C5_MEASURE_END", mode=label, samples=len(delays), seconds=elapsed,
         consumer_tick_delay_p95_ms=sorted(delays)[int(len(delays) * 0.95)],
         backend_fm_cpu_percent=(time.process_time() - cpu) / elapsed * 100, backend_fm_rss_bytes=rss)


async def post_charge(fleet, probe, node, consumer, store, dispatcher):
    await validate_post_charge(fleet, probe, node, consumer, store, dispatcher)
    terminal_fence = time.monotonic_ns()

    def verified():
        path = Path(os.environ["C5_SNAPSHOT_PATH"])
        source = read_source(path)
        if (not source or source.captured_monotonic_ns < terminal_fence
                or source.fleet.task_counts.active or not source.fleet.tasks):
            return None
        for robot in source.fleet.robots:
            if robot.battery_reliability != "LIVE" or robot.pose_reliability != "LIVE":
                return None
            stamp = int(robot.battery_sim_ns)
            battery = probe.states[robot.robot_id].get(stamp)
            if battery is None:
                return None
            assert battery.battery_soc_percent == robot.battery_soc_percent
            assert battery.battery_energy_wh == robot.battery_energy_wh
            measured_pose = next((msg.pose for msg in list(probe.status[robot.robot_id].values())
                                  if stamp_ns(msg.pose.header.stamp) == int(robot.pose_sim_ns)), None)
            if measured_pose is None:
                return None
            assert robot.pose.frame_id == measured_pose.header.frame_id == "map"
            assert (robot.pose.x, robot.pose.y) == (measured_pose.pose.position.x, measured_pose.pose.position.y)
            orientation = measured_pose.pose.orientation
            assert robot.pose.yaw == quaternion_to_yaw(orientation.x, orientation.y, orientation.z, orientation.w)
        for task in source.fleet.tasks:
            saved = store.connection.execute("SELECT * FROM tasks WHERE task_id=?", (task.task_id,)).fetchone()
            assert (task.status, task.assigned_robot_id) == (saved["status"], saved["robot_id"])
        for station in source.fleet.stations:
            saved = store.connection.execute("SELECT * FROM reservations WHERE station_id=?",
                                             (station.station_id,)).fetchone()
            assert (station.state, station.occupied_by_robot_id, station.reserved_by_robot_id) == (
                saved["state"], saved["occupied_by"], saved["reserved_by"],
            )
            assert station.pose.model_dump() == json.loads(saved["snapshot"])["pose"]
        Path("/evidence/verified-source.json").write_text(source.fleet.model_dump_json(indent=2))
        return source

    snapshot = await wait_for(verified, "C5 source did not match verified battery and SQLite records", timeout=10)
    emit("C5_SOURCE_MATCHED", sequence=snapshot.fleet.sequence)
    await measure(consumer, dispatcher, "publisher-enabled", duration=15)
    await consumer.dashboard_stack.aclose()
    await measure(consumer, dispatcher, "publisher-disabled")


async def check(config_path, fleet, executor):
    await validate(
        config_path, fleet, executor, consumer_type=DashboardObserver,
        after_charging=post_charge, database_path="/evidence/c5-charging.sqlite3",
    )


if __name__ == "__main__":
    raise SystemExit(main(check=check))
