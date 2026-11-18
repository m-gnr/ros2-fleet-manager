"""Review-only reachable-stop geometry. No calibrated bound or motion API.

Nav2 limits are commanded settings, not measured braking capacity. Missing
measurements produce no finite tube, even when observed velocity is zero.
"""
from dataclasses import dataclass, asdict
import math

from .traffic import Box, sweep, covered


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class StopInputs:
    linear_deceleration_m_s2: float | None = None
    angular_deceleration_rad_s2: float | None = None
    linear_acceleration_m_s2: float | None = None
    angular_acceleration_rad_s2: float | None = None
    detection_sec: float | None = None
    computation_sec: float | None = None
    communication_sec: float | None = None
    actuator_sec: float | None = None
    position_error_m: float | None = None
    speed_error_m_s: float | None = None
    angular_speed_error_rad_s: float | None = None
    margin_m: float | None = None
    evidence_sha256: str | None = None


def stop_envelope(*, x, y, linear_speed, angular_speed, footprint_radius, inputs):
    """Isotropic over-approximation; all headings/rotation fit in the circle.

    Reaction-phase acceleration is included before constant minimum braking.
    This conditional model assumes those bounds hold throughout the stop.
    Evidence references record provenance only; they cannot self-qualify a bound.
    """
    result = dict(status='UNBOUNDED', qualified=False, movement_authorized=False,
                  physical_stop='UNKNOWN', ownership_release=False, tube=None,
                  independent_fail_safe='UNVERIFIED')
    if (not all(finite(v) for v in (x, y, linear_speed, angular_speed, footprint_radius))
            or linear_speed < 0 or footprint_radius <= 0 or not isinstance(inputs, StopInputs)):
        return {**result, 'reasons': ['INVALID_OBSERVATION_OR_FOOTPRINT']}
    values = asdict(inputs)
    missing = [name for name, value in values.items() if value is None]
    if missing:
        return {**result, 'reasons': ['MISSING_MEASUREMENTS'], 'missing': missing}
    digest = values.pop('evidence_sha256')
    if (not isinstance(digest, str) or len(digest) != 64 or set(digest)-set('0123456789abcdef')
            or any(not finite(v) or v < 0 for v in values.values())
            or inputs.linear_deceleration_m_s2 <= 0 or inputs.angular_deceleration_rad_s2 <= 0):
        return {**result, 'reasons': ['INVALID_MEASUREMENT_BOUNDS']}
    delay = sum(values[name] for name in ('detection_sec', 'computation_sec', 'communication_sec', 'actuator_sec'))
    v, w = linear_speed + inputs.speed_error_m_s, abs(angular_speed) + inputs.angular_speed_error_rad_s
    v1, w1 = v + inputs.linear_acceleration_m_s2*delay, w + inputs.angular_acceleration_rad_s2*delay
    distance = v*delay + inputs.linear_acceleration_m_s2*delay*delay/2 + v1*v1/(2*inputs.linear_deceleration_m_s2)
    angle = w*delay + inputs.angular_acceleration_rad_s2*delay*delay/2 + w1*w1/(2*inputs.angular_deceleration_rad_s2)
    horizon = delay + max(v1/inputs.linear_deceleration_m_s2, w1/inputs.angular_deceleration_rad_s2)
    radius = footprint_radius + inputs.position_error_m + inputs.margin_m + distance
    if not all(math.isfinite(v) for v in (delay, distance, angle, horizon, radius, x-radius, x+radius, y-radius, y+radius)):
        return {**result, 'reasons': ['NUMERICAL_OVERFLOW']}
    return {**result, 'status': 'CONDITIONAL_CANDIDATE', 'reasons': ['PHYSICAL_CALIBRATION_UNVERIFIED', 'NONZERO_DISABLED'],
            'distance_m': distance, 'angle_rad': angle, 'horizon_sec': horizon,
            'radius_m': radius, 'center': [x, y], 'evidence_sha256': digest,
            'tube': [asdict(b) for b in sweep([(x, y)], radius)],
            'rotation_handling': 'Circumscribed footprint includes every yaw; angle is diagnostic'}


def reservation_check(envelope, reserved):
    """Reuse B6B union containment. No claim is acquired, released or mutated."""
    if not envelope.get('tube'):
        return dict(status='UNKNOWN_STOP_TUBE', movement_authorized=False)
    boxes = tuple(Box(**v) for v in envelope['tube'])
    inside = all(covered(box, reserved) for box in boxes)
    return dict(status='CANDIDATE_INSIDE' if inside else 'PREDICTED_BOUNDARY_BREACH',
                qualified=False, movement_authorized=False)


def relative_stop_check(first, second):
    """Worst-case relative occupancy: either robot may move toward the other.

    Independent tubes cover their entire respective horizons, so no timing or
    mutual-yield assumption shrinks their Minkowski sum. Unbounded peer => unknown.
    """
    if not first.get('tube') or not second.get('tube'):
        return dict(status='UNKNOWN_RELATIVE_OCCUPANCY', movement_authorized=False)
    separation = math.dist(first['center'], second['center'])
    clearance = separation-first['radius_m']-second['radius_m']
    return dict(status='POTENTIAL_CONFLICT' if clearance <= 0 else 'CANDIDATES_DISJOINT',
                conditional_clearance_m=clearance, qualified=False, movement_authorized=False)
