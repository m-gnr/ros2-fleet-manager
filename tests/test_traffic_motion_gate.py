"""No ROS processes: fake velocity source, fake actuator and synthetic evidence only."""
from copy import deepcopy
from pathlib import Path
import sys
from uuid import uuid4
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ros2_ws/src/fleet_robot_executor'))
from fleet_robot_executor.motion_gate import TrafficMotionGate, boundary_digest


class FakeProducer:
    name = 'fake-smoother'
    command = (.1, 0., 0., 0., 0., .1)


class FakeActuator:
    """Models last-command retention when no independent watchdog exists."""
    def __init__(self):
        self.velocity = (0.,) * 6

    def receive(self, command):
        self.velocity = command


def fixture(applied=True):
    uid = lambda: str(uuid4())
    now = [10.]
    gate = TrafficMotionGate(clock=lambda: now[0], producer=FakeProducer.name)
    r = dict(request_id=uid(), robot_id='r1', task_id='t1', epoch=1, execute_uuid=uid(), child_uuid=uid(),
             executor_session=uid(), path_hash='digest', map_revision='m1', geometry_revision='g1', frame='map',
             movement_kind='PICKUP', station_id='', geometry_digest=boundary_digest(((-1., -1., 2., 2.),)))
    gate.prepare(r, 2.)
    identity = {k: v for k, v in r.items() if k not in ('request_id', 'movement_kind', 'station_id', 'geometry_digest')}
    identity.update(permit_id=uid(), fm_session=uid(), generation=1)
    decision = dict(identity=identity, request_id=r['request_id'], movement_kind='PICKUP', station_id='',
                    geometry_digest=boundary_digest(((-1., -1., 2., 2.),)), committed=True, movement_authorized=False, status='RESERVED')
    assert gate.receive(decision)
    context = {k: deepcopy(decision[k]) for k in ('identity', 'movement_kind', 'station_id')}
    if applied:
        assert gate.apply_local(context=context, regions=((-1., -1., 2., 2.),), geometry_digest=boundary_digest(((-1., -1., 2., 2.),)))
    evidence = {s: dict(received=10., source_age=0., budget=.5, valid=True)
                for s in ('pose', 'tf', 'observation', 'velocity', 'clock')}
    evidence.update(tf_at_measurement=True, all_required_measurements_used=True,
                    footprint=((0., 0., .2, .2),), stop_tube=((0., 0., .5, .5),))
    return gate, context, evidence, now, decision


def check(gate, context=None, evidence=None, producer=FakeProducer.name):
    output = gate.filter_velocity(FakeProducer.command, producer=producer, context=context, evidence=evidence)
    actuator = FakeActuator()
    actuator.receive(output.velocity)
    assert actuator.velocity == (0.,) * 6
    assert output.stop_requested and output.physical_stop == 'UNKNOWN' and not output.ownership_release
    return output.reasons


def test_no_permit():
    assert 'NO_LIVE_PERMIT' in check(TrafficMotionGate(clock=lambda: 10., producer=FakeProducer.name))


def test_no_applied_ack():
    g, c, e, _, _ = fixture(False)
    assert 'NO_LOCAL_APPLIED_ACK' in check(g, c, e)


@pytest.mark.parametrize('field,value', [('epoch', 2), ('child_uuid', str(uuid4())),
    ('execute_uuid', str(uuid4())), ('generation', 2), ('path_hash', 'other'),
    ('executor_session', str(uuid4())), ('fm_session', str(uuid4())), ('task_id', 'other')])
def test_context_fences(field, value):
    g, c, e, _, d = fixture()
    c['identity'][field] = value
    assert 'MOVEMENT_CONTEXT_MISMATCH' in check(g, c, e)
    assert not g.receive(d)


def test_session_change_cannot_reopen():
    g, c, e, _, d = fixture()
    old_ack = deepcopy(g.applied)
    g.session_changed()
    assert 'SESSION_CHANGED' in check(g, c, e)
    assert not g.receive(d) and not g.applied_ack(old_ack)
    with pytest.raises(ValueError):
        g.prepare(g.request, 2.)


@pytest.mark.parametrize('source', ['pose', 'tf', 'observation', 'velocity', 'clock'])
def test_stale_source(source):
    g, c, e, _, _ = fixture()
    e[source]['source_age'] = .5
    assert 'STALE_OR_UNKNOWN_' + source.upper() in check(g, c, e)


def test_revoke_late_ack_and_ownership_untouched():
    g, c, e, _, d = fixture()
    owner = deepcopy(c)  # No gate API has an ownership store/release capability.
    ack = deepcopy(g.applied)
    g.revoke()
    assert not g.applied_ack(ack) and not g.receive(d)
    assert 'NO_LIVE_PERMIT' in check(g, c, e)
    assert c == owner


def test_restart_closed_and_old_ack_rejected():
    old, c, e, _, _ = fixture()
    new = TrafficMotionGate(clock=lambda: 10., producer=FakeProducer.name)
    assert old.local_session != new.local_session
    assert not new.applied_ack(old.applied)
    assert 'NO_LIVE_PERMIT' in check(new, c, e)


