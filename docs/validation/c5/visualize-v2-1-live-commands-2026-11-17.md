# Visualize V2.1 — komut ve sonuç eki

17 Kasım 2026. Komutlar `feature/visualize` depo kökünden çalıştırıldı. Çalışan container'a yalnız okuma, ROS parametre sorgusu, WebSocket aboneliği ve `ComputePathToPose` plan isteği yapıldı. `NavigateToPose`, `ExecuteTask`, permit veya hız komutu gönderilmedi.

| Komut / işlem | Sonuç |
|---|---|
| `git status --short --branch`; `docker ps`; `docker inspect c5-20261117T081139Z-0ead015f09` | `feature/visualize` kullanıcı değişiklikleri korundu; container salt okunur `/private/tmp/ros2-fleet-manager-c5-alpha-beta-stable` mount'u ve `stage1_run.py config/fleet.warehouse-30x18.yaml` komutu belirlendi. |
| Container içinde `load_config` + `profile_digest`; `GET http://127.0.0.1:21482/api/warehouse-layout`; `GET /api/fleet` | Profil özeti `58a5ca33e1995d1c765e93f25bf3e65c669fde8a0f2e56a798dc98071cddfb65` eşleşti. API'de üç robot ve eski üç park pozu bulundu. |
| Hostta `load_config` ile feature ve bağlı üç robotlu YAML engelleri/istasyonlarının karşılaştırılması | Raf/duvar engelleri eşit; robot sayısı 2/3 ve park hedefleri farklı. |
| `docker exec ... ros2 param get /robot_alpha/{local_costmap,global_costmap}/... robot_radius` ve `inflation_layer.inflation_radius` | Her iki costmap'te yarıçap 0,30 m, inflation 0,45 m. Diğer iki robotun runtime parametreleri bu koşuda ayrı sorgulanmadı. |
| Container içinde ROS `ComputePathToPose` (`GridBased`, `use_start=True`), üç robotun snapshot pozundan yeni karşılık gelen park hedefine; her yeni park hedefinden `dock_6` ve `(11,5;2,5)` noktasına | **9/9 plan sonucu `SUCCEEDED`.** Park giriş uzunlukları alpha 10,401 m, beta 9,068 m, gamma 8,486 m. En dar statik engel uzaklığı 0,471 m (`rack_B2`). Hareket yapılmadı. |
| `docker exec ... timeout 5 ros2 topic hz /tf`; `timeout 5 ros2 topic echo /clock --once`; `ros2 topic info /tf -v` | Yayıncı kayıtlı; gözlem süresinde `/tf` ve `/clock` örneği alınmadı. |
| `websockets.connect('ws://127.0.0.1:21482/ws/fleet', origin='http://127.0.0.1:21484', subprotocols=['fleet.scene.v1'])`, 6 saniye | 25 ürün snapshot'ı, artan sıra; 0 `robot_pose`; 36 `data_status`, üç robot için STALE. |
| `docker exec ... ros2 service list | grep traffic`; `ros2 topic list | grep -E 'traffic|permit'` | Aktif trafik permit servisi/topic'i bulunmadı. |
| `docker run --rm -v '/Users/murat/develop/ros2-fleet-manager-visualize:/workspace:ro' -w /workspace --entrypoint bash ros2-fleet-c5-validation:humble-fortress -lc 'PYTHONPATH=/workspace:/workspace/backend python3 -m pytest tests/test_warehouse_grid.py -q'` | **3 passed**; önceki global host ortamındaki `fastapi` eksikliği image içinde yok. Salt okunur mount nedeniyle pytest cache uyarısı. |
| Aynı image/mount ile `PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor python3 -m pytest -p no:cacheprovider tests/test_warehouse_grid.py tests/test_c43_station_dispatch.py tests/test_c5_dashboard.py tests/test_traffic_motion_gate.py -q` | **63 passed**, 1 Starlette/httpx deprecation uyarısı. |
| `C5_UI_PORT=18471 C5_API_PORT=18472 npm --prefix frontend test -- visualize-v1.spec.ts warehouse-profile.spec.ts` | **5 passed** mock Chrome. Bağlı gerçek API olmadığı için fixture dışı `/api/task-catalog` proxy hatası; canlı test sayılmaz. |

Canlı simülasyon eski hedeflerde ve TF/clock duraksamış olduğundan fiziksel park, şarj ve eşzamanlı çıkış komutları çalıştırılmadı.
