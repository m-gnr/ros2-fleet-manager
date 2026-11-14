"""ROS 2 Robot Executor Node.

Provides the logistics adapter layer between Fleet Manager and Nav2:
- ActionServer for fleet_interfaces/action/ExecuteTask
- ActionClient for nav2_msgs/action/NavigateToPose
- 5 Hz periodic publisher for fleet_interfaces/msg/RobotStatus
- ServiceServer for fleet_interfaces/srv/ClearRobotError
- Odometry and battery telemetry subscriber
- Active zero-velocity braking and stop verification for safe preemption
"""

import copy
import json
import math
import signal
import threading
import time
from typing import Optional, Tuple
import uuid

import rclpy
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.clock import Clock, ClockType, JumpThreshold
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.serialization import serialize_message
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time

from action_msgs.msg import GoalStatus
from builtin_interfaces.msg import Time as RosTime
from geometry_msgs.msg import PoseStamped as RosPoseStamped, Twist
from nav_msgs.msg import Odometry

from fleet_interfaces.action import ExecuteTask, NavigateToStation
from fleet_interfaces.msg import BatteryControlApplied, BatteryState, RobotStatus
from fleet_interfaces.srv import ClearRobotError
from nav2_msgs.action import NavigateToPose
from tf2_ros import Buffer, TransformException, TransformListener

from .battery import BatteryTelemetry
from .config_loader import load_robot_fleet_config
from .constants import (
    DEFAULT_ANGULAR_STOP_THRESHOLD_RAD_S,
    DEFAULT_CANCEL_STOP_TIMEOUT_SEC,
    DEFAULT_LINEAR_STOP_THRESHOLD_M_S,
    DEFAULT_LOADING_DURATION_SEC,
    DEFAULT_ODOMETRY_FRESHNESS_SEC,
    DEFAULT_UNLOADING_DURATION_SEC,
    ErrorReason,
    RobotState,
    TaskPhase,
    TaskPriority,
    TaskResultStatus,
)
from .models import (
    ExecutorConfig,
    OdometryReading,
    PoseStamped,
    TaskGoal,
)
from .state_machine import RobotExecutorStateMachine
from .safety import ExecutorSafety
from .stop_detector import StopDetector


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """Extract yaw heading angle (radians) from quaternion coordinates."""
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def yaw_to_quaternion(yaw: float) -> Tuple[float, float, float, float]:
    """Convert yaw heading angle (radians) to quaternion (x, y, z, w)."""
    half = yaw * 0.5
    return (0.0, 0.0, math.sin(half), math.cos(half))


