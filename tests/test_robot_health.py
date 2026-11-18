"""Explicit synthetic unit fixtures. No physical or production health evidence."""
from copy import deepcopy
from uuid import uuid4
import json
import math
import pytest

from fleet_config import load_config
from fleet_config.native_zero import compact, sign, STATUS_DOMAIN
from backend.fleet_manager.domain.robot_health import HealthWindow, HEALTH_DOMAIN, observation_budgets, covariance_summary

KEY = b'\xab'*32


def packet(identity, *, sequence=1, sim_ns=10_000_000_000):
    status = dict(robot_id=identity['robot_id'],receiver_session='a'*64,ticket='b'*64,report_sequence=sequence,
        receiver_state='ACTIVE',source_session=identity['fm_session'],sequence=1,permit_id=identity['permit_id'],
        generation=1,context_sha256='c'*64,command_sha256='d'*64,operation='INSTALL_ZERO',
        verified_steady_ns=100,steady_ns=100+sequence,movement_authorized=False,ownership_release=False)
    health = dict(native_status=__import__('json').loads(sign(compact(status),KEY,domain=STATUS_DOMAIN)),sim_ns=sim_ns,
                  target_linear=0.,target_angular=0.,joint_commands=[[0.],[0.]],update_sequence=sequence)
    return {'native_health':json.loads(sign(compact(health),KEY,domain=HEALTH_DOMAIN))}


def ready():
    policy = load_config('config/fleet.warehouse-30x18.yaml').fleet.perception_safety
    w = HealthWindow(robot_id='r1',frames=dict(map='map',odom='r1/odom',base='r1/base_link',odom_child='r1/base_link'),
                     budgets=observation_budgets(policy),key=KEY)
    identity = dict(robot_id='r1',executor_session=str(uuid4()),fm_session=str(uuid4()),permit_id=str(uuid4()),
                    epoch=1,task_id='unit-task',generation=1,child_uuid=str(uuid4()),path_hash='f'*64)
    ctx = dict(identity=identity,context_sha256='c'*64,claim_reserved=True)
    values = {'clock':10_000_000_000,
        'odometry':dict(frame='r1/odom',child='r1/base_link',position=[0.,0.,0.],orientation=[0.,0.,0.,1.],velocity=[0.,0.,0.]),
        'amcl':dict(frame='map',position=[0.,0.,0.],orientation=[0.,0.,0.,1.],covariance=[0.]*36),
        'tf':dict(frame='map',child='r1/base_link',position=[0.,0.,0.],orientation=[0.,0.,0.,1.],at_odometry_stamp=True),
        'robot_status':dict(robot_id='r1',session=identity['executor_session'],sequence=1,epoch=1,task_id='unit-task',state=2)}
    values.update({'lifecycle:'+role:3 for role in ('amcl','controller_server','planner_server','bt_navigator')})
    for stream,value in values.items():
        assert w.receive(stream,value=value,stamp_ns=None if stream.startswith('lifecycle:') else 10_000_000_000,
                         receipt=10.,source_id=stream)
    assert w.native(packet(identity),receipt=10.)
    return w,ctx


def evaluate(w,ctx,**kwargs):
    return w.evaluate(ros_ns=kwargs.get('ros_ns',10_000_000_000),now=kwargs.get('now',10.),context=ctx,known_command=('d'*64,1))


def test_complete_fixture_remains_ineligible_and_uncalibrated():
    w,c = ready();result = evaluate(w,c)
    assert result['observations_current'] and not result['movement_eligible']
    assert result['physical_stop']=='UNKNOWN' and not result['ownership_release']
    assert result['derived']['localization']['hard_position_bound_m'] is None
    assert 'NONZERO_DISABLED' in result['qualification_blockers']


@pytest.mark.parametrize('stream',['clock','odometry','amcl','tf','robot_status','native','lifecycle:controller_server'])
def test_missing_or_old_source_cannot_be_current(stream):
    w,c=ready();w.samples.pop(stream)
    assert 'STALE_OR_UNKNOWN:'+stream in evaluate(w,c)['reasons']
    w,c=ready();w.samples[stream]['receipt']=0.
    assert not evaluate(w,c)['observations_current']


@pytest.mark.parametrize('change',['future','frame','nan','wrong_child','bad_quaternion','tf_not_at_measurement','invalid_covariance','inactive'])
def test_invalid_real_source_shapes_rejected(change):
    w,c=ready()
    if change=='future':w.samples['odometry']['stamp_ns']+=1
    if change=='frame':w.samples['odometry']['value']['frame']='other/odom'
    if change=='nan':w.samples['odometry']['value']['velocity'][0]=math.nan
    if change=='wrong_child':w.samples['tf']['value']['child']='other/base_link'
    if change=='bad_quaternion':w.samples['tf']['value']['orientation']=[0.,0.,0.,0.]
    if change=='tf_not_at_measurement':w.samples['tf']['value']['at_odometry_stamp']=False
    if change=='invalid_covariance':w.samples['amcl']['value']['covariance'][0]=-1.
    if change=='inactive':w.samples['lifecycle:controller_server']['value']=2
    assert not evaluate(w,c)['observations_current']


@pytest.mark.parametrize('field',['epoch','executor_session','fm_session','generation','permit_id','child_uuid','path_hash','context_sha256','claim_reserved'])
def test_context_and_session_fences(field):
    w,c=ready();assert evaluate(w,c)['observations_current']
    if field=='context_sha256':c[field]='e'*64
    elif field=='claim_reserved':c[field]=False
    elif field in ('epoch','generation'):c['identity'][field]+=1
    else:c['identity'][field]=str(uuid4())
    assert not evaluate(w,c)['observations_current']


