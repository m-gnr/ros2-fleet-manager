"""Offline linkage/observation audit. Private HMAC keys are not archived.

Live HealthWindow verified native health and nested native status MACs. This
audit rechecks their bytes, provenance and safe semantics, not the MAC key.
"""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def sha(text):return hashlib.sha256(text.encode()).hexdigest()


def audit(path):
    report=json.loads((path/'summary.json').read_text())
    assert report['result']=='PASS_REAL_FM_NATIVE_ZERO_ONLY'
    assert not report['movement_authorized'] and report['physical_stop']=='UNKNOWN' and not report['ownership_release']
    db=sqlite3.connect('file:'+str(path/'fleet.sqlite3')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    records={r['event_id']:r for r in db.execute('SELECT rowid,* FROM traffic_decisions')}
    outbox={r['event_id']:r for r in db.execute('SELECT * FROM traffic_outbox')}
    assert set(records)==set(outbox)
    assert all(r['decision']==outbox[e]['payload'] and outbox[e]['state']=='PENDING' for e,r in records.items())
    transfers={e:json.loads(r['decision']) for e,r in records.items() if e.startswith('native-transfer:')}
    acks=[json.loads(r['decision']) for e,r in records.items() if e.startswith('native-ack:')]
    assert transfers and acks
    for event_id,transfer in transfers.items():
        body=json.loads(transfer['body']);context=body['command_context'];identity=transfer['identity']
        assert body['velocity']==[0.]*6 and sha(transfer['body'])==transfer['command_sha256']
        for label in ('permit','child'):
            source=context[label+'_event_id'];raw=context[label+'_decision']
            assert raw==records[source]['decision']==outbox[source]['payload']
            assert sha(raw)==context[label+'_decision_sha256']
            assert json.loads(raw)['identity']==identity
            assert records[source]['rowid']<records[event_id]['rowid']
        child=json.loads(records[context['child_event_id']]['payload'])['payload']
        assert hashlib.sha256(bytes.fromhex(child['path_bytes'])).hexdigest()==identity['path_hash']
        assert len({identity['execute_uuid'],identity['child_uuid'],child['child_provenance']['nav_uuid']})==3
        row=db.execute('SELECT payload FROM outbox_events WHERE kind=? AND task_id=? AND assignment_epoch=? AND goal_uuid=?',
            ('EXECUTE_TASK',identity['task_id'],identity['epoch'],identity['execute_uuid'])).fetchone()
        assert row and json.loads(row[0])['assigned_robot_id']==identity['robot_id']
    for ack in acks:
        transfer=transfers[ack['transfer_id']]
        assert ack['identity']==transfer['identity'] and ack['native_status']['command_sha256']==sha(transfer['body'])
        assert records[transfer['transfer_id']]['rowid']<records['native-ack:'+transfer['transfer_id']]['rowid']
        assert not ack['movement_authorized'] and not ack['ownership_release'] and ack['physical_stop']=='UNKNOWN'
    native_packets={};counts=collections.Counter();matched=set()
    with gzip.open(path/'health-sources.jsonl.gz','rt') as stream:
        for line in stream:
            item=json.loads(line)
            if item['stream']!='native':continue
            packet=item['value'];health=json.loads(packet['native_health']['body']);status=json.loads(health['native_status']['body'])
            assert health['native_status']==packet['native_status']
            for field in ('sim_ns','target_linear','target_angular','joint_commands'):assert health[field]==packet[field]
            assert health['target_linear']==health['target_angular']==0.
            assert all(v==[0.] for v in health['joint_commands'])
            native_packets[item['robot'],status['receiver_session'],health['update_sequence']]=health
    reasons=collections.Counter();health_counts=collections.Counter();covariance_examples={};admitted_native=collections.Counter()
    with gzip.open(path/'health.jsonl.gz','rt') as stream:
        for line in stream:
            item=json.loads(line);rid=item['robot_id'];health_counts[rid]+=1;reasons.update(item['reasons'])
            assert item['movement_eligible'] is False and item['ownership_release'] is False and item['physical_stop']=='UNKNOWN'
            value=item['measured'].get('native')
            if value:
                health=native_packets[rid,value['status']['receiver_session'],value['update_sequence']]
                assert {k:v for k,v in value.items() if k!='status'}==health
                assert value['status']==json.loads(health['native_status']['body'])
                admitted_native[rid]+=1
                known=next((t for t in transfers.values() if t['command_sha256']==value['status']['command_sha256']),None)
                if value['status']['sequence']>0:
                    assert known is not None
                    body=json.loads(known['body']);status=value['status']
                    assert status['source_session']==body['source_session']
                    assert status['receiver_session']==body['actuator_session']
                    assert status['generation']==body['permit_generation'] and status['permit_id']==body['permit_id']
                    assert status['sequence']==body['command_sequence']
                    matched.add((rid,status['receiver_session'],value['update_sequence']))
            if any('PSD' in r for r in item['reasons']) and rid not in covariance_examples:
                a=item['measured'].get('amcl')
                if a:covariance_examples[rid]=a['covariance']
    assert len(health_counts)==3 and len(admitted_native)==3 and matched
    with gzip.open(path/'native.jsonl.gz','rt') as stream:
        for line in stream:
            s=json.loads(line);counts[s['robot']]+=1
            assert s['target_linear']==s['target_angular']==0. and all(v==[0.] for v in s['joint_commands'])
    assert dict(counts)==report['native_samples']
    assert not (path/'unsafe-contact').exists()
    assert json.loads((path/'release-response.json').read_text())['reason']=='RELEASE_THRESHOLDS_UNVERIFIED'
    evaluation=report['cases']['health_validation']
    assert evaluation['stop_envelope']['tube'] is None and not evaluation['stop_envelope']['qualified']
    assert evaluation['reservation_assessment']['status']=='UNKNOWN_STOP_TUBE'
    assert all(v['envelope']['tube'] is None and v['relative_to_assignee']['status']=='UNKNOWN_RELATIVE_OCCUPANCY'
               for v in evaluation['peer_stop_assessments'].values())
    fault=report['cases'].get('health_faults',{})
    for label,value in fault.items():
        if isinstance(value,dict) and 'during' in value:
            assert not value['during']['observations_current'] and not value['during']['movement_eligible']
            assert value['source_receipt_age_sec']>0
    shutdown=json.loads((path/'shutdown.json').read_text())
    expected={'manager_restart':1}
    if report['case']=='fm-loss':expected['manager']=-9
    if report['case']=='bridge-loss':expected['command_bridge']=-9
    if report['case']=='executor-loss':expected['executor_'+evaluation['actual_robot']]=-9
    assert all(value==expected.get(name,0) for name,value in shutdown.items()),shutdown
    assert json.loads((path/'transport-shutdown.json').read_text())=={'odometry_link':0,'tf_helper':0}
    db.close()
    return dict(result=report['result'],actual_assignee=evaluation['actual_robot'],native_samples=dict(counts),
        health_evaluations=dict(health_counts),admitted_native_observations=dict(admitted_native),
        distinct_committed_context_readbacks=len(matched),
        ack_stages=dict(collections.Counter(a['status'] for a in acks)),outbox_all_pending=True,
        finite_physical_stop_tube=False,independent_braking_guarantee=False,
        psd_rejection_examples=covariance_examples,top_health_reasons=reasons.most_common(10),
        mac_verification='Live verifier checked private key; offline audit checks packet bytes and linkage only')


if __name__=='__main__':
    root=Path(sys.argv[1]).resolve()
    names=['fm-loss-a5','bridge-loss-a3','replan-a5','negative-a1','update-freeze-a3',
           'sensor-loss-a3','controller-inactive-a2','executor-loss-a2']
    print(json.dumps({name:audit(root/name) for name in names},indent=2))
