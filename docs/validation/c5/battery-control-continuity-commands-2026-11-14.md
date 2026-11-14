# Battery Control / C4 süreklilik komutları

Repo kökünden hedefli test:

```bash
PYTHONPATH=ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator:.:${PYTHONPATH:-} \
  python3 -m pytest -q \
  tests/test_c42_battery_measurement.py \
  tests/test_c42_battery_domain.py
```

Sonuç: `35 passed`.

Python sözdizimi kontrolü:

```bash
python3 -m compileall -q \
  backend/fleet_manager/adapters/status_subscriber.py \
  backend/fleet_manager/domain/fleet_manager_core.py \
  backend/fleet_manager/domain/fleet_tracker.py \
  backend/fleet_manager/domain/models.py \
  ros2_ws/src/fleet_battery_simulator/fleet_battery_simulator/node.py \
  ros2_ws/src/fleet_robot_executor/fleet_robot_executor/battery.py \
  ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py \
  tests/test_c42_battery_measurement.py \
  tests/test_c42_battery_domain.py
```

Sonuç: geçti. Host'ta `ros2` ve `colcon` bulunmadığı için interface build ve ROS/Gazebo kontrolleri çalıştırılmadı. Chrome `http://127.0.0.1:20301/?trace=1#overview` adresindeki hazır panel mevcut olsa da backend bağlantısı yoktu; gerçek panel SoC kontrolü denenmedi.
