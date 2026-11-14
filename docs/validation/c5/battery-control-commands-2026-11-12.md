# C5 Aşama 2.0 batarya kontrolü — komut eki

12 Kasım 2026; bütün komutlar depo kökünden. [Sonuç ve sınırlar](battery-control-validation-2026-11-12.md). Port/domain değerleri bu koşuya özgüdür, ürün sabiti değildir. Mevcut uzun şarj deneyi başka worktree/container'da bırakıldı; bu koşu onun ROS ağına bağlanmadı.

## Host ve Chrome

```bash
python3 -m venv /tmp/fleet-battery-control-venv
/tmp/fleet-battery-control-venv/bin/pip install -r requirements-c1.txt -r requirements-c5-test.txt pytest pytest-asyncio
PYTHONPATH=.:ros2_ws/src/fleet_battery_simulator:ros2_ws/src/fleet_robot_executor \
  /tmp/fleet-battery-control-venv/bin/python -m pytest tests -q
npm --prefix frontend ci
npm --prefix frontend run build
C5_UI_PORT=18884 C5_API_PORT=18885 C5_BROWSER_TEST_DIR=/tmp/c5-battery-browser-final \
  npm --prefix frontend test -- --workers=1
```

Host: 460 geçti / 22 atlandı. ROS olmadığı için atlananlar başarı sayılmaz. Chrome: 24 geçti (23 mevcut test + yeni panel testi). `frontend-build-final.log`, `host-tests-final.log`, `chrome-tests-final.log` gerçek son koşu çıktılarıdır. İlk host denemesi sistem Python'unda FastAPI ve paket yolları eksik olduğundan toplama aşamasında durdu; `host-targeted.log` bu başarısız denemeyi korur. Sonraki doğrulama izole venv ile yapıldı.

## IDL ve gerçek ROS

Bu koşuda önceden mevcut `ros2-fleet-c5-validation:humble-fortress` image'ı kullanıldı. Repo read-only, yalnız bu aşamanın kanıt dizini writable bağlandı:

```bash
docker run -d --name fleet-battery-control-validation --network bridge \
  -p 127.0.0.1:18885:18885 -v "$PWD":/workspace:ro \
  -v "$PWD/docs/validation/c5/battery-control-2026-11-12":/evidence \
  -w /workspace -e ROS_DOMAIN_ID=216 -e ROS_LOCALHOST_ONLY=1 \
  ros2-fleet-c5-validation:humble-fortress sleep infinity

docker exec fleet-battery-control-validation bash -lc '
  source /opt/ros/humble/setup.bash
  colcon --log-base /evidence/colcon-log build --base-paths interfaces/fleet_interfaces \
    --build-base /evidence/build --install-base /evidence/install
'

docker exec -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp fleet-battery-control-validation bash -lc '
  source /opt/ros/humble/setup.bash
  source /evidence/install/setup.bash
  export ROS_DOMAIN_ID=219
  export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/ros2_ws/src/fleet_robot_executor:$PYTHONPATH
  python3 -m pytest tests/test_battery_control.py tests/test_battery_control_ros2.py \
    tests/test_battery_ros2.py tests/test_c42_battery_ros2.py tests/test_c44_charging.py \
    -q -rs -o cache_dir=/evidence/pytest-cache
'
```

İlk colcon çağrısında `--log-base` yanlış konumda verildi; `idl-build-initial.log` bu CLI hatasını korur. Yukarıdaki global argüman sırası ile IDL build geçti; son ROS seçkisi 51 geçti / 0 atlandı. İlk ROS komutunda `PYTHONPATH` uzantısı yanlışlıkla ROS'un mevcut yolunu korumadı; `ros-tests.log` içindeki 3 atlama ROS kanıtı değildir. Bu düzeltildi. Fast DDS denemesinde `test_source_change_fences_assignment[legacy_type]` farklı tipte publisher yaratılmadan middleware tarafından reddedildi (`ros-integration.log`: 12 geçti / 1 kaldı). C4 kabulünde kullanılan Cyclone DDS ile aynı seçki geçti (`ros-cyclone.log`: 13 geçti). ROS servis anahtarı eklendikten sonra Chrome ve canlı probe ile eşzamanlı genişletilmiş koşuda eski `test_executor_restart_keeps_reset_gate` ilk BatteryState için 3 saniyelik DDS bekleme sınırında kaldı (`ros-concurrent-timeout.log`: 50 geçti / 1 kaldı). Ayrı domain 218 tekrarında eski clock-rewind testi ilk BatteryState beklemesinde kaldı (`ros-discovery-timeout.log`). `Rig.add_source` fixture'ında alıcı graph'ının yayıncı node kimliğini de keşfetmesi beklenir hale getirildi; publisher eşleşmesinin bu ayrı gözlemi garanti etmediği mevcut `test_discovery_waits_for_ros_node_identity` ile zaten tanımlıdır. Test iddiaları ve ürün kimlik retleri korunur. Son genişletilmiş seçki domain 219 ile `ros-tests-final.log` içindedir.

