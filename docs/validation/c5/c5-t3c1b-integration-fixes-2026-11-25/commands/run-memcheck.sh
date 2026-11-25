#!/usr/bin/env bash
set -u
scenario=${1:?case};run=${2:?new run};index=${3:?domain}
name="c5-1b-recovery-$run"
docker run --rm --init --name "$name" --ulimit core=-1 --network bridge --workdir /workspace \
 --env C5_1B_DIAGNOSTICS=1 --env C5_1B_MEMCHECK=1 --env ROS_DOMAIN_ID="$index" --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
 --env ROS_LOCALHOST_ONLY=0 --env IGN_PARTITION="$name" \
 -v "$PWD:/workspace:ro" -v /tmp/c5-t3c1b-recovery-20261124/ros-debug:/build:ro \
 -v /tmp/c5-t3c1b-native-20261124-a4:/b6b7-native:ro \
 -v /tmp/c5-t3c1b-recovery-20261124:/evidence c5-t3c1b-memcheck:local bash -ec '
 source /opt/ros/humble/setup.bash
 source /build/install/local_setup.bash
 export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
 python3 docker/experiments/c5-t3c1b/live.py config/fleet.warehouse-30x18.yaml "/evidence/$1" --case "$2"
 ' recovery "$run" "$scenario" > "/tmp/c5-t3c1b-recovery-20261124/$run.cli.log" 2>&1
result=$?
printf '%s\t%s\t%s\t%s\n' "$scenario" "$run" "$index" "$result" >> /tmp/c5-t3c1b-recovery-20261124/diagnostics.tsv
exit "$result"
