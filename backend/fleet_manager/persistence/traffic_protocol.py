"""Test-only protocol; all calls run inside the existing consumer transaction."""
from dataclasses import asdict
import hashlib
import json
from uuid import UUID, uuid5

from .store import encode
from .traffic import process_traffic
from ..domain.traffic import Box, ClaimKind, PermitIdentity, TrafficAreaClaim, TrafficCore, sweep
from ..domain.constants import RobotState, StationType


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def context_reason(core, p, now):
    robot = core.tracker.get_robot(p['robot_id'])
    if (robot is None or not robot.initial_status_verified or robot.session_blocked
            or robot.is_stale(now) or robot.state == RobotState.STATE_ERROR
            or robot.session_id != p['executor_session']):
        return 'SESSION_OR_STATUS_FENCE'
    kind = p['movement_kind']
    if kind in ('PICKUP', 'DROPOFF'):
        owner = core._active_tasks_by_robot.get(p['robot_id'])
        if p['station_id']:
            return 'STATION_FENCE'
    else:
        owner = core.station_dispatch.active.get(p['robot_id']) if core.station_dispatch else None
        if owner is None or owner.station_id != p['station_id']:
            return 'STATION_FENCE'
        expected = 'CHARGE' if owner.station_type == StationType.CHARGING else 'PARK'
        if kind != expected or owner.session_id != robot.session_id:
            return 'STATION_FENCE'
    if (owner is None or owner.task_id != p['task_id'] or owner.assignment_epoch != p['epoch']
            or owner.goal_uuid != p['execute_uuid'] or owner.assigned_robot_id != p['robot_id']):
        return 'ASSIGNMENT_FENCE'
    return ''


