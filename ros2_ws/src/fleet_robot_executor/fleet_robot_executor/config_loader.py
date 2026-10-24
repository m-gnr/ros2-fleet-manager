"""Configuration loader for Robot Executor.

Loads and validates robot configuration from config/fleet.yaml using either
fleet_config (when Pydantic is available) or JSON Schema / PyYAML fallback
(for environments with minimal ROS 2 dependencies).
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import List, Optional, Tuple, Union

import yaml


@dataclass(frozen=True)
class RobotConfig:
    """Robot execution parameters loaded from fleet.yaml."""

    robot_id: str
    namespace: str
    nav2_action_name: str
    initial_pose: Tuple[float, float, float]  # (x, y, yaw)
    battery_model: str
    use_sim_time: bool = True
    nav2_params_path: str = ""


def _find_fleet_yaml(path: Optional[Union[str, Path]] = None) -> Path:
    """Locate fleet.yaml path from given path, env variable, or default locations."""
    if path:
        p = Path(path)
        if p.is_file():
            return p.resolve()
        raise FileNotFoundError(f"Specified fleet config file not found: {p}")

    env_path = os.environ.get("FLEET_CONFIG_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p.resolve()
        raise FileNotFoundError(f"FLEET_CONFIG_PATH not found: {p}")

    # Common relative locations
    cwd = Path.cwd()
    candidates = [
        cwd / "config/fleet.yaml",
        cwd / "fleet.yaml",
        Path(__file__).resolve().parents[4] / "config/fleet.yaml",
        Path("/config/fleet.yaml"),
    ]

    for cand in candidates:
        if cand.is_file():
            return cand.resolve()

    raise FileNotFoundError(
        f"fleet.yaml not found. Checked: {[str(c) for c in candidates]}"
    )


def _load_data_with_schema_fallback(config_file: Path) -> dict:
    """Load and validate fleet.yaml with jsonschema when Pydantic is not present."""
    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"{config_file}: expected YAML mapping root")

    # Locate schema
    schema_candidates = [
        config_file.parent / "fleet.schema.json",
        config_file.parent.parent / "config/fleet.schema.json",
        Path("/config/fleet.schema.json"),
    ]
    schema_path = next((p for p in schema_candidates if p.is_file()), None)

    if schema_path:
        try:
            import jsonschema

            with open(schema_path, "r", encoding="utf-8") as sf:
                schema = json.load(sf)
            jsonschema.validate(instance=data, schema=schema)
        except ImportError:
            pass  # jsonschema not installed; proceed with loaded data
        except Exception as e:
            raise ValueError(f"fleet.yaml failed schema validation: {e}") from e

    return data


def load_all_robots_from_fleet(
    config_path: Optional[Union[str, Path]] = None,
) -> List[RobotConfig]:
    """Load all robot definitions from fleet.yaml."""
    config_file = _find_fleet_yaml(config_path)

    # Attempt to use fleet_config if pydantic is available
    try:
        from fleet_config.loader import load_config

        fleet_cfg = load_config(config_file)
        use_sim_time = fleet_cfg.fleet.use_sim_time
        robots: List[RobotConfig] = []
        for r in fleet_cfg.robots:
            init_p = (r.initial_pose.x, r.initial_pose.y, r.initial_pose.yaw)
            robots.append(
                RobotConfig(
                    robot_id=r.id,
                    namespace=r.namespace,
                    nav2_action_name=r.nav2_action_name,
                    initial_pose=init_p,
                    battery_model=r.battery_model,
                    use_sim_time=use_sim_time,
                    nav2_params_path=r.nav2_params_path,
                )
            )
        return robots
    except (ImportError, ModuleNotFoundError):
        pass

    # Fallback to pure PyYAML + jsonschema
    data = _load_data_with_schema_fallback(config_file)
    use_sim_time = bool(data.get("fleet", {}).get("use_sim_time", True))
    robots_data = data.get("robots", [])
    if not isinstance(robots_data, list) or not robots_data:
        raise ValueError(f"{config_file}: 'robots' must be a non-empty list")

    robots = []
    for r in robots_data:
        pose_data = r.get("initial_pose", {})
        init_p = (
            float(pose_data.get("x", 0.0)),
            float(pose_data.get("y", 0.0)),
            float(pose_data.get("yaw", 0.0)),
        )
        robots.append(
            RobotConfig(
                robot_id=str(r["id"]),
                namespace=str(r["namespace"]),
                nav2_action_name=str(r["nav2_action_name"]),
                initial_pose=init_p,
                battery_model=str(r.get("battery_model", "")),
                use_sim_time=use_sim_time,
                nav2_params_path=str(r.get("nav2_params_path", "")),
            )
        )
    return robots


def load_robot_fleet_config(
    config_path: Optional[Union[str, Path]] = None,
    robot_id: Optional[str] = None,
) -> RobotConfig:
    """Load configuration for a specific robot ID from fleet.yaml.

    If robot_id is None, defaults to the first robot in the fleet configuration.
    """
    all_robots = load_all_robots_from_fleet(config_path)
    if not all_robots:
        raise ValueError("No robots found in fleet configuration")

    if not robot_id:
        return all_robots[0]

    for r in all_robots:
        if r.robot_id == robot_id:
            return r

    valid_ids = [r.robot_id for r in all_robots]
    raise ValueError(
        f"Robot ID '{robot_id}' not found in fleet configuration. Available: {valid_ids}"
    )
