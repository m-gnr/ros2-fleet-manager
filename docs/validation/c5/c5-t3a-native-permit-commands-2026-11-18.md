# C5-T3A — Komutlar, ortam ve kanıt eki

18 Kasım 2026. [Sonuç raporu](c5-t3a-native-permit-2026-11-18.md).
Komutlar depo kökünden çalıştırıldı. Yeni build/test ve canlı koşular önceki
durdurma kanıtından ayrıdır; eski kayıtlar üzerine yazılmadı. `start_demo.sh`
bu görevde çalıştırılmadı/değiştirilmedi. Aşağıdaki canlı komutlar yalnız yeni
DB/reset ile sıfır-komut deneyi başlatır; ürün hareket reçetesi değildir.

## Başlangıç ve test ortamı

```bash
cd /Users/murat/develop/ros2-fleet-manager-demo
git status --short
git diff --stat
git ls-remote origin refs/heads/main
docker ps --format '{{.Names}} {{.Status}}'
```

Başlangıç HEAD/uzak main `f94ed776c616334c17a3ce6b79e4bf5192d75508`;
dal `codex/c5-t3a-native-permit-context`, mevcut 19 kaynak/test değişikliği
durdurma snapshot'ıyla eşit. Açık container yoktu. Host test venv'i mevcut
`/tmp/c5-perf-test-venv`; Docker image `c5-b6b5-build:local`, Humble/Fortress,
CycloneDDS, aarch64. Image ID/paket sürümleri yeni native build kanıtındadır.
`/tmp/c5-t2-build-20261118` mevcut T2 IDL/BT/perception overlay'i salt okunur
kullanıldı; yeni native kod ayrı temiz dizinlerde derlendi. T2 native peer
gtest sonucu tarihsel kanıttır; bu görevde yeniden derlenmiş sayılmaz.

## Host ve ROS seçkileri

Son geniş host komutu (**375 PASS**, exit 0):

```bash
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
  /tmp/c5-perf-test-venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_native_permit_context.py tests/test_traffic_product_child.py \
  tests/test_traffic_child_binding.py tests/test_peer_awareness_config.py \
  tests/test_traffic_protocol.py tests/test_traffic_motion_gate.py tests/test_traffic_core.py \
  tests/test_fleet_manager_outbox.py tests/test_fleet_manager_domain.py \
  tests/test_executor_safety.py tests/test_executor_state_machine.py \
  tests/test_b6b4_topology.py tests/test_c43_station_dispatch.py \
  tests/test_c44_charging.py tests/test_ros2_route_resolver.py
```

Log `checks/c5-t3a-resume-regression-a3.log.gz`. Ara `-a1` 371 PASS;
ayrı ilk hedefli seçki dört dosyayla 163 PASS (`unit-a1`).
Son ROS komutu (**84 PASS**, exit 0):

```bash
docker run --rm --init --name c5-t3a-resume-ros4 --network none --workdir /workspace \
  --env ROS_DOMAIN_ID=226 --env ROS_LOCALHOST_ONLY=1 \
  -v /Users/murat/develop/ros2-fleet-manager-demo:/workspace:ro \
  -v /tmp/c5-t2-build-20261118:/build:ro c5-b6b5-build:local bash -ec '
  source /opt/ros/humble/setup.bash
  source /build/install/local_setup.bash
  export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:$PYTHONPATH
  export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
  python3 -m pytest -q -p no:cacheprovider \
    tests/test_native_permit_context.py tests/test_native_permit_ros2.py \
    tests/test_traffic_product_child.py tests/test_traffic_product_child_ros2.py \
    tests/test_traffic_protocol_ros2.py tests/test_executor_safety_ros2.py
  '
```

