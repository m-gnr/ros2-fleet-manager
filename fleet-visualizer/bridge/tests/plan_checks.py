import asyncio
import json
from time import monotonic_ns
from types import SimpleNamespace as Fields
import unittest

from websockets.asyncio.client import connect

from observed_plan import MAX_POINTS, PLAN_TTL_NS, ObservedPlan, PlanBuffer
from server import Stream, listen, send
from telemetry import NS, Pose, Snapshot, Telemetry

ORIGIN = "http://127.0.0.1:5173"


def path(stamp=20, frame="map", count=2, x=1.0):
    header = Fields(frame_id=frame, stamp=Fields(sec=stamp, nanosec=0))
    point = Fields(position=Fields(x=x, y=-2.0, z=0.0), orientation=Fields(x=0, y=0, z=0, w=1))
    return Fields(header=header, poses=[Fields(header=header, pose=point) for _ in range(count)])


class PlanChecks(unittest.TestCase):
    def test_rejects_frames_coordinates_timestamps_and_oversize(self):
        bad_pose_frame = path()
        bad_pose_frame.poses[1].header = path(frame="odom").header
        bad_pose_stamp = path()
        bad_pose_stamp.poses[1].header = path(stamp=19).header
        bad_orientation = path()
        bad_orientation.poses[1].pose.orientation.w = 0
        for message in (path(frame="odom"), path(count=0), path(count=MAX_POINTS + 1),
                        path(x=float("nan")), path(x=float("inf")), path(x=10_001),
                        path(stamp=17), path(stamp=21), bad_pose_frame, bad_pose_stamp, bad_orientation):
            with self.subTest(message=message.header):
                buffer = PlanBuffer()
                buffer.accept(message, 20 * NS, 42)
                self.assertIsNone(buffer.plan)
        buffer = PlanBuffer()
        buffer.accept(path(count=MAX_POINTS), 20 * NS, 42)
        self.assertEqual(len(buffer.plan.points), MAX_POINTS)

    def test_no_replay_and_independent_expiry_and_reset(self):
        a, b = PlanBuffer(), PlanBuffer()
        a.accept(path(), 20 * NS, 5)
        b.accept(path(19), 20 * NS, 8)
        a.accept(path(x=9.0), 20 * NS, 9)
        a.accept(path(19, x=8.0), 20 * NS, 10)
        self.assertEqual(a.current(20 * NS, 10).points[0], (1, -2))
        self.assertIsNone(b.current(21 * NS, 10))
        self.assertIsNone(a.current(20 * NS, 5 + PLAN_TTL_NS))
        a.accept(path(), 20 * NS, 5 + PLAN_TTL_NS)
        self.assertIsNone(a.plan)
        a.reset()
        a.accept(path(1), NS, 5 + PLAN_TTL_NS)
        self.assertEqual(a.plan.stamp_ns, NS)
        self.assertEqual(b.cutoff, 19 * NS)


class PlanSocketChecks(unittest.IsolatedAsyncioTestCase):
    async def test_connection_cutoff_plan_clear_and_epoch(self):
        ids = [Telemetry(id, "map", "tf", 1).identity for id in ("a", "b")]
        topics = {id: f"/{id}/plan" for id in ("a", "b")}
        stream = Stream(ids, stale_ms=1000, plan_topics=topics)
        server = await listen(stream, "127.0.0.1", 0, [ORIGIN])
        async def close():
            server.close()
            await server.wait_closed()

        self.addAsyncCleanup(close)
        url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/telemetry/fleet"

        def update(id, stamp, epoch=0, points=()):
            now = monotonic_ns()
            plan = ObservedPlan(stamp, now, points) if points else None
            stream.update({id: Snapshot(epoch, "LIVE", Pose(id, "map", stamp, 0, 0, 0, now), plan)})

        async def next_type(socket, expected):
            while True:
                packet = json.loads(await asyncio.wait_for(socket.recv(), timeout=2))
                if packet["type"] == expected:
                    return packet
                self.assertNotIn(packet["type"], ("robot_path", "robot_path_clear"))

        points = ((1.0, -2.0),) * MAX_POINTS
        update("a", 10, points=points)
        async with connect(url, origin=ORIGIN) as socket:
            await next_type(socket, "fleet_hello")
            self.assertEqual((await next_type(socket, "hello"))["path_topic"], "/a/plan")
            self.assertEqual((await next_type(socket, "hello"))["path_topic"], "/b/plan")
            update("b", 11, points=points)
            plan = await next_type(socket, "robot_path")
            self.assertEqual((plan["robot_id"], plan["stamp_ns"], len(plan["points"])), ("b", "11", MAX_POINTS))
            update("b", 12)
            clear = await next_type(socket, "robot_path_clear")
            self.assertEqual((clear["robot_id"], clear["stamp_ns"]), ("b", "11"))
            update("b", 1, epoch=1, points=points)
            plan = await next_type(socket, "robot_path")
            self.assertEqual((plan["epoch"], plan["stamp_ns"]), (1, "1"))
        async with connect(url, origin=ORIGIN) as socket:
            for _ in range(5):
                self.assertIn(json.loads(await asyncio.wait_for(socket.recv(), timeout=2))["type"],
                              ("fleet_hello", "hello", "data_status"))
            update("b", 2, epoch=1, points=points)
            self.assertEqual((await next_type(socket, "robot_path"))["stamp_ns"], "2")

    async def test_slow_send_does_not_hold_other_clients(self):
        waiting = asyncio.Event()

        class Slow:
            async def send(self, _):
                await waiting.wait()

        class Fast:
            async def send(self, data):
                self.data = data

        slow = asyncio.create_task(send(Slow(), {"type": "robot_path"}))
        fast = Fast()
        self.assertGreater(await asyncio.wait_for(send(fast, {"type": "robot_pose"}), 0.25), 0)
        self.assertIn("robot_pose", fast.data)
        with self.assertRaises(asyncio.TimeoutError):
            await slow
