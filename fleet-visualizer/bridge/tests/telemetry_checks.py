import json
import math
import unittest
from dataclasses import replace

from telemetry import NS, Pose, Telemetry, pose_packet, yaw_from_quaternion


class TelemetryChecks(unittest.TestCase):
    def setUp(self):
        self.telemetry = Telemetry("selected", "map", "tf", 1)
        self.telemetry.clock(3 * NS, 10 * NS)
        self.pose = Pose("selected", "map", 3 * NS, 2.45, 1.2, 1.57, 10 * NS)

    def test_pose_packet(self):
        accepted = self.telemetry.sample(self.pose, 10 * NS)
        packet = json.loads(json.dumps(pose_packet(self.telemetry.identity, accepted.epoch, accepted.pose),
                                       allow_nan=False))
        self.assertEqual(packet, dict(self.telemetry.identity, type="robot_pose", epoch=0,
                                      stamp_ns="3000000000", x=2.45, y=1.2, yaw=1.57))

    def test_quaternion_preserves_yaw(self):
        self.assertAlmostEqual(yaw_from_quaternion(0, 0, math.sin(-1.2), math.cos(-1.2)), -2.4)
        for z, w in ((0, 0), (0, math.inf), (math.nan, 1)):
            with self.assertRaises(ValueError):
                yaw_from_quaternion(0, 0, z, w)

    def test_frame_robot_and_missing_transform(self):
        self.assertEqual(self.telemetry.sample(None, 10 * NS).status, "NO_DATA")
        self.assertEqual(self.telemetry.sample(None, 10 * NS, frame_error=True).status, "FRAME_ERROR")
        for pose in (replace(self.pose, frame_id="odom"), replace(self.pose, robot_id="other")):
            sample = self.telemetry.sample(pose, 10 * NS)
            self.assertEqual(sample.status, "FRAME_ERROR")
            self.assertIsNone(sample.pose)

    def test_invalid_old_future_and_zero_measurements(self):
        for pose in (replace(self.pose, x=math.nan), replace(self.pose, y=math.inf),
                     replace(self.pose, yaw=-math.inf), replace(self.pose, stamp_ns=0),
                     replace(self.pose, stamp_ns=2 * NS), replace(self.pose, stamp_ns=3 * NS + 1),
                     replace(self.pose, received_ns=9 * NS)):
            self.assertIsNone(self.telemetry.sample(pose, 10 * NS).pose)

    def test_duplicate_and_reordered_samples_do_not_replace_or_refresh(self):
        self.telemetry.sample(self.pose, 10 * NS)
        for stamp in (self.pose.stamp_ns, self.pose.stamp_ns - 1):
            late = replace(self.pose, stamp_ns=stamp, x=99, received_ns=10 * NS + 1)
            self.assertEqual(self.telemetry.sample(late, late.received_ns).pose, self.pose)
        self.telemetry.clock(3 * NS + 1, 11 * NS)
        self.assertEqual(self.telemetry.sample(replace(self.pose, received_ns=11 * NS),
                                               11 * NS).status, "STALE")

    def test_clock_freeze_or_missing_data_keeps_last_pose_stale(self):
        self.telemetry.sample(self.pose, 10 * NS)
        self.telemetry.clock(3 * NS, 11 * NS)
        sample = self.telemetry.sample(None, 11 * NS)
        self.assertEqual((sample.status, sample.pose), ("STALE", self.pose))

    def test_clock_rewind_invalidates_pose_and_advances_epoch(self):
        self.telemetry.sample(self.pose, 10 * NS)
        self.assertTrue(self.telemetry.clock(NS, 10 * NS + 10))
        sample = self.telemetry.sample(self.pose, 10 * NS + 10)
        self.assertEqual((sample.epoch, sample.status, sample.pose), (1, "NO_DATA", None))
        new_pose = replace(self.pose, stamp_ns=NS, received_ns=10 * NS + 10)
        self.assertEqual(self.telemetry.sample(new_pose, 10 * NS + 10).pose, new_pose)
