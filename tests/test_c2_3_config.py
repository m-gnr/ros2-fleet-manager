"""Unit tests for Stage C2.3 configuration and schema."""
import json
import os
from pathlib import Path
import jsonschema
import pytest


def test_simulation_c2_3_config_matches_schema():
    config_path = Path("config/simulation-c2-3.json")
    schema_path = Path("config/simulation-c2-3.schema.json")
    assert config_path.exists(), "simulation-c2-3.json must exist"
    assert schema_path.exists(), "simulation-c2-3.schema.json must exist"

    config = json.loads(config_path.read_text())
    schema = json.loads(schema_path.read_text())

    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(config, schema)

    assert config["robot"]["name"] == "robot_1"
    assert config["robot"]["namespace"] == "robot_1"
    assert len(config["robot"]["initial_pose"]) == 6
    assert Path(config["map_path"].lstrip("/")).exists() or Path(config["map_path"]).exists()
    assert Path(config["nav2_template_path"].lstrip("/")).exists() or Path(config["nav2_template_path"]).exists()
