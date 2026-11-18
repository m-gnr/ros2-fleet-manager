"""Offline consistency audit of raw T3A evidence; no keys or motion authority.

MAC verification was performed inside each live runner with the private test
key before removal of the container. This audit checks bytes and linkages;
it does not independently reauthenticate without that key.
"""
import collections
import gzip
import hashlib
import json
import pathlib
import sqlite3
import sys


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def audit(path):
    summary = json.loads((path / 'summary.json').read_text())
    db = sqlite3.connect('file:' + str(path / 'fleet.sqlite3') + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    records = {r['event_id']: r for r in db.execute('SELECT rowid,* FROM traffic_decisions')}
    outbox = {r['event_id']: r for r in db.execute('SELECT * FROM traffic_outbox')}
    assert set(records) == set(outbox)
    assert all(r['decision'] == outbox[e]['payload'] and outbox[e]['state'] == 'PENDING'
               for e, r in records.items())
    transfers = {e: json.loads(r['decision']) for e, r in records.items() if e.startswith('native-transfer:')}
    acks = [json.loads(r['decision']) for e, r in records.items() if e.startswith('native-ack:')]
    assigned = set()
    for event_id, transfer in transfers.items():
        body = json.loads(transfer['body'])
        context, identity = body['command_context'], transfer['identity']
        assert body['velocity'] == [0.] * 6
        assert sha(transfer['body']) == transfer['command_sha256']
        for label in ('permit', 'child'):
            raw = context[label + '_decision']
            source = context[label + '_event_id']
            assert raw == records[source]['decision'] == outbox[source]['payload']
            assert sha(raw) == context[label + '_decision_sha256']
            assert json.loads(raw)['identity'] == identity
            assert records[source]['rowid'] < records[event_id]['rowid']
        child = json.loads(records[context['child_event_id']]['payload'])['payload']
        assert hashlib.sha256(bytes.fromhex(child['path_bytes'])).hexdigest() == identity['path_hash']
        assert len({identity['execute_uuid'], identity['child_uuid'], child['child_provenance']['nav_uuid']}) == 3
        assignment = db.execute('SELECT * FROM outbox_events WHERE kind=? AND task_id=? AND assignment_epoch=? AND goal_uuid=?',
                                ('EXECUTE_TASK', identity['task_id'], identity['epoch'], identity['execute_uuid'])).fetchone()
        assert assignment and json.loads(assignment['payload'])['assigned_robot_id'] == identity['robot_id']
        initial = json.loads((path / (identity['robot_id'] + '-initial-session.json')).read_text())
        assert initial['executor_session'] == identity['executor_session']
        assigned.add(identity['robot_id'])
    for ack in acks:
        transfer = transfers[ack['transfer_id']]
        body = json.loads(transfer['body'])
        assert ack['identity'] == transfer['identity']
        assert records[transfer['transfer_id']]['rowid'] < records['native-ack:' + transfer['transfer_id']]['rowid']
        status = ack['native_status']
        assert status['command_sha256'] == sha(transfer['body'])
        assert status['context_sha256'] == sha(compact({**body['command_context'], 'operation': 'INSTALL_ZERO'}))
        assert status['receiver_session'] == body['actuator_session']
        assert status['source_session'] == body['source_session']
        assert status['generation'] == body['permit_generation']
        assert status['permit_id'] == body['permit_id']
        assert status['sequence'] == body['command_sequence']
        payload = json.loads(records['native-ack:' + transfer['transfer_id']]['payload'])['payload']
        assert json.loads(payload['native_status']['body']) == status
        assert ack['native_verified'] and not ack['movement_authorized'] and not ack['ownership_release']
        assert ack['physical_stop'] == ack['receiver_live_now'] == 'UNKNOWN'
    counts = collections.Counter()
    with gzip.open(path / 'native.jsonl.gz', 'rt') as stream:
        for line in stream:
            state = json.loads(line)
            counts[state['robot']] += 1
            assert state['target_linear'] == state['target_angular'] == 0
            assert all(joint is None or joint == [0.] for joint in state['joint_commands'])
            assert not state['movement_authorized'] and not state['ownership_release']
    assert dict(counts) == summary['native_samples'] and len(counts) == 3 and min(counts.values()) > 0
    assert not (path / 'unsafe-contact').exists()
    if summary['case'] != 'startup-missing':
        assert transfers and acks and (path / 'traffic-start-proof.json').exists()
        proof = json.loads((path / 'traffic-start-proof.json').read_text())
        assert len(proof['robots']) == 3
        for robot in proof['robots']:
            assert robot['initial_status_verified'] and not robot['session_blocked']
            assert 0 <= proof['receipt_monotonic'] - robot['status_received_at'] < 2.
        assert json.loads((path / 'release-response.json').read_text())['reason'] == 'RELEASE_THRESHOLDS_UNVERIFIED'
    else:
        assert not transfers and not acks and not list(db.execute('SELECT * FROM traffic_state'))
    db.close()
    return dict(result=summary['result'], actual_assignees=sorted(assigned), transfers=len(transfers),
                ack_stages=dict(collections.Counter(a['status'] for a in acks)), native_samples=dict(counts),
                source_outbox_bytes_match=True, outbox_all_pending=True, path_bytes_hash_match=True,
                zero_targets=True, startup_proof_checked=True,
                mac_verification='Live runner checked with private key; offline audit is byte/linkage only')


if __name__ == '__main__':
    root = pathlib.Path(sys.argv[1]).resolve()
    names = ['negative-a2', 'executor-loss-a1', 'bridge-loss-a2', 'fm-loss-a1',
             'startup-missing-a1', 'startup-delayed-a1', 'replan-a2']
    print(json.dumps({name: audit(root / name) for name in names}, indent=2))
