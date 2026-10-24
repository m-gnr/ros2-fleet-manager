"""C1 contract tests; no ROS, simulation, or deployment claims."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from fleet_config import FleetConfig, load_config
from fleet_config.loader import generated_schema

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample(tmp_path):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    path = tmp_path / "config/fleet.yaml"
    return path, yaml.safe_load(path.read_text())


def save(path, data):
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path


def set_field(data, route, value):
    for key in route[:-1]:
        data = data[key]
    data[route[-1]] = value


@pytest.mark.parametrize("count", [1, 2, 3])
def test_robot_counts_from_yaml_only(sample, count):
    path, data = sample
    if count == 3:
        robot = deepcopy(data["robots"][0])
        robot.update(id="robot_3", name="robot_3", namespace="/robot_3",
                     nav2_action_name="/robot_3/navigate_to_pose")
        robot["initial_pose"]["x"] = 3.0
        data["robots"].append(robot)
    data["robots"] = data["robots"][:count]
    assert len(load_config(save(path, data)).robots) == count


def test_schema_is_generated_and_has_no_defaults():
    schema = json.loads((ROOT / "config/fleet.schema.json").read_text())
    assert schema == generated_schema()
    Draft202012Validator.check_schema(schema)
    def walk(node):
        if isinstance(node, dict):
            assert "default" not in node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(schema)


@pytest.mark.parametrize("route,value", [
    (["robots", 0, "id"], "bad-id"),
    (["robots", 0, "id"], "2robot"),
    (["robots", 0, "namespace"], "robot_1"),
    (["robots", 0, "namespace"], "/robot//one"),
    (["robots", 0, "initial_pose", "x"], "1.0"),
    (["robots", 0, "initial_pose", "yaw"], True),
    (["fleet", "battery_models", "turtlebot3_burger", "usable_capacity_wh"], 0),
    (["fleet", "battery_models", "turtlebot3_burger", "consumption_wh_per_meter"], -1),
    (["fleet", "battery_models", "turtlebot3_burger", "idle_power_w"], -1),
    (["fleet", "battery_models", "turtlebot3_burger", "charge_power_w"], 0),
    (["policies", "low_soc_percent"], 101),
    (["policies", "emergency_soc_percent"], -1),
    (["policies", "safety_margin_wh"], -1),
    (["policies", "charge_target_soc_percent"], 90),
    (["policies", "max_preemptions"], 3),
    (["policies", "extra_swap_enabled"], True),
    (["policies", "automatic_retry"], True),
    (["policies", "automatic_reassignment"], True),
    (["policies", "automatic_retry"], 0),
    (["policies", "preemption_priority"], "MEDIUM"),
    (["policies", "assignment"], "cost_based"),
    (["fleet", "use_sim_time"], False),
    (["fleet", "use_sim_time"], 1),
    (["stations", "charging_stations", 0, "tolerance_radius"], 0),
    (["robots"], []),
    (["stations", "charging_stations"], []),
])
def test_structural_rules_agree_in_schema_and_pydantic(sample, route, value):
    path, data = sample
    set_field(data, route, value)
    assert list(Draft202012Validator(generated_schema()).iter_errors(data))
    with pytest.raises(ValidationError):
        FleetConfig.model_validate(data)
    with pytest.raises(ValueError):
        load_config(save(path, data))


@pytest.mark.parametrize("route", [
    ["fleet"], ["robots"], ["stations"], ["policies"],
    ["robots", 0, "id"], ["robots", 0, "initial_pose", "yaw"],
    ["fleet", "battery_models", "turtlebot3_burger", "charge_power_w"],
    ["policies", "safety_margin_wh"],
])
def test_required_fields(sample, route):
    path, data = sample
    target = data
    for key in route[:-1]:
        target = target[key]
    del target[route[-1]]
    with pytest.raises(ValueError, match=route[-1]):
        load_config(save(path, data))


@pytest.mark.parametrize("field", ["id", "name", "namespace", "nav2_action_name"])
def test_duplicate_robot_resource(sample, field):
    path, data = sample
    data["robots"][1][field] = data["robots"][0][field]
    with pytest.raises(ValueError):
        load_config(save(path, data))


@pytest.mark.parametrize("case,match", [
    ("station_id", "duplicate resource id"),
    ("station_pose", "physical position"),
    ("robot_pose", "duplicate initial position"),
    ("unknown_model", "unknown model"),
    ("foreign_action", "namespace"),
    ("nested_namespace", "nested namespaces"),
    ("threshold_order", "emergency_soc_percent"),
    ("margin", "safety margin"),
    ("unknown_field", "Additional properties"),
])
def test_semantic_failures(sample, case, match):
    path, data = sample
    first, second = data["robots"]
    dock = data["stations"]["charging_stations"][0]
    park = data["stations"]["parking_stations"][0]
    if case == "station_id":
        park["id"] = dock["id"]
    elif case == "station_pose":
        park["pose"] = dock["pose"].copy()
        park["pose"]["yaw"] = 1.0
    elif case == "robot_pose":
        second["initial_pose"] = first["initial_pose"].copy()
    elif case == "unknown_model":
        first["battery_model"] = "unknown"
    elif case == "foreign_action":
        first["nav2_action_name"] = "/other/navigate_to_pose"
    elif case == "nested_namespace":
        second.update(namespace="/robot_1/child", nav2_action_name="/robot_1/child/navigate_to_pose")
    elif case == "threshold_order":
        data["policies"]["low_soc_percent"] = data["policies"]["emergency_soc_percent"]
    elif case == "margin":
        data["policies"]["safety_margin_wh"] = 100
    else:
        data["fleet"]["stations"] = {}
    with pytest.raises(ValueError, match=match):
        load_config(save(path, data))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("route", [
    ["robots", 0, "initial_pose", "x"],
    ["fleet", "battery_models", "turtlebot3_burger", "usable_capacity_wh"],
])
def test_nonfinite_numbers(sample, route, value):
    path, data = sample
    set_field(data, route, value)
    with pytest.raises(ValueError):
        load_config(save(path, data))


@pytest.mark.parametrize("asset", ["map", "nav2", "image"])
def test_missing_asset(sample, asset):
    path, data = sample
    if asset == "map":
        data["fleet"]["map_path"] = "missing.yaml"
    elif asset == "nav2":
        data["robots"][0]["nav2_params_path"] = "missing.yaml"
    else:
        (path.parent / "map/map.pgm").unlink()
    with pytest.raises(ValueError, match="file not found"):
        load_config(save(path, data))


@pytest.mark.parametrize("content", ["fleet: [", "fleet: {}\nfleet: {}", "1: value", "!!python/object:bad {}"])
def test_invalid_yaml(sample, content):
    path, _ = sample
    path.write_text(content)
    with pytest.raises((ValueError, yaml.YAMLError)):
        load_config(path)


def test_paths_independent_of_cwd(sample, monkeypatch, tmp_path):
    path, _ = sample
    monkeypatch.chdir(tmp_path)
    assert len(load_config(path).robots) == 2


def test_schema_drift_rejected(sample, tmp_path):
    path, _ = sample
    schema = generated_schema()
    del schema["required"]
    altered = tmp_path / "schema.json"
    altered.write_text(json.dumps(schema))
    with pytest.raises(ValueError, match="differs"):
        load_config(path, altered)


@pytest.mark.parametrize("content,match", [
    ("node:\n  ros__parameters:\n    use_sim_time: false", "use_sim_time"),
    ("node: '@UNKNOWN@'", "placeholder"),
    ("[]", "mapping"),
])
def test_bad_nav2_content(sample, content, match):
    path, data = sample
    (path.parent / data["robots"][0]["nav2_params_path"]).write_text(content)
    with pytest.raises(ValueError, match=match):
        load_config(path)


def test_cli_success_and_failure(sample):
    path, data = sample
    result = subprocess.run([sys.executable, "-m", "fleet_config", str(path)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0
    assert "VALID: 2 robots" in result.stdout
    del data["robots"][0]["id"]
    save(path, data)
    result = subprocess.run([sys.executable, "-m", "fleet_config", str(path)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 1
    assert "INVALID:" in result.stderr and "id" in result.stderr
    assert "Traceback" not in result.stderr


def test_zero_idle_power_and_empty_parking_are_valid(sample):
    path, data = sample
    data["fleet"]["battery_models"]["turtlebot3_burger"]["idle_power_w"] = 0
    data["stations"]["parking_stations"] = []
    assert load_config(save(path, data))


@pytest.mark.parametrize("content", ["node: {}", "node:\n  ros__parameters: {}"])
def test_nav2_requires_simulation_parameter_blocks(sample, content):
    path, data = sample
    (path.parent / data["robots"][0]["nav2_params_path"]).write_text(content)
    with pytest.raises(ValueError, match="ros__parameters"):
        load_config(path)


def test_missing_map_image_field(sample):
    path, _ = sample
    (path.parent / "map/map.yaml").write_text("resolution: 0.05\n")
    with pytest.raises(ValueError, match="image path"):
        load_config(path)
