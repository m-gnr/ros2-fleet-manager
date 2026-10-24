"""Test-only entry point: used only with a freshly created C3.3.3 Gazebo world.

Never install this as a production executable or use it to resume a scenario.
Strictly conforms to C3.3.1-DEC-07 in-process test seam.
"""
import sys
import rclpy
from rclpy.executors import MultiThreadedExecutor
from fleet_robot_executor.node import RobotExecutorNode


def main():
    rclpy.init(args=sys.argv)
    # Instantiate with test reset verified to open admission in fresh test world
    node = RobotExecutorNode(_test_reset_verified=True)
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        executor.shutdown()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
