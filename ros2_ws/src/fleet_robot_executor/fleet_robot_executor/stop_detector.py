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
