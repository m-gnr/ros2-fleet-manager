# Fleet Visualizer Aşama 4 komut eki

6 Kasım 2026. [Sonuçlar](report.md) · [Path kaynak kararı](nav2-source.md). Komutlar aksi belirtilmedikçe Aşama 4 worktree kökünden çalıştırılır. Aşağıdaki Docker proje adları bu görevin ayrı test ortamlarına aittir.

## Git başlangıcı

İlk komutlar ana worktree kökünde çalıştırıldı.

```sh
git status --short
git branch -avv
git worktree list
git log -1 --oneline
git rev-parse HEAD
git rev-parse origin/main
git rev-parse feat/fleet-visualizer-multi-robot
git show 7cf6e7edf31bcf54c4554bf1c1fe2f72be044036:docs/validation/fleet-visualizer/stage-3/report.md
git worktree add -b feat/fleet-visualizer-nav2-routes \
  ../ros2-fleet-manager-nav2-routes 7cf6e7edf31bcf54c4554bf1c1fe2f72be044036
```

## Canlı C4.5 Compose ve kaynak keşfi

`RUN_LABEL`, kanıt dizini ve Compose proje adını belirler. İlk enerji keşfi `energy` / 108, ilk şarj keşfi `charging` / 109, ilk Chrome kabulü `live-charge` / 111 ve son Chrome kabulü `final-charge` / 115 kullandı. Her koşu ayrı boş SQLite dizininde başladı. İmajlar, salt okunur kaynak bağları, kanıt bağı ve DDS ağı çözümlenen JSON'dan kontrol edildi. Aşağıdaki işlev Bash ve Zsh ile çalışır.

```bash
export EVIDENCE="$PWD/fleet-visualizer/artifacts/stage-4"
export RUN_LABEL=final-charge C45_PROFILE=charging ROS_DOMAIN_ID=115
export DDS_TEST_PAYLOAD="fleet-viz4-$RUN_LABEL"
export C43_EVIDENCE_DIR="$EVIDENCE/$RUN_LABEL"
mkdir -p "$C43_EVIDENCE_DIR"
compose_c45() {
  local args=() layer
  for layer in dds simulation-check simulation-c3-3-3 simulation-c4-1 simulation-c4-2 simulation-c4-3 simulation-c4-4 simulation-c4-5; do
    args+=(-f "docker/compose/docker-compose.$layer.yml")
  done
  docker compose -p "$DDS_TEST_PAYLOAD" "${args[@]}" "$@"
}
compose_c45 config --format json > "$C43_EVIDENCE_DIR/config.json"
compose_c45 create --no-build
compose_c45 start simulation
sim="$DDS_TEST_PAYLOAD-simulation-1"
backend="$DDS_TEST_PAYLOAD-backend-1"
```

Son iki koşuda backend'in `/workspace/build` ve `/workspace/install` dizinleri aynı worktree kaynaklarıyla çalışan şarj keşfi konteynerinden kopyalandı. Compose giriş noktası kendi colcon komutunu yeniden çalıştırdı. Kopyalama ilk koşu için gerekli değildir.

```sh
docker exec "$sim" bash -c '
  source /opt/ros/humble/setup.bash
  dpkg-query -W ros-humble-nav2-{planner,controller,bt-navigator} ros-humble-rclpy
  ros2 topic list -t --no-daemon --include-hidden-topics
  for id in robot_1 robot_2; do
    grep -nE "global_frame|robot_base_frame|planner_plugins|plugin:|controller_plugins" /tmp/nav2-params-$id.yaml
    ros2 topic info -v --no-daemon /$id/navigate_to_pose/_action/status
  done
  cat /opt/ros/humble/share/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml
' > "$C43_EVIDENCE_DIR/graph-and-config.txt"

docker exec "$sim" bash -c '
  source /opt/ros/humble/setup.bash
  ros2 topic list -t --no-daemon |
    awk "/\[nav_msgs\/msg\/Path\]/{print \$1}" |
    while read -r topic; do
      echo "$topic"
      ros2 topic info -v --no-daemon "$topic" | sed "/^Subscription count:/q"
    done
' > "$C43_EVIDENCE_DIR/path-endpoints.txt"

docker exec -i "$sim" bash -c 'source /opt/ros/humble/setup.bash; exec python3 -u - 300' \
  < fleet-visualizer/validation/nav2_reference.py \
  > "$C43_EVIDENCE_DIR/nav2.jsonl" 2> "$C43_EVIDENCE_DIR/nav2.err" &
```

Yalnız keşif ve enerji koşularında gözlemci hazır olduktan sonra backend başlatıldı. Son canlı Chrome koşusunda aşağıdaki hazır işareti beklendi.

## Visualizer derleme ve otomatik testler

