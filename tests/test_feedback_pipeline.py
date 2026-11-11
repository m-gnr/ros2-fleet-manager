"""Real action adapter -> single consumer -> domain/SQLite progress regressions."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest

from backend.fleet_manager.adapters.action_client import ExecuteTaskActionClientBridge
from backend.fleet_manager.domain import FleetManagerCore, Pose2D
from backend.fleet_manager.event_loop import Event, FleetEventLoop
from backend.fleet_manager.persistence import SQLiteStore


class Routes:
    def get_path_distance(self, *_):
        return 1.0


@asynccontextmanager
async def pipeline(tmp_path):
    store = SQLiteStore(tmp_path/'feedback.sqlite3')
    clock = [10.]
    core = FleetManagerCore(Routes(), Pose2D())
    core.register_robot('r1')
    core.register_robot('r2')
    consumer = FleetEventLoop(store, core, clock=lambda: clock[0])
    await consumer.start()
    observed, errors, events = [], [], []

    class Observe:
        async def submit(self, event):
            events.append(event)
            try:
                result = await consumer.submit(event)
                observed.append(result)
                return result
            except Exception as exc:
                errors.append(exc)
                raise

    bridge = ExecuteTaskActionClientBridge('r1', Observe(), asyncio.get_running_loop())
    try:
        for rid in ('r1', 'r2'):
            await consumer.submit(Event('ROBOT_STATUS', dict(robot_id=rid,status_seq=1,current_epoch=0,
                current_task_id=None,state=1,current_phase=0,is_loaded=False,pose=Pose2D(),battery_soc_percent=100.,
                battery_energy_wh=100.,timestamp_sec=10.,publisher_session_id='session-'+rid)))
        await consumer.submit(Event('SUBMIT_TASK',dict(task_id='t1',pickup_pose=Pose2D(1,0),
            dropoff_pose=Pose2D(2,0),priority=3,created_at=1.)))
        await consumer.submit(Event('TICK',dict(current_time=10.)))
        task = consumer.core._active_tasks['t1']
        assert task.assigned_robot_id == 'r1'

        async def feedback(**changes):
            wrapper = SimpleNamespace(feedback=SimpleNamespace(current_phase=1,distance_to_goal=1.,battery_soc=99.))
            bridge.robot_id = changes.pop('robot_id','r1')
            old = len(observed)+len(errors)
            bridge._handle_feedback(changes.get('task_id',task.task_id), changes.get('goal_uuid',task.goal_uuid),
                changes.get('assignment_epoch',task.assignment_epoch), wrapper)
            for _ in range(100):
                if len(observed)+len(errors)>old:
                    break
                await asyncio.sleep(.001)
            assert len(observed)+len(errors)>old
            await asyncio.sleep(0)

        yield consumer, task, feedback, observed, errors, events, clock
    finally:
        await consumer.close()
        store.close()


def rows(consumer, table):
    return [dict(r) for r in consumer.store.connection.execute('SELECT * FROM '+table)]


def test_adapter_payload_reaches_real_domain_and_executes(tmp_path, monkeypatch):
    calls = []
    original = FleetManagerCore.handle_action_feedback
    def record(self, **kwargs):
        calls.append(kwargs)
        return original(self, **kwargs)
    monkeypatch.setattr(FleetManagerCore,'handle_action_feedback',record)
    async def scenario():
        async with pipeline(tmp_path) as (consumer,task,feedback,observed,errors,events,clock):
            before = rows(consumer,'outbox_events')
            await feedback()
            assert observed==['APPLIED'] and not errors
            assert set(events[0].payload)=={'robot_id','task_id','assignment_epoch','goal_uuid','status_seq',
                                         'current_phase','distance_to_goal','battery_soc'}
            assert calls==[dict(robot_id='r1',task_id='t1',assignment_epoch=task.assignment_epoch,
                                goal_uuid=task.goal_uuid,current_phase=1)]
            assert rows(consumer,'tasks')[0]['status']=='EXECUTING'
            assert rows(consumer,'outbox_events')==before
    asyncio.run(scenario())


@pytest.mark.parametrize('changes',[
    {'task_id':'another-task'}, {'robot_id':'r2'}, {'assignment_epoch':99},
    {'goal_uuid':'another-goal'},
])
def test_wrong_identity_cannot_mutate_assignment(tmp_path,changes):
    async def scenario():
        async with pipeline(tmp_path) as (consumer,task,feedback,observed,errors,events,clock):
            before = {t:rows(consumer,t) for t in ('tasks','robots','outbox_events','reservations')}
            await feedback(**changes)
            assert observed==['STALE'] and not errors
            assert {t:rows(consumer,t) for t in before}==before
    asyncio.run(scenario())


def test_duplicate_and_backwards_feedback_and_terminal_fencing(tmp_path):
    async def scenario():
        async with pipeline(tmp_path) as (consumer,task,feedback,observed,errors,events,clock):
            await feedback()
            original = events[0]
            assert await consumer.submit(original)=='DUPLICATE'
            assert await consumer.submit(Event('ACTION_FEEDBACK',deepcopy(original.payload)))=='STALE'
            await feedback()
            assert observed[-1]=='APPLIED'
            assert await consumer.submit(Event('ACTION_FEEDBACK',deepcopy(original.payload)))=='STALE'
            await consumer.submit(Event('ACTION_RESULT',dict(robot_id='r1',task_id=task.task_id,
                assignment_epoch=task.assignment_epoch,goal_uuid=task.goal_uuid,
                completed_epoch=task.assignment_epoch,result_status=1,error_reason='')))
            before = {t:rows(consumer,t) for t in ('tasks','robots','outbox_events')}
            await feedback()
            assert observed[-1]=='STALE'
            assert {t:rows(consumer,t) for t in before}==before
            assert rows(consumer,'tasks')[0]['status']=='COMPLETED'
    asyncio.run(scenario())


@pytest.mark.parametrize('change',[
    {'unexpected_critical':True}, {'current_phase':False}, {'current_phase':99},
    {'distance_to_goal':float('nan')}, {'battery_soc':101.}, {'assignment_epoch':True},
    {'status_seq':0}, {'status_seq':1.5}, {'battery_soc':'99'},
])
def test_invalid_feedback_rolls_back_and_logs_context(tmp_path,caplog,change):
    async def scenario():
        async with pipeline(tmp_path) as (consumer,task,feedback,observed,errors,events,clock):
            await feedback()
            payload={**events[0].payload,'status_seq':2,**change}
            before = {t:rows(consumer,t) for t in ('tasks','robots','outbox_events','processed_events')}
            with pytest.raises(ValueError):
                await consumer.submit(Event('ACTION_FEEDBACK',payload))
            assert {t:rows(consumer,t) for t in before}==before
            assert 'EVENT_REJECTED kind=ACTION_FEEDBACK robot=r1 task=t1 epoch=' in caplog.text
            assert task.goal_uuid in caplog.text
            await feedback()
            assert observed[-1]=='APPLIED'
    asyncio.run(scenario())


def test_callback_future_exception_is_observable_and_consumer_survives(tmp_path,caplog,monkeypatch):
    async def scenario():
        async with pipeline(tmp_path) as (consumer,task,feedback,observed,errors,events,clock):
            original = FleetManagerCore.handle_action_feedback
            def broken(*args,**kwargs):
                raise RuntimeError('injected-domain-failure')
            monkeypatch.setattr(FleetManagerCore,'handle_action_feedback',broken)
            before=rows(consumer,'outbox_events')
            await feedback()
            assert errors and not observed
            assert rows(consumer,'tasks')[0]['status']=='ASSIGNED'
            assert rows(consumer,'outbox_events')==before
            assert 'CALLBACK_REJECTED kind=ACTION_FEEDBACK robot=r1 task=t1 epoch=1' in caplog.text
            assert 'injected-domain-failure' in caplog.text and task.goal_uuid in caplog.text
            monkeypatch.setattr(FleetManagerCore,'handle_action_feedback',original)
            await feedback()
            assert observed==['APPLIED']
    asyncio.run(scenario())


def test_feedback_does_not_refresh_physical_status_or_battery(tmp_path):
    async def scenario():
        async with pipeline(tmp_path) as (consumer,task,feedback,observed,errors,events,clock):
            before=consumer.core.tracker.get_robot('r1')
            clock[0]=15.
            await feedback()
            after=consumer.core.tracker.get_robot('r1')
            assert after.is_stale(clock[0])
            assert after.last_status_received_at==before.last_status_received_at
            assert after.battery_energy_wh==before.battery_energy_wh
            assert after.pose==before.pose and after.state==before.state
    asyncio.run(scenario())
