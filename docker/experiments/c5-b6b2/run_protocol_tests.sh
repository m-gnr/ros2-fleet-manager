set -e
source /opt/ros/humble/setup.bash
cd /repo
colcon --log-base /tmp/b6b2/log build --base-paths interfaces/fleet_interfaces --build-base /tmp/b6b2/build --install-base /tmp/b6b2/install --event-handlers console_cohesion+ > /tmp/b6b2-build.log 2>&1 || { tail -70 /tmp/b6b2-build.log; exit 1; }
source /tmp/b6b2/install/setup.bash
export PYTHONPATH=/repo:/repo/ros2_ws/src/fleet_robot_executor:${PYTHONPATH:-}
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python3 -m pytest -p no:cacheprovider -q tests/test_traffic_protocol.py tests/test_traffic_core.py tests/test_traffic_protocol_ros2.py tests/test_executor_lifecycle_integration.py
