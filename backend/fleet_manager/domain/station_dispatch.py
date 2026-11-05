"""Station movement planning and ownership, independent of transport tasks."""

from dataclasses import dataclass
from math import isfinite
from uuid import uuid4

from .constants import ReservationState, RobotState, StationType, TaskResultStatus
from .energy import check_energy_eligibility
from .models import Pose2D


@dataclass
class StationMove:
    task_id: str  # Internal movement identity used by the Outbox envelope.
    assigned_robot_id: str
    station_id: str
    station_type: StationType
    pose: Pose2D
    tolerance_radius: float
    session_id: str
    assignment_epoch: int
    goal_uuid: str
    status: str = "ASSIGNED"
    cancel_for_task: str | None = None
    cancel_declined: bool = False
    error_reason: str = ""


class StationDispatch:
    def __init__(self, low_soc_percent):
        self.low_soc_percent = low_soc_percent
        self.active = {}
        self.history = {}
        self.park_due = set()
        self.held = set()
        self.wait_reasons = {}

    def can_move(self, core, robot, now):
        sim_ns = core.scheduler.battery_clock_ns() if core.scheduler.battery_clock_ns else None
        return (
            robot.robot_id not in core._active_tasks_by_robot
            and robot.robot_id not in self.active
            and robot.robot_id not in self.held
            and robot.session_id
            and robot.state == RobotState.STATE_IDLE
            and robot.is_eligible_for_new_assignment(now)
            and robot.last_pose_sample_ns > 0
            and now <= robot.route_pose_valid_until
            and robot.has_fresh_battery(now, sim_ns)
        )

    def allows_transport(self, core, robot):
        if robot.robot_id in self.active or robot.robot_id in self.held:
            return False
        if robot.state != RobotState.STATE_IDLE or robot.battery_soc_percent < self.low_soc_percent:
            return False
        return not any(
            station.has_owner(robot.robot_id) and station.station_type == StationType.CHARGING
            and station.state != ReservationState.BLOCKED
            for station in core.reservations.list_stations()
        )

    def request_park_cancel(self, core, task, now):
        if any(move.cancel_for_task == task.task_id and not move.cancel_declined for move in self.active.values()):
            return True
        candidates = []
        for robot_id, move in self.active.items():
            robot = core.tracker.get_robot(robot_id)
            if (move.cancel_for_task is not None or move.cancel_declined or robot.session_blocked
                    or robot.is_loaded or robot.is_stale(now)
                    or robot.state != RobotState.STATE_RETURNING_TO_PARK
                    or robot.battery_soc_percent < self.low_soc_percent):
                continue
            evaluation = core.scheduler.evaluate_robot_for_task(robot, task, now)
            if evaluation is not None:
                candidates.append((evaluation.d_pickup, robot_id))
        if candidates and task.task_id not in core.scheduler.pending_route_tasks:
            self.active[min(candidates)[1]].cancel_for_task = task.task_id
            return True
        return False

    def needs_station(self, core, robot, now):
        if not self.can_move(core, robot, now):
            return False
        low = robot.battery_soc_percent < self.low_soc_percent
        owners = core.reservations.stations_owned_by(robot.robot_id)
        if any(s.state in (ReservationState.RESERVED, ReservationState.BLOCKED, ReservationState.RELEASING)
               for s in owners):
            return False
        if low:
            return all(s.station_type != StationType.CHARGING for s in owners)
        return not owners and robot.robot_id in self.park_due

    def schedule(self, core, now, lookup=None):
        for robot in core.tracker.list_robots():
            if not self.needs_station(core, robot, now):
                continue
            low = robot.battery_soc_percent < self.low_soc_percent
            # Give a ready transport task the first opportunity to take a parked robot.
            if not low and core.scheduler.pending_route_tasks:
                continue
            primary = StationType.CHARGING if low else StationType.PARKING
            # A robot already holding a safe berth can wait there for charge.
            station_types = (primary,) if core.reservations.stations_owned_by(robot.robot_id) else (
                primary, StationType.SAFE_WAITING,
            )
            for station_type in station_types:
                station, pending = self._select(core, robot, station_type, now, lookup)
                if station is not None or pending:
                    break
            if station is not None:
                self._assign(core, robot, station)
            elif not pending:
                self.wait_reasons[robot.robot_id] = (
                    "NO_REACHABLE_CHARGE_OR_WAITING_STATION" if low else "NO_REACHABLE_PARK_OR_WAITING_STATION"
                )

    def _select(self, core, robot, station_type, now, lookup):
        scheduler = core.scheduler
        choices = []
        pending = False
        for station in core.reservations.list_stations(station_type):
            if station.state != ReservationState.FREE:
                continue
            # A FREE record is not permission to drive into a robot known to be there.
            if any(other.robot_id != robot.robot_id and station.is_physically_occupied(other.pose)
                   for other in core.tracker.list_robots()):
                continue
            escapes = core.reservations.list_stations(StationType.CHARGING)
            escape_poses = ([None] if station_type == StationType.CHARGING else
                            [s.pose for s in escapes if s.state != ReservationState.BLOCKED])
            for escape in escape_poses:
                legs = [(robot.pose, station.pose)]
                if escape is not None:
                    legs.append((station.pose, escape))
                if lookup is None:
                    distances = [scheduler.route_provider.get_path_distance(robot.robot_id, *leg) for leg in legs]
                else:
                    distances, waiting = lookup(robot, station, legs)
                    pending |= waiting
                if distances is None or any(d is None or not isfinite(d) or d < 0 for d in distances):
                    continue
                distance = distances[0]
                result = check_energy_eligibility(
                    specs=robot.specs, battery_soc_percent=robot.battery_soc_percent,
                    d_total_m=distance, d_escape_m=distances[1] if escape is not None else 0.0,
                    emergency_soc_percent=scheduler.emergency_soc_percent,
                    safety_margin_wh=scheduler.safety_margin_wh,
                    battery_energy_wh=robot.battery_energy_wh,
                )
                if result.is_eligible:
                    choices.append((distance, station.station_id, station))
        if pending or not choices:
            return None, pending
        return min(choices, key=lambda choice: choice[:2])[2], False

    def _assign(self, core, robot, station):
        previous_stations = core.reservations.stations_owned_by(robot.robot_id)
        if not core.reservations.reserve(station.station_id, robot.robot_id):
            return
        for previous in previous_stations:
            core.reservations.initiate_release(previous.station_id, robot.robot_id)
        robot.current_epoch += 1
        goal_uuid = str(uuid4())
        move = StationMove(
            f"station:{goal_uuid}", robot.robot_id, station.station_id, station.station_type,
            station.pose, station.tolerance_radius, robot.session_id, robot.current_epoch, goal_uuid,
        )
        self.active[robot.robot_id] = move
        self.wait_reasons.pop(robot.robot_id, None)

    def result(self, core, move, status, proof_ns, error_reason):
        station = core.reservations.get_station(move.station_id)
        if not station.has_owner(move.assigned_robot_id):
            return False
        if status == TaskResultStatus.STATUS_SUCCEEDED:
            if not core.reservations.mark_occupied(move.station_id, move.assigned_robot_id):
                return False
            station.departure_after_ns = proof_ns
            self.park_due.discard(move.assigned_robot_id)
            move.status = "ARRIVED"
        elif status == TaskResultStatus.STATUS_PREEMPTED and move.cancel_for_task is not None:
            if not core.reservations.initiate_release(move.station_id, move.assigned_robot_id):
                return False
            station.departure_after_ns = proof_ns
            move.status = "CANCELED"
        elif status == TaskResultStatus.STATUS_FAILED:
            # Reserve the uncertain destination until operator recovery.
            core.reservations.mark_blocked(move.station_id, move.assigned_robot_id, session_id=move.session_id)
            self.held.add(move.assigned_robot_id)
            move.status = "FAILED"
            move.error_reason = error_reason
        else:
            return False
        self._finish(move)
        return True

    def reject(self, move):
        # A goal reject requires review and retains the reservation.
        self.held.add(move.assigned_robot_id)
        move.status = "HELD_FOR_REVIEW"
        move.error_reason = "Station goal rejected"
        self._finish(move)

    def _finish(self, move):
        del self.active[move.assigned_robot_id]
        self.history[move.task_id] = move
