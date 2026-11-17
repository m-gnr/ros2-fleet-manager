# C5 Gamma entegrasyonu — komut ve kanıt eki — 17 Kasım 2026

Worktree: `/private/tmp/ros2-fleet-manager-c5-alpha-beta-stable` · Branch: `demo/alpha-beta-stable` · Başlangıç Git durumu: temiz.
Doğrulama raporu: [üçüncü robot Gamma entegrasyonu](third-robot-gamma-2026-11-17.md).

## Statik kontroller

```sh
python3 -m fleet_config config/fleet.warehouse-30x18.yaml
```

Sonuç: `VALID: 3 robots; schema, semantic and file reference checks passed`.

Gamma, occupancy geometrisi ile C1 yaklaşım zarfı üzerinden ayrıca kontrol edildi. En yakın katı nesne `rack_B2`, robot merkezinden 1,25 m uzakta; konfigüre edilen muhafazakâr zarf 0,45 m. Alpha ve Beta başlangıç konumları değişmedi. Üretilen işgal haritası 0,05 m çözünürlükte.

```sh
python3 docker/simulation-warehouse-grid/test_startup_readiness.py
```

Sonuç: **3 test geçti**. Test artık Alpha, Beta ve Gamma için tüm `amcl`, `nav2`, `tf` fazları tamamlanmadan `READY` üretmediğini de kontrol ediyor.

```sh
python3 -m py_compile docker/simulation-warehouse-grid/stage1_run.py \
  docker/simulation-warehouse-grid/stage1_observer.py \
  docker/simulation-warehouse-grid/startup_readiness.py
git diff --check
```

Sonuç: derleme ve whitespace kontrolleri geçti.

```sh
npm --prefix frontend run build
```

Sonuç: TypeScript kontrolü ve Vite üretim derlemesi geçti. Zod vendor bağımlılığında Rollup annotation uyarıları görüldü; derlemeyi bozmadı.

## Gerçek headless cold-start

Kullanılan image: `ros2-fleet-c5-validation:humble-fortress`; domain `197`; IGN partition `c5-alpha-beta-gamma-live-retry1-20261117`; API host portu `21484`; GUI `21486`. Kaynak `/workspace` içine salt okunur bağlandı; kanıt `/tmp/c5-alpha-beta-gamma-live-20261117` altına yazıldı. Yeni container `--workdir /workspace` ile çalıştırıldı:

```sh
docker run --detach \
  --name c5-alpha-beta-gamma-live-retry1-20261117 \
  --network bridge \
  --workdir /workspace \
  --env ROS_DOMAIN_ID=197 \
  --env IGN_PARTITION=c5-alpha-beta-gamma-live-retry1-20261117 \
  --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  --publish 127.0.0.1:21484:21484 \
  --volume /tmp/c5-alpha-beta-gamma-live-20261117:/evidence \
  --volume /private/tmp/ros2-fleet-manager-c5-alpha-beta-stable:/workspace:ro \
  ros2-fleet-c5-validation:humble-fortress \
  bash -ec 'source /opt/ros/humble/setup.bash; \
    colcon --log-base /evidence/idl-log-retry1 build \
      --base-paths interfaces/fleet_interfaces \
      --build-base /evidence/idl-build-retry1 \
      --install-base /evidence/idl-install-retry1; \
    source /evidence/idl-install-retry1/setup.bash; \
    export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:${PYTHONPATH:-}; \
    exec python3 docker/simulation-warehouse-grid/stage1_run.py \
      config/fleet.warehouse-30x18.yaml /evidence/live \
      --api-port 21484 --scene-port 21487 \
      --origin http://127.0.0.1:21486'
```

İlk container çağrısında `--workdir /workspace` eksikti ve launcher `/docker/...` yolunu bulamadı; bu süreç ROS/Gazebo başlatmadan çıktı. Düzeltilmiş, ayrı isimli container başarılı cold-start kanıtını üretti. Kullanıcıya ait iki önceki demo container'ı değiştirilmedi.

