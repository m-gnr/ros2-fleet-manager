# C5-T3C-1A — Çalıştırılmış komutlar ve kanıt eki

19 Kasım 2026 · [Sonuç](c5-t3c1a-native-worker-2026-11-19.md).
Komutlar depo kökünden çalıştırıldı. Varsayılan demo/GUI veya hareketli test yok.

## Native ve regresyon

```bash
git status --short
git rev-parse HEAD origin/main
git switch -c codex/c5-t3c1a-native-worker
bash docker/experiments/c5-t3c1a/build.sh /tmp/c5-t3c1a-native-20261119-a5
bash docker/experiments/c5-b6b7/run_native.sh /tmp/c5-t3c1a-legacy-b6b7-20261119
```

Yeni native build a1–a5 ayrı dizinlerdedir. Son a5 temiz CMake/CTest,
`-O2 -UNDEBUG`, image ID, paket/source/binary SHA-256 kayıtları içerir.
Eski B6B.5, aynı image/repo salt okunur ve yeni build diziniyle:

```bash
cmake -S docker/experiments/c5-b6b5 -B /build \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE='-O2 -UNDEBUG'
cmake --build /build -j2
ctest --test-dir /build --output-on-failure
```

Host seçkisi, mevcut test venv'iyle:

```bash
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
  /tmp/c5-perf-test-venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_robot_health.py tests/test_stop_envelope.py tests/test_health_fixture_transports.py \
  tests/test_native_permit_context.py tests/test_traffic_product_child.py tests/test_traffic_child_binding.py \
  tests/test_peer_awareness_config.py tests/test_traffic_protocol.py tests/test_traffic_motion_gate.py \
  tests/test_traffic_core.py tests/test_fleet_manager_outbox.py tests/test_fleet_manager_domain.py \
  tests/test_executor_safety.py tests/test_executor_state_machine.py tests/test_b6b4_topology.py \
  tests/test_c43_station_dispatch.py tests/test_c44_charging.py tests/test_ros2_route_resolver.py
```

ROS seçkisi aynı image, `--network none`, repo ve T2 overlay salt okunur;
domain **173**, `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `IGN_PARTITION=c5-t3c1a-ros-regression`:

```bash
source /opt/ros/humble/setup.bash
source /build/install/local_setup.bash
export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
python3 -m pytest -q -p no:cacheprovider \
  tests/test_robot_health.py tests/test_stop_envelope.py tests/test_health_fixture_transports.py \
  tests/test_robot_health_ros2.py tests/test_native_permit_context.py tests/test_native_permit_ros2.py \
  tests/test_traffic_product_child.py tests/test_traffic_product_child_ros2.py \
  tests/test_traffic_protocol_ros2.py tests/test_executor_safety_ros2.py
```

Sonuçlar: host 442, ROS 154, yeni native 1, eski B6B.7 3 ve B6B.5 2 geçti.
Tekrarlanan/kapsamı örtüşen seçkiler benzersiz toplam olarak toplanmaz.

## İzole canlı çağrı

Gerçek tam matris scriptleri ve CLI/domain TSV'leri
[commands/](c5-t3c1a-native-worker-2026-11-19/commands/) altındadır.
Son `final3` scripti sekiz koşuyu seri çalıştırdı; domain **204–211**,
her biri ayrı `IGN_PARTITION`, DB/session/boot ve reset. Asıl çağrı:

```bash
docker run --rm --init --name "$name" --network bridge --workdir /workspace \
  --env ROS_DOMAIN_ID="$index" --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  --env ROS_LOCALHOST_ONLY=0 --env IGN_PARTITION="$name" \
  -v "$root:/workspace:ro" -v /tmp/c5-t2-build-20261118:/build:ro \
  -v /tmp/c5-t3c1a-native-20261119-a5:/b6b7-native:ro \
  -v /tmp/c5-t3c1a-live-20261119:/evidence c5-b6b5-build:local bash -ec '
    source /opt/ros/humble/setup.bash
    source /build/install/local_setup.bash
    export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
    python3 docker/experiments/c5-t3c1a/live.py config/fleet.warehouse-30x18.yaml "/evidence/$1" --case "$2"
  ' t3c1a "$run" "$case"
```

Ara domain'ler: ilk prototipler 181–183, final1 184–191, final2 194–197.
Final1 sekiz CLI 0 aldı; eksik stock-library mapping gözlemi nedeniyle son
kabul yerine kullanılmadı. Final2 duplicate kapanışı -6 ile kaldı. Final3
yalnız fixture kapanış sırasını düzeltti; **aynı a5 native binary** kullanıldı.
Kaynak/versiyon farkları ve bütün başarısız ham denemeler saklanır.

```bash
python3 docker/experiments/c5-t3c1a/audit.py \
  /tmp/c5-t3c1a-live-20261119 \
  /tmp/c5-t3c1a-live-matrix-final3-20261119.tsv \
  /tmp/c5-t3c1a-live-audit-final-20261119.json
```

Offline audit kalıcı body/context/Outbox/ACK, gerçek Scheduler ataması,
imzalı gözlemin byte/alan bağları, writer hedefi, Physics ilerlemesi ve
release reddini denetler. Anahtarlar arşivde yok; MAC yalnız canlı probe'da
doğrulandı. Audit gzip JSON/JSONL de okuyabilir; SQLite backup kimlik olarak
arşivlenir. Arşivdeki case dizinleri `live/`, matris TSV'si `commands/` altındadır.

## İzolasyon ve arşiv

Statik kontrol başlangıç Git blob'larıyla 464 dokümantasyon dışı dosyayı ve
4332 önceki C5 kanıt/dokümanını karşılaştırdı. Eski B6B.5/B6B.7 etkin koşullu
DiffDrive kaynakları da boşluk/yönerge ayrımı sonrası tabanla eşleşti.
Native C++ girdileri a5 source hash'leriyle yeniden karşılaştırıldı.
Kaynak/hash kayıtları yeni kanıt dizinindedir.

Ham log/JSONL/SDF/YAML çıktıları kayıpsız gzip; zaten gzip dosyalar ve SQLite
backup'lar kimlik olarak tutulur. Orijinal byte hash manifesti ve dosya
manifesti ayrıca doğrulanır. Provision anahtarları, native executable/.so,
venv/cache Git'e alınmaz. Hiçbir eski kanıt dosyası silinmedi/sıfırlanmadı.

Mermaid CLI 11.12.0 ile SVG ve PNG üretildi; PNG görsel olarak incelendi:

```bash
node /Users/murat/.npm/_npx/bb964472b4759b27/node_modules/@mermaid-js/mermaid-cli/src/cli.js \
  -i docs/diagrams/src/traffic-native-worker.mmd \
  -o docs/diagrams/svg/traffic-native-worker.svg -w 1600 -b white
```

Son aşama yalnız kapsam dosyalarını commit etmek, uzak main'in tabanla
fast-forward uygunluğunu kontrol etmek ve normal push/uzak SHA/temiz ağaç
doğrulamasıdır. Force push, reset, clean veya başka worktree değişikliği yoktur.
