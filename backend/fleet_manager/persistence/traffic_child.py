"""Actual-child metadata in the B6B consumer transaction and existing traffic Outbox."""
from .store import encode
from .traffic import process_traffic
from .traffic_protocol import context_reason, process_protocol
from ..domain.traffic import TrafficCore
from uuid import UUID
import json
import hashlib


def process_child(store, event, core, now, session, radius):
    from ..event_loop import Event
    db, p = store.connection, event.payload
    if not db.in_transaction:
        raise RuntimeError('Consumer transaction required')
    evidence = p['child_provenance']
    denied = lambda reason: TrafficCore.decision('DENIED', reason)
    if session is None:
        return denied('TEST_MODE_DISABLED')
    reason = context_reason(core, p, now)
    if reason:
        return denied(reason)
    if hashlib.sha256(bytes.fromhex(p['path_bytes'])).hexdigest() != p['path_hash']:
        return denied('DIGEST_MISMATCH')
    for key in ('context_id', 'nav_uuid', 'observer_session'):
        if UUID(evidence[key]).int == 0:
            return denied('CHILD_PROVENANCE_FENCE')
    if (evidence['nav_uuid'] in (p['execute_uuid'], p['child_uuid'])
            or p['child_uuid'] == p['execute_uuid']
            or type(evidence['sequence']) is not int or evidence['sequence'] <= 0
            or evidence['kind'] not in (1, 2, 3)
            or (evidence['kind'] == 3 and evidence['terminal_status'] not in (4, 5, 6))):
        return denied('CHILD_PROVENANCE_FENCE')
    expected_id = 'child:' + evidence['context_id'] + ':' + str(evidence['sequence'])
    if event.event_id != expected_id:
        raise ValueError('Stable child event ID required')
    rows = db.execute("SELECT payload,decision FROM traffic_decisions WHERE event_id LIKE 'child:%'").fetchall()
    history = [(json.loads(r[0])['payload'], json.loads(r[1])) for r in rows
               if json.loads(r[0])['kind'] == 'TRAFFIC_PROTOCOL_CHILD']
    matching = [(old, result) for old, result in history
                if old['child_provenance']['context_id'] == evidence['context_id']]
    if matching:
        old, result = max(matching, key=lambda row: row[0]['child_provenance']['sequence'])
        previous = old['child_provenance']
        if any(old[k] != p[k] for k in ('robot_id', 'task_id', 'epoch', 'execute_uuid', 'executor_session',
                                        'child_uuid', 'path_hash', 'request_id', 'geometry_digest')):
            return denied('CHILD_BINDING_IDENTITY_FENCE')
        if any(previous[k] != evidence[k] for k in ('nav_uuid', 'observer_session')):
            return denied('CHILD_OBSERVER_SESSION_FENCE')
        if evidence['sequence'] <= previous['sequence']:
            return denied('CHILD_OBSERVATION_REPLAY')
        if previous['kind'] != 1 or result.get('status') != 'RESERVED':
            return denied('CHILD_CONTEXT_CLOSED')
        if evidence['kind'] == 1 or evidence['sequence'] != previous['sequence'] + 1:
            return denied('CHILD_REPLACEMENT_REQUIRES_RELEASE')
    elif evidence['kind'] == 1 and evidence['sequence'] != 1:
        return denied('CHILD_SEQUENCE_GAP')
    # Invalidations are allowed to arrive before acceptance: persist a tombstone.
    # A delayed initial request cannot revive that binding or release its claims.
    if evidence['kind'] == 1:
        result = process_protocol(store, Event('TRAFFIC_PROTOCOL_REQUEST', p, 'permit:' + p['request_id']),
                                  core, now, session, radius)
    else:
        process_traffic(store, Event('TRAFFIC_BLOCK', {'robot_id': p['robot_id'],
            'reason': 'CHILD_INVALIDATED_UNQUALIFIED'}, event.event_id + ':block'))
        result = TrafficCore.decision('RECORDED', 'CHILD_CLOSED_OWNERSHIP_RETAINED')
    result = {**result, 'child_provenance': evidence, 'physical_stop': 'UNKNOWN', 'ownership_release': False}
    db.execute('INSERT INTO traffic_decisions VALUES (?,?,?)',
               (event.event_id, encode({'kind': event.kind, 'payload': p}), encode(result)))
    db.execute('INSERT INTO traffic_outbox(event_id,payload) VALUES (?,?)', (event.event_id, encode(result)))
    return result
