"""Comprehensive unit tests for Pure Python Fleet Manager Core Domain.

Tests cover:
- T01: Work-conserving FIFO in same priority class (created_at order)
- T02: Strict priority dispatch order (HIGH -> MEDIUM -> LOW)
- T03: Non-preemption of active task by LOW or MEDIUM task
- T04: Nearest eligible IDLE robot selection by Nav2 route distance
- T05: IDLE robot priority over preemption (never preempt if IDLE robot available)
- T06: Preemption candidate selection by shortest Nav2 pickup distance
- T07: Running HIGH task protection (HIGH never preempts HIGH)
- T08: Preemption lock after pickup loading starts or when loaded
- T09: FIFO preservation of preempted task with original created_at
- N=2 Preemption protection limit
- Stale robot detection (2.0s threshold and recovery on fresh telemetry - C3-DEC-01)
- Communication loss monitoring (5s warning, 10s alert, NO automatic FAILED/ERROR - C3-DEC-02)
- Nav2 route planner failure & strict NO Euclidean fallback (C3-DEC §2.1)
- Wh energy insufficiency (E_required > E_available)
- Distance tie-break by longest IDLE duration and alphabetical robot_id (C3-DEC-03)
- Reservation single ownership and lifecycle
- Physical departure verification before FREE (C3-DEC §2.2)
- BLOCKED resource containment when robot is in STATE_ERROR (C3-DEC §2.2)
- Epoch and UUID deduplication / stale result rejection
"""

import pytest

from backend.fleet_manager.domain import (
    COMMUNICATION_ALERT_SEC,
    COMMUNICATION_WARNING_SEC,
    DISTANCE_TIE_EPSILON,
    MAX_PREEMPTIONS,
    ROBOT_STATUS_STALE_TIMEOUT_SEC,
    CandidateEvaluation,
    FleetManagerCore,
    FleetTracker,
    Pose2D,
    PreemptionDecision,
    ReservationManager,
    ReservationState,
    RobotBatterySpecs,
    RobotRecord,
    RobotState,
    RouteDistanceProvider,
    Scheduler,
    StationRecord,
    StationType,
    Task,
    TaskPhase,
    TaskPriority,
    TaskQueue,
    TaskResultStatus,
    TaskStatus,
    calculate_available_energy,
    calculate_emergency_reserve,
    calculate_escape_energy,
    calculate_remaining_energy,
    calculate_required_energy,
    check_energy_eligibility,
)


class MockRouteProvider:
    """Mock Nav2 route provider for deterministic testing."""

    def __init__(self, default_distance: float = 10.0) -> None:
        self.default_distance = default_distance
        self.route_overrides: dict[tuple[tuple[float, float], tuple[float, float]], float | None] = {}

    def set_distance(self, start: Pose2D, goal: Pose2D, distance: float | None) -> None:
        key = ((round(start.x, 3), round(start.y, 3)), (round(goal.x, 3), round(goal.y, 3)))
        self.route_overrides[key] = distance

    def get_path_distance(self, start: Pose2D, goal: Pose2D) -> float | None:
        key = ((round(start.x, 3), round(start.y, 3)), (round(goal.x, 3), round(goal.y, 3)))
        if key in self.route_overrides:
            return self.route_overrides[key]
        return self.default_distance


@pytest.fixture
def route_provider() -> MockRouteProvider:
    return MockRouteProvider(default_distance=10.0)


@pytest.fixture
def safe_dock_pose() -> Pose2D:
    return Pose2D(x=0.5, y=-2.0)


@pytest.fixture
def core(route_provider: MockRouteProvider, safe_dock_pose: Pose2D) -> FleetManagerCore:
    fm = FleetManagerCore(
        route_provider=route_provider,
        safe_charge_station_pose=safe_dock_pose,
    )
    # Register default stations
    fm.register_station("charge_dock_1", StationType.CHARGING, safe_dock_pose, tolerance_radius=0.30)
    fm.register_station("park_slot_1", StationType.PARKING, Pose2D(x=-2.0, y=1.0), tolerance_radius=0.30)
    return fm


