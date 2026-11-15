"""Conservative reservation-only geometry. Never authorizes actuator movement."""
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json
import math
from uuid import UUID


class ClaimKind(str, Enum):
    STATIC_ZONE = 'STATIC_ZONE'
    DYNAMIC_SWEEP = 'DYNAMIC_SWEEP'
    PHYSICAL_OCCUPANCY = 'PHYSICAL_OCCUPANCY'
    STOP_HOLD = 'STOP_HOLD'


@dataclass(frozen=True)
class Box:
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self):
        if not all(math.isfinite(v) for v in asdict(self).values()) or self.x0 >= self.x1 or self.y0 >= self.y1:
            raise ValueError('Finite positive-area bounds required')

    def intersects(self, other):
        return self.x0 <= other.x1 and other.x0 <= self.x1 and self.y0 <= other.y1 and other.y0 <= self.y1


def sweep(points, enclosing_radius):
    """Segment AABBs enclose the full circumscribed footprint at every yaw.

    Radius is supplied geometry, not a calibrated safety margin. This intentionally
    over-reserves diagonal paths and rotations; no sampled-waypoint gap exists.
    """
    if not points or not math.isfinite(enclosing_radius) or enclosing_radius <= 0:
        raise ValueError('Explicit enclosing radius and path required')
    if any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in points):
        raise ValueError('Finite planar path required')
    pairs = list(zip(points, points[1:])) or [(points[0], points[0])]
    r = enclosing_radius
    return tuple(Box(min(a[0], b[0])-r, min(a[1], b[1])-r,
                     max(a[0], b[0])+r, max(a[1], b[1])+r) for a, b in pairs)


def covered(box, managed):
    """Exact rectangle-union containment using a boundary grid."""
    xs = sorted({box.x0, box.x1, *(v for b in managed for v in (b.x0, b.x1) if box.x0 < v < box.x1)})
    ys = sorted({box.y0, box.y1, *(v for b in managed for v in (b.y0, b.y1) if box.y0 < v < box.y1)})
    return all(any(b.x0 <= (x+xx)/2 <= b.x1 and b.y0 <= (y+yy)/2 <= b.y1 for b in managed)
               for x, xx in zip(xs, xs[1:]) for y, yy in zip(ys, ys[1:]))


@dataclass(frozen=True)
class PermitIdentity:
    robot_id: str
    task_id: str
    epoch: int
    execute_uuid: str
    child_uuid: str
    executor_session: str
    fm_session: str
    permit_id: str
    generation: int
    path_hash: str
    map_revision: str
    frame: str
    geometry_revision: str

    def __post_init__(self):
        if any(not isinstance(v, str) or not v for k, v in asdict(self).items() if k not in ('epoch', 'generation')):
            raise ValueError('Nonempty identity fields required')
        if type(self.epoch) is not int or self.epoch < 1 or type(self.generation) is not int or self.generation < 1:
            raise ValueError('Positive epoch/generation required')
        for value in (self.execute_uuid, self.child_uuid, self.executor_session, self.fm_session, self.permit_id):
            if UUID(value).int == 0:
                raise ValueError('Nonzero UUID required')


@dataclass(frozen=True)
class TrafficAreaClaim:
    claim_id: str
    kind: ClaimKind
    identity: PermitIdentity
    geometry: tuple[Box, ...]
    claim_generation: int
    occupancy_evidence: dict | None = None
    blocked_reason: str | None = None

    def __post_init__(self):
        ClaimKind(self.kind)
        if not self.claim_id or not self.geometry or any(not isinstance(b, Box) for b in self.geometry):
            raise ValueError('Claim ID and bounded geometry required')
        if type(self.claim_generation) is not int or self.claim_generation < 1:
            raise ValueError('Positive claim generation required')


@dataclass(frozen=True)
class ReleaseEvidence:
    identity: PermitIdentity
    claim_ids: tuple[str, ...]
    child_terminal: str | None = None
    local_retire_ack: str | None = None
    pose_samples: tuple[dict, ...] = ()
    velocity_stamp: int | None = None
    tf_stamp: int | None = None
    footprint_outside: bool = False


