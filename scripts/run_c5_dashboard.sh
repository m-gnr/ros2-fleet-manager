#!/usr/bin/env bash
set -euo pipefail

DDS_TEST_PAYLOAD="${DDS_TEST_PAYLOAD:-c5-launch-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')}"
export DDS_TEST_PAYLOAD
compose=(
  docker compose -p "${DDS_TEST_PAYLOAD:?Set a unique validation project name}"
  -f docker/compose/docker-compose.dds.yml
  -f docker/compose/docker-compose.simulation-check.yml
  -f docker/compose/docker-compose.simulation-c3-3-3.yml
  -f docker/compose/docker-compose.simulation-c4-1.yml
  -f docker/compose/docker-compose.simulation-c4-2.yml
  -f docker/compose/docker-compose.simulation-c4-3.yml
  -f docker/compose/docker-compose.simulation-c4-4.yml
  -f docker/compose/docker-compose.simulation-c4-5.yml
  -f docker/compose/docker-compose.simulation-c5.yml
)

if [[ -n ${C5_SCENE_PORT:-} ]]; then
  compose+=(-f docker/compose/docker-compose.simulation-c5-3d.yml)
fi

export C45_PROFILE=charging
args=()
allow_concurrent=0
for arg in "$@"; do
  if [[ "$arg" == --allow-concurrent-simulation ]]; then
    allow_concurrent=1
  else
    args+=("$arg")
  fi
done

case "${1:-}" in
  api)
    exec "${compose[@]}" exec -T backend bash -ec '
      exec 9>/run/fleet-dashboard/api.lock
      flock -n 9
      echo "$$" > /run/fleet-dashboard/api.pid
      cd /workspace
      scene=()
      if [[ -n ${C5_SCENE_PORT:-} ]]; then
        scene=(--scene-port "$C5_SCENE_PORT" --fleet /config/fleet.yaml)
      fi
      exec python3 -m backend.dashboard.api --container-bind --snapshot "$C5_SNAPSHOT_PATH" \
        --port "$C5_API_PORT" --origin "$C5_UI_ORIGIN" "${scene[@]}"
    '
    ;;
  stop-api)
    exec "${compose[@]}" exec -T backend bash -ec '
      pid=$(cat /run/fleet-dashboard/api.pid)
      [[ $(tr "\000" " " < "/proc/$pid/cmdline") == *"backend.dashboard.api "* ]]
      kill -TERM "$pid"
    '
    ;;
  demo)
    guard=(python3 scripts/c5_launch_guard.py --workspace "$PWD")
    if (( allow_concurrent )); then
      guard+=(--allow-concurrent-simulation)
    fi
    guard+=(-- python3 scripts/c5_demo_start.py "$PWD")
    exec "${guard[@]}"
    ;;
  *)
    case "${args[0]:-}" in
      up|create|start|restart|run)
        guard=(python3 scripts/c5_launch_guard.py --workspace "$PWD")
        if (( allow_concurrent )); then
          guard+=(--allow-concurrent-simulation)
        fi
        guard+=(-- "${compose[@]}" "${args[@]}")
        exec "${guard[@]}"
        ;;
    esac
    exec "${compose[@]}" "${args[@]}"
    ;;
esac
