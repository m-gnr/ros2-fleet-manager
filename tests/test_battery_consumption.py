import pytest
from pydantic import ValidationError

from fleet_battery_simulator.consumption import BatteryConsumption, OdometrySample
from fleet_config.models import BatteryModel

SECOND = 10**9
STEP = SECOND // 4


def model(**overrides):
    return BatteryModel.model_validate({
        "usable_capacity_wh": 100.0,
        "consumption_wh_per_meter": 0.2,
        "idle_power_w": 2.0,
        "charge_power_w": 20.0,
    } | overrides)


def odom(stamp, x=0.0, *, frame="odom", linear_speed=0.5, angular_speed=0.0):
    return OdometrySample(stamp, (frame, "base_link"), (x, 0.0, 0.0), linear_speed, angular_speed)


def test_full_initial_capacity_and_first_samples():
    battery = BatteryConsumption(model())
    battery.observe_odometry(odom(0, -4.0))
    assert battery.clock_ns is None
    battery.update_clock(50 * SECOND)
    battery.observe_odometry(odom(50 * SECOND, 19.0))
    battery.update_clock(50 * SECOND + 1)
    assert battery.capacity_wh == 100.0
    assert battery.remaining_wh == pytest.approx(100.0)
    assert battery.soc_percent == pytest.approx(100.0)


@pytest.mark.parametrize("idle_power", [0.0, 2.0])
def test_ten_metres_and_continuous_base_load(idle_power):
    battery = BatteryConsumption(model(idle_power_w=idle_power))
    battery.update_clock(0)
    for step in range(81):
        # Deliver odometry just before the matching clock to exercise DDS reordering.
        battery.observe_odometry(odom(step * STEP, 0.125 * step))
        battery.update_clock(step * STEP)
    assert battery.remaining_wh == pytest.approx(100.0 - 2.0 - idle_power * 20 / 3600)


def test_one_simulated_hour_without_odometry():
    battery = BatteryConsumption(model())
    battery.update_clock(10 * SECOND)
    battery.update_clock(3610 * SECOND)
    assert battery.remaining_wh == pytest.approx(98.0)


def test_pause_then_resume():
    battery = BatteryConsumption(model())
    battery.update_clock(0)
    battery.observe_odometry(odom(0))
    battery.observe_odometry(odom(STEP, 0.125))
    for _ in range(100):
        battery.update_clock(0)
        assert battery.remaining_wh == 100.0
    battery.update_clock(STEP)
    assert battery.remaining_wh == pytest.approx(100.0 - 0.125 * 0.2 - 2 * 0.25 / 3600)


def test_duplicate_out_of_order_and_negative_samples_do_not_change_baseline():
    battery = BatteryConsumption(model(idle_power_w=0.0))
    battery.update_clock(0)
    battery.observe_odometry(odom(0))
    battery.observe_odometry(odom(STEP, 0.125))
    battery.update_clock(STEP)
    for stamp in (STEP, 0, -1):
        battery.observe_odometry(odom(stamp, -500))
    battery.observe_odometry(odom(2 * STEP, 0.25))
    battery.update_clock(2 * STEP)
    assert battery.remaining_wh == pytest.approx(99.95)


@pytest.mark.parametrize("reset", ["jump", "frame", "gap"])
def test_reference_change_does_not_bridge_and_next_motion_counts(reset):
    battery = BatteryConsumption(model(idle_power_w=0.0))
    battery.update_clock(0)
    battery.observe_odometry(odom(0, 5))
    battery.update_clock(STEP)
    stamp = 2 * STEP
    frame = "odom"
    x = 0.0
    if reset == "frame":
        frame, x = "new_odom", 5.125
    if reset == "gap":
        stamp, x = 3 * STEP, 5.125
        battery.update_clock(2 * STEP)
    battery.observe_odometry(odom(stamp, x, frame=frame))
    battery.update_clock(stamp)
    assert battery.remaining_wh == 100.0
    battery.observe_odometry(odom(stamp + STEP, x + 0.125, frame=frame))
    battery.update_clock(stamp + STEP)
    assert battery.remaining_wh == pytest.approx(99.975)


