# C5-T3B — Çalıştırılmış komutlar ve kanıt eki

18 Kasım 2026. [Sonuç raporu](c5-t3b-health-stop-2026-11-18.md) ·
[T3C önkoşul ve planı](c5-t3c-braking-plan-2026-11-18.md).
Komutlar depo kökünden çalıştırıldı. Varsayılan demo/GUI başlatılmadı;
deneysel native sürücü bütün koşularda yalnız sıfır komut kabul etti.

## Başlangıç ve ortam

```bash
cd /Users/murat/develop/ros2-fleet-manager-demo
git status --short
git log -1 --format='%H %s'
git ls-remote origin refs/heads/main
docker ps --format '{{.Names}} {{.Status}}'
git switch -c codex/c5-t3b-health-stop-envelope
```

Başlangıç temiz, HEAD/uzak main `e4b04ad6a4fc79a485b58f747cb0b557fd58aaa9`.
Image `c5-b6b5-build:local`, Humble/Fortress; canlı koşularda CycloneDDS.
Mevcut T2 `/tmp/c5-t2-build-20261118` overlay'i salt okunur kullanıldı;
IDL/BT observer/PeerRobotLayer yeniden değiştirilmedi veya build edilmiş
gibi sunulmadı. Docker gözlemi 8 CPU, 8.319.770.624 byte bellek raporladı;
bu bir performans/ölçek garantisi değildir.

## Unit / integration ve native

Geniş host seçkisi:

```bash
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
  /tmp/c5-perf-test-venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_robot_health.py tests/test_stop_envelope.py tests/test_health_fixture_transports.py \
  tests/test_native_permit_context.py tests/test_traffic_product_child.py \
  tests/test_traffic_child_binding.py tests/test_peer_awareness_config.py \
  tests/test_traffic_protocol.py tests/test_traffic_motion_gate.py tests/test_traffic_core.py \
  tests/test_fleet_manager_outbox.py tests/test_fleet_manager_domain.py \
  tests/test_executor_safety.py tests/test_executor_state_machine.py \
  tests/test_b6b4_topology.py tests/test_c43_station_dispatch.py \
  tests/test_c44_charging.py tests/test_ros2_route_resolver.py
```

ROS seçkisinde image, `--network none`, repo ve overlay salt okunur,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `/opt/ros/humble/setup.bash` ve
`/build/install/local_setup.bash` kullanıldı. PYTHONPATH host seçkisinin
aynı workspace paketlerini `/workspace` altında gösterir. Son seçki:

```bash
python3 -m pytest -q -p no:cacheprovider \
  tests/test_robot_health.py tests/test_stop_envelope.py tests/test_health_fixture_transports.py \
  tests/test_robot_health_ros2.py tests/test_native_permit_context.py tests/test_native_permit_ros2.py \
  tests/test_traffic_product_child.py tests/test_traffic_product_child_ros2.py \
  tests/test_traffic_protocol_ros2.py tests/test_executor_safety_ros2.py
```

Ara ROS domain'leri 227–232 ve 174–179; son koşu farklı izole domain'dedir.
İlk domain 241 denemesi exit 1 verdi. Ayrı minimal probe kurulu FastDDS'den
`Calculated port number is too high ... domainId ... over 232` hatasını
doğruladı; log korunur. Alan/threshold gevşetilmedi. Kurulu Humble callback
uygulaması `inspect.getsource(Executor._take_subscription)` ile okundu:
yalnız `msg_info[0]` callback'e verilir. Graph endpoint kümesi mesajın
yayıncı kimliğine dönüştürülmedi; ham API çıktısı da kanıttadır.

```bash
bash docker/experiments/c5-b6b7/run_native.sh /tmp/c5-t3b-native-20261118-a1
bash docker/experiments/c5-b6b7/run_native.sh /tmp/c5-t3b-native-20261118-a2
```

Her biri yeni dizinde temiz build, assert'ler açık `-O2 -UNDEBUG` ve 3 CTest.
Son binary a2, açık/profile bağlı sağlık cadence'ini içerir. Image ID,
paket/sürüm, source SHA-256, build/test ve binary SHA-256 arşivlenir.
Native binary Git'e alınmaz. Değişen ortak dosyanın health satırı
`C5_AUTH_ZERO_ONLY` içindedir; B6B.5'in normal sıfır build'i ayrıca
`cmake -S docker/experiments/c5-b6b5 -B /build`, `cmake --build /build -j2`,
`ctest --test-dir /build --output-on-failure` ile yeni dizinde doğrulandı.
Lease kaynak kodu değiştirilmedi.

## İzole canlı komut

Her satır yeni `/evidence/<run>` dizini/DB/session ve fiziksel reset kullanır.
Koşular seri çalışır; aynı anda ikinci Gazebo yoktur. Gerçek komut gövdesi:

