# C5 — 30 × 18 m doğrulama komut eki

11 Kasım 2026 · [Rapor ve sınırlar](warehouse-30x18-validation-2026-11-11.md)

Komutlar feature worktree kökünden çalıştırıldı. Geçici çalışma dizini `/tmp/c5-warehouse-30x18.M8jHJk` idi. Yeni tekrar için ayrı bir dizin ve kullanılmayan port/domain değerleri seçilir. Aşağıdaki portlar ve domain ID’leri test ortamı değerleridir. Hazır Fortress image’ı kullanıldı. Compose build tarifinden Nav2 image’ı üretileceği varsayılmadı.

## Host ve derleme

```sh
run_dir=/tmp/c5-warehouse-30x18.M8jHJk
python3 -m venv "$run_dir/venv"
"$run_dir/venv/bin/python" -m pip install -r requirements-c1.txt -r requirements-c5-test.txt
"$run_dir/venv/bin/python" -m fleet_config config/fleet.yaml
"$run_dir/venv/bin/python" -m fleet_config config/fleet.warehouse-grid-12x8.yaml
"$run_dir/venv/bin/python" -m fleet_config config/fleet.warehouse-grid.yaml
"$run_dir/venv/bin/python" -m fleet_config config/fleet.warehouse-30x18.yaml
PYTHONPATH=. "$run_dir/venv/bin/python" -m pytest -q \
  tests/test_config.py tests/test_c5_dashboard.py tests/test_warehouse_grid.py tests/test_warehouse_operations.py
npm --prefix frontend run build -- --outDir "$run_dir/release" --emptyOutDir
C5_UI_PORT=19942 C5_API_PORT=19944 C5_BROWSER_TEST_DIR="$run_dir/playwright-final" \
  npm --prefix frontend test -- --workers=1
PYTHONPATH=. "$run_dir/venv/bin/python" scripts/generate_warehouse_grid.py \
  config/fleet.warehouse-30x18.yaml "$run_dir/generated"
git diff --check
```

Son host sonucu 87 geçti. Playwright sonucu 23 geçti. TypeScript/Vite derlemesi tamamlandı. Host koşusunda Starlette TestClient’in httpx kullanımı için deprecation uyarısı var. Vite, mevcut Zod yorum işaretleri için iki Rollup uyarısı verdi. Bunlar başarısız test veya skip olarak sayılmadı.

Önce kaynağı yalnız okunarak alındı. Mevcut çalışma ağacına checkout veya reset uygulanmadı. Aynı kurulu frontend bağımlılıkları kullanıldı.

```sh
mkdir -p "$run_dir/before-source"
git archive 30373ff frontend | tar -x -C "$run_dir/before-source"
ln -s "$PWD/frontend/node_modules" "$run_dir/before-source/frontend/node_modules"
npm --prefix "$run_dir/before-source/frontend" run build \
  -- --outDir "$run_dir/before-reproduced" --emptyOutDir
```

## Fiziksel koşular

Son üç çift koşusu domain 157, son contact sensörlü karşılıklı geçiş domain 155 ile ayrı container’larda çalıştı. Her test kendi world/map/parametre dosyalarını üretir. Readiness dosyası tamamlanmadan probe başlamaz. Çıkışta Nav2 lifecycle, köprü ve Gazebo kapatılır.

```sh
mkdir -p "$run_dir/complete-live" "$run_dir/verified-live"
docker run --rm --init --name fleet-30x18-complete-routes \
  -e ROS_DOMAIN_ID=157 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e ROS_LOCALHOST_ONLY=0 \
  -e LIBGL_ALWAYS_SOFTWARE=1 -v "$PWD:/workspace:ro" -v "$run_dir/complete-live:/evidence" \
  --entrypoint bash ros2-fleet-c5-validation:humble-fortress \
  /workspace/docker/simulation-warehouse-grid/run.sh routes config/fleet.warehouse-30x18.yaml

docker run --rm --init --name fleet-30x18-verified-passing \
  -e ROS_DOMAIN_ID=155 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e ROS_LOCALHOST_ONLY=0 \
  -e LIBGL_ALWAYS_SOFTWARE=1 -v "$PWD:/workspace:ro" -v "$run_dir/verified-live:/evidence" \
  --entrypoint bash ros2-fleet-c5-validation:humble-fortress \
  /workspace/docker/simulation-warehouse-grid/run.sh passing config/fleet.warehouse-30x18.yaml
```

