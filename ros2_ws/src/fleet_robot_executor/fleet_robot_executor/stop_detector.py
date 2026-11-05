"""Stop detector and physical motion verification.

Validates that the robot has physically come to a complete halt based on
fresh odometry readings before confirming preemption or safe recovery.
"""

from typing import Tuple
import math

from .constants import (
    DEFAULT_ANGULAR_STOP_THRESHOLD_RAD_S,
    DEFAULT_LINEAR_STOP_THRESHOLD_M_S,
    DEFAULT_ODOMETRY_FRESHNESS_SEC,
)
from .models import OdometryReading


# Cover two control periods in the configured 10 Hz Nav2/smoother stack.
CANCEL_STOP_WINDOW_SEC = 0.2
CANCEL_STOP_MAX_SAMPLE_GAP_SEC = 0.1


class CancelStopConfirmation:
    """Require a continuous run of stopped odometry after Nav2 cancellation."""

    def __init__(self, terminal_at, config):
        self.terminal_at = terminal_at
        self.config = config
        self.first_stopped_at = None
        self.last_sample = None

    def observe(self, reading, now):
        stamp = reading.timestamp_sec
        if stamp <= self.terminal_at:
            return
        previous = self.last_sample
        self.last_sample = reading
        if not self._stopped(reading, now):
            self.first_stopped_at = None
        elif (self.first_stopped_at is None or previous is None
              or stamp > previous.timestamp_sec + min(
                  CANCEL_STOP_MAX_SAMPLE_GAP_SEC, self.config.odometry_freshness_sec,
              )):
            self.first_stopped_at = stamp

    def confirmed(self, now):
        reading = self.last_sample
        if (reading is not None and self.first_stopped_at is not None
                and reading.timestamp_sec >= self.first_stopped_at + CANCEL_STOP_WINDOW_SEC
                and self._stopped(reading, now)):
            return reading
        return None

    def _stopped(self, reading, now):
        if not reading.source_frame_valid:
            return False
        stopped, _ = StopDetector.verify_stopped(
            reading, now, self.config.linear_stop_threshold_m_s, self.config.angular_stop_threshold_rad_s,
            self.config.odometry_freshness_sec,
        )
        return stopped


class StopDetector:
    """Evaluates zero-velocity and odometry freshness criteria."""

    @staticmethod
    def verify_stopped(
        odometry: OdometryReading,
        current_sim_time: float,
        linear_threshold: float = DEFAULT_LINEAR_STOP_THRESHOLD_M_S,
        angular_threshold: float = DEFAULT_ANGULAR_STOP_THRESHOLD_RAD_S,
        freshness_sec: float = DEFAULT_ODOMETRY_FRESHNESS_SEC,
    ) -> Tuple[bool, str]:
        """Verify that the robot is physically stopped with fresh odometry.

        Criteria:
        1. Freshness: current_sim_time - odometry.timestamp_sec <= freshness_sec.
           Stale odometry cannot confirm physical stop.
        2. Linear velocity: |v| <= linear_threshold.
        3. Angular velocity: |w| <= angular_threshold.

        Returns:
            Tuple[bool, str]: (is_stopped, failure_reason)
        """
        if not all(math.isfinite(v) for v in (current_sim_time, odometry.timestamp_sec,
                odometry.linear_velocity, odometry.angular_velocity)):
            return False, "NONFINITE_ODOMETRY"

        # Protect against stale odometry
        age = current_sim_time - odometry.timestamp_sec
        if age > freshness_sec:
            return False, f"ODOMETRY_STALE: age {age:.3f}s exceeds freshness threshold {freshness_sec:.3f}s"
        if age < 0:
            return False, f"ODOMETRY_IN_FUTURE: odometry timestamp {odometry.timestamp_sec:.3f}s > current sim time {current_sim_time:.3f}s"

        # Check linear velocity threshold
        lin_speed = abs(odometry.linear_velocity)
        if lin_speed > linear_threshold:
            return False, f"LINEAR_VELOCITY_EXCEEDED: speed {lin_speed:.4f} m/s > threshold {linear_threshold:.4f} m/s"

        # Check angular velocity threshold
        ang_speed = abs(odometry.angular_velocity)
        if ang_speed > angular_threshold:
            return False, f"ANGULAR_VELOCITY_EXCEEDED: speed {ang_speed:.4f} rad/s > threshold {angular_threshold:.4f} rad/s"

        return True, ""
