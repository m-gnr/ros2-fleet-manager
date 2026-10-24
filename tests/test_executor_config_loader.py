"""Unit tests for Robot Executor config_loader."""

from pathlib import Path
import pytest

from fleet_robot_executor.config_loader import (
    load_all_robots_from_fleet,
    load_robot_fleet_config,
)


FLEET_YAML = Path("config/fleet.yaml").resolve()


def test_load_robot_1_defaults():
    cfg = load_robot_fleet_config(FLEET_YAML, "robot_1")
    assert cfg.robot_id == "robot_1"
    assert cfg.namespace == "/robot_1"
    assert cfg.nav2_action_name == "/robot_1/navigate_to_pose"
    assert cfg.initial_pose == (-2.0, -0.5, 0.0)
    assert cfg.battery_model == "turtlebot3_burger"
    assert cfg.use_sim_time is True


def test_load_robot_2():
    cfg = load_robot_fleet_config(FLEET_YAML, "robot_2")
    assert cfg.robot_id == "robot_2"
    assert cfg.namespace == "/robot_2"
    assert cfg.nav2_action_name == "/robot_2/navigate_to_pose"
    assert cfg.initial_pose == (1.0, 2.5, 3.1415)
    assert cfg.battery_model == "turtlebot3_burger"
    assert cfg.use_sim_time is True


def test_load_all_robots():
    robots = load_all_robots_from_fleet(FLEET_YAML)
    assert len(robots) == 2
    assert robots[0].robot_id == "robot_1"
    assert robots[1].robot_id == "robot_2"


def test_load_default_robot_when_id_none():
    cfg = load_robot_fleet_config(FLEET_YAML, None)
    assert cfg.robot_id == "robot_1"


def test_load_unknown_robot_raises():
    with pytest.raises(ValueError, match="Robot ID 'unknown_robot' not found"):
        load_robot_fleet_config(FLEET_YAML, "unknown_robot")


def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_robot_fleet_config(Path("config/non_existent.yaml"))