## İzole canlı ROS → API → Chrome

`battery_control_probe.py` iki gerçek Battery Simulator ve kontrollü `/clock` başlatır. Gerçek BatteryState örneklerini GUI sözleşmesine yazar; robot fiziksel durumu `NO_DATA`, pose ve istasyonlar boştur. Fleet Manager/Executor veya Gazebo kabulü değildir. Bu clock probe'u çalışan bir dünya/DDS domain'ine bağlanmamalıdır.

Gizli anahtar container içinde üretildi, hosta `/tmp/fleet-battery-control-token` olarak 0600 izinle alındı. Anahtar kanıta veya kaynak koduna yazılmadı:

```bash
docker exec fleet-battery-control-validation python3 -c \
  'import secrets,pathlib; p=pathlib.Path("/tmp/battery-control-token"); p.write_text(secrets.token_hex(32)); p.chmod(0o600)'
docker cp fleet-battery-control-validation:/tmp/battery-control-token /tmp/fleet-battery-control-token
chmod 600 /tmp/fleet-battery-control-token
```

Canlı süreçler aşağıdaki komutlarla, yalnız bu container içinde başlatıldı. Yeniden üretim için aynı komutları izole container'da kullanın; iki sürecin loglarını kanıt dizininde saklayın:

```bash
docker exec -d -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  fleet-battery-control-validation bash -lc '
    source /opt/ros/humble/setup.bash
    source /evidence/install/setup.bash
    export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/ros2_ws/src/fleet_robot_executor:$PYTHONPATH
    export FLEET_SIM_BATTERY_CONTROL=1
    export FLEET_SIM_BATTERY_TOKEN="$(cat /tmp/battery-control-token)"
    export C5_BATTERY_EVIDENCE=/evidence C5_FLEET_CONFIG=config/fleet.yaml
    export C5_API_PORT=18885 C5_BROWSER_ORIGIN=http://127.0.0.1:18884
    bash docker/simulation-c5/run_battery_control_probe.sh
  '
C5_UI_PORT=18884 C5_API_PORT=18885 npm --prefix frontend run dev
```

Vite ayrı terminalde çalışırken:

```bash
C5_UI_PORT=18884 C5_API_PORT=18885 \
  C5_BATTERY_EVIDENCE="$PWD/docs/validation/c5/battery-control-2026-11-12" \
  node frontend/tests/battery-live.mjs
```

İlk canlı deneme probe'un `source_session_id` alanı UUID olmadığı için mevcut frontend sözleşmesince reddedildi; düğme devre dışı kaldı (`live-chrome.log`). Probe gerçek UUID üretir hale getirildi. Ürün sözleşmesi gevşetilmedi. `live-chrome-retry.log` ilk başarılı, `live-chrome-final.log` ilk son görsel koşudur. ROS servisine de anahtar doğrulaması eklendikten sonra son canlı kabul `live-chrome-service-auth.log` ile tekrarlandı. `live-chrome.json`, `live-chrome.png`, `live-simulator.log` ve `live-api.log` son kanıtı tutar. `live-simulator-first-pass.log` / `live-api-first-pass.log` önceki başarılı koşuyu korur.

Bu test gerçek %25 SoC yazımını, diğer robota sıçramadığını, 5/15 dakika profilinin iki simülatörden 900/1120 W olarak geri okunmasını ve anahtarsız isteğin 401 almasını doğrular. Uzun şarj veya üç dock kabulü başlatılmadı.

## Diyagram ve kapanış

Mermaid kaynak ve SVG birlikte güncellendi. Yerelde var olan Mermaid CLI, Chrome yürütücüsüyle çalıştırıldı (`diagram-render.log`). `git diff --check` ve yeni Markdown bağlantıları kontrol edildi. Yalnız bu koşunun container/Vite süreçleri kapatılır; önceki deney container'ına stop/kill uygulanmaz. Commit ve push yapılmadı.
