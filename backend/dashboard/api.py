"""Read-only ASGI surface for the private latest-value feed."""
import argparse
import os
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
import json
import time
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .models import MAX_BYTES, SOURCE_TTL_NS, SourceSnapshot, WireSnapshot
from .scene_stream import PROTOCOL, send_operations

POLL_SEC = 0.10
SEND_TIMEOUT_SEC = 1.0
MAX_CLIENTS = 16


def read_source(path):
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) <= MAX_BYTES:
            return SourceSnapshot.model_validate_json(data)
    except (OSError, ValidationError):
        pass
    return None


class Feed:
    def __init__(self, path, *, clock=time.monotonic_ns):
        self.path = Path(path)
        self.session = str(uuid4())
        self.clock = clock
        self.captured_ns = 0
        self.snapshot = None
        self.payload = None

    def update(self, source):
        if source is None or not 0 <= self.clock() - source.captured_monotonic_ns <= SOURCE_TTL_NS:
            return
        previous = self.snapshot
        fleet = source.fleet
        if source.captured_monotonic_ns <= self.captured_ns or (
            previous is not None and previous.source_session_id == fleet.source_session_id
            and previous.sequence >= fleet.sequence
        ):
            return
        self.snapshot = WireSnapshot(**fleet.model_dump(), backend_session_id=self.session)
        self.payload = self.snapshot.model_dump_json()
        self.captured_ns = source.captured_monotonic_ns

    def current(self):
        if self.snapshot is not None and 0 <= self.clock() - self.captured_ns <= SOURCE_TTL_NS:
            return self.snapshot
        return None

    async def run(self):
        while True:
            self.update(await asyncio.to_thread(read_source, self.path))
            await asyncio.sleep(POLL_SEC)


async def send_latest(socket, feed, *, poll_sec=POLL_SEC):
    receiver = asyncio.create_task(socket.receive())
    last = None
    close_code = None
    try:
        while True:
            current = feed.current()
            if current is None or (last and current.source_session_id != last.source_session_id):
                close_code = 1013
                break
            if current is not last:
                await asyncio.wait_for(socket.send_text(feed.payload), SEND_TIMEOUT_SEC)
                last = current
            done, _ = await asyncio.wait((receiver,), timeout=poll_sec)
            if done:
                if receiver.result()["type"] != "websocket.disconnect":
                    close_code = 1008
                break
    except asyncio.TimeoutError:
        close_code = 1013
    except (WebSocketDisconnect, OSError):
        return
    finally:
        receiver.cancel()
        with suppress(asyncio.CancelledError, WebSocketDisconnect, OSError):
            await receiver
    if close_code is not None:
        with suppress(asyncio.TimeoutError, WebSocketDisconnect, OSError):
            await asyncio.wait_for(socket.close(close_code), SEND_TIMEOUT_SEC)


