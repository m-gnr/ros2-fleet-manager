# Fleet Visualizer doğrulama komutları

6 Kasım 2026. Komutları Visualizer worktree'sinin kökünden çalıştır. DDS domain değerleri bu izole kabul koşularına aittir. [Sonuçlar](report.md).

## Başlangıç ve birim testleri

```sh
git status --short
git branch --show-current
git log -1 --oneline
git rev-parse HEAD
git rev-parse origin/main
git ls-remote origin refs/heads/main

export EVIDENCE=/tmp/fleet-viz-evidence
mkdir -p "$EVIDENCE"
export CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

docker build -t fleet-visualizer:humble -f fleet-visualizer/bridge/Dockerfile .
npm ci --prefix fleet-visualizer/frontend
npm --prefix fleet-visualizer/frontend run test
npm --prefix fleet-visualizer/frontend run build
```

Köprü birim testleri ve ayrı Vite başlatma komutu [Visualizer README](../../../fleet-visualizer/README.md#testler) içinde. Vite'ı Chrome testleri bitene kadar ayrı terminalde açık tut.

## Tek robotlu canlı doğrulama

Ön incelemede C2.3 simulation servisi tek başına çalıştırıldı. Nihai kabulde iki C2.3 servisi birlikte başlatıldı. Bu sayede sürücü AMCL'in açılıştaki ilk poz yayınını aldı.

```sh
export ROS_DOMAIN_ID=84 DDS_TEST_PAYLOAD=fleet-viz-single
compose_single() {
  docker compose -p "$DDS_TEST_PAYLOAD" \
    -f docker/compose/docker-compose.dds.yml \
    -f docker/compose/docker-compose.simulation-check.yml \
    -f docker/compose/docker-compose.simulation-c2-3.yml "$@"
}

compose_single config --format json > "$EVIDENCE/single-config.json"
compose_single create --no-build

docker run -d --name fleet-viz-bridge --init --network fleet-viz-single_dds \
  --env-file config/dds.env -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
  -p 127.0.0.1:8765:8765 --mount "type=bind,src=$PWD/config,dst=/app/config,readonly" \
  fleet-visualizer:humble --robot robot_1 --bind 0.0.0.0 --trace

VISUALIZER_EVIDENCE="$EVIDENCE/single-final" VISUALIZER_CUTS=1 \
  npm --prefix fleet-visualizer/frontend run verify:live &
browser_pid=$!
compose_single up -d --no-build

docker exec -i fleet-viz-single-simulation-1 bash -c \
  'source /opt/ros/humble/setup.bash; exec timeout --signal=INT 220s python3 -u - robot_1/base_link' \
  < fleet-visualizer/validation/ros_reference.py > "$EVIDENCE/ros-single-final.jsonl" &
```

Ön incelemede `source /opt/ros/humble/setup.bash` sonrasında `ros2 run tf2_tools view_frames` geçici dizinde, `ros2 run tf2_ros tf2_echo map robot_1/base_link --ros-args -p use_sim_time:=true` ise süre sınırlı çalıştırıldı. IDL için `source /workspace/install/setup.bash` ile `ros2 topic info --no-daemon -v /robot_1/robot_status` ve `ros2 topic echo --no-daemon --once /robot_1/robot_status` kullanıldı.

Aşağıdaki kesintiyi yalnız izole C2.3 kabul koşusunda ve backend test sürücüsü bittikten sonra uygula. `stale.json`, `ros-recovered.json` ve `disconnected.json` tarayıcı kontrollerinin tamamlanma işaretleridir.

```sh
docker wait fleet-viz-single-backend-1
docker logs fleet-viz-single-backend-1 > "$EVIDENCE/single-final-backend.log" 2>&1
test -s "$EVIDENCE/single-final/moving.json"

tf_pid=$(docker exec fleet-viz-single-simulation-1 pgrep -f '^python3 /opt/simulation-c2-3/tf_helper.py$')
docker exec fleet-viz-single-simulation-1 kill -STOP "$tf_pid"
# Tarayıcı STALE durumunu kaydedene kadar stale.json dosyasını bekle.
docker exec fleet-viz-single-simulation-1 kill -CONT "$tf_pid"
# ros-recovered.json ile yeni bir geçerli ölçüm geldiğini kontrol et.

for sample in 1 2 3 4 5 6 7 8; do
  docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' \
    fleet-viz-single-simulation-1 fleet-viz-bridge
done > "$EVIDENCE/stats-on.txt"

docker stop fleet-viz-bridge
# Tarayıcı DISCONNECTED durumunu disconnected.json dosyasına kaydeder.
for sample in 1 2 3 4 5 6 7 8; do
  docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' \
    fleet-viz-single-simulation-1
done > "$EVIDENCE/stats-off.txt"

docker exec fleet-viz-single-simulation-1 bash -c \
  'source /opt/ros/humble/setup.bash; source /workspace/install/setup.bash; ros2 node list --no-daemon; timeout 8 ros2 topic echo --no-daemon --once /robot_1/robot_status' \
  > "$EVIDENCE/single-alive-after-stop.txt"

docker start fleet-viz-bridge
wait "$browser_pid"
docker stop fleet-viz-bridge fleet-viz-single-simulation-1
docker logs fleet-viz-bridge > "$EVIDENCE/bridge-single-final.log" 2>&1
docker logs fleet-viz-single-simulation-1 > "$EVIDENCE/single-final-simulation.log" 2>&1

for service in fleet-viz-bridge fleet-viz-single-simulation-1 fleet-viz-single-backend-1; do
  docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' "$service"
done
docker rm fleet-viz-bridge
compose_single down

python3 fleet-visualizer/validation/compare.py "$EVIDENCE/single-final" \
  "$EVIDENCE/ros-single-final.jsonl" "$EVIDENCE/bridge-single-final.log"
```

## C4.5 enerji profili ve izolasyon

[Mevcut C4.5 komut ekindeki](../c4/c4-5-commands-2026-11-06.md#temiz-kabul-profilleri) Compose dosyalarının tamamı aynı sırada kullanıldı. `ROS_DOMAIN_ID=86`, `DDS_TEST_PAYLOAD=fleet-viz-c45`, `C45_PROFILE=energy` ve boş `C43_EVIDENCE_DIR="$EVIDENCE/c45-db"` seçildi. Önce `compose_c45 config --format json` ile ağ, domain ve imajlar denetlendi, sonra `compose_c45 up -d --no-build simulation` çalıştırıldı.

Tek robot örneğindeki Docker komutu, bu koşu için `--network fleet-viz-c45_dds`, `--name fleet-viz-bridge-c45`, domain 86 ve `--robot robot_2` ile çalıştırıldı. Aynı bağımsız referans okuyucu `robot_2/base_link` için açıldı. Chrome testi `VISUALIZER_EVIDENCE="$EVIDENCE/browser-c45"` ile başlatıldı. `ready.json` oluşunca `compose_c45 up -d --no-build backend`, `moving.json` oluşunca `docker stop fleet-viz-bridge-c45` çalıştırıldı. Kapanış ile backend teslimat onayının sırası Docker UTC damgalarıyla karşılaştırıldı.

```sh
docker wait fleet-viz-c45-backend-1
docker logs --timestamps fleet-viz-c45-backend-1 > "$EVIDENCE/c45-backend.log" 2>&1
docker logs fleet-viz-bridge-c45 > "$EVIDENCE/bridge-c45.log" 2>&1
sqlite3 "$C43_EVIDENCE_DIR/c45-energy.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
python3 fleet-visualizer/validation/compare.py "$EVIDENCE/browser-c45" \
  "$EVIDENCE/ros-c45.jsonl" "$EVIDENCE/bridge-c45.log"
```

Ayrı `ros2 node info /fleet_visualizer --no-daemon` ve kapanıştan sonra `ros2 node list` ile endpoint denetimi yapıldı. Simulation servisi durdurulduktan sonra her üç konteyner için çıkış kodu, `OOMKilled` ve kapanış işaretleri alındı. Sonra köprü konteyneri kaldırıldı ve `compose_c45 down` çalıştırıldı.

Ayrı C4.5 şarj regresyonu Visualizer kapalıyken aynı Compose katmanlarında çalıştırıldı.

```sh
export ROS_DOMAIN_ID=88 DDS_TEST_PAYLOAD=fleet-viz-c45-charging C45_PROFILE=charging
export C43_EVIDENCE_DIR="$EVIDENCE/c45-charging-db"
mkdir -p "$C43_EVIDENCE_DIR"
compose_c45 config --format json > "$EVIDENCE/c45-charging-config.json"
compose_c45 up --no-build --abort-on-container-exit --exit-code-from backend \
  > "$EVIDENCE/c45-charging.log" 2>&1
sqlite3 "$C43_EVIDENCE_DIR/c45-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  fleet-viz-c45-charging-simulation-1 fleet-viz-c45-charging-backend-1
compose_c45 down
```

## Depo regresyonu

```sh
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator
python3 -m fleet_config config/fleet.yaml
python3 -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test

docker run --rm --name fleet-viz-ros-regression \
  -e ROS_DOMAIN_ID=85 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" -w /work --entrypoint bash \
  ros2-fleet-simulation-c3-3-3-backend:humble-fortress -c '
set -e
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:$PYTHONPATH
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros tests/ ros2_ws/src/fleet_robot_executor/test
'

COMPOSE_PROJECT_NAME=fleet-viz-c333 python3 scripts/run_c3_3_3.py \
  --domain 87 --token fleet-viz-c333
git diff --check
```
