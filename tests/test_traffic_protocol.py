"""Targeted consumer/SQLite integration and fake service/action admission checks."""
import asyncio
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ros2_ws/src/fleet_robot_executor'))
from fleet_robot_executor.traffic import MovementGate
from backend.fleet_manager.domain import FleetManagerCore, Pose2D, StationType
from backend.fleet_manager.domain.traffic import Box, sweep
from backend.fleet_manager.event_loop import FleetEventLoop, Event
from backend.fleet_manager.persistence.store import SQLiteStore
from backend.fleet_manager.persistence.traffic_protocol import digest


def uid():
    return str(uuid4())


class Routes:
    def get_path_distance(self, *args):
        return 1.


async def setup(tmp_path, *, enabled=True, native_keys=None):
    store = SQLiteStore(tmp_path / 'traffic.db')
    core = FleetManagerCore(Routes(), Pose2D())
    core.register_robot('r1')
    core.register_station('dock', StationType.CHARGING, Pose2D())
    loop = FleetEventLoop(store, core, clock=lambda: 10.)
    if enabled:
        loop.enable_traffic_protocol_test(enclosing_radius=.2)
    if native_keys is not None:
        loop.enable_native_zero_test(keys=native_keys,ack_timeout=.5)
    await loop.start()
    session = uid()
    await loop.submit(Event('ROBOT_STATUS', dict(robot_id='r1', status_seq=1, current_epoch=0,
        current_task_id=None, state=1, current_phase=0, is_loaded=False, pose=Pose2D(), battery_soc_percent=100,
        battery_energy_wh=100, timestamp_sec=10., publisher_session_id=session)))
    await loop.submit(Event('SUBMIT_TASK', dict(task_id='real-task', pickup_pose=Pose2D(1,0),
        dropoff_pose=Pose2D(2,0), priority=3, created_at=1.)))
    await loop.submit(Event('TICK', {'current_time': 10.}))
    await loop.submit(Event('TRAFFIC_CONFIGURE', dict(revision='m1', frame='map', geometry_revision='g1',
        managed=[asdict(Box(-10,-10,10,10))])))
    task = loop.core._active_tasks_by_robot['r1']
    boxes = [asdict(b) for b in sweep(((0.,0.),(1.,0.)), .2)]
    p = dict(request_id=uid(), robot_id='r1', task_id=task.task_id, epoch=task.assignment_epoch,
        execute_uuid=task.goal_uuid, child_uuid=uid(), executor_session=session, movement_kind='PICKUP', station_id='',
        path_bytes=b'immutable-complete-ros-path'.hex(), path_hash=hashlib.sha256(b'immutable-complete-ros-path').hexdigest(),
        points=[(0.,0.),(1.,0.)], geometry=boxes, geometry_digest=digest(boxes),
        map_revision='m1', geometry_revision='g1', frame='map')
    return loop, p


def request(p):
    return Event('TRAFFIC_PROTOCOL_REQUEST', p, 'permit:' + p['request_id'])


def ack(d, kind='APPLIED'):
    return {**{k: d[k] for k in ('identity', 'request_id', 'movement_kind', 'station_id', 'geometry_digest')},
            'kind': kind, 'local_binding_id': uid()}


def run_case(function):
    def test(tmp_path):
        async def scenario():
            loop, p = await setup(tmp_path)
            try:
                await function(loop, p)
            finally:
                await loop.close()
                loop.store.close()
        asyncio.run(scenario())
    return test


@run_case
async def test_request_commit_duplicate_and_fake_ack(loop, p):
    result = await loop.submit(request(p))
    assert result['status'] == 'RESERVED' and result['movement_authorized'] is False
    assert not loop.store.connection.in_transaction
    saved = loop.store.connection.execute('SELECT payload FROM traffic_outbox WHERE event_id=?',
                                          (request(p).event_id,)).fetchone()
    assert json.loads(saved[0]) == result
    assert await loop.submit(request(p)) == result
    changed = deepcopy(p); changed['child_uuid'] = uid()
    assert (await loop.submit(request(changed)))['reason'] == 'EVENT_PAYLOAD_CHANGED'
    received = await loop.submit(Event('TRAFFIC_PROTOCOL_ACK', ack(result)))
    assert received['reason'] == 'UNQUALIFIED_LOCAL_ACK' and received['movement_authorized'] is False
    gate = MovementGate(clock=lambda: 1.)
    gate.prepare(p, 2.)
    calls = []
    assert not gate.send(lambda: calls.append(1))
    assert gate.receive({**result, 'committed': True})
    assert not gate.send(lambda: calls.append(1))
    assert gate.applied_ack(ack(result))
    assert not gate.send(lambda: calls.append(1)) and calls == []


@pytest.mark.parametrize('field,value', [('epoch',99), ('executor_session',None), ('execute_uuid',None),
    ('map_revision','old'), ('geometry_revision','old'), ('geometry_digest','wrong'), ('path_hash','wrong')])
