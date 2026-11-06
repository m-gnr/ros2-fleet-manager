from time import monotonic_ns
import unittest

try:
    from geometry_msgs.msg import TransformStamped
    from nav_msgs.msg import Odometry
    from rclpy import init
    from rclpy.context import Context
    from rclpy.signals import SignalHandlerOptions
    from rosgraph_msgs.msg import Clock
    from tf2_msgs.msg import TFMessage
except ImportError as error:
    raise unittest.SkipTest("ROS 2 Humble is required") from error

from ros_reader import RosReader
from telemetry import NS, Telemetry


def edge(parent, child, sec, x):
    transform = TransformStamped()
    transform.header.frame_id = parent
    transform.child_frame_id = child
    transform.header.stamp.sec = sec
    transform.transform.translation.x = float(x)
    transform.transform.rotation.w = 1.0
    return transform


class RosChecks(unittest.TestCase):
    def setUp(self):
        context = Context()
        init(args=[], context=context, signal_handler_options=SignalHandlerOptions.NO)
        self.addCleanup(context.shutdown)
        self.snapshots = []
        self.reader = RosReader("/selected", Telemetry("robot", "map", "tf", 1), 20,
                                self.snapshots.append, context=context)
        self.addCleanup(self.reader.destroy_node)
        self.clock(20)

    def clock(self, sec):
        msg = Clock()
        msg.clock.sec = sec
        self.reader.on_clock(msg)

    def tf(self, *edges):
        self.reader.on_tf(TFMessage(transforms=list(edges)))

    def test_ros_endpoints_and_chain(self):
        self.assertEqual(list(self.reader.publishers), [])
        self.assertEqual(list(self.reader.clients), [])
        self.assertEqual(list(self.reader.services), [])
        self.assertEqual({sub.topic_name for sub in self.reader.subscriptions}, {"/clock", "/selected/tf"})
        self.tf(edge("map", "other/odom", 20, 99), edge("other/odom", "other/base_link", 20, 99))
        self.reader.sample()
        self.assertEqual(self.snapshots[-1].status, "NO_DATA")
        self.tf(edge("selected/odom", "selected/base_link", 20, 2))
        self.reader.sample()
        self.assertEqual(self.snapshots[-1].status, "FRAME_ERROR")
        self.tf(edge("map", "selected/odom", 20, 5))
        self.reader.sample()
        self.assertEqual(self.snapshots[-1].status, "LIVE")
        self.assertEqual(self.snapshots[-1].pose.x, 7)

    def test_bad_parent_and_rewind_flush_tf(self):
        self.tf(edge("map", "selected/odom", 20, 5),
                edge("selected/odom", "selected/base_link", 20, 2),
                edge("other/odom", "selected/base_link", 20, 99))
        self.reader.sample()
        self.assertEqual(self.snapshots[-1].status, "FRAME_ERROR")
        self.clock(1)
        self.tf(edge("selected/odom", "selected/base_link", 20, 99))
        self.assertIsNone(self.reader.latest)
        self.tf(edge("selected/odom", "selected/base_link", 1, 4))
        self.assertEqual(self.reader.resolve_tf(monotonic_ns()), (None, True))
        self.tf(edge("map", "selected/odom", 1, 3))
        self.reader.sample()
        self.assertEqual((self.snapshots[-1].epoch, self.snapshots[-1].pose.stamp_ns,
                          self.snapshots[-1].pose.x), (1, NS, 7))

    def test_diagnostic_odometry_requires_its_own_frames(self):
        samples = []
        reader = RosReader("/selected", Telemetry("robot", "selected/odom", "diagnostic_odom", 1),
                           20, samples.append, context=self.reader.context)
        self.addCleanup(reader.destroy_node)
        msg = Clock()
        msg.clock.sec = 20
        reader.on_clock(msg)
        odom = Odometry()
        odom.header.stamp.sec = 20
        odom.header.frame_id = "other/odom"
        odom.child_frame_id = "other/base_link"
        odom.pose.pose.orientation.w = 1.0
        odom.pose.pose.position.x = 2.0
        reader.on_odom(odom)
        reader.sample()
        self.assertEqual(samples[-1].status, "FRAME_ERROR")

        odom.header.frame_id = "selected/odom"
        odom.child_frame_id = "selected/base_link"
        reader.on_odom(odom)
        reader.sample()
        self.assertEqual(samples[-1].status, "LIVE")
        self.assertEqual((samples[-1].pose.frame_id, samples[-1].pose.x), ("selected/odom", 2.0))
