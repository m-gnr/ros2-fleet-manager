"""Authoring format for a warehouse with dimensions defined once."""

import re
from math import isclose
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .models import ChargingStation, Contract, Fleet, FleetConfig, Policies, Robot, Station
from .warehouse import Area, ExampleTask, TransferPoint, WarehouseDoor, WarehouseRack, WarehouseZone

XAxis = float | Annotated[str, Field(pattern=r"^[WE]([+-][0-9]+(\.[0-9]+)?)?$")]
YAxis = float | Annotated[str, Field(pattern=r"^[SN]([+-][0-9]+(\.[0-9]+)?)?$")]


class AnchoredPose(Contract):
    x: XAxis
    y: YAxis
    yaw: float


class AnchoredRect(Contract):
    x_min: XAxis
    x_max: XAxis
    y_min: YAxis
    y_max: YAxis


class AnchoredRobot(Robot):
    initial_pose: AnchoredPose


class AnchoredStation(Station):
    pose: AnchoredPose


class AnchoredDock(ChargingStation):
    pose: AnchoredPose


class AnchoredStations(Contract):
    charging_stations: list[AnchoredDock]
    parking_stations: list[AnchoredStation]
    safe_waiting_areas: list[AnchoredStation]


class AnchoredRack(WarehouseRack):
    bounds: AnchoredRect


class AnchoredAisle(Area):
    bounds: AnchoredRect
    axis: Literal["x", "y"]
    role: Literal["main", "cross", "access"] | None = Field(default_factory=lambda: None)


class AnchoredPoint(Contract):
    x: XAxis
    y: YAxis


class AnchoredZone(WarehouseZone):
    bounds: AnchoredRect
    callout: AnchoredPoint | None = Field(default_factory=lambda: None)


class AnchoredTransfer(TransferPoint):
    pose: AnchoredPose


class WarehouseSource(Contract):
    frame_id: Literal["map"]
    grid_m: Annotated[float, Field(gt=0)]
    width: Annotated[float, Field(gt=0)]
    depth: Annotated[float, Field(gt=0)]
    wall_thickness_m: Annotated[float, Field(gt=0)]
    wall_height_m: Annotated[float, Field(gt=0)]
    door: WarehouseDoor
    racks: list[AnchoredRack]
    aisles: list[AnchoredAisle]
    zones: list[AnchoredZone]
    transfer_points: list[AnchoredTransfer]
    dock_approach_m: Annotated[float, Field(ge=2)]
    dock_rack_clearance_m: Annotated[float, Field(ge=2)]
    approach_clearance_m: Annotated[float, Field(gt=0)] | None = Field(default_factory=lambda: None)
    example_tasks: list[ExampleTask] = Field(default_factory=list)


class AnchoredFleetConfig(Contract):
    fleet: Fleet
    robots: list[AnchoredRobot]
    stations: AnchoredStations
    policies: Policies
    warehouse: WarehouseSource

    def resolve(self):
        data = self.model_dump()
        plan = data["warehouse"]
        width, depth = plan.pop("width"), plan.pop("depth")
        edges = {"W": -width / 2, "E": width / 2, "S": -depth / 2, "N": depth / 2}
        plan["bounds"] = {"x_min": edges["W"], "x_max": edges["E"],
                          "y_min": edges["S"], "y_max": edges["N"]}
        def resolve(value):
            if isinstance(value, str) and re.fullmatch(r"[WESN]([+-][0-9]+(\.[0-9]+)?)?", value):
                return edges[value[0]] + float(value[1:] or 0)
            return value

        def resolve_fields(fields):
            return {key: resolve(value) for key, value in fields.items()}

        for area in plan["racks"] + plan["aisles"] + plan["zones"]:
            area["bounds"] = resolve_fields(area["bounds"])
            if area.get("callout"):
                area["callout"] = resolve_fields(area["callout"])
        for point in plan["transfer_points"]:
            point["pose"] = resolve_fields(point["pose"])
        for robot in data["robots"]:
            robot["initial_pose"] = resolve_fields(robot["initial_pose"])
        for group in data["stations"].values():
            for station in group:
                station["pose"] = resolve_fields(station["pose"])
        resolved = FleetConfig.model_validate(data)
        grid = self.warehouse.grid_m
        def on_grid(n):
            return isclose(n / grid, round(n / grid), rel_tol=0, abs_tol=1e-8)
        poses = [robot.initial_pose for robot in resolved.robots] + [
            station.pose for group in (resolved.stations.charging_stations, resolved.stations.parking_stations,
                                       resolved.stations.safe_waiting_areas) for station in group
        ]
        if any(not (on_grid(p.x) and on_grid(p.y)) for p in poses):
            raise ValueError("robot and station positions must align with the warehouse grid")
        return resolved
