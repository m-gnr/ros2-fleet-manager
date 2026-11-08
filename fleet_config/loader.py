"""Fail-fast loading with schema, semantic and filesystem checks."""

import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from pydantic import TypeAdapter

from .models import FleetConfig
from .anchored import AnchoredFleetConfig


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError(f"YAML mapping keys must be strings at line {key_node.start_mark.line + 1}")
        if key in result:
            raise ValueError(f"Duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def read_yaml(path):
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueKeyLoader)


def generated_schema():
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **TypeAdapter(FleetConfig | AnchoredFleetConfig).json_schema()}


def require_file(base, value, label):
    path = (base / value).resolve()
    if not path.is_file():
        raise ValueError(f"{label}: file not found: {path}")
    return path


def check_assets(config, base):
    if config.fleet.map_path != "warehouse:generated":
        map_path = require_file(base, config.fleet.map_path, "fleet.map_path")
        map_data = read_yaml(map_path)
        if not isinstance(map_data, dict) or not isinstance(map_data.get("image"), str):
            raise ValueError("fleet.map_path: map YAML must contain an image path")
        require_file(map_path.parent, map_data["image"], "map.image")
    for robot in config.robots:
        path = require_file(base, robot.nav2_params_path, f"robots.{robot.id}.nav2_params_path")
        # Parse the existing B3 template without writing rendered files into config/.
        # Sentinels check template syntax only; they are never runtime defaults.
        substitutions = {key: "validation_frame" for key in (
            "BASE_FRAME", "ODOM_FRAME", "SCAN_TOPIC", "ODOM_TOPIC")}
        substitutions.update({key: "0.0" for key in (
            "INIT_X", "INIT_Y", "INIT_Z", "INIT_YAW")})
        content = path.read_text(encoding="utf-8")
        for key, value in substitutions.items():
            content = content.replace(f"@{key}@", value)
        if re.search(r"@[A-Z_]+@", content):
            raise ValueError(f"{path}: unknown Nav2 template placeholder")
        nav2 = yaml.load(content, Loader=UniqueKeyLoader)
        if not isinstance(nav2, dict) or not nav2:
            raise ValueError(f"{path}: expected Nav2 parameter mapping")
        parameter_blocks = []
        def check_clock(node):
            if isinstance(node, dict):
                if "ros__parameters" in node:
                    parameters = node["ros__parameters"]
                    if not isinstance(parameters, dict) or parameters.get("use_sim_time") is not True:
                        raise ValueError(f"{path}: ros__parameters requires use_sim_time: true")
                    parameter_blocks.append(parameters)
                if "use_sim_time" in node and node["use_sim_time"] is not True:
                    raise ValueError(f"{path}: use_sim_time must be true")
                for value in node.values():
                    check_clock(value)
            elif isinstance(node, list):
                for value in node:
                    check_clock(value)
        check_clock(nav2)
        if not parameter_blocks:
            raise ValueError(f"{path}: missing ros__parameters blocks")


def load_config(path, schema_path=None):
    path = Path(path).resolve()
    schema_path = Path(schema_path) if schema_path else Path(__file__).resolve().parents[1] / "config/fleet.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema != generated_schema():
        raise ValueError("fleet.schema.json differs from Pydantic contract; regenerate schema")
    Draft202012Validator.check_schema(schema)
    data = read_yaml(path)
    warehouse = data.get("warehouse") if isinstance(data, dict) else None
    anchored = isinstance(warehouse, dict) and "width" in warehouse
    kind = "AnchoredFleetConfig" if anchored else "FleetConfig"
    selected = {"$ref": f"#/$defs/{kind}", "$defs": schema["$defs"]}
    errors = sorted(Draft202012Validator(selected).iter_errors(data), key=lambda error: str(list(error.path)))
    if errors:
        raise ValueError("\n".join(f"{'.'.join(map(str, error.path)) or '$'}: {error.message}" for error in errors))
    config = AnchoredFleetConfig.model_validate(data).resolve() if anchored else FleetConfig.model_validate(data)
    check_assets(config, path.parent)
    return config
