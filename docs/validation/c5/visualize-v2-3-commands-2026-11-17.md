# Visualize V2.3 — komut ve sonuç eki

17 Kasım 2026. Komutlar `feature/visualize` kökünden çalıştırıldı. İzole container `visualize-v23-verified-20261117`, kanıt dizini `/tmp/visualize-v23-20261117/live4`.

| Komut / işlem | Sonuç |
|---|---|
| `python3 frontend/scripts/generate_warehouse_profile.py`; aynı komut `--check` ile | Profil üretildi; son kontrol **PASS**. |
| `npm --prefix frontend run build` | TypeScript ve Vite derlemesi **PASS**. |
| `C5_UI_PORT=21584 C5_API_PORT=21582 C5_BROWSER_TEST_DIR=/tmp/visualize-v23-browser2 npm --prefix frontend test -- visualize-v1.spec.ts warehouse-profile.spec.ts` | **5 passed**; mock Chrome regresyonu. |
| C5 image'ında `PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor python3 -m pytest -p no:cacheprovider tests/test_warehouse_grid.py tests/test_c43_station_dispatch.py tests/test_c5_dashboard.py tests/test_traffic_motion_gate.py -q` | **63 passed**, 1 deprecation uyarısı. |
| Humble + IDL overlay ile `PYTHONPATH=/workspace/fleet-visualizer/bridge:$PYTHONPATH /usr/bin/python3 -m unittest discover -s fleet-visualizer/bridge/tests -p ros_checks.py -v` | **4 passed**, skip yok. Overlay olmadan ilk deneme ROS importu eksik diye skip oldu; PASS sayılmadı. |
| C5 image'ında `load_config`, `raster`, `check_approaches`, `profile_digest` | **PASS**, profil özeti `e9dfb0d9cb42…`. |
| `docker inspect visualize-v23-verified-20261117`; üretilen `warehouse.sdf`, `map.yaml`, `reset-verified.json` | Kaynak bu worktree, SDF hedef pozları ve gerçek fiziksel reset **PASS**. |
| Container içinde `ros2 topic echo /clock --once`, `ros2 topic echo /tf --once`; `GET /api/fleet` | Canlı saat, TF ve üç ürün LIVE **PASS**. |
| `ws://127.0.0.1:21582/ws/fleet`, Origin `http://127.0.0.1:21584`, `fleet.scene.v1`, 5 sn | 201 `robot_pose`, üç `data_status: LIVE`, üç ürün LIVE **PASS**; [JSON](visualize-v2-3-2026-11-17/websocket-sample.json). |
| Chrome `http://127.0.0.1:21584/`, izometrik ve üstten sahne | Üç model, ayrı `robot_alpha`/`robot_beta`/`robot_gamma` etiketleri, `3/3 TF LIVE` **PASS**. |
| `git diff --check` | **PASS**. Commit/push yapılmadı. |

İzole Docker başlangıcında C5 image'ına `fleet_perception` ayrı overlay olarak derlendi; mevcut `stage1_run.py --ros-overlay` kullanıldı. `--add-host scene:127.0.0.1`, aynı container içindeki API'nin köprüye erişmesini sağladı. Güvenlik zarfı değiştirilmedi; `NavigateToPose`, `ExecuteTask`, permit veya hız komutu gönderilmedi.