# =============================================================================
# Wh Energy Model Tests
# =============================================================================
class TestEnergyModel:
    """Tests for Section 7 mathematical formulations and contracts."""

    def test_remaining_and_available_energy(self) -> None:
        usable_wh = 100.0
        soc = 50.0
        emergency_soc = 8.0

        rem = calculate_remaining_energy(usable_wh, soc)
        assert rem == 50.0

        emerg = calculate_emergency_reserve(usable_wh, emergency_soc)
        assert emerg == 8.0

        avail = calculate_available_energy(usable_wh, soc, emergency_soc)
        assert avail == 42.0

    def test_required_energy_formula(self) -> None:
        k = 0.20  # Wh/m
        d_total = 30.0  # metres
        d_escape = 15.0  # metres
        margin_wh = 10.0  # Wh

        e_escape = calculate_escape_energy(k, d_escape)
        assert e_escape == 3.0

        e_req = calculate_required_energy(k, d_total, d_escape, safety_margin_wh=margin_wh)
        # (0.20 * 30) + 3.0 + 10.0 = 6.0 + 3.0 + 10.0 = 19.0 Wh
        assert e_req == 19.0

    def test_energy_eligibility_sufficient(self) -> None:
        specs = RobotBatterySpecs(usable_capacity_wh=100.0, consumption_wh_per_meter=0.20)
        res = check_energy_eligibility(
            specs=specs,
            battery_soc_percent=50.0,
            d_total_m=30.0,
            d_escape_m=15.0,
            emergency_soc_percent=8.0,
            safety_margin_wh=10.0,
        )
        assert res.is_eligible is True
        assert res.required_wh == 19.0
        assert res.available_wh == 42.0
        assert res.reason == "ENERGY_SUFFICIENT"

    def test_energy_eligibility_insufficient(self) -> None:
        specs = RobotBatterySpecs(usable_capacity_wh=100.0, consumption_wh_per_meter=0.20)
        # SoC 15% -> available = (15 - 8) = 7.0 Wh
        # Required = 19.0 Wh -> Insufficient!
        res = check_energy_eligibility(
            specs=specs,
            battery_soc_percent=15.0,
            d_total_m=30.0,
            d_escape_m=15.0,
            emergency_soc_percent=8.0,
            safety_margin_wh=10.0,
        )
        assert res.is_eligible is False
        assert "ENERGY_INSUFFICIENT" in res.reason

    def test_route_failure_strict_no_euclidean_fallback(self) -> None:
        specs = RobotBatterySpecs(usable_capacity_wh=100.0, consumption_wh_per_meter=0.20)
        res = check_energy_eligibility(
            specs=specs,
            battery_soc_percent=80.0,
            d_total_m=None,  # Route planner failed!
            d_escape_m=15.0,
        )
        assert res.is_eligible is False
        assert res.reason == "NAV2_ROUTE_FAILED_EUCLIDEAN_FALLBACK_FORBIDDEN"


# =============================================================================
# TaskQueue Unit Tests
# =============================================================================
class TestTaskQueue:
    """Tests for multi-priority work-conserving FIFO queue."""

    def test_fifo_ordering_within_same_priority(self) -> None:
        q = TaskQueue()
        t1 = Task(task_id="t1", pickup_pose=Pose2D(), dropoff_pose=Pose2D(), priority=TaskPriority.PRIORITY_LOW, created_at=10.0)
        t2 = Task(task_id="t2", pickup_pose=Pose2D(), dropoff_pose=Pose2D(), priority=TaskPriority.PRIORITY_LOW, created_at=5.0)
        t3 = Task(task_id="t3", pickup_pose=Pose2D(), dropoff_pose=Pose2D(), priority=TaskPriority.PRIORITY_LOW, created_at=15.0)

        q.enqueue(t1)
        q.enqueue(t2)
        q.enqueue(t3)

        ordered = [t.task_id for t in q.iter_assignable_tasks()]
        assert ordered == ["t2", "t1", "t3"]

    def test_priority_ordering(self) -> None:
        q = TaskQueue()
        t_low = Task(task_id="low", pickup_pose=Pose2D(), dropoff_pose=Pose2D(), priority=TaskPriority.PRIORITY_LOW, created_at=1.0)
        t_med = Task(task_id="med", pickup_pose=Pose2D(), dropoff_pose=Pose2D(), priority=TaskPriority.PRIORITY_MEDIUM, created_at=2.0)
        t_high = Task(task_id="high", pickup_pose=Pose2D(), dropoff_pose=Pose2D(), priority=TaskPriority.PRIORITY_HIGH, created_at=3.0)

        q.enqueue(t_low)
        q.enqueue(t_med)
        q.enqueue(t_high)

        ordered = [t.task_id for t in q.iter_assignable_tasks()]
        assert ordered == ["high", "med", "low"]