Log `checks/c5-t3a-resume-ros-a4.log.gz`; ara domain 223/a1 **76 PASS**,
224/a2 **80 PASS**. Seçkiler örtüşür; sayıları toplanmaz. Bazı ROS fixture
endpoint'leri fake'dir; Gazebo süreç kaybı kanıtı aşağıdaki koşulardadır.
Tam depo suite'i veya hareketli görev kabulü çalıştırılmadı.

## Native build ve üç CTest

```bash
bash docker/experiments/c5-b6b7/run_native.sh /tmp/c5-t3a-native-resume-20261118
bash docker/experiments/c5-b6b7/run_native.sh /tmp/c5-t3a-native-resume-20261118-v2
```

İkisi de temiz build ve **3/3 CTest / exit 0**. Son build, nonzero ret
tanısını ve onu izleyen paket sonrası kalıcılık testini içerir. Script
`--network none`, repo salt okunur, yeni `/build`, Release `-O2 -UNDEBUG`
kullanır. Test assert'leri kapatılmaz. Son SHA:
`8979ce39d5b9f3f452a51c6a36f5233e35c7e89d8571354532175cba55f57b9c`.
Binary/venv/cache Git'e alınmadı; kaynak hash'leri, binary hash'i, build/test
logları, image ID ve paket listeleri `native-build/` altında korunur.

## Canlı komut ve koşu parametreleri

Aşağıdaki ortak komut gövdesi her satırın literal değerleriyle ayrı ayrı
çalıştırıldı. Aynı anda yalnız bir Gazebo dünyası vardı. Her output klasörü
yeni oluşturuldu; eski hata dünyaları yeniden kullanılmadı.

```bash
docker run --rm --init --name "$container_name" --network bridge --workdir /workspace \
  --env ROS_DOMAIN_ID="$test_domain" --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  --env ROS_LOCALHOST_ONLY=0 --env IGN_PARTITION="$test_partition" \
  -v /Users/murat/develop/ros2-fleet-manager-demo:/workspace:ro \
  -v /tmp/c5-t2-build-20261118:/build:ro \
  -v "$native_build":/b6b7-native:ro \
  -v /tmp/c5-t3a-resume-live-20261118:/evidence \
  c5-b6b5-build:local bash -ec '
  source /opt/ros/humble/setup.bash
  source /build/install/local_setup.bash
  export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
  python3 docker/experiments/c5-t3a/live.py config/fleet.warehouse-30x18.yaml '"/evidence/$run_name --case $test_case"
```

`test_partition=c5-t3a-resume-<run_name>`; container adları ve domain'ler:

| run_name / test_case | container_name | domain | build | Runner sonucu |
|---|---|---:|---|---|
| replan-a1 / replan | c5-t3a-resume-replan | 201 | ilk | 0 / PASS |
| negative-a1 / negative | c5-t3a-resume-negative | 202 | ilk | **1 / FAIL**, ret nedeni örtüldü |
| negative-a2 / negative | c5-t3a-resume-negative2 | 203 | v2 | 0 / PASS |
| executor-loss-a1 / executor-loss | c5-t3a-resume-executor-loss | 204 | v2 | 0 / PASS |
| bridge-loss-a1 / bridge-loss | c5-t3a-resume-bridge-loss | 205 | v2 | **1 / FAIL**, JSON dosyası yarışı |
| bridge-loss-a2 / bridge-loss | c5-t3a-resume-bridge-loss2 | 206 | v2 | 0 / PASS |
| fm-loss-a1 / fm-loss | c5-t3a-resume-fm-loss | 207 | v2 | 0 / PASS |
| startup-missing-a1 / startup-missing | c5-t3a-resume-startup-missing | 208 | v2 | 0 / PASS_SAFE_STARTUP_REFUSAL |
| startup-delayed-a1 / startup-delayed | c5-t3a-resume-startup-delayed | 209 | v2 | 0 / PASS |
| replan-a2 / replan | c5-t3a-resume-replan2 | 210 | v2 | 0 / PASS |

