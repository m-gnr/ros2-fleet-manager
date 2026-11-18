"""FM persistence/Outbox component tests. Native states here are explicit unit fixtures."""
import asyncio
from copy import deepcopy
import json
from uuid import uuid4
import pytest

from fleet_config.native_zero import STATUS_DOMAIN, compact, sha, sign, verify, decisions
from fleet_robot_executor.traffic import MovementGate
from backend.fleet_manager.event_loop import Event
from backend.fleet_manager.adapters.native_zero import traffic_start_ready
from backend.fleet_manager.domain.constants import RobotState
from test_traffic_protocol import setup
from test_traffic_protocol import request as legacy_request
from test_traffic_product_child import prepared,consume,enrich,event as child_event

KEY=b'\xab'*32


def test_default_consumer_has_no_native_transport_authority(tmp_path):
    async def run():
        c,p=await setup(tmp_path)
        try:
            assert c._native_zero_profile is None
            result=await c.submit(exchange(p,{}))
            assert result['reason']=='NATIVE_TEST_MODE_DISABLED' and not result['movement_authorized']
            assert not c.store.connection.execute('SELECT 1 FROM traffic_native_receivers').fetchone()
            with pytest.raises(ValueError):c.enable_native_zero_test(keys={'r1':KEY},ack_timeout=.5)
        finally:await c.close();c.store.close()
    asyncio.run(run())


async def start(tmp_path):
    c,p=await setup(tmp_path,native_keys={'r1':KEY})
    b,o=prepared(p);p=enrich(consume(b,o,p),p)
    decision=await c.submit(child_event(p))
    state=dict(robot_id='r1',receiver_session='a'*64,ticket='b'*64,report_sequence=1,receiver_state='NO_COMMAND',
        source_session='',sequence=0,permit_id='',generation=0,context_sha256='',command_sha256='',operation='NONE',
        verified_steady_ns=0,steady_ns=100,movement_authorized=False,ownership_release=False)
    return c,p,b,decision,state


def exchange(p,s,key=KEY):
    return Event('TRAFFIC_PROTOCOL_NATIVE_EXCHANGE',dict(robot_id='r1',request_id=p['request_id'],
                                                       native_status=sign(compact(s),key,domain=STATUS_DOMAIN)))


def accepted(s,transfer):
    b=json.loads(transfer['body']);normalized={**b['command_context'],'operation':'INSTALL_ZERO'}
    return {**s,'report_sequence':s['report_sequence']+1,'ticket':'c'*64,'receiver_state':'ACTIVE',
        'source_session':b['source_session'],'sequence':b['command_sequence'],'permit_id':b['permit_id'],
        'generation':b['permit_generation'],'context_sha256':sha(compact(normalized)),
        'command_sha256':sha(transfer['body']),'operation':b['command_context']['operation'],'verified_steady_ns':101,'steady_ns':102}


def test_commit_native_transfer_exact_retry_ack_and_movement_stays_closed(tmp_path):
    async def run():
        c,p,b,decision,s=await start(tmp_path)
        try:
            r=await c.submit(exchange(p,s));t=r['transfer'];body=json.loads(t['body'])
            permit,child=decisions(body['command_context'])
            assert permit['identity']==decision['identity'] and child['child_provenance']==p['child_provenance']
            assert permit['identity']['fm_session']==c._traffic_protocol_session==body['source_session']
            row=c.store.connection.execute('SELECT payload,state FROM traffic_outbox WHERE event_id=?',(t['transfer_id'],)).fetchone()
            assert json.loads(row['payload'])==t and row['state']=='PENDING' and not c.store.connection.in_transaction
            assert r['ack'] is None
            assert (await c.submit(exchange(p,s)))['reason']=='DUPLICATE_OR_OLD_NATIVE_REPORT'
            newer={**s,'report_sequence':2}
            assert (await c.submit(exchange(p,newer)))['transfer']['body']==t['body']
            proof=accepted(newer,t)
            ack=(await c.submit(exchange(p,proof)))['ack']
            assert ack['native_verified'] and ack['fm_context_valid_at_ack']
            assert ack['receiver_live_now']=='UNKNOWN' and not ack['movement_authorized'] and not ack['ownership_release']
            assert c.store.connection.execute('SELECT state FROM traffic_outbox WHERE event_id=?',(t['transfer_id'],)).fetchone()[0]=='PENDING'
            saved=c.store.connection.execute('SELECT decision FROM traffic_decisions WHERE event_id=?',('native-ack:'+t['transfer_id'],)).fetchone()
            assert json.loads(saved[0])==ack
            gate=MovementGate(clock=lambda:1.);gate.prepare(p,2.)
            assert gate.receive({**decision,'committed':True})
            assert not gate.native_zero_matches(body['command_context'])
            assert gate.observe_child_accepted(p['child_uuid'],bytes.fromhex(p['path_bytes']))
            assert gate.native_zero_matches(body['command_context'])
            assert not gate.send(lambda:pytest.fail('Movement opened'))
            gate.revoke();assert not gate.native_zero_matches(body['command_context'])
        finally:await c.close();c.store.close()
    asyncio.run(run())


