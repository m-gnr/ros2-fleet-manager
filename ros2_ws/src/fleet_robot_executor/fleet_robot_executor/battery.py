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
        self.charging_station_id = ""
        self.blocked_reason = ""
        self._control_authorization = None
        self._used_control_requests = set()
        self._last_control_revision = 0
        self.control_proof = None

    def authorize_control(self, msg, sim_ns: int, received_at: float) -> bool:
        """Accept one explicit, fresh attestation from the Battery Simulator."""
        if (msg.robot_id != self.robot_id or not msg.request_id or msg.request_id in self._used_control_requests
                or len(self._used_control_requests) >= 10000
                or not isinstance(msg.revision, int) or msg.revision <= self._last_control_revision
                or not msg.control_session_id or not isfinite(msg.applied_energy_wh)
                or not isfinite(msg.capacity_wh) or not 0 <= msg.applied_soc_percent <= 100
                or not isclose(msg.applied_soc_percent,
                              100.0 * msg.applied_energy_wh / msg.capacity_wh,
                              rel_tol=0.0, abs_tol=SOC_TOLERANCE_PERCENT)
                or msg.capacity_wh != self.capacity_wh):
            return False
        stamp = msg.applied_stamp
        if not 0 <= stamp.nanosec < NANOSECONDS_PER_SECOND:
            return False
        stamp_ns = stamp.sec * NANOSECONDS_PER_SECOND + stamp.nanosec
        try:
            event_session = bytes(__import__('uuid').UUID(msg.control_session_id).bytes)
        except (ValueError, AttributeError, TypeError):
            return False
        if (not 0 < stamp_ns <= sim_ns or sim_ns - stamp_ns > BATTERY_TIMEOUT_SEC * NANOSECONDS_PER_SECOND
                or (self.session_id is not None and event_session != self.session_id)):
            return False
        self._control_authorization = (msg.request_id, msg.control_session_id, stamp_ns,
                                       float(msg.applied_soc_percent), float(msg.applied_energy_wh), received_at)
        self._last_control_revision = msg.revision
        return True

    def observe(self, msg, sim_ns: int, received_at: float, dock_station_id="") -> bool:
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
        charging_station = getattr(msg, "charging_station_id", "")
        if msg.is_charging and charging_station and charging_station != dock_station_id:
            return False  # A delayed charging sample can arrive just after departure.
        request_id = getattr(msg, "control_request_id", "")
        authorized = False
        proof = self._control_authorization
        if request_id:
            authorized = bool(proof and proof[0] == request_id and proof[2] == stamp_ns
                              and proof[3] == float(soc) and proof[4] == float(energy)
                              and received_at - proof[5] <= BATTERY_TIMEOUT_SEC
                              and session_id.hex() == __import__('uuid').UUID(proof[1]).hex)
            if not authorized:
                self.blocked_reason = "Battery control sample lacks matching one-shot attestation"
                return False
        if (bool(charging_station) != msg.is_charging
                or (self.session_id is not None and energy > self.energy_wh
                    and not (charging_station or self.charging_station_id or authorized))):
            self.blocked_reason = "Unexpected energy increase or unverified charging"
            return False

        self.session_id = session_id
        self.stamp_ns = stamp_ns
        self.received_at = received_at
        self.energy_wh = energy
        self.charging_station_id = charging_station
        self.control_proof = ((proof[1], request_id, float(soc), float(energy), stamp_ns)
                              if authorized else None)
        if authorized:
            self._used_control_requests.add(request_id)
            self._control_authorization = None
        return True

    def fresh_stamp(self, sim_ns: int, now: float) -> int:
        if (not self.blocked_reason and self.stamp_ns > 0
                and 0 <= sim_ns - self.stamp_ns <= BATTERY_TIMEOUT_SEC * NANOSECONDS_PER_SECOND
                and 0 <= now - self.received_at <= BATTERY_TIMEOUT_SEC):
            return self.stamp_ns
        return 0