# =============================================================================
# Karar 08 T01 - T09 Acceptance & Scenario Tests
# =============================================================================
class TestKarar08Scenarios:
    """Tests strictly mirroring Karar 08 test matrix T01-T09 and architectural rules."""

    def test_t01_fifo_same_priority(self, core: FleetManagerCore) -> None:
        """T01 / P01: Same priority class, different created_at. Assign in created_at order."""
        core.register_robot("robot_1", initial_pose=Pose2D(x=0, y=0))
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(x=0, y=0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=100.0,
        )

        core.submit_task("task_b", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_MEDIUM, created_at=102.0)
        core.submit_task("task_a", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_MEDIUM, created_at=100.0)
        core.submit_task("task_c", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_MEDIUM, created_at=105.0)

        assignments = core.schedule_tick(current_time=100.0)
        assert len(assignments) == 1
        r_id, assign = assignments[0]
        # task_a had earliest created_at (100.0)
        assert assign.task_id == "task_a"
        assert assign.robot_id == "robot_1"

    def test_t02_strict_priority_ordering(self, core: FleetManagerCore) -> None:
        """T02 / P01: Three priorities waiting together. Order must be HIGH -> MEDIUM -> LOW."""
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=10.0,
        )

        # Submit LOW first, then MEDIUM, then HIGH
        core.submit_task("low_task", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_LOW, created_at=1.0)
        core.submit_task("med_task", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_MEDIUM, created_at=2.0)
        core.submit_task("high_task", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_HIGH, created_at=3.0)

        assignments = core.schedule_tick(current_time=10.0)
        assert len(assignments) == 1
        assert assignments[0][1].task_id == "high_task"

    def test_t03_no_preemption_by_low_or_medium(self, core: FleetManagerCore) -> None:
        """T03 / P02: Active LOW task is NOT preempted when new LOW or MEDIUM arrives."""
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=10.0,
        )

        # Start low_1
        core.submit_task("low_1", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_LOW, created_at=1.0)
        core.schedule_tick(current_time=10.0)

        # Robot is executing low_1
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_EXECUTING_TASK, current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
            is_loaded=False, pose=Pose2D(0.5, 0.5), battery_soc_percent=98.0,
            battery_energy_wh=98.0, current_epoch=1, current_task_id="low_1", timestamp_sec=11.0,
        )

        # Now submit new MEDIUM and LOW tasks
        core.submit_task("med_2", Pose2D(3, 3), Pose2D(4, 4), priority=TaskPriority.PRIORITY_MEDIUM, created_at=12.0)
        core.submit_task("low_2", Pose2D(5, 5), Pose2D(6, 6), priority=TaskPriority.PRIORITY_LOW, created_at=13.0)

        new_assignments = core.schedule_tick(current_time=14.0)
        # Neither MEDIUM nor LOW can preempt active low_1!
        assert len(new_assignments) == 0
        robot = core.tracker.get_robot("robot_1")
        assert robot.current_task_id == "low_1"

    def test_t04_nearest_idle_robot_selection(self, core: FleetManagerCore, route_provider: MockRouteProvider) -> None:
        """T04 / P03: When multiple IDLE robots are available, nearest by Nav2 pickup route is selected."""
        core.register_robot("robot_far", initial_pose=Pose2D(0, 0))
        core.register_robot("robot_near", initial_pose=Pose2D(10, 10))

        core.handle_robot_status(
            robot_id="robot_far", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=10.0,
        )
        core.handle_robot_status(
            robot_id="robot_near", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(10, 10), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=10.0,
        )

        pickup = Pose2D(9, 9)
        # robot_far is 20m from pickup, robot_near is 2m from pickup
        route_provider.set_distance(Pose2D(0, 0), pickup, 20.0)
        route_provider.set_distance(Pose2D(10, 10), pickup, 2.0)

        core.submit_task("test_task", pickup, Pose2D(15, 15), priority=TaskPriority.PRIORITY_LOW, created_at=10.0)

        assignments = core.schedule_tick(current_time=10.0)
        assert len(assignments) == 1
        r_id, assign = assignments[0]
        assert r_id == "robot_near"  # Closer robot selected!
        assert assign.task_id == "test_task"

    def test_t05_idle_robot_priority_over_preemption(self, core: FleetManagerCore) -> None:
        """T05 / P03: If an IDLE robot is available, HIGH must NOT preempt running task."""
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))
        core.register_robot("robot_2", initial_pose=Pose2D(5, 5))

        # robot_1 running low_1
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_EXECUTING_TASK, current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=90.0,
            battery_energy_wh=90.0, current_epoch=1, current_task_id="low_1", timestamp_sec=10.0,
        )
        # robot_2 is IDLE
        core.handle_robot_status(
            robot_id="robot_2", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(5, 5), battery_soc_percent=90.0,
            battery_energy_wh=90.0, current_epoch=0, current_task_id=None, timestamp_sec=10.0,
        )

        # Submit HIGH task
        core.submit_task("high_task", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_HIGH, created_at=11.0)

        assignments = core.schedule_tick(current_time=12.0)
        assert len(assignments) == 1
        r_id, assign = assignments[0]
        # HIGH task went directly to IDLE robot_2!
        assert r_id == "robot_2"
        assert assign.task_id == "high_task"

    def test_t06_preemption_candidate_shortest_pickup(self, core: FleetManagerCore, route_provider: MockRouteProvider) -> None:
        """T06 / P04: No IDLE robot; two preemptible candidates. Select candidate with shortest pickup distance."""
        core.register_robot("robot_a", initial_pose=Pose2D(0, 0))
        core.register_robot("robot_b", initial_pose=Pose2D(10, 10))

        # Set up active tasks
        task_a = Task("task_a", Pose2D(0, 0), Pose2D(1, 1), priority=TaskPriority.PRIORITY_LOW, created_at=1.0)
        task_b = Task("task_b", Pose2D(10, 10), Pose2D(11, 11), priority=TaskPriority.PRIORITY_MEDIUM, created_at=2.0)
        core._active_tasks["task_a"] = task_a
        core._active_tasks_by_robot["robot_a"] = task_a
        core._active_tasks["task_b"] = task_b
        core._active_tasks_by_robot["robot_b"] = task_b

        core.handle_robot_status(
            robot_id="robot_a", state=RobotState.STATE_EXECUTING_TASK, current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=90.0,
            battery_energy_wh=90.0, current_epoch=1, current_task_id="task_a", timestamp_sec=15.0,
        )
        core.handle_robot_status(
            robot_id="robot_b", state=RobotState.STATE_EXECUTING_TASK, current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
            is_loaded=False, pose=Pose2D(10, 10), battery_soc_percent=90.0,
            battery_energy_wh=90.0, current_epoch=1, current_task_id="task_b", timestamp_sec=15.0,
        )

        high_pickup = Pose2D(2, 2)
        # robot_a to high_pickup is 3m, robot_b to high_pickup is 20m
        route_provider.set_distance(Pose2D(0, 0), high_pickup, 3.0)
        route_provider.set_distance(Pose2D(10, 10), high_pickup, 20.0)

        core.submit_task("high_task", high_pickup, Pose2D(4, 4), priority=TaskPriority.PRIORITY_HIGH, created_at=15.0)

        core.schedule_tick(current_time=16.0)

        # robot_a should be selected for preemption because it's closer to HIGH pickup (3m < 20m)
        assert "robot_a" in core._pending_preemption_assignments
        assert core._pending_preemption_assignments["robot_a"].task_id == "high_task"

    def test_t07_running_high_task_cannot_be_preempted(self, core: FleetManagerCore) -> None:
        """T07 / P06: Running HIGH task can NEVER be preempted by another HIGH task."""
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))
        active_high = Task("active_high", Pose2D(0, 0), Pose2D(1, 1), priority=TaskPriority.PRIORITY_HIGH, created_at=1.0)
        core._active_tasks["active_high"] = active_high
        core._active_tasks_by_robot["robot_1"] = active_high

        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_EXECUTING_TASK, current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=95.0,
            battery_energy_wh=95.0, current_epoch=1, current_task_id="active_high", timestamp_sec=10.0,
        )

        core.submit_task("new_high", Pose2D(2, 2), Pose2D(3, 3), priority=TaskPriority.PRIORITY_HIGH, created_at=12.0)

        core.schedule_tick(current_time=13.0)

        # Preemption must NOT be initiated on robot_1
        assert "robot_1" not in core._pending_preemption_assignments
        assert len(core.queue) == 1  # new_high stays safely queued

    def test_t08_preemption_locked_when_loading_or_loaded(self, core: FleetManagerCore) -> None:
        """T08 / P06: Preemption is forbidden once pickup loading starts or robot is loaded."""
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))
        active_low = Task("active_low", Pose2D(0, 0), Pose2D(1, 1), priority=TaskPriority.PRIORITY_LOW, created_at=1.0)
        core._active_tasks["active_low"] = active_low
        core._active_tasks_by_robot["robot_1"] = active_low

        # 1. Test when robot is in PHASE_LOADING (unloaded)
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_EXECUTING_TASK, current_phase=TaskPhase.PHASE_LOADING,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=95.0,
            battery_energy_wh=95.0, current_epoch=1, current_task_id="active_low", timestamp_sec=10.0,
        )
        core.submit_task("high_task_1", Pose2D(2, 2), Pose2D(3, 3), priority=TaskPriority.PRIORITY_HIGH, created_at=12.0)
        core.schedule_tick(current_time=13.0)
        assert "robot_1" not in core._pending_preemption_assignments

        # 2. Test when robot is loaded (PHASE_MOVING_TO_DROPOFF)
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_EXECUTING_TASK, current_phase=TaskPhase.PHASE_MOVING_TO_DROPOFF,
            is_loaded=True, pose=Pose2D(0.5, 0.5), battery_soc_percent=94.0,
            battery_energy_wh=94.0, current_epoch=1, current_task_id="active_low", timestamp_sec=15.0,
        )
        core.schedule_tick(current_time=16.0)
        assert "robot_1" not in core._pending_preemption_assignments

    def test_t09_preempted_task_preserves_original_created_at(self, core: FleetManagerCore) -> None:
        """T09 / P05: Preempted task returns to queue with original created_at, preserving FIFO rank."""
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))

        # low_1 submitted at t=100
        low_1 = core.submit_task("low_1", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_LOW, created_at=100.0)
        # Assign to robot_1
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=101.0,
        )
        assigns = core.schedule_tick(current_time=101.0)
        assert len(assigns) == 1
        assign = assigns[0][1]

        # low_2 submitted at t=102, low_3 at t=103
        core.submit_task("low_2", Pose2D(3, 3), Pose2D(4, 4), priority=TaskPriority.PRIORITY_LOW, created_at=102.0)
        core.submit_task("low_3", Pose2D(5, 5), Pose2D(6, 6), priority=TaskPriority.PRIORITY_LOW, created_at=103.0)

        # robot_1 reports MOVING_TO_PICKUP
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_EXECUTING_TASK, current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
            is_loaded=False, pose=Pose2D(0.2, 0.2), battery_soc_percent=99.0,
            battery_energy_wh=99.0, current_epoch=1, current_task_id="low_1", timestamp_sec=104.0,
        )

        # HIGH task arrives at t=105 -> triggers preemption of low_1
        core.submit_task("high_task", Pose2D(2, 2), Pose2D(3, 3), priority=TaskPriority.PRIORITY_HIGH, created_at=105.0)
        core.schedule_tick(current_time=105.0)
        assert "robot_1" in core._pending_preemption_assignments

        # Terminal PREEMPTED action result arrives from Executor
        accepted, task = core.handle_action_result(
            robot_id="robot_1",
            task_id="low_1",
            result_status=TaskResultStatus.STATUS_PREEMPTED,
            completed_epoch=assign.assignment_epoch,
            goal_uuid=assign.goal_uuid,
        )
        assert accepted is True
        assert task.preemption_count == 1
        assert task.created_at == 100.0  # Original created_at preserved!

        # Check queue order of LOW tasks: low_1 (100.0) MUST be before low_2 (102.0) and low_3 (103.0)
        low_tasks = [t.task_id for t in core.queue.iter_assignable_tasks() if t.priority == TaskPriority.PRIORITY_LOW]
        assert low_tasks == ["low_1", "low_2", "low_3"]


