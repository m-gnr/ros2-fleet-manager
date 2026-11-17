# Visualize → main entegrasyon komut eki

17 Kasım 2026. Komutlar `/Users/murat/develop/ros2-fleet-manager-visualize-integration` worktree’sinde çalıştırıldı. ROS/C5 test container’larına kaynak kodu salt okunur bağlandı; hareket komutu gönderilmedi.

| Komut | Sonuç |
|---|---|
| `C5_UI_PORT=5254 C5_API_PORT=8254 C5_BROWSER_TEST_DIR=/tmp/visualize-main-integration-final2 npm test -- --workers=1 --reporter=line` (`frontend/`) | **34 passed**. Task-catalog backend’i çalışmadığından test fixture’ları dışındaki API proxy isteklerinde `ECONNREFUSED` uyarıları görüldü. |
| `npm run build` (`frontend/`) | **PASS**, TypeScript + Vite. Rollup, Zod içindeki iki `@__PURE__` açıklamasını kaldıramadığına dair uyarı yazdı. |
| `python3 -m fleet_config config/fleet.warehouse-30x18.yaml` | **PASS**, üç robot; schema, semantic ve dosya başvurusu kontrolleri geçti. |
| `python3 -c '...assert one robot_gamma; assert gamma pose equals park_3...'` | **PASS**; tam bir gamma, üç benzersiz namespace, eşleşen `(13.5, 4.0, π)` pozu. |
| `python3 scripts/generate_warehouse_profile.py --check` (`frontend/`) | **PASS**. |
| `docker run --rm --network none -v <integration-worktree>:/workspace:ro ... python3 -m pytest -p no:cacheprovider tests/test_fleet_manager_domain.py tests/test_fleet_manager_outbox.py tests/test_warehouse_grid.py tests/test_c43_station_dispatch.py tests/test_c44_charging.py tests/test_c5_dashboard.py tests/test_traffic_core.py tests/test_traffic_protocol.py tests/test_traffic_motion_gate.py ros2_ws/src/fleet_robot_executor/test -q -rs` | **255 passed, 8 skipped**. Sekiz skip, test imajında Executor ROS node fixture’larının interface kurulum koşulunu sağlayamamasından kaynaklanıyor. |
| Humble container içinde `colcon --log-base /tmp/ros-log build --packages-select fleet_interfaces --base-paths /workspace/interfaces/fleet_interfaces --build-base /tmp/ros-build --install-base /tmp/ros-install --merge-install`, sonra `PYTHONPATH=/workspace/fleet-visualizer/bridge:$PYTHONPATH /usr/bin/python3 -m unittest discover -s /workspace/fleet-visualizer/bridge/tests -p ros_checks.py -v` | **4 passed**, skip yok. |
| `git diff --cached --check && git diff --check` | **PASS**. |
| `origin/main` tabanı üzerinde Playwright karşılaştırması: `lists robots...`, `keeps product and TF validity...`, `fits, follows...`, `shows a small reconnecting state after five seconds...` | **2 failed, 2 passed**. İlk ikisi grid/WAITING-for-TF eski beklentileriyle fail; kamera NaN ve 5 saniyelik reconnect testleri main tabanında geçti. |

Tam rapor ve hareket/Gazebo kapsam sınırları: [entegrasyon regresyon raporu](visualize-main-integration-2026-11-17.md). Push yapılmadı; kullanıcı onayı bekleniyor.
