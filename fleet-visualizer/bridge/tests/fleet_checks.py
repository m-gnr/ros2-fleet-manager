import asyncio
from dataclasses import replace
from types import SimpleNamespace
import unittest

from fleet_config import load_config
from run import LatestSnapshots, ROOT, select_robots
from server import Stream
from telemetry import NS, Pose, Snapshot, Telemetry


class FleetChecks(unittest.TestCase):
    def test_config_roster_and_invalid_robot(self):
        fleet = load_config(ROOT / "config/fleet.yaml", schema_path=ROOT / "config/fleet.schema.json")
        selected = select_robots(fleet, None, "tf")
        self.assertEqual([(robot.id, robot.namespace) for robot in selected],
                         [("robot_1", "/robot_1"), ("robot_2", "/robot_2")])
        self.assertEqual(select_robots(fleet, selected[1].id, "tf"), [selected[1]])
        with self.assertRaisesRegex(ValueError, "Unknown robot id"):
            select_robots(fleet, "not_configured", "tf")
        with self.assertRaisesRegex(ValueError, "requires --robot"):
            select_robots(fleet, None, "diagnostic_odom")

    def test_independent_freshness_watermarks_and_epoch(self):
        a, b = (Telemetry(id, "map", "tf", 1) for id in ("a", "b"))
        first = Pose("a", "map", 3 * NS, 1, 0, 0, 5 * NS)
        second = replace(first, robot_id="b", stamp_ns=3 * NS - 20, x=5)
        for telemetry, pose in ((a, first), (b, second)):
            telemetry.clock(3 * NS, 5 * NS)
            self.assertEqual(telemetry.sample(pose, 5 * NS).status, "LIVE")
            telemetry.clock(4 * NS, 6 * NS)
        self.assertEqual(a.sample(replace(first, received_ns=6 * NS), 6 * NS).status, "STALE")
        self.assertEqual(b.sample(replace(second, stamp_ns=4 * NS, received_ns=6 * NS), 6 * NS).status, "LIVE")
        a.clock(NS, 6 * NS + 1)
        self.assertEqual(a.sample(None, 6 * NS + 1), Snapshot(1))
        self.assertEqual(b.sample(None, 6 * NS + 1).epoch, 0)

    def test_ros_relay_coalesces_to_one_pending_update_per_robot(self):
        callbacks, updates = [], []
        relay = LatestSnapshots(SimpleNamespace(call_soon_threadsafe=callbacks.append),
                                SimpleNamespace(update=updates.append))
        for i in range(1000):
            relay.offer("a", Snapshot(i))
            relay.offer("b", Snapshot(i + 1))
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(len(relay.pending), 2)
        callbacks.pop()()
        self.assertEqual(updates, [{"a": Snapshot(999), "b": Snapshot(1000)}])
        self.assertEqual(relay.pending, {})


class SlowSocketChecks(unittest.IsolatedAsyncioTestCase):
    async def test_slow_sender_has_no_backlog_or_effect_on_another_client(self):
        blocked = asyncio.Event()
        fast = asyncio.Queue()
        release = asyncio.Event()

        async def slow_send(_):
            blocked.set()
            await release.wait()

        stream = Stream([Telemetry(id, "map", "tf", 1).identity for id in ("a", "b")], stale_ms=1000)
        slow = asyncio.create_task(stream.send_stream(SimpleNamespace(send=slow_send), ("a", "b"), fleet=True))
        quick = asyncio.create_task(stream.send_stream(SimpleNamespace(send=fast.put), ("a", "b"), fleet=True))
        try:
            await blocked.wait()
            for epoch in range(100):
                stream.update({"a": Snapshot(epoch), "b": Snapshot(epoch)})
            for _ in range(5):
                await asyncio.wait_for(fast.get(), 0.5)
            self.assertEqual(stream.snapshots, {"a": Snapshot(99), "b": Snapshot(99)})
            self.assertFalse(slow.done())
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(slow), 1.5)
            self.assertTrue(slow.done())
        finally:
            quick.cancel()
            slow.cancel()
            await asyncio.gather(quick, slow, return_exceptions=True)
