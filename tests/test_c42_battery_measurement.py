"""Validation of individual C4.2 samples without a ROS runtime."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from fleet_robot_executor.battery import BatteryTelemetry

NS = 10**9


def measurement(**changes):
    return SimpleNamespace(**{
        "robot_id": "robot",
        "publisher_session_id": SimpleNamespace(uuid=uuid4().bytes),
        "battery_stamp": SimpleNamespace(sec=10, nanosec=0),
        "battery_energy_wh": 75.0,
        "battery_capacity_wh": 100.0,
        "battery_soc_percent": 75.0,
        "is_charging": False,
        "control_request_id": "",
        **changes,
    })


@pytest.mark.parametrize("changes", [
    {"robot_id": "other"},
    {"battery_energy_wh": -1.0},
    {"battery_energy_wh": 100.1},
    {"battery_energy_wh": float("nan")},
    {"battery_energy_wh": float("inf")},
    {"battery_capacity_wh": 0.0},
    {"battery_capacity_wh": -1.0},
    {"battery_capacity_wh": float("inf")},
    {"battery_capacity_wh": float("nan")},
    {"battery_capacity_wh": 150.0, "battery_soc_percent": 50.0},
    {"battery_soc_percent": -1.0},
    {"battery_soc_percent": 100.01},
    {"battery_soc_percent": float("nan")},
    {"battery_soc_percent": float("inf")},
    {"battery_soc_percent": 75.001},
    {"battery_stamp": SimpleNamespace(sec=10, nanosec=1)},  # Future.
    {"battery_stamp": SimpleNamespace(sec=7, nanosec=0)},  # Expired.
    {"battery_stamp": SimpleNamespace(sec=9, nanosec=NS)},  # Invalid ROS time.
    {"battery_stamp": SimpleNamespace(sec=0, nanosec=0)},
    {"publisher_session_id": SimpleNamespace(uuid=bytes(16))},
])
def test_invalid_measurement_does_not_establish_freshness(changes):
    battery = BatteryTelemetry("robot", 100.0)
    assert not battery.observe(measurement(**changes), 10 * NS, 1.0)
    assert not battery.fresh_stamp(10 * NS, 1.0)
    assert battery.session_id is None


def test_delayed_sample_does_not_replace_or_refresh_current_measurement():
    battery = BatteryTelemetry("robot", 100.0)
    sample = measurement()
    assert battery.observe(sample, 10 * NS, 1.0)
    assert not battery.observe(sample, 11 * NS, 2.0)
    sample.battery_stamp.sec = 9
    assert not battery.observe(sample, 11 * NS, 2.0)
    assert battery.fresh_stamp(10 * NS, 3.1) == 0
    assert battery.fresh_stamp(13 * NS, 2.0) == 0


@pytest.mark.parametrize("charging", [True, False])
def test_unexplained_energy_increase_fences_current_source(charging):
    battery = BatteryTelemetry("robot", 100.0)
    sample = measurement()
    assert battery.observe(sample, 10 * NS, 1.0)
    sample.battery_stamp.sec = 11
    sample.is_charging = charging
    sample.battery_soc_percent = sample.battery_energy_wh = 100.0
    assert not battery.observe(sample, 11 * NS, 1.5)
    sample.battery_soc_percent = sample.battery_energy_wh = 74.0
    assert not battery.observe(sample, 11 * NS, 1.5)
    assert battery.energy_wh == 75.0
    assert battery.fresh_stamp(11 * NS, 1.5) == 0


def test_authorized_control_sample_is_one_shot_and_resets_continuity_baseline():
    from uuid import uuid4

    battery = BatteryTelemetry("robot", 100.0)
    session = uuid4()
    first = measurement(publisher_session_id=SimpleNamespace(uuid=session.bytes))
    assert battery.observe(first, 10 * NS, 1.0)
    request_id = str(uuid4())
    proof = SimpleNamespace(
        robot_id="robot", control_session_id=str(session), request_id=request_id,
        applied_soc_percent=100.0, applied_energy_wh=100.0, capacity_wh=100.0,
        revision=1, applied_stamp=SimpleNamespace(sec=11, nanosec=0),
    )
    assert battery.authorize_control(proof, 11 * NS, 1.1)
    controlled = measurement(
        publisher_session_id=SimpleNamespace(uuid=session.bytes),
        battery_stamp=SimpleNamespace(sec=11, nanosec=0),
        battery_energy_wh=100.0, battery_soc_percent=100.0,
        control_request_id=request_id,
    )
    assert battery.observe(controlled, 11 * NS, 1.2)
    assert battery.energy_wh == 100.0
    assert not battery.authorize_control(proof, 12 * NS, 1.3)  # request replay
    down = measurement(
        publisher_session_id=SimpleNamespace(uuid=session.bytes),
        battery_stamp=SimpleNamespace(sec=12, nanosec=0),
        battery_energy_wh=20.0, battery_soc_percent=20.0,
    )
    assert battery.observe(down, 12 * NS, 1.3)


def test_control_marker_without_explicit_attestation_is_rejected():
    battery = BatteryTelemetry("robot", 100.0)
    first = measurement()
    assert battery.observe(first, 10 * NS, 1.0)
    controlled = measurement(
        battery_stamp=SimpleNamespace(sec=11, nanosec=0),
        battery_energy_wh=100.0, battery_soc_percent=100.0,
        control_request_id="forged",
    )
    assert not battery.observe(controlled, 11 * NS, 1.1)
    assert battery.blocked_reason


@pytest.mark.parametrize("changes,sim_ns", [
    ({"robot_id": "other"}, 11 * NS),
    ({"request_id": ""}, 11 * NS),
    ({"applied_stamp": SimpleNamespace(sec=8, nanosec=0)}, 11 * NS),
    ({"applied_soc_percent": 99.0}, 11 * NS),
    ({"control_session_id": str(uuid4())}, 11 * NS),
])
def test_invalid_control_attestation_cannot_authorize(changes, sim_ns):
    from uuid import uuid4

    battery = BatteryTelemetry("robot", 100.0)
    session = uuid4()
    first = measurement(publisher_session_id=SimpleNamespace(uuid=session.bytes))
    assert battery.observe(first, 10 * NS, 1.0)
    proof_values = dict(
        robot_id="robot", control_session_id=str(session), request_id=str(uuid4()),
        applied_soc_percent=100.0, applied_energy_wh=100.0, capacity_wh=100.0,
        revision=1, applied_stamp=SimpleNamespace(sec=11, nanosec=0),
    )
    proof_values.update(changes)
    proof = SimpleNamespace(**proof_values)
    assert not battery.authorize_control(proof, sim_ns, 1.1)
