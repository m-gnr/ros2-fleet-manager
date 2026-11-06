"""Fleet Manager Core builder from fleet.yaml specification.

Conforms strictly to:
- DOC-ARCH-2026-10-23-FINAL Section 4 & 5: Single editable configuration source config/fleet.yaml.
- C3.3.3-DEC-02: fleet.yaml single source of truth for robot initial poses and stations.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union

from .adapters.route_cache import CachedRouteDistanceProvider, RouteCache
from .domain.constants import StationType
from .domain.fleet_manager_core import FleetManagerCore
from .domain.models import Pose2D, RobotBatterySpecs
from .domain.scheduler import RouteDistanceProvider


def build_fleet_manager_from_config(
    fleet_config_path: Union[str, Path] = "config/fleet.yaml",
    route_provider: Optional[RouteDistanceProvider] = None,
    *,
    _legacy_test_battery: bool = False,
) -> Tuple[FleetManagerCore, List[str]]:
    """Construct FleetManagerCore and register all robots and stations dynamically from fleet.yaml."""
    from fleet_config.loader import load_config

    cfg = load_config(fleet_config_path)
    safe_station = cfg.stations.charging_stations[0]
    safe_charge_pose = Pose2D(
        x=safe_station.pose.x,
        y=safe_station.pose.y,
        yaw=safe_station.pose.yaw,
    )

    if route_provider is None:
        route_provider = CachedRouteDistanceProvider(RouteCache())

    core = FleetManagerCore(
        route_provider=route_provider,
        safe_charge_station_pose=safe_charge_pose,
        emergency_soc_percent=cfg.policies.emergency_soc_percent,
        safety_margin_wh=cfg.policies.safety_margin_wh,
        low_soc_percent=None if _legacy_test_battery else cfg.policies.low_soc_percent,
        charge_target_soc_percent=cfg.policies.charge_target_soc_percent,
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
        core.register_robot(
            robot_id=r.id, specs=specs, initial_pose=init_pose,
            requires_battery_telemetry=not _legacy_test_battery,
        )
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

    for area in cfg.stations.safe_waiting_areas:
        core.register_station(
            station_id=area.id,
            station_type=StationType.SAFE_WAITING,
            pose=Pose2D(x=area.pose.x, y=area.pose.y, yaw=area.pose.yaw),
        )

    return core, robot_ids
