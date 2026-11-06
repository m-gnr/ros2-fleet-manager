# C5 / Aşama 1.6 doğrulama komutları

[Sonuç raporu](c5-stage1-6-validation-2026-11-06.md) · [Aşama 1.5 komutları](c5-stage1-5-commands-2026-11-06.md) · [Compose katman kılavuzu](../../../docker/compose/README.md)

Komutlar ilgili Git worktree kökünde çalıştırıldı. Chrome hostta, Humble/CycloneDDS/Fortress Docker Desktop üzerinde ARM64 image'larında çalıştı.

## Git tabanı ve üretim build'i

Ana worktree'de aşağıdaki bilgiler alındı. GitHub'daki Aşama 1.5 dal ucu ile yerel dal ucu aynı tam SHA'yı döndürdü.

```sh
git status --short
git branch -avv
git worktree list
git log -1 --oneline
git rev-parse HEAD origin/main
git ls-remote origin refs/heads/main refs/heads/feat/c5-3d-operations-dashboard refs/heads/feat/c5-dashboard-ui-polish
git worktree add -b feat/c5-dashboard-ui-polish \
  ../ros2-fleet-manager-c5-ui-polish 72e500eb84e0409f220779adab5035a2bcf28f0f
```

Yeni worktree'de, kaynak değişikliğinden önce Aşama 1.5 build'i alındı ve ayrı çıktı dizininde saklandı. Aşama 1.6 üretim build'i aynı lockfile ile yeniden alındı.

```sh
npm --prefix frontend ci
npm --prefix frontend run build
mkdir -p /tmp/fleet-c5-ui-baseline
cp -R frontend/dist /tmp/fleet-c5-ui-baseline/dist
C5_API_PORT=18968 C5_UI_PORT=18967 npm --prefix frontend run preview -- --outDir /tmp/fleet-c5-ui-baseline/dist
# Aşama 1.6 kaynaklarıyla ayrı terminalde
npm --prefix frontend run build
C5_API_PORT=18978 C5_UI_PORT=18977 npm --prefix frontend run preview
```

## Canlı kabul

Her koşuda boş bir kanıt dizini ve boş DDS domain kullanıldı. Aşağıdaki değerler son Aşama 1.6 koşusuna aittir. Aşama 1.5 karşılaştırması `fleet-c5-ui-before` projesi ve DDS domain 124 ile çalıştı. Preview portu 18967, API portu 18968, sahne portu 18969 ve kanıt dizini `/tmp/fleet-c5-ui-before` kullanıldı. `C5_REQUIRE_COMPACT=1` Aşama 1.6'ya özgü masaüstü boyut ve canlı model seçimi kontrollerini açar.

```sh
export DDS_TEST_PAYLOAD=fleet-c5-ui-after ROS_DOMAIN_ID=125
export C5_UI_PORT=18977 C5_API_PORT=18978 C5_SCENE_PORT=18979
export C5_UI_ORIGIN="http://127.0.0.1:$C5_UI_PORT"
export C43_EVIDENCE_DIR=/tmp/fleet-c5-ui-after C5_REQUIRE_COMPACT=1
mkdir -p "$C43_EVIDENCE_DIR/gates"
scripts/run_c5_dashboard.sh config --format json > "$C43_EVIDENCE_DIR/compose.json"
scripts/run_c5_dashboard.sh create --no-build
scripts/run_c5_dashboard.sh start simulation scene

git show f3e3901:fleet-visualizer/validation/nav2_reference.py |
  docker exec -i "$DDS_TEST_PAYLOAD-simulation-1" bash -c \
    'source /opt/ros/humble/setup.bash; exec python3 -u - 240' \
  > "$C43_EVIDENCE_DIR/nav2.jsonl" 2> "$C43_EVIDENCE_DIR/nav2.err" &
for id in robot_1 robot_2; do
  git show f3e3901:fleet-visualizer/validation/ros_reference.py |
    docker exec -i "$DDS_TEST_PAYLOAD-simulation-1" bash -c \
      'source /opt/ros/humble/setup.bash; exec timeout -s INT 240 python3 -u - --namespace "/$1" "$1/base_link"' -- "$id" \
    > "$C43_EVIDENCE_DIR/tf-$id.jsonl" 2> "$C43_EVIDENCE_DIR/tf-$id.err" &
done

scripts/run_c5_dashboard.sh start backend
node frontend/tests/live-acceptance.mjs > "$C43_EVIDENCE_DIR/chrome.log" 2>&1
docker exec "$DDS_TEST_PAYLOAD-simulation-1" bash -ec \
  'source /opt/ros/humble/setup.bash; ros2 node info /fleet_visualizer --no-daemon --include-hidden' \
  > "$C43_EVIDENCE_DIR/bridge-graph.txt"
docker wait "$DDS_TEST_PAYLOAD-backend-1" > "$C43_EVIDENCE_DIR/backend-exit.txt"
scripts/run_c5_dashboard.sh stop backend scene simulation
docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  "$DDS_TEST_PAYLOAD-backend-1" "$DDS_TEST_PAYLOAD-simulation-1" "$DDS_TEST_PAYLOAD-scene-1" > "$C43_EVIDENCE_DIR/shutdown.txt"
scripts/run_c5_dashboard.sh logs --no-color > "$C43_EVIDENCE_DIR/compose.log"
scripts/run_c5_dashboard.sh down
sqlite3 "$C43_EVIDENCE_DIR/c5-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
python3 docker/simulation-c5/compare_scene_evidence.py "$C43_EVIDENCE_DIR"
```

## Regresyon

Host Python seçkisi için Aşama 1 worktree'sindeki hazır sanal ortam kullanıldı. Üretim önizlemesi açıkken Playwright aynı porttaki sunucuyu kullanır. Fixture WebSocket verileri Playwright koşusuna özeldir.

```sh
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator
../ros2-fleet-manager-c5-dashboard/.venv/bin/python -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test
../ros2-fleet-manager-c5-dashboard/.venv/bin/python -m pytest -q tests/test_c5_dashboard.py
C5_UI_PORT=18977 C5_API_PORT=18978 C5_BROWSER_TEST_DIR=/tmp/fleet-c5-ui-regression/playwright-final \
  npm --prefix frontend test -- --workers=1
git diff --check
```

Aşama 4 Visualizer testleri kendi worktree kökünde çalıştırıldı.

```sh
npm --prefix fleet-visualizer/frontend run test
```

```sh
docker run --rm --name fleet-c5-ui-ros-regression \
  -e ROS_DOMAIN_ID=66 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" -w /work --entrypoint bash \
  ros2-fleet-c5-validation:humble-fortress -c '
set -e
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:$PYTHONPATH
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros tests/ ros2_ws/src/fleet_robot_executor/test
for test in docker/simulation-c2-3/test_config.py docker/simulation-c3-3-3/test_config.py; do
  python3 -m pytest -q -p no:cacheprovider -p no:launch_testing -p no:launch_ros "$test"
done
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/repo:/repo/fleet-visualizer/bridge:$PYTHONPATH \
  python3 -m unittest discover -s fleet-visualizer/bridge/tests -p "*_checks.py"
'
```