@pytest.mark.parametrize("bad", [
    {"x": float("nan")}, {"x": float("inf")}, {"linear_speed": float("inf")},
    {"linear_speed": -1.0}, {"angular_speed": float("nan")}, {"frame": ""},
])
def test_invalid_sample_breaks_the_chain_without_stopping_base_load(bad):
    battery = BatteryConsumption(model())
    battery.update_clock(0)
    battery.observe_odometry(odom(0))
    battery.observe_odometry(odom(STEP, **bad))
    battery.update_clock(STEP)
    battery.observe_odometry(odom(2 * STEP, 0.25))
    battery.update_clock(2 * STEP)
    assert battery.remaining_wh == pytest.approx(100.0 - 2 * 0.5 / 3600)


def test_clock_rewind_discards_pending_odometry_and_never_refills():
    battery = BatteryConsumption(model())
    battery.update_clock(10 * SECOND)
    battery.observe_odometry(odom(10 * SECOND, 9.0))
    battery.update_clock(10 * SECOND + STEP)
    battery.observe_odometry(odom(10 * SECOND + 2 * STEP, 9.2))
    before_reset = battery.remaining_wh
    battery.update_clock(-1)
    assert battery.clock_ns == 10 * SECOND + STEP
    battery.update_clock(0)
    assert battery.remaining_wh == before_reset
    battery.observe_odometry(odom(10 * SECOND + STEP, 9.0))  # Delayed old epoch.
    battery.observe_odometry(odom(0, -4.0))
    battery.observe_odometry(odom(STEP, -3.875))
    battery.update_clock(STEP)
    assert battery.remaining_wh == pytest.approx(before_reset - 0.025 - 2 * 0.25 / 3600)
    battery.update_clock(11 * SECOND)
    assert battery.remaining_wh == pytest.approx(before_reset - 0.025 - 2 * 11 / 3600)


def test_late_odometry_cannot_bridge_stale_history():
    battery = BatteryConsumption(model(idle_power_w=0.0))
    battery.update_clock(0)
    battery.observe_odometry(odom(0))
    battery.update_clock(SECOND)
    battery.observe_odometry(odom(STEP, 0.125))
    battery.update_clock(SECOND + STEP)
    assert battery.remaining_wh == 100.0


def test_isolation_and_energy_and_soc_floor():
    first = BatteryConsumption(model())
    second = BatteryConsumption(model(
        usable_capacity_wh=60.0, idle_power_w=4.0, consumption_wh_per_meter=0.4,
    ))
    first.update_clock(0)
    second.update_clock(10 * SECOND)
    first.observe_odometry(odom(0))
    first.observe_odometry(odom(STEP, 0.125))
    first.update_clock(STEP)
    assert second.remaining_wh == 60.0
    second.observe_odometry(odom(10 * SECOND))
    second.observe_odometry(odom(10 * SECOND + STEP, 0.125))
    second.update_clock(10 * SECOND + STEP)
    assert second.remaining_wh == pytest.approx(60.0 - 0.05 - 4 * 0.25 / 3600)
    assert first.remaining_wh == pytest.approx(100.0 - 0.025 - 2 * 0.25 / 3600)
    first.update_clock(300_000 * SECOND)
    assert first.remaining_wh == first.soc_percent == 0.0
    assert 0 < second.soc_percent < 100


@pytest.mark.parametrize("invalid", [
    {"usable_capacity_wh": 0}, {"consumption_wh_per_meter": -1},
    {"idle_power_w": float("inf")}, {"idle_power_w": None},
])
def test_invalid_model_rejected_by_c1_contract(invalid):
    with pytest.raises(ValidationError):
        model(**invalid)
