"""Deterministic Wh accounting for one simulated robot."""

from collections import deque
from dataclasses import dataclass
from math import hypot, isfinite

from fleet_config.models import BatteryModel

# Odometry is 30 Hz in Fortress. Avoid bridging across missing or delayed data.
MAX_ODOMETRY_GAP_NS = 500_000_000
MAX_PENDING_SAMPLES = 64
# Discontinuity guard with headroom over the current 0.25 m/s Nav2 limit.
MAX_LINEAR_SPEED_M_S = 1.0
NANOSECONDS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True)
class OdometrySample:
    stamp_ns: int
    frames: tuple[str, str]
    position_m: tuple[float, float, float]
    linear_speed_m_s: float
    angular_speed_rad_s: float


class BatteryConsumption:
    def __init__(self, model: BatteryModel):
        self.capacity_wh = model.usable_capacity_wh
        self.remaining_wh = self.capacity_wh
        self._consumption_wh_per_meter = model.consumption_wh_per_meter
        self._idle_power_w = model.idle_power_w
        self._charge_power_w = model.charge_power_w
        self.clock_ns: int | None = None
        self._clock_epoch_start_ns = 0
        self._last_odom_ns: int | None = None
        self._previous_odom: OdometrySample | None = None
        self._pending: deque[OdometrySample] = deque()

    @property
    def soc_percent(self) -> float:
        return 100.0 * (self.remaining_wh / self.capacity_wh)

    def observe_odometry(self, sample: OdometrySample) -> None:
        if self.clock_ns is None:
            return
        if (sample.stamp_ns < max(self._clock_epoch_start_ns, self.clock_ns - MAX_ODOMETRY_GAP_NS)
                or sample.stamp_ns > self.clock_ns + MAX_ODOMETRY_GAP_NS):
            return
        if self._last_odom_ns is not None and sample.stamp_ns <= self._last_odom_ns:
            return

        # Clock and odometry travel on separate DDS topics. Integrate only once
        # an advancing clock covers the sample, including during pause/resume.
        self._last_odom_ns = sample.stamp_ns
        if len(self._pending) == MAX_PENDING_SAMPLES:
            self._pending.popleft()
            self._previous_odom = None
        self._pending.append(sample)

    def update_clock(self, stamp_ns: int, *, charging: bool = False) -> bool:
        """Apply a valid new clock stamp. A rewind starts a fresh reference epoch."""
        previous_clock = self.clock_ns
        if stamp_ns < 0 or stamp_ns == previous_clock:
            return False
        self.clock_ns = stamp_ns
        if previous_clock is None or stamp_ns < previous_clock:
            self._clock_epoch_start_ns = stamp_ns
            self._last_odom_ns = None
            self._previous_odom = None
            self._pending.clear()
            return True

        elapsed_sec = (stamp_ns - previous_clock) / NANOSECONDS_PER_SECOND
        distance_m = 0.0
        while self._pending and self._pending[0].stamp_ns <= stamp_ns:
            distance_m += self._motion_distance(self._pending.popleft())
        idle_wh = self._idle_power_w * (elapsed_sec / 3600.0)
        motion_wh = self._consumption_wh_per_meter * distance_m
        charge_wh = self._charge_power_w * elapsed_sec / 3600.0 if charging else 0.0
        self.remaining_wh = min(self.capacity_wh, max(0.0, self.remaining_wh + charge_wh - idle_wh - motion_wh))
        return True

    def _motion_distance(self, sample: OdometrySample) -> float:
        previous = self._previous_odom
        if (not all(sample.frames) or not all(map(isfinite, sample.position_m))
                or not 0 <= sample.linear_speed_m_s <= MAX_LINEAR_SPEED_M_S
                or not isfinite(sample.angular_speed_rad_s) or sample.angular_speed_rad_s < 0):
            self._previous_odom = None
            return 0.0

        self._previous_odom = sample
        if previous is None or sample.frames != previous.frames:
            return 0.0
        elapsed_ns = sample.stamp_ns - previous.stamp_ns
        if not 0 < elapsed_ns <= MAX_ODOMETRY_GAP_NS:
            return 0.0
        distance_m = hypot(sample.position_m[0] - previous.position_m[0],
                           sample.position_m[1] - previous.position_m[1])
        if distance_m > MAX_LINEAR_SPEED_M_S * elapsed_ns / NANOSECONDS_PER_SECOND:
            return 0.0
        return distance_m
