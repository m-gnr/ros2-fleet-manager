# Fleet Visualizer Aşama 2 komut eki

6 Kasım 2026. Komutlar Aşama 2 worktree kökünden çalıştırılır. [Sonuçlar](report.md).

## Derleme, birim testleri ve fixture

```sh
export EVIDENCE="$PWD/fleet-visualizer/artifacts/stage-2"
export CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
mkdir -p "$EVIDENCE"

npm ci --prefix fleet-visualizer/frontend
npm --prefix fleet-visualizer/frontend run test
npm --prefix fleet-visualizer/frontend run build
npm --prefix fleet-visualizer/frontend audit

PYTHONPATH=fleet-visualizer/bridge python3 -m unittest discover \
  -s fleet-visualizer/bridge/tests -p '*_checks.py'
docker build -t fleet-visualizer-stage2:humble -f fleet-visualizer/bridge/Dockerfile .
docker run --rm --network none --entrypoint /ros_entrypoint.sh \
  -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD/fleet-visualizer/bridge/tests:/checks:ro" fleet-visualizer-stage2:humble \
  bash -c 'PYTHONPATH=/app/fleet-visualizer/bridge:$PYTHONPATH python3 -m unittest discover -s /checks -p "*_checks.py"'
```

Geliştirme sunucusu için `npm --prefix fleet-visualizer/frontend run dev` kullanıldı. Nihai Chrome kontrolleri için üretim derlemesi aşağıdaki loopback adresinde sunuldu. Sunucuyu ayrı terminalde çalıştır.

```sh
(cd fleet-visualizer/frontend && npm exec -- vite preview --host 127.0.0.1 --port 5174 --strictPort)

export VISUALIZER_URL='http://127.0.0.1:5174/?trace'
VISUALIZER_EVIDENCE="$EVIDENCE/fixture" npm --prefix fleet-visualizer/frontend run verify:browser
```

Soğuk yüklemede Aşama 1 worktree kökünde aynı `run build` komutu çalıştırıldı. Üretim derlemesi ayrı Vite preview ile 5175 portunda sunuldu. Her URL için yeni Chrome bağlamında üç örnek alındı.

```sh
node fleet-visualizer/frontend/validation/initial-load.mjs \
  'http://127.0.0.1:5175/?trace' 'http://127.0.0.1:5174/?trace' \
  > "$EVIDENCE/initial-load.json"
```

## Canlı C2.3 ve Chrome

