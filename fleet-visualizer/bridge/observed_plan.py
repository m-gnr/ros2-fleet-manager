"""Validate observations from the verified Humble Nav2 planner topology."""
from dataclasses import dataclass
from math import hypot, isfinite

from telemetry import NS

PLAN_TTL_NS = 2 * NS
MAX_POINTS = 1024
MAX_ROS_BYTES = 112 * 1024
MAX_COORDINATE = 10_000  # Keep validated coordinates safe for Float32 rendering.


@dataclass(frozen=True)
class ObservedPlan:
    stamp_ns: int
    received_ns: int
    points: tuple[tuple[float, float], ...]


class PlanBuffer:
    def __init__(self):
        self.reset()

    def reset(self):
        self.plan = None
        self.cutoff = 0

    def accept(self, message, clock, now):
        header = message.header
        stamp = header.stamp.sec * NS + header.stamp.nanosec
        # Allow a little DDS ordering skew between /clock and the planner.
        if clock <= 0 or stamp <= self.cutoff or not -NS // 10 <= clock - stamp < PLAN_TTL_NS:
            return
        if (header.frame_id != "map" or not 0 <= header.stamp.nanosec < NS
                or not 2 <= len(message.poses) <= MAX_POINTS):
            self.plan = None
            return

        points = []
        for row in message.poses:
            position, q = row.pose.position, row.pose.orientation
            if (row.header.frame_id != "map" or row.header.stamp != header.stamp
                    or not all(isfinite(v) and abs(v) <= MAX_COORDINATE
                               for v in (position.x, position.y, position.z))
                    or not abs(hypot(q.x, q.y, q.z, q.w) - 1) <= 0.01):
                self.plan = None
                return
            points.append((position.x, position.y))
        self.plan = ObservedPlan(stamp, now, tuple(points))
        self.cutoff = stamp

    def current(self, clock, now):
        plan = self.plan
        if plan is None:
            return None
        if now - plan.received_ns >= PLAN_TTL_NS or clock - plan.stamp_ns >= PLAN_TTL_NS:
            self.plan = None
            return None
        return plan if clock >= plan.stamp_ns else None
