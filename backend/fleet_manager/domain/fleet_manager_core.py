"""Pure Python Fleet Manager Core Engine.

Coordinates:
- Task Queue (Priority HIGH -> MED -> LOW, work-conserving FIFO, no aging)
- Fleet Tracker (RobotStatus 5 Hz updates, 2.0s stale exclusion, comm health)
- Reservation Manager (Station single ownership, physical departure, BLOCKED containment)
- Scheduler (Route distance, Wh energy, nearest idle robot, tie-breaking, safe preemption)
- Assignment & UUID/Epoch matching (Deduplication, stale result rejection)
"""

import logging
from typing import Dict, List, Optional, Tuple
import uuid

from .constants import (
    COMMUNICATION_ALERT_SEC,
    COMMUNICATION_WARNING_SEC,
    ROBOT_STATUS_STALE_TIMEOUT_SEC,
    ReservationState,
    RobotState,
    StationType,
    TaskPhase,
    TaskPriority,
    TaskResultStatus,
    TaskStatus,
)
from .fleet_tracker import FleetTracker
from .models import (
    Assignment,
    Pose2D,
    PreemptionDecision,
    RobotBatterySpecs,
    RobotRecord,
    StationRecord,
    Task,
)
from .reservations import ReservationManager
from .scheduler import RouteDistanceProvider, Scheduler
from .task_queue import TaskQueue

logger = logging.getLogger(__name__)


