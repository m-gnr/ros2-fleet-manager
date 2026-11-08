#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
export PYTHONPATH=/workspace:${PYTHONPATH:-}
cd /workspace
profile=config/fleet.warehouse-grid.yaml
scenario=$1
out=/evidence/$scenario
mkdir -p "$out"
world_scenario=$scenario
[[ "$scenario" != inspection ]] || world_scenario=delivery
python3 docker/simulation-warehouse-grid/serve.py "$profile" "$out" "$world_scenario" > "$out/fortress.log" 2>&1 &
server=$!
cleanup() {
  kill -TERM "$server" 2>/dev/null || true
  wait "$server"
}
trap cleanup EXIT
if [[ "$scenario" == inspection ]]; then
  python3 docker/simulation-warehouse-grid/inspect_route.py "$profile" "$out/inspection.json"
else
  python3 docker/simulation-warehouse-grid/probe.py "$profile" "$out" "$scenario"
fi