class RobotExecutorNode(Node):
    """ROS 2 node wrapping the pure Python RobotExecutorStateMachine."""

    def __init__(self, node_name: str = "robot_executor", *, parameter_overrides=None,
                 _test_reset_verified: bool = False, _legacy_test_battery: bool = False) -> None:
        super().__init__(node_name, parameter_overrides=parameter_overrides)
        self.declare_parameter("duplicate_record_capacity", Parameter.Type.INTEGER)
        self.safety = ExecutorSafety(self.get_parameter("duplicate_record_capacity").value)
        if _test_reset_verified:
            # In-process test seam only; no ROS parameter/service can open admission.
            self.safety.blocked = False
            self.safety.reason = ""
        self._admission_pending = False
        self._stopping = threading.Event()

        # ---------------------------------------------------------------------
        # Parameters Declaration
        # ---------------------------------------------------------------------
        self.declare_parameter("fleet_config_path", "config/fleet.yaml")
        self.declare_parameter("robot_id", "")
        self.declare_parameter("robot_namespace", "")
        self.declare_parameter("nav2_action_name", "")
        self.declare_parameter("status_rate_hz", 5.0)
        self.declare_parameter("loading_duration_sec", DEFAULT_LOADING_DURATION_SEC)
        self.declare_parameter("unloading_duration_sec", DEFAULT_UNLOADING_DURATION_SEC)
        self.declare_parameter("linear_stop_threshold_m_s", DEFAULT_LINEAR_STOP_THRESHOLD_M_S)
        self.declare_parameter("angular_stop_threshold_rad_s", DEFAULT_ANGULAR_STOP_THRESHOLD_RAD_S)
        self.declare_parameter("odometry_freshness_sec", DEFAULT_ODOMETRY_FRESHNESS_SEC)
        self.declare_parameter("cancel_stop_timeout_sec", DEFAULT_CANCEL_STOP_TIMEOUT_SEC)
        self.declare_parameter("nav2_cancel_result_timeout_sec", 3.0)
        self._nav2_cancel_result_timeout_sec = self.get_parameter("nav2_cancel_result_timeout_sec").value
        if not math.isfinite(self._nav2_cancel_result_timeout_sec) or self._nav2_cancel_result_timeout_sec <= 0:
            raise ValueError("nav2_cancel_result_timeout_sec must be finite and positive")
        self.declare_parameter("cmd_vel_topic_name", "cmd_vel")
        self.declare_parameter("odom_topic_name", "odom")
        self.declare_parameter("status_topic_name", "robot_status")
        self.declare_parameter("battery_state_topic_name", "battery_state")

        fleet_config_path = self.get_parameter("fleet_config_path").value
        param_robot_id = self.get_parameter("robot_id").value

        # ---------------------------------------------------------------------
        # Configuration Loading
        # ---------------------------------------------------------------------
        robot_cfg = None
        try:
            robot_cfg = load_robot_fleet_config(fleet_config_path, param_robot_id or None)
            self.get_logger().info(
                f"Successfully loaded configuration from {fleet_config_path} for robot '{robot_cfg.robot_id}'"
            )
        except Exception as e:
            if not _legacy_test_battery:
                raise
            self.get_logger().warn(
                f"Could not load fleet configuration ({e}). Falling back to ROS parameters."
            )

        if robot_cfg:
            self.robot_id = param_robot_id or robot_cfg.robot_id
            self.robot_namespace = self.get_parameter("robot_namespace").value or robot_cfg.namespace
            self.nav2_action_name = self.get_parameter("nav2_action_name").value or robot_cfg.nav2_action_name
            self.initial_pose = getattr(robot_cfg, "initial_pose", (0.0, 0.0, 0.0))
        else:
            self.robot_id = param_robot_id or "robot_1"
            self.robot_namespace = self.get_parameter("robot_namespace").value or f"/{self.robot_id}"
            self.nav2_action_name = self.get_parameter("nav2_action_name").value or f"{self.robot_namespace}/navigate_to_pose"
            self.initial_pose = (0.0, 0.0, 0.0)

        # ---------------------------------------------------------------------
        # State Machine Initialization
        # ---------------------------------------------------------------------
        self.executor_config = ExecutorConfig(
            linear_stop_threshold_m_s=float(self.get_parameter("linear_stop_threshold_m_s").value),
            angular_stop_threshold_rad_s=float(self.get_parameter("angular_stop_threshold_rad_s").value),
            odometry_freshness_sec=float(self.get_parameter("odometry_freshness_sec").value),
            cancel_stop_timeout_sec=float(self.get_parameter("cancel_stop_timeout_sec").value),
            loading_duration_sec=float(self.get_parameter("loading_duration_sec").value),
            unloading_duration_sec=float(self.get_parameter("unloading_duration_sec").value),
        )

        self.state_machine = RobotExecutorStateMachine(
            robot_id=self.robot_id,
            config=self.executor_config,
        )
        if self.initial_pose != (0.0, 0.0, 0.0):
            init_x, init_y, init_yaw = self.initial_pose
            self.state_machine.current_pose = PoseStamped(
                x=init_x,
                y=init_y,
                z=0.0,
                yaw=init_yaw,
                frame_id="map",
            )
        self._lock = threading.Lock()
        self._battery = None
        self._map_tf = None
        self._physical_pose = None
        self._battery_endpoint_gid = None
        self._battery_control_endpoint_gid = None
        self._battery_control_proof = None
        self._battery_clock_changed = threading.Event()
        if not _legacy_test_battery:
            if (not robot_cfg.use_sim_time or not self.get_parameter("use_sim_time").value
                    or robot_cfg.usable_capacity_wh is None):
                raise ValueError("C4 battery telemetry requires validated fleet config and use_sim_time=true")
            self._battery_topic = f"{robot_cfg.namespace}/battery_state"
            if (self.robot_namespace != robot_cfg.namespace
                    or self.get_namespace() not in ("/", robot_cfg.namespace)
                    or self.resolve_topic_name(self._battery_topic) != self._battery_topic):
                raise ValueError("C4 BatteryState must stay in the configured robot namespace")
            self._battery = BatteryTelemetry(self.robot_id, robot_cfg.usable_capacity_wh)
            self._map_tf = Buffer()
            self._tf_listener = TransformListener(self._map_tf, self)
            self.state_machine.update_battery(0.0, 0.0)
            self._battery_clock_guard = self.get_clock().create_jump_callback(
                JumpThreshold(min_forward=None, min_backward=Duration(nanoseconds=-1), on_clock_change=True),
                pre_callback=self._battery_clock_changed.set,
            )

        # ---------------------------------------------------------------------
        # ROS 2 Interfaces (Callback Groups & Endpoints)
        # ---------------------------------------------------------------------
        self.cb_group = ReentrantCallbackGroup()

        # ExecuteTask Action Server
        action_server_name = self._qualify("execute_task")
        self._action_server = ActionServer(
            self,
            ExecuteTask,
            action_server_name,
            execute_callback=self._execute_task_callback,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
            callback_group=self.cb_group,
        )
        self.get_logger().info(f"ExecuteTask ActionServer listening on '{action_server_name}'")
        if self._battery is not None:
            self._station_server = ActionServer(
                self, NavigateToStation, self._qualify("navigate_to_station"),
                execute_callback=self._execute_station_move,
                goal_callback=self._station_goal_callback,
                cancel_callback=self._station_cancel_callback,
                callback_group=self.cb_group,
            )
            self._physical_pose_sub = self.create_subscription(
                RosPoseStamped, self._qualify("physical_pose"), self._physical_pose_callback, 10,
            )

        # Nav2 NavigateToPose Action Client
        self._nav2_client = ActionClient(
            self,
            NavigateToPose,
            self.nav2_action_name,
            callback_group=self.cb_group,
        )
        self.get_logger().info(f"Nav2 NavigateToPose ActionClient targeting '{self.nav2_action_name}'")

        # RobotStatus 5 Hz Publisher
        status_topic = self._qualify(str(self.get_parameter("status_topic_name").value))
        self._status_pub = self.create_publisher(RobotStatus, status_topic, 10)
        status_rate_hz = float(self.get_parameter("status_rate_hz").value)
        self._status_timer = self.create_timer(
            1.0 / status_rate_hz,
            self._status_timer_callback,
            callback_group=self.cb_group,
            clock=Clock(clock_type=ClockType.STEADY_TIME) if self._battery is not None else None,
        )
        self.get_logger().info(f"Publishing RobotStatus at {status_rate_hz} Hz on '{status_topic}'")

        # ClearRobotError Service Server
        clear_error_service = self._qualify("clear_robot_error")
        self._clear_error_srv = self.create_service(
            ClearRobotError,
            clear_error_service,
            self._clear_error_callback,
            callback_group=self.cb_group,
        )
        self.get_logger().info(f"ClearRobotError service available on '{clear_error_service}'")

        # Odometry Subscriber
        odom_topic = self._qualify(str(self.get_parameter("odom_topic_name").value))
        self._odom_group = MutuallyExclusiveCallbackGroup()
        self._odom_sub = self.create_subscription(
            Odometry,
            odom_topic,
            self._odom_callback,
            10,
            callback_group=self._odom_group,
        )
        self.get_logger().info(f"Subscribed to Odometry on '{odom_topic}'")

        # Active Braking cmd_vel Publisher
        cmd_vel_topic = self._qualify(str(self.get_parameter("cmd_vel_topic_name").value))
        self._cmd_vel_pub = self.create_publisher(Twist, cmd_vel_topic, 10)

        if self._battery is not None:
            self._battery_sub = self.create_subscription(
                BatteryState, self._battery_topic, self._battery_callback, 10,
                callback_group=self.cb_group,
            )
            self._battery_control_topic = f"{robot_cfg.namespace}/battery_control_applied"
            self._battery_control_sub = self.create_subscription(
                BatteryControlApplied, self._battery_control_topic, self._battery_control_callback, 10,
                callback_group=self.cb_group,
            )
        else:
            battery_topic = self._qualify(str(self.get_parameter("battery_state_topic_name").value))
            self._battery_sub = self.create_subscription(
                RobotStatus, battery_topic, self._legacy_battery_callback, 10,
                callback_group=self.cb_group,
            )

        self._active_nav2_goal_handle = None

    def _qualify(self, name: str) -> str:
        """Qualify topic or service name with robot namespace if not running under one."""
        node_ns = self.get_namespace()
        if node_ns in ("/", "") and self.robot_namespace:
            ns = self.robot_namespace.rstrip("/")
            rel = name.lstrip("/")
            return f"{ns}/{rel}"
        return name

    @staticmethod
    def _uuid_to_str(goal_id_uuid) -> str:
        """Convert ROS 2 16-byte UUID array to standard string UUID."""
        try:
            return str(uuid.UUID(bytes=bytes(goal_id_uuid)))
        except Exception:
            return str(goal_id_uuid)

    @staticmethod
    def _ros_pose_to_model(ros_pose: RosPoseStamped) -> PoseStamped:
        """Convert geometry_msgs/PoseStamped to internal dataclass PoseStamped."""
        stamp_sec = ros_pose.header.stamp.sec + ros_pose.header.stamp.nanosec * 1e-9
        yaw = quaternion_to_yaw(
            ros_pose.pose.orientation.x,
            ros_pose.pose.orientation.y,
            ros_pose.pose.orientation.z,
            ros_pose.pose.orientation.w,
        )
        return PoseStamped(
            x=ros_pose.pose.position.x,
            y=ros_pose.pose.position.y,
            z=ros_pose.pose.position.z,
            yaw=yaw,
            frame_id=ros_pose.header.frame_id or "map",
            timestamp_sec=stamp_sec,
        )

    # =========================================================================
    # Action Server Callbacks (Goal, Cancel, Execute)
    # =========================================================================

    def _goal_callback(self, goal_request: ExecuteTask.Goal) -> GoalResponse:
        """Pre-execution validation of incoming ExecuteTask Goal."""
        pickup = self._ros_pose_to_model(goal_request.pickup_pose)
        dropoff = self._ros_pose_to_model(goal_request.dropoff_pose)

        candidate_goal = TaskGoal(
            task_id=goal_request.task_id,
            assignment_epoch=goal_request.assignment_epoch,
            pickup_pose=pickup,
            dropoff_pose=dropoff,
            priority=goal_request.priority,
            goal_uuid="pre-validation",
        )

        with self._lock:
            can_accept, reason = self.state_machine.can_accept_goal(candidate_goal)
            can_accept = (can_accept and not self._admission_pending
                          and self.safety.available(goal_request.task_id, goal_request.assignment_epoch))
            if (can_accept and self._battery is not None
                    and not self._fresh_battery_stamp(self.get_clock().now().nanoseconds)):
                can_accept, reason = False, "Fresh BatteryState required"
            if can_accept:
                self._admission_pending = True

        if not can_accept:
            self.get_logger().warn(
                f"Rejecting goal for task '{goal_request.task_id}' (epoch {goal_request.assignment_epoch}): {reason}"
            )
            return GoalResponse.REJECT

        self.get_logger().info(
            f"Accepting goal for task '{goal_request.task_id}' (epoch {goal_request.assignment_epoch}, priority {goal_request.priority})"
        )
        return GoalResponse.ACCEPT

    def _cancel_callback(self, goal_handle: ServerGoalHandle) -> CancelResponse:
        """Evaluate preemption eligibility upon cancellation request."""
        goal_uuid = self._uuid_to_str(goal_handle.goal_id.uuid)

        with self._lock:
            can_cancel, reason = self.state_machine.request_cancel(
                goal_uuid, self.get_clock().now().nanoseconds / 1e9)

        if not can_cancel:
            self.get_logger().warn(
                f"Rejecting cancel request for goal {goal_uuid}: {reason}"
            )
            return CancelResponse.REJECT

        self.get_logger().info(f"Accepted cancel request for goal {goal_uuid}. Initiating safe preemption.")
        return CancelResponse.ACCEPT

    def _hold_uncertain(self, reason, *, brake_until=None):
        with self._lock:
            self.safety.block(reason)
        self.get_logger().error(reason)
        # No unapproved timeout -> FAILED/ERROR transition. Ownership stays held.
        interval = 0.02 if brake_until is not None else 0.05
        while self.context.ok() and not self._stopping.wait(interval):
            if brake_until is not None and not brake_until.done():
                self._cmd_vel_pub.publish(Twist())
        raise RuntimeError("Executor stopped with unresolved ownership")

    def _station_goal_callback(self, request):
        target = self._ros_pose_to_model(request.target_pose)
        if (request.robot_id != self.robot_id or not request.move_id or not request.station_id
                or bytes(request.expected_session_id.uuid) != self.safety.session_id.bytes
                or target.frame_id != "map"
                or not all(math.isfinite(v) for v in (target.x, target.y, target.z, target.yaw,
                                                      request.tolerance_radius))
                or request.tolerance_radius <= 0):
            return GoalResponse.REJECT
        with self._lock:
            machine = self.state_machine
            now = self.get_clock().now()
            can_leave_dock = (not request.charging_station and machine.state == RobotState.STATE_CHARGING
                              and bool(machine.dock_station_id))
            if (self._admission_pending or machine.is_loaded
                    or (machine.state != RobotState.STATE_IDLE and not can_leave_dock)
                    or machine.active_goal_uuid is not None or request.assignment_epoch <= machine.current_epoch
                    or not self.safety.available(request.move_id, request.assignment_epoch)
                    or not self._fresh_battery_stamp(now.nanoseconds)
                    or self._stationary_odom(now.nanoseconds / 1e9) is None):
                return GoalResponse.REJECT
            self._admission_pending = True
        return GoalResponse.ACCEPT

    def _station_cancel_callback(self, handle):
        request = handle.request
        goal_uuid = self._uuid_to_str(handle.goal_id.uuid)
        with self._lock:
            if (request.charging_station or self.state_machine.active_goal_uuid != goal_uuid
                    or self.state_machine.state != RobotState.STATE_RETURNING_TO_PARK
                    or self.safety.blocked):
                return CancelResponse.REJECT
            self.state_machine.is_cancelling = True
        return CancelResponse.ACCEPT

    def _execute_station_move(self, handle):
        request = handle.request
        goal_uuid = self._uuid_to_str(handle.goal_id.uuid)
        identity = (request.move_id, request.assignment_epoch, goal_uuid)
        payload = serialize_message(request)
        try:
            with self._lock:
                admitted = self.safety.admit(identity, payload) and self.state_machine.begin_station_move(
                    *identity, charging=request.charging_station,
                )
            if not admitted:
                raise RuntimeError("Accepted station goal conflicts with assignment evidence")
            status, proof, reason = self._navigate_to_station(handle)
            result = NavigateToStation.Result()
            result.status = int(status)
            result.move_id = request.move_id
            result.station_id = request.station_id
            result.error_reason = reason
            result.stationary_stamp.sec, result.stationary_stamp.nanosec = divmod(proof, 10**9)
            with self._lock:
                result.completed_epoch = self.state_machine.current_epoch
                valid = self.safety.finish(identity, payload, result) and self.state_machine.finish_station_move(
                    goal_uuid, reason, self.get_clock().now().nanoseconds / 1e9,
                )
                if valid:
                    if status == TaskResultStatus.STATUS_SUCCEEDED and request.charging_station:
                        self.state_machine.dock_station_id = request.station_id
                    self._admission_pending = False
            if not valid:
                raise RuntimeError("Station terminal result does not match assignment")
            if status == TaskResultStatus.STATUS_SUCCEEDED:
                handle.succeed()
            elif status == TaskResultStatus.STATUS_PREEMPTED:
                handle.canceled()
            else:
                handle.abort()
            return result
        except Exception as exc:
            return self._hold_uncertain(f"Station movement evidence unavailable: {exc}")

    def _navigate_to_station(self, handle):
        while not self._nav2_client.wait_for_server(timeout_sec=0.1):
            if self._stopping.is_set():
                raise RuntimeError("Stopped while awaiting station navigation server")
        request = handle.request
        nav_goal = NavigateToPose.Goal()
        nav_goal.pose = copy.deepcopy(request.target_pose)
        nav_goal.pose.header.stamp = self.get_clock().now().to_msg()
        future = self._nav2_client.send_goal_async(nav_goal)
        while not future.done():
            if self._stopping.wait(0.02):
                raise RuntimeError("Stopped with unresolved station navigation delivery")
        nav_handle = future.result()
        if nav_handle is None:
            raise RuntimeError("Station navigation acceptance is unknown")
        if not nav_handle.accepted:
            return TaskResultStatus.STATUS_FAILED, 0, "Station Nav2 goal rejected"
        self._active_nav2_goal_handle = nav_handle
        result = nav_handle.get_result_async()
        while not result.done():
            with self._lock:
                cancel_requested = self.state_machine.is_cancelling
            if cancel_requested:
                self._await_nav2_cancel_terminal(nav_handle, result)
                break
            if self._stopping.wait(0.02):
                raise RuntimeError("Stopped with active station navigation")
        self._active_nav2_goal_handle = None
        terminal = result.result().status
        if terminal == GoalStatus.STATUS_ABORTED:
            return TaskResultStatus.STATUS_FAILED, 0, "Station Nav2 goal aborted"
        with self._lock:
            canceled = terminal == GoalStatus.STATUS_CANCELED and self.state_machine.is_cancelling
        if terminal != GoalStatus.STATUS_SUCCEEDED and not canceled:
            raise RuntimeError("Unexpected station Nav2 terminal state")
        after = self.get_clock().now().nanoseconds / 1e9
        if canceled:
            with self._lock:
                self.state_machine.begin_cancel_stop_confirmation(after)
        deadline = after + self.executor_config.cancel_stop_timeout_sec
        while not self._stopping.is_set():
            now = self.get_clock().now().nanoseconds / 1e9
            with self._lock:
                proof = (self.state_machine.cancel_stop.confirmed(now) if canceled
                         else self._stationary_odom(now, after=after))
            if proof is not None:
                stamp = round(proof.timestamp_sec * 10**9)
                if canceled:
                    return TaskResultStatus.STATUS_PREEMPTED, stamp, ""
                target = request.target_pose.pose.position
                if math.hypot(proof.pose.x - target.x, proof.pose.y - target.y) > request.tolerance_radius:
                    return TaskResultStatus.STATUS_FAILED, 0, "Station stop outside configured radius"
                return TaskResultStatus.STATUS_SUCCEEDED, stamp, ""
            if now > deadline or now < after:
                break
            self._cmd_vel_pub.publish(Twist())
            self._stopping.wait(0.02)
        raise RuntimeError("Station movement lacks fresh stopped odometry")

    def _stationary_odom(self, now, *, after=0.0):
        reading = self.state_machine.last_odometry
        if (reading is None or reading.timestamp_sec <= after or reading.pose is None
                or reading.pose.frame_id != "map"
                or not all(math.isfinite(v) for v in (reading.pose.x, reading.pose.y, reading.pose.yaw))):
            return None
        config = self.executor_config
        stopped, _ = StopDetector.verify_stopped(
            reading, now, config.linear_stop_threshold_m_s, config.angular_stop_threshold_rad_s,
            config.odometry_freshness_sec,
        )
        return reading if stopped else None

    def _execute_task_callback(self, goal_handle: ServerGoalHandle) -> ExecuteTask.Result:
        req = goal_handle.request
        identity = (req.task_id, req.assignment_epoch, self._uuid_to_str(goal_handle.goal_id.uuid))
        payload = serialize_message(req)
        with self._lock:
            admitted = self.safety.admit(identity, payload)
        if not admitted:
            return self._hold_uncertain("Accepted goal conflicts with assignment evidence")
        try:
            result = self._execute_task_body(goal_handle)
            with self._lock:
                valid = self.safety.finish(identity, payload, result)
                if valid:
                    self._admission_pending = False
            if not valid:
                return self._hold_uncertain("Terminal result does not match assignment")
            if result.status == TaskResultStatus.STATUS_SUCCEEDED:
                goal_handle.succeed()
            elif result.status == TaskResultStatus.STATUS_PREEMPTED:
                goal_handle.canceled()
            else:
                goal_handle.abort()
            return result
        except Exception as exc:
            return self._hold_uncertain(f"Execution evidence unavailable: {exc}")

    def _execute_task_body(self, goal_handle: ServerGoalHandle) -> ExecuteTask.Result:
        """Execute full logistics lifecycle: Pickup -> Load -> Dropoff -> Unload."""
        goal_uuid = self._uuid_to_str(goal_handle.goal_id.uuid)
        req = goal_handle.request
        pickup_model = self._ros_pose_to_model(req.pickup_pose)
        dropoff_model = self._ros_pose_to_model(req.dropoff_pose)

        task_goal = TaskGoal(
            task_id=req.task_id,
            assignment_epoch=req.assignment_epoch,
            pickup_pose=pickup_model,
            dropoff_pose=dropoff_model,
            priority=req.priority,
            goal_uuid=goal_uuid,
        )

        with self._lock:
            if not self.state_machine.accept_goal(task_goal):
                self.get_logger().error(f"Failed to transition state machine into ACCEPTED for {goal_uuid}")
                self.safety.block("State machine rejected an accepted assignment")
                raise RuntimeError("State machine admission mismatch")

        self.get_logger().info(
            f"Task {req.task_id} execution started (phase=MOVING_TO_PICKUP, UUID={goal_uuid})"
        )

        # ---------------------------------------------------------------------
        # Phase 1: Moving to Pickup
        # ---------------------------------------------------------------------
        pickup_ok, terminal_res = self._navigate_with_cancel_support(
            goal_handle=goal_handle,
            target_pose=req.pickup_pose,
            target_model=pickup_model,
            phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
        )
        if not pickup_ok:
            return terminal_res

        # ---------------------------------------------------------------------
        # Phase 2: Cargo Loading (Non-cancelable critical section)
        # ---------------------------------------------------------------------
        with self._lock:
            if not self.state_machine.start_loading(goal_uuid):
                raise RuntimeError("Pickup transition mismatch")
        self.get_logger().info(
            f"Robot {self.robot_id} arrived at pickup. Loading cargo ({self.executor_config.loading_duration_sec}s)..."
        )

        load_start = time.time()
        stop_cmd = Twist()
        while time.time() - load_start < self.executor_config.loading_duration_sec:
            try:
                self._cmd_vel_pub.publish(stop_cmd)
            except Exception:
                pass
            self._publish_feedback(goal_handle, TaskPhase.PHASE_LOADING, 0.0)
            time.sleep(0.05)

        with self._lock:
            self.state_machine.finish_loading(goal_uuid)
        self.get_logger().info(
            f"Robot {self.robot_id} cargo loaded (is_loaded=True). Moving to dropoff..."
        )

        # ---------------------------------------------------------------------
        # Phase 3: Moving to Dropoff
        # ---------------------------------------------------------------------
        dropoff_ok, terminal_res = self._navigate_with_cancel_support(
            goal_handle=goal_handle,
            target_pose=req.dropoff_pose,
            target_model=dropoff_model,
            phase=TaskPhase.PHASE_MOVING_TO_DROPOFF,
        )
        if not dropoff_ok:
            return terminal_res

        # ---------------------------------------------------------------------
        # Phase 4: Cargo Unloading
        # ---------------------------------------------------------------------
        with self._lock:
            self.state_machine.start_unloading(goal_uuid)
        self.get_logger().info(
            f"Robot {self.robot_id} arrived at dropoff. Unloading cargo ({self.executor_config.unloading_duration_sec}s)..."
        )

        unload_start = time.time()
        while time.time() - unload_start < self.executor_config.unloading_duration_sec:
            try:
                self._cmd_vel_pub.publish(stop_cmd)
            except Exception:
                pass
            self._publish_feedback(goal_handle, TaskPhase.PHASE_UNLOADING, 0.0)
            time.sleep(0.05)

        now_sim = self.get_clock().now().nanoseconds / 1e9
        with self._lock:
            task_res = self.state_machine.finish_unloading(goal_uuid, now_sim)

        self.get_logger().info(
            f"Task {req.task_id} SUCCEEDED. Robot {self.robot_id} returned to IDLE (is_loaded=False)."
        )

        result = ExecuteTask.Result()
        result.status = TaskResultStatus.STATUS_SUCCEEDED
        result.completed_epoch = task_res.completed_epoch
        result.completion_stamp = self.get_clock().now().to_msg()
        result.error_reason = ""
        return result

    # =========================================================================
    # Navigation & Preemption Subroutines
    # =========================================================================

    def _navigate_with_cancel_support(
        self,
        goal_handle: ServerGoalHandle,
        target_pose: RosPoseStamped,
        target_model: PoseStamped,
        phase: TaskPhase,
    ) -> Tuple[bool, Optional[ExecuteTask.Result]]:
        """Run Nav2 navigation, publish feedback, and handle preemption requests."""
        goal_uuid = self._uuid_to_str(goal_handle.goal_id.uuid)

        self.get_logger().info(f"Awaiting Nav2 server on '{self.nav2_action_name}'...")
        while not self._nav2_client.wait_for_server(timeout_sec=0.1):
            if self._stopping.is_set():
                raise RuntimeError("Stopped while awaiting Nav2")
        self.get_logger().info(f"Nav2 server '{self.nav2_action_name}' is ready. Sending goal...")
        nav2_goal = NavigateToPose.Goal()
        nav2_goal.pose = copy.deepcopy(target_pose)

        nav2_goal_handle = None
        for attempt in range(5):
            nav2_goal.pose.header.stamp = self.get_clock().now().to_msg()
            send_future = self._nav2_client.send_goal_async(nav2_goal)
            while not send_future.done():
                if self._stopping.wait(0.02):
                    raise RuntimeError("Stopped with unresolved Nav2 delivery")
            nav2_goal_handle = send_future.result()
            if nav2_goal_handle is not None and nav2_goal_handle.accepted:
                break
            if attempt < 4:
                self.get_logger().warn(
                    f"Nav2 goal rejected (attempt {attempt + 1}/5) on '{self.nav2_action_name}', retrying in 0.5s..."
                )
                if self._stopping.wait(0.5):
                    raise RuntimeError("Stopped while awaiting Nav2 retry")

        if nav2_goal_handle is None:
            return self._hold_uncertain("Nav2 goal acceptance unknown")
        if not nav2_goal_handle.accepted:
            self.get_logger().warn(f"Nav2 goal rejected after retries by '{self.nav2_action_name}' for goal {goal_uuid}")
            return False, self._navigation_failed(goal_uuid)

        self.get_logger().info(f"Nav2 goal accepted by '{self.nav2_action_name}' for goal {goal_uuid}. Awaiting completion...")
        self._active_nav2_goal_handle = nav2_goal_handle
        result_future = nav2_goal_handle.get_result_async()
        while not result_future.done():
            with self._lock:
                cancelling = self.state_machine.is_cancelling
            if cancelling:
                terminal = self._execute_safe_cancel(goal_uuid, nav2_goal_handle, result_future)
                self._active_nav2_goal_handle = None
                return (True, None) if terminal is None else (False, terminal)
            self._publish_feedback(goal_handle, phase, self._calculate_distance_to(target_model))
            if self._stopping.wait(0.05):
                raise RuntimeError("Stopped with active Nav2 goal")

        self._active_nav2_goal_handle = None
        nav2_res = result_future.result()
        self.get_logger().info(f"Nav2 navigation completed with status {nav2_res.status} for goal {goal_uuid}")
        with self._lock:
            cancelling = self.state_machine.is_cancelling
        if cancelling:
            terminal = self._execute_safe_cancel(goal_uuid, nav2_goal_handle, result_future)
            return (True, None) if terminal is None else (False, terminal)
        if nav2_res.status == GoalStatus.STATUS_SUCCEEDED:
            return True, None
        if nav2_res.status == GoalStatus.STATUS_ABORTED:
            return False, self._navigation_failed(goal_uuid)
        return self._hold_uncertain("Unexpected Nav2 terminal status")

    def _navigation_failed(self, goal_uuid):
        with self._lock:
            terminal = self.state_machine.report_task_error(
                goal_uuid, ErrorReason.NAV2_ABORTED, self.get_clock().now().nanoseconds / 1e9)
        if terminal is None:
            return self._hold_uncertain("Nav2 failure identity mismatch")
        return self._terminal_message(terminal)

    def _terminal_message(self, terminal):
        result = ExecuteTask.Result()
        result.status = int(terminal.status)
        result.completed_epoch = terminal.completed_epoch
        result.completion_stamp = self.get_clock().now().to_msg()
        result.error_reason = terminal.error_reason
        return result

    def _execute_safe_cancel(self, goal_uuid, nav2_goal_handle, result_future):
        terminal = self._await_nav2_cancel_terminal(nav2_goal_handle, result_future)
        if terminal.status == GoalStatus.STATUS_SUCCEEDED:
            with self._lock:
                self.state_machine.is_cancelling = False
                self.state_machine.cancel_requested_at = None
                self.state_machine.cancel_stop = None
            # The pickup step succeeded naturally; continue its logistics phases.
            return None
        if terminal.status == GoalStatus.STATUS_ABORTED:
            return self._navigation_failed(goal_uuid)
        if terminal.status != GoalStatus.STATUS_CANCELED:
            return self._hold_uncertain("Ambiguous terminal cancel outcome")
        now = self.get_clock().now().nanoseconds / 1e9
        terminal_monotonic_ns = time.monotonic_ns()
        with self._lock:
            task_result = self.state_machine.notify_nav2_cancel_result(goal_uuid, True, now)
            proof = self.state_machine.last_odometry
            decision_monotonic_ns = time.monotonic_ns()
        while task_result is None:
            self._cmd_vel_pub.publish(Twist())
            if self._stopping.wait(0.05):
                raise RuntimeError("Stopped without fresh stationary odometry")
            with self._lock:
                task_result = self.state_machine.check_cancel_timeout(
                    self.get_clock().now().nanoseconds / 1e9)
                proof = self.state_machine.last_odometry
                decision_monotonic_ns = time.monotonic_ns()
        self.get_logger().info("PREEMPTION_STOP_PROOF " + json.dumps({
            "robot_id": self.robot_id,
            "goal_uuid": goal_uuid,
            "nav2_goal_uuid": self._uuid_to_str(nav2_goal_handle.goal_id.uuid),
            "epoch": task_result.completed_epoch,
            "nav2_terminal_ns": round(now * 10**9),
            "nav2_terminal_monotonic_ns": terminal_monotonic_ns,
            "decision_ns": round(task_result.completion_stamp_sec * 10**9),
            "decision_monotonic_ns": decision_monotonic_ns,
            "stop_window_start_ns": round(task_result.stop_window_start_sec * 10**9),
            "odometry_ns": round(proof.timestamp_sec * 10**9),
            "odometry_received_monotonic_ns": proof.received_monotonic_ns,
            "frame_id": proof.source_frame_id,
            "linear_m_s": proof.linear_velocity,
            "angular_rad_s": proof.angular_velocity,
        }))
        return self._terminal_message(task_result)

    def _await_nav2_cancel_terminal(self, nav2_goal_handle, result_future):
        # The result future belongs to this exact Nav2 goal handle. The cancel
        # service response, including ERROR_NONE, cannot establish termination.
        if not result_future.done():
            deadline = time.monotonic() + self._nav2_cancel_result_timeout_sec
            nav2_goal_handle.cancel_goal_async()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return self._hold_uncertain("Timed out awaiting terminal Nav2 cancellation",
                                                brake_until=result_future)
                if result_future.done():
                    break
                self._cmd_vel_pub.publish(Twist())
                if self._stopping.wait(min(0.02, remaining)):
                    raise RuntimeError("Stopped while awaiting terminal Nav2 cancellation")
        return result_future.result()

    # =========================================================================
    # Telemetry, Odometry & Periodic Callbacks
    # =========================================================================

    def _calculate_distance_to(self, target: PoseStamped) -> float:
        with self._lock:
            curr = self.state_machine.current_pose
        return float(math.hypot(curr.x - target.x, curr.y - target.y))

    def _publish_feedback(
        self,
        goal_handle: ServerGoalHandle,
        phase: TaskPhase,
        distance_to_goal: float,
    ) -> None:
        try:
            if not goal_handle.is_active:
                return
        except Exception:
            return

        fb = ExecuteTask.Feedback()
        fb.current_phase = int(phase)
        fb.distance_to_goal = float(distance_to_goal)

        with self._lock:
            snapshot_pose = self.state_machine.current_pose
            fb.battery_soc = float(self.state_machine.battery_soc_percent)

        ros_pose = RosPoseStamped()
        ros_pose.header.stamp = self.get_clock().now().to_msg()
        ros_pose.header.frame_id = snapshot_pose.frame_id or "map"
        ros_pose.pose.position.x = snapshot_pose.x
        ros_pose.pose.position.y = snapshot_pose.y
        ros_pose.pose.position.z = snapshot_pose.z
        qx, qy, qz, qw = yaw_to_quaternion(snapshot_pose.yaw)
        ros_pose.pose.orientation.x = qx
        ros_pose.pose.orientation.y = qy
        ros_pose.pose.orientation.z = qz
        ros_pose.pose.orientation.w = qw

        fb.current_pose = ros_pose
        try:
            goal_handle.publish_feedback(fb)
        except Exception:
            pass

    def _odom_callback(self, msg: Odometry) -> None:
        """Receive odometry messages, compute velocity and heading, and update state machine."""
        received_monotonic_ns = time.monotonic_ns()
        stamp_sec = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

        px = msg.pose.pose.position.x
        py = msg.pose.pose.position.y
        pz = msg.pose.pose.position.z
        qx = msg.pose.pose.orientation.x
        qy = msg.pose.pose.orientation.y
        qz = msg.pose.pose.orientation.z
        qw = msg.pose.pose.orientation.w
        yaw = quaternion_to_yaw(qx, qy, qz, qw)

        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        lin_speed = math.hypot(vx, vy)
        ang_speed = msg.twist.twist.angular.z

        odom_frame = msg.header.frame_id.lstrip("/")
        pose_stamped = self._map_odometry_pose(odom_frame, msg.header.stamp, px, py, pz, yaw)
        reading = OdometryReading(
            timestamp_sec=stamp_sec,
            linear_velocity=lin_speed,
            angular_velocity=ang_speed,
            pose=pose_stamped,
            source_frame_id=msg.header.frame_id,
            source_frame_valid=odom_frame in ("map", "odom", f"{self.robot_namespace.strip('/')}/odom"),
            received_monotonic_ns=received_monotonic_ns,
        )

        with self._lock:
            self.state_machine.update_odometry(reading, self.get_clock().now().nanoseconds / 1e9)

    def _map_odometry_pose(self, frame, stamp, x, y, z, yaw):
        robot_odom = f"{self.robot_namespace.strip('/')}/odom"
        stamp_ns = stamp.sec * 10**9 + stamp.nanosec
        if frame in ("odom", robot_odom):
            if self._map_tf is None:
                origin_x, origin_y, origin_yaw = self.initial_pose
            else:
                if stamp_ns <= 0:
                    return None
                try:
                    transform = self._map_tf.lookup_transform("map", robot_odom, Time.from_msg(stamp)).transform
                except TransformException:
                    return None
                origin_x, origin_y = transform.translation.x, transform.translation.y
                z += transform.translation.z
                q = transform.rotation
                origin_yaw = quaternion_to_yaw(q.x, q.y, q.z, q.w)
            cos_yaw, sin_yaw = math.cos(origin_yaw), math.sin(origin_yaw)
            x, y = origin_x + x * cos_yaw - y * sin_yaw, origin_y + x * sin_yaw + y * cos_yaw
            yaw = math.atan2(math.sin(origin_yaw + yaw), math.cos(origin_yaw + yaw))
            frame = "map"
        elif self._map_tf is not None and frame != "map":
            return None
        return PoseStamped(x=x, y=y, z=z, yaw=yaw, frame_id=frame, timestamp_sec=stamp_ns / 1e9)

    def _battery_source_available(self) -> bool:
        """Check the discovered source while holding the Executor lock."""
        if self._battery.blocked_reason:
            return False
        if self._battery_clock_changed.is_set():
            self._battery.blocked_reason = "Simulation clock rewound or changed source"
        else:
            endpoints = self.get_publishers_info_by_topic(self._battery_topic)
            if not endpoints:
                return False
            endpoint = endpoints[0]
            gid = bytes(endpoint.endpoint_gid)
            if (len(endpoints) == 1 and any(gid)
                    and endpoint.topic_type == "fleet_interfaces/msg/BatteryState"
                    and self._battery_endpoint_gid in (None, gid)):
                # DDS writer discovery can precede its association with a ROS node.
                if endpoint.node_name in ("_NODE_NAME_UNKNOWN_", "_CREATED_BY_BARE_DDS_APP_"):
                    return False
                if endpoint.node_name == "battery_simulator" and endpoint.node_namespace == self.robot_namespace:
                    self._battery_endpoint_gid = gid
                    return True
            self._battery.blocked_reason = "Conflicting or replaced BatteryState publisher"
        self.get_logger().error(f"{self._battery.blocked_reason}. Scenario reset required.")
        return False

    def _battery_callback(self, msg: BatteryState) -> None:
        with self._lock:
            if not self._battery_source_available():
                return
            if self._battery.observe(msg, self.get_clock().now().nanoseconds, time.monotonic(),
                                     self.state_machine.dock_station_id):
                self.state_machine.update_battery(msg.battery_soc_percent, msg.battery_energy_wh)
                if self._battery.charging_station_id:
                    self.state_machine.start_charging()
                else:
                    self.state_machine.stop_charging()
                proof = self._battery.control_proof
                if proof:
                    self._battery_control_proof = (proof, time.monotonic())
            elif self._battery.blocked_reason:
                self.get_logger().error(f"{self._battery.blocked_reason}. Scenario reset required.")

    def _battery_control_callback(self, msg: BatteryControlApplied) -> None:
        with self._lock:
            endpoints = self.get_publishers_info_by_topic(self._battery_control_topic)
            if (len(endpoints) != 1 or endpoints[0].topic_type != "fleet_interfaces/msg/BatteryControlApplied"
                    or endpoints[0].node_name != "battery_simulator"
                    or endpoints[0].node_namespace != self.robot_namespace):
                self._battery.blocked_reason = "Conflicting Battery Control attestation publisher"
                return
            gid = bytes(endpoints[0].endpoint_gid)
            if not any(gid) or self._battery_control_endpoint_gid not in (None, gid):
                self._battery.blocked_reason = "Battery Control attestation source changed"
                return
            self._battery_control_endpoint_gid = gid
            if self._battery.authorize_control(msg, self.get_clock().now().nanoseconds, time.monotonic()):
                # Kept for at most the two-second freshness window so FM's 5 Hz stream observes it.
                if self._battery.blocked_reason:
                    self.get_logger().error(f"{self._battery.blocked_reason}. Scenario reset required.")
                    return
                self._pending_battery_control_session = msg.control_session_id
                proof = self._battery.take_resolved_control_proof()
                if proof:
                    self.state_machine.update_battery(self._battery.soc_percent, self._battery.energy_wh)
                    if self._battery.charging_station_id:
                        self.state_machine.start_charging()
                    else:
                        self.state_machine.stop_charging()
                    self._battery_control_proof = (proof, time.monotonic())

    def _legacy_battery_callback(self, msg: RobotStatus) -> None:
        if msg.robot_id != self.robot_id:
            return
        with self._lock:
            self.state_machine.update_battery(msg.battery_soc_percent, msg.battery_energy_wh)

    def _physical_pose_callback(self, msg: RosPoseStamped) -> None:
        stamp = msg.header.stamp
        stamp_ns = stamp.sec * 10**9 + stamp.nanosec
        if (not msg.header.frame_id or not 0 <= stamp.nanosec < 10**9
                or not 0 < stamp_ns <= self.get_clock().now().nanoseconds + 300_000_000):
            return
        with self._lock:
            if self._physical_pose is None or stamp_ns > self._physical_pose[0]:
                self._physical_pose = (stamp_ns, msg)

    def _fresh_battery_stamp(self, sim_ns: int) -> int:
        if self._battery is not None and self._battery_source_available():
            return self._battery.fresh_stamp(sim_ns, time.monotonic())
        return 0

    def _status_timer_callback(self) -> None:
        """Publish 5 Hz RobotStatus telemetry snapshot."""
        now_stamp = self.get_clock().now()
        now_sim = now_stamp.nanoseconds / 1e9

        with self._lock:
            sequence = self.safety.next_status()
            if sequence is None:
                return
            snap = self.state_machine.get_status_snapshot(now_sim)
            battery_stamp_ns = self._fresh_battery_stamp(now_stamp.nanoseconds)
            dock_station_id = self.state_machine.dock_station_id
            charging_station_id = self._battery.charging_station_id if battery_stamp_ns else ""
            physical_pose = self._physical_pose

        msg = RobotStatus()
        msg.header.stamp = now_stamp.to_msg()
        msg.header.frame_id = snap.pose.frame_id
        msg.status_seq = sequence
        msg.publisher_session_id.uuid = list(self.safety.session_id.bytes)
        msg.robot_id = snap.robot_id
        msg.current_epoch = snap.current_epoch
        msg.state = snap.state
        msg.current_phase = snap.current_phase
        msg.is_loaded = snap.is_loaded

        # Preserve measurement time when a heartbeat republishes cached odometry.
        pose_ns = round(snap.pose.timestamp_sec * 10**9)
        msg.pose.header.stamp.sec, msg.pose.header.stamp.nanosec = divmod(pose_ns, 10**9)
        msg.pose.header.frame_id = msg.header.frame_id
        msg.pose.pose.position.x = snap.pose.x
        msg.pose.pose.position.y = snap.pose.y
        msg.pose.pose.position.z = snap.pose.z
        qx, qy, qz, qw = yaw_to_quaternion(snap.pose.yaw)
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw

        msg.battery_soc_percent = float(snap.battery_soc_percent)
        msg.battery_energy_wh = float(snap.battery_energy_wh)
        msg.battery_stamp.sec, msg.battery_stamp.nanosec = divmod(battery_stamp_ns, 10**9)
        msg.current_task_id = snap.current_task_id
        msg.dock_station_id = dock_station_id
        msg.charging_station_id = charging_station_id
        proof = getattr(self, "_battery_control_proof", None)
        if proof and time.monotonic() - proof[1] <= 2.0:
            values = proof[0]
            msg.battery_control_session_id = values[0]
            msg.battery_control_request_id = values[1]
            msg.battery_control_soc_percent = values[2]
            msg.battery_control_energy_wh = values[3]
            msg.battery_control_stamp.sec, msg.battery_control_stamp.nanosec = divmod(values[4], 10**9)
        if physical_pose is not None and 0 <= now_stamp.nanoseconds - physical_pose[0] <= 300_000_000:
            msg.physical_pose = physical_pose[1]

        self._status_pub.publish(msg)

    def _clear_error_callback(
        self,
        request: ClearRobotError.Request,
        response: ClearRobotError.Response,
    ) -> ClearRobotError.Response:
        """Execute conditional error clearing preserving assignment_epoch (Option A)."""
        now_sim = self.get_clock().now().nanoseconds / 1e9
        with self._lock:
            if self.safety.blocked:
                response.accepted = False
                response.reason = self.safety.reason
                response.resulting_state = int(self.state_machine.state)
                return response
            odom = self.state_machine.last_odometry
            res = self.state_machine.clear_robot_error(
                robot_id=request.robot_id,
                expected_epoch=request.expected_epoch,
                odometry=odom,
                current_sim_time=now_sim,
            )

        response.accepted = res.accepted
        response.reason = res.reason
        response.resulting_state = res.resulting_state

        if res.accepted:
            self.get_logger().info(
                f"Cleared error for robot '{request.robot_id}' at epoch {request.expected_epoch}."
            )
        else:
            self.get_logger().warn(
                f"ClearRobotError rejected for robot '{request.robot_id}': {res.reason}"
            )

        return response


    def destroy_node(self):
        self._stopping.set()
        return super().destroy_node()


def main(args=None, *, _test_reset_verified=False, _legacy_test_battery=False):
    """Entry point for robot_executor_node."""
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    node = None
    executor = MultiThreadedExecutor()
    try:
        node = RobotExecutorNode(
            _test_reset_verified=_test_reset_verified, _legacy_test_battery=_legacy_test_battery,
        )
        executor.add_node(node)
        while rclpy.ok() and not stopping:
            executor.spin_once(timeout_sec=0.2)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node._stopping.set()
        executor.shutdown()
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
