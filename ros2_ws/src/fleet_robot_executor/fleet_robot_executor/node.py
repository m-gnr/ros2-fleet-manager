"""ROS 2 Robot Executor Node.

Provides the logistics adapter layer between Fleet Manager and Nav2:
- ActionServer for fleet_interfaces/action/ExecuteTask
- ActionClient for nav2_msgs/action/NavigateToPose
- 5 Hz periodic publisher for fleet_interfaces/msg/RobotStatus
- ServiceServer for fleet_interfaces/srv/ClearRobotError
- Odometry and battery telemetry subscriber
- Active zero-velocity braking and stop verification for safe preemption
"""

import math
import threading
import time
from typing import Optional, Tuple
import uuid

import rclpy
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node

from action_msgs.msg import GoalStatus
from builtin_interfaces.msg import Time as RosTime
from geometry_msgs.msg import PoseStamped as RosPoseStamped, Twist
from nav_msgs.msg import Odometry

from fleet_interfaces.action import ExecuteTask
from fleet_interfaces.msg import RobotStatus
from fleet_interfaces.srv import ClearRobotError
from nav2_msgs.action import NavigateToPose

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

    def __init__(self, node_name: str = "robot_executor") -> None:
        super().__init__(node_name)

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
            self.get_logger().warn(
                f"Could not load fleet configuration ({e}). Falling back to ROS parameters."
            )

        if robot_cfg:
            self.robot_id = param_robot_id or robot_cfg.robot_id
            self.robot_namespace = self.get_parameter("robot_namespace").value or robot_cfg.namespace
            self.nav2_action_name = self.get_parameter("nav2_action_name").value or robot_cfg.nav2_action_name
        else:
            self.robot_id = param_robot_id or "robot_1"
            self.robot_namespace = self.get_parameter("robot_namespace").value or f"/{self.robot_id}"
            self.nav2_action_name = self.get_parameter("nav2_action_name").value or f"{self.robot_namespace}/navigate_to_pose"

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
        self._lock = threading.Lock()

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
        self._odom_sub = self.create_subscription(
            Odometry,
            odom_topic,
            self._odom_callback,
            10,
            callback_group=self.cb_group,
        )
        self.get_logger().info(f"Subscribed to Odometry on '{odom_topic}'")

        # Active Braking cmd_vel Publisher
        cmd_vel_topic = self._qualify(str(self.get_parameter("cmd_vel_topic_name").value))
        self._cmd_vel_pub = self.create_publisher(Twist, cmd_vel_topic, 10)

        # Battery State Subscriber (for future C4 battery_simulator integration)
        battery_topic = self._qualify(str(self.get_parameter("battery_state_topic_name").value))
        self._battery_sub = self.create_subscription(
            RobotStatus,  # generic telemetry container or fallback
            battery_topic,
            self._battery_callback,
            10,
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
            can_cancel, reason = self.state_machine.can_cancel_goal(goal_uuid)

        if not can_cancel:
            self.get_logger().warn(
                f"Rejecting cancel request for goal {goal_uuid}: {reason}"
            )
            return CancelResponse.REJECT

        self.get_logger().info(f"Accepted cancel request for goal {goal_uuid}. Initiating safe preemption.")
        return CancelResponse.ACCEPT

    def _execute_task_callback(self, goal_handle: ServerGoalHandle) -> ExecuteTask.Result:
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
                goal_handle.abort()
                res = ExecuteTask.Result()
                res.status = TaskResultStatus.STATUS_FAILED
                res.error_reason = ErrorReason.REJECTED_ROBOT_NOT_IDLE
                return res

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
            self.state_machine.start_loading(goal_uuid)
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
        result.completed_epoch = task_res.completed_epoch if task_res else req.assignment_epoch
        result.completion_stamp = self.get_clock().now().to_msg()
        result.error_reason = ""
        goal_handle.succeed()
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

        # Check Nav2 action server readiness
        if not self._nav2_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error(f"Nav2 action server '{self.nav2_action_name}' not available!")
            now_sim = self.get_clock().now().nanoseconds / 1e9
            with self._lock:
                self.state_machine.report_task_error(goal_uuid, ErrorReason.NAV2_FAILED, now_sim)
            goal_handle.abort()
            res = ExecuteTask.Result()
            res.status = TaskResultStatus.STATUS_FAILED
            res.error_reason = ErrorReason.NAV2_FAILED
            res.completion_stamp = self.get_clock().now().to_msg()
            return False, res

        nav2_goal = NavigateToPose.Goal()
        nav2_goal.pose = target_pose
        # Always use current sim time so Nav2 transform lookup and costmaps use latest time
        nav2_goal.pose.header.stamp = self.get_clock().now().to_msg()

        send_future = self._nav2_client.send_goal_async(nav2_goal)
        t_start = time.time()
        while not send_future.done() and (time.time() - t_start < 5.0):
            time.sleep(0.02)

        nav2_goal_handle = send_future.result()
        if not nav2_goal_handle or not nav2_goal_handle.accepted:
            self.get_logger().error(f"Nav2 rejected navigation goal for {goal_uuid}")
            now_sim = self.get_clock().now().nanoseconds / 1e9
            with self._lock:
                self.state_machine.report_task_error(goal_uuid, ErrorReason.NAV2_ABORTED, now_sim)
            goal_handle.abort()
            res = ExecuteTask.Result()
            res.status = TaskResultStatus.STATUS_FAILED
            res.error_reason = ErrorReason.NAV2_ABORTED
            res.completion_stamp = self.get_clock().now().to_msg()
            return False, res

        self._active_nav2_goal_handle = nav2_goal_handle
        result_future = nav2_goal_handle.get_result_async()

        # Navigation loop
        while not result_future.done():
            # Check preemption request
            if goal_handle.is_cancel_requested:
                terminal_res = self._execute_safe_cancel(
                    goal_handle=goal_handle,
                    goal_uuid=goal_uuid,
                    nav2_goal_handle=nav2_goal_handle,
                )
                self._active_nav2_goal_handle = None
                return False, terminal_res

            # Periodic feedback
            dist = self._calculate_distance_to(target_model)
            self._publish_feedback(goal_handle, phase, dist)
            time.sleep(0.05)

        self._active_nav2_goal_handle = None
        nav2_res = result_future.result()
        if nav2_res.status != GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().error(
                f"Nav2 navigation failed with status {nav2_res.status} for {goal_uuid}"
            )
            now_sim = self.get_clock().now().nanoseconds / 1e9
            with self._lock:
                self.state_machine.report_task_error(goal_uuid, ErrorReason.NAV2_ABORTED, now_sim)
            goal_handle.abort()
            res = ExecuteTask.Result()
            res.status = TaskResultStatus.STATUS_FAILED
            res.error_reason = ErrorReason.NAV2_ABORTED
            res.completion_stamp = self.get_clock().now().to_msg()
            return False, res

        return True, None

    def _execute_safe_cancel(
        self,
        goal_handle: ServerGoalHandle,
        goal_uuid: str,
        nav2_goal_handle,
    ) -> ExecuteTask.Result:
        """Handle 3-criteria safe preemption with Nav2 abort, active brake, and odom stop check."""
        now_sim = self.get_clock().now().nanoseconds / 1e9
        with self._lock:
            self.state_machine.request_cancel(goal_uuid, now_sim)

        self.get_logger().info(f"Cancelling Nav2 trajectory for task {goal_uuid}...")
        nav2_cancel_ok = False
        if nav2_goal_handle is not None:
            cancel_future = nav2_goal_handle.cancel_goal_async()
            t0 = time.time()
            while not cancel_future.done() and (time.time() - t0 < 3.0):
                time.sleep(0.02)
            if cancel_future.done():
                cancel_resp = cancel_future.result()
                nav2_cancel_ok = getattr(cancel_resp, "return_code", 0) == 0
                self.get_logger().info(f"Nav2 cancel response return_code: {getattr(cancel_resp, 'return_code', None)}, ok={nav2_cancel_ok}")
            else:
                self.get_logger().warn("Nav2 cancel request timed out!")

        with self._lock:
            terminal_task_res = self.state_machine.notify_nav2_cancel_result(
                goal_uuid, nav2_cancel_ok, now_sim
            )

        # Active zero-velocity braking
        stop_cmd = Twist()
        try:
            self._cmd_vel_pub.publish(stop_cmd)
        except Exception:
            pass

        # Loop until stop confirmed or timeout
        if terminal_task_res is None:
            while True:
                try:
                    self._cmd_vel_pub.publish(stop_cmd)
                except Exception:
                    pass
                curr_sim = self.get_clock().now().nanoseconds / 1e9
                with self._lock:
                    terminal_task_res = self.state_machine.check_cancel_timeout(curr_sim)
                if terminal_task_res is not None:
                    break
                time.sleep(0.05)

        res = ExecuteTask.Result()
        res.status = terminal_task_res.status
        res.completed_epoch = terminal_task_res.completed_epoch
        res.completion_stamp = self.get_clock().now().to_msg()
        res.error_reason = terminal_task_res.error_reason

        if terminal_task_res.status == TaskResultStatus.STATUS_PREEMPTED:
            self.get_logger().info(
                f"Task {goal_uuid} safe preemption confirmed! Robot halted and returned to IDLE."
            )
            goal_handle.canceled()
        else:
            self.get_logger().error(
                f"Preemption stop timeout for {goal_uuid}! Robot transitioned to STATE_ERROR."
            )
            goal_handle.abort()

        return res

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
        stamp_sec = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if stamp_sec <= 0:
            stamp_sec = self.get_clock().now().nanoseconds / 1e9

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

        pose_stamped = PoseStamped(
            x=px,
            y=py,
            z=pz,
            yaw=yaw,
            frame_id=msg.header.frame_id or "map",
            timestamp_sec=stamp_sec,
        )
        reading = OdometryReading(
            timestamp_sec=stamp_sec,
            linear_velocity=lin_speed,
            angular_velocity=ang_speed,
            pose=pose_stamped,
        )

        with self._lock:
            self.state_machine.update_odometry(reading)

    def _battery_callback(self, msg) -> None:
        """Receive battery state updates from battery simulator node."""
        soc = getattr(msg, "battery_soc_percent", None)
        energy = getattr(msg, "battery_energy_wh", None)
        if soc is not None and energy is not None:
            with self._lock:
                self.state_machine.update_battery(float(soc), float(energy))

    def _status_timer_callback(self) -> None:
        """Publish 5 Hz RobotStatus telemetry snapshot."""
        now_stamp = self.get_clock().now()
        now_sim = now_stamp.nanoseconds / 1e9

        with self._lock:
            snap = self.state_machine.get_status_snapshot(now_sim)

        msg = RobotStatus()
        msg.header.stamp = now_stamp.to_msg()
        msg.header.frame_id = snap.pose.frame_id or "map"
        msg.robot_id = snap.robot_id
        msg.current_epoch = snap.current_epoch
        msg.state = snap.state
        msg.current_phase = snap.current_phase
        msg.is_loaded = snap.is_loaded

        msg.pose.header.stamp = msg.header.stamp
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
        msg.current_task_id = snap.current_task_id

        self._status_pub.publish(msg)

    def _clear_error_callback(
        self,
        request: ClearRobotError.Request,
        response: ClearRobotError.Response,
    ) -> ClearRobotError.Response:
        """Execute conditional error clearing preserving assignment_epoch (Option A)."""
        now_sim = self.get_clock().now().nanoseconds / 1e9
        with self._lock:
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


def main(args=None):
    """Entry point for robot_executor_node."""
    rclpy.init(args=args)
    node = RobotExecutorNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