def test_alternative_source_and_direct_actuator_bypass():
    g, c, e, _, d = fixture()
    assert 'BYPASS_DETECTED' in check(g, c, e, producer='teleop')
    assert not g.receive(d)
    actuator = FakeActuator()
    actuator.receive(FakeProducer.command)
    assert actuator.velocity != (0.,) * 6  # Direct downstream write bypasses any Python gate.


@pytest.mark.parametrize('field,reason', [('stop_tube', 'PREDICTED_BOUNDARY_BREACH'),
                                        ('footprint', 'ZONE_VIOLATION')])
def test_boundary_alarm_and_latch(field, reason):
    g, c, e, _, d = fixture()
    e[field] = ((1.9, 0., 2.1, .2),)
    assert reason in check(g, c, e)
    assert not g.receive(d)


def test_cut_output_does_not_stop_last_command_actuator():
    actuator = FakeActuator()
    actuator.receive(FakeProducer.command)  # Prior command, not emitted by TrafficMotionGate.
    g, c, e, _, _ = fixture()
    out = g.filter_velocity(FakeProducer.command, producer=FakeProducer.name, context=c, evidence=e)
    # Simulate gate death / lost bridge: its zero never reaches the actuator.
    assert out.physical_stop == 'UNKNOWN' and actuator.velocity == FakeProducer.command
    actuator.receive(out.velocity)
    assert actuator.velocity == (0.,) * 6  # Target zero alone is still not physical stop proof.


def test_complete_fixture_still_never_enables_nonzero():
    g, c, e, _, _ = fixture()
    assert check(g, c, e) == ('PHYSICAL_FAIL_SAFE_UNQUALIFIED', 'NONZERO_DISABLED')


def test_deadline_not_refreshed_by_duplicate():
    g, c, e, now, d = fixture()
    now[0] = 12.
    assert not g.receive(d)
    assert 'NO_LIVE_PERMIT' in check(g, c, e)


def test_region_union_gap_is_not_authorized():
    g, c, e, _, _ = fixture(False)
    regions = ((-1., -1., .1, 2.), (.2, -1., 2., 2.))
    g.decision['geometry_digest'] = boundary_digest(regions)  # Synthetic committed gap fixture.
    assert g.apply_local(context=c, regions=regions, geometry_digest=boundary_digest(regions))
    assert 'PREDICTED_BOUNDARY_BREACH' in check(g, c, e)


def test_external_ack_cannot_replace_local_binding():
    g, c, e, _, _ = fixture(False)
    ack = {k: deepcopy(g.decision[k]) for k in ('identity', 'request_id', 'geometry_digest', 'movement_kind', 'station_id')}
    ack.update(kind='APPLIED', local_binding_id=str(uuid4()))
    assert not g.applied_ack(ack)
    assert 'NO_LOCAL_APPLIED_ACK' in check(g, c, e)


@pytest.mark.parametrize('kind', ['PICKUP', 'DROPOFF', 'PARK', 'CHARGE'])
def test_movement_kinds_remain_closed(kind):
    g, c, e, _, _ = fixture(False)
    g.decision['movement_kind'] = c['movement_kind'] = kind
    assert g.apply_local(context=c, regions=((-1., -1., 2., 2.),), geometry_digest=g.decision['geometry_digest'])
    assert 'NONZERO_DISABLED' in check(g, c, e)


def test_changed_geometry_cannot_use_old_digest():
    g, c, e, _, _ = fixture(False)
    assert g.apply_local(context=c, regions=((-1., -1., 3., 3.),), geometry_digest=g.decision['geometry_digest']) is None
    assert 'NO_LIVE_PERMIT' in check(g, c, e)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), None, 'unknown'])
def test_invalid_velocity_fails_closed(value):
    g, c, e, _, _ = fixture()
    out = g.filter_velocity((value, 0., 0., 0., 0., 0.), producer=FakeProducer.name, context=c, evidence=e)
    assert out.velocity == (0.,) * 6 and 'INVALID_VELOCITY' in out.reasons


def test_missing_health_and_future_pose_fails_closed():
    g, c, e, _, _ = fixture()
    del e['observation']
    e['pose']['received'] = 11.
    e['all_required_measurements_used'] = False
    reasons = check(g, c, e)
    assert 'STALE_OR_UNKNOWN_OBSERVATION' in reasons and 'STALE_OR_UNKNOWN_POSE' in reasons
    assert 'UNQUALIFIED_OBSERVATION' in reasons



def test_stale_footprint_is_not_reported_as_actual_violation():
    g, c, e, _, _ = fixture()
    e['pose'] = None
    e['footprint'] = ((3., 3., 4., 4.),)
    reasons = check(g, c, e)
    assert 'BOUNDARY_OBSERVATION_UNKNOWN' in reasons and 'ZONE_VIOLATION' not in reasons


def test_local_application_copies_and_duplicate_is_idempotent():
    g, c, e, _, _ = fixture(False)
    ack = g.apply_local(context=c, regions=((-1., -1., 2., 2.),), geometry_digest=g.decision['geometry_digest'])
    assert g.apply_local(context=c, regions=((-1., -1., 2., 2.),), geometry_digest=g.decision['geometry_digest']) == ack
    ack['identity']['generation'] = 100
    assert g.applied['identity']['generation'] == 1
    assert 'NONZERO_DISABLED' in check(g, c, e)
