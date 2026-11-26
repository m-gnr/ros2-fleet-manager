"""Candidate peer observations remain opt-in and share the fleet geometry source."""
from itertools import product
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import yaml

from fleet_config import load_config
from fleet_config.obstacle_sensors import compose, pose, shape_bound
from fleet_config.warehouse_assets import generate, configure_peer_observations

PROFILE = Path("config/fleet.warehouse-30x18.yaml").resolve()


def test_demo_escape_tree_shares_one_lease_and_replans_original_goal(tmp_path):
    with pytest.raises(ValueError, match="requires peer costmap"):
        generate(PROFILE, tmp_path / "unsafe", warehouse_escape=True)
    out = tmp_path / "demo"
    cfg = generate(PROFILE, out, peer_awareness=True, warehouse_escape=True)
    world = ET.parse(out / "warehouse.sdf")
    for robot in cfg.robots:
        params = yaml.safe_load((out / f"nav2-{robot.id}.yaml").read_text())
        nav = params["bt_navigator"]["ros__parameters"]
        assert "fleet_escape_bt_nodes" in nav["plugin_lib_names"]
        tree = ET.parse(nav["default_nav_to_pose_bt_xml"])
        recovery = tree.find(".//RecoveryNode[@name='NavigateRecovery']")
        assert recovery.get("number_of_retries") == "1"
        planner = recovery.find(".//ComputePathToPose")
        assert planner.get("goal") == "{goal}"
        assert int(planner.get("server_timeout")) > nav["default_server_timeout"]
        assert recovery.find(".//FleetFollowPath").get("aborted") == "{aborted_follow}"
        escape = recovery.find("FleetEscape")
        assert float(escape.get("radius")) == cfg.fleet.nav2_escape_radius_m
        assert escape.get("base_frame") == f"{robot.id}/base_link"
        assert escape.get("odom_topic") == f"{robot.namespace}/odom"
        assert escape.get("lease") == "/tmp/fleet-nav2-escape.lock"
        controller = params["controller_server"]["ros__parameters"]
        for kind in ("local_costmap", "global_costmap"):
            layer = params[kind][kind]["ros__parameters"]["peer_robot_layer"]
            assert layer["publish_recovery_costmap"]
        clearance = controller["FleetClearance"]
        assert clearance["physical_topics"] == [r.namespace + "/physical_pose" for r in cfg.robots]
        assert escape.get("physical_topics").split(";") == clearance["physical_topics"]
        assert escape.get("physical_radii").split(";") == list(map(str, clearance["radii"]))
        assert cfg.robots[clearance["self_index"]].id == robot.id
        assert int(escape.get("self_index")) == clearance["self_index"]
        assert recovery.find(".//FleetFollowPath").get("goal_checker_id") == "general_goal_checker"
        assert escape.get("physical_hulls").split("|") == clearance["physical_hulls"]
        hull = list(map(float, clearance["physical_hulls"][clearance["self_index"]].split(";")))
        vertices = list(zip(hull[::2], hull[1::2], strict=True))
        assert len(vertices) >= 3
        edges = list(zip(vertices, vertices[1:] + vertices[:1], strict=True))
        for link in world.findall(f".//model[@name='{robot.id}']/link"):
            for collision in link.findall("collision"):
                center, rotation = compose(pose(link), pose(collision))
                _, bounds = shape_bound(collision.find("geometry"), center, rotation)
                for x, y in product(*bounds[:2]):
                    assert all((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]) >= -1e-10
                               for a, b in edges)


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
