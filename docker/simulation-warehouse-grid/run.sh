#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
export PYTHONPATH=/workspace:${PYTHONPATH:-}
cd /workspace
profile=${2:-config/fleet.warehouse-grid.yaml}
scenario=$1
out=/evidence/$scenario
mkdir -p "$out"
world_scenario=$scenario
[[ "$scenario" != inspection ]] || world_scenario=delivery
ready=$(mktemp)
python3 docker/simulation-warehouse-grid/serve.py "$profile" "$out" "$world_scenario" --ready "$ready" > "$out/fortress.log" 2>&1 &
server=$!
cleanup() {
  kill -TERM "$server" 2>/dev/null || true
  wait "$server"
  rm "$ready"
}
trap cleanup EXIT
for attempt in $(seq 1 100); do
  [[ -s "$ready" ]] && break
  kill -0 "$server"
  sleep .1
done
test -s "$ready"
if [[ "$scenario" == inspection ]]; then
  python3 docker/simulation-warehouse-grid/inspect_route.py "$profile" "$out/inspection.json"
else
  python3 docker/simulation-warehouse-grid/probe.py "$profile" "$out" "$scenario"
fi
