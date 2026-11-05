"""Test-only entry point: used only with a freshly created C3.3.3 Gazebo world.

Never install this as a production executable or use it to resume a scenario.
"""
from fleet_robot_executor.node import main

if __name__ == "__main__":
    main(_test_reset_verified=True)
