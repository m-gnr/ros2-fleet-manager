r"""Scheduler for task assignment and safe preemption.

Implements approved rules:
- Dynamic Wh energy feasibility ($E_{required} \le E_{available}$)
- Nav2 global route path distance (NO Euclidean fallback on route failure - C3-DEC §2.1)
- Nearest eligible robot selection
- Tie-breaking: longest IDLE duration, then alphabetical robot_id (C3-DEC-03)
- Safe HIGH preemption rules:
  * Only HIGH task can preempt
  * Active task must be LOW or MEDIUM
  * Never preempt if an IDLE eligible robot exists
  * Candidate must be unloaded and prior to loading (PHASE_MOVING_TO_PICKUP)
  * N=2 preemption protection limit (task with preemption_count >= 2 cannot be preempted)
  * Tie-break between preemptible candidates by shortest pickup distance (Karar 08 T06)
"""

from dataclasses import dataclass
from math import isfinite
from typing import List, Optional, Protocol, Tuple

from .constants import (
    DEFAULT_EMERGENCY_SOC,
    DEFAULT_SAFETY_MARGIN_WH,
    DISTANCE_TIE_EPSILON,
    MAX_PREEMPTIONS,
    RobotState,
    TaskPhase,
    TaskPriority,
)
from .energy import check_energy_eligibility
from .models import Pose2D, PreemptionDecision, RobotRecord, Task


class RouteDistanceProvider(Protocol):
    """Protocol for calculating Nav2 path distances."""

    def get_path_distance(self, robot_id: str, start: Pose2D, goal: Pose2D) -> Optional[float]:
        """Return the Nav2 global path distance in metres, or None if path fails."""
        ...


@dataclass(frozen=True)
class CandidateEvaluation:
    """Detailed evaluation result of a robot candidate for a given task."""

    robot: RobotRecord
    d_pickup: float
    d_delivery: float
    d_escape: float
    d_total: float
    e_required_wh: float
    e_available_wh: float
    idle_duration: float


