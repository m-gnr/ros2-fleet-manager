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

from ros_reader import RobotReader, RosReader
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
        self.node = RosReader([("/selected", Telemetry("robot", "map", "tf", 1))], 20,
                              lambda _, snapshot: self.snapshots.append(snapshot), context=context)
        self.addCleanup(self.node.destroy_node)
        self.reader = self.node.robots["robot"]
        self.clock(20)

    def clock(self, sec):
        msg = Clock()
        msg.clock.sec = sec
        self.node.on_clock(msg)

    def tf(self, *edges):
        self.reader.on_tf(TFMessage(transforms=list(edges)))

    def test_ros_endpoints_and_chain(self):
        self.assertEqual(list(self.node.publishers), [])
        self.assertEqual(list(self.node.clients), [])
        self.assertEqual(list(self.node.services), [])
        self.assertEqual({sub.topic_name for sub in self.node.subscriptions}, {"/clock", "/selected/tf"})
        self.tf(edge("map", "other/odom", 20, 99), edge("other/odom", "other/base_link", 20, 99))
        self.node.sample()
        self.assertEqual(self.snapshots[-1].status, "NO_DATA")
        self.tf(edge("selected/odom", "selected/base_link", 20, 2))
        self.node.sample()
        self.assertEqual(self.snapshots[-1].status, "FRAME_ERROR")
        self.tf(edge("map", "selected/odom", 20, 5))
        self.node.sample()
        self.assertEqual(self.snapshots[-1].status, "LIVE")
        self.assertEqual(self.snapshots[-1].pose.x, 7)

    def test_bad_parent_and_rewind_flush_tf(self):
        self.tf(edge("map", "selected/odom", 20, 5),
                edge("selected/odom", "selected/base_link", 20, 2),
                edge("other/odom", "selected/base_link", 20, 99))
        self.node.sample()
        self.assertEqual(self.snapshots[-1].status, "FRAME_ERROR")
        self.clock(1)
        self.tf(edge("selected/odom", "selected/base_link", 20, 99))
        self.assertIsNone(self.reader.latest)
        self.tf(edge("selected/odom", "selected/base_link", 1, 4))
        self.assertEqual(self.reader.resolve_tf(monotonic_ns()), (None, True))
        self.tf(edge("map", "selected/odom", 1, 3))
        self.node.sample()
        self.assertEqual((self.snapshots[-1].epoch, self.snapshots[-1].pose.stamp_ns,
                          self.snapshots[-1].pose.x), (1, NS, 7))

    def test_diagnostic_odometry_requires_its_own_frames(self):
        reader = RobotReader("/selected", Telemetry("robot", "selected/odom", "diagnostic_odom", 1))
        reader.clock(20 * NS, monotonic_ns())
        odom = Odometry()
        odom.header.stamp.sec = 20
        odom.header.frame_id = "other/odom"
        odom.child_frame_id = "other/base_link"
        odom.pose.pose.orientation.w = 1.0
        odom.pose.pose.position.x = 2.0
        reader.on_odom(odom)
        self.assertEqual(reader.sample(monotonic_ns()).status, "FRAME_ERROR")

        odom.header.frame_id = "selected/odom"
        odom.child_frame_id = "selected/base_link"
        reader.on_odom(odom)
        result = reader.sample(monotonic_ns())
        self.assertEqual(result.status, "LIVE")
        self.assertEqual((result.pose.frame_id, result.pose.x), ("selected/odom", 2.0))

    def test_two_isolated_buffers_and_shared_clock_rewind(self):
        snapshots = {}
        node = RosReader([(f"/r{i}", Telemetry(f"r{i}", "map", "tf", 1)) for i in (1, 2)],
                         20, snapshots.__setitem__, context=self.node.context)
        self.addCleanup(node.destroy_node)
        self.assertEqual({sub.topic_name for sub in node.subscriptions}, {"/clock", "/r1/tf", "/r2/tf"})
        msg = Clock()
        msg.clock.sec = 20
        node.on_clock(msg)
        first, second = node.robots.values()
        first.on_tf(TFMessage(transforms=[
            edge("map", "r2/odom", 20, 999), edge("r2/odom", "r2/base_link", 20, 999),
            edge("map", "r1/odom", 20, 1), edge("r1/odom", "r1/base_link", 20, 2),
        ]))
        node.sample()
        self.assertEqual(snapshots["r1"].pose.x, 3)
        self.assertEqual(snapshots["r2"].status, "NO_DATA")
        second.on_tf(TFMessage(transforms=[
            edge("map", "r2/odom", 20, 10), edge("r2/odom", "r2/base_link", 20, 20),
        ]))
        node.sample()
        self.assertEqual(snapshots["r2"].pose.x, 30)
        # Break only the first frame chain. Correct odometry cannot clear a bad map edge.
        first.on_tf(TFMessage(transforms=[edge("other", "r1/odom", 20, 999)]))
        node.sample()
        self.assertEqual((snapshots["r1"].status, snapshots["r2"].status), ("FRAME_ERROR", "LIVE"))
        msg.clock.sec = 2
        node.on_clock(msg)
        self.assertEqual([(s.epoch, s.status, s.pose) for s in snapshots.values()],
                         [(1, "NO_DATA", None), (1, "NO_DATA", None)])
        self.assertTrue(all(reader.latest is None for reader in node.robots.values()))