İki komutun son sonucu 0. Üç çift ve karşılıklı geçiş sonucu `geçti`. Ham çıktılar ve temiz kapanışlar [kanıt klasöründedir](warehouse-30x18/).

## Tarayıcı ve gerçek görev API’si

Son tarayıcı koşusu, rapora eklenen başlangıç Fleet Manager fikstürünü, kaydedilmiş TF/Path izlerini ve gerçek Nav2 costmap kaydını kullandı. Önce/sonra web sunucuları ve host görev sunucusu ayrı süreçlerde açıldı.

```sh
PYTHONPATH=. "$run_dir/venv/bin/python" tests/test_warehouse_operations.py \
  --state "$run_dir/operator-confirmed" --port 19947 --origin http://127.0.0.1:19946

C5_UI_PORT=19945 C5_API_PORT=19947 npm --prefix frontend run preview \
  -- --outDir "$run_dir/before-reproduced"
C5_UI_PORT=19946 C5_API_PORT=19947 npm --prefix frontend run preview \
  -- --outDir "$run_dir/release"

node frontend/tests/warehouse-operations.mjs \
  http://127.0.0.1:19945 http://127.0.0.1:19946 \
  docs/validation/c5/warehouse-30x18/before-fixture.json \
  docs/validation/c5/warehouse-30x18/after-fixture.json \
  docs/validation/c5/warehouse-30x18/nav2-costmap.json \
  "$run_dir/browser-confirmed" docs/validation/c5/warehouse-30x18/live-routes.json \
  http://127.0.0.1:19946
```

Son betik önce kontrollü görsel/arayüz denetimini, ardından mock içermeyen ayrı bir tarayıcı sayfasıyla gerçek görev API’sini sınar. Gerçek API’nin aldığı üç görev ayrı UUID’lerle SQLite’a girer. Test sunucusu durunca `task-evidence.json` yazar ve yerel soketi kaldırır. Son birleşik komut 0 koduyla bitti. Bütün oluşturulan test sunucuları kapatıldı.

Host görev sunucusu ROS robotları üretmez. Tam fiziksel görev yürütmesi için mevcut Executor ve Battery Simulator düğümlerinin de aynı profille çalışması gerekir.

## ROS runtime başlangıç ve kapanış smoke testi

Ürün IDL’si aşağıdaki yollarla container içinde derlendi. Kaynak mount salt okunurdu.

```sh
source /opt/ros/humble/setup.bash
cd /workspace
colcon --log-base /evidence/log build --base-paths interfaces/fleet_interfaces \
  --build-base /evidence/build --install-base /evidence/install
source /evidence/install/setup.bash
export PYTHONPATH=/workspace:${PYTHONPATH:-}
python3 -m backend.dashboard.runtime --fleet config/fleet.warehouse-30x18.yaml \
  --database /evidence/verified/runtime.sqlite3 --snapshot /tmp/fleet-runtime/latest.json
```

İlk denemede socket için host bind mount kullanılması `chmod` hatası verdi. Son smoke testinde snapshot ve görev soketi container yerel `/tmp/fleet-runtime` yolundaydı. Kalıcı SQLite `/evidence/verified` altında kaldı. Snapshot oluşması gözlendi, SIGINT gönderildi, process 0 koduyla çıktı ve `latest.tasks.sock` kaldırıldı. Bu smoke testinde RobotStatus/Executor görev tamamlaması sınanmadı.

Ayrı FastAPI sürecindeki `--fleet` aynı profili seçer. `--task-socket`, snapshot’ın `.tasks.sock` uzantılı yolunu etkinleştirir. `--costmap`, aynı profil özetine ait kayıt dosyasını seçer. API’nin port ve Origin değerleri açık argümanlarla verilir. Bu alanlar [tasarım kaydında](../../design/c5-3d-operations.md#11-kasım-2026-dağıtılmış-depo-ve-katalogdan-görev-girişi) açıklanır.
