"""Bounded, send-only WebSocket transport."""
import asyncio
from contextlib import suppress
import json
from time import monotonic_ns

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from telemetry import Snapshot, pose_packet


class Stream:
    def __init__(self, identity, *, stale_ms, trace_clock=None, max_clients=4):
        self.identity = identity
        self.snapshot = Snapshot()
        self.changed = asyncio.Event()
        self.stale_ms = stale_ms
        self.trace_clock = trace_clock
        self.max_clients = max_clients
        self.clients = 0

    def update(self, snapshot):
        self.snapshot = snapshot
        changed, self.changed = self.changed, asyncio.Event()
        changed.set()

    async def handle(self, socket):
        if socket.request.path != "/telemetry":
            await socket.close(1008, "Unknown path")
            return
        if self.clients >= self.max_clients:
            await socket.close(1013, "Connection limit")
            return

        self.clients += 1
        sender = asyncio.create_task(self.send_stream(socket))
        receiver = asyncio.create_task(socket.recv())
        try:
            done, _ = await asyncio.wait((sender, receiver), return_when=asyncio.FIRST_COMPLETED)
            if receiver in done:
                receiver.result()
                await socket.close(1008, "Read-only stream")
            if sender in done:
                sender.result()
        except (ConnectionClosed, TimeoutError):
            pass
        finally:
            for task in (sender, receiver):
                task.cancel()
                with suppress(asyncio.CancelledError, ConnectionClosed, TimeoutError):
                    await task
            self.clients -= 1

    async def send_stream(self, socket):
        snapshot = self.snapshot
        epoch = snapshot.epoch
        cutoff = snapshot.pose.stamp_ns if snapshot.pose else 0
        await send(socket, dict(self.identity, type="hello", epoch=epoch,
                                after_stamp_ns=str(cutoff), stale_after_ms=self.stale_ms))
        last_status = None
        heartbeat_at = 0
        while True:
            snapshot, changed = self.snapshot, self.changed
            pose = snapshot.pose
            now = monotonic_ns()
            status = snapshot.status
            if epoch != snapshot.epoch:
                epoch, cutoff = snapshot.epoch, 0
                last_status = None
            if status != last_status or now >= heartbeat_at:
                await send(socket, dict(self.identity, type="data_status", epoch=epoch, status=status))
                last_status, heartbeat_at = status, now + 500_000_000
            if (status == "LIVE" and pose is not None and pose.stamp_ns > cutoff
                    and epoch == self.snapshot.epoch and self.snapshot.status == "LIVE"
                    and monotonic_ns() - pose.received_ns < self.stale_ms * 1e6):
                packet = pose_packet(self.identity, epoch, pose)
                start = monotonic_ns()
                sim_clock = self.trace_clock() if self.trace_clock else None
                await send(socket, packet)
                cutoff = pose.stamp_ns
                if sim_clock:
                    clock_epoch, clock_ns = sim_clock
                    age_ms = (clock_ns - pose.stamp_ns) / 1e6 if clock_epoch == epoch else None
                    print(json.dumps(dict(packet, event="WS_POSE",
                                          rx_to_send_ms=(start - pose.received_ns) / 1e6,
                                          rx_to_sent_ms=(monotonic_ns() - pose.received_ns) / 1e6,
                                          ros_age_at_send_ms=age_ms)),
                          flush=True)
            # The ROS steady timer also wakes this stream when ROS time stops.
            await changed.wait()


async def send(socket, payload):
    await asyncio.wait_for(socket.send(json.dumps(payload, allow_nan=False)), timeout=1)


def listen(stream, host, port, origins):
    return serve(stream.handle, host, port, origins=origins, compression=None,
                 max_size=1024, max_queue=1, write_limit=4096, open_timeout=3,
                 close_timeout=1, ping_interval=5, ping_timeout=5)
