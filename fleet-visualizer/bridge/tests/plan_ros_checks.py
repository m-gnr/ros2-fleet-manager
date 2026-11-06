from time import monotonic, monotonic_ns, sleep
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

try:
    from action_msgs.msg import GoalStatus, GoalStatusArray
    from geometry_msgs.msg import PoseStamped
    from nav_msgs.msg import Path
    from rclpy import init
    from rclpy.context import Context
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rosgraph_msgs.msg import Clock
except ImportError as error:
    raise unittest.SkipTest("ROS 2 Humble is required") from error

from observed_plan import ObservedPlan
from ros_reader import PlannerReader, RosReader
from telemetry import NS, Telemetry


def wait_for(check, executor):
    end = monotonic() + 4
    while not check() and monotonic() < end:
        executor.spin_once(timeout_sec=0.01)
        sleep(0.005)
    if not check():
        raise AssertionError("Timed out waiting for DDS graph or sample")


class PlanRosChecks(unittest.TestCase):
    def test_verified_namespaces_writer_loss_and_clock_reset(self):
        context = Context()
        init(args=[], context=context)
        self.addCleanup(context.shutdown)
        states = {id: Telemetry(id, "map", "tf", 1) for id in ("a", "b")}
        reader = RosReader([(f"/{id}", state) for id, state in states.items()], 20,
                           lambda *_: None, context=context,
                           plan_topics={id: f"/{id}/plan" for id in states})
        self.addCleanup(reader.destroy_node)
        nodes = {id: Node("planner_server", namespace=f"/{id}", context=context) for id in states}
        for node in nodes.values():
            self.addCleanup(node.destroy_node)
        executor = SingleThreadedExecutor(context=context)
        self.addCleanup(executor.shutdown)
        executor.add_node(reader)
        # The timer normally also requires live TF. Test Path ingestion independently.
        for timer in reader.timers:
            timer.cancel()
        writers = {id: node.create_publisher(Path, f"/{id}/plan", 1) for id, node in nodes.items()}
        clock = Clock()
        clock.clock.sec = 20
        reader.on_clock(clock)
        for planner in reader.planners.values():
            wait_for(planner.check_writer, executor)
        self.assertEqual(list(reader.publishers) + list(reader.clients) + list(reader.services), [])
        self.assertEqual({sub.topic_name for sub in reader.subscriptions}, {
            "/clock", "/a/tf", "/b/tf", "/a/plan", "/b/plan",
            "/a/navigate_to_pose/_action/status", "/b/navigate_to_pose/_action/status",
        })

        for x, writer in enumerate(writers.values()):
            message = Path()
            message.header.frame_id = "map"
            message.header.stamp.sec = 20
            pose = PoseStamped(header=message.header)
            pose.pose.position.x = float(x)
            pose.pose.orientation.w = 1.0
            message.poses = [pose, pose]
            wait_for(lambda: writer.get_subscription_count() == 1, executor)
            writer.publish(message)
        wait_for(lambda: all(p.buffer.plan for p in reader.planners.values()), executor)
        a, b = reader.planners.values()
        self.assertEqual((a.buffer.plan.points[0][0], b.buffer.plan.points[0][0]), (0, 1))

        wrong = nodes["b"].create_publisher(Path, "/a/plan", 1)
        wait_for(lambda: len(reader.get_publishers_info_by_topic("/a/plan")) == 2, executor)
        self.assertIsNone(a.sample(monotonic_ns(), True))
        self.assertIsNotNone(b.sample(monotonic_ns(), True))
        nodes["b"].destroy_publisher(wrong)
        nodes["b"].destroy_publisher(writers["b"])
        wait_for(lambda: len(reader.get_publishers_info_by_topic("/b/plan")) == 0, executor)
        self.assertFalse(b.check_writer())
        self.assertIsNone(b.buffer.plan)

        clock.clock.sec = 1
        reader.on_clock(clock)
        self.assertEqual(a.buffer.cutoff, 0)
        self.assertEqual(states["a"].clock_observation, (1, NS))


    def test_navigation_transition_clears_observation_without_setting_ownership(self):
        node = Mock()
        node.get_publishers_info_by_topic.return_value = [
            SimpleNamespace(node_name="bt_navigator", node_namespace="/a"),
        ]
        reader = PlannerReader(node, "/a", "/a/plan", Telemetry("a", "map", "tf", 1))
        status = GoalStatus(status=GoalStatus.STATUS_EXECUTING)
        observation = ObservedPlan(NS, monotonic_ns(), ((1.0, 2.0), (3.0, 4.0)))
        reader.buffer.plan = observation
        reader.on_navigation(GoalStatusArray(status_list=[status]))
        self.assertIsNone(reader.buffer.plan)
        reader.buffer.plan = observation
        reader.on_navigation(GoalStatusArray(status_list=[status]))
        self.assertIs(reader.buffer.plan, observation)
        status.status = GoalStatus.STATUS_CANCELING
        reader.on_navigation(GoalStatusArray(status_list=[status]))
        self.assertIsNone(reader.buffer.plan)
        reader.buffer.plan = observation
        status.status = GoalStatus.STATUS_CANCELED
        reader.on_navigation(GoalStatusArray(status_list=[status]))
        self.assertIsNone(reader.buffer.plan)
