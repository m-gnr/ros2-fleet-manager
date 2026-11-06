import asyncio
import json
from time import monotonic_ns
import unittest

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from server import Stream, listen
from telemetry import Pose, Snapshot, Telemetry

ORIGIN = "http://127.0.0.1:5173"


async def packet(socket):
    return json.loads(await asyncio.wait_for(socket.recv(), timeout=2))


class SocketChecks(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.stream = Stream([Telemetry("robot", "map", "tf", 1).identity], stale_ms=1000, max_clients=1)
        self.server = await listen(self.stream, "127.0.0.1", 0, [ORIGIN])
        self.addAsyncCleanup(self.stop_server)
        self.url = f"ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}/telemetry"

    async def stop_server(self):
        self.server.close()
        await asyncio.wait_for(self.server.wait_closed(), timeout=2)

    def sample(self, stamp, epoch=0):
        self.stream.update({"robot": Snapshot(epoch, "LIVE", Pose("robot", "map", stamp, 1, 2, 3,
                                                                  monotonic_ns()))})

    async def test_reconnect_never_replays_latest_snapshot(self):
        self.sample(1)
        for cutoff in (1, 2):
            async with connect(self.url, origin=ORIGIN) as socket:
                hello = await packet(socket)
                self.assertEqual(hello["after_stamp_ns"], str(cutoff))
                self.assertEqual((await packet(socket))["type"], "data_status")
                self.sample(cutoff + 1)
                self.assertEqual((await packet(socket))["stamp_ns"], str(cutoff + 1))

    async def test_origin_limit_and_inbound_commands(self):
        with self.assertRaises(InvalidStatus):
            async with connect(self.url, origin="https://elsewhere.invalid"):
                self.fail("Accepted unlisted origin")
        async with connect(self.url, origin=ORIGIN) as first:
            await packet(first)
            async with connect(self.url, origin=ORIGIN) as extra:
                with self.assertRaises(ConnectionClosed):
                    await packet(extra)
                self.assertEqual(extra.close_code, 1013)
            await packet(first)
            await first.send('{"type":"command"}')
            with self.assertRaises(ConnectionClosed):
                await packet(first)
            self.assertEqual(first.close_code, 1008)

    async def test_stale_transition_and_shutdown(self):
        async with connect(self.url, origin=ORIGIN) as socket:
            await packet(socket)
            self.assertEqual((await packet(socket))["status"], "NO_DATA")
            self.sample(9)
            self.assertEqual((await packet(socket))["status"], "LIVE")
            self.assertEqual((await packet(socket))["stamp_ns"], "9")
            self.stream.update({"robot": Snapshot(0, "STALE", self.stream.snapshots["robot"].pose)})
            self.assertEqual((await packet(socket))["status"], "STALE")
            self.sample(1, epoch=1)
            self.assertEqual((await packet(socket))["epoch"], 1)
            self.assertEqual((await packet(socket))["stamp_ns"], "1")
            self.server.close()
            await asyncio.wait_for(self.server.wait_closed(), timeout=2)
            self.assertEqual(self.stream.clients, 0)
            self.assertEqual(socket.close_code, 1001)

    async def test_fleet_handshake_resume_and_legacy_projection(self):
        stream = Stream([Telemetry(id, "map", "tf", 1).identity for id in ("a", "b")], stale_ms=1000)
        server = await listen(stream, "127.0.0.1", 0, [ORIGIN])
        url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/telemetry"
        try:
            def update(id, epoch, stamp, status="LIVE"):
                stream.update({id: Snapshot(epoch, status, Pose(id, "map", stamp, stamp, 0, 0,
                                                                monotonic_ns()))})

            update("a", 0, 3)
            update("b", 0, 1)
            async with connect(url + "/fleet", origin=ORIGIN) as fleet, connect(url, origin=ORIGIN) as legacy:
                self.assertEqual(await packet(fleet), {"type": "fleet_hello", "version": 1, "robot_ids": ["a", "b"]})
                for id, cutoff in (("a", "3"), ("b", "1")):
                    hello = await packet(fleet)
                    self.assertEqual((hello["robot_id"], hello["after_stamp_ns"]), (id, cutoff))
                self.assertEqual((await packet(legacy))["robot_id"], "a")
                for _ in range(2):
                    self.assertEqual((await packet(fleet))["type"], "data_status")
                self.assertEqual((await packet(legacy))["type"], "data_status")
                update("a", 0, 3, "STALE")
                update("b", 0, 2)
                self.assertEqual((await packet(fleet))["status"], "STALE")
                pose = await packet(fleet)
                self.assertEqual((pose["robot_id"], pose["stamp_ns"], pose["x"]), ("b", "2", 2))
                update("a", 1, 1)
                self.assertEqual((await packet(fleet))["epoch"], 1)
                self.assertEqual((await packet(fleet))["stamp_ns"], "1")
                self.assertEqual((await packet(legacy))["status"], "STALE")
                self.assertEqual((await packet(legacy))["epoch"], 1)
                self.assertEqual((await packet(legacy))["robot_id"], "a")
        finally:
            server.close()
            await server.wait_closed()
