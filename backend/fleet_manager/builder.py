"""Fleet Manager Core builder from fleet.yaml specification.

Conforms strictly to:
- DOC-ARCH-2026-10-23-FINAL Section 4 & 5: Single editable configuration source config/fleet.yaml.
- C3.3.3-DEC-02: fleet.yaml single source of truth for robot initial poses and stations.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union
import yaml

from .domain.constants import StationType
from .domain.fleet_manager_core import FleetManagerCore
from .domain.models import Pose2D, RobotBatterySpecs
from .domain.scheduler import RouteDistanceProvider


def build_fleet_manager_from_config(
    fleet_config_path: Union[str, Path] = "config/fleet.yaml",
    route_provider: Optional[RouteDistanceProvider] = None,
) -> Tuple[FleetManagerCore, List[str]]:
    """Construct FleetManagerCore and register all robots and stations dynamically from fleet.yaml."""
    config_file = Path(fleet_config_path).resolve()
    if not config_file.exists():
        # Fallback search
        for candidate in [Path("config/fleet.yaml"), Path("/config/fleet.yaml")]:
            if candidate.exists():
                config_file = candidate.resolve()
                break

    try:
        from fleet_config.loader import load_config as load_pydantic_config

        cfg = load_pydantic_config(config_file)
        safe_station = cfg.stations.charging_stations[0]
        safe_charge_pose = Pose2D(
            x=safe_station.pose.x,
            y=safe_station.pose.y,
            yaw=safe_station.pose.yaw,
        )

        core = FleetManagerCore(
            route_provider=route_provider,
            safe_charge_station_pose=safe_charge_pose,
        )

        robot_ids: List[str] = []
        for r in cfg.robots:
            b_model = cfg.fleet.battery_models[r.battery_model]
            specs = RobotBatterySpecs(
                usable_capacity_wh=b_model.usable_capacity_wh,
                consumption_wh_per_meter=b_model.consumption_wh_per_meter,
                idle_power_w=b_model.idle_power_w,
                charge_power_w=b_model.charge_power_w,
            )
            init_pose = Pose2D(x=r.initial_pose.x, y=r.initial_pose.y, yaw=r.initial_pose.yaw)
            core.register_robot(robot_id=r.id, specs=specs, initial_pose=init_pose)
            robot_ids.append(r.id)

        for cs in cfg.stations.charging_stations:
            core.register_station(
                station_id=cs.id,
                station_type=StationType.CHARGING,
                pose=Pose2D(x=cs.pose.x, y=cs.pose.y, yaw=cs.pose.yaw),
                tolerance_radius=cs.tolerance_radius,
            )

        for ps in cfg.stations.parking_stations:
            core.register_station(
                station_id=ps.id,
                station_type=StationType.PARKING,
                pose=Pose2D(x=ps.pose.x, y=ps.pose.y, yaw=ps.pose.yaw),
            )

        return core, robot_ids

    except (ImportError, ModuleNotFoundError):
        # Pure YAML fallback when pydantic/fleet_config is not installed
        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        stations_data = data.get("stations", {})
        charging = stations_data.get("charging_stations", [])
        if not charging:
            raise ValueError(f"{config_file}: at least one charging station required")

        cs0 = charging[0]
        cs0_pose = cs0.get("pose", {})
        safe_charge_pose = Pose2D(
            x=float(cs0_pose.get("x", 0.0)),
            y=float(cs0_pose.get("y", 0.0)),
            yaw=float(cs0_pose.get("yaw", 0.0)),
        )

        core = FleetManagerCore(
            route_provider=route_provider,
            safe_charge_station_pose=safe_charge_pose,
        )

        battery_models = data.get("fleet", {}).get("battery_models", {})
        robot_ids = []
        for r in data.get("robots", []):
            rid = str(r["id"])
            bm_name = r.get("battery_model")
            bm_data = battery_models.get(bm_name, {})
            specs = RobotBatterySpecs(
                usable_capacity_wh=float(bm_data.get("usable_capacity_wh", 100.0)),
                consumption_wh_per_meter=float(bm_data.get("consumption_wh_per_meter", 0.20)),
                idle_power_w=float(bm_data.get("idle_power_w", 2.0)),
                charge_power_w=float(bm_data.get("charge_power_w", 20.0)),
            )
            r_pose = r.get("initial_pose", {})
            init_pose = Pose2D(
                x=float(r_pose.get("x", 0.0)),
                y=float(r_pose.get("y", 0.0)),
                yaw=float(r_pose.get("yaw", 0.0)),
            )
            core.register_robot(robot_id=rid, specs=specs, initial_pose=init_pose)
            robot_ids.append(rid)

        for cs in charging:
            p = cs.get("pose", {})
            core.register_station(
                station_id=str(cs["id"]),
                station_type=StationType.CHARGING,
                pose=Pose2D(x=float(p.get("x", 0.0)), y=float(p.get("y", 0.0)), yaw=float(p.get("yaw", 0.0))),
                tolerance_radius=float(cs.get("tolerance_radius", 0.30)),
            )

        for ps in stations_data.get("parking_stations", []):
            p = ps.get("pose", {})
            core.register_station(
                station_id=str(ps["id"]),
                station_type=StationType.PARKING,
                pose=Pose2D(x=float(p.get("x", 0.0)), y=float(p.get("y", 0.0)), yaw=float(p.get("yaw", 0.0))),
            )

        return core, robot_ids
