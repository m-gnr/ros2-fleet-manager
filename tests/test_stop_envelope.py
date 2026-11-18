"""Conditional arithmetic fixtures only; no physical braking measurements."""
from dataclasses import replace
import math
import pytest
from backend.fleet_manager.domain.stop_envelope import StopInputs, stop_envelope, reservation_check, relative_stop_check
from backend.fleet_manager.domain.traffic import Box


def inputs():
    return StopInputs(1.,2.,.5,1.,.1,.1,.1,.1,.05,.02,.03,.1,'a'*64)


def envelope(**kwargs):
    args=dict(x=0.,y=0.,linear_speed=1.,angular_speed=-.5,footprint_radius=.3,inputs=inputs())
    args.update(kwargs);return stop_envelope(**args)


def test_missing_real_calibration_remains_unbounded_at_zero_speed():
    r=envelope(linear_speed=0.,angular_speed=0.,inputs=StopInputs())
    assert r['status']=='UNBOUNDED' and r['tube'] is None and not r['qualified']
    assert 'linear_deceleration_m_s2' in r['missing'] and 'actuator_sec' in r['missing']


def test_acceleration_delay_braking_uncertainty_and_footprint_all_count():
    r=envelope();delay=.4;v=1.02;v1=v+.5*delay
    expected=v*delay+.5*.5*delay**2+v1*v1/2
    assert r['distance_m']==pytest.approx(expected)
    assert r['radius_m']==pytest.approx(.3+.05+.1+expected)
    assert not r['qualified'] and not r['movement_authorized'] and not r['ownership_release']
    assert r['tube'][0]['x0']==-r['radius_m']


@pytest.mark.parametrize('field',['linear_deceleration_m_s2','actuator_sec','position_error_m','margin_m','speed_error_m_s'])
@pytest.mark.parametrize('bad',[None,-1.,math.nan,math.inf])
def test_bad_or_missing_bound_never_becomes_finite_tube(field,bad):
    r=envelope(inputs=replace(inputs(),**{field:bad}));assert r['tube'] is None


def test_nonpositive_braking_invalid_and_negative_angular_speed_supported():
    assert envelope(inputs=replace(inputs(),linear_deceleration_m_s2=0.))['tube'] is None
    assert envelope()['angle_rad']>0
    assert envelope(linear_speed=-1.)['tube'] is None


def test_exact_b6b_union_containment_does_not_jump_gaps():
    r=envelope();radius=r['radius_m']
    assert reservation_check(r,[Box(-radius,-radius,radius,radius)])['status']=='CANDIDATE_INSIDE'
    assert reservation_check(r,[Box(-2.,-2.,-.01,2.),Box(.01,-2.,2.,2.)])['status']=='PREDICTED_BOUNDARY_BREACH'
    assert reservation_check(envelope(inputs=StopInputs()),[])['status']=='UNKNOWN_STOP_TUBE'


def test_relative_motion_adds_both_robots_tubes_and_unknown_peer_is_unknown():
    a,b=envelope(),envelope(x=1.)
    assert relative_stop_check(a,b)['status']=='POTENTIAL_CONFLICT'
    assert relative_stop_check(a,envelope(x=20.))['status']=='CANDIDATES_DISJOINT'
    assert relative_stop_check(a,envelope(inputs=StopInputs()))['status']=='UNKNOWN_RELATIVE_OCCUPANCY'


def test_large_finite_inputs_fail_closed_without_overflow_or_bounded_claim():
    assert envelope(linear_speed=1.e308)['tube'] is None
    assert envelope(inputs=replace(inputs(),actuator_sec=1.e308))['tube'] is None
