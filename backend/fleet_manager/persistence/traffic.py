"""Traffic snapshot and decision outbox, called only inside consumer transaction."""
from dataclasses import asdict
import json
from ..domain.traffic import (Box, ClaimKind, PermitIdentity, TrafficAreaClaim,
                              TrafficCore, ReleaseEvidence)
from .store import encode


def claim_from(data):
    return TrafficAreaClaim(data['claim_id'], ClaimKind(data['kind']), PermitIdentity(**data['identity']),
                            tuple(Box(**b) for b in data['geometry']), data['claim_generation'],
                            data.get('occupancy_evidence'), data.get('blocked_reason'))


def process_traffic(store, event):
    db = store.connection
    if not db.in_transaction:
        raise RuntimeError('Traffic requires consumer transaction')
    payload = encode({'kind': event.kind, 'payload': event.payload})
    previous = db.execute('SELECT * FROM traffic_decisions WHERE event_id=?', (event.event_id,)).fetchone()
    if previous:
        if previous['payload'] != payload:
            return TrafficCore.decision('DENIED', 'EVENT_PAYLOAD_CHANGED')
        return json.loads(previous['decision'])
    row = db.execute('SELECT snapshot FROM traffic_state WHERE singleton=1').fetchone()
    snapshot = json.loads(row[0]) if row else None
    p = event.payload
    if event.kind == 'TRAFFIC_CONFIGURE':
        if snapshot is not None:
            result = TrafficCore.decision('DENIED', 'ALREADY_CONFIGURED')
        else:
            managed = tuple(Box(**v) for v in p['managed'])
            if not managed or not all(isinstance(p[k], str) and p[k] for k in ('revision', 'frame', 'geometry_revision')):
                raise ValueError('Explicit managed coverage/revisions required')
            core = TrafficCore(p['revision'], p['frame'], p['geometry_revision'], managed)
            snapshot = dict(revision=p['revision'], frame=p['frame'], geometry_revision=p['geometry_revision'],
                            managed=[asdict(b) for b in managed], state=core.state)
            result = core.decision('CONFIGURED', '')
    elif snapshot is None:
        result = TrafficCore.decision('DENIED', 'UNCONFIGURED')
    else:
        core = TrafficCore(snapshot['revision'], snapshot['frame'], snapshot['geometry_revision'],
                           tuple(Box(**b) for b in snapshot['managed']), snapshot['state'])
        if event.kind == 'TRAFFIC_BIND':
            result = core.bind(PermitIdentity(**p['identity']))
        elif event.kind == 'TRAFFIC_ACQUIRE':
            result = core.acquire(p['request_id'], tuple(claim_from(c) for c in p['claims']))
        elif event.kind == 'TRAFFIC_BLOCK':
            result = core.block(p['robot_id'], p['reason'])
        elif event.kind == 'TRAFFIC_OBSERVE':
            result = core.observe(claim_from(p['claim']))
        elif event.kind == 'TRAFFIC_RELEASE':
            values = dict(p['evidence'])
            values['identity'] = PermitIdentity(**values['identity'])
            result = core.release(ReleaseEvidence(**values))
        else:
            result = core.decision('DENIED', 'UNKNOWN_TRAFFIC_EVENT')
    if snapshot is not None:
        db.execute('INSERT INTO traffic_state VALUES (1,?) ON CONFLICT(singleton) DO UPDATE SET snapshot=excluded.snapshot', (encode(snapshot),))
    db.execute('INSERT INTO traffic_decisions VALUES (?,?,?)', (event.event_id, payload, encode(result)))
    db.execute('INSERT INTO traffic_outbox(event_id,payload) VALUES (?,?)', (event.event_id, encode(result)))
    return result
