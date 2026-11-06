"""Project one committed Fleet Manager generation onto a private latest-value file."""
import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from itertools import chain, islice
import logging
import os
from pathlib import Path
import tempfile
import time
from uuid import uuid4

from ..fleet_manager.domain.constants import (
    ReservationState, ROBOT_STATUS_STALE_TIMEOUT_SEC, StationType, TaskPriority,
)
from .models import MAX_BYTES, FleetSnapshot, Pose, Robot, SourceSnapshot, Station, Task, TaskCounts
from .telemetry import MAP_FRAME

MAX_TASKS = 100
SAMPLE_INTERVAL = 0.25
logger = logging.getLogger(__name__)


def _pose(pose):
    return Pose(x=pose.x, y=pose.y, yaw=pose.yaw, frame_id=pose.frame_id)


def _fresh_sim(sim_ns, sample_ns):
    return (sim_ns is not None and sample_ns > 0
            and 0 <= sim_ns - sample_ns <= ROBOT_STATUS_STALE_TIMEOUT_SEC * 10**9)


def _robot(core, robot, sample, now, sim_ns):
    status_ns = sample.stamp_ns if sample else 0
    last_map = sample.last_map_sample if sample else None
    age = max(0.0, now - robot.last_status_received_at) if robot.last_status_received_at > 0 else None
    if robot.session_blocked:
        status = "BLOCKED"
    elif age is None:
        status = "NO_DATA"
    elif robot.is_stale(now):
        status = "STALE"
    elif not status_ns or not sample.state:
        status = "UNAVAILABLE"
    else:
        status = "LIVE" if _fresh_sim(sim_ns, status_ns) else "STALE"

    pose_status = status
    if status != "BLOCKED":
        if last_map is None:
            pose_status = "NO_DATA"
        elif (status == "LIVE" and sample.pose_current and now <= robot.route_pose_valid_until
              and _fresh_sim(sim_ns, last_map.stamp_ns)):
            pose_status = "LIVE"
        else:
            pose_status = "STALE"

    battery_live = (status == "LIVE" and sim_ns is not None and robot.requires_battery_telemetry
                    and robot.has_fresh_battery(now, sim_ns))
    if battery_live:
        battery_status = "LIVE"
    elif status in ("BLOCKED", "STALE"):
        battery_status = status
    else:
        battery_status = "UNAVAILABLE" if age is not None else "NO_DATA"

    charging = "UNAVAILABLE"
    charging_station_id = None
    if battery_live:
        station = core.reservations.get_station(robot.charging_station_id)
        if (station is not None and station.station_type == StationType.CHARGING
                and station.state in (ReservationState.OCCUPIED, ReservationState.RELEASING)
                and station.has_owner(robot.robot_id) and robot.dock_station_id == station.station_id):
            charging = "CHARGING"
            charging_station_id = station.station_id
        elif not robot.charging_station_id and sample.state != "CHARGING":
            charging = "NOT_CHARGING"

    active = core._active_tasks_by_robot.get(robot.robot_id)
    return Robot(
        robot_id=robot.robot_id, state=sample.state if sample else None, telemetry=status,
        initial_status_verified=robot.initial_status_verified,
        status_sim_ns=str(status_ns) if status_ns else None, status_age_sec=age,
        pose=_pose(last_map.pose) if last_map else None, pose_reliability=pose_status,
        pose_sim_ns=str(last_map.stamp_ns) if last_map else None,
        battery_reliability=battery_status,
        battery_soc_percent=robot.battery_soc_percent if battery_live else None,
        battery_energy_wh=robot.battery_energy_wh if battery_live else None,
        battery_sim_ns=str(robot.battery_sample_ns) if robot.battery_sample_ns else None,
        charging=charging, charging_station_id=charging_station_id,
        active_task_id=active.task_id if active else None,
    )


def _station(station, robots):
    owner = robots.get(station.occupied_by_robot_id or station.reserved_by_robot_id)
    charging = "NOT_APPLICABLE"
    charging_robot_id = None
    if station.station_type == StationType.CHARGING:
        charging = "UNAVAILABLE"
        if owner and owner.charging_station_id == station.station_id:
            charging = "CHARGING"
            charging_robot_id = owner.robot_id
        elif owner and owner.charging == "NOT_CHARGING":
            charging = "NOT_CHARGING"
    pose = station.pose
    return Station(
        station_id=station.station_id, station_type=station.station_type, state=station.state,
        pose=_pose(pose) if pose.frame_id == MAP_FRAME and pose.has_finite_coordinates() else None,
        reserved_by_robot_id=station.reserved_by_robot_id,
        occupied_by_robot_id=station.occupied_by_robot_id,
        charging=charging, charging_robot_id=charging_robot_id,
    )


def project(sample, source_session_id, sequence, generated_at):
    core, telemetry, now, sim_ns = sample
    robots = {r.robot_id: _robot(core, r, telemetry.get(r.robot_id), now, sim_ns)
              for r in core.tracker.list_robots()}
    active = core._active_tasks
    pending = core._pending_preemption_assignments
    completed, failed = core._completed_tasks, core._failed_tasks
    # Active assignments first, then the existing dispatch queue and retained terminal records.
    entries = chain(active.values(), core.queue.iter_assignable_tasks(), pending.values(),
                    reversed(completed.values()), reversed(failed.values()))
    tasks = tuple(
        Task(task_id=t.task_id, status=t.status.value, priority=TaskPriority(t.priority).name.removeprefix("PRIORITY_"),
             pickup=_pose(t.pickup_pose), dropoff=_pose(t.dropoff_pose), assigned_robot_id=t.assigned_robot_id,
             created_at_source_seconds=t.created_at or None, review_hold=core.has_review_hold(t.task_id))
        for t in islice(entries, MAX_TASKS)
    )
    queued = len(core.queue) + len(pending)
    return FleetSnapshot(
        source_session_id=source_session_id, sequence=sequence, generated_at_utc=generated_at,
        robots=tuple(robots.values()), tasks=tasks,
        task_counts=TaskCounts(total=len(active) + queued + len(completed) + len(failed),
                               active=len(active), queued=queued),
        stations=tuple(_station(s, robots) for s in core.reservations.list_stations()),
    )


def _write(path, sample, session, sequence, captured_ns, utc):
    source = SourceSnapshot(captured_monotonic_ns=captured_ns, fleet=project(sample, session, sequence, utc))
    data = source.model_dump_json().encode()
    if len(data) > MAX_BYTES:
        raise ValueError("Dashboard snapshot exceeds size limit")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            temporary.write(data)
            temporary.close()
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)


async def _publish(consumer, path):
    session = str(uuid4())
    sequence = 0
    failed = False
    while True:
        started = time.monotonic_ns()
        try:
            sample = consumer.dashboard_sample()
            sequence += 1
            await asyncio.to_thread(_write, path, sample, session, sequence, started, datetime.now(timezone.utc))
            failed = False
        except Exception:
            if not failed:
                logger.exception("Dashboard snapshot unavailable")
                failed = True
        remaining = SAMPLE_INTERVAL - (time.monotonic_ns() - started) / 10**9
        await asyncio.sleep(max(0.0, remaining))


@asynccontextmanager
async def publish_fleet(consumer, path):
    """Optional producer. Its lifetime follows the consumer, never HTTP clients."""
    consumer.enable_dashboard_sampling()
    task = asyncio.create_task(_publish(consumer, Path(path)))
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        consumer.disable_dashboard_sampling()