@pytest.mark.parametrize('change',['signature','robot','session','request','missing_child','changed_outbox'])
def test_invalid_sources_do_not_create_native_transfer(tmp_path,change):
    async def run():
        c,p,b,d,s=await start(tmp_path)
        try:
            key=KEY
            if change=='signature':key=b'wrong'
            if change=='robot':s['robot_id']='other'
            if change=='session':
                # Existing cursor refuses a new receiver session, even before any ACK.
                await c.submit(exchange(p,s));s.update(receiver_session='d'*64,report_sequence=2)
            if change=='request':p['request_id']=str(uuid4())
            if change=='missing_child':c.store.connection.execute('DELETE FROM traffic_outbox WHERE event_id=?',(child_event(p).event_id,))
            if change=='changed_outbox':c.store.connection.execute("UPDATE traffic_outbox SET payload='{}' WHERE event_id=?",('permit:'+p['request_id'],))
            result=await c.submit(exchange(p,s,key))
            assert result['status']=='DENIED' and not result.get('transfer')
            assert not result['movement_authorized']
        finally:await c.close();c.store.close()
    asyncio.run(run())


@pytest.mark.parametrize('reason',['REPLAN','CANCEL','PREEMPTION'])
def test_closed_context_and_late_native_ack_never_restores_it(tmp_path,reason):
    async def run():
        c,p,b,d,s=await start(tmp_path)
        try:
            t=(await c.submit(exchange(p,s)))['transfer']
            b.request=deepcopy(p);closed=b.close(reason);await c.submit(child_event(closed))
            result=await c.submit(exchange(p,accepted(s,t)))
            assert result['ack']['status']=='NATIVE_ZERO_VERIFIED_LATE'
            assert result['ack']['fm_context_valid_at_ack'] is False
            assert json.loads(result['transfer']['body'])['command_context']['operation']=='REVOKE_ZERO'
            assert result['transfer']['command_sequence']>t['command_sequence']
            assert not result['movement_authorized']
        finally:await c.close();c.store.close()
    asyncio.run(run())


def test_ack_commit_failure_retries_actual_readback_without_rewriting_prior_ack(tmp_path):
    async def run():
        c,p,b,d,s=await start(tmp_path)
        try:
            t=(await c.submit(exchange(p,s)))['transfer'];proof=accepted(s,t)
            c.store.connection.execute("CREATE TRIGGER fail_ack BEFORE INSERT ON traffic_outbox WHEN NEW.event_id LIKE 'native-ack:%' BEGIN SELECT RAISE(ABORT,'ack rollback'); END")
            with pytest.raises(Exception,match='ack rollback'):await c.submit(exchange(p,proof))
            assert c.store.connection.execute('SELECT report_seq FROM traffic_native_receivers').fetchone()[0]==1
            assert not c.store.connection.execute("SELECT 1 FROM traffic_decisions WHERE event_id LIKE 'native-ack:%'").fetchone()
            c.store.connection.execute('DROP TRIGGER fail_ack')
            ack=(await c.submit(exchange(p,proof)))['ack']
            assert ack['native_verified'] and ack['native_status']['command_sha256']==sha(t['body'])
            proof['report_sequence']+=1
            assert (await c.submit(exchange(p,proof)))['ack'] is None
            saved=c.store.connection.execute('SELECT decision FROM traffic_decisions WHERE event_id=?',('native-ack:'+t['transfer_id'],)).fetchone()[0]
            assert json.loads(saved)==ack
            assert set(r[0] for r in c.store.connection.execute('SELECT state FROM traffic_outbox'))=={'PENDING'}
        finally:await c.close();c.store.close()
    asyncio.run(run())


