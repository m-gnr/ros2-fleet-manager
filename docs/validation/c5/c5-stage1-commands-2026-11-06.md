# C5 / Aşama 1 — Çalıştırma ve doğrulama komutları

Komutları C5 çalışma ağacının kökünden çalıştırın. Doğrulama Apple Silicon ve mevcut ARM64 C4.5 image'larıyla yürütüldü. Docker Desktop, Node.js (frontend `engines` alanına uygun) ve otomasyon için kurulu Google Chrome gerekir.

## Yerel iki robotlu panel

Önce C4.5'in mevcut [image önkoşullarını](../../../docker/compose/README.md) sağlayın. C5 image'ını kendi Dockerfile'ından oluşturun.

```sh
docker build -f docker/simulation-c5/Dockerfile -t ros2-fleet-c5-validation:humble-fortress .
npm --prefix frontend ci
npm --prefix frontend run build
```

Her koşu için boş kanıt dizini, kullanılmayan DDS domain'i ve loopback portları seçin. Aşağıdaki değerler son kabul koşusunun örneğidir. Ayrı terminaller aynı ortam değişkenlerini almalıdır.

```sh
export DDS_TEST_PAYLOAD=fleet-c5-accept
export ROS_DOMAIN_ID=78
export C5_API_PORT=18768
export C5_UI_PORT=18767
export C5_UI_ORIGIN="http://127.0.0.1:$C5_UI_PORT"
export C43_EVIDENCE_DIR="$(mktemp -d /tmp/fleet-c5.XXXXXX)"

scripts/run_c5_dashboard.sh config --format json > "$C43_EVIDENCE_DIR/compose.json"
scripts/run_c5_dashboard.sh up -d --no-build
```

Frontend'i ayrı terminalde açın. Tarayıcıda `C5_UI_ORIGIN` değerine gidin. Simülasyon hazırlanırken bağlantı yeniden denenir. Bu düzenek süreli C4.5 şarj ve taşıma senaryosunu yürütür.

```sh
npm --prefix frontend run preview
```

Elle izlemek için başka bir terminalde `scripts/run_c5_dashboard.sh api` çalıştırın. Bu komut yalnız web sürecini başlatır. `scripts/run_c5_dashboard.sh stop-api` web sürecini kapatır. Otomatik Chrome kabulü API başlatma, durdurma ve yeniden başlatma adımlarını kendisi yürütür. Otomasyon sırasında ayrı bir API süreci açmayın.

```sh
node frontend/tests/live-acceptance.mjs
```

Canlı koşu bittiğinde temiz kapanışı ve SQLite'ı denetleyin. Chrome otomasyonu tamamlandığında backend kısa kapalı panel ölçümünü bitiriyor olabilir.

```sh
docker wait "$DDS_TEST_PAYLOAD-backend-1"
scripts/run_c5_dashboard.sh stop simulation
docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  "$DDS_TEST_PAYLOAD-backend-1" "$DDS_TEST_PAYLOAD-simulation-1"
scripts/run_c5_dashboard.sh logs --no-color > "$C43_EVIDENCE_DIR/compose.log"
scripts/run_c5_dashboard.sh down
sqlite3 "$C43_EVIDENCE_DIR/c5-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
```

## Otomatik seçkiler

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-c1.txt -r requirements-c5-test.txt
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator
.venv/bin/python -m fleet_config config/fleet.yaml
.venv/bin/python -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test
npm --prefix frontend test
npm --prefix frontend audit
git diff --check
```

Humble/CycloneDDS seçkisi C5 image'ında çalıştırıldı. C2.3 ve C3.3.3 config testleri aynı konteynerde ayrı çağrılardır.

```sh
docker run --rm --name fleet-c5-ros-regression \
  -e ROS_DOMAIN_ID=66 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" -w /work --entrypoint bash \
  ros2-fleet-c5-validation:humble-fortress -c '
set -e
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:$PYTHONPATH
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros tests/ ros2_ws/src/fleet_robot_executor/test
for test in docker/simulation-c2-3/test_config.py docker/simulation-c3-3-3/test_config.py; do
  python3 -m pytest -q -p no:cacheprovider -p no:launch_testing -p no:launch_ros "$test"
done
'
```

Bağımsız enerji regresyonu [C4.5 enerji profili](../c4/c4-5-commands-2026-11-06.md) üzerinden, `fleet-c5-energy` projesinde ve DDS domain 72 ile çalıştırıldı. C5'in canlı şarj seçkisi mevcut C4.5 şarj senaryosunun denetimlerini içerir.

İki değişen SVG, [mevcut Mermaid temasını](../organization/organization-commands-2026-10-26.md#mermaid-ve-svg-üretimi) ve `@mermaid-js/mermaid-cli@11.12.0` sürümünü kullanır. Çıktılar XML olarak ayrıştırıldı ve katalogdaki Mermaid blokları kaynakla karşılaştırıldı.
