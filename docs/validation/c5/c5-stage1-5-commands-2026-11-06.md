# C5 / Aşama 1.5 — Doğrulama komutları

[Sonuç raporu](c5-stage1-5-validation-2026-11-06.md) · [Teknik tasarım](../../design/c5-3d-operations.md). Komutlar aksi belirtilmedikçe entegrasyon worktree kökünden çalıştırılır. Chrome ve Docker Desktop hostta çalışır. Katmanlar mevcut C4.5 ARM64 Fortress image'larını kullanır.

## Git tabanı ve image hazırlığı

İlk komutlar ana worktree kökünde çalıştırıldı.

```sh
git status --short
git branch -avv
git worktree list
git rev-parse HEAD
git rev-parse origin/main
git rev-parse feat/c5-readonly-dashboard
git rev-parse feat/fleet-visualizer-nav2-routes
git worktree add -b feat/c5-3d-operations-dashboard \
  ../ros2-fleet-manager-c5-3d-dashboard 76a80abb5d35ca5a4e7005b145d0c83ce3104b0e
```

Entegrasyon worktree'sinde çalıştırın. [Compose image önkoşulları](../../../docker/compose/README.md)

```sh
docker build -f fleet-visualizer/bridge/Dockerfile -t fleet-visualizer-stage4:humble .
docker build -f docker/simulation-c5/Dockerfile -t ros2-fleet-c5-validation:humble-fortress .
npm --prefix frontend ci
npm --prefix frontend run build
```

## İki robotlu Fortress ve Chrome

Boş bir kanıt dizini, boş loopback portları ve ayrı DDS domain seçin. Ayrı terminaller aynı ortam değişkenlerini kullanır. Aşağıdakiler son kabul koşusunun değerleridir.

```sh
export DDS_TEST_PAYLOAD=fleet-c5-scene-final
export ROS_DOMAIN_ID=117
export C5_API_PORT=18868 C5_UI_PORT=18867 C5_SCENE_PORT=18869
export C5_UI_ORIGIN="http://127.0.0.1:$C5_UI_PORT"
export C43_EVIDENCE_DIR=/tmp/fleet-c5-scene-final
mkdir -p "$C43_EVIDENCE_DIR/gates"
scripts/run_c5_dashboard.sh config --format json > "$C43_EVIDENCE_DIR/compose.json"
scripts/run_c5_dashboard.sh create --no-build
scripts/run_c5_dashboard.sh start simulation scene
```

Vite için ayrı terminalde `npm --prefix frontend run preview` çalıştırın. Elle izlemek için backend konteyneri başlatıldıktan sonra ayrı terminalde `scripts/run_c5_dashboard.sh api` kullanın. Otomatik kabul API yaşam döngüsünü kendisi yönettiği için otomasyonla aynı anda elle API başlatmayın.

İsteğe bağlı bağımsız ROS referanslarını Chrome'dan önce başlatın. Bu çağrılar Aşama 4 doğrulama araçlarını kaynak commit'ten okur. Son kabulde karşılaştırma için ikisi de çalıştırıldı.

```sh
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
node frontend/tests/live-acceptance.mjs
docker exec "$DDS_TEST_PAYLOAD-simulation-1" bash -ec \
  'source /opt/ros/humble/setup.bash; ros2 node info /fleet_visualizer --no-daemon --include-hidden' \
  > "$C43_EVIDENCE_DIR/bridge-graph.txt"
docker wait "$DDS_TEST_PAYLOAD-backend-1"
scripts/run_c5_dashboard.sh stop scene simulation
docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  "$DDS_TEST_PAYLOAD-backend-1" "$DDS_TEST_PAYLOAD-simulation-1" "$DDS_TEST_PAYLOAD-scene-1"
scripts/run_c5_dashboard.sh logs --no-color > "$C43_EVIDENCE_DIR/compose.log"
scripts/run_c5_dashboard.sh down
sqlite3 "$C43_EVIDENCE_DIR/c5-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
python3 docker/simulation-c5/compare_scene_evidence.py "$C43_EVIDENCE_DIR"
```

## Regresyonlar

Host Python ve C5 Chrome seçkileri. Node bağımlılıkları lockfile ile kurulur. ROS bağımlılığı olan host testlerinin ayrı Humble koşusu aşağıdadır.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-c1.txt -r requirements-c5-test.txt
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator
.venv/bin/python -m fleet_config config/fleet.yaml
.venv/bin/python -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test
C5_UI_PORT=18887 C5_API_PORT=18888 npm --prefix frontend test
npm --prefix frontend audit
git diff --check
```

Bu koşuda host Python için C5 Aşama 1 worktree'sindeki hazır sanal ortam kullanıldı. Aşama 1'in beş Chrome testi o worktree'de kendi portlarıyla tekrar çalıştı. Visualizer frontend seçkisi ve derlemesi, bağımsız `feat/fleet-visualizer-nav2-routes` worktree'sinde çalıştı.

```sh
C5_UI_PORT=18877 C5_API_PORT=18878 npm --prefix frontend test
# Visualizer worktree kökünde
npm --prefix fleet-visualizer/frontend run test
npm --prefix fleet-visualizer/frontend run build
```

Humble/CycloneDDS ürün testleri, C2.3/C3.3.3 config kontrolleri ve Visualizer köprüsü. Gerçek ROS testleri için ARM64 image kullanılır.

```sh
docker run --rm --name fleet-c5-scene-ros-regression \
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

C3.3.3 güvenlik profilleri için domain 118 kullanıldı. Her çağrıdan sonra üç C3.3.3 katmanıyla Compose `down` çalıştırıldı.

```sh
COMPOSE_PROJECT_NAME=fleet-c5-scene-c333 python3 scripts/run_c3_3_3.py \
  --domain 118 --token fleet-c5-scene-c333
COMPOSE_PROJECT_NAME=fleet-c5-scene-high python3 scripts/run_c3_3_3.py \
  --domain 118 --token fleet-c5-scene-high --high-preemption
```

C4.5 enerji koşusu `fleet-c5-scene-energy` projesi, DDS domain 119 ve [C4.5 enerji komutları](../c4/c4-5-commands-2026-11-06.md) ile yürütüldü. Şarj seçkisi C5'in canlı koşusunun içindedir. Güncellenen SVG'ler [depo Mermaid teması ve CLI sürümü](../organization/organization-commands-2026-10-26.md#mermaid-ve-svg-üretimi) ile üretildi ve XML olarak ayrıştırıldı.