`/tmp/c5-alpha-beta-gamma-live-20261117/live/startup-readiness.json` ilk tam hazır anında `status=READY`, `current_status=READY` verdi; bu an observer başlangıcından **12,983 ms** sonraydı. Alpha/Beta/Gamma'nın her biri için AMCL, gerçek map-frame TF ve Nav2 lifecycle/action hazır olma zamanları rapordaki tabloda verilmiştir. Observer başlangıç reset kaydı, üç robot için beklenen poz, yön ve sıfıra yakın hızla `reset-verified.json` oluşturdu. `unsafe-contact` oluşmadı.

Container canlı bırakıldıktan sonraki son incelemede aynı dosyanın `status=READY`, `current_status=WAITING` olduğu görüldü. O sıradaki API sağlık ve robot sorguları ya da daha önceki Chrome `3/3 TF LIVE` kanıtı bunu açıklamıyor; bu nedenle sürekli readiness bu koşunun kabul kapsamı dışında bırakıldı ve takip sorunu olarak kaydedildi.

SDF, `robot_alpha`, `robot_beta`, `robot_gamma` modellerini içerdi. Her robotun üretilmiş Nav2 parametre dosyası kendi `base_link`, `odom`, `scan` namespace'ini kullandı. Gazebo bridge listesi üç robotun `scan`, `odom`, `cmd_vel`, contact ve physical-pose başlıklarını içerdi. AMCL poz, lifecycle ve action server şartları observer tarafından aynı gerçek ROS domain'de ölçüldü.

## Fleet API ve Chrome

```sh
curl -fsS http://127.0.0.1:21484/api/health
curl -fsS http://127.0.0.1:21484/api/robots
curl -fsS http://127.0.0.1:21484/api/tasks
```

Son gözlemde health `source=LIVE`; üç robotun durumu `IDLE`, telemetry/pose/battery `LIVE`, `active_task_id=null`; görev sayıları sıfırdı. GUI, 21484 API proxy'si ile şu komutla açıldı:

```sh
cd /private/tmp/ros2-fleet-manager-c5-alpha-beta-stable/frontend
C5_API_PORT=21484 C5_UI_PORT=21486 ./node_modules/.bin/vite --host 127.0.0.1
```

Chrome `http://127.0.0.1:21486/` adresinde 3D depo render'ını, üç robot etiketini/kartını ve `3/3 TF LIVE` göstergesini verdi. İlk bağlantı beklemesinde aynı gösterge `WAITING FOR TF` idi; sayfa yenileme gerekmedi.

Bu koşuda `/api/tasks` için POST veya Nav2 action goal gönderilmedi. Container ve Vite oturumu doğrulama sonunda canlı bırakıldı.

## Gerçek Gamma görevi takip koşusu — 17 Kasım

Önceki iki görev/demo container'ı ve ilk Gamma cold-start container'ı çalışır bırakıldı. Ayrı domain, IGN partition, host portu ve boş SQLite ile tek yeni oturum açıldı. Worktree kaynakları salt okunur mount edildi; build ve kanıtlar `/tmp/c5-three-robot-e2e-20261117/` içindedir.

```sh
docker run --detach \
  --name c5-three-robot-e2e-20261117 \
  --network bridge \
  --workdir /workspace \
  --env ROS_DOMAIN_ID=198 \
  --env IGN_PARTITION=c5-three-robot-e2e-20261117 \
  --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  --publish 127.0.0.1:21494:21494 \
  --volume /tmp/c5-three-robot-e2e-20261117:/evidence \
  --volume /private/tmp/ros2-fleet-manager-c5-alpha-beta-stable:/workspace:ro \
  ros2-fleet-c5-validation:humble-fortress \
  bash -ec 'source /opt/ros/humble/setup.bash; \
    colcon --log-base /evidence/idl-log build \
      --base-paths interfaces/fleet_interfaces \
      --build-base /evidence/idl-build \
      --install-base /evidence/idl-install; \
    source /evidence/idl-install/setup.bash; \
    export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:${PYTHONPATH:-}; \
    exec python3 docker/simulation-warehouse-grid/stage1_run.py \
      config/fleet.warehouse-30x18.yaml /evidence/live \
      --api-port 21494 --scene-port 21497 \
      --origin http://127.0.0.1:21496'
```

