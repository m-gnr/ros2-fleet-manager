# C5-T3C-1B — Çalıştırılmış komutlar ve kanıt eki

24 Kasım 2026 · [Sonuç ve kabul engelleri](c5-t3c1b-health-veto-2026-11-24.md).
Komutlar depo kökünde çalıştırıldı; default demo/GUI veya hareketli test yoktur.
**Son matrisin tam kabulü başarısızdır; bu ek hareket yetkisi veya GitHub
yayın onayı değildir. Commit/push yapılmadı.**

## Başlangıç ve native

```bash
git status --short
git rev-parse HEAD origin/main
git switch -c codex/c5-t3c1b-health-veto
bash docker/experiments/c5-t3c1b/build.sh /tmp/c5-t3c1b-native-20261124-a4
bash docker/experiments/c5-b6b7/run_native.sh /tmp/c5-t3c1b-legacy-b6b7-20261124
bash docker/experiments/c5-t3c1a/build.sh /tmp/c5-t3c1b-legacy-1a-20261124
```

Native build a1/a2 başarısız, a3 ve son a4 CTest **2/2** geçti. a4,
`-O2 -UNDEBUG` ile derlendi. C++/header/CMake girdileri, paketler, image ID ve
binary hash'leri [native/](c5-t3c1b-health-veto-2026-11-24/native/) altındadır.
Native HMAC/session/context doğrulama testleri sentetik bileşen testleridir;
fiziksel sağlık/stop kanıtı değildir. B6B.7 **3**, makro kapalı 1A **1** geçti.

B6B.5 aynı `c5-b6b5-build:local` image içinde repo salt okunur, yeni build
diziniyle **2/2** geçti:

```bash
cmake -S docker/experiments/c5-b6b5 -B /build \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE='-O2 -UNDEBUG'
cmake --build /build -j2
ctest --test-dir /build --output-on-failure
```

## Host ve typed ROS regresyonları

Son host komutu **472 PASS**, 0 fail/skip:

```bash
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
 /tmp/c5-perf-test-venv/bin/python -m pytest -q -p no:cacheprovider \
 tests/test_robot_health.py tests/test_stop_envelope.py tests/test_split_health.py \
 tests/test_health_fixture_transports.py tests/test_native_permit_context.py \
 tests/test_traffic_product_child.py tests/test_traffic_child_binding.py \
 tests/test_peer_awareness_config.py tests/test_traffic_protocol.py tests/test_traffic_motion_gate.py \
 tests/test_traffic_core.py tests/test_fleet_manager_outbox.py tests/test_fleet_manager_domain.py \
 tests/test_executor_safety.py tests/test_executor_state_machine.py tests/test_b6b4_topology.py \
 tests/test_c43_station_dispatch.py tests/test_c44_charging.py tests/test_ros2_route_resolver.py
```

Önceki geçici T2 overlay bulunmadığından mevcut üç paket aynı Nav2 validation
image'ında yeniden build edildi: `fleet_interfaces`, `fleet_nav2_observer`,
`fleet_perception`; **3 paket başarılı, 20.5 s**. Yeni dizin
`/tmp/c5-t3c1b-ros-build-20261124`, build log'u kanıttadır. Overlay ürün bileşeni
veya varsayılan kurulumun parçası yapılmadı.

ROS seçkisi `c5-b6b5-build:local`, `--network none`, domain **173**,
`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
repo/overlay salt okunur olarak **185 PASS** verdi:

```bash
source /opt/ros/humble/setup.bash
source /build/install/local_setup.bash
export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
python3 -m pytest -q -p no:cacheprovider \
 tests/test_robot_health.py tests/test_stop_envelope.py tests/test_split_health.py \
 tests/test_health_fixture_transports.py tests/test_robot_health_ros2.py \
 tests/test_native_permit_context.py tests/test_native_permit_ros2.py \
 tests/test_traffic_product_child.py tests/test_traffic_product_child_ros2.py \
 tests/test_traffic_protocol_ros2.py tests/test_executor_safety_ros2.py
```

İlk ROS koşusu **1 fail / 177 pass** ile duplicate odometri alımının TF
beklerken yenilenmesini ortaya çıkardı; log korunur. Düzeltme sonrası 178,
son ek testlerle 185 geçti. Son ROS invalid feedback-publisher kapanış uyarısı
saklandı; fiziksel duruş veya test atlama olarak yorumlanmadı. Host/ROS seçkileri
örtüşür; test toplamları birleştirilmez.

## İzole durağan Gazebo matrisi

Tam gerçek shell/CLI ledger'ları
[commands/](c5-t3c1b-health-veto-2026-11-24/commands/) altındadır:
`c5-t3c1b-live-matrix-20261124.sh` (13 koşu, **8/13 CLI 0**) ve
`c5-t3c1b-live-matrix-final2-20261124.sh` (14 koşu, **11/14 CLI 0**).
Her senaryo seri çalıştırıldı; domain/partition, DB/session/boot ve reset ayrıdır.
İkinci matriste domain **210–223** kullanıldı. Koşu başına temel çağrı:

```bash
docker run --rm --init --name "$name" --network bridge --workdir /workspace \
 --env ROS_DOMAIN_ID="$index" --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
 --env ROS_LOCALHOST_ONLY=0 --env IGN_PARTITION="$name" \
 -v "$root:/workspace:ro" -v /tmp/c5-t3c1b-ros-build-20261124:/build:ro \
 -v /tmp/c5-t3c1b-native-20261124-a4:/b6b7-native:ro \
 -v /tmp/c5-t3c1b-live-20261124:/evidence c5-b6b5-build:local bash -ec '
 source /opt/ros/humble/setup.bash
 source /build/install/local_setup.bash
 export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
 python3 docker/experiments/c5-t3c1b/live.py config/fleet.warehouse-30x18.yaml "/evidence/$1" --case "$2"
 ' t3c1b "$run" "$scenario"
