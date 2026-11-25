"""Explicit synthetic component fixtures, never physical health/stop evidence."""
from copy import deepcopy
import json
import pytest

from fleet_config.native_zero import sign,compact,verify,STATUS_DOMAIN
from backend.fleet_manager.domain.split_health import SplitHealthWindow,READBACK_DOMAIN
from test_robot_health import ready as legacy_ready,packet,KEY


def fixture():
    old,context=legacy_ready()
    w=SplitHealthWindow(robot_id=old.robot_id,frames=old.frames,budgets=old.budgets,key=KEY,
        observations={'local':['scan']},scan_budget=.5)
    w.samples=deepcopy(old.samples);w.cursors=deepcopy(old.cursors);w.pins=deepcopy(old.pins)
    w.status_session=old.status_session;w.status_sequence=old.status_sequence
    status=verify(packet(context['identity'])['native_health'],KEY,domain=b'C5_NATIVE_ZERO_HEALTH_V1\n')['native_status']
    writer=dict(writer_boot='a'*64,native_session='a'*64,context_sha256='c'*64,command_sha256='d'*64,
        command_sequence=1,physics_steps=1,iteration=1,sim_ns=10_000_000_000,selected=[0.,0.],joint_velocity=[0.,0.],
        body_velocity=[0.]*6,velocity_known=True,latched=False,health_ticket=1)
    value=dict(robot_id=w.robot_id,native_status=status,writer=writer,movement_authorized=False,ownership_release=False)
    signed=json.loads(sign(compact(value),KEY,domain=READBACK_DOMAIN))
    w.native_progress=None;w.samples.pop('native');w.cursors.pop('native')
    assert w.native(dict(native_status=status,split_readback=signed),receipt=10.)
    assert w.observation('local',dict(session='layer1',sequence=1,processed_ns=10_000_000_000,
        topics=['scan'],stamps=[10_000_000_000],used=[True]),receipt=10.,source='UNKNOWN_GRAPH_SET')
    context['writer_command']=['d'*64,1]
    return w,context,value


def evaluate(w,c,now=10.,ros=10_000_000_000):
    return w.evaluate(now=now,ros_ns=ros,context=c,known_command=('d'*64,1))


def test_current_sources_and_real_shape_readback_only_clear_a_veto():
    w,c,_=fixture();result=evaluate(w,c)
    assert result['observations_current'] and not result['movement_eligible']
    assert result['physical_stop']=='UNKNOWN' and not result['ownership_release']
    wire=w.veto_packet(result,context=c,observer_session='e'*64,sequence=1,ros_ns=10_000_000_000,now=10.)
    p=verify(wire,KEY,domain=b'C5_HEALTH_VETO_V1\n')
    assert p['observations_current'] and p['remaining_ns']<=350_000_000
    assert all(v['source_identity']=='UNKNOWN' for v in p['sources'].values())


@pytest.mark.parametrize('stream',['tf','odometry','amcl','lifecycle:controller_server','observation:local','native'])
def test_missing_or_stale_source_vetoes(stream):
    w,c,_=fixture();w.samples.pop(stream)
    assert not evaluate(w,c)['observations_current']
    w,c,_=fixture();w.samples[stream]['receipt']=0.
    assert not evaluate(w,c)['observations_current']


@pytest.mark.parametrize('field',['writer_boot','native_session','context_sha256','selected','velocity_known','latched','body_velocity'])
def test_conflicting_writer_readback_cannot_clear(field):
    w,c,value=fixture();value=deepcopy(value);value['writer']['physics_steps']=2;value['writer']['iteration']=2;value['writer']['sim_ns']+=1
    change={'writer_boot':'f'*64,'native_session':'f'*64,'context_sha256':'f'*64,'selected':[1.,0.],
            'velocity_known':False,'latched':True,'body_velocity':[float('nan')]*6}[field]
    value['writer'][field]=change
    if field=='body_velocity':
        w.samples['native']['value']['writer'][field]=change
    else:
        signed=json.loads(sign(compact(value),KEY,domain=READBACK_DOMAIN))
        w.native(dict(native_status=value['native_status'],split_readback=signed),receipt=10.0001)
    assert not evaluate(w,c)['observations_current']


