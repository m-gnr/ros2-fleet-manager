"""Map-space warehouse geometry shared by renderers and future map generators."""

from math import hypot, isclose
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

GridSide = Literal["north", "south", "east", "west"]
TransferKind = Literal["pickup", "dropoff"]
Positive = Annotated[float, Field(gt=0)]


class Geometry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class MapRectangle(Geometry):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @model_validator(mode="after")
    def ordered(self):
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("rectangle must have positive width and depth")
        return self

    def contains(self, x, y, margin=0):
        return (self.x_min + margin <= x <= self.x_max - margin
                and self.y_min + margin <= y <= self.y_max - margin)

    def overlaps(self, other):
        return (self.x_min < other.x_max and other.x_min < self.x_max
                and self.y_min < other.y_max and other.y_min < self.y_max)


class Area(Geometry):
    id: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    label: str = Field(min_length=1)
    bounds: MapRectangle


class WarehouseDoor(Geometry):
    side: GridSide
    center: float
    width: Annotated[float, Field(ge=1)]


class WarehouseRack(Geometry):
    id: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    bounds: MapRectangle
    height: Positive
    bays: Annotated[int, Field(ge=1, le=12)]


class WarehouseAisle(Area):
    axis: Literal["x", "y"]

    @model_validator(mode="after")
    def minimum_width(self):
        b = self.bounds
        width = b.y_max - b.y_min if self.axis == "x" else b.x_max - b.x_min
        if width < 1:
            raise ValueError(f"{self.id}: clear aisle width must be at least 1 m")
        return self


class MapPoint(Geometry):
    x: float
    y: float


class WarehouseZone(Area):
    kind: Literal["pickup", "dropoff", "charging", "parking"]
    callout: MapPoint | None = Field(default_factory=lambda: None)


class TransferPose(Geometry):
    x: float
    y: float
    yaw: float


class TransferPoint(Geometry):
    id: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_-]*$")
    kind: TransferKind
    pose: TransferPose


