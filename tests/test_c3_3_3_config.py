"""Unit tests for Stage C3.3.3 configuration and schema."""
import json
from pathlib import Path
import jsonschema
import yaml


def test_simulation_c3_3_3_config_matches_schema():
    config_path = Path("config/simulation-c3-3-3.json")
    schema_path = Path("config/simulation-c3-3-3.schema.json")
    fleet_path = Path("config/fleet.yaml")
    assert config_path.exists(), "simulation-c3-3-3.json must exist"
    assert schema_path.exists(), "simulation-c3-3-3.schema.json must exist"
    assert fleet_path.exists(), "fleet.yaml must exist"

    config = json.loads(config_path.read_text())
    schema = json.loads(schema_path.read_text())

    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(config, schema)

    fleet_data = yaml.safe_load(fleet_path.read_text())
    assert len(fleet_data["robots"]) == 2
    r_ids = [r["id"] for r in fleet_data["robots"]]
    assert "robot_1" in r_ids
    assert "robot_2" in r_ids

    assert Path(config["map_path"].lstrip("/")).exists() or Path(config["map_path"]).exists()
    assert Path(config["nav2_template_path"].lstrip("/")).exists() or Path(config["nav2_template_path"]).exists()
