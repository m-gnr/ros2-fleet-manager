"""Authenticated simulation controls, independent of Fleet Manager domain writes."""
import asyncio
import secrets
import math
from typing import Literal

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field


class BatteryCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    request_id: str = Field(min_length=1, max_length=128)
    robot_id: str | None = Field(default=None, max_length=128)
    all_robots: bool = False
    confirm_bulk_soc: bool = False
    safe_test_environment: bool = False
    soc_percent: float | None = Field(default=None, ge=0, le=100)
    mode: Literal["NORMAL", "FAST"] | None = None
    discharge_minutes: float = Field(default=10.0, ge=1, le=1440)
    charge_minutes: float = Field(default=10.0, ge=1, le=1440)
    # The client confirms the exact publisher session shown during selection.
    sessions: dict[str, str] = Field(default_factory=dict, max_length=256)


class BatteryControls:
    def __init__(self, config, gateway):
        self.config, self.gateway = config, gateway
        self.robots = {robot.id: robot for robot in config.robots}
        self.locks = {robot.id: asyncio.Lock() for robot in config.robots}

    async def inspect(self, robot_id):
        robot = self.robots[robot_id]
        try:
            state = await self.gateway.read(robot)
            model = self.config.fleet.battery_models[robot.battery_model]
            if state["robot_id"] != robot_id or state["capacity_wh"] != model.usable_capacity_wh:
                raise ValueError("Robot identity or configured capacity mismatch")
            numbers = ("soc_percent", "energy_wh", "capacity_wh", "idle_power_w", "charge_power_w",
                       "consumption_wh_per_meter", "discharge_minutes", "charge_minutes")
            if (not all(math.isfinite(state[k]) and state[k] >= 0 for k in numbers)
                    or not 0 <= state["soc_percent"] <= 100 or state["capacity_wh"] <= 0
                    or not math.isclose(state["energy_wh"], state["capacity_wh"] * state["soc_percent"] / 100,
                                        rel_tol=1e-6, abs_tol=1e-6)):
                raise ValueError("Inconsistent simulator readback")
            return dict(robot_id=robot_id, namespace=robot.namespace, available=True, state=state)
        except Exception as error:
            return dict(robot_id=robot_id, namespace=robot.namespace, available=False, error=str(error))

    async def inventory(self):
        return {"enabled": True, "robots": await asyncio.gather(*(self.inspect(r) for r in self.robots))}

    async def apply(self, command):
        if not command.safe_test_environment:
            raise HTTPException(409, "Safe simulation test environment confirmation required")
        if command.all_robots == (command.robot_id is not None):
            raise HTTPException(422, "Choose one robot or the authoritative full inventory")
        if command.soc_percent is None and command.mode is None:
            raise HTTPException(422, "No battery change requested")
        if command.all_robots and command.soc_percent is not None and not command.confirm_bulk_soc:
            raise HTTPException(409, "Explicit bulk SoC confirmation required")
        ids = list(self.robots) if command.all_robots else [command.robot_id]
        if any(r not in self.robots for r in ids):
            raise HTTPException(404, "Unknown robot ID")
        if set(command.sessions) != set(ids):
            raise HTTPException(409, "Confirm the current session for every target robot")

        async def one(robot_id):
            async with self.locks[robot_id]:
                record = await self.inspect(robot_id)
                if not record["available"]:
                    return dict(robot_id=robot_id, outcome="REJECTED", error=record["error"])
                before = record["state"]
                if command.sessions[robot_id] != before["session_id"]:
                    return dict(robot_id=robot_id, outcome="REJECTED", error="Battery session changed")
                try:
                    applied = await self.gateway.apply(self.robots[robot_id], command, before["session_id"])
                    if applied["robot_id"] != robot_id or applied["session_id"] != before["session_id"]:
                        raise ValueError("Applied robot identity or session mismatch")
                    if command.soc_percent is not None and not math.isclose(applied["soc_percent"], command.soc_percent, abs_tol=1e-6):
                        raise ValueError("Requested SoC was not applied")
                    if command.mode is not None:
                        model = self.config.fleet.battery_models[self.robots[robot_id].battery_model]
                        idle, charge = model.idle_power_w, model.charge_power_w
                        if command.mode == "FAST":
                            idle = model.usable_capacity_wh * .75 * 60 / command.discharge_minutes
                            charge = idle + model.usable_capacity_wh * .55 * 60 / command.charge_minutes
                        expected = dict(mode=command.mode, idle_power_w=idle, charge_power_w=charge,
                                        consumption_wh_per_meter=model.consumption_wh_per_meter,
                                        discharge_minutes=command.discharge_minutes if command.mode == "FAST" else 0.,
                                        charge_minutes=command.charge_minutes if command.mode == "FAST" else 0.)
                        if any(applied[k] != v for k, v in expected.items()):
                            raise ValueError("Requested profile was not applied")
                    # A separate read proves the effective profile, independently of the apply reply.
                    readback = await self.gateway.read(self.robots[robot_id])
                    keys = ("revision", "mode", "idle_power_w", "charge_power_w", "consumption_wh_per_meter",
                            "discharge_minutes", "charge_minutes", "capacity_wh", "session_id", "robot_id")
                    if any(applied[k] != readback[k] for k in keys):
                        raise ValueError("Readback changed; applied parameters not verified")
                    return dict(robot_id=robot_id, outcome="VERIFIED", applied=applied, readback=readback)
                except Exception as error:
                    # The service might have applied before a lost acknowledgement. Never retry automatically.
                    return dict(robot_id=robot_id, outcome="UNVERIFIED", error=str(error))
        results = await asyncio.gather(*(one(r) for r in ids))
        return dict(request_id=command.request_id, atomic=False, results=results,
                    all_verified=all(r["outcome"] == "VERIFIED" for r in results))


def install_routes(app, controls, token, origins):
    if len(token) < 32:
        raise ValueError("Battery controls require a secret token of at least 32 characters")

    def authorize(request, *, mutation=False):
        supplied = request.headers.get("authorization", "")
        if not secrets.compare_digest(supplied.encode("utf-8"), ("Bearer " + token).encode("utf-8")):
            raise HTTPException(401, "Simulation control authentication required")
        if mutation and (request.headers.get("origin") not in origins or
                         request.headers.get("content-type") != "application/json"):
            raise HTTPException(403, "Exact browser origin and JSON required")

    @app.get("/api/sim/batteries")
    async def inventory(request: Request):
        authorize(request)
        return await controls.inventory()

    @app.post("/api/sim/batteries")
    async def apply(request: Request):
        authorize(request, mutation=True)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 32768:
                raise HTTPException(413, "Battery request too large")
        try:
            command = BatteryCommand.model_validate_json(raw)
        except ValueError as error:
            raise HTTPException(422, "Invalid battery parameters") from error
        return await controls.apply(command)
