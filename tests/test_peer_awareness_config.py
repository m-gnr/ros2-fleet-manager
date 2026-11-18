"""Candidate peer observations remain opt-in and share the fleet geometry source."""
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

from fleet_config import load_config
from fleet_config.warehouse_assets import generate, configure_peer_observations

PROFILE = Path("config/fleet.warehouse-30x18.yaml").resolve()


def test_default_generation_and_experiment_preserve_world_and_lidar(tmp_path):
    baseline, candidate = tmp_path / "baseline", tmp_path / "candidate"
    cfg = generate(PROFILE, baseline)
    generate(PROFILE, candidate, peer_awareness=True)
    assert (baseline / "warehouse.sdf").read_bytes() == (candidate / "warehouse.sdf").read_bytes()
    assert (baseline / "map.pgm").read_bytes() == (candidate / "map.pgm").read_bytes()
    for robot in cfg.robots:
        before = yaml.safe_load((baseline / f"nav2-{robot.id}.yaml").read_text())
        after = yaml.safe_load((candidate / f"nav2-{robot.id}.yaml").read_text())
        for name in ("local_costmap", "global_costmap"):
            original = before[name][name]["ros__parameters"]
            cost = after[name][name]["ros__parameters"]
            assert "peer_robot_layer" not in original
            assert cost["plugins"].index("peer_robot_layer") < cost["plugins"].index("inflation_layer")
            layer = cost.pop("peer_robot_layer")
            cost["plugins"].remove("peer_robot_layer")
            assert cost == original
            assert layer["self_id"] == robot.id
            assert layer["robot_ids"] == [r.id for r in cfg.robots]
            assert layer["tf_topics"] == [r.namespace + "/tf" for r in cfg.robots]
            assert layer["radii"] == [original["robot_radius"]] * len(cfg.robots)
            assert layer["transport_sec"] == cfg.fleet.perception_safety.transport_sec
            assert layer["pose_age_sec"] == cfg.fleet.perception_safety.odometry_freshness_sec
        after["map_server"]["ros__parameters"]["yaml_filename"] = before["map_server"]["ros__parameters"]["yaml_filename"]
        assert before == after


def test_peer_configuration_is_driven_by_robot_list_and_each_radius():
    cfg = load_config(PROFILE)
    cfg.robots = cfg.robots[::-1]
    radii = {r.id: .3 + i*.1 for i, r in enumerate(cfg.robots)}
    params = {name: {name: {"ros__parameters": {"plugins": ["static_layer", "inflation_layer"]}}}
              for name in ("local_costmap", "global_costmap")}
    params["amcl"] = {"ros__parameters": {"global_frame_id": "map", "transform_tolerance": 1.}}
    configure_peer_observations(params, cfg, cfg.robots[0], radii)
    layer = params["global_costmap"]["global_costmap"]["ros__parameters"]["peer_robot_layer"]
    assert layer["self_id"] == cfg.robots[0].id
    assert layer["robot_ids"] == [r.id for r in cfg.robots]
    assert layer["radii"] == [radii[r.id] for r in cfg.robots]
    assert layer["localization_age_sec"] == cfg.fleet.perception_safety.observation_age_sec


def test_missing_explicit_safety_profile_is_rejected():
    cfg = load_config(PROFILE)
    cfg.fleet.perception_safety = None
    with pytest.raises(ValueError, match="explicit perception_safety"):
        configure_peer_observations({}, cfg, cfg.robots[0], {})


def test_peer_plugin_registration():
    root = ET.parse("ros2_ws/src/fleet_perception/plugins.xml").getroot()
    assert len([c for c in root.findall("class") if c.attrib["type"] == "fleet_perception::PeerRobotLayer"]) == 1
