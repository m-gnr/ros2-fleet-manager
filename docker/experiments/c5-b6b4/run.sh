#!/bin/bash
set -euo pipefail
: "${ROS_DOMAIN_ID:?Set an isolated test ROS_DOMAIN_ID}"
set +u
source /opt/ros/humble/setup.bash
set -u
cd /repo
export PYTHONPATH=/repo:/repo/ros2_ws/src/fleet_robot_executor:/repo/docker/experiments/c5-b6b4:${PYTHONPATH:-}
export PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_LOCALHOST_ONLY=1
export IGN_PARTITION="b6b4_${ROS_DOMAIN_ID}_$$"
python3 -m pytest -p no:cacheprovider -q -s docker/experiments/c5-b6b4/test_ros_topology.py tests/test_traffic_motion_gate.py tests/test_b6b4_topology.py