class Scheduler:
    """Fleet assignment and preemption scheduler."""

    def __init__(
        self,
        route_provider: RouteDistanceProvider,
        safe_charge_station_pose: Pose2D,
        *,
        emergency_soc_percent: float = DEFAULT_EMERGENCY_SOC,
        safety_margin_wh: float = DEFAULT_SAFETY_MARGIN_WH,
    ) -> None:
        self.route_provider = route_provider
        self.safe_charge_station_pose = safe_charge_station_pose
        self._emergency_soc_percent = emergency_soc_percent
        self._safety_margin_wh = safety_margin_wh
        self.route_lookup = None
        self.battery_clock_ns = None
        self.pending_route_tasks: set[str] = set()

    def evaluate_robot_for_task(
        self,
        robot: RobotRecord,
        task: Task,
        current_time: float,
    ) -> Optional[CandidateEvaluation]:
        """Evaluate a robot for executing a task.
        
        Returns CandidateEvaluation if route and energy are valid, else None.
        Strictly enforces NO Euclidean fallback if route planner fails.
        """
        sim_ns = self.battery_clock_ns() if self.battery_clock_ns is not None else None
        if not robot.has_fresh_battery(current_time, sim_ns) or not 0.0 <= robot.battery_soc_percent <= 100.0:
            return None

        legs = (
            (robot.pose, task.pickup_pose),
            (task.pickup_pose, task.dropoff_pose),
            (task.dropoff_pose, self.safe_charge_station_pose),
        )
        if self.route_lookup is None:
            distances = tuple(
                self.route_provider.get_path_distance(robot.robot_id, start, goal)
                for start, goal in legs
            )
        else:
            distances = self.route_lookup(robot, task, legs)
        if distances is None or any(d is None or not isfinite(d) or d < 0 for d in distances):
            return None
        d_pickup, d_delivery, d_escape = distances

        d_total = d_pickup + d_delivery

        # 2. Dynamic Wh Energy eligibility
        energy_res = check_energy_eligibility(
            specs=robot.specs,
            battery_soc_percent=robot.battery_soc_percent,
            d_total_m=d_total,
            d_escape_m=d_escape,
            emergency_soc_percent=self._emergency_soc_percent,
            safety_margin_wh=self._safety_margin_wh,
            battery_energy_wh=robot.battery_energy_wh if robot.requires_battery_telemetry else None,
        )

        if not energy_res.is_eligible:
            return None

        return CandidateEvaluation(
            robot=robot,
            d_pickup=d_pickup,
            d_delivery=d_delivery,
            d_escape=d_escape,
            d_total=d_total,
            e_required_wh=energy_res.required_wh,
            e_available_wh=energy_res.available_wh,
            idle_duration=robot.idle_duration(current_time),
        )

    def select_best_idle_robot(
        self,
        task: Task,
        available_robots: List[RobotRecord],
        current_time: float,
    ) -> Optional[Tuple[RobotRecord, CandidateEvaluation]]:
        """Find the nearest eligible IDLE or returning robot for a task.
        
        Tie-breaking (C3-DEC-03):
        - Primary: Minimum Nav2 pickup distance (d_pickup)
        - If |d1 - d2| <= 1e-4: Longest IDLE duration
        - If idle durations equal: Alphabetical robot_id (robot_1 < robot_2)
        """
        candidates: List[CandidateEvaluation] = []

        for robot in available_robots:
            if not robot.is_eligible_for_new_assignment(current_time):
                continue

            eval_res = self.evaluate_robot_for_task(robot, task, current_time)
            if eval_res is not None:
                candidates.append(eval_res)

        if not candidates or task.task_id in self.pending_route_tasks:
            return None

        # Sort with multi-tier tie-breaking:
        # We want:
        # 1. d_pickup ascending (clustered within DISTANCE_TIE_EPSILON)
        # 2. idle_duration descending (longer idle preferred)
        # 3. robot_id ascending
        best_candidate = candidates[0]
        for candidate in candidates[1:]:
            delta_d = abs(candidate.d_pickup - best_candidate.d_pickup)
            if delta_d > DISTANCE_TIE_EPSILON:
                # Substantial distance difference
                if candidate.d_pickup < best_candidate.d_pickup:
                    best_candidate = candidate
            else:
                # Distances are considered equal within epsilon -> apply C3-DEC-03 tie break
                if candidate.idle_duration > best_candidate.idle_duration:
                    best_candidate = candidate
                elif candidate.idle_duration == best_candidate.idle_duration:
                    if candidate.robot.robot_id < best_candidate.robot.robot_id:
                        best_candidate = candidate

        return (best_candidate.robot, best_candidate)

    def select_preemption_candidate(
        self,
        high_task: Task,
        active_robots: List[RobotRecord],
        active_tasks_by_robot: dict[str, Task],
        current_time: float,
    ) -> Optional[PreemptionDecision]:
        """Evaluate running robots for safe preemption by a HIGH priority task.
        
        Rules:
        - Only a HIGH task can preempt (high_task.priority == TaskPriority.PRIORITY_HIGH).
        - Active task on candidate robot must be LOW or MEDIUM.
        - Active task must NOT have been preempted N=2 times already.
        - Robot must be prior to pickup loading (current_phase == PHASE_MOVING_TO_PICKUP).
        - Robot must be unloaded (is_loaded == False).
        - Robot must not be STALE (is_stale == False).
        - Robot must have valid route distance and sufficient Wh energy for the HIGH task.
        - If multiple preemptible candidates exist, select the one with shortest pickup distance (T06).
        """
        if high_task.priority != TaskPriority.PRIORITY_HIGH:
            return None  # Only HIGH tasks can preempt

        preemptible_candidates: List[Tuple[RobotRecord, Task, CandidateEvaluation]] = []

        for robot in active_robots:
            # Must not be session blocked
            if robot.session_blocked:
                continue

            # Must not be stale
            if robot.is_stale(current_time):
                continue

            # Must be actively executing a task
            if robot.state != RobotState.STATE_EXECUTING_TASK:
                continue

            # Must be unloaded
            if robot.is_loaded:
                continue

            # Must strictly be in moving to pickup phase (pickup loading hasn't started)
            if robot.current_phase != TaskPhase.PHASE_MOVING_TO_PICKUP:
                continue

            # Check victim task
            victim_task = active_tasks_by_robot.get(robot.robot_id)
            if victim_task is None:
                continue

            # Running HIGH task can NEVER be preempted! (Karar 08 T07)
            if victim_task.priority == TaskPriority.PRIORITY_HIGH:
                continue

            # N=2 Preemption protection limit check (DOC-ARCH Sec 6.2)
            if victim_task.preemption_count >= MAX_PREEMPTIONS:
                continue

            # Evaluate robot's route and energy suitability for the incoming HIGH task
            eval_res = self.evaluate_robot_for_task(robot, high_task, current_time)
            if eval_res is None:
                continue

            preemptible_candidates.append((robot, victim_task, eval_res))

        if not preemptible_candidates or high_task.task_id in self.pending_route_tasks:
            return None

        # Sort candidates by shortest pickup distance to the HIGH task (Karar 08 T06)
        preemptible_candidates.sort(key=lambda item: item[2].d_pickup)

        best_robot, victim_task, best_eval = preemptible_candidates[0]

        return PreemptionDecision(
            high_task=high_task,
            victim_task=victim_task,
            robot_id=best_robot.robot_id,
            victim_goal_uuid=best_robot.active_goal_uuid or "",
            target_epoch=best_robot.current_epoch,
            reason=f"HIGH_PREEMPTION (victim={victim_task.task_id}, d_pickup={best_eval.d_pickup:.2f}m)",
        )
