"""ROS-independent pose validation and stream state."""
from dataclasses import dataclass
from math import atan2, hypot, isfinite
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from observed_plan import ObservedPlan

NS = 1_000_000_000


def yaw_from_quaternion(x, y, z, w):
    length = hypot(x, y, z, w)
    if not isfinite(length) or abs(length - 1) > 0.01:
        raise ValueError("Invalid orientation quaternion")
    x, y, z, w = (value / length for value in (x, y, z, w))
    return atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


@dataclass(frozen=True)
class Pose:
    robot_id: str
    frame_id: str
    stamp_ns: int
    x: float
    y: float
    yaw: float
    received_ns: int


@dataclass(frozen=True)
class Snapshot:
    epoch: int = 0
    status: str = "NO_DATA"
    pose: Optional[Pose] = None
    plan: Optional["ObservedPlan"] = None


class Telemetry:
    def __init__(self, robot_id, frame_id, source, stale_seconds):
        self.identity = dict(version=1, stream_id=str(uuid4()), robot_id=robot_id,
                             frame_id=frame_id, source=source)
        self.stale_ns = round(stale_seconds * NS)
        self.clock_observation = (0, 0)
        self.clock_advanced_ns = 0
        self.pose = None

    @property
    def clock_ns(self):
        return self.clock_observation[1]

    def clock(self, stamp_ns, now_ns):
        epoch, previous = self.clock_observation
        rewound = stamp_ns < previous
        if rewound:
            epoch += 1
            self.pose = None
        if stamp_ns != previous:
            self.clock_advanced_ns = now_ns
        self.clock_observation = (epoch, stamp_ns)
        return rewound

    def sample(self, candidate, now_ns, *, frame_error=False):
        clock_fresh = self.clock_ns > 0 and now_ns - self.clock_advanced_ns < self.stale_ns
        status = "NO_DATA"
        if candidate is not None and (
            candidate.robot_id != self.identity["robot_id"]
            or candidate.frame_id != self.identity["frame_id"]
        ):
            frame_error = True
            candidate = None
        if not frame_error and clock_fresh and self.fresh(candidate, now_ns):
            if self.pose is None or candidate.stamp_ns > self.pose.stamp_ns:
                self.pose = candidate
        if frame_error:
            status = "FRAME_ERROR"
        elif self.pose is not None:
            status = "LIVE" if clock_fresh and self.fresh(self.pose, now_ns) else "STALE"
        return Snapshot(self.clock_observation[0], status, self.pose)

    def fresh(self, pose, now_ns):
        return (pose is not None and 0 < pose.stamp_ns
                and 0 <= self.clock_ns - pose.stamp_ns < self.stale_ns
                and 0 <= now_ns - pose.received_ns < self.stale_ns
                and all(isfinite(value) for value in (pose.x, pose.y, pose.yaw)))


def pose_packet(identity, epoch, pose):
    return dict(identity, type="robot_pose", epoch=epoch, stamp_ns=str(pose.stamp_ns),
                x=pose.x, y=pose.y, yaw=pose.yaw)
