"""Offline final-velocity interlock model; no ROS wiring or nonzero enable exists."""
from copy import deepcopy
from dataclasses import dataclass
import math
import hashlib
import json
from uuid import uuid4

from .traffic import MovementGate


@dataclass(frozen=True)
class GateOutput:
    velocity: tuple
    reasons: tuple
    stop_requested: bool = True
    physical_stop: str = 'UNKNOWN'
    ownership_release: bool = False


def _box(value):
    return (isinstance(value, (tuple, list)) and len(value) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in value)
            and value[0] < value[2] and value[1] < value[3])


def boundary_digest(regions):
    """Same canonical geometry encoding as B6B.2; not authentication."""
    boxes = [dict(zip(('x0', 'y0', 'x1', 'y1'), r)) for r in regions]
    return hashlib.sha256(json.dumps(boxes, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _covered(box, regions):
    """Full AABB containment in a union, including gaps between path segments."""
    xs = sorted({box[0], box[2], *(v for r in regions for v in (r[0], r[2]) if box[0] < v < box[2])})
    ys = sorted({box[1], box[3], *(v for r in regions for v in (r[1], r[3]) if box[1] < v < box[3])})
    return all(any(r[0] <= (x+xx)/2 <= r[2] and r[1] <= (y+yy)/2 <= r[3] for r in regions)
               for x, xx in zip(xs, xs[1:]) for y, yy in zip(ys, ys[1:]))


class TrafficMotionGate(MovementGate):
    """Same lock fences protocol, local application, command checks and revoke.

    APPLIED here means an immutable offline binding only, never physical qualification.
    Identity-less Twist cannot prove its producer/context. Fixture producer identity and
    geometry evidence must eventually be replaced by a qualified local ROS adapter.
    No method can open nonzero output, including with otherwise complete evidence.
    """
    def __init__(self, *, clock, producer):
        super().__init__(clock=clock)
        if not isinstance(producer, str) or not producer:
            raise ValueError('Explicit expected producer required')
        self.producer = producer
        self.local_session = str(uuid4())
        self.binding = None
        self.session_blocked = False

    def prepare(self, request, timeout):
        with self.lock:
            if self.session_blocked:
                raise ValueError('Session change requires external reset, not reprepare')
            self.binding = None
            super().prepare(request, timeout)

    def apply_local(self, *, context, regions, geometry_digest):
        """Atomically freeze synthetic permit boundary/context and create local ACK."""
        with self.lock:
            if not self._live() or not self.decision or self.session_blocked:
                return None
            d = self.decision
            if (context != self._context() or geometry_digest != d['geometry_digest']
                    or not regions or not all(_box(r) for r in regions)
                    or boundary_digest(regions) != geometry_digest):
                self.revoke('LOCAL_BINDING_MISMATCH')
                return None
            candidate = dict(context=deepcopy(context), regions=tuple(tuple(r) for r in regions),
                             geometry_digest=geometry_digest)
            if self.binding:
                if candidate != self.binding:
                    self.revoke('LOCAL_BINDING_CHANGED')
                    return None
                return deepcopy(self.applied)
            ack = {k: deepcopy(d[k]) for k in ('identity', 'request_id', 'geometry_digest', 'movement_kind', 'station_id')}
            ack.update(kind='APPLIED', local_binding_id=self.local_session)
            if not super().applied_ack(ack):
                return None
            self.binding = candidate
            return deepcopy(ack)

    def applied_ack(self, ack):
        # Remote/self-reported ACK cannot stand in for this instance's application.
        return False

    def _context(self):
        if not self.decision:
            return None
        return {k: deepcopy(self.decision[k]) for k in ('identity', 'movement_kind', 'station_id')}

    def revoke(self, reason='REVOKED'):
        with self.lock:
            self.binding = None
            super().revoke(reason)

    def session_changed(self):
        with self.lock:
            self.session_blocked = True
            self.revoke('SESSION_CHANGED')

    def filter_velocity(self, velocity, *, producer, context=None, evidence=None):
        """Always return a zero six-axis Twist representation plus diagnostic reasons.

        Evidence is explicitly fake: receive/source freshness, TF measurement validity,
        ObservationHealth used measurements, and expanded footprint/reachable-stop tube.
        Caller assertions are not qualified physical sources. No owner mutation exists.
        """
        with self.lock:
            reasons = []
            if producer != self.producer:
                reasons.append('BYPASS_DETECTED')
                self.revoke('BYPASS_DETECTED')
            if (not isinstance(velocity, (tuple, list)) or len(velocity) != 6
                    or not all(type(v) in (int, float) and math.isfinite(v) for v in velocity)):
                reasons.append('INVALID_VELOCITY')
            if not self._live() or not self.decision:
                reasons.append('NO_LIVE_PERMIT')
            if not self.binding or self.applied is None:
                reasons.append('NO_LOCAL_APPLIED_ACK')
            if context is None or context != self._context():
                reasons.append('MOVEMENT_CONTEXT_MISMATCH')
                if self.decision:
                    self.revoke('MOVEMENT_CONTEXT_MISMATCH')
            if self.session_blocked:
                reasons.append('SESSION_CHANGED')
            if (not isinstance(context, dict) or context.get('movement_kind') not in
                    ('PICKUP', 'DROPOFF', 'PARK', 'CHARGE')):
                reasons.append('UNKNOWN_MOVEMENT_KIND')
            e = evidence if isinstance(evidence, dict) else {}
            now = self.clock()
            # All timestamps are fake local monotonic receipt/source-age projections.
            for source in ('pose', 'tf', 'observation', 'velocity', 'clock'):
                sample = e.get(source, {})
                if not isinstance(sample, dict):
                    sample = {}
                received, age, budget = (sample.get(k) for k in ('received', 'source_age', 'budget'))
                fresh = (all(type(v) in (int, float) and math.isfinite(v) for v in (received, age, budget))
                         and budget > 0 and 0 <= now-received < budget and 0 <= age+now-received < budget
                         and sample.get('valid') is True)
                if not fresh:
                    reasons.append('STALE_OR_UNKNOWN_' + source.upper())
            if e.get('tf_at_measurement') is not True or e.get('all_required_measurements_used') is not True:
                reasons.append('UNQUALIFIED_OBSERVATION')
            geometry_fresh = not any(r.startswith('STALE_OR_UNKNOWN_') or r == 'UNQUALIFIED_OBSERVATION'
                                     for r in reasons)
            if not geometry_fresh:
                reasons.append('BOUNDARY_OBSERVATION_UNKNOWN')
            if self.binding and geometry_fresh:
                regions = self.binding['regions']
                footprint, tube = e.get('footprint', ()), e.get('stop_tube', ())
                if not footprint or not all(_box(r) for r in footprint):
                    reasons.append('UNKNOWN_FOOTPRINT')
                elif any(not _covered(r, regions) for r in footprint):
                    reasons.append('ZONE_VIOLATION')
                if not tube or not all(_box(r) for r in tube):
                    reasons.append('UNKNOWN_STOP_TUBE')
                elif any(not _covered(r, regions) for r in tube):
                    reasons.append('PREDICTED_BOUNDARY_BREACH')
                if 'ZONE_VIOLATION' in reasons or 'PREDICTED_BOUNDARY_BREACH' in reasons:
                    self.revoke(reasons[-1])
            reasons += ['PHYSICAL_FAIL_SAFE_UNQUALIFIED', 'NONZERO_DISABLED']
            self.state = 'MOTION_DISABLED'
            return GateOutput((0.,) * 6, tuple(reasons))
