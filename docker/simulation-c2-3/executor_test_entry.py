"""Test-only entry point: used only with a freshly created C2.3 Gazebo world.

Never install this as a production executable or use it to resume a scenario.
"""
import rclpy
from rclpy.executors import MultiThreadedExecutor
from fleet_robot_executor.node import RobotExecutorNode

rclpy.init()
node = RobotExecutorNode(_test_reset_verified=True)
executor = MultiThreadedExecutor()
executor.add_node(node)
try:
    executor.spin()
finally:
    node.destroy_node()
    executor.shutdown()
    rclpy.shutdown()