```

Önceki `health-flow-a1`–`a4` ayrı dört koşudur, domain 181–184.
a1/a2 native a3, a3/a4 native a4 kullandı. İlk source/TF/AMCL ve sağlık expiry
başarısızlıkları bu dizinlerdedir. a4 temiz sağlık-kaybı koşusudur; sonraki
tam matrisin başarısızlığını kaldırmaz. Kaynak hash'leri olmayan eski
prototipler son kaynakla tekrarlanmış gibi sunulmaz.

Tam audit komutu başarısız CLI nedeniyle **FAIL** verdi; traceback korunur:

```bash
python3 docker/experiments/c5-t3c1b/audit.py \
 /tmp/c5-t3c1b-live-20261124 /tmp/c5-t3c1b-live-matrix-final2-20261124.tsv \
 /tmp/c5-t3c1b-live-audit-full-20261124.json
```

Aynı komuta `--completed-only` eklenerek temiz 11 koşunun ham kanıtı ayrıca
incelendi. Çıktı `INCOMPLETE_1B_ACCEPTANCE_COMPLETED_CASES_AUDITED`,
`acceptance_complete=false`; dışlanan üç başarısız satır çıktıda tutulur.
Bu seçenek kabul bypass'ı değildir; tam matris yerine geçmez.
Anahtarlar arşivlenmedi; HMAC yalnız canlı probe'da doğrulandı.

## İzolasyon, arşiv ve devam

Taban blob karşılaştırması 6410 izlenen dosya ve önceki C5'ten 5771 dosyanın
değişmediğini doğruladı. İzinli kaynak/test/doküman diff'i kaydedildi.
`scripts/start_demo.sh`, GUI/config/IDL, Scheduler/Outbox/preemption ve güvenlik
eşikleri değişmedi. Deneysel native macro yalnız yeni CMake hedefinde açılır;
stok Twist yolu bu native ortama eklenmedi. Başka worktree'ye işlem yapılmadı.

31 ham canlı koşu, ilk başarısız derlemeler, test log'ları ve komutlar yeni
kanıt dizinine kayıpsız aktarıldı. **2212** ham dosya için orijinal byte ve
arşiv SHA-256 manifesti vardır; JSON/JSONL/log/SDF/YAML kayıpsız gzip, mevcut
gzip ve SQLite backup'lar kimlik olarak korunur. Native executable/.so,
provision anahtarı, venv ve cache arşivlenmedi. Orijinal `/tmp` kanıtları da
silinmedi. Derived raporlar manifestten ayrı açık dosyalardır.

Mermaid CLI 11.12.0 ile SVG ve PNG üretildi; PNG görsel olarak incelendi:

```bash
node /Users/murat/.npm/_npx/bb964472b4759b27/node_modules/@mermaid-js/mermaid-cli/src/cli.js \
 -i docs/diagrams/src/traffic-native-health-veto.mmd \
 -o docs/diagrams/svg/traffic-native-health-veto.svg -w 1800 -b white
```

Son durum: branch `codex/c5-t3c1b-health-veto`, HEAD/`origin/main` taban
`f69d1024b36a2cc5ac8ad93679f9f66c22f13397`, değişiklikler commit edilmeden
çalışma ağacında. Tam kabul sağlanmadığından commit/push/force/reset/clean yok.
Kendi test container ve alt süreçleri sonlandırıldı; default demo başlatılmadı.

Devam promptu:

> C5-T3C-1B devamı: mevcut çalışma ağacını ve kanıtları koru. Önce bu raporu ve
> son kaynak hash'lerini oku. Nonzero/rearm/rollover kapalıyken yanlış-session
> koşusundaki gerçek FM permit önkoşulu eksikliğini, controller/replan Nav2 ve
> ROS/IGN kapanış hatalarını incele. Güncel RobotStatus/readiness ve gerçek
> Scheduler atamasıyla tek dondurulmuş kaynak revizyonunda temiz 1B matrisini
> doğrula. Başarısızlıkta commit/push yapma; hareketli ölçüme geçme.
