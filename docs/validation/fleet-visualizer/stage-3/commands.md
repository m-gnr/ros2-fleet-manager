# Fleet Visualizer Aşama 3 komut eki

6 Kasım 2026. Komutlar Aşama 3 worktree kökünden çalıştırılır. [Doğrulama raporu](report.md).

## Git ve derleme

Başlangıçta ana worktree'de durum, dallar, worktree'ler ve commit'ler kontrol edildi. Aşama 2 raporu ilgili commit'te bulundu. Aşağıdaki `worktree add` ilk kurulum içindir.

```sh
git status --short
git branch -avv
git worktree list
git log -1 --oneline
git rev-parse HEAD origin/main
git show 015865403d5bf3cae62647fbc149c5bbcee620a5:docs/validation/fleet-visualizer/stage-2/report.md
git worktree add -b feat/fleet-visualizer-multi-robot \
  ../ros2-fleet-manager-multi-robot 015865403d5bf3cae62647fbc149c5bbcee620a5
```

```sh
export EVIDENCE="$PWD/fleet-visualizer/artifacts/stage-3"
export CHROME_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
mkdir -p "$EVIDENCE"
npm ci --prefix fleet-visualizer/frontend
npm --prefix fleet-visualizer/frontend run test
npm --prefix fleet-visualizer/frontend run build
docker build -t fleet-visualizer-stage3:humble -f fleet-visualizer/bridge/Dockerfile .
PYTHONPATH=.:fleet-visualizer/bridge python3 -m unittest discover \
  -s fleet-visualizer/bridge/tests -p '*_checks.py'
docker run --rm --network none --entrypoint /ros_entrypoint.sh \
  -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD/config:/app/config:ro" -v "$PWD/fleet-visualizer/bridge/tests:/checks:ro" \
  fleet-visualizer-stage3:humble \
  bash -c 'PYTHONPATH=/app/fleet-visualizer/bridge:$PYTHONPATH python3 -m unittest discover -s /checks -p "*_checks.py"'
```

Fixture koşusunda ayrı terminalde `npm --prefix fleet-visualizer/frontend run dev` açıldı. Canlı test üretim derlemesini preview üzerinden kullandı.

```sh
VISUALIZER_EVIDENCE="$EVIDENCE/fixture" npm --prefix fleet-visualizer/frontend run verify:browser
npm --prefix fleet-visualizer/frontend exec -- vite preview --host 127.0.0.1 --port 5174 \
  --strictPort --outDir "$PWD/fleet-visualizer/frontend/dist"
```

## C4.5 enerji profili ve canlı Chrome

