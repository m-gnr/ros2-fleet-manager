"""Read isolated, verified TF chains with one ROS participant."""
from dataclasses import replace
from math import isfinite
from time import monotonic_ns

from action_msgs.msg import GoalStatus, GoalStatusArray
from nav_msgs.msg import Odometry, Path
from rclpy.clock import Clock, ClockType
from rclpy.duration import Duration
from rclpy.impl.implementation_singleton import rclpy_implementation
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.serialization import deserialize_message
from rclpy.time import Time
from rosgraph_msgs.msg import Clock as ClockMessage
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformException

from observed_plan import MAX_ROS_BYTES, PlanBuffer
from telemetry import NS, Pose, yaw_from_quaternion


def stamp_ns(stamp):
    return stamp.sec * NS + stamp.nanosec


class RosReader(Node):
    def __init__(self, robots, hz, on_snapshot, *, context, plan_topics=None):
        super().__init__("fleet_visualizer", enable_rosout=False,
                         start_parameter_services=False, use_global_arguments=False, context=context)
        # Humble always creates a parameter event writer during Node initialization.
        for publisher in list(self.publishers):
            self.destroy_publisher(publisher)

        self.robots = {}
        self.planners = {}
        self.on_snapshot = on_snapshot
        for namespace, telemetry in robots:
            reader = RobotReader(namespace, telemetry)
            self.robots[reader.robot_id] = reader
            if plan_topics and reader.robot_id in plan_topics:
                self.planners[reader.robot_id] = PlannerReader(
                    self, namespace, plan_topics[reader.robot_id], telemetry)
            if reader.tf is not None:
                self.create_subscription(TFMessage, namespace + "/tf", reader.on_tf, 10)
            else:
                self.create_subscription(Odometry, namespace + "/odom", reader.on_odom,
                                         QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.create_subscription(ClockMessage, "/clock", self.on_clock,
                                 QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.create_timer(1 / hz, self.sample, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def on_clock(self, msg):
        stamp, now = stamp_ns(msg.clock), monotonic_ns()
        for robot_id, reader in self.robots.items():
            if reader.clock(stamp, now):
                planner = self.planners.get(robot_id)
                if planner:
                    planner.buffer.reset()
                self.on_snapshot(robot_id, reader.sample(now))

    def sample(self):
        now = monotonic_ns()
        for robot_id, reader in self.robots.items():
            snapshot = reader.sample(now)
            planner = self.planners.get(robot_id)
            if planner:
                plan = planner.sample(now, snapshot.status == "LIVE")
                if plan is not None:
                    snapshot = replace(snapshot, plan=plan)
            self.on_snapshot(robot_id, snapshot)


class PlannerReader:
    def __init__(self, node, namespace, topic, telemetry):
        self.node = node
        self.namespace = namespace
        self.topic = topic
        self.telemetry = telemetry
        self.buffer = PlanBuffer()
        self.writer = None
        self.next_graph_check = 0
        self.status_topic = namespace + "/navigate_to_pose/_action/status"
        self.goals = {}
        node.create_subscription(Path, topic, self.on_path, 1, raw=True)
        node.create_subscription(GoalStatusArray, self.status_topic, self.on_navigation,
                                 QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))

    def on_navigation(self, message):
        # Status can invalidate an observation, but never establishes Path ownership.
        endpoints = self.node.get_publishers_info_by_topic(self.status_topic)
        if (len(endpoints) != 1 or endpoints[0].node_name != "bt_navigator"
                or endpoints[0].node_namespace != self.namespace or len(message.status_list) > 128):
            self.buffer.plan = None
            return
        active = (GoalStatus.STATUS_ACCEPTED, GoalStatus.STATUS_EXECUTING, GoalStatus.STATUS_CANCELING)
        goals = {bytes(row.goal_info.goal_id.uuid): row.status for row in message.status_list}
        if (any(goals.get(goal) != status for goal, status in self.goals.items() if status in active)
                or any(self.goals.get(goal) != status for goal, status in goals.items() if status in active)):
            self.buffer.plan = None
        self.goals = goals

    def check_writer(self):
        endpoints = self.node.get_publishers_info_by_topic(self.topic)
        writer = None
        if len(endpoints) == 1:
            endpoint = endpoints[0]
            qos = endpoint.qos_profile
            if (endpoint.node_namespace == self.namespace and endpoint.node_name == "planner_server"
                    and endpoint.topic_type == "nav_msgs/msg/Path"
                    and qos.reliability == ReliabilityPolicy.RELIABLE
                    and qos.durability == DurabilityPolicy.VOLATILE
                    and qos.history == HistoryPolicy.KEEP_LAST and qos.depth == 1):
                writer = tuple(endpoint.endpoint_gid)
        if writer != self.writer:
            self.buffer.plan = None
            self.writer = writer
        return writer is not None

    def on_path(self, raw):
        if not self.check_writer():
            return
        if len(raw) > MAX_ROS_BYTES:
            self.buffer.plan = None
            return
        try:
            message = deserialize_message(raw, Path)
        except rclpy_implementation.RMWError:
            self.buffer.plan = None
            return
        self.buffer.accept(message, self.telemetry.clock_ns, monotonic_ns())

    def sample(self, now, pose_live):
        if not pose_live:
            self.buffer.plan = None
        elif self.buffer.plan is not None and now >= self.next_graph_check:
            self.check_writer()
            self.next_graph_check = now + NS // 4
        return self.buffer.current(self.telemetry.clock_ns, now)


class RobotReader:
    def __init__(self, namespace, telemetry):
        self.telemetry = telemetry
        self.odom_frame = namespace.lstrip("/") + "/odom"
        self.base_frame = namespace.lstrip("/") + "/base_link"
        self.frame = telemetry.identity["frame_id"]
        self.robot_id = telemetry.identity["robot_id"]
        self.latest = None
        self.localization_ns = 0
        self.frame_error = False
        self.bad_edges = set()
        self.tf = Buffer(cache_time=Duration(seconds=5)) if telemetry.identity["source"] == "tf" else None

    def clock(self, stamp, now):
        if self.telemetry.clock(stamp, now):
            if self.tf is not None:
                self.tf.clear()
            self.latest = None
            self.localization_ns = 0
            self.frame_error = False
            self.bad_edges.clear()
            return True
        return False

    def on_tf(self, msg):
        now = monotonic_ns()
        clock = self.telemetry.clock_ns
        if clock <= 0:
            return
        for transform in msg.transforms:
            parent, child = transform.header.frame_id, transform.child_frame_id
            stamp = stamp_ns(transform.header.stamp)
            if child == self.odom_frame:
                expected, cutoff, lead = self.frame, self.localization_ns, 2 * NS
            elif child == self.base_frame:
                expected, cutoff, lead = self.odom_frame, self.latest[0] if self.latest else 0, NS // 4
            else:
                continue

            if parent != expected:
                self.bad_edges.add(child)
                continue
            if not cutoff < stamp <= clock + lead:
                continue
            translation, q = transform.transform.translation, transform.transform.rotation
            try:
                yaw_from_quaternion(q.x, q.y, q.z, q.w)
                if not all(isfinite(value) for value in (translation.x, translation.y, translation.z)):
                    raise ValueError("Invalid TF translation")
                self.tf.set_transform(transform, "visualizer")
            except (TransformException, ValueError):
                self.bad_edges.add(child)
                continue
            self.bad_edges.discard(child)
            if child == self.odom_frame:
                self.localization_ns = stamp
            else:
                self.latest = (stamp, now)

    def make_pose(self, position, q, stamp, received):
        yaw = yaw_from_quaternion(q.x, q.y, q.z, q.w)
        return Pose(self.robot_id, self.frame, stamp, position.x, position.y, yaw, received)

    def on_odom(self, msg):
        self.frame_error = (msg.header.frame_id != self.odom_frame
                            or msg.child_frame_id != self.base_frame)
        if self.frame_error:
            return
        stamp = stamp_ns(msg.header.stamp)
        clock = self.telemetry.clock_ns
        if 0 < stamp <= clock + NS // 4 and clock > 0 and (
            self.latest is None or stamp > self.latest.stamp_ns
        ):
            try:
                self.latest = self.make_pose(msg.pose.pose.position, msg.pose.pose.orientation,
                                             stamp, monotonic_ns())
            except ValueError:
                self.frame_error = True

    def sample(self, now):
        if self.tf is None:
            return self.telemetry.sample(self.latest, now, frame_error=self.frame_error)
        candidate, frame_error = self.resolve_tf(now)
        return self.telemetry.sample(candidate, now, frame_error=frame_error)

    def resolve_tf(self, now):
        if self.latest is None or self.bad_edges:
            return None, bool(self.bad_edges)
        stamp, received = self.latest
        if now - received >= self.telemetry.stale_ns:
            return None, False
        try:
            transform = self.tf.lookup_transform(self.frame, self.base_frame, Time(nanoseconds=stamp))
            if (transform.header.frame_id != self.frame or transform.child_frame_id != self.base_frame
                    or stamp_ns(transform.header.stamp) != stamp):
                return None, True
            return self.make_pose(transform.transform.translation, transform.transform.rotation,
                                  stamp, received), False
        except (TransformException, ValueError):
            return None, True
