"""Reuse 1A cross-stage audit; add actual health/IPC binding, never APPLIED."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('split_audit',ROOT/'docker/experiments/c5-t3c1a/audit.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


def audit(root,matrix,*,completed_only=False):
    expected={k:{'HEALTH_EXPIRED','HEALTH_REJECTED'} for k in
        ('tf-loss','odometry-loss','amcl-loss','observation-loss')}
    expected.update({k:{'HEALTH_REJECTED'} for k in ('health-context','health-session','health-old')})
    expected.update({k:{'TIMEOUT','HEALTH_EXPIRED','WORKER_CLOSED'} for k in ('worker-stop','worker-kill','ipc-loss')})
    expected.update({'health-flow-loss':{'HEALTH_EXPIRED'},'controller-inactive':{'HEALTH_REJECTED','NATIVE_CLOSED'},
        'replan':{'NATIVE_CLOSED','CONTEXT','HEALTH_REJECTED'},'cancel':{'NATIVE_CLOSED','HEALTH_REJECTED'}})
    rows=[line.split('\t') for line in matrix.read_text().splitlines()[1:] if line]
    assert len(rows)==len(expected) and {row[0] for row in rows}==set(expected)
    failed=[row for row in rows if row[-1]!='0']
    if completed_only:
        rows=[row for row in rows if row[-1]=='0'];expected={row[0]:expected[row[0]] for row in rows}
    report=base.audit(root,matrix,expected=expected,selected=[row[1:] for row in rows])
    digest=lambda value:hashlib.sha256(value.encode()).hexdigest()
    for entry,row in zip(report['cases'],rows):
        case,run,_,_=row;path=root/run;s=json.loads(base.read(path/'summary.json'))
        before=json.loads(base.read(path/'health-before.json'));v=before['writer'];packet=before['packet'];body=packet['body']
        assert body==json.loads(json.loads(packet['wire'])['body'])
        assert digest(json.loads(packet['wire'])['body'])==v['health']['health_digest']
        assert body['sequence']==v['health']['health_sequence'] and v['health']['health_seen']
        assert body['observations_current'] is True and not body['reasons'] and body['remaining_ns']>0
        assert body['movement_eligible'] is False and body['ownership_release'] is False and body['physical_stop']=='UNKNOWN'
        assert body['context_sha256']==v['context_sha256']==s['before']['context_sha256']
        assert body['receiver_session']==v['native_session'] and body['writer_boot']==v['writer_boot']
        identity=before['actual_task_identity'];assert identity==s['committed_ack']['identity']
        assert body['identity_sha256']==digest(json.dumps(identity,sort_keys=True,separators=(',',':')))
        assert all(p['source_identity']=='UNKNOWN' and p['remaining_ns']>=body['remaining_ns'] for p in body['sources'].values())
        assert before['health']['observations_current'] and not before['health']['movement_eligible']
        assert v['ipc_input']['accepted'] and all(v['ipc_input'][k]==v[k] for k in
            ('native_session','context_sha256','command_sha256','command_sequence'))
        samples=[json.loads(line) for line in base.read(path/'writer.jsonl').splitlines()]
        assert v in samples and v['robot_id']==identity['robot_id']
        assert s['first_latched']['writer_steady_ns']>=s['fault_started_observer_monotonic_ns']
        native=[json.loads(line) for line in base.read(path/'native-verifier.jsonl').splitlines()]
        signed=[json.loads(n['split_readback']['body']) for n in native if 'split_readback' in n]
        assert any(n['robot_id']==v['robot_id'] and n['writer']['health_digest']==v['health']['health_digest']
            and n['writer']['context_sha256']==v['context_sha256'] and n['writer']['writer_boot']==v['writer_boot'] for n in signed)
        validation=json.loads(base.read(path/'health-validation.json'))
        assert validation['after']['latched'] and validation['stop_envelope']['status']=='UNBOUNDED'
        assert validation['stop_envelope']['tube'] is None and validation['physical_stop']=='UNKNOWN'
        fault=json.loads(base.read(path/'health-fault.json')) if case not in ('worker-stop','worker-kill','ipc-loss') else {}
        stream={'tf-loss':'tf','odometry-loss':'odometry','amcl-loss':'amcl','observation-loss':'observation:local'}.get(case)
        if stream:assert 'STALE_OR_UNKNOWN:'+stream in fault['health_during']['reasons']
        if case=='controller-inactive':assert 'LIFECYCLE_NOT_ACTIVE:controller_server' in fault['health_during']['reasons']
        if case=='replan':assert any(a['status']=='NATIVE_ZERO_REVOKED' for a in fault['native_revoke_acks'])
        if case=='cancel':assert fault['cancel_return_code']==0 and fault['actual_execute_uuid']==identity['execute_uuid']
        entry.update(health_sequence=body['sequence'],health_digest=v['health']['health_digest'],
            health_to_actual_ipc_and_signed_readback=True,physical_applied=False,stop_envelope='UNBOUNDED')
    report['result']='INCOMPLETE_1B_ACCEPTANCE_COMPLETED_CASES_AUDITED' if failed else 'PASS_STATIONARY_HEALTH_VETO_CROSS_STAGE_AUDIT'
    report['acceptance_complete']=not failed;report['excluded_failed_runs']=failed
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('matrix',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--completed-only',action='store_true',help='Inspect completed runs while explicitly retaining incomplete acceptance')
    args=p.parse_args();result=audit(args.root,args.matrix,completed_only=args.completed_only)
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(result['result'])