class WarehouseLayout(Geometry):
    frame_id: Literal["map"]
    grid_m: Positive
    bounds: MapRectangle
    wall_thickness_m: Positive
    wall_height_m: Positive
    door: WarehouseDoor
    racks: Annotated[list[WarehouseRack], Field(min_length=1, max_length=32)]
    aisles: Annotated[list[WarehouseAisle], Field(min_length=3, max_length=24)]
    zones: Annotated[list[WarehouseZone], Field(min_length=4, max_length=4)]
    transfer_points: Annotated[list[TransferPoint], Field(min_length=4, max_length=8)]
    dock_approach_m: Positive | None = Field(default_factory=lambda: None)
    dock_rack_clearance_m: Positive | None = Field(default_factory=lambda: None)

    def zone(self, kind):
        return next(zone.bounds for zone in self.zones if zone.kind == kind)

    def walls(self):
        """Physical wall rectangles, including the door's two jamb-side sections."""
        b, half = self.bounds, self.wall_thickness_m / 2
        for side, edge, start, end, along_x in (
            ("north", b.y_max, b.x_min, b.x_max, True),
            ("south", b.y_min, b.x_min, b.x_max, True),
            ("west", b.x_min, b.y_min, b.y_max, False),
            ("east", b.x_max, b.y_min, b.y_max, False),
        ):
            if side == self.door.side:
                center, gap = self.door.center, self.door.width / 2
                segments = [(start, center - gap), (center + gap, end)]
            else:
                segments = [(start, end)]
            for index, (lo, hi) in enumerate(segments, 1):
                bounds = (MapRectangle(x_min=lo, x_max=hi, y_min=edge-half, y_max=edge+half) if along_x
                          else MapRectangle(x_min=edge-half, x_max=edge+half, y_min=lo, y_max=hi))
                yield {"id": f"wall_{side}_{index}", "side": side, "edge": edge, "bounds": bounds}

    def scene_payload(self):
        walls = [{**wall, "bounds": wall["bounds"].model_dump(mode="json")} for wall in self.walls()]
        return {**self.model_dump(mode="json"), "walls": walls}

    def check_service(self, docks, parking):
        if self.dock_approach_m is None or self.dock_rack_clearance_m is None:
            return
        from math import cos, sin
        approaches = []
        for dock in docks:
            x, y, yaw = dock.pose.x, dock.pose.y, dock.pose.yaw
            dx, dy = cos(yaw), sin(yaw)
            if min(abs(dx), abs(dy)) > 1e-8:
                raise ValueError(f"{dock.id}: docking direction must align with a grid axis")
            clear_length = self.dock_approach_m + dock.tolerance_radius
            end_x = x - clear_length * dx
            end_y = y - clear_length * dy
            approach = MapRectangle(x_min=min(x, end_x) - .5, x_max=max(x, end_x) + .5,
                                    y_min=min(y, end_y) - .5, y_max=max(y, end_y) + .5)
            if not self.bounds.contains(approach.x_min, approach.y_min) or not self.bounds.contains(
                approach.x_max, approach.y_max
            ):
                raise ValueError(f"{dock.id}: dock approach leaves the warehouse")
            for rack in self.racks:
                b = rack.bounds
                pad = dock.tolerance_radius
                distance = hypot(max(b.x_min - (x + pad), x - pad - b.x_max, 0),
                                 max(b.y_min - (y + pad), y - pad - b.y_max, 0))
                if distance < self.dock_rack_clearance_m or approach.overlaps(b):
                    raise ValueError(f"{dock.id}: rack clearance or dock approach is blocked")
            if any(approach.overlaps(other) for other in approaches):
                raise ValueError(f"{dock.id}: docking approaches overlap")
            approaches.append(approach)
            if any(approach.contains(p.pose.x, p.pose.y, -.45) for p in parking):
                raise ValueError(f"{dock.id}: parking blocks the approach")

    @model_validator(mode="after")
    def aligned(self):
        entries = self.racks + self.aisles + self.zones + self.transfer_points
        if len({item.id for item in entries}) != len(entries):
            raise ValueError("warehouse IDs must be unique")
        if {zone.kind for zone in self.zones} != {"pickup", "dropoff", "charging", "parking"}:
            raise ValueError("warehouse requires one zone of each kind")

        def on_grid(*values):
            return all(isclose(value / self.grid_m, round(value / self.grid_m), abs_tol=1e-8) for value in values)

        for area in [self.bounds] + [item.bounds for item in self.racks + self.aisles + self.zones]:
            if not on_grid(area.x_min, area.x_max, area.y_min, area.y_max):
                raise ValueError("warehouse rectangles must use grid_m")
            if not (self.bounds.contains(area.x_min, area.y_min)
                    and self.bounds.contains(area.x_max, area.y_max)):
                raise ValueError("warehouse rectangle is outside the perimeter")

        lower, upper = ((self.bounds.x_min, self.bounds.x_max) if self.door.side in ("north", "south")
                        else (self.bounds.y_min, self.bounds.y_max))
        a, b = self.door.center - self.door.width / 2, self.door.center + self.door.width / 2
        if not lower < a < b < upper or not on_grid(a, b):
            raise ValueError("warehouse door must leave a wall on both sides and align to the grid")

        if sum(aisle.axis == "x" for aisle in self.aisles) < 2 or not any(
            aisle.axis == "y" and sum(aisle.bounds.overlaps(other.bounds)
                                     for other in self.aisles if other.axis == "x") >= 2
            for aisle in self.aisles
        ):
            raise ValueError("warehouse requires two parallel aisles linked by a cross aisle")

        for index, rack in enumerate(self.racks):
            if any(rack.bounds.overlaps(area.bounds)
                   for area in self.racks[index + 1:] + self.aisles + self.zones):
                raise ValueError(f"{rack.id}: rack overlaps an aisle, zone or rack")
        for index, zone in enumerate(self.zones):
            if zone.callout:
                x, y = zone.callout.x, zone.callout.y
                if (not on_grid(x, y) or not self.bounds.contains(x, y, .15)
                        or any(item.bounds.contains(x, y) for item in self.zones + self.racks)):
                    raise ValueError(f"{zone.id}: callout anchor must use free grid floor outside zones")
            if any(zone.bounds.overlaps(other.bounds) for other in self.zones[index + 1:]):
                raise ValueError(f"{zone.id}: operation zones overlap")

        for kind in ("pickup", "dropoff"):
            points = [point for point in self.transfer_points if point.kind == kind]
            if not 2 <= len(points) <= 4:
                raise ValueError(f"warehouse requires two to four {kind} points")
            for point in points:
                if not on_grid(point.pose.x, point.pose.y) or not self.zone(kind).contains(point.pose.x, point.pose.y, .4):
                    raise ValueError(f"{point.id}: transfer pose must be on the grid inside its zone")
        return self