# =============================================================================
# N=2 Preemption Protection Limit Tests
# =============================================================================
class TestN2PreemptionProtection:
    """Tests for N=2 preemption protection limit (Karar 08, DOC-ARCH Sec 6.2)."""

    def test_n2_preemption_counter_and_immunity(self, core: FleetManagerCore) -> None:
        """A task preempted N=2 times cannot be preempted on its 3rd execution."""
        task = Task(
            task_id="resilient_task",
            pickup_pose=Pose2D(1, 1),
            dropoff_pose=Pose2D(2, 2),
            priority=TaskPriority.PRIORITY_LOW,
            created_at=10.0,
            preemption_count=0,
        )
        assert task.can_be_preempted() is True

        # First preemption
        task.preemption_count = 1
        assert task.can_be_preempted() is True

        # Second preemption (N=2 reached)
        task.preemption_count = 2
        assert task.can_be_preempted() is False  # Protected!

        # Try scheduling a HIGH task when running task has preemption_count = 2
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))
        core._active_tasks["resilient_task"] = task
        core._active_tasks_by_robot["robot_1"] = task

        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_EXECUTING_TASK, current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=90.0,
            battery_energy_wh=90.0, current_epoch=3, current_task_id="resilient_task", timestamp_sec=20.0,
        )

        core.submit_task("high_task", Pose2D(2, 2), Pose2D(3, 3), priority=TaskPriority.PRIORITY_HIGH, created_at=25.0)
        core.schedule_tick(current_time=25.0)

        # Must NOT preempt resilient_task!
        assert "robot_1" not in core._pending_preemption_assignments
        assert len(core.queue) == 1


