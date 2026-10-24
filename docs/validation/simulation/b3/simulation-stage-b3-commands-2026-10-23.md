# Aşama B3 Komut ve Çıktı Eki

[Ana B3 doğrulama kaydı](simulation-stage-b3-2026-10-23.md).

## 1. Birim Testleri

```sh
docker run --rm -v $(pwd)/config:/config:ro -v $(pwd)/docker/simulation-b3:/opt/simulation-b3:ro -w /opt/simulation-b3 ros2-fleet-simulation-nav2-check:humble-fortress python3 -m unittest discover -s /opt/simulation-b3 -p "test_*.py"
```

Çıkış kodu: 0

```text
...
----------------------------------------------------------------------
Ran 3 tests in 0.007s

OK
```

## 2. Docker Compose Yapılandırma Doğrulaması

```sh
env DDS_TEST_PAYLOAD=test-config docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-b3.yml config
```

Çıkış kodu: 0

---

## 3. Canlı Koşu 1 (`simulation-b3-20261023-01`)

```sh
env DDS_TEST_PAYLOAD=simulation-b3-20261023-01 ROS_DOMAIN_ID=45 ROS_LOCALHOST_ONLY=0 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-b3.yml up --abort-on-container-exit --exit-code-from backend
```

Sonuç: TF remapping uyuşmazlığı nedeniyle durduruldu (Hata satırları kaydedildi).

```text
simulation-1  | [component_container_isolated-1] [INFO] [robot_1.local_costmap.local_costmap]: Timed out waiting for transform from robot_1/base_link to robot_1/odom to become available, tf error: Invalid frame ID "robot_1/odom" passed to canTransform argument target_frame - frame does not exist
```

Temizlik komutu:
```sh
env DDS_TEST_PAYLOAD=cleanup docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-b3.yml down -v --remove-orphans
```

Çıkış kodu: 0

---

## 4. Canlı Koşu 2 (`simulation-b3-20261023-02`)

```sh
env DDS_TEST_PAYLOAD=simulation-b3-20261023-02 ROS_DOMAIN_ID=46 ROS_LOCALHOST_ONLY=0 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-b3.yml up --abort-on-container-exit --exit-code-from backend
```

Çıkış kodu: 0

### Önemli JSON Olayları:
```json
{"event": "CONFIG_VALID", "role": "backend", "token": "simulation-b3-20261023-02"}
{"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp", "token": "simulation-b3-20261023-02"}
{"event": "CLOCK_AND_SENSORS_OK", "clock": 1.822, "robot_1_scans": 10, "robot_2_scans": 10, "robot_1_odom_frame": "robot_1/odom", "robot_2_odom_frame": "robot_2/odom", "robot_1_gt": [1.000000005689777, 1.5, 0.1999998861964761, 1.8930741510996536e-20], "robot_2_gt": [-1.000000005689777, -1.5, 0.1999998861964761, -3.141592653589587]}
{"event": "LIFECYCLE_ACTIVE", "total_nodes": 12, "states": {"/robot_1/map_server": "active", "/robot_1/amcl": "active", "/robot_1/controller_server": "active", "/robot_1/planner_server": "active", "/robot_1/behavior_server": "active", "/robot_1/bt_navigator": "active", "/robot_2/map_server": "active", "/robot_2/amcl": "active", "/robot_2/controller_server": "active", "/robot_2/planner_server": "active", "/robot_2/behavior_server": "active", "/robot_2/bt_navigator": "active"}}
{"event": "TF_CHAINS_VALID", "robot_1_trans": [1.0, 1.5000000000000002], "robot_2_trans": [-1.0, -1.5000000000000002]}
{"event": "AMCL_INITIAL_POSE", "robot": "robot_1", "x": 1.0, "y": 1.5000000000000002, "error_m": 2.220446049250313e-16}
{"event": "AMCL_INITIAL_POSE", "robot": "robot_2", "x": -1.0, "y": -1.5000000000000002, "error_m": 2.220446049250313e-16}
{"event": "AMCL_INITIAL_POSES_VALID"}
{"event": "SENDING_NAVIGATE_TO_POSE_GOAL", "robot": "robot_1", "target_x": 2.5, "target_y": 1.5, "target_yaw": 0.0}
{"event": "SENDING_NAVIGATE_TO_POSE_GOAL", "robot": "robot_2", "target_x": -2.5, "target_y": -1.5, "target_yaw": 3.14159265359}
{"event": "GOAL_ACCEPTED", "robot": "robot_1"}
{"event": "GOAL_ACCEPTED", "robot": "robot_2"}
{"event": "MONITORING_PARALLEL_NAVIGATION"}
{"event": "NAVIGATION_PROGRESS", "robot_1_done": false, "robot_2_done": false, "inter_robot_dist_m": 4.161387273317691, "min_inter_robot_dist_m": 3.60555128177623}
{"event": "NAVIGATION_PROGRESS", "robot_1_done": false, "robot_2_done": false, "inter_robot_dist_m": 4.873169965310952, "min_inter_robot_dist_m": 3.60555128177623}
{"event": "GOALS_COMPLETED_CHECKING_RESULTS"}
{"event": "DESTINATION_REACHED", "robot": "robot_1", "status": 4, "dist_odom_m": 1.959986923874663, "dist_amcl_m": 0.29161160845602113, "dist_gt_m": 0.21127666029096298, "tolerance_m": 0.35}
{"event": "DESTINATION_REACHED", "robot": "robot_2", "status": 4, "dist_odom_m": 4.086777345405563, "dist_amcl_m": 0.2670414409757245, "dist_gt_m": 0.19887590073613529, "tolerance_m": 0.35}
{"event": "RESOURCE_METRICS", "run_duration_s": 11.37, "total_cpu_time_s": 5.07, "avg_cpu_percent": 44.57, "peak_memory_mb": 50.66, "scan_rates_hz": {"robot_1": 5.0, "robot_2": 5.0}, "total_scans": {"robot_1": 44, "robot_2": 44}, "min_inter_robot_distance_m": 3.6056}
{"event": "B3_PASS", "token": "simulation-b3-20261023-02", "robot_1_final_dist_m": 0.29161160845602113, "robot_2_final_dist_m": 0.2670414409757245, "min_inter_robot_distance_m": 3.6056, "avg_cpu_percent": 44.57, "peak_memory_mb": 50.66}
```