def test_request_fences(tmp_path, field, value):
    async def scenario():
        loop, p = await setup(tmp_path)
        try:
            p[field] = uid() if value is None else value
            result = await loop.submit(request(p))
            assert result['status'] == 'DENIED' and not result['movement_authorized']
            snapshot = json.loads(loop.store.connection.execute('SELECT snapshot FROM traffic_state').fetchone()[0])
            assert not snapshot['state']['claims']
        finally:
            await loop.close(); loop.store.close()
    asyncio.run(scenario())


@run_case
async def test_commit_failure_no_grant_or_outbox(loop, p):
    loop.store.connection.execute("CREATE TRIGGER no_protocol BEFORE INSERT ON traffic_outbox "
        "WHEN NEW.event_id LIKE 'permit:%' BEGIN SELECT RAISE(ABORT,'injected'); END")
    with pytest.raises(Exception, match='injected'):
        await loop.submit(request(p))
    assert loop.store.connection.execute('SELECT 1 FROM traffic_decisions WHERE event_id=?',
                                          (request(p).event_id,)).fetchone() is None
    snap = json.loads(loop.store.connection.execute('SELECT snapshot FROM traffic_state').fetchone()[0])
    assert snap['state']['contexts'] == {} and snap['state']['claims'] == {}


@run_case
async def test_revoke_retire_and_disconnect_keep_ownership(loop, p):
    result = await loop.submit(request(p))
    before = loop.core._active_tasks_by_robot['r1']
    assert (await loop.submit(Event('TRAFFIC_PROTOCOL_ACK', ack(result, 'RETIRED'))))['movement_authorized'] is False
    updates = await loop.submit(Event('TRAFFIC_PROTOCOL_UPDATES'))
    assert updates[0]['status'] == 'REVOKED'
    assert (await loop.submit(request(p)))['status'] == 'DENIED'
    snapshot = json.loads(loop.store.connection.execute('SELECT snapshot FROM traffic_state').fetchone()[0])
    assert snapshot['state']['claims'][result['identity']['permit_id']]['state'] == 'BLOCKED'
    after = loop.core._active_tasks_by_robot['r1']
    assert (after.task_id, after.assignment_epoch, after.goal_uuid) == (before.task_id,before.assignment_epoch,before.goal_uuid)
    await loop.submit(Event('TICK', {'current_time': 30.}))
    assert 'r1' in loop.core._active_tasks_by_robot


@run_case
async def test_session_change_denies_cached_grant(loop, p):
    await loop.submit(request(p))
    await loop.submit(Event('ROBOT_STATUS', dict(robot_id='r1', status_seq=1, current_epoch=p['epoch'],
        current_task_id=p['task_id'], state=2, current_phase=1, is_loaded=False, pose=Pose2D(),
        battery_soc_percent=100, battery_energy_wh=100, timestamp_sec=10., publisher_session_id=uid())))
    assert (await loop.submit(request(p)))['status'] == 'DENIED'
    assert (await loop.submit(Event('TRAFFIC_PROTOCOL_UPDATES')))[0]['status'] == 'REVOKED'


def test_disabled_by_default(tmp_path):
    async def scenario():
        loop, p = await setup(tmp_path, enabled=False)
        try:
            result = await loop.submit(request(p))
            assert result['reason'] == 'TEST_MODE_DISABLED'
            assert loop._traffic_protocol_session is None
        finally:
            await loop.close(); loop.store.close()
    asyncio.run(scenario())


def test_gate_late_changed_session_digest_generation_and_send_revoke_race():
    now = [1.]
    p = dict(request_id=uid(), robot_id='r1', task_id='actual', epoch=1, execute_uuid=uid(), child_uuid=uid(),
        executor_session=uid(), path_hash='digest', map_revision='m1', geometry_revision='g1', frame='map',
        geometry_digest='geometry', movement_kind='PICKUP', station_id='')
    i = {k:v for k,v in p.items() if k not in ('request_id','movement_kind','station_id','geometry_digest')}
    i.update(fm_session=uid(), permit_id=uid(), generation=1)
    d = dict(identity=i, request_id=p['request_id'], geometry_digest=p['geometry_digest'], movement_kind='PICKUP',
             station_id='', committed=True, movement_authorized=False, status='RESERVED', reason='')
    for field in ('epoch','child_uuid','execute_uuid','executor_session','path_hash','map_revision','geometry_revision'):
        gate = MovementGate(clock=lambda: now[0]); gate.prepare(p, 2.)
        bad = deepcopy(d); bad['identity'][field] = 99 if field=='epoch' else uid()
        assert not gate.receive(bad)
        assert not gate.receive(d)  # rejection fences this prepared child permanently
    for revoke_first in (True, False):
        gate = MovementGate(clock=lambda: now[0]); gate.prepare(p, 2.)
        assert gate.receive(d) and gate.receive(d)
        assert gate.applied_ack(ack(d))
        calls = []
        if revoke_first: gate.revoke()
        assert not gate.send(lambda: calls.append(1))
        gate.revoke()
        assert not gate.receive(d) and not gate.send(lambda: calls.append(1))
        assert calls == []
    gate = MovementGate(clock=lambda: now[0]); gate.prepare(p, 2.)
    now[0] = 4.
    assert not gate.receive(d) and gate.state == 'TIMEOUT'
    gate = MovementGate(clock=lambda: 1.); gate.prepare(p, 2.); assert gate.receive(d)
    bad = deepcopy(d); bad['identity']['generation'] = 2
    assert not gate.receive(bad) and not gate.receive(d)


