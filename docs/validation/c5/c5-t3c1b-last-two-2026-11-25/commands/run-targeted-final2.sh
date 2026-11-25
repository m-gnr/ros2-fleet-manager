#!/usr/bin/env bash
set -u
ledger=/tmp/c5-t3c1b-last-two-20261125/targeted-final2.tsv
printf 'case\trun\tdomain\texit\n' > "$ledger"
index=219
for scenario in odometry-loss observation-loss; do
 run="$scenario-targeted-final2";name="c5-1b-two-$run"
 docker run --rm --init --name "$name" --network bridge --workdir /workspace \
  --env C5_1B_DIAGNOSTICS=1 --env ROS_DOMAIN_ID="$index" --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp --env ROS_LOCALHOST_ONLY=0 --env IGN_PARTITION="$name" \
  --env C5_1B_CLEANUP_FIX_LIBRARY=/build/lifecycle/libc5-costmap-cleanup.so \
  -v /tmp/c5-t3c1b-last-two-20261125/source-final2:/workspace:ro \
  -v /tmp/c5-t3c1b-recovery-20261124/ros-fixed-a4:/build:ro \
  -v /tmp/c5-t3c1b-last-two-20261125/native-final:/b6b7-native:ro \
  -v /tmp/c5-t3c1b-last-two-20261125:/evidence c5-b6b5-build:local bash -ec '
  source /opt/ros/humble/setup.bash
  source /build/install/local_setup.bash
  export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
  python3 docker/experiments/c5-t3c1b/live.py config/fleet.warehouse-30x18.yaml "/evidence/$1" --case "$2"
 ' targeted "$run" "$scenario" > "/tmp/c5-t3c1b-last-two-20261125/$run.cli.log" 2>&1
 result=$?;printf '%s\t%s\t%s\t%s\n' "$scenario" "$run" "$index" "$result" >> "$ledger"
 index=$((index+1))
done
