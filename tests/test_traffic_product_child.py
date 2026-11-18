"""Actual-child provenance fences; all motion and physical release stay disabled."""
import asyncio
import ast
from copy import deepcopy
from dataclasses import asdict
import json
from uuid import uuid4
from pathlib import Path
import pytest

from fleet_robot_executor.child_binding import ChildBinding
from backend.fleet_manager.event_loop import Event, FleetEventLoop
from backend.fleet_manager.persistence.store import SQLiteStore, ScenarioResetRequired
from backend.fleet_manager.domain.traffic import PermitIdentity, ReleaseEvidence
from test_traffic_protocol import setup


def uid(): return str(uuid4())


def test_default_launcher_cannot_install_child_observer():
    root=Path(__file__).resolve().parents[1]
    source=(root/'ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py').read_text()
    constructor=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name=='__init__')
    defaults=dict(zip((arg.arg for arg in constructor.args.kwonlyargs),constructor.args.kw_defaults))
    assert isinstance(defaults['_traffic_child_test_profile'],ast.Constant)
    assert defaults['_traffic_child_test_profile'].value is None
    for name in ['scripts/start_demo.py','scripts/start_demo.sh','scripts/c5_demo_start.py',
                 'backend/dashboard/runtime.py','ros2_ws/src/fleet_robot_executor/launch/robot_executor.launch.py']:
        text=(root/name).read_text()
        assert '_traffic_child_test_profile' not in text and 'fleet_nav2_observer' not in text
        assert 'c5-b6b7' not in text and 'C5_AUTH_ZERO_ONLY' not in text


def context(p):
    return {k: p[k] for k in ('robot_id', 'task_id', 'epoch', 'execute_uuid', 'executor_session',
                             'movement_kind', 'station_id')}


def observation(b, p):
    return dict(context_id=b.context_id, nav_uuid=b.nav_uuid, executor_session=p['executor_session'],
        observer_session=uid(), child_uuid=p['child_uuid'], path_bytes=bytes.fromhex(p['path_bytes']),
        sequence=1, stamp_ns=10**9, kind=1, reason='ACCEPTED', terminal_status=0)


def prepared(p):
    b = ChildBinding(context(p), uid(), deadline=3., timeout_ns=2*10**9)
    assert b.confirm_nav(b.nav_uuid)
    return b, observation(b, p)


def consume(b, o, p, **kw):
    return b.observe(o, now_ns=10**9, receipt_now=1., assignment=context(p), **kw)


def event(p):
    c = p['child_provenance']
    return Event('TRAFFIC_PROTOCOL_CHILD', p, 'child:'+c['context_id']+':'+str(c['sequence']))


@pytest.mark.parametrize('field', ['context_id', 'nav_uuid', 'executor_session', 'child_uuid', 'observer_session'])
def test_wrong_initial_provenance_never_creates_binding(tmp_path, field):
    async def run():
        c,p=await setup(tmp_path)
        try:
            b,o=prepared(p)
            # Unknown context/nav/session is rejected. A distinct real child/session
            # is only trusted when supplied by the instrumented client transaction;
            # upper action UUIDs and zero observer IDs are never accepted as a child.
            o[field] = p['execute_uuid'] if field=='child_uuid' else ('00000000-0000-0000-0000-000000000000' if field=='observer_session' else uid())
            assert consume(b,o,p) is None and b.request is None
        finally: await c.close();c.store.close()
    asyncio.run(run())


@pytest.mark.parametrize('change', ['path', 'child', 'sequence_gap', 'terminal', 'replan', 'stale', 'assignment', 'timeout'])
def test_changes_close_without_reviving_old_context(tmp_path, change):
    async def run():
        c,p=await setup(tmp_path)
        try:
            b,o=prepared(p)
            assert consume(b,o,p)
            changed=deepcopy(o);changed['sequence']=2
            if change=='path': changed['path_bytes']+=b'changed'
            if change=='child': changed['child_uuid']=uid()
            if change=='sequence_gap': changed['sequence']=3
            if change=='terminal': changed.update(kind=3,terminal_status=4)
            if change=='replan': changed.update(kind=2,reason='REPLAN')
            if change=='stale': changed['stamp_ns']=-2*10**9
            current=context(p);receipt=1.
            if change=='assignment': current['epoch']+=1
            if change=='timeout': receipt=3.
            closed=b.observe(changed, now_ns=10**9,receipt_now=receipt,assignment=current)
            assert b.closed and closed['child_provenance']['kind'] in (2,3)
            assert consume(b,o,p) is None and not b.confirm_nav(b.nav_uuid)
        finally: await c.close();c.store.close()
    asyncio.run(run())


def test_duplicate_and_observer_restart_do_not_refresh_or_replace(tmp_path):
    async def run():
        c,p=await setup(tmp_path)
        try:
            b,o=prepared(p);assert consume(b,o,p)
            assert consume(b,o,p) is None
            wrong={**o,'observer_session':uid(),'sequence':2}
            assert consume(b,wrong,p) is None
            assert b.sequence==1 and b.deadline==3.
            fresh,_=prepared(p)
            assert consume(fresh,o,p) is None
            assert b.close('CANCEL')['child_provenance']['kind']==2
            assert b.close('DUPLICATE_CANCEL') is None
        finally: await c.close();c.store.close()
    asyncio.run(run())


