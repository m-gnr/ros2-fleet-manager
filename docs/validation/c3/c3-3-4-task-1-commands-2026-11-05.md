# C3.3.4 Görev 1 — Doğrulama komutları

5 Kasım 2026 tarihinde depo kökünden çalıştırıldı. [Doğrulama raporu](c3-3-4-task-1-validation-2026-11-05.md)

## Host ve config

```sh
# Düzeltme öncesi 3 başarısız (APPLIED yerine STALE bekleniyordu)
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor python3 -m pytest -q \
  tests/test_fleet_manager_outbox.py -k invalid_terminal_epochs --tb=short

# 219 geçti, 16 ROS testi atlandı
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor python3 -m pytest -q -rs tests/

# 3 geçti
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor python3 -m pytest -q \
  docker/simulation-c3-3-3/test_config.py
```

## ROS 2 Humble ve CycloneDDS

Yerel `ros2-fleet-simulation-nav2-check:humble-fortress` Linux/arm64 imajı kullanıldı. `colcon` üç paketi derledi. Doğrudan `rclpy` kullanan testler için launch eklentilerinin otomatik yüklemesi engellendi.

```sh
docker run --rm --name ros2-fleet-c334-epoch-tests \
  -e ROS_DOMAIN_ID=53 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -w /work --entrypoint bash \
  ros2-fleet-simulation-nav2-check:humble-fortress -c '
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src || exit
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:/repo/ros2_ws/src/fleet_robot_executor:$PYTHONPATH
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
  tests/test_executor_*.py tests/test_c2_3_config.py tests/test_ros2_*.py \
  tests/test_task_review_holds.py tests/test_clear_robot_error_client.py \
  tests/test_fleet_manager_domain.py tests/test_fleet_manager_outbox.py
'
```

## Canlı simülasyon

DDS → A → ilgili simülasyon katmanı için `docker compose config` ile bind mount kaynakları, imaj ve etkin domain 42 kontrol edildi. İki koşu ayrı Compose projeleriyle mevcut Nav2 imajını kullandı.

```sh
# T01–T10, 10/10, backend çıkışı 0
COMPOSE_PROJECT_NAME=ros2-fleet-c334-epoch python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-epoch-20261105

# 7/7, backend çıkışı 0
COMPOSE_PROJECT_NAME=ros2-fleet-c334-c23 python3 scripts/run_c2_3.py \
  --domain 42 --token c334-c23-20261105
```

## Diyagram

[Mevcut tema](../organization/organization-commands-2026-10-26.md#mermaid-ve-svg-üretimi) ve Mermaid CLI 11.12.0 ile `assignment-reconciliation.svg` yeniden üretildi. SVG XML olarak ayrıştırıldı. Uyarı etiketi, uygulama durumu ve katalogdaki Mermaid bloğunun kaynakla eşleşmesi kontrol edildi.
