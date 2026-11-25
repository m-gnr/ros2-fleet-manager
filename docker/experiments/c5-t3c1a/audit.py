"""Offline cross-check of committed FM, verifier and writer evidence, not MAC reauthentication."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET


def read(path):
    if path.exists():return path.read_text()
    with gzip.open(str(path)+'.gz','rt') as stream:return stream.read()


def audit(root,matrix,*,expected=None,selected=None):
    expected=expected or {'worker-stop':'TIMEOUT','worker-kill':'TIMEOUT','ipc-loss':'TIMEOUT','duplicate':'REPLAY',
              'wrong-context':'CONTEXT','wrong-session':'SESSION','corrupt':'MALFORMED','delayed':'TIMEOUT'}
    selected=selected if selected is not None else [line.split('\t') for line in matrix.read_text().splitlines() if line]
    assert len(selected)==len(expected)
    reports=[]
    for run,domain,code in selected:
        assert code=='0';path=root/run;s=json.loads(read(path/'summary.json'));case=s['case'];rid=s['robot_id']
        assert case in expected and s['result']=='PASS_STATIONARY_SPLIT_ZERO_ONLY'
        assert s['movement_authorized'] is False and s['ownership_release'] is False and s['physical_stop']=='UNKNOWN'
        assert not any(json.loads(read(path/'shutdown.json')).values())
        shutdown=json.loads(read(path/'worker-shutdown.json'))
        assert all(v==0 or (case=='worker-kill' and k==rid and v==-9) for k,v in shutdown.items())
        before,first,during,after=(s[k] for k in ('before','first_latched','during','after'))
        assert before['selection_reason']=='VERIFIED_ZERO' and not before['latched']
        allowed=expected[case] if isinstance(expected[case],set) else {expected[case]}
        assert first['selection_reason'] in allowed
        assert all(v['latched'] and v['pre_selected_joint_targets']==[0.,0.] for v in (first,during,after))
        assert after['accepted']==first['accepted']
        assert during['post_completed_physics_updates']>first['post_completed_physics_updates']+20
        assert during['sim_ns']>before['sim_ns']
        if case=='worker-stop':assert 'State:\tT' in s['process_evidence']['worker_status_during']
        mappings=json.loads(read(path/'loaded-mappings.json'))
        gazebo=next(m for m in mappings if m['pid']==s['gazebo_pid'])
        assert all(any(name in line for line in gazebo['mappings']) for name in
            ('libc5-authorized-zero-drive.so','libc5-physics-observer.so','physics-system.so','dartsim-plugin.so'))
        assert s['worker_pid']!=s['gazebo_pid']
        manifest=json.loads(read(path/'workers.json'))
        assert all(v['auto_restart'] is False for v in manifest.values())
        world=ET.fromstring(read(path/'generated/warehouse.sdf')).find('world')
        physics=[p for p in world.findall('plugin') if 'Physics' in p.get('name','')]
        assert len(physics)==1 and physics[0].get('name')=='c5::test::PhysicsObserver'
        for robot in manifest:
            drivers=[p for p in world.find('model[@name="'+robot+'"]').findall('plugin') if 'DiffDrive' in p.get('name','')]
            assert len(drivers)==1 and drivers[0].get('name')=='c5::test::SplitZeroDiffDrive'
            assert drivers[0].find('authorization_file') is None
        if case=='worker-kill':
            assert manifest[rid]['restart_pid']!=manifest[rid]['pid']
            starts=[json.loads(line) for line in read(path/(rid+'-worker-audit.jsonl')).splitlines() if json.loads(line)['event']=='START']
            assert len(starts)==2 and starts[0]['receiver_session']!=starts[1]['receiver_session']
            assert after['native_session']==starts[0]['receiver_session']
        connection=sqlite3.connect('file:'+str(path/'fleet.sqlite3')+'?mode=ro',uri=True)
        assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        for decision,payload in connection.execute('SELECT d.decision,o.payload FROM traffic_decisions d JOIN traffic_outbox o ON o.event_id=d.event_id'):
            assert decision==payload
        assert {row[0] for row in connection.execute('SELECT DISTINCT state FROM traffic_outbox')}=={'PENDING'}
        binding=json.loads(read(path/'writer-committed-binding.json'));v=binding['selection'];n=binding['native_status'];t=binding['committed_transfer']
        body=json.loads(t['body']);context=body['command_context'];identity=t['identity']
        digest=lambda text:hashlib.sha256(text.encode()).hexdigest()
        assert t['command_sha256']==digest(t['body'])==v['command_sha256']==n['command_sha256']
        assert v['command_sequence']==n['sequence']==body['command_sequence']
        assert v['native_session']==n['receiver_session']==body['actuator_session']
        assert v['context_sha256']==n['context_sha256']
        for kind in ('permit','child'):
            assert digest(context[kind+'_decision'])==context[kind+'_decision_sha256']
            decision=json.loads(context[kind+'_decision']);assert decision['identity']==identity
            stored=connection.execute('SELECT payload FROM traffic_outbox WHERE event_id=?',(context[kind+'_event_id'],)).fetchone()[0]
            assert stored==context[kind+'_decision']
        actual=connection.execute("SELECT payload FROM outbox_events WHERE kind='EXECUTE_TASK' AND goal_uuid=?",(identity['execute_uuid'],)).fetchone()
        assert json.loads(actual[0])['assigned_robot_id']==rid
        assert identity['child_uuid']!=identity['execute_uuid']
        ack=s['committed_ack'];assert ack['identity']==identity and ack['status']=='NATIVE_ZERO_VERIFIED'
        ackrow=json.loads(connection.execute('SELECT decision FROM traffic_decisions WHERE event_id=?',('native-ack:'+ack['transfer_id'],)).fetchone()[0])
        assert ackrow==ack
        connection.close()
        verifier=[json.loads(line) for line in read(path/'native-verifier.jsonl').splitlines()]
        assert any(json.loads(row['native_status']['body'])==n for row in verifier)
        assert all(row['source_stage']=='NATIVE_VERIFIER_PROCESS' and 'native_health' not in row and 'joint_commands' not in row for row in verifier)
        samples=[json.loads(line) for line in read(path/'writer.jsonl').splitlines()]
        assert all(v['pre_selected_joint_targets']==[0.,0.] for v in samples)
        assert any(v['post_actual_velocity_known'] and v['post_completed_physics_updates']>=during['post_completed_physics_updates'] for v in samples)
        assert all(math.isfinite(z) for v in samples for z in v['post_actual_body_velocity'])
        assert json.loads(read(path/'release-response.json'))['reason']=='RELEASE_THRESHOLDS_UNVERIFIED'
        assert max(s['max_stationary_displacement_m'].values())<.001
        reports.append(dict(run=run,domain=int(domain),robot_id=rid,reason=first['selection_reason'],
            physics_before=before['post_completed_physics_updates'],physics_while_fault=during['post_completed_physics_updates'],
            writer_samples=s['writer_samples'],source_assignment_and_body_match=True,
            mac_reauthenticated_offline=False,mac_verified_by_live_probe=True))
    assert {json.loads(read(root/run/'summary.json'))['case'] for run,_,_ in selected}==set(expected)
    return dict(result='PASS_OFFLINE_CROSS_STAGE_AUDIT',cases=reports,movement_authorized=False,
        physical_stop='UNKNOWN',ownership_release=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('matrix',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args();args.output.write_text(json.dumps(audit(args.root,args.matrix),indent=2)+'\n');print('PASS 8 committed-FM/verifier/writer/Physics cases; zero-only, release denied')
