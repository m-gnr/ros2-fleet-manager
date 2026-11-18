# C5 gerçek trafik entegrasyonu — komut ve kanıt eki

18 Kasım 2026. [Aşama raporu](traffic-integration-2026-11-18.md) sonucu ve
sınırını belirler. Bütün komutlar depo kökünden çalıştırıldı; commit/push yoktur.

## Başlangıç ve koruma

```sh
pwd
git status --short
git rev-parse HEAD
git log -4 --oneline
docker ps --format '{{.Names}} {{.Status}}'
```

HEAD `da6f27a00e8b6b623b64dd57b257a48f45fc1317` idi. Önceki deneysel Peer
değişiklikleri çalışma ağacındaydı. Takipli/takipsiz 2.593 mevcut dosyanın
SHA-256 başlangıç manifesti alındı. [Başlangıç durumu](traffic-integration-2026-11-18/starting-status.txt),
[kaynak koruması](traffic-integration-2026-11-18/preservation.json).
Başka worktree/container durdurulmadı; native test build'leri ağ kapalıydı.

## Native build ve tekrar

İlk build ve temiz ikinci build, aynı image üzerinde `/tmp/c5-b6b7-build` ve
`/tmp/c5-b6b7-rebuild` host dizinlerini container'da `/build` olarak kullandı:

```sh
docker run --rm --name c5-b6b7-native-rebuild --network none --workdir /repo \
  --volume /Users/murat/develop/ros2-fleet-manager-demo:/repo:ro \
  --volume /tmp/c5-b6b7-rebuild:/build c5-b6b5-build:local bash -ec \
  'cmake -S docker/experiments/c5-b6b7 -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE="-O2 -UNDEBUG"; cmake --build /build -j2; ctest --test-dir /build --output-on-failure; sha256sum /build/libc5-authorized-zero-drive.so'

bash docker/experiments/c5-b6b7/run_native.sh /tmp/c5-b6b7-wrapper-verify
```

İlk fixture JSON yazım hatasında 2/2 test kaldı; kaynak düzeltilince 2/2 geçti.
Son wrapper da çalıştırılıp geçti. [Build/test logları](traffic-integration-2026-11-18/checks/),
[wrapper paket/sürüm/kaynak kayıtları](traffic-integration-2026-11-18/native-build/).
İki temiz ve son incremental build'in binary hash'i aynıydı:
`00d6fb6687b32dfd3b475688a8c0fe7ee0455c76f67afaf6b8e8e9798b5a275f`.
Bu, farklı tarihte yeniden kurulmuş apt ortamı için byte eşleşmesi garantisi değildir.

B6B.5 aynı değişmiş ortak kaynağın varsayılan koluyla ayrı derlendi:

```sh
docker run --rm --name c5-b6b5-regression --network none \
  --volume /Users/murat/develop/ros2-fleet-manager-demo:/repo:ro \
  --volume /tmp/c5-b6b5-regression:/build c5-b6b5-build:local bash -ec \
  'cmake -S /repo/docker/experiments/c5-b6b5 -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE="-O2 -UNDEBUG"; cmake --build /build -j2; ctest --test-dir /build --output-on-failure'
```

Sonuç 2/2 PASS. Eski rapor/source hash manifestleri yeniden yazılmadı.

## İzole gerçek dünya

[Dış test başlatıcısı](traffic-integration-2026-11-18/tools/start.py), mevcut
`c5_demo_start` runner'ını kullanır; yalnız dev image/binary mount'u ve
`docker/experiments/c5-b6b7/supervisor.py` girişini seçer. Supervision, reset,
AMCL/Nav2/TF readiness, API, Executor, Battery Simulator ve gözlemci korunur.
`server.py` config robotlarından aynı dünyayı üretir, üç tek stock sürücüyü
native sıfır sürücülerle değiştirir ve peer katmanını etkinleştirir.

```sh
source .venv/bin/activate
python3 /tmp/c5-b6b7-start.py
```

Her çağrı yeni session/domain/partition ve temiz DB üretir. Gerçek ad/portlar
`session.json` dosyasından okundu; [son launch komutu](traffic-integration-2026-11-18/final/launch-command.json)
ve [ortam kaydı](traffic-integration-2026-11-18/environment.json) arşivlidir.
Bu araç varsayılan ürün launcher'ına eklenmedi. Arşivlenmiş araç yeniden
çalıştırılmadan önce kendi test binary/cache yolunu gerektirir.

Son temiz koşuda:

```sh
docker exec c5-native-20261118T080634Z-e136c7eaa9ae bash -ec \
  'source /opt/ros/humble/setup.bash; source /c5-cache/install/local_setup.bash; export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/docker/experiments/c5-b6b7:$PYTHONPATH; python3 docker/experiments/c5-b6b7/test_live.py config/fleet.warehouse-30x18.yaml /evidence/live/native-matrix; python3 docker/experiments/c5-b6b7/test_child.py config/fleet.warehouse-30x18.yaml /evidence/live/child-binding'
```

Native matris gerçek ROS/IGN ham Twist, doğrudan IGN StringMsg yanlış MAC,
yetkili sıfır, üretici SIGKILL, komut bridge'i SIGKILL/restart ve imzalı
nonzero retlerini sınadı. Bridge ayrı test sürecidir; kaybında Gazebo ve native
durum okuyucusu canlı kalır. Testin yaratmadığı bir süreç öldürülmez.
Varsayılan stock hareket zincirine rogue nonzero gönderilmedi; bu dünyanın
bütün native sürücüleri derleme seviyesinde daima sıfırdır.