Aşağıdaki katmanlar [C4.5 tarifindekiyle](../../c4/c4-5-commands-2026-11-06.md#temiz-kabul-profilleri) aynı sıradadır. `config --format json` çıktısındaki imajlar, bağlanan dizinler, domain ve ağ başlatmadan önce kontrol edildi. Tekrarda aynı konteynerler derleme önbelleğiyle yeniden başlatıldı. Önceki DB ve kayıtlar ayrı dizine taşındı ve kanıt dizini boşaltılmış bir yola bağlandı.

```bash
export DDS_TEST_PAYLOAD=fleet-viz3-c45 ROS_DOMAIN_ID=104 C45_PROFILE=energy
export C43_EVIDENCE_DIR="$EVIDENCE/energy"
mkdir -p "$C43_EVIDENCE_DIR"
compose_c45() {
  local args=() layer
  for layer in dds simulation-check simulation-c3-3-3 simulation-c4-1 simulation-c4-2 simulation-c4-3 simulation-c4-4 simulation-c4-5; do
    args+=(-f "docker/compose/docker-compose.$layer.yml")
  done
  docker compose -p "$DDS_TEST_PAYLOAD" "${args[@]}" "$@"
}
compose_c45 config --format json > "$EVIDENCE/c45-config.json"
compose_c45 up -d --no-build simulation
compose_c45 create --no-build backend

sim=fleet-viz3-c45-simulation-1
docker exec "$sim" bash -lc 'source /opt/ros/humble/setup.bash; ros2 topic list --no-daemon'
for robot in robot_1 robot_2; do
  docker exec "$sim" bash -c "source /opt/ros/humble/setup.bash;
    timeout 8 ros2 run tf2_ros tf2_echo map $robot/base_link --ros-args \
    -r /tf:=/$robot/tf -r /tf_static:=/$robot/tf_static" | head -15
done
```

Köprü, enerji kabulünde yalnız test sarmalayıcısıyla açıldı. Sarmalayıcı, Chrome probunun oluşturduğu dosya süresince ilgili robotun gelen TF mesajlarını köprü içinde atlar. Gazebo, Nav2 ve ürün TF yayıncıları normal şekilde çalışır.

```sh
docker run -d --name fleet-viz3-bridge --init --network fleet-viz3-c45_dds \
  --env-file config/dds.env -e ROS_DOMAIN_ID \
  -e PYTHONPATH=/app:/opt/visualizer-deps:/app/fleet-visualizer/bridge \
  -p 127.0.0.1:8765:8765 -v "$PWD/config:/app/config:ro" \
  -v "$PWD/fleet-visualizer/validation/gated_bridge.py:/gated_bridge.py:ro" \
  -v "$EVIDENCE:/validation-gates:ro" --entrypoint /ros_entrypoint.sh \
  fleet-visualizer-stage3:humble python3 /gated_bridge.py \
  --bind 0.0.0.0 --origin http://127.0.0.1:5174 --trace

docker exec -i "$sim" bash -c \
  'source /opt/ros/humble/setup.bash; exec timeout --signal=INT 360s python3 -u - robot_1/base_link robot_2/base_link' \
  < fleet-visualizer/validation/ros_reference.py > "$EVIDENCE/ros-reference-final.jsonl" 2>"$EVIDENCE/ros-reference-final.err" &

export VISUALIZER_EVIDENCE="$EVIDENCE/live" VISUALIZER_GATE_DIR="$EVIDENCE"
export VISUALIZER_BRIDGE=fleet-viz3-bridge VISUALIZER_BACKEND_DONE="$EVIDENCE/backend-exit.txt"
node fleet-visualizer/frontend/validation/fleet-live.mjs > "$EVIDENCE/live-browser.log" 2>&1 &
probe=$!
# live/ready.json oluştuktan sonra backend başlatılır.
docker start fleet-viz3-c45-backend-1
(docker wait fleet-viz3-c45-backend-1 > "$EVIDENCE/backend-exit.txt.wait"
 mv "$EVIDENCE/backend-exit.txt.wait" "$EVIDENCE/backend-exit.txt") &
wait "$probe"

docker logs --timestamps fleet-viz3-c45-backend-1 > "$EVIDENCE/backend-final.log" 2>&1
docker logs fleet-viz3-bridge > "$EVIDENCE/bridge-final.log" 2>&1
python3 fleet-visualizer/validation/compare_fleet.py "$VISUALIZER_EVIDENCE" \
  "$EVIDENCE/ros-reference-final.jsonl" "$EVIDENCE/bridge-final.log" > "$EVIDENCE/live/compare.json"
sqlite3 "$C43_EVIDENCE_DIR/c45-energy.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
```

Köprü kapalı ve açık zamanları Chrome'un `bridge-off.json` ve `bridge-on.json` kayıtlarıyla, görev kabulü Docker zaman damgalı backend çıktısıyla karşılaştırıldı. Enerji testinden sonra test köprüsü durduruldu. Varsayılan giriş noktası [README komutuyla](../../../../fleet-visualizer/README.md#çalıştırma) açıldı. Simülasyonun iki robotu aynı kadrajda canlı TF aktarırken aşağıdaki ölçümler yapıldı.

```sh
node fleet-visualizer/frontend/validation/fleet-performance.mjs > "$EVIDENCE/performance-fit.json"
docker exec "$sim" bash -c \
  'source /opt/ros/humble/setup.bash; ros2 node info /fleet_visualizer --no-daemon' > "$EVIDENCE/ros-node-final.txt"
docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' fleet-visualizer-stage3
docker stop fleet-visualizer-stage3
docker stop -t 90 "$sim"
docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  "$sim" fleet-viz3-c45-backend-1 fleet-visualizer-stage3
docker logs --tail 80 "$sim"
docker rm fleet-visualizer-stage3 fleet-viz3-bridge
compose_c45 down
```

## Ürün regresyonları

```sh
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator
python3 -m fleet_config config/fleet.yaml
python3 -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test
```

Humble/CycloneDDS ilk koşusu [C4.3 Docker komutunu](../../c4/c4-3-commands-2026-11-06.md) kullandı. Domain 105, `ROS_LOCALHOST_ONLY=1`. Tekrar konteynerine aynı kaynaklardan C4.5 simulation içinde üretilen `/workspace/install` kopyalandı. Yerel `/repo` ve `/config` salt okunur bağlandı. Gazebo kapalıyken aşağıdaki çağrılar çalıştırıldı.

```sh
source /opt/ros/humble/setup.bash
source /workspace/install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:$PYTHONPATH
for spec in tests/test_executor_safety_ros2.py::test_startup_session_and_overflow_gate \
            docker/simulation-c2-3/test_config.py docker/simulation-c3-3-3/test_config.py; do
  python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros "$spec"
done
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
  tests/ ros2_ws/src/fleet_robot_executor/test
```

Ham kayıtlar `fleet-visualizer/artifacts/stage-3/` dizininde, sürümlenen örnekler [ölçüm dizininde](measurements/) tutulur.

## C4.5 şarj ve C3.3.3 canlı regresyonları

Şarj ayrı proje, domain ve boş kanıt dizininde çalıştırıldı. Enerji profilindeki aynı kaynaklar ve imajlardan üretilen `/workspace/build` ve `/workspace/install` ilgili konteynerlere kopyalandı. Compose kendi colcon komutunu yeniden çalıştırdı. Şarj köprüsü varsayılan giriş noktasını kullandı.

```sh
export DDS_TEST_PAYLOAD=fleet-viz3-charging ROS_DOMAIN_ID=106 C45_PROFILE=charging
export C43_EVIDENCE_DIR="$EVIDENCE/charging"
mkdir -p "$C43_EVIDENCE_DIR"
compose_c45 config --format json > "$EVIDENCE/charging-config.json"
compose_c45 create --no-build
# Derleme önbelleği alınacaksa enerji konteynerleri kaldırılmadan önce çalıştırılır.
for role in simulation backend; do
  cache="$EVIDENCE/c45-colcon/$role"
  mkdir -p "$cache"
  for directory in build install; do
    docker cp "fleet-viz3-c45-${role}-1:/workspace/$directory" "$cache/"
    docker cp "$cache/$directory" "fleet-viz3-charging-${role}-1:/workspace/$directory"
  done
done
docker start fleet-viz3-charging-simulation-1
docker run -d --init --name fleet-viz3-charging-bridge --network fleet-viz3-charging_dds \
  --env-file config/dds.env -e ROS_DOMAIN_ID -p 127.0.0.1:8765:8765 \
  --mount "type=bind,src=$PWD/config,dst=/app/config,readonly" \
  fleet-visualizer-stage3:humble --bind 0.0.0.0 --origin http://127.0.0.1:5174 --trace

sim=fleet-viz3-charging-simulation-1
docker exec -i "$sim" bash -c \
  'source /opt/ros/humble/setup.bash; exec timeout --signal=INT 480s python3 -u - robot_1/base_link robot_2/base_link' \
  < fleet-visualizer/validation/ros_reference.py > "$EVIDENCE/charging-ros.jsonl" &

VISUALIZER_PROFILE=charging VISUALIZER_EVIDENCE="$EVIDENCE/live-charging" \
  node fleet-visualizer/frontend/validation/fleet-live.mjs > "$EVIDENCE/charging-browser.log" 2>&1 &
probe=$!
# live-charging/ready.json oluştuktan sonra backend başlatılır.
docker start fleet-viz3-charging-backend-1
docker wait fleet-viz3-charging-backend-1
wait "$probe"
docker logs --timestamps fleet-viz3-charging-backend-1 > "$EVIDENCE/charging-backend.log" 2>&1
docker logs fleet-viz3-charging-bridge > "$EVIDENCE/charging-bridge.log" 2>&1
python3 fleet-visualizer/validation/compare_fleet.py "$EVIDENCE/live-charging" \
  "$EVIDENCE/charging-ros.jsonl" "$EVIDENCE/charging-bridge.log"
sqlite3 "$C43_EVIDENCE_DIR/c45-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
docker stop fleet-viz3-charging-bridge
docker stop -t 90 "$sim"
docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  "$sim" fleet-viz3-charging-backend-1 fleet-viz3-charging-bridge
docker rm fleet-viz3-charging-bridge
compose_c45 down
```

```sh
COMPOSE_PROJECT_NAME=fleet-viz3-c333 python3 scripts/run_c3_3_3.py \
  --domain 107 --token fleet-viz3-c333 > "$EVIDENCE/c333.log" 2>&1
docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  fleet-viz3-c333-simulation-1 fleet-viz3-c333-backend-1
DDS_TEST_PAYLOAD=fleet-viz3-c333 ROS_DOMAIN_ID=107 docker compose -p fleet-viz3-c333 \
  -f docker/compose/docker-compose.dds.yml -f docker/compose/docker-compose.simulation-check.yml \
  -f docker/compose/docker-compose.simulation-c3-3-3.yml down
git diff --check
```
