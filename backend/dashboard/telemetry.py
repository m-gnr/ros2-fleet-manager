"""Bounded post-commit observation of physical RobotStatus values."""
from dataclasses import dataclass
from uuid import UUID

from ..fleet_manager.domain.constants import RobotState
from ..fleet_manager.domain.models import Pose2D

MAP_FRAME = "map"


@dataclass(frozen=True)
class MapSample:
    pose: Pose2D
    stamp_ns: int


@dataclass(frozen=True)
class StatusSample:
    state: str | None
    stamp_ns: int
    pose_current: bool
    last_map_sample: MapSample | None


class CommittedTelemetry:
    def __init__(self):
        self._samples: dict[str, StatusSample] = {}

    def snapshot(self):
        return self._samples.copy()

    def record(self, robot, payload, now):
        previous = self._samples.get(robot.robot_id)
        last_map_sample = previous.last_map_sample if previous else None
        stamp = payload.get("source_status_ns", 0)
        try:
            session_valid = bool(UUID(robot.session_id).int)
        except (ValueError, TypeError, AttributeError):
            session_valid = False
        if not session_valid or not stamp or not payload.get("status_seq"):
            self._samples[robot.robot_id] = StatusSample(None, 0, False, last_map_sample)
            return

        pose = payload.get("pose")
        sample_ns = payload.get("pose_sample_ns", 0)
        pose_current = (
            isinstance(pose, Pose2D) and pose.frame_id == MAP_FRAME and pose.has_finite_coordinates()
            and 0 < sample_ns <= stamp and now <= robot.route_pose_valid_until
        )
        if pose_current:
            sample = MapSample(pose, sample_ns)
            if last_map_sample is None or sample_ns > last_map_sample.stamp_ns:
                last_map_sample = sample
            pose_current = sample == last_map_sample
        try:
            state = RobotState(payload["state"]).name.removeprefix("STATE_")
        except ValueError:
            state = None
        self._samples[robot.robot_id] = StatusSample(state, stamp, pose_current, last_map_sample)
