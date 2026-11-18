#!/usr/bin/env bash
set -u
test ! -e /tmp/c5-t3b-final-runs-v3.tsv || exit 2
while read -r test_case test_run test_domain; do
  test ! -e "/tmp/c5-t3b-${test_run}.log" || exit 2
  docker run --rm --init --name "c5-t3b-final-${test_run}" --network bridge --workdir /workspace \
    --env ROS_DOMAIN_ID="$test_domain" --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp --env ROS_LOCALHOST_ONLY=0 \
    --env IGN_PARTITION="c5-t3b-${test_run}" \
    -v /Users/murat/develop/ros2-fleet-manager-demo:/workspace:ro \
    -v /tmp/c5-t2-build-20261118:/build:ro -v /tmp/c5-t3b-native-20261118-a2:/b6b7-native:ro \
    -v /tmp/c5-t3b-live-20261118:/evidence c5-b6b5-build:local bash -ec '
    source /opt/ros/humble/setup.bash
    source /build/install/local_setup.bash
    export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
    python3 docker/experiments/c5-t3b/live.py config/fleet.warehouse-30x18.yaml "$@"
    ' t3b-run "/evidence/$test_run" --case "$test_case" > "/tmp/c5-t3b-${test_run}.log" 2>&1
  test_exit=$?
  printf '%s\t%s\t%s\n' "$test_run" "$test_domain" "$test_exit" >> /tmp/c5-t3b-final-runs-v3.tsv
  printf 'Finished %s: exit %s\n' "$test_run" "$test_exit"
  if [ "$test_exit" -ne 0 ]; then tail -25 "/tmp/c5-t3b-${test_run}.log"; exit "$test_exit"; fi
done <<'CASES'
replan replan-a3 204
fm-loss fm-loss-a4 205
bridge-loss bridge-loss-a2 206
negative negative-a1 207
update-freeze update-freeze-a3 208
sensor-loss sensor-loss-a2 209
controller-inactive controller-inactive-a2 210
executor-loss executor-loss-a2 211
CASES