Başlangıç observer'ı `2026-11-17T00:33:14Z`'de başladı. Tüm robotlar için ilk AMCL, gerçek TF ve Nav2 hazır gözlemleri 19.989–26.492 saniyede geldi. Fleet API üç robotu `IDLE`/`LIVE` ve task listesi boş gösterdi. Ek read-only prob her robotta AMCL map örneğini, 8/8 lifecycle `active` durumunu, `NavigateToPose` action server'ını ve TF zincirini 1.02 saniye kesintisiz doğruladı.

`pick_B2` için görev öncesi gerçek Nav2 `ComputePathToPose` mesafeleri:

| Robot | Pickup rota mesafesi |
|---|---:|
| Alpha | 16.875 m |
| Beta | 12.649 m |
| Gamma | 9.169 m |

Bu, scheduler davranışını zorlamadı; yalnızca aday seçim kuralına göre Gamma'yı en kısa pickup rotasıyla seçen katalog noktasını kullandı. `quality_1`, geçerli config katalog dropoff noktasıdır.

İstek payload'u ve HTTP yanıtı kanıtta saklandı: `gamma-task-request.json`, `gamma-task-response-headers.txt`, `gamma-task-response.json`. Tek POST `POST /api/tasks` ile HTTP `201`, `outcome=APPLIED` ve task ID `web-e060891d-9f3a-4a73-acad-3383d3b0abb3` döndü. Atama `/api/fleet`/`/api/tasks`, SQLite ve Executor kaydıyla `robot_gamma`, epoch `1`, goal UUID `b166666d-970b-4c22-bee1-9f3a889c0ea2` olarak doğrulandı.

Executor Nav2 goal kabulünden sonra Gamma fiziksel olarak `(8.0, 5.5)` başlangıcından yaklaşık `(10.47, 4.74)` konumuna ilerledi. `pick_B2` `(6.0, 2.5)` hedefine ulaşmadı. Nav2 logu `compute_path_to_pose` ve `follow_path` action acknowledgement timeout'larını; Executor Nav2 status `6` (`ABORTED`) ve `NAV2_ABORTED` terminalini verdi. SQLite görev terminali `FAILED`, robot durumu `STATE_ERROR` (`6`), yük `false` olarak kaydedildi. Dropoff gönderilmedi. Görev `COMPLETED` varsayılmadı.

API polling sırasında tekrar eden 503/STALE gözlemleri `gamma-progress.jsonl` ve Manager/API snapshot kayıtlarında bulunur. Observer'da `UNSAFE_CONTACT` olayı ve `unsafe-contact` sentinel'i oluşmadı. Son 10 saniyede Gamma aynı `(10.508, 4.750)` pozunda, sıfır odometri hızı ve `STATE_ERROR` ile kaldı; bu stall koşulunda yalnız `c5-three-robot-e2e-20261117` container'ı SIGTERM ile durduruldu. `live/shutdown.json` bütün süreçlerin kod `0` ile kapandığını gösterir. Diğer container'lar durdurulmadı. Üç robotlu görev koşusu, Gamma testi başarısız olduğu için başlatılmadı.

Observer `status=READY`, `current_status=WAITING` geçişinde tam eksik fazı yazmıyor. `submit_gamma.py` içindeki bağımsız read-only kapı AMCL/Nav2/TF koşullarını aynı anda sağlanmış ölçse de observer alanı örneklerde `WAITING` idi. Kesin alt faz kök nedeni doğrulanmadı; observer kodu yalnız birleşik current status kaydetti. İstek ve pre-task teşhis JSON'u, `live/startup-readiness.json` ve startup/ROS kayıtları kanıt dizinindedir.