class FleetManagerCore:
    """Central pure Python domain core for ROS 2 Fleet Manager."""

    def __init__(
        self,
        route_provider: RouteDistanceProvider,
        safe_charge_station_pose: Pose2D,
    ) -> None:
        self.queue = TaskQueue()
        self.tracker = FleetTracker()
        self.reservations = ReservationManager()
        self.scheduler = Scheduler(
            route_provider=route_provider,
            safe_charge_station_pose=safe_charge_station_pose,
        )

        # Active tasks by task_id and by robot_id
        self._active_tasks: Dict[str, Task] = {}
        self._active_tasks_by_robot: Dict[str, Task] = {}

        # Preemption in progress: maps robot_id -> pending HIGH task
        self._pending_preemption_assignments: Dict[str, Task] = {}

        # History of completed / failed tasks
        self._completed_tasks: Dict[str, Task] = {}
        self._failed_tasks: Dict[str, Task] = {}

    # -------------------------------------------------------------------------
    # Configuration / Registration
    # -------------------------------------------------------------------------
    def register_robot(
        self,
        robot_id: str,
        specs: Optional[RobotBatterySpecs] = None,
        initial_pose: Optional[Pose2D] = None,
    ) -> RobotRecord:
        """Register a robot from fleet configuration."""
        return self.tracker.register_robot(robot_id, specs=specs, initial_pose=initial_pose)

    def register_station(
        self,
        station_id: str,
        station_type: StationType,
        pose: Pose2D,
        tolerance_radius: float = 0.30,
        departure_margin: float = 0.05,
    ) -> StationRecord:
        """Register a station or parking slot."""
        return self.reservations.register_station(
            station_id=station_id,
            station_type=station_type,
            pose=pose,
            tolerance_radius=tolerance_radius,
            departure_margin=departure_margin,
        )

    # -------------------------------------------------------------------------
    # Task Ingestion
    # -------------------------------------------------------------------------
    def submit_task(
        self,
        task_id: str,
        pickup_pose: Pose2D,
        dropoff_pose: Pose2D,
        priority: int = TaskPriority.PRIORITY_LOW,
        created_at: float = 0.0,
    ) -> Task:
        """Submit a new transport task to the queue."""
        task = Task(
            task_id=task_id,
            pickup_pose=pickup_pose,
            dropoff_pose=dropoff_pose,
            priority=priority,
            created_at=created_at,
            status=TaskStatus.QUEUED,
        )
        self.queue.enqueue(task)
        return task

    # -------------------------------------------------------------------------
    # Telemetry and Event Handlers
    # -------------------------------------------------------------------------
    def handle_robot_status(
        self,
        robot_id: str,
        state: int,
        current_phase: int,
        is_loaded: bool,
        pose: Pose2D,
        battery_soc_percent: float,
        battery_energy_wh: float,
        current_epoch: int,
        current_task_id: Optional[str],
        timestamp_sec: float,
    ) -> Optional[RobotRecord]:
        """Process incoming 5 Hz RobotStatus message.
        
        Strictly preserves the Robot Executor as the single authority of physical state.
        Also checks physical departure from stations and marks BLOCKED if robot entered ERROR.
        """
        robot = self.tracker.update_robot_status(
            robot_id=robot_id,
            state=state,
            current_phase=current_phase,
            is_loaded=is_loaded,
            pose=pose,
            battery_soc_percent=battery_soc_percent,
            battery_energy_wh=battery_energy_wh,
            current_epoch=current_epoch,
            current_task_id=current_task_id,
            timestamp_sec=timestamp_sec,
        )
        if robot is None:
            return None

        # Check departure from any station robot was occupying/releasing
        station = self.reservations.get_station_by_robot(robot_id)
        if station is not None:
            if state == RobotState.STATE_ERROR:
                # Robot errored at station -> mark resource BLOCKED (C3-DEC §2.2)
                self.reservations.mark_blocked(station.station_id, robot_id)
            elif station.state in (ReservationState.RELEASING, ReservationState.OCCUPIED):
                self.reservations.update_physical_departure(station.station_id, pose)

        return robot

    def handle_action_feedback(
        self,
        robot_id: str,
        task_id: str,
        current_phase: int,
        assignment_epoch: int,
        goal_uuid: str,
    ) -> bool:
        """Validate and handle action feedback.
        
        Discards stale or mismatched feedback based on (task_id, epoch, goal_uuid).
        """
        robot = self.tracker.get_robot(robot_id)
        if robot is None:
            return False

        # Strictly validate assignment identity
        if (
            robot.current_task_id != task_id
            or robot.current_epoch != assignment_epoch
            or robot.active_goal_uuid != goal_uuid
        ):
            # Mismatched or stale feedback -> ignore
            return False

        task = self._active_tasks.get(task_id)
        if task is not None and task.status == TaskStatus.ASSIGNED:
            task.status = TaskStatus.EXECUTING

        return True

    def handle_action_result(
        self,
        robot_id: str,
        task_id: str,
        result_status: int,
        completed_epoch: int,
        goal_uuid: str,
        error_reason: str = "",
    ) -> Tuple[bool, Optional[Task]]:
        """Validate and handle terminal action result from Robot Executor.
        
        Strictly filters out-of-order or stale results (C3-DEC §2.3 / DOC-ARCH Sec 6).
        Returns (accepted, task).
        """
        robot = self.tracker.get_robot(robot_id)
        if robot is None:
            return False, None

        # Strictly match (task_id, completed_epoch, goal_uuid)
        if (
            robot.current_task_id != task_id
            or robot.current_epoch != completed_epoch
            or robot.active_goal_uuid != goal_uuid
        ):
            # Outdated or duplicate result -> ignore (idempotency & deduplication)
            return False, None

        task = self._active_tasks.pop(task_id, None)
        self._active_tasks_by_robot.pop(robot_id, None)

        if task is None:
            return False, None

        if result_status == TaskResultStatus.STATUS_SUCCEEDED:
            task.status = TaskStatus.COMPLETED
            self._completed_tasks[task_id] = task
            # Clear robot active goal
            robot.active_goal_uuid = None
            robot.current_task_id = None
            return True, task

        elif result_status == TaskResultStatus.STATUS_PREEMPTED:
            # Safe Preemption Handshake Completion:
            # 1. Increment victim task preemption_count
            task.preemption_count += 1
            task.status = TaskStatus.PREEMPTED
            # 2. Requeue victim with original created_at (Karar 08 T09)
            self.queue.requeue_preempted(task)

            # 3. Clear robot active goal
            robot.active_goal_uuid = None
            robot.current_task_id = None

            # 4. Check if a HIGH task was waiting for this robot
            pending_high = self._pending_preemption_assignments.pop(robot_id, None)
            if pending_high is not None:
                # Dispatch the waiting HIGH task now that robot is confirmed PREEMPTED/stopped
                self._dispatch_assignment(robot, pending_high)

            return True, task

        elif result_status == TaskResultStatus.STATUS_FAILED:
            # Strict Policy (P14, C3-DEC §2): No automatic retry or reassignment
            task.status = TaskStatus.FAILED
            self._failed_tasks[task_id] = task
            robot.active_goal_uuid = None
            robot.current_task_id = None

            # Mark occupied station BLOCKED if any
            station = self.reservations.get_station_by_robot(robot_id)
            if station is not None:
                self.reservations.mark_blocked(station.station_id, robot_id)

            return True, task

        return False, None

    # -------------------------------------------------------------------------
    # Scheduling Cycle
    # -------------------------------------------------------------------------
    def schedule_tick(
        self,
        current_time: float,
    ) -> List[Tuple[str, Assignment]]:
        """Run one scheduling evaluation pass across the queued tasks.
        
        Returns list of newly dispatched assignments: [(robot_id, Assignment), ...]
        """
        new_assignments: List[Tuple[str, Assignment]] = []

        # Iterate through queued tasks in Priority / FIFO order
        for task in self.queue.iter_assignable_tasks():
            # 1. Look for available eligible IDLE or returning robots
            idle_robots = self.tracker.get_eligible_idle_robots(current_time)
            # Filter out robots currently in preemption handshake
            idle_robots = [
                r for r in idle_robots
                if r.robot_id not in self._pending_preemption_assignments
                and r.robot_id not in self._active_tasks_by_robot
            ]

            selection = self.scheduler.select_best_idle_robot(
                task=task,
                available_robots=idle_robots,
                current_time=current_time,
            )

            if selection is not None:
                robot, eval_res = selection
                # Assign task to this idle robot!
                self.queue.remove(task.task_id)
                assignment = self._dispatch_assignment(robot, task, current_time)
                new_assignments.append((robot.robot_id, assignment))
                continue

            # 2. If task is HIGH priority and no IDLE robot was available:
            #    Attempt safe preemption of a running LOW/MEDIUM task
            if task.priority == TaskPriority.PRIORITY_HIGH:
                active_robots = [
                    r for r in self.tracker.list_robots()
                    if r.robot_id in self._active_tasks_by_robot
                    and r.robot_id not in self._pending_preemption_assignments
                ]
                preemption = self.scheduler.select_preemption_candidate(
                    high_task=task,
                    active_robots=active_robots,
                    active_tasks_by_robot=self._active_tasks_by_robot,
                    current_time=current_time,
                )
                if preemption is not None:
                    # Initiate preemption!
                    # Remove HIGH task from queue and hold it in pending preemption
                    self.queue.remove(task.task_id)
                    self._pending_preemption_assignments[preemption.robot_id] = task
                    # Note: We do NOT assign the HIGH task immediately!
                    # Fleet Manager must await terminal PREEMPTED result before dispatching (DOC-ARCH Sec 6.2).
                    logger.info(f"Initiated safe preemption: {preemption.reason}")

            # 3. If cannot assign or preempt, skip to next task in work-conserving FIFO

        return new_assignments

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------
    def _dispatch_assignment(
        self,
        robot: RobotRecord,
        task: Task,
        current_time: float = 0.0,
    ) -> Assignment:
        """Assign task to robot with incremented monotonic epoch and new goal UUID."""
        # Check if robot was at a station and initiate release
        station = self.reservations.get_station_by_robot(robot.robot_id)
        if station is not None and station.state in (ReservationState.RESERVED, ReservationState.OCCUPIED):
            self.reservations.initiate_release(station.station_id, robot.robot_id)

        # Increment monotonic assignment epoch
        robot.current_epoch += 1
        new_uuid = str(uuid.uuid4())

        robot.current_task_id = task.task_id
        robot.active_goal_uuid = new_uuid
        robot.state = RobotState.STATE_EXECUTING_TASK

        task.assigned_robot_id = robot.robot_id
        task.assignment_epoch = robot.current_epoch
        task.goal_uuid = new_uuid
        task.status = TaskStatus.ASSIGNED

        self._active_tasks[task.task_id] = task
        self._active_tasks_by_robot[robot.robot_id] = task

        return Assignment(
            task_id=task.task_id,
            robot_id=robot.robot_id,
            assignment_epoch=robot.current_epoch,
            goal_uuid=new_uuid,
            pickup_pose=task.pickup_pose,
            dropoff_pose=task.dropoff_pose,
            priority=task.priority,
            assigned_at=current_time,
        )
