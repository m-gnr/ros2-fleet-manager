# Visualize → main entegrasyon komut eki

17 Kasım 2026. Komutlar `/Users/murat/develop/ros2-fleet-manager-visualize` kökünden çalıştırıldı; C5/ROS hedefli testler mevcut, izole `visualize-v3-gui-20261117` container'ında yürütüldü. Kaynak bind'i salt okunurdu. Hiçbir görev veya hareket komutu gönderilmedi.

| Komut / işlem | Sonuç |
|---|---|
| `npm --prefix frontend run build` | TypeScript + Vite **PASS**. Zod paketinde mevcut Rollup annotation uyarıları vardı. |
| `C5_UI_PORT=5233 C5_API_PORT=8233 C5_BROWSER_TEST_DIR=/tmp/visualize-v6-palette npm --prefix frontend test -- visualize-v1.spec.ts --workers=1 --reporter=line` | **3 passed**. Fixture tabanlı Chrome regresyonu; yerel task-catalog API yokluğu için beklenen proxy uyarısı görüldü. |
| `docker exec visualize-v3-gui-20261117 bash -lc 'source /opt/ros/humble/setup.bash && source /evidence/overlay-install/setup.bash && cd /workspace && PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tests/test_warehouse_grid.py tests/test_c43_station_dispatch.py tests/test_c5_dashboard.py tests/test_traffic_motion_gate.py -q'` | **63 passed**, 1 Starlette/httpx deprecation uyarısı. |
| Aynı image'da Scheduler/Outbox/dispatch/charge/traffic/Executor paketi: `python3 -m pytest -p no:cacheprovider tests/test_fleet_manager_domain.py tests/test_fleet_manager_outbox.py tests/test_c43_station_dispatch.py tests/test_c44_charging.py tests/test_traffic_core.py tests/test_traffic_protocol.py tests/test_traffic_motion_gate.py ros2_ws/src/fleet_robot_executor/test -q -rs` | **245 passed, 8 skipped**. Skip edilenler Executor ROS düğüm fixture'larıdır; test ortamı kaynaklıdır. |
| Humble + IDL overlay: `PYTHONPATH=/workspace/fleet-visualizer/bridge:$PYTHONPATH /usr/bin/python3 -m unittest discover -s fleet-visualizer/bridge/tests -p ros_checks.py -v` | **4 passed**, skip yok. |
| Yerel host komutu `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test` | **Koleksiyon durdu:** yerel Python ortamında `fastapi`, ROS paketleri ve çalışma alanı Python modülleri bulunmadı; 10 import hatası, 7 ROS testi skip. Bu sonuç PASS sayılmadı. |
| Mevcut Chrome canlı paneli salt okunur gözlem | **3/3 TF LIVE**, üç robot bağlı ve ürün telemetrisi güncel; görev sayısı 0, `Çevreyi göster` açık, V1–V6 görünümü çizildi. Yeni Gazebo spawn veya yeni WebSocket örneği alınmadı. |
| Gerçek görev, park/şarj hareketi veya permit ile nonzero hareket | **Çalıştırılmadı.** Güvenlik kabulindeki eksikler nedeniyle kullanıcı koşulu sağlanmıyor. |
| `git diff --check` | Palet değişikliği için **PASS**. |

Merge/push yapılmadı. Tam sınırlama ve karar [entegrasyon raporundadır](visualize-main-integration-2026-11-17.md).