```sh
docker build -t fleet-visualizer-stage4:humble -f fleet-visualizer/bridge/Dockerfile .
npm ci --prefix fleet-visualizer/frontend
npm --prefix fleet-visualizer/frontend run test
npm --prefix fleet-visualizer/frontend run build
PYTHONPATH=.:fleet-visualizer/bridge python3 -m unittest discover \
  -s fleet-visualizer/bridge/tests -p '*_checks.py'

docker run --rm --network none --entrypoint /ros_entrypoint.sh \
  -e ROS_DOMAIN_ID=113 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD/config:/app/config:ro" -v "$PWD/fleet-visualizer/bridge/tests:/checks:ro" \
  fleet-visualizer-stage4:humble \
  bash -c 'PYTHONPATH=/app/fleet-visualizer/bridge:$PYTHONPATH python3 -m unittest discover -s /checks -p "*_checks.py"'
```

Fixture için ayrı terminalde `npm --prefix fleet-visualizer/frontend run dev` çalıştırıldı.

```sh
export CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
VISUALIZER_EVIDENCE="$EVIDENCE/fixture" npm --prefix fleet-visualizer/frontend run verify:browser
```

## Canlı Chrome, kaynak ve performans

Üretim derlemesi ayrı terminalde sunuldu.

```sh
npm --prefix fleet-visualizer/frontend exec -- vite preview --host 127.0.0.1 --port 5174 \
  --strictPort --outDir "$PWD/fleet-visualizer/frontend/dist"
```

Nav2 gözlemcisi yukarıdaki komutla başlatılır. Köprü için test sarmalayıcısı yalnız kendi TF aboneliğinde kontrollü kesinti uygular.

```bash
export CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
export VISUALIZER_EVIDENCE="$C43_EVIDENCE_DIR/browser" VISUALIZER_GATE_DIR="$C43_EVIDENCE_DIR"
export VISUALIZER_BRIDGE="$DDS_TEST_PAYLOAD-bridge" VISUALIZER_SIMULATION="$sim"
export VISUALIZER_BACKEND_DONE="$C43_EVIDENCE_DIR/exit.txt"

docker run -d --name "$VISUALIZER_BRIDGE" --init --network "${DDS_TEST_PAYLOAD}_dds" \
  --env-file config/dds.env -e ROS_DOMAIN_ID \
  -e PYTHONPATH=/app:/opt/visualizer-deps:/app/fleet-visualizer/bridge \
  -p 127.0.0.1:8765:8765 -v "$PWD/config:/app/config:ro" \
  -v "$PWD/fleet-visualizer/validation/gated_bridge.py:/gated_bridge.py:ro" \
  -v "$C43_EVIDENCE_DIR:/validation-gates:ro" --entrypoint /ros_entrypoint.sh \
  fleet-visualizer-stage4:humble python3 /gated_bridge.py \
  --bind 0.0.0.0 --origin http://127.0.0.1:5174 --observed-nav2-plans --trace

for id in robot_1 robot_2; do
  docker exec -i "$sim" bash -c "source /opt/ros/humble/setup.bash;
    exec timeout --signal=INT 300s python3 -u - --namespace /$id $id/base_link" \
    < fleet-visualizer/validation/ros_reference.py \
    > "$C43_EVIDENCE_DIR/tf-$id.jsonl" 2> "$C43_EVIDENCE_DIR/tf-$id.err" &
done
docker exec "$sim" bash -c 'source /opt/ros/humble/setup.bash;
  ros2 node info /fleet_visualizer --no-daemon --include-hidden' > "$C43_EVIDENCE_DIR/bridge-endpoints.txt"

node fleet-visualizer/frontend/validation/routes-live.mjs > "$C43_EVIDENCE_DIR/browser.log" 2>&1 &
probe=$!
# browser/ready.json oluştuktan sonra başlat.
compose_c45 start backend
(docker wait "$backend" > "$VISUALIZER_BACKEND_DONE.tmp"
 docker logs --timestamps "$backend" > "$C43_EVIDENCE_DIR/backend.log" 2>&1
 mv "$VISUALIZER_BACKEND_DONE.tmp" "$VISUALIZER_BACKEND_DONE") &
(for i in {1..90}; do
   date -u +%FT%TZ
   docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' "$VISUALIZER_BRIDGE"
 done) > "$C43_EVIDENCE_DIR/bridge-stats.txt" 2>&1 &
wait "$probe"

cat "$C43_EVIDENCE_DIR"/tf-robot_*.jsonl > "$C43_EVIDENCE_DIR/tf.jsonl"
docker logs --timestamps "$VISUALIZER_BRIDGE" > "$C43_EVIDENCE_DIR/bridge.log" 2>&1
python3 fleet-visualizer/validation/compare_routes.py "$C43_EVIDENCE_DIR" > "$C43_EVIDENCE_DIR/compare.json"
sqlite3 "$C43_EVIDENCE_DIR/c45-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
```

