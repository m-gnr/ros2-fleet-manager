"""Scenario-local validation of Battery Simulator measurements."""

from math import isclose, isfinite

NANOSECONDS_PER_SECOND = 10**9
BATTERY_TIMEOUT_SEC = 2.0
SOC_TOLERANCE_PERCENT = 5e-6  # RobotStatus and BatteryState carry float32 SoC.


class BatteryTelemetry:
    def __init__(self, robot_id: str, capacity_wh: float):
        self.robot_id = robot_id
        self.capacity_wh = capacity_wh
        self.session_id = None
        self.stamp_ns = 0
        self.received_at = 0.0
        self.energy_wh = 0.0
        self.blocked_reason = ""

    def observe(self, msg, sim_ns: int, received_at: float) -> bool:
        if self.blocked_reason or msg.robot_id != self.robot_id:
            return False
        session_id = bytes(msg.publisher_session_id.uuid)
        if not any(session_id):
            return False
        if self.session_id is not None and session_id != self.session_id:
            self.blocked_reason = "Battery Simulator session changed"
            return False

        stamp = msg.battery_stamp
        if not 0 <= stamp.nanosec < NANOSECONDS_PER_SECOND:
            return False
        stamp_ns = stamp.sec * NANOSECONDS_PER_SECOND + stamp.nanosec
        if (not self.stamp_ns < stamp_ns <= sim_ns
                or sim_ns - stamp_ns > BATTERY_TIMEOUT_SEC * NANOSECONDS_PER_SECOND):
            return False

        energy, capacity, soc = msg.battery_energy_wh, msg.battery_capacity_wh, msg.battery_soc_percent
        if not (isfinite(capacity) and capacity > 0.0 and capacity == self.capacity_wh
                and 0.0 <= energy <= capacity and 0.0 <= soc <= 100.0
                and isclose(soc, 100.0 * (energy / capacity), rel_tol=0.0, abs_tol=SOC_TOLERANCE_PERCENT)):
            return False
        if msg.is_charging or (self.session_id is not None and energy > self.energy_wh):
            self.blocked_reason = "Unexpected energy increase or charging in C4.2"
            return False

        self.session_id = session_id
        self.stamp_ns = stamp_ns
        self.received_at = received_at
        self.energy_wh = energy
        return True

    def fresh_stamp(self, sim_ns: int, now: float) -> int:
        if (not self.blocked_reason and self.stamp_ns > 0
                and 0 <= sim_ns - self.stamp_ns <= BATTERY_TIMEOUT_SEC * NANOSECONDS_PER_SECOND
                and 0 <= now - self.received_at <= BATTERY_TIMEOUT_SEC):
            return self.stamp_ns
        return 0
