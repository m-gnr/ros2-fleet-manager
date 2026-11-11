# C5 Aşama 1.2 — Komut ve kanıt eki

11 Kasım 2026 · [Rapor](c5-stage1-2-physical-localization-2026-11-11.md)

Bütün komutlar `/Users/murat/develop/ros2-fleet-manager-c5-warehouse-grid` kökünden çalıştı. Ana worktree yalnız okundu. HEAD tek başına kaynak durumu değildir: 30×18 m/API/frontend kullanıcı değişiklikleri başlangıçta kirliydi; baseline hash ve source manifest birlikte okunmalıdır. Önceki kişisel notlar ve PDF’ler değiştirilmedi. Aşağıdaki domain/port/volume adları test ortamı değerleridir.

## Kaynak kontrolü

```sh
git status --short
git branch -avv
git worktree list
git log -5 --oneline
git diff --stat
```

[baseline.json](stage1-2-2026-11-11/baseline.json), [hash’ler](stage1-2-2026-11-11/baseline-hashes.json), [son kaynak manifesti](stage1-2-2026-11-11/source-manifest.json), [ortam ve gerçek Docker komutları](stage1-2-2026-11-11/environment.json). Image yeniden build edilmedi; mevcut `ros2-fleet-c5-validation:humble-fortress` kullanıldı. Ürün IDL/Python paketleri Humble regresyon container’ında colcon ile geçici dosya sistemine derlendi.

## Fiziksel deneyler

İlk çalışma aşağıdaki Docker zarfını kullandı:

```sh
docker run -d --init --name fleet-c5-stage12-motion \
 -e ROS_DOMAIN_ID=180 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
 -e ROS_LOCALHOST_ONLY=0 -e LIBGL_ALWAYS_SOFTWARE=1 -e PYTHONDONTWRITEBYTECODE=1 \
 -v "$PWD:/workspace:ro" \
 -v "$PWD/docs/validation/c5/stage1-2-2026-11-11:/evidence" \
 -w /workspace --entrypoint bash ros2-fleet-c5-validation:humble-fortress -ec '
source /opt/ros/humble/setup.bash
export PYTHONPATH=/workspace:${PYTHONPATH:-}
python3 docker/simulation-warehouse-grid/stage12_run.py \
 config/fleet.warehouse-30x18.yaml /evidence/baseline-motion --motions
'
```

İlk run ileri/geri/90° ölçtü; 180° gözlemcisinin TF hazır olma assertion’ı ile **1** çıktı. Sonraki `motion-rest` container’ı domain 181’de `--only turn90 turn180 turn_forward corridor pickup-1 pickup-2 pickup-3` çalıştırdı, **0** çıktı. Her dünya sonlanıp kapanmadan sonraki açılmaz. Kaydedilmiş fiziksel JSON sonuçları süreç kodundan ayrı değerlendirilir.

İzolasyon container’ı domain 182’de ek olarak önceki Aşama 1 IDL install dizinini `/types:ro` bağladı, `source /types/setup.bash` yaptı. Komutlar sıralıydı:

```sh
python3 docker/simulation-warehouse-grid/stage12_run.py \
 config/fleet.warehouse-30x18.yaml /evidence/timestep \
 --variant timestep --only turn90 --lifecycle 30
python3 docker/simulation-warehouse-grid/stage12_run.py \
 config/fleet.warehouse-30x18.yaml /evidence/effective-track \
 --variant effective_track \
 --only forward turn90 turn180 turn_forward pickup-1 pickup-2 pickup-3 --routes
```

İzolasyon **0**; bu yalnız ölçümlerin tamamlandığını gösterir. `timestep` tek parametreyi 1 ms yaptı; kaynakta kalıcılaştırılmadı. `effective_track` yalnız plugin etkin track’ini 0,36 m yaptı; bu sırada Nav2 yarıçapı 0,25 m idi. Son kaynak artık track düzeltmesini içerir; eski nominal track değerini seçmek için `--variant nominal_track` 0,40 m’yi açıkça seçebilir; ilk baseline’ın 0,25 m Nav2 yarıçapı da saklı parametrelerden ayrıca korunmalıdır. Eski dünya/parametre dosyaları ve hash’ler asıl koşunun kaynağıdır. Aynı output dizini yeniden kullanılmaz.

Track düzeltmesi uygulandıktan sonra domain 183’te ayrı footprint varyantı:

```sh
python3 docker/simulation-warehouse-grid/stage12_run.py \
 config/fleet.warehouse-30x18.yaml /evidence/footprint \
 --variant footprint \
 --only reverse corridor pickup-1 pickup-2 pickup-3 pickup-4 pickup-5 \
 --routes --access --lifecycle 30
```

Süreç **0**, ancak fiziksel kabul **1/5**. Son pickup sonrasında aynı izole Nav2 dünyasında yalnız seçili dropoff→park→dock erişimi yapıldı; tam şarj veya istasyon taraması yapılmadı. İki costmap r=0,30 m varyantı sonradan kaynak şablonuna aynı değerlerle uygulandı; üretilen etkin parametreler aynı kaldı. AMCL ve hedef toleransları değişmedi.