İlk build `/tmp/c5-t3a-native-resume-20261118`, v2 sonuna `-v2` eklenir.
Docker stdout/stderr `/tmp/c5-t3a-resume-<run_name>.log` dosyalarına
yönlendirildi; exit code korunarak `tail -20` gösterildi. Bu logların
gzip kopyaları `checks/` altındadır. Başarısız koşular da `live/` altında
JSON, ROS/native, SQLite ve subprocess loglarıyla saklanır.

Runner yalnız kendi Popen süreçlerine sinyal gönderir. FM/Executor/bridge
kaybında seçilen süreç SIGKILL, kalanlar kontrollü kapanış; Gazebo mevcut
supervisor ile kapanır. Beklenen -9 ve restart exit 1, normal exit 0'dan
`shutdown.json` ile ayrılır. Varsayılan launcher ve ilgisiz süreçler açılmaz.

## Bağımsız kayıt denetimi ve arşiv

```bash
python3 docs/validation/c5/c5-t3a-native-permit-2026-11-18/checks/audit_live.py \
  /tmp/c5-t3a-resume-live-20261118
```

Yedi son koşu geçti. Sonuç `live-audit.json` içinde. İlk audit taslağının
dict/string TypeError'ı analiz hatasıydı; kayıtlar değiştirilmedi.
Canlı runner native MAC'i özel test anahtarıyla kontrol etti; offline audit
anahtarı saklamaz ve yalnız byte/kimlik/SQL bağlarını doğrular. Yeni
arşivde 450 ham dosyanın orijinal byte hash'i, `original-byte-sha256.json`
ile saklanır. `.log/.jsonl/.sqlite3/.sdf/.pgm/.yaml` dosyaları kayıpsız gzip;
zaten `.gz` olan native kayıtlar aynen kopyalandı. Orijinaller `/tmp`'de kaldı.
Private provision/key dosyaları arşive dahil edilmedi. Tarihsel T1/T2 ve
durdurma manifest'leri bağımsız olarak yeniden karşılaştırıldı.

Mermaid CLI 11.12.0 ile SVG ve kontrol PNG'si üretildi; PNG görsel olarak
incelendi, metin/bağlantı kesilmesi görülmedi:

```bash
node /Users/murat/.npm/_npx/bb964472b4759b27/node_modules/@mermaid-js/mermaid-cli/src/cli.js \
  -i docs/diagrams/src/traffic-live-permit-zero.mmd \
  -o docs/diagrams/svg/traffic-live-permit-zero.svg -w 1600 -b white
```

Aynı komutun PNG çıktısı `/tmp/c5-t3a-live-permit-zero.png` olarak alındı.
GitHub üzerinde render testi yapılmadı. Kaynak/varsayılan izolasyonu
`git show f94ed776:<path>` ile byte karşılaştırmasıdır; hash'ler
`default-isolation.json` içinde. Varsayılan demoyu çalıştırmak yeni canlı
hareket testi olacağından bu sıfır-komut görevinde yapılmadı.

Son kontrol ve Git teslim sırası: ilgili manifest/hash/link ve
`git diff --check` doğrulaması → yalnız ilgili dosyaları stage → staged diff
incelemesi → `git fetch origin main` / FF kontrolü → commit → normal
`git push origin HEAD:main` → `git ls-remote` / temiz durum kontrolü.
Force push, geçmiş yeniden yazma veya başka worktree işlemi yoktur.

Tam staged `git diff --check`, iki ham `.diff` kanıtındaki 17 boş context
satırının tek boşluğunu raporladı (exit 2). Bunlar kod kusuru değil, orijinal
Git patch byte'larıdır; kullanıcı koruma talebiyle aynen bırakıldı. Yalnız
bu iki ham patch hariç bütün kaynak/doküman/SVG/kanıt kontrolü exit 0.
`whitespace-checks.json` ve gzip ham çıktı bu ayrımı kaydeder; güvenlik
testi veya izolasyon kontrolü atlanmadı.