# =============================================================================
# C3-DEC-01 & C3-DEC-02: Stale Detection & Communication Health Tests
# =============================================================================
class TestStaleAndCommunicationHealth:
    """Tests for C3-DEC-01 (2.0s stale exclusion) and C3-DEC-02 (communication monitoring)."""

    def test_stale_robot_excluded_and_recovered(self, core: FleetManagerCore) -> None:
        """RobotStatus not received for > 2.0s is excluded; recovers on fresh status."""
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))

        # Status at t=10.0s
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=10.0,
        )

        core.submit_task("task_1", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_LOW, created_at=10.0)

        # At t=12.1s (dt = 2.1s > 2.0s threshold) -> robot is STALE
        assert core.tracker.is_stale("robot_1", current_time=12.1) is True
        assigns = core.schedule_tick(current_time=12.1)
        assert len(assigns) == 0  # Not assigned because robot is stale!

        # Fresh status arrives at t=12.2s
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=12.2,
        )
        assert core.tracker.is_stale("robot_1", current_time=12.2) is False

        # Now scheduling succeeds!
        assigns = core.schedule_tick(current_time=12.3)
        assert len(assigns) == 1
        assert assigns[0][1].task_id == "task_1"

    def test_communication_loss_no_automatic_failed_or_error(self, core: FleetManagerCore) -> None:
        """Communication loss at 5s produces warning, 10s alert; NO automatic FAILED or ERROR."""
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_EXECUTING_TASK, current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=90.0,
            battery_energy_wh=90.0, current_epoch=1, current_task_id="active_task", timestamp_sec=10.0,
        )

        task = Task("active_task", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_LOW, created_at=5.0)
        core._active_tasks["active_task"] = task
        core._active_tasks_by_robot["robot_1"] = task

        # At dt = 5.5s -> WARNING
        health_5 = core.tracker.check_communication_health(current_time=15.5)
        assert len(health_5) == 1
        assert health_5[0][1] == "WARNING"

        # At dt = 10.5s -> ALERT
        health_10 = core.tracker.check_communication_health(current_time=20.5)
        assert len(health_10) == 1
        assert health_10[0][1] == "ALERT"

        # Crucially: Task MUST NOT be marked FAILED, and robot MUST NOT be marked ERROR!
        assert task.status != TaskStatus.FAILED
        assert core.tracker.get_robot("robot_1").state != RobotState.STATE_ERROR


