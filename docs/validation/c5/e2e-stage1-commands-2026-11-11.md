# C5 — Aşama 1 uçtan uca doğrulama komutları

11 Kasım 2026 · [Sonuçlar ve başarısız kontroller](e2e-stage1-validation-2026-11-11.md)

Bütün komutlar ilgili worktree kökünden çalıştırıldı. Ana worktree'de yalnız Git durumu ve belgeler okundu; testler 30 × 18 m değişikliklerinin bulunduğu `/Users/murat/develop/ros2-fleet-manager-c5-warehouse-grid` kökünde yapıldı. Kullanıcı değişiklikleri commit edilmedi. Aşağıdaki port/domain/container adları bu koşuya aittir; yeni tekrar için boş değerler ve yeni DB yolu seçilmelidir.

## Başlangıç kaydı

```sh
git status --short --branch
git worktree list
git log -6 --oneline
git rev-parse HEAD
docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker image inspect ros2-fleet-c5-validation:humble-fortress
docker info --format '{{.OperatingSystem}} arch={{.Architecture}} cpus={{.NCPU}} memory={{.MemTotal}}'
```

Python `subprocess`, `hashlib` ve `pathlib` ile Git çıktıları, başlangıç `git diff --binary`, config/şema/Nav2/lockfile SHA-256 değerleri [baseline](e2e-stage1-2026-11-11/baseline.json) ve [patch](e2e-stage1-2026-11-11/baseline.diff) dosyalarına yazıldı. Ürün kaynaklarının ve yeni doğrulama araçlarının SHA-256 değerleri [manifestte](e2e-stage1-2026-11-11/source-manifest.json) bulunur. Manifest hash'i, koruma karşılaştırması ve son kaynak durumları [son denetim kaydındadır](e2e-stage1-2026-11-11/final-audit.json).

## Derleme ve ilk ortam denemeleri

Hazır ARM64 C5/Fortress image'ı kullanıldı; image build yapılmadı. İlk container'da şu komut ürün IDL'sini derledi:

```sh
source /opt/ros/humble/setup.bash
colcon --log-base /evidence/build-log build --base-paths interfaces/fleet_interfaces \
  --build-base /evidence/build --install-base /evidence/install
```

Sonuç **0**, bir paket derlendi; [çıktı](e2e-stage1-2026-11-11/container-a.log). Ürün Python paketleri salt okunur workspace'ten `PYTHONPATH` ile kullanıldı. Sonraki denemeler aynı IDL install'ını kaynakladı.