@pytest.mark.parametrize('kind,station_type', [('PARK',StationType.PARKING),('CHARGE',StationType.CHARGING)])
def test_station_identity_is_domain_generated(tmp_path, kind, station_type):
    async def scenario():
        core = FleetManagerCore(Routes(), Pose2D(), low_soc_percent=20.)
        core.register_robot('r1')
        core.register_station('berth', station_type, Pose2D(1.,0.))
        robot = core.tracker.get_robot('r1')
        robot.session_id = uid(); robot.initial_status_verified = True; robot.last_status_received_at = 10.
        # The normal station domain allocator creates move_id, epoch and action UUID.
        core.station_dispatch._assign(core, robot, core.reservations.get_station('berth'))
        move = core.station_dispatch.active['r1']
        store = SQLiteStore(tmp_path / 'station.db')
        loop = FleetEventLoop(store, core, clock=lambda:10.)
        loop.enable_traffic_protocol_test(enclosing_radius=.2)
        await loop.start()
        try:
            await loop.submit(Event('TRAFFIC_CONFIGURE', dict(revision='m1',frame='map',geometry_revision='g1',
                managed=[asdict(Box(-10,-10,10,10))])))
            boxes = [asdict(b) for b in sweep(((0.,0.),(1.,0.)),.2)]
            p = dict(request_id=uid(),robot_id='r1',task_id=move.task_id,epoch=move.assignment_epoch,
                execute_uuid=move.goal_uuid,child_uuid=uid(),executor_session=move.session_id,
                movement_kind=kind,station_id=move.station_id,path_bytes=b'path'.hex(),
                path_hash=hashlib.sha256(b'path').hexdigest(),points=[(0.,0.),(1.,0.)],geometry=boxes,
                geometry_digest=digest(boxes),map_revision='m1',geometry_revision='g1',frame='map')
            d = await loop.submit(request(p))
            assert d['status']=='RESERVED' and d['identity']['task_id']==move.task_id
            assert not d['movement_authorized']
            wrong = {**p,'request_id':uid(),'station_id':'other'}
            assert (await loop.submit(request(wrong)))['status']=='DENIED'
            assert loop.core.reservations.get_station('berth').has_owner('r1')
        finally:
            await loop.close();store.close()
    asyncio.run(scenario())


def test_product_config_does_not_expose_traffic_enable():
    import yaml
    from pydantic import ValidationError
    from fleet_config.models import FleetConfig
    data = yaml.safe_load((ROOT / 'config/fleet.warehouse-30x18.yaml').read_text())
    data['traffic_protocol_test'] = True
    with pytest.raises(ValidationError):
        FleetConfig.model_validate(data)


@run_case
async def test_local_ack_fences_and_old_child_response(loop, p):
    d = {**(await loop.submit(request(p))), 'committed':True}
    gate = MovementGate(clock=lambda:1.); gate.prepare(p,2.); assert gate.receive(d)
    for field in ('request_id','geometry_digest','station_id','movement_kind'):
        bad = ack(d); bad[field] = 'wrong'
        assert not gate.applied_ack(bad)
    bad = ack(d); bad['identity'] = {**bad['identity'],'executor_session':uid()}
    assert not gate.applied_ack(bad)
    assert gate.applied_ack(ack(d)) and gate.applied_ack(ack(d))
    new = {**p,'request_id':uid(),'child_uuid':uid()}
    gate.prepare(new,2.)
    assert not gate.receive(d) and gate.state == 'WAITING'
    assert not gate.applied_ack(ack(d))
    gate.revoke('SESSION_CHANGED')
    assert not gate.receive(d) and not gate.send(lambda: pytest.fail('old child sent'))


@run_case
async def test_concurrent_send_revoke_cannot_open(loop, p):
    import threading
    d = {**(await loop.submit(request(p))), 'committed':True}
    gate = MovementGate(clock=lambda:1.); gate.prepare(p,2.); gate.receive(d); gate.applied_ack(ack(d))
    barrier = threading.Barrier(3); results = []; sent = []
    def send():
        barrier.wait(); results.append(gate.send(lambda:sent.append(True)))
    def revoke():
        barrier.wait(); gate.revoke()
    threads = [threading.Thread(target=send),threading.Thread(target=revoke)]
    for t in threads: t.start()
    barrier.wait()
    for t in threads: t.join(2.); assert not t.is_alive()
    assert results == [False] and sent == [] and not gate.receive(d)