def process_protocol(store, event, core, now, session, radius):
    """Request identity fields select records; they never create assignment authority."""
    from ..event_loop import Event
    db, p = store.connection, event.payload
    if not db.in_transaction:
        raise RuntimeError('Consumer transaction required')
    if event.kind == 'TRAFFIC_PROTOCOL_UPDATES':
        if session is None:
            return []
        row = db.execute('SELECT snapshot FROM traffic_state WHERE singleton=1').fetchone()
        snapshot = json.loads(row[0]) if row else None
        updates = []
        for record in db.execute("SELECT d.payload,o.payload FROM traffic_decisions d "
                                 "JOIN traffic_outbox o ON o.event_id=d.event_id WHERE d.event_id LIKE 'permit:%'"):
            source, decision = json.loads(record[0]), json.loads(record[1])
            if source['kind'] != 'TRAFFIC_PROTOCOL_REQUEST' or decision.get('status') != 'RESERVED':
                continue
            reason = context_reason(core, source['payload'], now)
            reserved = snapshot and any(v['claim']['identity'] == decision['identity'] and v['state'] == 'RESERVED'
                                       for v in snapshot['state']['claims'].values())
            updates.append({**decision, 'status': 'REVOKED' if reason or not reserved else 'RESERVED',
                            'reason': reason or ('PERMIT_REVOKED' if not reserved else '')})
        return updates
    raw = encode({'kind': event.kind, 'payload': p})
    previous = db.execute('SELECT * FROM traffic_decisions WHERE event_id=?', (event.event_id,)).fetchone()
    if previous and previous['payload'] != raw:
        return TrafficCore.decision('DENIED', 'EVENT_PAYLOAD_CHANGED')
    result = TrafficCore.decision('DENIED', 'TEST_MODE_DISABLED')
    if session is not None:
        row = db.execute('SELECT snapshot FROM traffic_state WHERE singleton=1').fetchone()
        snapshot = json.loads(row[0]) if row else None
        if event.kind == 'TRAFFIC_PROTOCOL_REQUEST':
            reason = context_reason(core, p, now)
            if previous:
                result = json.loads(previous['decision'])
                identity = result.get('identity')
                if identity and snapshot:
                    claims = snapshot['state']['claims'].values()
                    if not any(v['claim']['identity'] == identity and v['state'] == 'RESERVED' for v in claims):
                        reason = reason or 'PERMIT_REVOKED'
                if reason:
                    result = {**result, 'status': 'DENIED', 'reason': reason, 'movement_authorized': False}
                return result
            if not snapshot:
                reason = reason or 'UNCONFIGURED'
            for k in ('request_id', 'execute_uuid', 'child_uuid', 'executor_session'):
                if UUID(p[k]).int == 0:
                    raise ValueError('Nonzero protocol UUID required')
            if event.event_id != 'permit:' + p['request_id']:
                raise ValueError('Stable request event ID required')
            if not reason and (p['map_revision'], p['frame'], p['geometry_revision']) != (
                    snapshot['revision'], snapshot['frame'], snapshot['geometry_revision']):
                reason = 'REVISION_MISMATCH'
            geometry = tuple(sweep(tuple(tuple(v) for v in p['points']), radius))
            boxes = [asdict(b) for b in geometry]
            if (p['geometry'] != boxes or p['geometry_digest'] != digest(boxes)
                    or hashlib.sha256(bytes.fromhex(p['path_bytes'])).hexdigest() != p['path_hash']):
                reason = reason or 'DIGEST_MISMATCH'
            # Generation and permit ID belong to the manager, not the ROS caller.
            generation = 1 + sum(1 for v in db.execute('SELECT event_id FROM traffic_decisions')
                                 if v[0].startswith('permit:'))
            i = PermitIdentity(p['robot_id'], p['task_id'], p['epoch'], p['execute_uuid'], p['child_uuid'],
                               p['executor_session'], session, str(uuid5(UUID(session), p['request_id'])),
                               generation, p['path_hash'], p['map_revision'], p['frame'], p['geometry_revision'])
            result = {**TrafficCore.decision('DENIED', reason), 'identity': asdict(i),
                      'request_id': p['request_id'], 'movement_kind': p['movement_kind'],
                      'station_id': p['station_id'], 'geometry_digest': p['geometry_digest']}
            if not reason:
                bound = process_traffic(store, Event('TRAFFIC_BIND', {'identity': asdict(i)}, event.event_id + ':bind'))
                if bound['status'] == 'BOUND':
                    claim = TrafficAreaClaim(i.permit_id, ClaimKind.DYNAMIC_SWEEP, i, geometry, i.generation)
                    acquired = process_traffic(store, Event('TRAFFIC_ACQUIRE',
                        {'request_id': p['request_id'], 'claims': [asdict(claim)]}, event.event_id + ':acquire'))
                    result.update(acquired)
                else:
                    result.update(bound)
        elif event.kind == 'TRAFFIC_PROTOCOL_ACK':
            identity = p['identity']
            original = db.execute('SELECT decision FROM traffic_decisions WHERE event_id=?',
                                  ('permit:' + p['request_id'],)).fetchone()
            original = json.loads(original[0]) if original else {}
            valid = (original.get('identity') == identity and
                     all(original.get(k) == p[k] for k in ('movement_kind', 'station_id', 'geometry_digest')))
            reason = context_reason(core, {**identity, 'movement_kind': p['movement_kind'], 'station_id': p['station_id']}, now)
            if p['kind'] not in ('APPLIED', 'RETIRED') or UUID(p['local_binding_id']).int == 0:
                valid = False
            result = {**TrafficCore.decision('RECORDED' if valid and not reason else 'DENIED',
                        'UNQUALIFIED_LOCAL_ACK' if valid and not reason else reason or 'ACK_IDENTITY_FENCE'),
                      **{k: p[k] for k in ('identity', 'request_id', 'movement_kind', 'station_id', 'geometry_digest')}}
            if valid and p['kind'] == 'RETIRED':
                process_traffic(store, Event('TRAFFIC_BLOCK', {'robot_id': identity['robot_id'],
                    'reason': 'LOCAL_RETIRED_UNQUALIFIED'}, event.event_id + ':retire'))
            if previous:
                return json.loads(previous['decision'])
        else:
            raise ValueError('Unknown protocol event')
    # This result can leave the consumer only after the outer COMMIT succeeds.
    if not previous:
        db.execute('INSERT INTO traffic_decisions VALUES (?,?,?)', (event.event_id, raw, encode(result)))
        db.execute('INSERT INTO traffic_outbox(event_id,payload) VALUES (?,?)', (event.event_id, encode(result)))
    return result
