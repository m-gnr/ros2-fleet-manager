#!/usr/bin/env bash
# Isolated acceptance probe; never attach this controlled clock to a running world.
set -euo pipefail
: "${C5_BATTERY_EVIDENCE:?Evidence directory required}"
: "${C5_API_PORT:?API port required}"
: "${C5_BROWSER_ORIGIN:?Exact loopback origin required}"
: "${C5_FLEET_CONFIG:?Authoritative config required}"
: "${FLEET_SIM_BATTERY_TOKEN:?Secret test token required}"
: "${FLEET_SIM_BATTERY_CONTROL:?Explicit simulation opt-in required}"
if [[ "$FLEET_SIM_BATTERY_CONTROL" != 1 || "${ROS_LOCALHOST_ONLY:-}" != 1 ]]; then
  echo 'Probe requires explicit simulation opt-in and localhost-only DDS' >&2
  exit 1
fi
mkdir -p "$C5_BATTERY_EVIDENCE"
python3 docker/simulation-c5/battery_control_probe.py --fleet "$C5_FLEET_CONFIG" \
  --snapshot "$C5_BATTERY_EVIDENCE/live-snapshot.json" > "$C5_BATTERY_EVIDENCE/live-simulator.log" 2>&1 &
probe_pid=$!
python3 -m backend.dashboard.api --fleet "$C5_FLEET_CONFIG" \
  --snapshot "$C5_BATTERY_EVIDENCE/live-snapshot.json" --port "$C5_API_PORT" \
  --container-bind --origin "$C5_BROWSER_ORIGIN" > "$C5_BATTERY_EVIDENCE/live-api.log" 2>&1 &
api_pid=$!
cleanup() {
  kill -TERM "$probe_pid" "$api_pid" 2>/dev/null || true
  wait "$probe_pid" "$api_pid" || true
}
trap cleanup EXIT
trap 'exit 0' TERM INT
wait -n "$probe_pid" "$api_pid"
