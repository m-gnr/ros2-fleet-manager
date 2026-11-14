# C5-B2 hedefli doğrulama komutları

- `PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_obstacle_sensors.py` — 9 passed.
- `PYTHONPATH=. python3 -m fleet_config config/fleet.warehouse-30x18.yaml` — 2 robot geçerli.
- `git diff --check` — temiz.
- Tek kontrollü Gazebo koşusu container `fleet-c5-b2-live-retry-20261114` içinde yürütüldü; image `ros2-fleet-c5-validation:humble-fortress` (SHA `7fb7e7fc4aebe0d2b4097752e9b470e30d8ea7a8126bb1dee87d03f30330609d`), partition/domain `fleet-c5-b2-live-retry-20261114` / 192. `colcon build --base-paths interfaces/fleet_interfaces ros2_ws/src/fleet_perception` — 2 paket geçti.
- Çalışan koşuda `ros2 topic list` local costmap, `/scan`, `/physical_pose` ve `perception_observations` başlıklarını gösterdi. İki costmap observation raporunda üç kaynağın her biri `used: true`; grid çözünürlük 0.05 m, boyut 60×60 (3×3 m).
- Kapanış: `docker stop --time 50 fleet-c5-b2-live-retry-20261114`; container exit 0, OOM yok; observer `unsafe-contact` üretmedi. İlk, Gazebo başlamayan build denemesi IDL hedefi hatasıyla başarısız oldu ve çalışma kanıtında tutuldu.
