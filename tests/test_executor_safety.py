"""Assignment evidence must survive terminal transitions and reject ambiguity."""
from dataclasses import replace
import pytest
from fleet_robot_executor.safety import ExecutorSafety, StatusOrderGuard, UINT64_MAX
from fleet_robot_executor.models import TaskResult, OdometryReading
from fleet_robot_executor.stop_detector import StopDetector


def opened(capacity=2):
    safety = ExecutorSafety(capacity)
    safety.blocked = False  # Explicit isolated test reset evidence.
    return safety


@pytest.mark.parametrize('capacity', [None, 0, -1, True, 1.5])
def test_capacity_has_no_implicit_default(capacity):
    with pytest.raises(ValueError):
        ExecutorSafety(capacity)


def test_restart_changes_session_and_blocks_admission():
    old = opened()
    assert old.admit(('task', 7, 'uuid'), b'payload')
    restarted = ExecutorSafety(2)
    assert restarted.session_id != old.session_id
    assert not restarted.admit(('task', 7, 'uuid'), b'payload')
    assert restarted.next_status() == 1


def test_sequence_does_not_wrap():
    safety = opened()
    assert [safety.next_status(), safety.next_status()] == [1, 2]
    safety.status_seq = UINT64_MAX - 1
    assert safety.next_status() == UINT64_MAX
    assert safety.next_status() is None
    assert safety.blocked
    assert not safety.admit(('task', 1, 'uuid'), b'')


def test_old_duplicate_and_changed_sessions_cannot_update_state():
    safety = opened()
    guard = StatusOrderGuard(safety.session_id.bytes)
    assert guard.accept(safety.session_id.bytes, 2)
    assert not guard.accept(safety.session_id.bytes, 1)
    assert not guard.accept(safety.session_id.bytes, 2)
    assert guard.accept(safety.session_id.bytes, 3)
    assert not guard.accept(ExecutorSafety(2).session_id.bytes, 1)
    assert not guard.accept(safety.session_id.bytes, 4)
    assert guard.blocked


def test_duplicate_active_terminal_and_changed_payload_never_execute_twice():
    safety = opened()
    identity = ('task', 7, 'uuid')
    payload = bytearray(b'original')
    assert safety.admit(identity, payload)
    payload[0] = 0
    assert safety.records[identity].payload == b'original'
    assert not safety.admit(identity, b'original')
    assert not safety.admit(identity, b'changed')
    result = TaskResult(1, 7, 10.)
    assert safety.finish(identity, b'original', result)
    assert not safety.admit(identity, b'original')
    assert not safety.admit(('task', 7, 'different-uuid'), b'original')
    assert not safety.admit(('other', 8, 'uuid'), b'original')
    assert safety.admit(('task', 8, 'new-uuid'), b'new assignment')
    assert not safety.admit(('other', 9, 'another-uuid'), b'full')
    assert len(safety.records) == 2


@pytest.mark.parametrize('identity,payload,epoch', [
    (('task', 7, 'wrong'), b'payload', 7),
    (('task', 7, 'uuid'), b'changed', 7),
    (('task', 7, 'uuid'), b'payload', 8),
])
def test_bad_terminal_evidence_keeps_active_record(identity, payload, epoch):
    safety = opened()
    key = ('task', 7, 'uuid')
    safety.admit(key, b'payload')
    assert not safety.finish(identity, payload, TaskResult(1, epoch, 10.))
    assert safety.records[key].terminal is None
    assert safety.blocked


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_motion_cannot_prove_stopped(value):
    odom = OdometryReading(10., value, 0.)
    assert not StopDetector.verify_stopped(odom, 10.)[0]
    assert not StopDetector.verify_stopped(replace(odom, linear_velocity=0., timestamp_sec=value),10.)[0]
