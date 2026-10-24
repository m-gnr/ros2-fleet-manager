"""Required configuration fields; no implicit operational defaults."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
RosName = Annotated[str, Field(pattern=r"^/[A-Za-z_][A-Za-z0-9_]*(/[A-Za-z_][A-Za-z0-9_]*)*$")]
Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
Positive = Annotated[float, Field(gt=0)]
NonNegative = Annotated[float, Field(ge=0)]
Percent = Annotated[float, Field(ge=0, le=100)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Pose(Contract):
    x: float = Field(description="X position in map frame, metres.")
    y: float = Field(description="Y position in map frame, metres.")
    yaw: float = Field(description="Heading in map frame, radians.")


class BatteryModel(Contract):
    usable_capacity_wh: Positive
    consumption_wh_per_meter: Positive
    idle_power_w: NonNegative
    charge_power_w: Positive


class Fleet(Contract):
    name: Text
    map_path: Text = Field(description="File path relative to the fleet YAML directory.")
    use_sim_time: Literal[True]
    battery_models: Annotated[dict[Identifier, BatteryModel], Field(min_length=1)]

    @field_validator("use_sim_time", mode="before")
    @classmethod
    def boolean_clock(cls, value):
        if type(value) is not bool:
            raise ValueError("use_sim_time must be a boolean")
        return value


class Robot(Contract):
    id: Identifier
    name: Text
    namespace: RosName
    initial_pose: Pose
    battery_model: Identifier
    nav2_action_name: RosName
    nav2_params_path: Text = Field(description="Nav2 template path relative to fleet YAML.")

    @model_validator(mode="after")
    def isolated_action(self):
        if not self.nav2_action_name.startswith(self.namespace + "/"):
            raise ValueError("nav2_action_name must belong to the robot namespace")
        return self


class Station(Contract):
    id: Identifier
    pose: Pose


class ChargingStation(Station):
    tolerance_radius: Positive = Field(description="Dock contact region radius, metres.")


class Stations(Contract):
    charging_stations: Annotated[list[ChargingStation], Field(min_length=1)]
    parking_stations: list[Station]
    safe_waiting_areas: list[Station]


class Policies(Contract):
    assignment: Literal["priority_fifo_nearest_eligible"]
    preemption_priority: Literal["HIGH"]
    max_preemptions: Literal[2]
    extra_swap_enabled: Literal[False]
    automatic_retry: Literal[False]
    automatic_reassignment: Literal[False]
    charge_target_soc_percent: Literal[80]
    charge_queue: Literal["lowest_soc_fifo"]
    emergency_soc_percent: Percent
    low_soc_percent: Percent
    safety_margin_wh: NonNegative

    @field_validator("extra_swap_enabled", "automatic_retry", "automatic_reassignment", mode="before")
    @classmethod
    def boolean_policy(cls, value):
        if type(value) is not bool:
            raise ValueError("policy flag must be a boolean")
        return value

    @model_validator(mode="after")
    def energy_thresholds(self):
        if not self.emergency_soc_percent < self.low_soc_percent < self.charge_target_soc_percent:
            raise ValueError("require emergency_soc_percent < low_soc_percent < charge_target_soc_percent")
        return self


class FleetConfig(Contract):
    fleet: Fleet
    robots: Annotated[list[Robot], Field(min_length=1)]
    stations: Stations
    policies: Policies

    @model_validator(mode="after")
    def references_and_ownership(self):
        for field in ("id", "name", "namespace", "nav2_action_name"):
            values = [getattr(robot, field) for robot in self.robots]
            if len(set(values)) != len(values):
                raise ValueError(f"robots: duplicate {field}")
        namespaces = [robot.namespace for robot in self.robots]
        for index, namespace in enumerate(namespaces):
            for other in namespaces[index + 1:]:
                if namespace.startswith(other + "/") or other.startswith(namespace + "/"):
                    raise ValueError("robots: nested namespaces overlap")
        starts = [(r.initial_pose.x, r.initial_pose.y) for r in self.robots]
        if len(set(starts)) != len(starts):
            raise ValueError("robots: duplicate initial position")
        for robot in self.robots:
            if robot.battery_model not in self.fleet.battery_models:
                raise ValueError(f"robots.{robot.id}.battery_model: unknown model {robot.battery_model}")
        for name, battery in self.fleet.battery_models.items():
            available = battery.usable_capacity_wh * (1 - self.policies.emergency_soc_percent / 100)
            if self.policies.safety_margin_wh >= available:
                raise ValueError(f"fleet.battery_models.{name}: safety margin exhausts usable energy after reserve")
        stations = (self.stations.charging_stations + self.stations.parking_stations
                    + self.stations.safe_waiting_areas)
        ids = [station.id for station in stations]
        if len(set(ids)) != len(ids):
            raise ValueError("stations: duplicate resource id across station groups")
        poses = [(station.pose.x, station.pose.y) for station in stations]
        if len(set(poses)) != len(poses):
            raise ValueError("stations: resources share the same physical position")
        return self
