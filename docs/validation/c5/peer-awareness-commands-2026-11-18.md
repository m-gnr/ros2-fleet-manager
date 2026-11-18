# C5 robotlar arası farkındalık — komut ve kanıt eki

18 Kasım 2026. Komutlar depo kökünden çalıştırıldı. [Rapor](peer-awareness-2026-11-18.md)
sonucun sınırını belirler; bu ek bir üretim kurulum veya genel güvenlik kabulü
değildir. [Kanıt dizini](peer-awareness-2026-11-18/).

## Başlangıç, baseline ve izole adaylar

```sh
pwd
git status --short
source .venv/bin/activate
./scripts/start_demo.sh
```

Başlangıç çalışma ağacı temizdi; yerel HEAD ve image bilgisi
[ortam kaydındadır](peer-awareness-2026-11-18/environment.json).
Baseline normal launcher ile açıldı. Başlatılan yalnız bu workspace'e ait
oturumun adı, domain ve kanıtı runner'ın `session.json` dosyasına yazıldı.
Başka worktree durdurulmadı veya değiştirilmedi. Fiziksel reset/AMCL/Nav2/TF
kapıları geçilmeden API üzerinden görev gönderilmedi.

Baseline için önce probe, ardından aynı katalog/API yolu kullanıldı:

```sh
docker exec c5-demo-20261118T063426Z-13936ad0dbed bash -ec \
  'source /opt/ros/humble/setup.bash; export PYTHONPATH=/workspace:/workspace/backend:$PYTHONPATH; python3 docker/simulation-warehouse-grid/peer_awareness_probe.py config/fleet.warehouse-30x18.yaml /evidence/live/peer-probe-compressed.jsonl --duration 580'
```

İlk probe çağrısında `PYTHONPATH` ROS yolunu ezdiğinden rclpy import edilemedi.
Mevcut yol korunarak düzeltildi. İlk başarılı recorder büyük grid JSON'u
yazıyordu; salt okunur probe durdurulup kayıpsız int8/zlib grid kaydıyla devam
edildi. İlk kayıt da korunur. Bu probe değişimi ürün veya politika değişimi
değildir; zaman pencereleri raporda performans karşılaştırması yapılmaz.

Gönderim payload'u gerçek `GET /api/task-catalog` session/digest alanlarını,
yeni request UUID'sini ve MEDIUM önceliği kullanır. Üç çift:
`pick_A1 → packing_1`, `pick_B2 → delivery-01`, `pick_D1 → shipping_2`.
[Gönderim aracı](peer-awareness-2026-11-18/tools/c5-peer-submit.py) ve her
koşunun `submissions.json` dosyası gerçek istek/yanıtları tutar. FM DB'sine
doğrudan görev yazılmadı.

Adaylar standart `c5_demo_start.main()` runner'ına yalnız
`--peer-awareness-experiment` ekleyen dış test aracıyla başlatıldı:

```sh
source .venv/bin/activate
python3 /tmp/c5-peer-start-candidate.py
python3 /tmp/c5-peer-submit.py c5-demo-20261118T064710Z-25037b4febf4
python3 /tmp/c5-peer-start-candidate.py
```

[Arşivlenmiş araç](peer-awareness-2026-11-18/tools/c5-peer-start-candidate.py),
A2/A3 `launch-command.json` dosyaları ve bütün koşuların `preflight.json`
dosyaları gerçek Docker/harness argümanlarını saklar. Araç oturumu dinamik
isimlendirir; sonraki çalıştırmada aynı ad/port varsayılmaz. Tarihsel kontrol
araçlarındaki sabit oturum adları yeniden kullanılamaz.

A1'de düğüm envanteri kontrol edildi:

```sh
docker exec c5-demo-20261118T064710Z-25037b4febf4 bash -ec \
  'source /opt/ros/humble/setup.bash; ros2 node info /robot_alpha/global_costmap/global_costmap'
```

Abonelik `/robot_alpha/global_costmap/tf` idi; doğru TF uçlarıyla düzeltildi.
A1 durduruldu; mevcut kuyruğu/DB'yi sürdürmek yerine temiz A2 oturumu açıldı.
A2'de görevlerden önce altı peer katmanının current=true olduğu kontrol edildi
([stationary-health.json](peer-awareness-2026-11-18/candidate-a2-transport-park/stationary-health.json)).
A2 probe komutu baseline ile aynı, süre 650 s ve çıktı `peer-probe.jsonl` idi.
Üç görev/park tamamlandıktan sonra koşu kontrollü durduruldu; 650 s tamamlanmış
test süresi olarak sunulmaz. Gerçek probe penceresi 331,38 s'dir.

## Ayrı şarj ve TF kesintisi

```sh
source .venv/bin/activate
python3 /tmp/c5-peer-start-candidate.py --battery
python3 /tmp/c5-peer-charge-control.py
python3 /tmp/c5-peer-tf-fault.py
```

A3 için aynı runner'ın simülasyon test kontrolü mevcut
`FLEET_SIM_BATTERY_CONTROL=1` ile etkinleştirildi. Anahtar yalnız `/tmp`
dosyasında 0600 izinle tutuldu; rapor/kaynaklara konmadı. Arşivlenmiş Docker
komutundaki anahtar maskelidir. Kontrol [aracı](peer-awareness-2026-11-18/tools/c5-peer-charge-control.py)
mevcut session'ları okuyup `soc_percent=24.0`, `mode=NORMAL`,
`safe_test_environment=true`, `confirm_bulk_soc=true` gönderdi. Üç yanıt
VERIFIED ve ayrı servis geri okumasıyla doğrulandı. Bu, doğal düşük enerji
şarj politikasını tetikledi; sahte dock/poz/hız üretmedi.

