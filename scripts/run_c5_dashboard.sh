#!/usr/bin/env bash
set -euo pipefail

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
  *)
    exec "${compose[@]}" "$@"
    ;;
esac