class TrafficCore:
    def __init__(self, revision, frame, geometry_revision, managed, state=None):
        self.revision, self.frame, self.geometry_revision = revision, frame, geometry_revision
        self.managed = tuple(managed)
        self.state = state or {'claims': {}, 'contexts': {}, 'requests': {}, 'blocked_robots': [], 'global_block': False}

    def bind(self, identity):
        """Trusted consumer binding; never replaces an existing active context."""
        data = asdict(identity)
        old = self.state['contexts'].get(identity.robot_id)
        if old is not None and old != data:
            return self.decision('DENIED', 'CONTEXT_ALREADY_BOUND')
        if (identity.map_revision, identity.frame, identity.geometry_revision) != (self.revision, self.frame, self.geometry_revision):
            return self.decision('DENIED', 'REVISION_MISMATCH')
        self.state['contexts'][identity.robot_id] = data
        return self.decision('BOUND', '')

    @staticmethod
    def decision(status, reason):
        return {'status': status, 'reason': reason, 'movement_authorized': False}

    def acquire(self, request_id, claims):
        if not request_id or not claims:
            return self.decision('DENIED', 'EMPTY_REQUEST')
        raw = [asdict(c) for c in claims]
        fingerprint = hashlib.sha256(json.dumps(raw, sort_keys=True, allow_nan=False).encode()).hexdigest()
        previous = self.state['requests'].get(request_id)
        if previous:
            return previous['decision'] if previous['hash'] == fingerprint else self.decision('DENIED', 'REQUEST_PAYLOAD_CHANGED')
        reason = self._check(claims)
        result = self.decision('DENIED' if reason else 'RESERVED', reason)
        if not reason:
            for claim, data in zip(claims, raw):
                self.state['claims'][claim.claim_id] = {'claim': data, 'state': 'RESERVED', 'blocked_reason': None,
                                                      'observed_occupants': {}}
        self.state['requests'][request_id] = {'hash': fingerprint, 'decision': result}
        return result

    def _check(self, claims):
        identity = asdict(claims[0].identity)
        if self.state['global_block']:
            return 'PHYSICAL_UNCERTAINTY'
        if len({c.claim_id for c in claims}) != len(claims):
            return 'DUPLICATE_CLAIM_ID'
        for c in claims:
            if asdict(c.identity) != identity or self.state['contexts'].get(c.identity.robot_id) != identity:
                return 'IDENTITY_FENCE'
            if c.identity.robot_id in self.state['blocked_robots']:
                return 'ROBOT_BLOCKED'
            if (c.identity.map_revision, c.identity.frame, c.identity.geometry_revision) != (self.revision, self.frame, self.geometry_revision):
                return 'REVISION_MISMATCH'
            if c.claim_generation != c.identity.generation:
                return 'CLAIM_GENERATION_FENCE'
            if c.claim_id in self.state['claims'] or c.blocked_reason:
                return 'CLAIM_FENCE'
            if c.kind in (ClaimKind.PHYSICAL_OCCUPANCY, ClaimKind.STOP_HOLD):
                return 'PHYSICAL_EVIDENCE_REQUIRES_OBSERVATION'
            if not all(covered(b, self.managed) for b in c.geometry):
                return 'UNMANAGED'
            for entry in self.state['claims'].values():
                other = entry['claim']
                if other['identity']['robot_id'] != c.identity.robot_id and any(
                        b.intersects(Box(**o)) for b in c.geometry for o in other['geometry']):
                    return 'GEOMETRIC_CONFLICT'
        return ''

    def block(self, robot_id, reason):
        if robot_id not in self.state['blocked_robots']:
            self.state['blocked_robots'].append(robot_id)
        for entry in self.state['claims'].values():
            if entry['claim']['identity']['robot_id'] == robot_id or robot_id in entry['observed_occupants']:
                entry['state'], entry['blocked_reason'] = 'BLOCKED', reason
        return self.decision('BLOCKED', reason)

    def observe(self, claim):
        """Unqualified physical evidence only increases restrictions, never frees."""
        if claim.kind not in (ClaimKind.PHYSICAL_OCCUPANCY, ClaimKind.STOP_HOLD):
            raise ValueError('Physical observation required')
        conflict = []
        for entry in self.state['claims'].values():
            if any(b.intersects(Box(**o)) for b in claim.geometry for o in entry['claim']['geometry']):
                entry['observed_occupants'][claim.identity.robot_id] = claim.occupancy_evidence
                if entry['claim']['identity']['robot_id'] != claim.identity.robot_id:
                    conflict.append(entry)
        context = self.state['contexts'].get(claim.identity.robot_id)
        authorized = context == asdict(claim.identity) and all(any(
            entry['state'] == 'RESERVED' and entry['claim']['identity'] == context and
            covered(b, tuple(Box(**v) for v in entry['claim']['geometry']))
            for entry in self.state['claims'].values()) for b in claim.geometry)
        violation = bool(conflict) or not authorized or not all(covered(b, self.managed) for b in claim.geometry)
        # Do not overwrite a reservation or an earlier physical footprint.
        key = 'observation:' + claim.claim_id
        while key in self.state['claims']:
            key += ':'
        self.state['claims'][key] = {'claim': asdict(claim), 'state': 'BLOCKED',
            'blocked_reason': 'UNQUALIFIED_PHYSICAL_EVIDENCE',
            'observed_occupants': {claim.identity.robot_id: claim.occupancy_evidence}}
        # Uncalibrated evidence cannot bound future occupancy: close all new grants.
        self.state['global_block'] = True
        for entry in conflict:
            entry['state'], entry['blocked_reason'] = 'BLOCKED', 'ZONE_VIOLATION'
        self.block(claim.identity.robot_id, 'ZONE_VIOLATION' if violation else 'UNQUALIFIED_PHYSICAL_EVIDENCE')
        return self.decision('ZONE_VIOLATION' if violation else 'BLOCKED', 'PHYSICAL_REVIEW_REQUIRED')

    def release(self, evidence):
        # No calibrated release qualification exists in B6B.1. Never infer FREE.
        for cid in evidence.claim_ids:
            entry = self.state['claims'].get(cid)
            if entry is None or entry['claim']['identity'] != asdict(evidence.identity):
                return self.decision('DENIED', 'RELEASE_IDENTITY_FENCE')
        return self.decision('DENIED', 'RELEASE_THRESHOLDS_UNVERIFIED')
