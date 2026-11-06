"""Versioned display schema, independent from ROS and persistence."""
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

MAX_BYTES = 512 * 1024
SOURCE_TTL_NS = 1_500_000_000

Reliability = Literal["LIVE", "STALE", "NO_DATA", "BLOCKED", "UNAVAILABLE"]


class DisplayModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)


class Pose(DisplayModel):
    x: float
    y: float
    yaw: float
    frame_id: str


class Robot(DisplayModel):
    robot_id: str
    state: Literal[
        "IDLE", "EXECUTING_TASK", "CHARGING", "RETURNING_TO_CHARGE", "RETURNING_TO_PARK", "ERROR"
    ] | None
    telemetry: Reliability
    initial_status_verified: bool
    status_sim_ns: str | None
    status_age_sec: float | None
    pose: Pose | None
    pose_sim_ns: str | None
    pose_reliability: Reliability
    battery_reliability: Reliability
    battery_soc_percent: float | None = Field(ge=0, le=100)
    battery_energy_wh: float | None = Field(ge=0)
    battery_sim_ns: str | None
    charging: Literal["CHARGING", "NOT_CHARGING", "UNAVAILABLE"]
    charging_station_id: str | None
    active_task_id: str | None


class Task(DisplayModel):
    task_id: str
    status: str
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    pickup: Pose
    dropoff: Pose
    assigned_robot_id: str | None
    created_at_source_seconds: float | None
    review_hold: bool


class Station(DisplayModel):
    station_id: str
    station_type: Literal["CHARGING", "PARKING", "SAFE_WAITING"]
    pose: Pose | None
    state: Literal["FREE", "RESERVED", "OCCUPIED", "RELEASING", "BLOCKED"]
    reserved_by_robot_id: str | None
    occupied_by_robot_id: str | None
    charging: Literal["CHARGING", "NOT_CHARGING", "UNAVAILABLE", "NOT_APPLICABLE"]
    charging_robot_id: str | None


class TaskCounts(DisplayModel):
    total: int = Field(ge=0)
    queued: int = Field(ge=0)
    active: int = Field(ge=0)


class FleetSnapshot(DisplayModel):
    schema_version: Literal[1] = 1
    source_session_id: str
    sequence: int = Field(gt=0, le=2**53 - 1)
    generated_at_utc: AwareDatetime
    map_frame: Literal["map"] = "map"
    robots: tuple[Robot, ...]
    tasks: tuple[Task, ...]
    task_counts: TaskCounts
    stations: tuple[Station, ...]


class SourceSnapshot(DisplayModel):
    captured_monotonic_ns: int = Field(gt=0)
    fleet: FleetSnapshot


class WireSnapshot(FleetSnapshot):
    backend_session_id: str
