# C5 / Aşama 1.1 — Komut ve kanıt eki

11 Kasım 2026 · [Değerlendirme](stage1-1-validation-2026-11-11.md)

Komutlar `/Users/murat/develop/ros2-fleet-manager-c5-warehouse-grid` kökünde çalıştırıldı. Ana worktree yalnız okunarak kontrol edildi. Yeni koşu için ayrı DB/dizin/container adı ve kullanılmayan port/domain gerekir. Eski DB replay edilmez. Aşağıdaki değerler bu test ortamının değerleridir.

## Başlangıç ve F1

```sh
git status --short
git branch -avv
git worktree list
git log -5 --oneline
git remote -v
```

Python `subprocess/pathlib/hashlib` ile başlangıç Git çıktıları, bütün mevcut kaynakların SHA-256 değerleri ve çalışma ağacı patch'i kaydedildi. Önceki rapor, ilgili `scenario-a4`/`scenario-b` JSONL/SQLite/Chrome ve fiziksel ölçüm dosyaları yerinde okundu; tarihsel rapora yazılmadı.

```sh
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
 /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python -m pytest -q -rs \
 tests/test_feedback_pipeline.py tests/test_fleet_manager_domain.py \
 tests/test_fleet_manager_outbox.py tests/test_ros2_action_client.py
```

Sonuç **150 geçti**, çıkış 0. Aynı host venv ile tam seçki:

```sh
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
 /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python -m pytest -q -rs \
 tests/ ros2_ws/src/fleet_robot_executor/test
```

**439 geçti, 28 atlandı**, çıkış 0. Skip listesi [host-tests.log](stage1-1-2026-11-11/host-tests.log) içinde; başarı sayılmadı.

```sh
PYTHONPATH=. /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python \
 docker/simulation-warehouse-grid/stage1_feedback_probe.py
```

Yeni probe **0**, gerçek callback→consumer→domain→SQLite `EXECUTING`. [JSON](stage1-1-2026-11-11/feedback-contract.json)

Yalnız ilgili dosyalar `git add` ile seçilip `fix(fleet): repair feedback contract and executing transition` commit'i oluşturuldu. Eski kullanıcı dashboard/config/frontend değişiklikleri eklenmedi. Commit **7b2bc82**.

## Humble regresyonu

```sh
docker run --init --name fleet-c5-stage11-ros \
 -e ROS_DOMAIN_ID=171 -e ROS_LOCALHOST_ONLY=1 \
 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e PYTHONDONTWRITEBYTECODE=1 \
 -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" \
 -v "$PWD/docs/validation/c5/stage1-1-2026-11-11:/evidence" \
 -w /tmp/ros-tests --entrypoint bash ros2-fleet-c5-validation:humble-fortress -ec '
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:/repo/ros2_ws/src/fleet_robot_executor:/repo/ros2_ws/src/fleet_battery_simulator:${PYTHONPATH:-}
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
 tests/ ros2_ws/src/fleet_robot_executor/test
'
```

**487 geçti**, çıkış 0; [ros-tests.log](stage1-1-2026-11-11/ros-tests.log). Hazır image kullanıldı, image build yapılmadı. IDL ve Python ROS paketleri container'ın geçici dosya sisteminde derlendi. Daha sonra ayrıca eklenen frame hesabı testleri bu sayıya dahil değildir:

```sh
PYTHONPATH=. /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python -m pytest -q \
 tests/test_stage11_localization_metrics.py
```

**3 geçti**, çıkış 0. [metrics-tests.log](stage1-1-2026-11-11/metrics-tests.log)

## Üç fiziksel lokalizasyon deneyi

```sh
docker run --init --name fleet-c5-stage11-localization \
 -e ROS_DOMAIN_ID=170 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
 -e ROS_LOCALHOST_ONLY=0 -e LIBGL_ALWAYS_SOFTWARE=1 -e PYTHONDONTWRITEBYTECODE=1 \
 -v "$PWD:/workspace:ro" \
 -v "$PWD/docs/validation/c5/stage1-1-2026-11-11:/evidence" \
 -w /workspace --entrypoint bash ros2-fleet-c5-validation:humble-fortress -ec '
source /opt/ros/humble/setup.bash
export PYTHONPATH=/workspace:${PYTHONPATH:-}
python3 docker/simulation-warehouse-grid/stage11_localization.py \
 config/fleet.warehouse-30x18.yaml /evidence/localization
'
```

Süreç **0**: üç ölçüm ve üç temiz dünya kapanışı tamamlandı. Bu çıkış fiziksel doğruluk kabulü değildir; deneme JSON sonuçları **1 geçti / 2 kaldı**. Üretici-v1'in yanlış frame'deki odom deltası ayrı analizle düzeltildi; ham kayıt silinmedi. [Analiz](stage1-1-2026-11-11/localization-analysis.json)

