# Bölüm B: AMCL Gerçek Sınama Komut ve Çıktı Eki

[Ana sınama kaydı](simulation-stage-amcl-test-2026-10-23.md).

## 1. Birim Testleri

```sh
docker run --rm -v $(pwd)/config:/config:ro -v $(pwd)/docker/simulation-amcl-test:/opt/simulation-amcl-test:ro -w /opt/simulation-amcl-test ros2-fleet-simulation-nav2-check:humble-fortress python3 -m unittest discover -s /opt/simulation-amcl-test -p "test_*.py"
```

Çıkış kodu: 0

```text
..
----------------------------------------------------------------------
Ran 2 tests in 0.004s

OK
```

## 2. Docker Compose Yapılandırma Doğrulaması

```sh
env DDS_TEST_PAYLOAD=test-config docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-amcl-test.yml config
```

Çıkış kodu: 0

---

## 3. Canlı Koşu 1 (`amcl-test-20261023-01`)

```sh
env DDS_TEST_PAYLOAD=amcl-test-20261023-01 ROS_DOMAIN_ID=43 ROS_LOCALHOST_ONLY=0 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-amcl-test.yml up --abort-on-container-exit --exit-code-from backend
```

Çıkış kodu: 0

### Önemli JSON Olayları:
```json
{"event": "CONFIG_VALID", "role": "backend", "token": "amcl-test-20261023-01"}
{"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp", "token": "amcl-test-20261023-01"}
{"event": "CLOCK_AND_SENSORS_OK", "clock": 1.806, "scan_count": 10, "ground_truth_x": 5.689782139542728e-09, "ground_truth_y": 2.185537253135847e-15, "ground_truth_yaw": -4.3689147706961365e-20}
{"event": "LIFECYCLE_ACTIVE", "states": {"map_server": "active", "amcl": "active", "controller_server": "active", "planner_server": "active", "behavior_server": "active", "bt_navigator": "active"}}
{"event": "INITIAL_AMCL_POSE_WITH_OFFSET", "ground_truth_x": 5.689782139542728e-09, "ground_truth_y": 2.185537253135847e-15, "ground_truth_yaw": -4.3689147706961365e-20, "amcl_x": 0.5, "amcl_y": 0.3000000000000005, "amcl_yaw": 0.300000000000005, "initial_error_m": 0.5830951846055813, "initial_yaw_error_rad": 0.30000000000000515, "map_to_odom_translation": [0.49999999999999994, 0.30000000000000054, 0.0]}
{"event": "STARTING_DRIVE_MOTION", "linear_v": 0.2, "angular_w": 0.15, "duration_s": 6.0}
{"event": "DRIVE_PROGRESS", "elapsed_s": 1.0, "gt_x": 0.193331398708489, "gt_y": 0.015280905174510216, "amcl_x": 0.59338320114119, "amcl_y": 0.33240396027158897, "error_m": 0.5104982631740853}
{"event": "DRIVE_PROGRESS", "elapsed_s": 2.0, "gt_x": 0.3877951296508414, "gt_y": 0.06355714060044676, "amcl_x": 0.810194665226584, "amcl_y": 0.4321120489551629, "error_m": 0.5605837030515214}
{"event": "DRIVE_PROGRESS", "elapsed_s": 3.0, "gt_x": 0.5713396120258757, "gt_y": 0.14342155948085591, "amcl_x": 1.006577175617316, "amcl_y": 0.5592560338302661, "error_m": 0.6019551867194629}
{"event": "DRIVE_PROGRESS", "elapsed_s": 4.0, "gt_x": 0.7387396884746312, "gt_y": 0.25243852487976864, "amcl_x": 1.0976061748585233, "amcl_y": 0.6240891369579424, "error_m": 0.5166326862555266}
{"event": "DRIVE_PROGRESS", "elapsed_s": 5.0, "gt_x": 0.8851933270755484, "gt_y": 0.38712682059913134, "amcl_x": 1.2613676878445936, "amcl_y": 0.8181493148434699, "error_m": 0.5720905000475105}
{"event": "DRIVE_PROGRESS", "elapsed_s": 6.0, "gt_x": 1.0062840583743935, "gt_y": 0.5424891335064171, "amcl_x": 1.327602015181693, "amcl_y": 0.9305315741677415, "error_m": 0.5038076667947948}
{"event": "MOTION_STOPPED_WAITING_SETTLE"}
{"event": "FINAL_AMCL_EVALUATION", "ground_truth_x": 1.0718142420290726, "ground_truth_y": 0.6434479426467757, "ground_truth_yaw": 0.9948055987840227, "amcl_x": 1.327602015181693, "amcl_y": 0.9305315741677415, "amcl_yaw": 1.050498969044303, "initial_error_m": 0.5830951846055813, "final_error_m": 0.3845053918759033, "error_reduction_m": 0.19858979272967797, "tolerance_m": 0.4, "passed": true, "initial_map_to_odom": [0.49999999999999994, 0.30000000000000054, 0.0], "final_map_to_odom": [0.42873466804652893, 0.2852536135701936, 0.0]}
{"event": "METRICS", "measured_scan_rate_hz": 4.999999999999999, "total_scan_messages": 60, "cgroup_usage_usec": 5109885}
{"event": "AMCL_TEST_PASS", "token": "amcl-test-20261023-01", "initial_error_m": 0.5830951846055813, "final_error_m": 0.3845053918759033, "error_reduction_m": 0.19858979272967797, "tolerance_m": 0.4}
```

