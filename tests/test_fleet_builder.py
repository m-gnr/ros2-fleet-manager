"""Tests for dynamic Fleet Manager builder from fleet.yaml."""

import pytest
from pathlib import Path
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.domain.constants import StationType
from backend.fleet_manager.domain.models import Pose2D
from backend.fleet_manager.domain.scheduler import RouteDistanceProvider


class DummyRouteProvider(RouteDistanceProvider):
    def get_path_distance(self, start: Pose2D, goal: Pose2D):
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