İlk `scenario-a` Battery Simulator başlatma hatası ve `scenario-a2` şema readiness hatasıyla görevsiz kapandı. `scenario-a3` bind mount SQLite okuyucu hatasıyla görev sürerken durdu. [Rapor](e2e-stage1-validation-2026-11-11.md#ortam-denemeleri-ve-kapanış) bu denemeleri başarıdan ayırır. Ayrı container logları ve senaryo dizinleri korunmuştur. A3 browser script'i eski koşuyu beklemeye devam ettiği için yalnız bu işin Node sürecine TERM gönderildi; tam kapanışlı Chrome raporu/video sonlandırması A3 için doğrulanmadı. A3 WS ve ekran görüntüleri korunmuştur.

Video desteği için çalıştırıldı; sonuç **0**:

```sh
npx --prefix frontend playwright install ffmpeg
```

## Son A ve B — gerçek ürün + Chrome

Frontend dev sunucusu bir kez başlatıldı; mevcut TypeScript kaynakları kullanıldı:

```sh
C5_UI_PORT=20081 C5_API_PORT=20082 npm --prefix frontend run dev \
  > docs/validation/c5/e2e-stage1-2026-11-11/frontend.log 2>&1
docker volume create fleet-c5-stage1-20261111
```

Son A koşusunun komutu; shell `source` işlemleri container içindedir:

```sh
docker run --init --name fleet-c5-e2e-stage1-a4 \
  --add-host scene:127.0.0.1 -p 127.0.0.1:20082:20082 \
  -e ROS_DOMAIN_ID=163 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -e ROS_LOCALHOST_ONLY=0 -e LIBGL_ALWAYS_SOFTWARE=1 -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD:/workspace:ro" \
  -v "$PWD/docs/validation/c5/e2e-stage1-2026-11-11:/evidence" \
  -v fleet-c5-stage1-20261111:/var/lib/fleet \
  -w /workspace --entrypoint bash ros2-fleet-c5-validation:humble-fortress -ec '
source /opt/ros/humble/setup.bash
source /evidence/install/setup.bash
export PYTHONPATH=/workspace:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:${PYTHONPATH:-}
python3 docker/simulation-warehouse-grid/stage1_run.py \
  config/fleet.warehouse-30x18.yaml /evidence/scenario-a4 \
  --api-port 20082 --scene-port 20083 --origin http://127.0.0.1:20081
' > docs/validation/c5/e2e-stage1-2026-11-11/container-a4.log 2>&1
```

Başka terminalde gerçek Chrome çalıştırıldı. HTTP/WS interception yoktur. Formdan oluşturulan kabul isteği aynı UUID ve değişmez payload'la browser `fetch` üzerinden tekrarlandı:

```sh
node frontend/tests/stage1-e2e.mjs http://127.0.0.1:20081 \
  docs/validation/c5/e2e-stage1-2026-11-11/chrome-a4 a \
  > docs/validation/c5/e2e-stage1-2026-11-11/chrome-a4.log 2>&1
```

Chrome script'i **0** ile tamamlandı. Bu çıkış fiziksel hassasiyet ve feedback sözleşme kabulünü içermez; bunlar aşağıda ayrıca sınandı. Tamamlanmadan sonra:

```sh
docker stop --time 50 fleet-c5-e2e-stage1-a4
docker inspect fleet-c5-e2e-stage1-a4 \
  > docs/validation/c5/e2e-stage1-2026-11-11/scenario-a4/docker-final.json
```

B koşusu yukarıdaki aynı Docker komutuyla, yalnız `--name fleet-c5-e2e-stage1-b`, `ROS_DOMAIN_ID=164`, output `/evidence/scenario-b`, log `container-b.log` değişiklikleriyle çalıştırıldı. Ayrı DB `/var/lib/fleet/scenario-b.sqlite3`; A DB'si tekrar kullanılmadı.

```sh
node frontend/tests/stage1-e2e.mjs http://127.0.0.1:20081 \
  docs/validation/c5/e2e-stage1-2026-11-11/chrome-b b \
  > docs/validation/c5/e2e-stage1-2026-11-11/chrome-b.log 2>&1
docker stop --time 50 fleet-c5-e2e-stage1-b
docker inspect fleet-c5-e2e-stage1-b \
  > docs/validation/c5/e2e-stage1-2026-11-11/scenario-b/docker-final.json
```

B Chrome script'i **0**. İki son container çıkışı **0**, OOM false; supervisor'ın her alt süreci **0**. Named volume ve container'lar silinmedi. Kaynak mount salt okunur; SQLite yalnız volume'de yazıldı ve ürün kapandıktan sonra SQLite backup API ile kanıt dizinine kopyalandı. Frontend dev süreci iş sonunda durduruldu.

Çalışma sırasında her son container'da ROS graph çıktılarını almak için:

```sh
source /opt/ros/humble/setup.bash
source /evidence/install/setup.bash
ros2 node list --no-daemon
ros2 topic list -t --include-hidden-topics
```

Ayrıca container içinde `uname -a`, `/etc/os-release`, `python3 --version`, ilgili ROS ortam değişkenleri ve `dpkg-query -W ros-humble-nav2-bringup ignition-fortress libdart6.12` kaydedildi.

## Kaynak karşılaştırması, başarısız probe ve statik genişlik

```sh
python3 docker/simulation-warehouse-grid/stage1_summarize.py \
  docs/validation/c5/e2e-stage1-2026-11-11/scenario-a4 \
  docs/validation/c5/e2e-stage1-2026-11-11/chrome-a4
python3 docker/simulation-warehouse-grid/stage1_summarize.py \
  docs/validation/c5/e2e-stage1-2026-11-11/scenario-b \
  docs/validation/c5/e2e-stage1-2026-11-11/chrome-b
```

Son araç sürümü karşılaştırma artifact'ı üretir ve başarısız kontrolde **1** ile çıkar. İki senaryonun sonucu da **başarısız veya doğrulanamadı**. F1 iki koşuda, F2 yalnız B2 pickup'ta başarısızdır. İlk özet sürümü ilerleme stream'ini denetlemiyordu; ilk A çıktısındaki `geçti` ifadesi bütün aşamanın kabulü değildir. Son özetler `EXECUTING`/feedback kontrolünü de içerir; eski başarı ifadesi kabul olarak kullanılmaz.

Aşağıdaki sözleşme probe'u ayrı geçici SQLite ve sahte test mesafe sağlayıcısı kullanır; fiziksel koşu kanıtı değildir. Gerçek adapter callback'ini gerçek consumer'a bağlar. Bilinen hatayı başarısız sonuçla raporlar:

```sh
PYTHONPATH=. /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python \
  docker/simulation-warehouse-grid/stage1_feedback_probe.py \
  > docs/validation/c5/e2e-stage1-2026-11-11/feedback-contract.json
```

Çıkış **1**, TypeError; `ASSIGNED → ASSIGNED`, feedback COMMIT sayısı 0.

SDF'deki collision ölçümlerinden türetilmiş YAML üretip bu YAML üzerinden statik genişlik hesabını yapmak için:

```sh
PYTHONPATH=. /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python \
  docker/simulation-warehouse-grid/stage1_clearance.py \
  config/fleet.warehouse-30x18.yaml \
  docs/validation/c5/e2e-stage1-2026-11-11/scenario-a4/generated \
  docs/validation/c5/e2e-stage1-2026-11-11
```

Çıkış **0**, `STATIC_PRECHECK_NOT_TRAFFIC_ACCEPTANCE`. Fiziksel robot zarfı değiştirilmedi. Nominal Burger ölçüsü için 11 Kasım'da [ROBOTIS](https://emanual.robotis.com/docs/en/platform/turtlebot3/features/) kaynağı ayrıca okundu.

## Regresyon ve son denetim

Önceki çalışma tarafından hazırlanmış host venv ve mevcut npm bağımlılıkları kullanıldı:

```sh
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
  /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python -m pytest -q -rs \
  tests/test_config.py tests/test_c5_dashboard.py \
  tests/test_warehouse_grid.py tests/test_warehouse_operations.py
C5_UI_PORT=20091 C5_API_PORT=20092 \
  C5_BROWSER_TEST_DIR=/tmp/fleet-c5-stage1-browser-regression \
  npm --prefix frontend test -- --workers=1
git diff --check
```

Sonuçlar **87 geçti**, **23 geçti**, diff kontrolü **0**. Skip yok. Loglar [python.log](e2e-stage1-2026-11-11/python.log) ve [playwright.log](e2e-stage1-2026-11-11/playwright.log). Bu seçkiler canlıda bulunan F1/F2'yi kapatmaz.

Yeni Python/JS araçlarının sözdizimi, yeni Markdown bağlantıları, kullanıcı patch'inin korunması, son kaynak SHA'ları, rapor envanteri ve son Docker durumları [final-audit.json](e2e-stage1-2026-11-11/final-audit.json) içinde kayıtlıdır. Aşama 2/3 komutu çalıştırılmadı.