def enrich(actual, p):
    return {**p, **actual, **{k:p[k] for k in ('geometry','geometry_digest','map_revision','geometry_revision','frame','points')}}


def test_consumer_actual_child_commit_invalidation_replay_and_release(tmp_path):
    async def run():
        c,p=await setup(tmp_path)
        try:
            b,o=prepared(p);actual=enrich(consume(b,o,p),p)
            result=await c.submit(event(actual))
            assert result['status']=='RESERVED' and result['identity']['child_uuid']==o['child_uuid']
            assert result['identity']['execute_uuid']==p['execute_uuid'] != o['child_uuid']
            assert result['child_provenance']['nav_uuid']==b.nav_uuid
            assert not result['movement_authorized'] and not result['ownership_release']
            assert (await c.submit(event(actual)))['reason']=='CHILD_OBSERVATION_REPLAY'
            b.request=deepcopy(actual)
            closed=b.close('PREEMPTION_ACCEPTED')
            assert (await c.submit(event(closed)))['reason']=='CHILD_CLOSED_OWNERSHIP_RETAINED'
            assert (await c.submit(event(actual)))['status']=='DENIED'
            altered=deepcopy(actual);altered['child_provenance']['sequence']=3
            assert (await c.submit(event(altered)))['reason']=='CHILD_CONTEXT_CLOSED'
            evidence=ReleaseEvidence(PermitIdentity(**result['identity']),(result['identity']['permit_id'],),
                                     child_terminal='STATUS_CANCELED')
            assert (await c.submit(Event('TRAFFIC_RELEASE',{'evidence':asdict(evidence)})))['reason']=='RELEASE_THRESHOLDS_UNVERIFIED'
            assert c.core._active_tasks_by_robot[p['robot_id']].task_id==p['task_id']
            snap=json.loads(c.store.connection.execute('SELECT snapshot FROM traffic_state').fetchone()[0])
            assert len(snap['state']['claims'])==1
            assert c.store.connection.execute("SELECT count(*) FROM traffic_outbox WHERE event_id IN (?,?)",
                (event(actual).event_id,event(closed).event_id)).fetchone()[0]==2
        finally: await c.close();c.store.close()
    asyncio.run(run())


@pytest.mark.parametrize('field', ['epoch','executor_session','execute_uuid','child_uuid','path_hash','observer_session','nav_uuid'])
def test_consumer_rejects_wrong_actual_context(tmp_path,field):
    async def run():
        c,p=await setup(tmp_path)
        try:
            b,o=prepared(p);actual=enrich(consume(b,o,p),p)
            assert (await c.submit(event(actual)))['status']=='RESERVED'
            bad=deepcopy(actual);bad['child_provenance']['sequence']=2;bad['child_provenance']['kind']=2
            if field in ('observer_session','nav_uuid'): bad['child_provenance'][field]=uid()
            else: bad[field]=99 if field=='epoch' else uid()
            assert (await c.submit(event(bad)))['status']=='DENIED'
            assert c.store.connection.execute("SELECT count(*) FROM traffic_decisions WHERE event_id LIKE 'child:%'").fetchone()[0]==1
        finally: await c.close();c.store.close()
    asyncio.run(run())


def test_out_of_order_invalidation_is_tombstone_and_rollback_is_atomic(tmp_path):
    async def run():
        c,p=await setup(tmp_path)
        try:
            b,o=prepared(p);actual=enrich(consume(b,o,p),p);b.request=deepcopy(actual)
            closed=b.close('CANCEL_BEFORE_RPC_COMMIT')
            assert (await c.submit(event(closed)))['status']=='RECORDED'
            assert (await c.submit(event(actual)))['status']=='DENIED'
            b,o=prepared(p);fresh=enrich(consume(b,o,p),p)
            c.store.connection.execute("CREATE TRIGGER fail_child BEFORE INSERT ON traffic_outbox WHEN NEW.event_id LIKE 'child:%' BEGIN SELECT RAISE(ABORT,'injected child rollback'); END")
            with pytest.raises(Exception,match='injected child rollback'):await c.submit(event(fresh))
            assert not c.store.connection.execute('SELECT 1 FROM traffic_decisions WHERE event_id=?',(event(fresh).event_id,)).fetchone()
            assert not c.store.connection.execute('SELECT 1 FROM traffic_decisions WHERE event_id=?',('permit:'+fresh['request_id'],)).fetchone()
        finally: await c.close();c.store.close()
    asyncio.run(run())


def test_restart_does_not_rehydrate_valid_context(tmp_path):
    async def run():
        c,p=await setup(tmp_path)
        b,o=prepared(p);actual=enrich(consume(b,o,p),p)
        assert (await c.submit(event(actual)))['status']=='RESERVED'
        core=c.core
        await c.close();c.store.close()
        store=SQLiteStore(tmp_path/'traffic.db')
        try:
            with pytest.raises(ScenarioResetRequired,match='Scenario reset required'):FleetEventLoop(store,core)
        finally:store.close()
    asyncio.run(run())
