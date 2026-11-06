"""Fence energy input with measured Gazebo contact and committed dock ownership."""

from dataclasses import dataclass
from math import hypot, isfinite


DOCK_EVIDENCE_MAX_AGE_NS = 300_000_000
DOCK_STATUS_MAX_AGE_NS = 500_000_000
STOP_LINEAR_M_S = 0.01
STOP_ANGULAR_RAD_S = 0.01


@dataclass(frozen=True)
class Ownership:
    stamp_ns: int
    robot_id: str
    station_id: str
    session_id: bytes
    epoch: int


class DockGate:
    def __init__(self, robot_id, stations):
        self.robot_id = robot_id
        self.stations = stations
        self.lease = None
        self.status = None
        self.status_seq = 0
        self.session_blocked = False
        self.contact = {}
        self.pose = None
        self.velocity = None

    def observe_status(self, evidence, sequence):
        if evidence.robot_id != self.robot_id or not any(evidence.session_id) or evidence.stamp_ns <= 0:
            return
        if self.status and self.status.session_id != evidence.session_id:
            self.session_blocked = True
        if self.session_blocked or sequence <= self.status_seq:
            return
        if self.status and (evidence.stamp_ns < self.status.stamp_ns or evidence.epoch < self.status.epoch):
            return
        self.status = evidence
        self.status_seq = sequence

    def observe_lease(self, lease):
        if (lease.robot_id == self.robot_id and lease.stamp_ns > 0
                and (self.lease is None or lease.stamp_ns > self.lease.stamp_ns)):
            self.lease = lease

    def observe_contact(self, station_id, stamp_ns, pairs):
        if stamp_ns <= self.contact.get(station_id, (0, False))[0]:
            return
        surface = f"{station_id}::pad::surface"
        occupants = set()
        for first, second in pairs:
            if first == surface:
                occupants.add(second.split("::", 1)[0])
            elif second == surface:
                occupants.add(first.split("::", 1)[0])
        self.contact[station_id] = (stamp_ns, occupants == {self.robot_id})

    def observe_pose(self, stamp_ns, x, y):
        if stamp_ns > (self.pose[0] if self.pose else 0):
            self.pose = (stamp_ns, x, y)

    def observe_velocity(self, stamp_ns, linear, angular):
        if stamp_ns > (self.velocity[0] if self.velocity else 0):
            self.velocity = (stamp_ns, linear, angular)

    def station(self, now_ns):
        lease, status = self.lease, self.status
        if (self.session_blocked or lease is None or status is None
                or not self.pose or not self.velocity or not lease.station_id
                or lease.station_id not in self.stations
                or (lease.station_id, lease.session_id, lease.epoch) !=
                (status.station_id, status.session_id, status.epoch)
                or not 0 <= now_ns - lease.stamp_ns <= DOCK_STATUS_MAX_AGE_NS
                or not 0 <= now_ns - status.stamp_ns <= DOCK_STATUS_MAX_AGE_NS):
            return ""
        contact_ns, contact = self.contact.get(lease.station_id, (0, False))
        pose_ns, x, y = self.pose
        velocity_ns, linear, angular = self.velocity
        target_x, target_y, radius = self.stations[lease.station_id]
        if (contact and all(0 <= now_ns - stamp <= DOCK_EVIDENCE_MAX_AGE_NS
                            for stamp in (contact_ns, pose_ns, velocity_ns))
                and all(isfinite(v) for v in (x, y, linear, angular))
                and hypot(x - target_x, y - target_y) <= radius
                and 0 <= linear <= STOP_LINEAR_M_S and 0 <= angular <= STOP_ANGULAR_RAD_S):
            return lease.station_id
        return ""