def test_commit_failure_rolls_back_cursor_and_transfer_without_ack(tmp_path):
    async def run():
        c,p,b,d,s=await start(tmp_path)
        try:
            c.store.connection.execute("CREATE TRIGGER fail_native BEFORE INSERT ON traffic_outbox WHEN NEW.event_id LIKE 'native-transfer:%' BEGIN SELECT RAISE(ABORT,'native rollback'); END")
            with pytest.raises(Exception,match='native rollback'):await c.submit(exchange(p,s))
            assert c.store.connection.execute('SELECT count(*) FROM traffic_native_receivers').fetchone()[0]==0
            assert c.store.connection.execute("SELECT count(*) FROM traffic_decisions WHERE event_id LIKE 'native-%'").fetchone()[0]==0
        finally:await c.close();c.store.close()
    asyncio.run(run())


@pytest.mark.parametrize('field',['command_sha256','source_session','generation','context_sha256','sequence'])
def test_ack_hash_session_generation_and_domain_cannot_be_forged(tmp_path,field):
    async def run():
        c,p,b,d,s=await start(tmp_path)
        try:
            t=(await c.submit(exchange(p,s)))['transfer']
            proof=accepted(s,t)
            proof[field]=999 if field in ('generation','sequence') else 'wrong'
            result=await c.submit(exchange(p,proof))
            assert result['reason']=='NATIVE_CONTEXT_FENCE' and result.get('ack') is None
            with pytest.raises(ValueError):verify(sign(compact(s),KEY),KEY,domain=STATUS_DOMAIN)
        finally:await c.close();c.store.close()
    asyncio.run(run())


def test_late_native_ack_is_historical_and_only_revoke_can_follow(tmp_path):
    async def run():
        c,p,b,d,s=await start(tmp_path)
        try:
            t=(await c.submit(exchange(p,s)))['transfer']
            c._clock=lambda:10.6
            r=await c.submit(exchange(p,accepted(s,t)))
            assert r['ack']['status']=='NATIVE_ZERO_VERIFIED_LATE'
            assert not r['ack']['fm_context_valid_at_ack']
            assert json.loads(r['transfer']['body'])['command_context']['operation']=='REVOKE_ZERO'
        finally:await c.close();c.store.close()
    asyncio.run(run())


def test_receiver_restart_fence_is_durable_and_old_session_cannot_return(tmp_path):
    async def run():
        c,p,b,d,s=await start(tmp_path)
        try:
            await c.submit(exchange(p,s))
            restart={**s,'receiver_session':'d'*64,'report_sequence':2}
            assert (await c.submit(exchange(p,restart)))['reason']=='NATIVE_RECEIVER_SESSION_CHANGED'
            assert (await c.submit(exchange(p,{**s,'report_sequence':3})))['reason']=='NATIVE_RECEIVER_SESSION_CHANGED'
            assert c.store.connection.execute('SELECT fenced FROM traffic_native_receivers').fetchone()[0]==1
        finally:await c.close();c.store.close()
    asyncio.run(run())


def test_legacy_preparation_cannot_become_actual_native_context(tmp_path):
    async def run():
        c,p=await setup(tmp_path,native_keys={'r1':KEY})
        try:
            assert (await c.submit(legacy_request(p)))['status']=='RESERVED'
            # Use a real schema-shaped unit status; absence of T2 actual proof is decisive.
            s=dict(robot_id='r1',receiver_session='a'*64,ticket='b'*64,report_sequence=1,receiver_state='NO_COMMAND',
                source_session='',sequence=0,permit_id='',generation=0,context_sha256='',command_sha256='',operation='NONE',
                verified_steady_ns=0,steady_ns=100,movement_authorized=False,ownership_release=False)
            assert (await c.submit(exchange(p,s)))['reason']=='ACTUAL_CHILD_REQUIRED'
        finally:await c.close();c.store.close()
    asyncio.run(run())


@pytest.mark.parametrize('fault',['missing','stale','session','error'])
def test_geometry_start_waits_for_all_current_statuses(tmp_path,fault):
    async def run():
        c,p,b,d,s=await start(tmp_path)
        try:
            core=c.core
            assert traffic_start_ready(core,10.)
            r=core.tracker.get_robot('r1')
            if fault=='missing':r.initial_status_verified=False
            if fault=='stale':r.last_status_received_at=7.999
            if fault=='session':r.session_blocked=True
            if fault=='error':r.state=RobotState.STATE_ERROR
            assert not traffic_start_ready(core,10.)
            assert traffic_start_ready(c.core,10.)  # Readiness cannot mutate/unblock core.
        finally:await c.close();c.store.close()
    asyncio.run(run())
