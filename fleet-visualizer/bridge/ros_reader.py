"""Read a single verified TF chain or explicit diagnostic odometry."""
from time import monotonic_ns

from nav_msgs.msg import Odometry
from rclpy.clock import Clock, ClockType
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from rosgraph_msgs.msg import Clock as ClockMessage
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformException

from telemetry import NS, Pose, yaw_from_quaternion


def stamp_ns(stamp):
    return stamp.sec * NS + stamp.nanosec


class RosReader(Node):
    def __init__(self, namespace, telemetry, hz, on_snapshot, *, context):
        super().__init__("fleet_visualizer", enable_rosout=False,
                         start_parameter_services=False, use_global_arguments=False, context=context)
        # Humble always creates a parameter event writer during Node initialization.
        for publisher in list(self.publishers):
            self.destroy_publisher(publisher)

        self.telemetry = telemetry
        self.on_snapshot = on_snapshot
        self.odom_frame = namespace.lstrip("/") + "/odom"
        self.base_frame = namespace.lstrip("/") + "/base_link"
        self.frame = telemetry.identity["frame_id"]
        self.robot_id = telemetry.identity["robot_id"]
        self.latest = None
        self.localization_ns = 0
        self.frame_error = False
        self.tf = None

        self.create_subscription(ClockMessage, "/clock", self.on_clock,
                                 QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
        if telemetry.identity["source"] == "tf":
            self.tf = Buffer(cache_time=Duration(seconds=5))
            self.create_subscription(TFMessage, namespace + "/tf", self.on_tf, 10)
        else:
            self.create_subscription(Odometry, namespace + "/odom", self.on_odom,
                                     QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.create_timer(1 / hz, self.sample, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def on_clock(self, msg):
        if self.telemetry.clock(stamp_ns(msg.clock), monotonic_ns()):
            if self.tf is not None:
                self.tf.clear()
            self.latest = None
            self.localization_ns = 0
            self.frame_error = False
            self.on_snapshot(self.telemetry.sample(None, monotonic_ns()))

    def on_tf(self, msg):
        now = monotonic_ns()
        clock = self.telemetry.clock_ns
        if clock <= 0:
            return
        for transform in msg.transforms:
            parent, child = transform.header.frame_id, transform.child_frame_id
            stamp = stamp_ns(transform.header.stamp)
            if child == self.odom_frame and parent == self.frame:
                # AMCL post-dates map->odom by the configured transform tolerance.
                if self.localization_ns < stamp <= clock + 2 * NS:
                    self.tf.set_transform(transform, "visualizer")
                    self.localization_ns = stamp
            elif child == self.base_frame and parent == self.odom_frame:
                # /clock and /tf are delivered independently. Allow a small receive skew.
                if (self.latest is None or stamp > self.latest[0]) and 0 < stamp <= clock + NS // 4:
                    self.tf.set_transform(transform, "visualizer")
                    self.latest = (stamp, now)
                    self.frame_error = False
            elif child in (self.base_frame, self.odom_frame):
                self.frame_error = True

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

    def sample(self):
        now = monotonic_ns()
        if self.tf is None:
            snapshot = self.telemetry.sample(self.latest, now, frame_error=self.frame_error)
        else:
            candidate, frame_error = self.resolve_tf(now)
            snapshot = self.telemetry.sample(candidate, now, frame_error=frame_error)
        self.on_snapshot(snapshot)

    def resolve_tf(self, now):
        if self.latest is None or self.frame_error:
            return None, self.frame_error
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