```bash
docker run --rm --init --name "$container_name" --network bridge --workdir /workspace \
  --env ROS_DOMAIN_ID="$test_domain" --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  --env ROS_LOCALHOST_ONLY=0 --env IGN_PARTITION="c5-t3b-$run_name" \
  -v /Users/murat/develop/ros2-fleet-manager-demo:/workspace:ro \
  -v /tmp/c5-t2-build-20261118:/build:ro \
  -v /tmp/c5-t3b-native-20261118-a2:/b6b7-native:ro \
  -v /tmp/c5-t3b-live-20261118:/evidence c5-b6b5-build:local bash -ec '
  source /opt/ros/humble/setup.bash
  source /build/install/local_setup.bash
  export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
  python3 docker/experiments/c5-t3b/live.py config/fleet.warehouse-30x18.yaml "$@"
  ' t3b-run "/evidence/$run_name" --case "$test_case"
```

`container_name=c5-t3b-final-<run>`. Çalıştırılmış seri script'ler ve
literal domain/run/exit TSV'leri arşivdedir. Son değerlendirmede kullanılan
koşular:

| run_name | test_case | domain | Kaynak aşaması |
|---|---|---:|---|
| replan-a5 | replan | 220 | V5 |
| fm-loss-a5 | fm-loss | 221 | V5 |
| bridge-loss-a3 | bridge-loss | 222 | V5 |
| negative-a1 | negative | 223 | V5 |
| update-freeze-a3 | update-freeze | 224 | V5 |
| sensor-loss-a3 | sensor-loss | 228 | V6 |
| controller-inactive-a2 | controller-inactive | 229 | V6 |
| executor-loss-a2 | executor-loss | 230 | V6 |

V5→V6 yalnız fixture'ın TF helper PID seçimini ve üreticileri bridge'den
önce durduran kapanış sırasını değiştirir. Sağlık/native/hesap algoritması,
bütçeler ve iletilen ölçümler aynıdır. V5/V6 source hash'leri ve önceki tüm
denemeler korunur. Önceki seri script bir hatada durdu; sonraki satırları
çalıştırmış sayılmaz. Özet PASS olsa bile CLI veya teardown nonzero ise
koşu kabul edilmez.

İlk a1 native binary ile `update-freeze-a1/a2`, `sensor-loss-a1`,
`controller-inactive-a1`, `executor-loss-a1`, `fm-loss-a1/a2/a3`,
`bridge-loss-a1`, `replan-a1` ara koşuları yapıldı. Bazıları sınırlı işlevsel
kanıt verdi, bazıları başarısız oldu; son matrix yerine kullanılmaz.
a2 ile ara `replan-a2/a3/a4`, `bridge-loss-a2`, `sensor-loss-a2` ve
gözlemcisiz T3A `baseline-replan-a1/a2` ayrıca arşivdedir. Fail nedenleri
raporda ayrılır; loglar temizlenmedi.

Hata hedefleri yalnız bu container'ın gerçek alt süreçleridir: odometry
bağlantısı/TF helper manifest PID'leri, namespace'e ait AMCL PID'si, gerçek
controller lifecycle servisi, native kitaplık mapping'ini taşıyan Gazebo
PID'si veya koşucunun kendi Popen handle'ı. Hiçbir host/kullanıcı/başka
worktree sürecine sinyal gönderilmez. SIGSTOP daima finally ile SIGCONT
alır. İzin/stop/release kanıtı üretilmez; ilk gerçek reset ve güncel READY
gelmeden initial Executor/traffic geometry kabul edilmez.

## Denetim ve koruma

```bash
python3 docs/validation/c5/c5-t3b-health-stop-2026-11-18/checks/audit_live.py \
  /tmp/c5-t3b-live-20261118
git diff --check
```

Offline audit private anahtar olmadan MAC'i yeniden tasdik etmez. Canlı
verifier doğrulaması, aynı ham paket byte'ları, bilinen committed komut,
gerçek atama/child/Path, PENDING Outbox, sıfır hedef, UNKNOWN fiziksel
duruş, release reddi ve normal/beklenen process exit'leri ayrı kontrol edilir.
Ham native/ROS/health, SQLite backup, SDF/parametre/envanter, başarısız
loglar ve stdout/stderr kayıpsız gzip ile korunur; açılmış orijinal byte
SHA-256'ları ayrıca kaydedilir. Provision anahtarları arşive alınmaz.

166 mevcut varsayılan dosya ve T1/T2/T3A'nın dört manifest'i başlangıçla
karşılaştırıldı. GUI veya varsayılan stock demo hareketi bu sıfır-komut
görevinde tekrar başlatılmadı; byte eşitliği canlı GUI kanıtı diye sunulmaz.

Mermaid CLI 11.12.0 ile SVG ve kontrol PNG'si üretildi, PNG incelendi:

```bash
node /Users/murat/.npm/_npx/bb964472b4759b27/node_modules/@mermaid-js/mermaid-cli/src/cli.js \
  -i docs/diagrams/src/traffic-health-stop.mmd \
  -o docs/diagrams/svg/traffic-health-stop.svg -w 1600 -b white
```

Aynı komutun PNG çıktısı `/tmp/c5-t3b-health-stop.png`; GitHub render testi
yapılmadı. Kabul ve scope kontrolünden sonra normal Git commit/FF push,
`ls-remote`, HEAD/origin/main ve temiz çalışma ağacı kontrolü yapılır.
Force push/reset/clean/stash/başka worktree değişikliği yapılmaz.