Robotlar şarjda dururken [TF hata aracı](peer-awareness-2026-11-18/tools/c5-peer-tf-fault.py)
yalnız doğrulanan bu container'daki `/workspace/docker/simulation-warehouse-grid/tf.py`
sürecine SIGSTOP gönderdi ve `finally` içinde SIGCONT ile devam ettirdi.
Monotonik durdurma/devam damgaları `tf-fault.json` içindedir. Global/yerel
ilk false/true süreleri probe'dan yeniden hesaplandı. Hareketli stop veya tüm
iletişim kesintisi sonucu çıkarılmaz.

Koşu sonlarında root mount/isim doğrulandıktan sonra yalnız ait olunan container
`docker stop --time 120 <oturum>` ile durduruldu. Vite PID'si workspace/port
kontrolüyle kapatıldı. Başlangıç launcher'ı ayrıca doğrulanmış PID'ye SIGINT
ile kapatıldı. Başka süreçlere toplu kill/cleanup uygulanmadı.

## Native ve host kontrolleri

Gerçek Humble/C++ katmanı, ROS callback'leri, Nav2 remap ve özel callback grubu:

```sh
docker run --rm --name c5-peer-native-tests-20261118 \
  --workdir /workspace --env ROS_DOMAIN_ID=227 \
  --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  --volume /Users/murat/develop/ros2-fleet-manager-demo:/workspace:ro \
  --volume /tmp/c5-peer-build-20261118:/peer-build \
  ros2-fleet-c5-validation:humble-fortress bash -ec \
  'source /opt/ros/humble/setup.bash; colcon --log-base /peer-build/log build --base-paths interfaces/fleet_interfaces ros2_ws/src/fleet_perception --build-base /peer-build/build --install-base /peer-build/install; source /peer-build/install/local_setup.bash; colcon --log-base /peer-build/log test --build-base /peer-build/build --install-base /peer-build/install --packages-select fleet_perception --event-handlers console_direct+; colcon --log-base /peer-build/log test-result --test-result-base /peer-build/build --verbose'
```

Son [native log](peer-awareness-2026-11-18/checks/c5-peer-native-tests-remap-retry.log):
**10 gtest geçti**, CTest wrapper'ıyla colcon 11; skip yok. İlk statik tip
değeri olmayan parametre bildirimi, `test-result` log dizini ve init öncesi
fixture executor context hataları önceki loglarda korunur. Dünya/actuator
başlatılmadı; native test fiziksel duruş kanıtı değildir.

Host `.venv` içinde pytest yoktu; ürün bağımlılığı değiştirilmedi. Daha önce
kurulmuş bağımsız `/tmp/c5-perf-test-venv` kullanıldı:

```sh
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
  /tmp/c5-perf-test-venv/bin/python -m pytest -q \
  tests/test_peer_awareness_config.py tests/test_traffic_core.py \
  tests/test_traffic_protocol.py tests/test_fleet_manager_outbox.py

PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
  /tmp/c5-perf-test-venv/bin/python -m pytest -q \
  tests/test_config.py tests/test_warehouse_grid.py tests/test_executor_safety.py \
  tests/test_traffic_motion_gate.py tests/test_ros2_route_resolver.py \
  tests/test_c43_station_dispatch.py tests/test_c44_charging.py \
  tests/test_battery_consumption.py tests/test_battery_control.py

git diff --check
```

Sonuçlar [138 geçti](peer-awareness-2026-11-18/checks/c5-peer-host-tests-remap.log),
[224 geçti](peer-awareness-2026-11-18/checks/c5-peer-regression.log); skip yok.
Tam host suite veya eski bütün canlı senaryolar bu çalışmada yeniden
çalıştırılmadı. Önceki performans raporundaki iki tarihsel host hatası yeni koşu
sonucu olarak sunulmaz.

## Replay, diyagram ve kayıt koruması

```sh
python3 docker/simulation-warehouse-grid/peer_awareness_analyze.py \
  docs/validation/c5/peer-awareness-2026-11-18/baseline /tmp/peer-baseline-replay.json
python3 docker/simulation-warehouse-grid/peer_awareness_analyze.py \
  docs/validation/c5/peer-awareness-2026-11-18/candidate-a2-transport-park /tmp/peer-a2-replay.json
python3 docker/simulation-warehouse-grid/peer_awareness_analyze.py \
  docs/validation/c5/peer-awareness-2026-11-18/candidate-a3-charge-tf /tmp/peer-a3-replay.json
```

Observer fiziksel/contact/action/SQLite kayıtları ile ayrı peer probe saklanır.
`GRID.data_int8_zlib` kayıpsız signed int8'dir. Replay fiziksel örnekleri en
fazla 50 ms damga farkıyla eşler; rapor→grid farkı en fazla 50 ms ve aynı frame
olmalıdır. Eksik eşleşme başarı sayılmaz. Minima sürekli uzaklık sınırı değildir.
Snapshot, action UUID/gerçek epoch ve DB kalıcı sonucu birbirinden ayrıdır.

Mermaid CLI'nin mevcut yerel kurulumuyla SVG üretildi; PNG render'ı görsel
olarak incelendi. Yeni PDF yoktur. Eski rapor/kişisel notlar değiştirilmedi.
Ham dosyalar gzip ile saklandı; dört DB `integrity_check=ok`, foreign-key hata
yok. [SHA manifesti](peer-awareness-2026-11-18/manifest.json) ve
[kaynak koruma kaydı](peer-awareness-2026-11-18/preservation.json) arşiv ve
mevcut performans/safety kaynaklarının korunduğunu kaydeder. Commit/push yoktur.