def test_ros_and_native_replay_do_not_refresh_after_invalid_packet():
    w,c=ready();old=packet(c['identity'])
    assert not w.native({'native_health':{'body':'{}','mac':'wrong'}},receipt=10.1)
    assert not w.native(old,receipt=10.2)
    assert w.rejections['native']=='NATIVE_REPLAY_OR_FROZEN'
    odom=w.samples['odometry'];v=deepcopy(odom['value'])
    assert not w.receive('odometry',value=v,stamp_ns=odom['stamp_ns'],receipt=10.5,source_id='odometry')
    assert w.samples['odometry']['receipt']==10.
    w.reject('odometry','INVALID_PACKET')
    assert not w.receive('odometry',value=v,stamp_ns=odom['stamp_ns'],receipt=10.7,source_id='odometry')
    assert 'odometry' not in w.samples


def test_source_and_executor_session_changes_latch_without_recovery():
    w,c=ready();odom=w.samples['odometry']
    assert not w.receive('odometry',value=odom['value'],stamp_ns=10_100_000_000,receipt=10.1,source_id='new-publisher')
    assert 'SOURCE_CHANGED:odometry' in evaluate(w,c)['reasons']
    status=deepcopy(w.samples['robot_status']['value']);status.update(session=str(uuid4()),sequence=2)
    assert not w.receive('robot_status',value=status,stamp_ns=10_100_000_000,receipt=10.1,source_id='robot_status')
    assert 'EXECUTOR_SESSION_CHANGED' in evaluate(w,c)['reasons']


def test_clock_pause_uses_receipt_time_and_rewind_latches():
    w,c=ready();evaluate(w,c)
    assert 'STALE_OR_UNKNOWN:clock' in evaluate(w,c,now=10.5)['reasons']
    assert 'CLOCK_REWOUND' in evaluate(w,c,ros_ns=9_000_000_000)['reasons']
    assert 'CLOCK_REWOUND' in evaluate(w,c)['reasons']


@pytest.mark.parametrize('fault',['nonzero_target','missing_joint','different_command','different_session','health_domain'])
def test_signed_readback_cannot_hide_contradictions(fault):
    import json
    w,c=ready();p=packet(c['identity'],sequence=2,sim_ns=10_010_000_000)
    h=json.loads(p['native_health']['body'])
    if fault=='nonzero_target':h['target_linear']=.2
    if fault=='missing_joint':h['joint_commands']=[None]
    if fault in ('different_command','different_session'):
        s=json.loads(h['native_status']['body'])
        s['command_sha256' if fault=='different_command' else 'source_session']='e'*64
        h['native_status']=json.loads(sign(compact(s),KEY,domain=STATUS_DOMAIN))
    p['native_health']=sign(compact(h),KEY,domain=STATUS_DOMAIN if fault=='health_domain' else HEALTH_DOMAIN)
    w.native(p,receipt=10.01)
    assert not evaluate(w,c,now=10.01,ros_ns=10_010_000_000)['observations_current']


def test_covariance_is_statistical_not_a_hard_error_bound():
    c=[0.]*36;c[0]=4.;c[7]=9.;c[35]=.25
    r=covariance_summary(c);assert r['xy_max_sigma_m']==3. and r['yaw_sigma_rad']==.5
    assert r['hard_position_bound_m'] is None
    c[1]=4.;c[6]=0.
    with pytest.raises(ValueError):covariance_summary(c)


def test_covariance_failure_does_not_hide_native_or_executor_observation():
    w,c=ready();w.samples['amcl']['value']['covariance'][0]=-1.
    result=evaluate(w,c)
    assert not result['observations_current'] and result['measured']['native'] and result['measured']['robot_status']


def test_new_status_sequence_can_share_publisher_time_without_refreshing_measurement_time():
    w,c=ready();status=deepcopy(w.samples['robot_status']['value']);status['sequence']=2
    assert w.receive('robot_status',value=status,stamp_ns=10_000_000_000,receipt=10.2,source_id='robot_status')
    result=evaluate(w,c,now=10.2,ros_ns=10_200_000_000)
    assert 'SOURCE_ORDER:robot_status' not in result['reasons']
    assert result['source_ages']['robot_status']['source_age_sec']==.2
    assert not w.receive('robot_status',value=status,stamp_ns=10_200_000_000,receipt=10.3,source_id='robot_status')


def test_covariance_overflow_stays_unknown():
    c=[0.]*36;c[0]=c[7]=c[35]=1.e308
    with pytest.raises(ValueError):covariance_summary(c)


def test_report_is_detached_from_accepted_measurements():
    w,c=ready();result=evaluate(w,c);result['measured']['odometry']['velocity'][0]=.5
    assert w.samples['odometry']['value']['velocity'][0]==0.


def test_unsigned_outer_readback_conflict_closes_observation_without_ack_upgrade():
    w,c=ready();p=packet(c['identity'],sequence=2,sim_ns=10_010_000_000);p['target_linear']=.5
    assert not w.native(p,receipt=10.01)
    assert w.rejections['native']=='NATIVE_READBACK_CONFLICT'
    assert not evaluate(w,c)['observations_current']


def test_closed_permit_cannot_be_reopened_by_a_later_positive_claim_snapshot():
    w,c=ready();assert evaluate(w,c)['observations_current']
    c['claim_reserved']=False;assert 'PERMIT_CLOSED' in evaluate(w,c)['reasons']
    c['claim_reserved']=True;assert not evaluate(w,c)['observations_current']