Native kayıt `joint_commands` alanını doğrudan ECM JointVelocityCmd
component'lerinden okur. `native.jsonl.gz` bütün matris örneklerini saklar;
bağımsız `ros.jsonl.gz` Gazebo fiziksel pozu/contact ve gerçek action
durumlarını içerir. Sıfır hedef ve duran fiziksel gövde, hareketten frenleme
kanıtı sayılmaz.

Child testinin üst atamaları ayrı SQLite fixture'ıdır. Ürün FM'ye task
gönderilmedi, fixture Outbox dispatcher'ı başlatılmadı. Gerçek Nav2 child
UUID'leri/terminal status ve tam Path byte hash'leri kayıtlıdır; bu sonuç
gerçek ExecuteTask veya taşıma COMPLETED kabulüne çevrilmez. Üç fixture DB'de
terminal sonrası release reddi ve sahipliğin korunduğu ayrıca kontrol edildi.

İlk startup mapping'leri `--ros-args` sonuna koyduğu için FAIL oldu. Sonraki
matris, öldürülen DDS subscriber'ın ghost graph kaydını yeni bridge hazır
sanıp mesajını kaybetti; FAIL olarak korundu. Test, tekrar edilen aynı
mesajın gerçek native reddini bekleyecek şekilde düzeltildi ve temiz reset
yapıldı. Güvenlik deadline'ı büyütülmedi veya ağdan rearm eklenmedi.

## Peer sorgu ve regresyonlar

Peer C++ BufferCore değişikliği için aynı 10 native test yeniden çalıştırıldı:

```sh
docker run --rm --name c5-peer-buffer-native-tests --workdir /workspace \
  --env ROS_DOMAIN_ID=227 --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  --volume /Users/murat/develop/ros2-fleet-manager-demo:/workspace:ro \
  --volume /tmp/c5-peer-build-20261118:/peer-build \
  ros2-fleet-c5-validation:humble-fortress bash -ec \
  'source /opt/ros/humble/setup.bash; colcon --log-base /peer-build/log build --base-paths interfaces/fleet_interfaces ros2_ws/src/fleet_perception --build-base /peer-build/build --install-base /peer-build/install; source /peer-build/install/local_setup.bash; colcon --log-base /peer-build/log test --build-base /peer-build/build --install-base /peer-build/install --packages-select fleet_perception --event-handlers console_direct+; colcon --log-base /peer-build/log test-result --test-result-base /peer-build/build --verbose'

docker exec c5-native-20261118T080634Z-e136c7eaa9ae bash -ec \
  'source /opt/ros/humble/setup.bash; export PYTHONPATH=/workspace:/workspace/backend:$PYTHONPATH; python3 docker/simulation-warehouse-grid/peer_awareness_probe.py config/fleet.warehouse-30x18.yaml /evidence/live/peer-final.jsonl --duration 10'
```

10 gtest PASS, 0 skip; colcon 11 wrapper dahil sayıdır. Son 10 s durağan probe
182/182 current raporu ve 0 TF thread uyarısı verdi. Önceki hareketli peer
kabul senaryosu bu değişiklikten sonra yeniden koşulmadı.

Host son seçki:

```sh
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
  /tmp/c5-perf-test-venv/bin/python -m pytest -q \
  tests/test_peer_awareness_config.py tests/test_traffic_child_binding.py \
  tests/test_traffic_protocol.py tests/test_traffic_motion_gate.py tests/test_traffic_core.py \
  tests/test_fleet_manager_outbox.py tests/test_executor_safety.py \
  tests/test_c43_station_dispatch.py tests/test_c44_charging.py tests/test_ros2_route_resolver.py
```

**252 PASS, 0 SKIP.** Aynı Humble container'ında gerçek ROS tipleriyle
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `-p no:cacheprovider` kullanılarak child,
protocol, protocol_ros2, motion gate, core ve Outbox seçkisi **188 PASS / 0 SKIP**
verdi. Bunlar hareketli Gazebo güvenlik qualification'ı değildir.

```sh
git diff --check
```

Python sözdizimi, yeni kaynak whitespace ve Markdown göreli bağlantıları da
kontrol edildi. Mermaid kaynağı SVG ve PNG'ye render edilip görsel incelendi.

## Kapanış ve arşiv

Container adı/image/workspace mount'u doğrulandıktan sonra yalnız bu görevin
oturumları `docker stop --time 120 <session>` ile kapatıldı. Vite, kendi
workspace/port/PID denetimiyle kapatıldı. Son üç oturumun bütün alt süreçleri
0; ilk startup simulation=1. OOM yok. Gizli `/run` provision dosyaları arşive
alınmadı. Yeni PDF yoktur; eski kanıt/kişisel notlar korunur.

Arşiv gzip ile saklandı. [Manifest](traffic-integration-2026-11-18/manifest.json)
dosya SHA-256 değerlerini, [DB incelemesi](traffic-integration-2026-11-18/database-checks.json)
integrity/foreign-key ve fixture claim/Outbox sonuçlarını tutar. Varsayılan
launcher'a deney entegrasyonu ve B6B hareket yetkileri kapalı bırakıldı;
main'e veya başka dala commit/push yoktur.
