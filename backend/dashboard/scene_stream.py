"""Bounded relay from the private read-only TF bridge to C5."""
import asyncio
from contextlib import suppress
import json
import time

from starlette.websockets import WebSocketDisconnect
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

PROTOCOL = "fleet.scene.v1"
PACKET_LIMIT = 64 * 1024
BRIDGE_ORIGIN = "http://scene"
BRIDGE_SILENCE = 2.5
MAX_RELAY_POSE_AGE_SEC = 0.25


class BridgeIdentity:
    def __init__(self, topics):
        self.topics = topics
        self.roster_seen = False

    def accepts(self, packet):
        if not isinstance(packet, dict) or type(packet.get("version")) is not int or packet["version"] != 1:
            return False
        kind = packet.get("type")
        if not self.roster_seen:
            ids = packet.get("robot_ids")
            self.roster_seen = (kind == "fleet_hello" and isinstance(ids, list)
                                and len(ids) == len(self.topics)
                                and all(isinstance(item, str) for item in ids)
                                and set(ids) == self.topics.keys())
            return self.roster_seen
        robot = packet.get("robot_id")
        if (not isinstance(robot, str) or robot not in self.topics
                or packet.get("frame_id") != "map" or packet.get("source") != "tf"):
            return False
        if kind == "hello":
            return packet.get("path_topic", self.topics[robot]) == self.topics[robot]
        if kind in ("robot_path", "robot_path_clear"):
            return (packet.get("source_topic") == self.topics[robot]
                    and packet.get("plan_source") == "nav2_observed_plan")
        return kind in ("data_status", "robot_pose")


async def bridge_events(url, topics):
    while True:
        identity = BridgeIdentity(topics)
        try:
            async with connect(url, origin=BRIDGE_ORIGIN, proxy=None, compression=None,
                               max_size=PACKET_LIMIT, max_queue=1, open_timeout=2,
                               close_timeout=0.25, ping_interval=5, ping_timeout=5) as upstream:
                while True:
                    raw = await asyncio.wait_for(upstream.recv(), BRIDGE_SILENCE)
                    received = time.monotonic()
                    if not isinstance(raw, str):
                        break
                    try:
                        packet = json.loads(raw)
                        if not identity.accepts(packet):
                            break
                        # Reject non-finite JSON constants before forwarding.
                        json.dumps(packet, allow_nan=False)
                        if packet["type"] == "fleet_hello":
                            yield {"type": "scene_connected"}, received
                    except (ValueError, RecursionError):
                        break
                    yield {"type": "scene", "packet": packet}, received
        except (OSError, WebSocketException, asyncio.TimeoutError):
            pass
        yield {"type": "scene_disconnected"}, time.monotonic()
        await asyncio.sleep(0.75)


async def send_operations(socket, feed, *, bridge_url, topics, poll_sec, send_timeout):
    """One sender, one pending bridge event, and a latest-value product snapshot."""
    receiver = asyncio.create_task(socket.receive())
    events = bridge_events(bridge_url, topics) if bridge_url else None
    pending = asyncio.create_task(anext(events)) if events else None
    last = None
    product_available = None
    heartbeat_at = 0.0
    close_code = None

    async def send(payload):
        await asyncio.wait_for(socket.send_text(payload), send_timeout)

    try:
        while True:
            if receiver.done():
                if receiver.result()["type"] != "websocket.disconnect":
                    close_code = 1008
                break

            current = feed.current()
            payload = feed.payload
            if current is None:
                if product_available is not False:
                    await send('{"type":"product_unavailable"}')
                product_available = False
                last = None
            elif current is not last:
                if last is not None and current.source_session_id != last.source_session_id:
                    await send('{"type":"product_unavailable"}')
                await send(payload)
                product_available = True
                last = current

            now = time.monotonic()
            if now >= heartbeat_at:
                await send('{"type":"heartbeat"}')
                heartbeat_at = now + 1

            if pending is not None and pending.done():
                envelope, received = pending.result()
                packet = envelope.get("packet")
                if packet and packet["type"] == "robot_path":
                    ttl = packet.get("ttl_ms")
                    if type(ttl) is int and 1 <= ttl <= 2000:
                        packet["ttl_ms"] = ttl - int((time.monotonic() - received) * 1000)
                        if packet["ttl_ms"] > 0:
                            await send(json.dumps(envelope, separators=(",", ":"), allow_nan=False))
                elif not packet or packet["type"] != "robot_pose" or time.monotonic() - received <= MAX_RELAY_POSE_AGE_SEC:
                    await send(json.dumps(envelope, separators=(",", ":"), allow_nan=False))
                pending = asyncio.create_task(anext(events))

            await asyncio.wait((receiver, pending) if pending else (receiver,), timeout=poll_sec,
                               return_when=asyncio.FIRST_COMPLETED)
    except asyncio.TimeoutError:
        close_code = 1013
    except (WebSocketDisconnect, OSError):
        return
    finally:
        for task in (receiver, pending):
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError, WebSocketDisconnect, OSError):
                    await task
        if events is not None:
            await events.aclose()
    if close_code is not None:
        with suppress(asyncio.TimeoutError, WebSocketDisconnect, OSError):
            await asyncio.wait_for(socket.close(close_code), send_timeout)