# =============================================================================
# C3-DEC-03: Distance Tie-Breaking Tests
# =============================================================================
class TestTieBreaking:
    """Tests for C3-DEC-03 (equal distance tie-breaking by longest IDLE, then robot_id)."""

    def test_equal_distance_longest_idle_preferred(self, core: FleetManagerCore, route_provider: MockRouteProvider) -> None:
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))
        core.register_robot("robot_2", initial_pose=Pose2D(0, 0))

        # Both robots at same distance (default 10m)
        # robot_1 became IDLE at t=10 (idle for 50s at t=60)
        # robot_2 became IDLE at t=40 (idle for 20s at t=60)
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=10.0,
        )
        core.handle_robot_status(
            robot_id="robot_2", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=40.0,
        )

        core.submit_task("task_x", Pose2D(5, 5), Pose2D(6, 6), priority=TaskPriority.PRIORITY_LOW, created_at=55.0)

        # Fresh telemetry at t=59.0 for both
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=59.0,
        )
        core.handle_robot_status(
            robot_id="robot_2", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=59.0,
        )

        # Note: idle_start_timestamp was set at t=10 for robot_1, t=40 for robot_2
        assigns = core.schedule_tick(current_time=60.0)
        assert len(assigns) == 1
        assert assigns[0][0] == "robot_1"  # robot_1 was idle longer!

    def test_equal_distance_and_equal_idle_alphabetical_tie_break(self, core: FleetManagerCore) -> None:
        core.register_robot("robot_2", initial_pose=Pose2D(0, 0))
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))

        # Both became IDLE at exactly t=20.0
        core.handle_robot_status(
            robot_id="robot_2", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=20.0,
        )
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=20.0,
        )

        core.submit_task("task_y", Pose2D(5, 5), Pose2D(6, 6), priority=TaskPriority.PRIORITY_LOW, created_at=20.0)

        assigns = core.schedule_tick(current_time=21.0)
        assert len(assigns) == 1
        # robot_1 < robot_2 alphabetically
        assert assigns[0][0] == "robot_1"