```sh
python3 docker/simulation-warehouse-grid/stage11_analyze.py \
 docs/validation/c5/stage1-1-2026-11-11
PYTHONPATH=. /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python \
 docker/simulation-warehouse-grid/stage1_clearance.py config/fleet.warehouse-30x18.yaml \
 docs/validation/c5/stage1-1-2026-11-11/scenario-a/generated \
 docs/validation/c5/stage1-1-2026-11-11
```

İki araç da **0**; ilki analiz çıktısı üretir, ikincisi statik ön kontroldür. Footprint başarısı veya trafik kabulü anlamına gelmez. `localization-analysis.json`, `physical-measurements.yaml` ve `clearance-precheck.json` okunmalıdır.

## Canlı C5 tek/paralel görevler

Frontend mevcut kaynaklardan çalıştırıldı. Kalıcı test volume'ü Docker tarafından ilk kullanımda oluşturuldu. Her senaryonun DB dosyası ayrıydı.

```sh
C5_UI_PORT=20111 C5_API_PORT=20112 npm --prefix frontend run dev
docker run --init --name fleet-c5-stage11-a --add-host scene:127.0.0.1 \
 -p 127.0.0.1:20112:20112 -e ROS_DOMAIN_ID=172 \
 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e ROS_LOCALHOST_ONLY=0 \
 -e LIBGL_ALWAYS_SOFTWARE=1 -e PYTHONDONTWRITEBYTECODE=1 \
 -e STAGE11_TRANSITIONS=/evidence/scenario-a/committed-events.jsonl \
 -v "$PWD:/workspace:ro" \
 -v "$PWD/docs/validation/c5/stage1-1-2026-11-11:/evidence" \
 -v "$PWD/docs/validation/c5/e2e-stage1-2026-11-11/install:/types:ro" \
 -v fleet-c5-stage11-20261111:/var/lib/fleet -w /workspace \
 --entrypoint bash ros2-fleet-c5-validation:humble-fortress -ec '
source /opt/ros/humble/setup.bash
source /types/setup.bash
export PYTHONPATH=/workspace:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:${PYTHONPATH:-}
python3 docker/simulation-warehouse-grid/stage11_run.py \
 config/fleet.warehouse-30x18.yaml /evidence/scenario-a \
 --api-port 20112 --scene-port 20113 --origin http://127.0.0.1:20111
'
```

Ayrı terminal:

```sh
node frontend/tests/stage11-e2e.mjs http://127.0.0.1:20111 \
 docs/validation/c5/stage1-1-2026-11-11/chrome-a a
docker stop --time 50 fleet-c5-stage11-a
```

İlk A browser script'i **0**, görev karşılaştırması **0**. Buna rağmen child alpha Battery Simulator kapanışı **1**; kabul kaydında ayrı başarısızlık.

B aynı Docker komutunda şu değerlerle çalıştı: ad `fleet-c5-stage11-b`, domain 173, transition/output `scenario-b`. Browser output `chrome-b`, son argüman `b`:

```sh
node frontend/tests/stage11-e2e.mjs http://127.0.0.1:20111 \
 docs/validation/c5/stage1-1-2026-11-11/chrome-b b
docker stop --time 50 fleet-c5-stage11-b
```

B browser **0**, gerçek görev terminalleri/feedback başarılı; fiziksel beta pickup kontrolünü içeren karşılaştırma **1**.

Görsel QA sonrası browser script'i görev tablosunun render'ını ve gerçek `Yürütülüyor`/`Tamamlandı` hücrelerini bekleyecek şekilde düzeltildi. Supervisor child kapanış hatasını üst sürece de yayacak şekilde sınırlandı. Bu iki değişiklik ayrı **f5cff89** test commit'idir; geçmişi yeniden yazmak için amend/rebase kullanılmadı. Araçların ilk checkpoint'i **0b9dee8** idi.

Ek A2/B2 aynı Docker komutu ve aynı ürün kaynaklarıyla, sırasıyla ad/domain/output olarak `fleet-c5-stage11-a2 / 175 / scenario-a2`, `fleet-c5-stage11-b2 / 176 / scenario-b2` kullandı. `STAGE11_TRANSITIONS` her birinin kendi çıktı dizinine işaret etti. Browser:

```sh
node frontend/tests/stage11-e2e.mjs http://127.0.0.1:20111 \
 docs/validation/c5/stage1-1-2026-11-11/chrome-a2 a
node frontend/tests/stage11-e2e.mjs http://127.0.0.1:20111 \
 docs/validation/c5/stage1-1-2026-11-11/chrome-b2 b
```

Her browser işlemi ilgili container hazırken ve diğer senaryo kapandıktan sonra çalıştı. Eşzamanlı iki FM veya aynı DB'nin tekrarı yoktu. Sonuçların tamamı [ek tekrar özetinde](stage1-1-2026-11-11/visual-repeat-summary.json). Görsel test tekrarları, ilk fiziksel başarısızlıkları geçersiz kılmaz.