DDS domain 94, `fleet-viz2-single` Compose projesi ve seçili `robot_1` kullanıldı. [Aşama 1 yöntemi](../commands.md#tek-robotlu-canlı-doğrulama) aynı imajlar ve bağımsız TF örnekleyicisi ile yeniden kullanıldı. `create` öncesinde çözülmüş volume kaynakları, DDS ağı, domain ve imaj denetlendi.

```sh
export ROS_DOMAIN_ID=94 DDS_TEST_PAYLOAD=fleet-viz2-single
compose_single() {
  docker compose -p "$DDS_TEST_PAYLOAD" \
    -f docker/compose/docker-compose.dds.yml \
    -f docker/compose/docker-compose.simulation-check.yml \
    -f docker/compose/docker-compose.simulation-c2-3.yml "$@"
}

compose_single config --format json > "$EVIDENCE/single-config.json"
compose_single create --no-build
docker run -d --name fleet-viz2-bridge --init --network fleet-viz2-single_dds \
  --env-file config/dds.env -e ROS_DOMAIN_ID \
  -p 127.0.0.1:8765:8765 --mount "type=bind,src=$PWD/config,dst=/app/config,readonly" \
  fleet-visualizer-stage2:humble --robot robot_1 --bind 0.0.0.0 --origin http://127.0.0.1:5174 --trace

export VISUALIZER_EVIDENCE="$EVIDENCE/live-single" VISUALIZER_CUTS=1
npm --prefix fleet-visualizer/frontend run verify:live > "$EVIDENCE/single-browser.log" 2>&1 &
browser_pid=$!
compose_single up -d --no-build

docker exec -i fleet-viz2-single-simulation-1 bash -c \
  'source /opt/ros/humble/setup.bash; exec timeout --signal=INT 220s python3 -u - robot_1/base_link' \
  < fleet-visualizer/validation/ros_reference.py > "$EVIDENCE/single-ros.jsonl" &
docker wait fleet-viz2-single-backend-1
```

`moving.json` dosyasını ve backend çıkış kodu 0'ı bekle. Yalnız bu izole koşuda TF yardımcısını duraklat. Her kesinti işaretinde Chrome kontrolü tamamlandıktan sonra sonraki adıma geç.

```sh
sim=fleet-viz2-single-simulation-1
tf_pid=$(docker exec "$sim" pgrep -f '^python3 /opt/simulation-c2-3/tf_helper.py$')
docker exec "$sim" kill -STOP "$tf_pid"
# live-single/stale.json oluşmasını bekle.
for sample in 1 2 3 4 5 6 7 8; do
  docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' "$sim" fleet-viz2-bridge
done > "$EVIDENCE/single-stats-stale.txt"
docker exec "$sim" kill -CONT "$tf_pid"
# live-single/ros-recovered.json oluşmasını bekle.
docker exec "$sim" bash -c 'source /opt/ros/humble/setup.bash; ros2 node info /fleet_visualizer --no-daemon' \
  > "$EVIDENCE/single-ros-node-info.txt"
for sample in 1 2 3 4 5 6 7 8; do
  docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' "$sim" fleet-viz2-bridge
done > "$EVIDENCE/single-stats-live.txt"

docker stop fleet-viz2-bridge
# live-single/disconnected.json oluşmasını bekle.
docker start fleet-viz2-bridge
wait "$browser_pid"
docker logs --timestamps fleet-viz2-bridge > "$EVIDENCE/single-bridge.log" 2>&1
sed -E 's/^[^ ]+ //' "$EVIDENCE/single-bridge.log" > "$EVIDENCE/single-bridge-compare.log"
python3 fleet-visualizer/validation/compare.py "$VISUALIZER_EVIDENCE" \
  "$EVIDENCE/single-ros.jsonl" "$EVIDENCE/single-bridge-compare.log" > "$EVIDENCE/single-compare.json"

docker stop fleet-viz2-bridge "$sim"
docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  fleet-viz2-bridge "$sim" fleet-viz2-single-backend-1
docker rm fleet-viz2-bridge
compose_single down
```

Chrome'da `performance.now()` ile gerçek WebGL kare başlangıçları kaydedilir. FPS, performans penceresindeki kare sayısının pencere süresine bölümüdür. p95 ardışık render çağrılarının aralığıdır. CDP `Performance.getMetrics` ve `SystemInfo.getProcessInfo` heap ve süreç CPU sayaçlarını verir. `ps -o rss=` Chrome süreçlerinin RSS toplamıdır. Three.js `renderer.info` sayaçları her render çağrısından sonra alınır. Köprü gönderim hızı en uzun kesintisiz `WS_POSE` dizisinde Docker zaman damgalarından hesaplanır. Aralarında 0,5 sn'den fazla olan kayıtlar ayrı dizilere ayrılır.

## C4.5 ve C3.3.3

C4.5 için [mevcut sekiz Compose katmanı](../../c4/c4-5-commands-2026-11-06.md#temiz-kabul-profilleri) aynı sırada kullanıldı. `C45_PROFILE=energy`, `ROS_DOMAIN_ID=96`, `DDS_TEST_PAYLOAD=fleet-viz2-c45`, `C43_EVIDENCE_DIR="$EVIDENCE/c45-energy-state"`. Boş koşu dizini oluşturuldu. `config --format json` denetiminden sonra önce simulation başlatıldı. Köprü aynı komutla `fleet-viz2-c45-bridge`, `fleet-viz2-c45_dds` ve `--robot robot_2` kullanılarak başlatıldı. TF örnekleyicisi `robot_2/base_link` için açıldı. Aşağıdaki sırada çalışıldı.

```sh
unset VISUALIZER_CUTS
export VISUALIZER_EVIDENCE="$EVIDENCE/live-c45"
npm --prefix fleet-visualizer/frontend run verify:live &
browser_pid=$!
# live-c45/ready.json oluşmasını bekle.
compose_c45 up -d --no-build backend
# live-c45/moving.json oluşmasını bekle.
docker stop fleet-viz2-c45-bridge
wait "$browser_pid"
docker wait fleet-viz2-c45-backend-1
docker logs --timestamps fleet-viz2-c45-backend-1 > "$EVIDENCE/c45-energy-backend.log" 2>&1
docker logs --timestamps fleet-viz2-c45-bridge > "$EVIDENCE/c45-energy-bridge-timestamps.log" 2>&1
docker logs fleet-viz2-c45-bridge > "$EVIDENCE/c45-energy-bridge.log" 2>&1
python3 fleet-visualizer/validation/compare.py "$VISUALIZER_EVIDENCE" \
  "$EVIDENCE/c45-energy-ros.jsonl" "$EVIDENCE/c45-energy-bridge.log" > "$EVIDENCE/c45-energy-compare.json"
```

Simulation durduruldu. Köprü, simulation ve backend için Docker exit/OOM alanları kaydedildi. Ardından köprü kaldırıldı ve `compose_c45 down` çalıştırıldı. Kalıcılık denetimlerinde mevcut kabul ve regresyon testlerinin çıktıları kullanıldı.

```sh
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator
python3 -m fleet_config config/fleet.yaml
python3 -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test

docker run --rm --name fleet-viz2-ros-regression \
  -e ROS_DOMAIN_ID=95 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
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

COMPOSE_PROJECT_NAME=fleet-viz2-c333 python3 scripts/run_c3_3_3.py \
  --domain 97 --token fleet-viz2-c333 > "$EVIDENCE/c333.log" 2>&1
docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  fleet-viz2-c333-simulation-1 fleet-viz2-c333-backend-1
DDS_TEST_PAYLOAD=fleet-viz2-c333 ROS_DOMAIN_ID=97 docker compose -p fleet-viz2-c333 \
  -f docker/compose/docker-compose.dds.yml \
  -f docker/compose/docker-compose.simulation-check.yml \
  -f docker/compose/docker-compose.simulation-c3-3-3.yml down
git diff --check
```

C4.5 şarj profili ayrı Compose projesinde Visualizer kapalıyken çalıştırıldı.

```sh
export DDS_TEST_PAYLOAD=fleet-viz2-charging ROS_DOMAIN_ID=98 C45_PROFILE=charging
export C43_EVIDENCE_DIR="$EVIDENCE/c45-charging-state"
mkdir -p "$C43_EVIDENCE_DIR"
compose_c45 config --format json > "$EVIDENCE/c45-charging-config.json"
compose_c45 up --no-build --abort-on-container-exit --exit-code-from backend \
  > "$EVIDENCE/c45-charging.log" 2>&1
docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  fleet-viz2-charging-simulation-1 fleet-viz2-charging-backend-1
compose_c45 down
```