# =============================================================================
# Reservation, Single Ownership, Physical Departure & BLOCKED Tests
# =============================================================================
class TestReservations:
    """Tests for station reservation rules, physical departure, and BLOCKED containment."""

    def test_single_ownership_enforcement(self) -> None:
        mgr = ReservationManager()
        mgr.register_station("dock_1", StationType.CHARGING, Pose2D(0, 0), tolerance_radius=0.30)

        # First reservation succeeds
        assert mgr.reserve("dock_1", "robot_1") is True
        st = mgr.get_station("dock_1")
        assert st.state == ReservationState.RESERVED
        assert st.reserved_by_robot_id == "robot_1"

        # Second reservation by robot_2 MUST fail!
        assert mgr.reserve("dock_1", "robot_2") is False

    def test_physical_departure_rule(self) -> None:
        """Station cannot be marked FREE until robot physically departs tolerance + margin."""
        mgr = ReservationManager()
        mgr.register_station("dock_1", StationType.CHARGING, Pose2D(0, 0), tolerance_radius=0.30, departure_margin=0.05)
        mgr.mark_occupied("dock_1", "robot_1")

        # Initiate release
        mgr.initiate_release("dock_1", "robot_1")
        assert mgr.get_station("dock_1").state == ReservationState.RELEASING

        # Robot at 0.20m (within tolerance 0.30 + margin 0.05 = 0.35m)
        became_free = mgr.update_physical_departure("dock_1", Pose2D(0.20, 0.0))
        assert became_free is False
        assert mgr.get_station("dock_1").state == ReservationState.RELEASING

        # Robot at 0.40m (> 0.35m) -> physically departed!
        became_free = mgr.update_physical_departure("dock_1", Pose2D(0.40, 0.0))
        assert became_free is True
        assert mgr.get_station("dock_1").state == ReservationState.FREE
        assert mgr.get_station("dock_1").reserved_by_robot_id is None

    def test_blocked_resource_on_error(self, core: FleetManagerCore) -> None:
        """When occupying robot enters STATE_ERROR, station transitions to BLOCKED."""
        core.register_robot("robot_1", initial_pose=Pose2D(0.5, -2.0))
        core.reservations.mark_occupied("charge_dock_1", "robot_1")

        # Robot reports STATE_ERROR
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_ERROR, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0.5, -2.0), battery_soc_percent=50.0,
            battery_energy_wh=50.0, current_epoch=1, current_task_id=None, timestamp_sec=10.0,
        )

        station = core.reservations.get_station("charge_dock_1")
        assert station.state == ReservationState.BLOCKED

        # Another robot cannot reserve BLOCKED station
        assert core.reservations.reserve("charge_dock_1", "robot_2") is False