def test_processed_observation_sequence_does_not_refresh_old_measurements():
    w,c,_=fixture();v=dict(session='layer1',sequence=2,processed_ns=10_600_000_000,
        topics=['scan'],stamps=[10_000_000_000],used=[True])
    assert w.observation('local',v,receipt=10.6,source='UNKNOWN_GRAPH_SET')
    assert 'OBSERVATION_UNUSED_OR_OLD:local' in evaluate(w,c,10.6,10_600_000_000)['reasons']


def test_repeated_layer_evaluation_time_is_not_a_new_sensor_measurement():
    w,c,_=fixture();original=w.samples['observation:local']['receipt']
    assert w.observation('local',dict(session='layer1',sequence=2,processed_ns=10_000_000_000,
        topics=['scan'],stamps=[10_000_000_000],used=[True]),receipt=10.1,source='UNKNOWN_GRAPH_SET')
    assert not w.fences and w.samples['observation:local']['receipt']==original
    assert not evaluate(w,c,10.51,10_510_000_000)['observations_current']


def test_one_buffer_update_cannot_refresh_another_buffers_receipt():
    w,c,_=fixture();stream='observation:local';w.observations['local']=['front','rear']
    for records in (w.samples,w.cursors,w.pins):records.pop(stream)
    w.layer_order.clear();w.layer_receipts.clear()
    for sequence,now,stamps in [(1,10.,[10_000_000_000]*2),(2,10.4,[10_400_000_000,10_000_000_000])]:
        assert w.observation('local',dict(session='layer1',sequence=sequence,processed_ns=int(now*1e9),
            topics=['front','rear'],stamps=stamps,used=[True,True]),receipt=now,source='UNKNOWN_GRAPH_SET')
    assert w.samples[stream]['receipt']==10.
    assert 'OBSERVATION_UNUSED_OR_OLD:local' in evaluate(w,c,10.51,10_510_000_000)['reasons']


@pytest.mark.parametrize('field',['physics_steps','iteration','health_ticket','latched','velocity_known'])
def test_signed_readback_requires_exact_numeric_and_boolean_types(field):
    w,_,value=fixture();value['writer'][field]=True if field not in ('latched','velocity_known') else 1
    signed=json.loads(sign(compact(value),KEY,domain=READBACK_DOMAIN))
    assert not w.native(dict(native_status=value['native_status'],split_readback=signed),receipt=10.01)
    assert w.rejections['native']=='SPLIT_READBACK_INVALID'


def test_duplicate_measurement_never_renews_packet_remaining_budget():
    w,c,_=fixture();a=evaluate(w,c)
    first=verify(w.veto_packet(a,context=c,observer_session='e'*64,sequence=1,ros_ns=10_000_000_000,now=10.),KEY,domain=b'C5_HEALTH_VETO_V1\n')
    w.observation('local',dict(session='layer1',sequence=2,processed_ns=10_100_000_000,
        topics=['scan'],stamps=[10_000_000_000],used=[True]),receipt=10.1,source='UNKNOWN_GRAPH_SET')
    b=evaluate(w,c,10.1,10_100_000_000)
    second=verify(w.veto_packet(b,context=c,observer_session='e'*64,sequence=2,ros_ns=10_100_000_000,now=10.1),KEY,domain=b'C5_HEALTH_VETO_V1\n')
    assert second['remaining_ns']<first['remaining_ns']
    assert second['sources']['observation:local']['measurement_id']==first['sources']['observation:local']['measurement_id']


@pytest.mark.parametrize('kind',['wrong_writer_command','closed_context','changed_epoch','changed_child','changed_session','unused_observation','new_layer'])
def test_closed_or_wrong_context_and_observation_remain_vetoed(kind):
    w,c,_=fixture();assert evaluate(w,c)['observations_current']
    if kind=='wrong_writer_command':c['writer_command']=['f'*64,2]
    if kind=='closed_context':c['claim_reserved']=False
    if kind=='changed_epoch':c['identity']['epoch']+=1
    if kind=='changed_child':c['identity']['child_uuid']='other'
    if kind=='changed_session':c['identity']['executor_session']='other'
    if kind=='unused_observation':w.samples['observation:local']['value']['used']=[False]
    if kind=='new_layer':w.observation('local',dict(session='new',sequence=1,processed_ns=10_100_000_000,topics=['scan'],stamps=[10_100_000_000],used=[True]),receipt=10.1,source='UNKNOWN_GRAPH_SET')
    assert not evaluate(w,c)['observations_current']
