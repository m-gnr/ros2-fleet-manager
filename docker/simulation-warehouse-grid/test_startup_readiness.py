import unittest

from startup_readiness import PHASES, StartupReadiness


class StartupReadinessTests(unittest.TestCase):
    def test_requires_all_phases_for_every_robot(self):
        tracker = StartupReadiness(("robot_alpha", "robot_beta", "robot_gamma"), 1_000_000_000)
        for phase in PHASES:
            tracker.mark("robot_alpha", phase, monotonic_ns=2_000_000_000,
                         observed_at_utc="2026-11-17T10:00:00+00:00")
        self.assertFalse(tracker.ready)
        for phase in PHASES:
            tracker.mark("robot_beta", phase, monotonic_ns=3_000_000_000,
                         observed_at_utc="2026-11-17T10:00:01+00:00")
        self.assertFalse(tracker.ready)
        for phase in PHASES:
            tracker.mark("robot_gamma", phase, monotonic_ns=3_050_000_000,
                         observed_at_utc="2026-11-17T10:00:01.050+00:00")
        self.assertTrue(tracker.ready)
        now = 3_100_000_000
        snapshot = tracker.snapshot(started_at_utc="2026-11-17T10:00:00+00:00",
                                    current_ready=True, observed_monotonic_ns=now,
                                    observed_at_utc="2026-11-17T10:00:01.100+00:00")
        self.assertEqual(snapshot["status"], "READY")
        self.assertEqual(snapshot["current_status"], "READY")
        waiting = tracker.snapshot(started_at_utc="2026-11-17T10:00:00+00:00", current_ready=False)
        self.assertEqual(waiting["status"], "READY")
        self.assertEqual(waiting["current_status"], "WAITING")

    def test_first_timestamp_is_stable_and_waiting_snapshot_is_explicit(self):
        tracker = StartupReadiness(("robot_alpha",), 10)
        first = tracker.mark("robot_alpha", "tf", monotonic_ns=1_000_010,
                             observed_at_utc="first")
        duplicate = tracker.mark("robot_alpha", "tf", monotonic_ns=2_000_010,
                                 observed_at_utc="later")
        self.assertEqual(first["elapsed_ms"], 1)
        self.assertIsNone(duplicate)
        snapshot = tracker.snapshot(started_at_utc="start")
        self.assertEqual(snapshot["status"], "WAITING")
        self.assertEqual(snapshot["robots"]["robot_alpha"]["amcl"], {"ready": False})

    def test_unknown_robot_phase_and_pre_start_time_are_rejected(self):
        tracker = StartupReadiness(("robot_alpha",), 10)
        with self.assertRaises(ValueError):
            tracker.mark("robot_beta", "tf", monotonic_ns=10, observed_at_utc="x")
        with self.assertRaises(ValueError):
            tracker.mark("robot_alpha", "camera", monotonic_ns=10, observed_at_utc="x")
        with self.assertRaises(ValueError):
            tracker.mark("robot_alpha", "tf", monotonic_ns=9, observed_at_utc="x")


if __name__ == "__main__":
    unittest.main()