---

## 4. Koşular Arası Temizlik

```sh
env DDS_TEST_PAYLOAD=amcl-cleanup docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-amcl-test.yml down -v --remove-orphans
```

Çıkış kodu: 0

---

## 5. Canlı Koşu 2 (`amcl-test-20261023-02`)

```sh
env DDS_TEST_PAYLOAD=amcl-test-20261023-02 ROS_DOMAIN_ID=44 ROS_LOCALHOST_ONLY=0 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-amcl-test.yml up --abort-on-container-exit --exit-code-from backend
```

Çıkış kodu: 1

### Önemli JSON Olayları:
```json
{"event": "CONFIG_VALID", "role": "backend", "token": "amcl-test-20261023-02"}
{"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp", "token": "amcl-test-20261023-02"}
{"event": "CLOCK_AND_SENSORS_OK", "clock": 1.806, "scan_count": 10, "ground_truth_x": 5.689782139542728e-09, "ground_truth_y": 2.185537253135847e-15, "ground_truth_yaw": -4.3689147706961365e-20}
{"event": "LIFECYCLE_ACTIVE", "states": {"map_server": "active", "amcl": "active", "controller_server": "active", "planner_server": "active", "behavior_server": "active", "bt_navigator": "active"}}
{"event": "INITIAL_AMCL_POSE_WITH_OFFSET", "ground_truth_x": 5.689782139542728e-09, "ground_truth_y": 2.185537253135847e-15, "ground_truth_yaw": -4.3689147706961365e-20, "amcl_x": 0.5, "amcl_y": 0.3000000000000005, "amcl_yaw": 0.300000000000005, "initial_error_m": 0.5830951846055813, "initial_yaw_error_rad": 0.30000000000000515, "map_to_odom_translation": [0.49999999999999994, 0.30000000000000054, 0.0]}
{"event": "STARTING_DRIVE_MOTION", "linear_v": 0.2, "angular_w": 0.15, "duration_s": 6.0}
{"event": "DRIVE_PROGRESS", "elapsed_s": 1.0, "gt_x": 0.19412116955660333, "gt_y": 0.015408427564383294, "amcl_x": 0.6041135518333811, "amcl_y": 0.3363321151003997, "error_m": 0.5206589735582228}
{"event": "DRIVE_PROGRESS", "elapsed_s": 2.0, "gt_x": 0.3877951296506634, "gt_y": 0.06355714059986078, "amcl_x": 0.8164771984108729, "amcl_y": 0.43185442162090676, "error_m": 0.5651647576450856}
{"event": "DRIVE_PROGRESS", "elapsed_s": 3.0, "gt_x": 0.5686963822385009, "gt_y": 0.14200264144921085, "amcl_x": 0.9067422448481349, "amcl_y": 0.48582382657945966, "error_m": 0.48217010750549477}
{"event": "DRIVE_PROGRESS", "elapsed_s": 4.0, "gt_x": 0.6981413267807309, "gt_y": 0.22224327495413312, "amcl_x": 1.0833527992564969, "amcl_y": 0.622398053103083, "error_m": 0.5554383179097235}
{"event": "DRIVE_PROGRESS", "elapsed_s": 5.0, "gt_x": 0.8487255715625986, "gt_y": 0.3492266905415439, "amcl_x": 1.1606941671644286, "amcl_y": 0.6956338558221882, "error_m": 0.4661784302169607}
{"event": "MOTION_STOPPED_WAITING_SETTLE"}
{"event": "FINAL_AMCL_EVALUATION", "ground_truth_x": 1.0477045529088194, "ground_truth_y": 0.5993716505697564, "ground_truth_yaw": 0.9531407429730149, "amcl_x": 1.320718516910749, "amcl_y": 0.8942906494437397, "amcl_yaw": 1.0152029301912475, "initial_error_m": 0.5830951846055813, "final_error_m": 0.4018878455948618, "error_reduction_m": 0.1812073390107195, "tolerance_m": 0.4, "passed": false, "initial_map_to_odom": [0.49999999999999994, 0.30000000000000054, 0.0], "final_map_to_odom": [0.3937131694429892, 0.2801956346992138, 0.0]}
{"event": "FAIL", "error": "AMCL failed to converge within tolerance: final error 0.4019m exceeds 0.4000m", "error_type": "ValueError"}
```

---

## 6. Koşu 2 Sonrası Temizlik

```sh
env DDS_TEST_PAYLOAD=amcl-cleanup docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-amcl-test.yml down -v --remove-orphans
```

Çıkış kodu: 0
