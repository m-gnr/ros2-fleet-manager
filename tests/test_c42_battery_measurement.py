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
