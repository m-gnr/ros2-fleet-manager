#!/usr/bin/env python3
"""Read-only API and WebSocket timing capture for one owned C5 demo session."""

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.request import urlopen

from websockets.asyncio.client import connect


def read_api(port):
    with urlopen(f"http://127.0.0.1:{port}/api/fleet", timeout=2) as response:
        return json.load(response)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path, help="Launcher evidence directory")
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds", type=float, default=45)
    args = parser.parse_args()
    session = json.loads((args.session / "session.json").read_text())
    if Path(session["workspace"]).resolve() != Path(__file__).resolve().parents[1]:
        parser.error("Session belongs to another workspace")
    port, origin = session["api_port"], f'http://127.0.0.1:{session["ui_port"]}'
    deadline = time.monotonic() + args.seconds
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w") as output:
        def record(kind, **values):
            output.write(json.dumps({"kind": kind, "utc": datetime.now(timezone.utc).isoformat(),
                                     "mono": time.monotonic(), **values}, separators=(",", ":")) + "\n")
            output.flush()

        async def api_loop():
            while time.monotonic() < deadline:
                started = time.monotonic()
                try:
                    data = await asyncio.to_thread(read_api, port)
                    record("api", duration_ms=(time.monotonic() - started) * 1000,
                           sequence=data["sequence"], generated_at_utc=data["generated_at_utc"],
                           robots=[{"id": row["robot_id"], "telemetry": row["telemetry"],
                                    "pose": row["pose_reliability"], "status_age_sec": row["status_age_sec"],
                                    "pose_sim_ns": row["pose_sim_ns"]} for row in data["robots"]],
                           tasks=data["task_counts"])
                except Exception as error:
                    record("api_error", error=str(error))
                await asyncio.sleep(max(0, 0.25 - (time.monotonic() - started)))

        async def ws_loop():
            while time.monotonic() < deadline:
                try:
                    async with connect(f"ws://127.0.0.1:{port}/ws/fleet", origin=origin,
                                       subprotocols=["fleet.scene.v1"], compression=None,
                                       max_queue=1, open_timeout=3) as socket:
                        record("ws_connected")
                        while time.monotonic() < deadline:
                            message = json.loads(await asyncio.wait_for(socket.recv(), timeout=3))
                            kind = message.get("type")
                            if kind == "scene":
                                packet = message["packet"]
                                if packet.get("type") in ("robot_pose", "data_status", "hello"):
                                    record("scene", packet_type=packet["type"], robot_id=packet["robot_id"],
                                           stamp_ns=packet.get("stamp_ns"), status=packet.get("status"),
                                           epoch=packet.get("epoch"))
                            elif kind == "heartbeat":
                                record("heartbeat")
                            elif kind:
                                record("ws_control", type=kind)
                            else:
                                record("ws_product", sequence=message["sequence"],
                                       generated_at_utc=message["generated_at_utc"],
                                       robots=[{"id": row["robot_id"], "telemetry": row["telemetry"],
                                                "pose": row["pose_reliability"]} for row in message["robots"]],
                                       tasks=message["task_counts"])
                except Exception as error:
                    record("ws_error", error=str(error))
                    await asyncio.sleep(0.5)

        await asyncio.gather(api_loop(), ws_loop())


if __name__ == "__main__":
    asyncio.run(main())