Karşılaştırma komutları her `scenario-a`, `scenario-b`, `scenario-a2`, `scenario-b2` için karşılık gelen `chrome-*` diziniyle çalıştı:

```sh
python3 docker/simulation-warehouse-grid/stage1_summarize.py \
 docs/validation/c5/stage1-1-2026-11-11/scenario-a \
 docs/validation/c5/stage1-1-2026-11-11/chrome-a
```

`comparison.json` başarılı kontrolü ayrı, fiziksel başarısızlığı ayrı içerir; başarısız kontrolde araç 1 döndürür. `committed-events.jsonl` gerçek consumer'ın COMMIT sonrası durumlarını okuyan gözlemcidir; scheduling veya domain state değiştirmez.

Canlı A sırasında şu parametreler ROS CLI ile okundu: local/global `robot_radius`, `footprint_padding`, local `footprint`; ayrıca `ros2 node list --no-daemon`. [Çıktı](stage1-1-2026-11-11/live-parameters.txt)

## Browser regresyonu ve HIGH

```sh
C5_UI_PORT=20101 C5_API_PORT=20102 C5_BROWSER_TEST_DIR=/tmp/fleet-c5-stage11-browser \
 npm --prefix frontend test -- --workers=1
```

**23 geçti**, çıkış 0. Mock regresyondaki task-catalog proxy bağlantı mesajları logda tutuldu; bu, gerçek canlı API yerine mock kullanıldığı iddiasını canlı koşuya taşımaz.

```sh
DDS_TEST_PAYLOAD=fleet-c5-stage11-high ROS_DOMAIN_ID=174 docker compose \
 -p fleet-c5-stage11-high -f docker/compose/docker-compose.dds.yml \
 -f docker/compose/docker-compose.simulation-check.yml \
 -f docker/compose/docker-compose.simulation-c3-3-3.yml config --format json
docker image inspect ros2-fleet-simulation-nav2-check:humble-fortress \
 ros2-fleet-simulation-c3-3-3-backend:humble-fortress
COMPOSE_PROJECT_NAME=fleet-c5-stage11-high python3 scripts/run_c3_3_3.py \
 --domain 174 --token fleet-c5-stage11-high --high-preemption
docker cp fleet-c5-stage11-high-backend-1:/tmp/c3_3_3_t04-high-e2e.db \
 docs/validation/c5/stage1-1-2026-11-11/high.sqlite3
```

HIGH runner **0**, backend/simulation **0/0**, `SCENARIO_PASSED T04-HIGH-E2E`, `SIMULATION_SHUTDOWN clean=true`. Image build tarifinin Nav2 image'ı ürettiği varsayılmadı; mevcut image'lar ve çözülmüş mount yolları kaydedildi. Bir `compose ps` denemesi zorunlu `DDS_TEST_PAYLOAD` verilmediği için config aşamasında hata verdi; env eklenerek okuma tekrarlandı. Bu deneme canlı kabul koşusu veya ürün hatası sayılmadı.

## Kanıtların saklanması ve son kontrol

Yeni raw JSONL, ROS/Fortress logları, SQLite kopyaları, üretilmiş SDF/harita/Nav2 ayarları, Chrome screenshot ve commit sonrası journal kayıtları [ham arşivde](stage1-1-2026-11-11/raw-evidence.tar.gz) saklanır. Dört Chrome videosu kendi `chrome-*/video/` dizinlerinde yerelde korunur; yaklaşık 44 MB video Git'e eklenmedi. [Medya manifesti](stage1-1-2026-11-11/media-manifest.json) yolları ve SHA'ları kaydeder. Açık JSON özetleri ve seçilmiş görseller ayrıca tutulur. Kaynak hash manifesti ayrı; önceki kullanıcı patch'i bu arşive katılmadı. Denemelerin ham LaserScan ışınları kalıcı kayda aktarılmadı; stamp'li scan/map residual ölçümleri, AMCL/TF/odom/fiziksel poz ham kayıtları vardır. Scan residual hesabının bütün ışınlarla sonradan yeniden yapılması bu artifact'tan doğrulanamaz.

```sh
node --check frontend/tests/stage11-e2e.mjs
git diff --check
git diff --cached --check
git log -5 --oneline
docker ps --format '{{.Names}}\t{{.Status}}'
```

Python araçları `ast.parse` ile kontrol edildi. Yeni yerel Markdown linkleri, baseline dosyalarının korunması ve stage dışı değişikliklerin commit'e alınmaması [final-audit.json](stage1-1-2026-11-11/final-audit.json) içinde kayıtlıdır. Başlatılan frontend süreçleri kapatıldı; container ve volume kanıtları silinmedi. Commit'ler mantıksal F1/araç/rapor gruplarına ayrıldı; görsel QA için ek araç commit'i vardır. **Push, merge veya sonraki aşama komutu çalıştırılmadı.**
