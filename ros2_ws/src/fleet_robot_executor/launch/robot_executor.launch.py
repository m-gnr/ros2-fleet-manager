"""ROS 2 launch file for fleet_robot_executor."""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    fleet_config_arg = DeclareLaunchArgument(
        "fleet_config_path",
        default_value="config/fleet.yaml",
        description="Path to fleet.yaml configuration file",
    )
    robot_id_arg = DeclareLaunchArgument(
        "robot_id",
        default_value="robot_1",
        description="ID of the robot in fleet.yaml to execute",
    )
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation time if true",
    )
    robot_namespace_arg = DeclareLaunchArgument(
        "robot_namespace",
        default_value="",
        description="Optional namespace override for the robot executor",
    )

    executor_node = Node(
        package="fleet_robot_executor",
        executable="robot_executor_node",
        name="robot_executor",
        output="screen",
        parameters=[
            {
                "fleet_config_path": LaunchConfiguration("fleet_config_path"),
                "robot_id": LaunchConfiguration("robot_id"),
                "use_sim_time": LaunchConfiguration("use_sim_time"),
                "robot_namespace": LaunchConfiguration("robot_namespace"),
            }
        ],
    )

    return LaunchDescription(
        [
            fleet_config_arg,
            robot_id_arg,
            use_sim_time_arg,
            robot_namespace_arg,
            executor_node,
        ]
    )
