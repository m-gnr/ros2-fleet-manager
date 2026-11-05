"""Tests for dynamic Fleet Manager builder from fleet.yaml."""

from pathlib import Path
import shutil

import pytest
import yaml

from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain.constants import RobotState, StationType, TaskPhase
from backend.fleet_manager.domain.models import Pose2D
from backend.fleet_manager.domain.scheduler import RouteDistanceProvider


class DummyRouteProvider(RouteDistanceProvider):
    def get_path_distance(self, robot_id, start: Pose2D, goal: Pose2D):
        return 5.0


def test_build_fleet_manager_from_fleet_yaml():
    core, robot_ids = build_fleet_manager_from_config("config/fleet.yaml", DummyRouteProvider())
    assert robot_ids == ["robot_1", "robot_2"]
    
    # Check robots registered with correct initial poses and specs
    r1 = core.tracker.get_robot("robot_1")
    assert r1 is not None
    assert r1.pose.x == -2.0
    assert r1.pose.y == -0.5
    assert r1.pose.yaw == 0.0
    assert r1.specs.usable_capacity_wh == 100.0
    assert r1.specs.consumption_wh_per_meter == 0.20
    assert r1.specs.idle_power_w == 2.0
    assert r1.specs.charge_power_w == 20.0
    
    r2 = core.tracker.get_robot("robot_2")
    assert r2 is not None
    assert r2.pose.x == 1.0
    assert r2.pose.y == 2.5
    assert r2.pose.yaw == 3.1415
    assert r2.specs.usable_capacity_wh == 100.0

    # Check stations
    dock_1 = core.reservations.get_station("dock_1")
    assert dock_1 is not None
    assert dock_1.station_type == StationType.CHARGING
    assert dock_1.pose.x == 0.5
    assert dock_1.pose.y == -2.0
    assert dock_1.tolerance_radius == 0.30

    park_1 = core.reservations.get_station("park_1")
    assert park_1 is not None
    assert park_1.station_type == StationType.PARKING
    assert park_1.pose.x == -2.0
    assert park_1.pose.y == 1.0

    # Check safe charge station pose
    assert core.scheduler.safe_charge_station_pose.x == 0.5
    assert core.scheduler.safe_charge_station_pose.y == -2.0


@pytest.fixture
def fleet_yaml(tmp_path):
    return shutil.copytree("config", tmp_path / "config") / "fleet.yaml"


@pytest.mark.parametrize(
    "policy, value, soc, eligible",
    [
        ("safety_margin_wh", 22.0, 37.5, True),
        ("safety_margin_wh", 22.25, 37.5, False),
        ("emergency_soc_percent", 12.5, 37.5, True),
        ("emergency_soc_percent", 16.0, 37.5, False),
        ("safety_margin_wh", 22.0, 37.49, False),
    ],
)
def test_builder_energy_policies_change_assignment(fleet_yaml, policy, value, soc, eligible):
    data = yaml.safe_load(fleet_yaml.read_text())
    data["policies"].update(emergency_soc_percent=12.5, safety_margin_wh=22.0)
    data["policies"][policy] = value
    data["fleet"]["battery_models"]["turtlebot3_burger"]["consumption_wh_per_meter"] = 0.25
    fleet_yaml.write_text(yaml.safe_dump(data))

    class FourMetreRoutes:
        def get_path_distance(self, robot_id, start, goal):
            return 4.0

    core, _ = build_fleet_manager_from_config(fleet_yaml, FourMetreRoutes())
    core.handle_robot_status(
        robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
        is_loaded=False, pose=Pose2D(),
        battery_soc_percent=soc, battery_energy_wh=100, current_task_id=None,
        current_epoch=0, timestamp_sec=10,
    )
    core.submit_task("delivery", Pose2D(1, 0), Pose2D(2, 0), priority=3, created_at=1)
    # At the threshold, 12 m costs 3 Wh, plus one 22 Wh margin.
    assert bool(core.schedule_tick(10)) is eligible
    if not eligible:
        assert core.queue.get("delivery").created_at == 1
        assert not core._failed_tasks


@pytest.mark.parametrize(
    "field, value, error",
    [
        ("safety_margin_wh", None, "safety_margin_wh"),
        ("emergency_soc_percent", None, "emergency_soc_percent"),
        ("safety_margin_wh", -1, "safety_margin_wh"),
        ("emergency_soc_percent", 25, "emergency_soc_percent"),
    ],
)
def test_builder_rejects_missing_or_invalid_policy(fleet_yaml, field, value, error):
    data = yaml.safe_load(fleet_yaml.read_text())
    if value is None:
        del data["policies"][field]
    else:
        data["policies"][field] = value
    fleet_yaml.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match=error):
        build_fleet_manager_from_config(fleet_yaml)


def test_builder_propagates_validator_import_error(monkeypatch):
    import fleet_config.loader

    def unavailable_validator(path):
        raise ImportError("C1 validator unavailable")

    monkeypatch.setattr(fleet_config.loader, "load_config", unavailable_validator)
    with pytest.raises(ImportError, match="C1 validator unavailable"):
        build_fleet_manager_from_config()


def test_builder_rejects_missing_explicit_config(tmp_path):
    path = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError, match="missing.yaml"):
        build_fleet_manager_from_config(path)
