"""Bounded, send-only WebSocket transport."""
import asyncio
from contextlib import suppress
from dataclasses import dataclass
import json
from time import monotonic_ns

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from telemetry import Snapshot, pose_packet


@dataclass
class Cursor:
    epoch: int
    cutoff: int
    status: str = ""
    heartbeat_at: int = 0


class Stream:
    def __init__(self, identities, *, stale_ms, trace_clock=None, max_clients=4):
        self.identities = {identity["robot_id"]: identity for identity in identities}
        self.snapshots = dict.fromkeys(self.identities, Snapshot())
        self.changed = asyncio.Event()
        self.stale_ms = stale_ms
        self.trace_clock = trace_clock
        self.max_clients = max_clients
        self.clients = 0

    def update(self, snapshots):
        self.snapshots.update(snapshots)
        changed, self.changed = self.changed, asyncio.Event()
        changed.set()

    async def handle(self, socket):
        if socket.request.path not in ("/telemetry", "/telemetry/fleet"):
            await socket.close(1008, "Unknown path")
            return
        if self.clients >= self.max_clients:
            await socket.close(1013, "Connection limit")
            return

        self.clients += 1
        fleet = socket.request.path == "/telemetry/fleet"
        robot_ids = tuple(self.identities) if fleet else (next(iter(self.identities)),)
        sender = asyncio.create_task(self.send_stream(socket, robot_ids, fleet=fleet))
        receiver = asyncio.create_task(socket.recv())
        try:
            done, _ = await asyncio.wait((sender, receiver), return_when=asyncio.FIRST_COMPLETED)
            if receiver in done:
                receiver.result()
                await socket.close(1008, "Read-only stream")
            if sender in done:
                sender.result()
        except (ConnectionClosed, asyncio.TimeoutError):
            pass
        finally:
            for task in (sender, receiver):
                task.cancel()
                with suppress(asyncio.CancelledError, ConnectionClosed, asyncio.TimeoutError):
                    await task
            self.clients -= 1

    async def send_stream(self, socket, robot_ids, *, fleet):
        cursors = {}
        if fleet:
            await send(socket, dict(type="fleet_hello", version=1, robot_ids=robot_ids))
        for robot_id in robot_ids:
            snapshot = self.snapshots[robot_id]
            cutoff = snapshot.pose.stamp_ns if snapshot.pose else 0
            cursors[robot_id] = Cursor(snapshot.epoch, cutoff)
            await send(socket, dict(self.identities[robot_id], type="hello", epoch=snapshot.epoch,
                                    after_stamp_ns=str(cutoff), stale_after_ms=self.stale_ms))
        while True:
            changed = self.changed
            for robot_id, cursor in cursors.items():
                await self.send_robot(socket, robot_id, cursor)
            # The ROS steady timer also wakes this stream when ROS time stops.
            await changed.wait()

    async def send_robot(self, socket, robot_id, cursor):
        snapshot = self.snapshots[robot_id]
        identity = self.identities[robot_id]
        pose, epoch, status = snapshot.pose, snapshot.epoch, snapshot.status
        now = monotonic_ns()
        if epoch != cursor.epoch:
            cursor.epoch, cursor.cutoff, cursor.status = epoch, 0, ""
        if status != cursor.status or now >= cursor.heartbeat_at:
            await send(socket, dict(identity, type="data_status", epoch=epoch, status=status))
            cursor.status, cursor.heartbeat_at = status, now + 500_000_000

        current = self.snapshots[robot_id]
        if (status == "LIVE" and pose is not None and pose.stamp_ns > cursor.cutoff
                and epoch == current.epoch and current.status == "LIVE"
                and monotonic_ns() - pose.received_ns < self.stale_ms * 1e6):
            packet = pose_packet(identity, epoch, pose)
            start = monotonic_ns()
            sim_clock = self.trace_clock(robot_id) if self.trace_clock else None
            await send(socket, packet)
            cursor.cutoff = pose.stamp_ns
            if sim_clock:
                clock_epoch, clock_ns = sim_clock
                age_ms = (clock_ns - pose.stamp_ns) / 1e6 if clock_epoch == epoch else None
                print(json.dumps(dict(packet, event="WS_POSE",
                                      rx_to_send_ms=(start - pose.received_ns) / 1e6,
                                      rx_to_sent_ms=(monotonic_ns() - pose.received_ns) / 1e6,
                                      ros_age_at_send_ms=age_ms)),
                      flush=True)


async def send(socket, payload):
    await asyncio.wait_for(socket.send(json.dumps(payload, allow_nan=False)), timeout=1)


def listen(stream, host, port, origins):
    return serve(stream.handle, host, port, origins=origins, compression=None,
                 max_size=1024, max_queue=1, write_limit=4096, open_timeout=3,
                 close_timeout=1, ping_interval=5, ping_timeout=5)