Temizlik komutu:
```sh
env DDS_TEST_PAYLOAD=cleanup docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-b3.yml down -v --remove-orphans
```

Çıkış kodu: 0

---

## 5. Canlı Koşu 3 (`simulation-b3-20261023-03`)

```sh
env DDS_TEST_PAYLOAD=simulation-b3-20261023-03 ROS_DOMAIN_ID=47 ROS_LOCALHOST_ONLY=0 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-b3.yml up --abort-on-container-exit --exit-code-from backend
```

Çıkış kodu: 1

### Önemli JSON Olayları:
```json
{"event": "CONFIG_VALID", "role": "backend", "token": "simulation-b3-20261023-03"}
{"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp", "token": "simulation-b3-20261023-03"}
{"event": "CLOCK_AND_SENSORS_OK", "clock": 1.812, "robot_1_scans": 10, "robot_2_scans": 10, "robot_1_odom_frame": "robot_1/odom", "robot_2_odom_frame": "robot_2/odom", "robot_1_gt": [1.000000005689777, 1.5, 0.1999998861964761, 1.8930741510996536e-20], "robot_2_gt": [-1.000000005689777, -1.5, 0.1999998861964761, -3.141592653589587]}
{"event": "LIFECYCLE_ACTIVE", "total_nodes": 12, "states": {"/robot_1/map_server": "active", "/robot_1/amcl": "active", "/robot_1/controller_server": "active", "/robot_1/planner_server": "active", "/robot_1/behavior_server": "active", "/robot_1/bt_navigator": "active", "/robot_2/map_server": "active", "/robot_2/amcl": "active", "/robot_2/controller_server": "active", "/robot_2/planner_server": "active", "/robot_2/behavior_server": "active", "/robot_2/bt_navigator": "active"}}
{"event": "TF_CHAINS_VALID", "robot_1_trans": [1.0, 1.5000000000000002], "robot_2_trans": [-1.0, -1.5000000000000002]}
{"event": "AMCL_INITIAL_POSE", "robot": "robot_1", "x": 1.0, "y": 1.5000000000000002, "error_m": 2.220446049250313e-16}
{"event": "AMCL_INITIAL_POSE", "robot": "robot_2", "x": -1.0, "y": -1.5000000000000002, "error_m": 2.220446049250313e-16}
{"event": "AMCL_INITIAL_POSES_VALID"}
{"event": "SENDING_NAVIGATE_TO_POSE_GOAL", "robot": "robot_1", "target_x": 2.5, "target_y": 1.5, "target_yaw": 0.0}
{"event": "SENDING_NAVIGATE_TO_POSE_GOAL", "robot": "robot_2", "target_x": -2.5, "target_y": -1.5, "target_yaw": 3.14159265359}
{"event": "GOAL_ACCEPTED", "robot": "robot_1"}
{"event": "GOAL_ACCEPTED", "robot": "robot_2"}
{"event": "MONITORING_PARALLEL_NAVIGATION"}
{"event": "NAVIGATION_PROGRESS", "robot_1_done": false, "robot_2_done": false, "inter_robot_dist_m": 4.2107800904951205, "min_inter_robot_dist_m": 3.60555128177623}
{"event": "NAVIGATION_PROGRESS", "robot_1_done": false, "robot_2_done": false, "inter_robot_dist_m": 4.966157158349693, "min_inter_robot_dist_m": 3.60555128177623}
{"event": "GOALS_COMPLETED_CHECKING_RESULTS"}
{"event": "DESTINATION_REACHED", "robot": "robot_1", "status": 4, "dist_odom_m": 1.9234932877038906, "dist_amcl_m": 0.3463363829495168, "dist_gt_m": 0.2041192295115727, "tolerance_m": 0.35}
{"event": "DESTINATION_REACHED", "robot": "robot_2", "status": 4, "dist_odom_m": 4.0734264155309114, "dist_amcl_m": 0.3525102042695336, "dist_gt_m": 0.2114732779971848, "tolerance_m": 0.35}
{"event": "FAIL", "error": "Robot robot_2 finished too far from goal: odom_err=4.0734m, amcl_err=0.3525m, tol=0.3500m", "error_type": "ValueError"}
```

Temizlik komutu:
```sh
env DDS_TEST_PAYLOAD=cleanup docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-b3.yml down -v --remove-orphans
```

Çıkış kodu: 0