Performans sampler’ı ilgili primary koşulardan önce `python3 docker/simulation-warehouse-grid/stage12_performance.py /evidence/performance-*.jsonl` ile başlatıldı; sonra SIGTERM ile kapandı. Başlangıç rest sampler’ı ilk dönüşler tamamlandıktan sonra, üç pickup’tan önce açıldı. Karşılaştırma yalnız damgalı primary pickup penceresini filtreler.

Sonradan yeniden hesaplamalar:

```sh
python3 docker/simulation-warehouse-grid/stage12_analyze.py \
 docs/validation/c5/stage1-2-2026-11-11/baseline-motion-rest
PYTHONPATH=. /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python \
 docker/simulation-warehouse-grid/stage12_scan_analysis.py \
 docs/validation/c5/stage1-2-2026-11-11/baseline-motion-rest \
 config/fleet.warehouse-30x18.yaml
python3 docker/simulation-warehouse-grid/stage12_performance_summary.py \
 docs/validation/c5/stage1-2-2026-11-11
```

İlk iki analiz effective-track ve footprint için de çalıştırıldı; her biri **0**. Özetleyici ilk başarısız 180° kaydını doğrulanamadı olarak korur. Ray analizi yalnız aynı fiziksel stamp’te quaternion olan scan’leri kullanır.

## Python ve Humble

```sh
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
 /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python -m pytest -q -rs \
 tests/ ros2_ws/src/fleet_robot_executor/test
```

Önce 442 geçti / 28 skip, sonra 449 geçti / 29 skip; **0**. Yeni ölçüm seçkisi 7 geçti; eski footprint’i kontrol eden ilk deneme **1**, 1 kaldı / 4 geçti. [Loglar](stage1-2-2026-11-11/)

```sh
docker run -d --init --name fleet-c5-stage12-ros \
 -e ROS_DOMAIN_ID=184 -e ROS_LOCALHOST_ONLY=1 \
 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e PYTHONDONTWRITEBYTECODE=1 \
 -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" \
 -v "$PWD/docs/validation/c5/stage1-2-2026-11-11:/evidence" \
 -w /tmp/ros-tests --entrypoint bash ros2-fleet-c5-validation:humble-fortress -ec '
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src > /evidence/ros-build.log 2>&1
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:/repo/ros2_ws/src/fleet_robot_executor:/repo/ros2_ws/src/fleet_battery_simulator:${PYTHONPATH:-}
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
 tests/ ros2_ws/src/fleet_robot_executor/test > /evidence/ros-tests.log 2>&1
'
```

İlk koşu **1**, 497 geçti / 2 test gözlemcisi kaldı. Readiness çıktısı düzeltildikten sonra log korundu ve container `docker start fleet-c5-stage12-ros` ile yeniden çalıştırıldı: **1**, 498 geçti / 1 DDS graph zamanlaması testi kaldı. Alıcı graph’ının bounded readiness beklemesi eklendi; ikinci log da korundu. Aynı container üçüncü kez çalıştı: **0, 499 geçti**. Eski loglar `ros-tests-initial.log`, `ros-tests-discovery-failure.log`; son log `ros-tests.log`.

Lifecycle denemeleri gerçek Gazebo akışı altında önce ve sonra `stage12_lifecycle.py <profile> <new-output> --count 30` ile yapıldı. Süreç ölçümü tamamlar; çocuk sonuçları `results.json`, ebeveyn context `parent.json`, traceback/context/thread ayrıntıları `child-*.log` içinde ayrı değerlendirilir. `--require-clean` gelecekteki kabul kullanımında temiz çıkışı zorunlu kılar. Bu kayıt başarıya göre filtrelenmiş tekrarlar içermez.

## Gerçek Chrome / tek ve paralel görev

```sh
C5_UI_PORT=20211 C5_API_PORT=20212 npm --prefix frontend run dev
```

Domain 185 A, domain 186 B için ayrı container ve ayrı `scenario-a` / `scenario-b` DB kullanıldı. [Tam Docker argv/mount/env kaydı](stage1-2-2026-11-11/environment.json). Esas runtime komutu:

```sh
python3 docker/simulation-warehouse-grid/stage11_run.py \
 config/fleet.warehouse-30x18.yaml /evidence/scenario-a \
 --api-port 20212 --scene-port 20213 --origin http://127.0.0.1:20211
node frontend/tests/stage11-e2e.mjs http://127.0.0.1:20211 \
 docs/validation/c5/stage1-2-2026-11-11/chrome-a a
```

Container image Humble/Fortress; profile source mount readonly, IDL `/types:ro`, kalıcı volume `fleet-c5-stage12-20261111:/var/lib/fleet`; loopback 20212 portu yayımlandı. `STAGE11_TRANSITIONS` her senaryonun `committed-events.jsonl` dosyasına işaret eder. Aynı portta A kapanmadan B açılmadı.