Enerji koşusunda `C45_PROFILE=energy`, `RUN_LABEL=energy` ve DDS 108 kullanıldı. Başarı işareti `ALL_C4_5_ENERGY_TESTS_PASSED` ve veri tabanı `c45-energy.sqlite3` idi. Son şarj koşusunda tarayıcı sarmalayıcısı kapatıldıktan sonra [README'nin varsayılan köprü giriş noktası](../../../../fleet-visualizer/README.md#çalıştırma) ayrı çalıştırıldı. Kapatmadan önce çalışan ağ ve domain `docker inspect` ile doğrulandı.

## Bağımsız ham TF doğrulaması

Ayrı temiz şarj projesi `RUN_LABEL=tf-trace` ve DDS 116 ile hazırlandı. Chrome yerine test köprüsü kabul edilen poz damgalarını ve köprünün kabul ettiği AMCL kenar damgalarını kaydetti. Bağımsız ROS gözlemcileri `--edges` ile gerçek dinamik kenarları kaydetti.

```sh
docker run -d --init --name "$DDS_TEST_PAYLOAD-bridge" --network "${DDS_TEST_PAYLOAD}_dds" \
  --env-file config/dds.env -e ROS_DOMAIN_ID \
  -e PYTHONPATH=/app:/opt/visualizer-deps:/app/fleet-visualizer/bridge \
  -v "$PWD/config:/app/config:ro" \
  -v "$PWD/fleet-visualizer/validation/trace_tf_bridge.py:/trace_tf_bridge.py:ro" \
  --entrypoint /ros_entrypoint.sh fleet-visualizer-stage4:humble \
  python3 /trace_tf_bridge.py --observed-nav2-plans
for id in robot_1 robot_2; do
  docker exec -i "$sim" bash -c "source /opt/ros/humble/setup.bash;
    exec timeout --signal=INT 245s python3 -u - --edges --namespace /$id $id/base_link" \
    < fleet-visualizer/validation/ros_reference.py \
    > "$C43_EVIDENCE_DIR/tf-$id.jsonl" 2> "$C43_EVIDENCE_DIR/edges-$id.jsonl" &
done
compose_c45 start backend
docker wait "$backend"
docker stop "$DDS_TEST_PAYLOAD-bridge"
docker logs "$DDS_TEST_PAYLOAD-bridge" > "$C43_EVIDENCE_DIR/bridge.log" 2>&1
python3 fleet-visualizer/validation/compare_tf_anchors.py "$C43_EVIDENCE_DIR"
```

## Ürün regresyonu ve kapanış

```sh
python3 -m fleet_config config/fleet.yaml
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
  python3 -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test

# Enerji simülasyonu kaldırılmadan önce aynı kaynaklarla üretilen ROS kurulumunu kopyala.
docker cp fleet-viz4-energy-simulation-1:/workspace/install "$EVIDENCE/ros-install"
docker run --rm --network none --entrypoint /ros_entrypoint.sh \
  -e ROS_DOMAIN_ID=114 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" -v "$EVIDENCE/ros-install:/workspace/install:ro" \
  ros2-fleet-simulation-c3-3-3-backend:humble-fortress bash -c '
    source /workspace/install/setup.bash
    cd /repo
    export PYTHONPATH=/repo:/repo/backend:$PYTHONPATH
    python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
      tests/test_c42_battery_ros2.py::test_discovery_waits_for_ros_node_identity
    python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
      tests/ ros2_ws/src/fleet_robot_executor/test
  '

COMPOSE_PROJECT_NAME=fleet-viz4-c333 python3 scripts/run_c3_3_3.py \
  --domain 112 --token fleet-viz4-c333 > "$EVIDENCE/c333.log" 2>&1
docker inspect -f '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  fleet-viz4-c333-simulation-1 fleet-viz4-c333-backend-1
DDS_TEST_PAYLOAD=fleet-viz4-c333 ROS_DOMAIN_ID=112 docker compose -p fleet-viz4-c333 \
  -f docker/compose/docker-compose.dds.yml -f docker/compose/docker-compose.simulation-check.yml \
  -f docker/compose/docker-compose.simulation-c3-3-3.yml down
```

Her C4.5 koşusunun ardından ilgili köprü durduruldu, simülasyona 90 sn temiz kapanış süresi verildi, çıkış/OOM alanları kaydedildi ve yalnız o koşuya ait ağ ile konteynerler kaldırıldı.

```sh
docker stop "$DDS_TEST_PAYLOAD-bridge"
docker stop -t 90 "$sim"
docker inspect -f '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  "$sim" "$backend" "$DDS_TEST_PAYLOAD-bridge"
docker rm "$DDS_TEST_PAYLOAD-bridge"
compose_c45 down
git diff --check
```

Ham kayıtlar ve test SQLite dosyaları worktree'deki `fleet-visualizer/artifacts/stage-4/` dizinindedir. [Sürümlenen ölçümler](measurements/) · [Canlı ekran görüntüleri](screenshots/).