def create_app(path, *, origins, max_clients=MAX_CLIENTS, bridge_url=None, scene_topics=None, fleet_config=None,
               task_socket=None, costmap_path=None, battery_gateway=None, battery_token=None):
    origins = frozenset(origins)
    for origin in origins:
        url = urlsplit(origin)
        if (url.scheme not in ("http", "https") or url.hostname not in ("127.0.0.1", "localhost")
                or url.username is not None or url.path or url.query or url.fragment
                or origin != f"{url.scheme}://{url.netloc}"):
            raise ValueError("C5 requires an exact loopback browser origin")
    if not origins:
        raise ValueError("C5 requires at least one browser origin")
    feed = Feed(path)
    clients = 0
    battery_controls = None
    if battery_gateway is not None:
        from .battery_control import BatteryControls
        if fleet_config is None or not battery_token:
            raise ValueError("Battery controls require authoritative fleet config and authentication")
        battery_controls = BatteryControls(fleet_config, battery_gateway)

    @asynccontextmanager
    async def lifespan(_app):
        worker = asyncio.create_task(feed.run())
        try:
            yield
        finally:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.add_middleware(CORSMiddleware, allow_origins=list(origins), allow_methods=["GET", "POST"] if task_socket or battery_controls else ["GET"],
                       allow_headers=["Content-Type", "Authorization"])

    if battery_controls:
        from .battery_control import install_routes
        install_routes(app, battery_controls, battery_token, origins)

    @app.middleware("http")
    async def prevent_cache(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    def current():
        snapshot = feed.current()
        if snapshot is None:
            raise HTTPException(503, "Fleet data unavailable")
        return snapshot

    def envelope(snapshot, key, data):
        return {**snapshot.model_dump(include={"schema_version", "source_session_id",
                                               "backend_session_id", "sequence", "generated_at_utc"}),
                key: data}

    @app.get("/api/health")
    async def health():
        return {"schema_version": 1, "backend_session_id": feed.session,
                "source": "LIVE" if feed.current() else "UNAVAILABLE"}

    @app.get("/api/fleet", response_model=WireSnapshot)
    async def fleet():
        return current()

    @app.get("/api/robots")
    async def robots():
        snapshot = current()
        return envelope(snapshot, "robots", snapshot.robots)

    @app.get("/api/robots/{robot_id}")
    async def robot(robot_id: str):
        snapshot = current()
        for record in snapshot.robots:
            if record.robot_id == robot_id:
                return envelope(snapshot, "robot", record)
        raise HTTPException(404, "Robot unavailable")

    @app.get("/api/tasks")
    async def tasks():
        snapshot = current()
        return {**envelope(snapshot, "tasks", snapshot.tasks), "task_counts": snapshot.task_counts}

    @app.get("/api/stations")
    async def stations():
        snapshot = current()
        return envelope(snapshot, "stations", snapshot.stations)

    def warehouse_payload():
        from fleet_config.occupancy import profile_digest

        if fleet_config is None or fleet_config.warehouse is None:
            return {"layout": None}
        snapshot = current()
        groups = (
            ("CHARGING", fleet_config.stations.charging_stations),
            ("PARKING", fleet_config.stations.parking_stations),
            ("SAFE_WAITING", fleet_config.stations.safe_waiting_areas),
        )
        expected = {(item.id, kind, item.pose.x, item.pose.y, item.pose.yaw)
                    for kind, stations in groups for item in stations}
        actual = {(item.station_id, item.station_type, item.pose.x, item.pose.y, item.pose.yaw)
                  for item in snapshot.stations if item.pose and item.pose.frame_id == "map"}
        compatible = (snapshot.map_frame == fleet_config.warehouse.frame_id
                      and len(snapshot.stations) == len(expected) and actual == expected
                      and {robot.robot_id for robot in snapshot.robots} == {robot.id for robot in fleet_config.robots})
        return {**envelope(snapshot, "layout", fleet_config.warehouse.scene_payload() if compatible else None),
                "profile_mismatch": not compatible, "profile_digest": profile_digest(fleet_config)}

    @app.get("/api/warehouse-layout")
    async def warehouse_layout():
        return warehouse_payload()

    @app.get("/api/task-catalog")
    async def task_catalog():
        payload = warehouse_payload()
        layout = payload["layout"]
        return {**payload, "enabled": bool(layout and task_socket and Path(task_socket).is_socket())}

    async def submit_task(request: Request):
        from .task_ingress import MAX_REQUEST_BYTES, TaskRequest, endpoints, send_task

        if request.headers.get("origin") not in origins or request.headers.get("content-type") != "application/json":
            raise HTTPException(403, "Exact browser origin and JSON content type required")
        payload = warehouse_payload()
        if payload["layout"] is None or task_socket is None:
            raise HTTPException(503, "Task ingress unavailable")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_REQUEST_BYTES:
                raise HTTPException(413, "Task request too large")
        try:
            command = TaskRequest.model_validate_json(bytes(raw))
            if (command.source_session_id != payload["source_session_id"] or
                    command.profile_digest != payload["profile_digest"]):
                raise HTTPException(409, "Fleet session changed")
            endpoints(fleet_config, command)
        except (ValueError, ValidationError) as error:
            raise HTTPException(422, "Invalid task endpoints, roles or request") from error
        try:
            response = await asyncio.wait_for(send_task(task_socket, command), timeout=6)
        except (OSError, ValueError, asyncio.TimeoutError) as error:
            raise HTTPException(503, "Task acknowledgement unavailable. Retry with the same request ID") from error
        if "error" in response:
            raise HTTPException(409, response["error"])
        return JSONResponse(response, status_code=200 if response["outcome"] == "DUPLICATE" else 201)

    if task_socket is not None:
        app.add_api_route("/api/tasks", submit_task, methods=["POST"])

    @app.get("/api/warehouse-costmap")
    async def warehouse_costmap():
        from fleet_config.occupancy import encode_grid, profile_digest, raster

        if warehouse_payload()["layout"] is None:
            raise HTTPException(503, "Warehouse profile unavailable")
        digest = profile_digest(fleet_config)
        if costmap_path is not None:
            try:
                if Path(costmap_path).stat().st_size > 16_000_000:
                    raise ValueError("Costmap capture exceeds size limit")
                recorded = json.loads(Path(costmap_path).read_text())
                if recorded["profile_digest"] != digest or recorded["source"] != "nav2_recorded":
                    raise ValueError("Costmap profile mismatch")
                return recorded
            except (OSError, ValueError, KeyError) as error:
                raise HTTPException(503, "Recorded costmap unavailable or profile mismatch") from error
        metadata, cells = raster(fleet_config.warehouse)
        return {**encode_grid(metadata, cells, "generated_occupancy"), "profile_digest": digest}

    @app.websocket("/ws/fleet")
    async def stream(socket: WebSocket):
        nonlocal clients
        if socket.headers.get("origin") not in origins or clients >= max_clients:
            await socket.close(1008)
            return
        clients += 1
        try:
            if PROTOCOL in socket.scope["subprotocols"]:
                await socket.accept(subprotocol=PROTOCOL)
                await send_operations(socket, feed, bridge_url=bridge_url, topics=scene_topics,
                                      poll_sec=POLL_SEC, send_timeout=SEND_TIMEOUT_SEC)
            else:
                await socket.accept()
                await send_latest(socket, feed)
        finally:
            clients -= 1

    return app


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="Read-only local fleet dashboard API")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--origin", action="append", required=True)
    parser.add_argument("--container-bind", action="store_true")
    parser.add_argument("--scene-port", type=int)
    parser.add_argument("--fleet", type=Path)
    parser.add_argument("--task-socket", type=Path)
    parser.add_argument("--costmap", type=Path)
    args = parser.parse_args()
    bridge_url = None
    topics = None
    config = None
    if args.fleet is not None:
        from fleet_config import load_config

        config = load_config(args.fleet, schema_path=args.fleet.with_name("fleet.schema.json"))
    if args.scene_port is not None:
        if config is None or not 1 <= args.scene_port <= 65535:
            parser.error("--scene-port requires a valid port and --fleet")
        topics = {robot.id: robot.namespace + "/plan" for robot in config.robots}
        bridge_url = f"ws://scene:{args.scene_port}/telemetry/fleet"
    gateway = None
    token = os.environ.get("FLEET_SIM_BATTERY_TOKEN")
    if os.environ.get("FLEET_SIM_BATTERY_CONTROL") == "1":
        if config is None or not token or len(token) < 32:
            parser.error("Simulation battery controls require --fleet and FLEET_SIM_BATTERY_TOKEN (32+ chars)")
        from .battery_ros import BatteryROSGateway
        gateway = BatteryROSGateway(config)
    try:
        uvicorn.run(
            create_app(args.snapshot, origins=frozenset(args.origin), bridge_url=bridge_url, scene_topics=topics,
                       fleet_config=config, task_socket=args.task_socket, costmap_path=args.costmap,
                       battery_gateway=gateway, battery_token=token),
            host="0.0.0.0" if args.container_bind else "127.0.0.1", port=args.port,
            proxy_headers=False, server_header=False, ws="websockets", ws_max_size=1024, ws_max_queue=1,
            ws_per_message_deflate=False, limit_concurrency=64, timeout_graceful_shutdown=3,
        )
    finally:
        if gateway:
            gateway.close()


if __name__ == "__main__":
    main()
