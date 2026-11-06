"""Read-only ASGI surface for the private latest-value feed."""
import argparse
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
import time
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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


def create_app(path, *, origins, max_clients=MAX_CLIENTS, bridge_url=None, scene_topics=None):
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
    app.add_middleware(CORSMiddleware, allow_origins=list(origins), allow_methods=["GET"], allow_headers=[])

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
    args = parser.parse_args()
    bridge_url = None
    topics = None
    if args.scene_port is not None:
        if args.fleet is None or not 1 <= args.scene_port <= 65535:
            parser.error("--scene-port requires a valid port and --fleet")
        from fleet_config import load_config

        fleet = load_config(args.fleet, schema_path=args.fleet.with_name("fleet.schema.json"))
        topics = {robot.id: robot.namespace + "/plan" for robot in fleet.robots}
        bridge_url = f"ws://scene:{args.scene_port}/telemetry/fleet"
    uvicorn.run(
        create_app(args.snapshot, origins=frozenset(args.origin), bridge_url=bridge_url, scene_topics=topics),
        host="0.0.0.0" if args.container_bind else "127.0.0.1", port=args.port,
        proxy_headers=False, server_header=False, ws="websockets", ws_max_size=1024, ws_max_queue=1,
        ws_per_message_deflate=False, limit_concurrency=64, timeout_graceful_shutdown=3,
    )


if __name__ == "__main__":
    main()