# =============================================================================
# Deduplication and Epoch/UUID Matching Tests
# =============================================================================
class TestDeduplicationAndMatching:
    """Tests for UUID, monotonic assignment_epoch, and stale result filtering."""

    def test_stale_result_deduplication(self, core: FleetManagerCore) -> None:
        core.register_robot("robot_1", initial_pose=Pose2D(0, 0))
        core.handle_robot_status(
            robot_id="robot_1", state=RobotState.STATE_IDLE, current_phase=TaskPhase.PHASE_NONE,
            is_loaded=False, pose=Pose2D(0, 0), battery_soc_percent=100.0,
            battery_energy_wh=100.0, current_epoch=0, current_task_id=None, timestamp_sec=10.0,
        )

        core.submit_task("task_active", Pose2D(1, 1), Pose2D(2, 2), priority=TaskPriority.PRIORITY_LOW, created_at=10.0)
        assigns = core.schedule_tick(current_time=10.0)
        assert len(assigns) == 1
        assign = assigns[0][1]

        # Stale result with previous epoch (epoch=0) arrives -> ignored!
        accepted, task = core.handle_action_result(
            robot_id="robot_1", task_id="task_active", result_status=TaskResultStatus.STATUS_SUCCEEDED,
            completed_epoch=0, goal_uuid="stale-uuid-123",
        )
        assert accepted is False
        assert core.tracker.get_robot("robot_1").current_task_id == "task_active"

        # Matching result with correct epoch and goal UUID succeeds!
        accepted, task = core.handle_action_result(
            robot_id="robot_1", task_id="task_active", result_status=TaskResultStatus.STATUS_SUCCEEDED,
            completed_epoch=assign.assignment_epoch, goal_uuid=assign.goal_uuid,
        )
        assert accepted is True
        assert task.status == TaskStatus.COMPLETED