A browser **0**, tek görev ve karşılaştırma **0**. B browser için aynı komutun dizini chrome-b ve son argümanı b oldu: **1**, beta FAILED. Alpha terminale kadar bırakıldı; ek salt okunur gözlem:

```sh
node frontend/tests/stage12-observe-terminal.mjs http://127.0.0.1:20211 \
 docs/validation/c5/stage1-2-2026-11-11/chrome-b-terminal
```

**0**: gerçek tablo alpha Tamamlandı / beta Başarısız. Yeni görev veya retry göndermez. Screenshot yerel görsel incelemeden geçirildi.

Her senaryo sonrasında `docker stop --timeout 50 <container>` ile kontrollü kapanış. A ilk stop’ta eşdeğer eski `--time` yazımı kullanıldı; CLI deprecation uyarısı vardı. Bütün A/B child exit’leri **0**, iki container **0**, OOMKilled=false.

```sh
python3 docker/simulation-warehouse-grid/stage1_summarize.py \
 docs/validation/c5/stage1-2-2026-11-11/scenario-a \
 docs/validation/c5/stage1-2-2026-11-11/chrome-a
```

A **0**; B/chrome-b aynı analiz **1**. [Son analiz çıkış kodları](stage1-2-2026-11-11/comparison-exits.json). Başarı odaklı önceki özetleyici başarısız action sonucunun doğru epoch’unu ayrı bir kabul saymaz; beta için `failed-task-safety.json` gerçek UUID/epoch/ERROR/tek gönderim kanıtını ayrıca kaydeder. SQL incelemesindeki ilk `assigned_robot_id` sorgusu bu şemada olmayan sütunu kullandı; ürün hatası sayılmadı, salt okunur export alanlarıyla doğrulandı.

Mock browser regresyonu:

```sh
C5_UI_PORT=20201 C5_API_PORT=20202 C5_BROWSER_TEST_DIR=/tmp/fleet-c5-stage12-browser \
 npm --prefix frontend test -- --workers=1
```

**0, 23 geçti**; proxy uyarıları logda saklanır.

## HIGH ve C3.3.3 canlı güvenlik

```sh
DDS_TEST_PAYLOAD=fleet-c5-stage12-high ROS_DOMAIN_ID=187 docker compose \
 -p fleet-c5-stage12-high -f docker/compose/docker-compose.dds.yml \
 -f docker/compose/docker-compose.simulation-check.yml \
 -f docker/compose/docker-compose.simulation-c3-3-3.yml config --format json
COMPOSE_PROJECT_NAME=fleet-c5-stage12-high python3 scripts/run_c3_3_3.py \
 --domain 187 --token fleet-c5-stage12-high --high-preemption
```

**0**, T01 + T04-HIGH-E2E geçti; backend/simulation 0/0 ve temiz lifecycle. Çözülmüş mount yolları `high-compose.json`, DB `high.sqlite3`; image ID’leri ortam kaydında. Build/up --build yapılmadı; eski A build tarifinin Nav2 image ürettiği varsayılmadı.

```sh
COMPOSE_PROJECT_NAME=fleet-c5-stage12-c333 python3 scripts/run_c3_3_3.py \
 --domain 188 --token fleet-c5-stage12-c333
```

İlk başlatma **1**, Docker address pool bitti; hiç ROS dünyası açılmadı. HIGH’ın bitmiş, bu göreve ait projesinden DB/inspect/log alındıktan sonra yalnız o projeye `docker compose ... down` uygulandı; başka ağ silinmedi. Aynı C3.3.3 komutu tekrarlandı: **0, T01–T10 10/10**, backend/simulation 0/0, temiz kapanış. STALE T07 ve SESSION_BLOCKED T08 canlı geçti. İlk ortam hatası `c333-network-failure.log`, son koşu `c333-regression.log`, [son durum](stage1-2-2026-11-11/live-regressions-final.json). Bu eski C3 profilindeki regresyon 30×18 m tam şarj kabulü değildir.

## Son denetim ve saklama

Yeni Python araçları ast.parse, yeni readonly Chrome aracı node --check ve git diff --check ile kontrol edildi. Kullanıcı dosyalarının baseline hash’leriyle karşılaştırılması ve kısmi doc-map staging denetimi son audit’te tutulur. Ham JSONL/üretilmiş world/param/harita/ROS logları yerelde korunur; seçilenler `raw-evidence.tar.gz` arşivine alınır. Ham kanıt arşivi ile videolar ayrı manifestte SHA-256 ile kayıtlıdır. Video ve bağımsız ham .log dosyaları Git’e alınmaz; .log dosyalarının değişmez kopyası ham arşivdedir. Arşiv yeni boş bir dizine açılarak incelenebilir. Commit’ler kullanıcıya ait önceki dirty kaynakları kapsamaz; bu SHA’lardan tek başına temiz checkout test edilen tüm kaynağı yeniden kurmaz.

**Aşama 1.2 kabul edilmedi; Aşama 2/3 ve 27 ziyaret taraması başlatılmadı. Push/merge yapılmadı.**
