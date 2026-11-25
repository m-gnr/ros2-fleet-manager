#!/usr/bin/env bash
set -u
root=$(pwd -P)
ledger=/tmp/c5-t3c1b-live-matrix-20261124.tsv
printf 'case\trun\tdomain\texit\n' > "$ledger"
index=190
for scenario in tf-loss odometry-loss amcl-loss controller-inactive observation-loss health-context health-session health-old worker-stop worker-kill ipc-loss replan cancel; do
  run="$scenario-final1"
  name="c5-t3c1b-$run"
  docker run --rm --init --name "$name" --network bridge --workdir /workspace \
    --env ROS_DOMAIN_ID="$index" --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp --env ROS_LOCALHOST_ONLY=0 --env IGN_PARTITION="$name" \
    -v "$root:/workspace:ro" -v /tmp/c5-t3c1b-ros-build-20261124:/build:ro \
    -v /tmp/c5-t3c1b-native-20261124-a4:/b6b7-native:ro -v /tmp/c5-t3c1b-live-20261124:/evidence \
    c5-b6b5-build:local bash -ec 'source /opt/ros/humble/setup.bash
source /build/install/local_setup.bash
export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
python3 docker/experiments/c5-t3c1b/live.py config/fleet.warehouse-30x18.yaml "/evidence/$1" --case "$2"' t3c1b "$run" "$scenario" > "/tmp/c5-t3c1b-$run.log" 2>&1
  result=$?
  printf '%s\t%s\t%s\t%s\n' "$scenario" "$run" "$index" "$result" >> "$ledger"
  index=$((index+1))
done
