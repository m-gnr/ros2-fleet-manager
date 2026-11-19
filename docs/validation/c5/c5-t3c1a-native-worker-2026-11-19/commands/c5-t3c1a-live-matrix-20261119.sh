#!/usr/bin/env bash
set -u
root=/Users/murat/develop/ros2-fleet-manager-demo
cd "$root"
index=184
for case in worker-stop worker-kill ipc-loss duplicate wrong-context wrong-session corrupt delayed; do
 run="${case}-final1"
 name="c5-t3c1a-$run"
 docker run --rm --init --name "$name" --network bridge --workdir /workspace \
  --env ROS_DOMAIN_ID="$index" --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp --env ROS_LOCALHOST_ONLY=0 --env IGN_PARTITION="$name" \
  -v "$root:/workspace:ro" -v /tmp/c5-t2-build-20261118:/build:ro \
  -v /tmp/c5-t3c1a-native-20261119-a5:/b6b7-native:ro -v /tmp/c5-t3c1a-live-20261119:/evidence \
  c5-b6b5-build:local bash -ec '
   source /opt/ros/humble/setup.bash
   source /build/install/local_setup.bash
   export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
   python3 docker/experiments/c5-t3c1a/live.py config/fleet.warehouse-30x18.yaml "/evidence/$1" --case "$2"
  ' t3c1a "$run" "$case" > "/tmp/c5-t3c1a-$run.log" 2>&1
 result=$?
 printf '%s\t%s\t%s\n' "$run" "$index" "$result" | tee -a /tmp/c5-t3c1a-live-matrix-20261119.tsv
 if [ "$result" -ne 0 ]; then tail -22 "/tmp/c5-t3c1a-$run.log"; exit "$result"; fi
 index=$((index+1))
done
