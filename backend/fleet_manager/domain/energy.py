"""Wh-based energy model and dynamic eligibility calculations.

This module implements the mathematical formulations locked in:
- DOC-ARCH-2026-10-23-FINAL (Section 7)
- C3 Decisions (Section 2.1 - Nav2 route failure & no Euclidean fallback)
"""

from dataclasses import dataclass
from typing import Optional

from .constants import DEFAULT_EMERGENCY_SOC, DEFAULT_SAFETY_MARGIN_WH
from .models import RobotBatterySpecs


@dataclass(frozen=True)
class EnergyEligibilityResult:
    """Result of an energy eligibility evaluation for a task."""

    is_eligible: bool
    remaining_wh: float
    available_wh: float
    required_wh: float
    d_total_m: Optional[float]
    d_escape_m: Optional[float]
    reason: str = ""


def calculate_remaining_energy(usable_capacity_wh: float, soc_percent: float) -> float:
    """Calculate an instantaneous physical remaining energy in Wh:
    
    E_remaining = C_usable * (SoC / 100)
    """
    clamped_soc = max(0.0, min(100.0, soc_percent))
    return usable_capacity_wh * (clamped_soc / 100.0)


def calculate_emergency_reserve(usable_capacity_wh: float, emergency_soc_percent: float = DEFAULT_EMERGENCY_SOC) -> float:
    """Calculate the non-negotiable emergency reserve buffer in Wh:
    
    E_emergency = C_usable * (SoC_emergency / 100)
    """
    return usable_capacity_wh * (emergency_soc_percent / 100.0)


def calculate_available_energy(
    usable_capacity_wh: float,
    soc_percent: float,
    emergency_soc_percent: float = DEFAULT_EMERGENCY_SOC,
) -> float:
    """Calculate net assignable energy above emergency threshold in Wh:
    
    E_available = E_remaining - (C_usable * SoC_emergency / 100)
    """
    e_remaining = calculate_remaining_energy(usable_capacity_wh, soc_percent)
    e_emergency = calculate_emergency_reserve(usable_capacity_wh, emergency_soc_percent)
    return max(0.0, e_remaining - e_emergency)


def calculate_escape_energy(
    consumption_wh_per_meter: float,
    d_escape_m: float,
) -> float:
    """Calculate escape energy from dropoff to nearest safe charge station in Wh:
    
    E_escape = k * L(p_dropoff, p_safe_charge_station)
    """
    return consumption_wh_per_meter * d_escape_m


def calculate_required_energy(
    consumption_wh_per_meter: float,
    d_total_m: float,
    d_escape_m: float,
    safety_margin_wh: float = DEFAULT_SAFETY_MARGIN_WH,
) -> float:
    """Calculate total task energy required in Wh:
    
    E_required = (k * d_total) + E_escape + E_margin
    
    Note on double counting: E_margin and E_escape are distinct energy terms;
    they must never be added as distance in d_total.
    """
    e_escape = calculate_escape_energy(consumption_wh_per_meter, d_escape_m)
    return (consumption_wh_per_meter * d_total_m) + e_escape + safety_margin_wh


def check_energy_eligibility(
    specs: RobotBatterySpecs,
    battery_soc_percent: float,
    d_total_m: Optional[float],
    d_escape_m: Optional[float],
    emergency_soc_percent: float = DEFAULT_EMERGENCY_SOC,
    safety_margin_wh: float = DEFAULT_SAFETY_MARGIN_WH,
) -> EnergyEligibilityResult:
    """Check whether a robot satisfies the dynamic Wh energy eligibility condition:
    
    E_required <= E_available
    
    STRICT CONTRACT (C3-DEC §2.1):
    If Nav2 route distance cannot be calculated (d_total_m is None or d_escape_m is None),
    Euclidean fallback MUST NOT be used under any circumstances.
    Energy eligibility must immediately FAIL.
    """
    e_rem = calculate_remaining_energy(specs.usable_capacity_wh, battery_soc_percent)
    e_avail = calculate_available_energy(specs.usable_capacity_wh, battery_soc_percent, emergency_soc_percent)

    if d_total_m is None or d_escape_m is None:
        return EnergyEligibilityResult(
            is_eligible=False,
            remaining_wh=e_rem,
            available_wh=e_avail,
            required_wh=0.0,
            d_total_m=d_total_m,
            d_escape_m=d_escape_m,
            reason="NAV2_ROUTE_FAILED_EUCLIDEAN_FALLBACK_FORBIDDEN",
        )

    if d_total_m < 0.0 or d_escape_m < 0.0:
        return EnergyEligibilityResult(
            is_eligible=False,
            remaining_wh=e_rem,
            available_wh=e_avail,
            required_wh=0.0,
            d_total_m=d_total_m,
            d_escape_m=d_escape_m,
            reason="INVALID_NEGATIVE_ROUTE_DISTANCE",
        )

    e_req = calculate_required_energy(
        consumption_wh_per_meter=specs.consumption_wh_per_meter,
        d_total_m=d_total_m,
        d_escape_m=d_escape_m,
        safety_margin_wh=safety_margin_wh,
    )

    if e_req <= e_avail:
        return EnergyEligibilityResult(
            is_eligible=True,
            remaining_wh=e_rem,
            available_wh=e_avail,
            required_wh=e_req,
            d_total_m=d_total_m,
            d_escape_m=d_escape_m,
            reason="ENERGY_SUFFICIENT",
        )
    else:
        return EnergyEligibilityResult(
            is_eligible=False,
            remaining_wh=e_rem,
            available_wh=e_avail,
            required_wh=e_req,
            d_total_m=d_total_m,
            d_escape_m=d_escape_m,
            reason=f"ENERGY_INSUFFICIENT (req={e_req:.2f} Wh > avail={e_avail:.2f} Wh)",
        )
