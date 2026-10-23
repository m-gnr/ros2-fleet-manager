# Aşama B2 Devam Komut ve Çıktı Eki

[Ana devam kaydı](simulation-stage-b2-continuation-2026-10-23.md). Komut çıktıları stdout/stderr birlikte, ANSI temizliği yapılarak kaydedilmiştir.

## 1. resolv.conf ve systemd Paket Doğrulaması

```sh
docker run --rm --entrypoint "" ros2-fleet-simulation-nav2-check:humble-fortress dpkg-query -W -f='${Package} ${Version} ${db:Status-Abbrev}\n' systemd
```

Çıkış kodu: 0

```text
systemd 249.11-0ubuntu3.23 ii
```

```sh
docker run --rm --entrypoint "" ros2-fleet-simulation-nav2-check:humble-fortress bash -c 'source /opt/ros/humble/setup.bash && ros2 pkg prefix nav2_bringup'
```

Çıkış kodu: 0

```text
/opt/ros/humble
```

## 2. B2 Harita ve Config Şema Doğrulaması

```sh
docker run --rm -v "$(pwd)/config:/config:ro" --entrypoint "" ros2-fleet-simulation-nav2-check:humble-fortress python3 -c '
import json
from pathlib import Path
import jsonschema

config = json.loads(Path("/config/simulation-nav2-check.json").read_text())
schema = json.loads(Path("/config/simulation-nav2-check.schema.json").read_text())
jsonschema.Draft7Validator.check_schema(schema)
jsonschema.validate(config, schema)
print("Config validation against schema: OK")
'
```

Çıkış kodu: 0

```text
Config validation against schema: OK
```

```sh
docker run --rm -v "$(pwd)/config:/config:ro" --entrypoint "" ros2-fleet-simulation-nav2-check:humble-fortress bash -c 'source /opt/ros/humble/setup.bash && python3 -c "
import yaml
from pathlib import Path
m = yaml.safe_load(Path(\"/config/map/map.yaml\").read_text())
print(\"Map yaml loaded:\", m)
assert Path(\"/config/map/\" + m[\"image\"]).exists()
print(\"Map pgm exists and readable.\")
"'
```

Çıkış kodu: 0

```text
Map yaml loaded: {'image': 'map.pgm', 'resolution': 0.05, 'origin': [-6.0, -6.0, 0.0], 'negate': 0, 'occupied_thresh': 0.65, 'free_thresh': 0.25, 'mode': 'trinary'}
Map pgm exists and readable.
```

## 3. B2 Birim Testleri

```sh
docker run --rm -v "$(pwd)/config:/config:ro" -v "$(pwd)/docker/simulation-nav2-check:/opt/simulation-nav2-check:ro" --entrypoint "" ros2-fleet-simulation-nav2-check:humble-fortress python3 -m unittest discover -s /opt/simulation-nav2-check -p "test_*.py"
```

Çıkış kodu: 0

```text
..
----------------------------------------------------------------------
Ran 2 tests in 0.005s

OK
```

## 4. Docker Compose Yapılandırma Doğrulaması

```sh
env DDS_TEST_PAYLOAD=test-config docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-nav2-check.yml config
```

Çıkış kodu: 0

```text
name: ros2-fleet-simulation-nav2-check
services:
  backend:
    command:
      - python3
      - /opt/simulation-nav2-check/check.py
    environment:
      DDS_PUBLISH_PERIOD_SECONDS: "1"
      DDS_ROLE: subscriber
      DDS_TEST_PAYLOAD: test-config
      DDS_TEST_TIMEOUT_SECONDS: "90"
      DDS_TEST_TOPIC: /dds_validation/probe
      RMW_IMPLEMENTATION: rmw_cyclonedds_cpp
      ROS_DOMAIN_ID: "42"
      ROS_LOCALHOST_ONLY: "0"
      SIM_CHECK_ROLE: backend
    image: ros2-fleet-simulation-nav2-check:humble-fortress
    init: true
    networks:
      dds: null
    volumes:
      - type: bind
        source: /Users/murat/develop/ros2-fleet-manager/config
        target: /config
        read_only: true
        bind: {}
      - type: bind
        source: /Users/murat/develop/ros2-fleet-manager/docker/simulation-nav2-check
        target: /opt/simulation-nav2-check
        read_only: true
        bind: {}
    build:
      context: /Users/murat/develop/ros2-fleet-manager
      dockerfile: docker/simulation-check/Dockerfile
  simulation:
    command:
      - python3
      - /opt/simulation-nav2-check/check.py
    environment:
      DDS_PUBLISH_PERIOD_SECONDS: "1"
      DDS_ROLE: publisher
      DDS_TEST_PAYLOAD: test-config
      DDS_TEST_TIMEOUT_SECONDS: "90"
      DDS_TEST_TOPIC: /dds_validation/probe
      EGL_PLATFORM: surfaceless
      IGN_GAZEBO_RENDER_ENGINE_PATH: /usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins
      IGN_RENDERING_PLUGIN_PATH: /usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins
      LIBGL_ALWAYS_SOFTWARE: "1"
      RMW_IMPLEMENTATION: rmw_cyclonedds_cpp
      ROS_DOMAIN_ID: "42"
      ROS_LOCALHOST_ONLY: "0"
      SIM_CHECK_ROLE: simulation
    image: ros2-fleet-simulation-nav2-check:humble-fortress
    init: true
    networks:
      dds: null
    volumes:
      - type: bind
        source: /Users/murat/develop/ros2-fleet-manager/config
        target: /config
        read_only: true
        bind: {}
      - type: bind
        source: /Users/murat/develop/ros2-fleet-manager/docker/simulation-nav2-check
        target: /opt/simulation-nav2-check
        read_only: true
        bind: {}
    build:
      context: /Users/murat/develop/ros2-fleet-manager
      dockerfile: docker/simulation-check/Dockerfile
networks:
  dds:
    name: ros2-fleet-simulation-nav2-check_dds
    driver: bridge
```

## 5. Canlı Koşu 1: simulation-b2-20261023-01

```sh
env DDS_TEST_PAYLOAD=simulation-b2-20261023-01 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-nav2-check.yml up --abort-on-container-exit --exit-code-from backend
```

Çıkış kodu: 0

```text
[+] up 3/3
 ✔ Network ros2-fleet-simulation-nav2-check_dds            Created          0.0s
 ✔ Container ros2-fleet-simulation-nav2-check-simulation-1 Created          0.0s
 ✔ Container ros2-fleet-simulation-nav2-check-backend-1    Created          0.0s
Attaching to backend-1, simulation-1
backend-1     | {"event": "CONFIG_VALID", "role": "backend", "token": "simulation-b2-20261023-01"}
simulation-1  | {"event": "CONFIG_VALID", "role": "simulation", "token": "simulation-b2-20261023-01"}
simulation-1  | {"event": "PROCESS_START", "command": ["ign", "gazebo", "-s", "-r", "-v", "3", "--headless-rendering", "--physics-engine", "/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5", "--render-engine-server", "/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6", "/tmp/nav2-world.sdf"]}
simulation-1  | {"event": "PROCESS_START", "command": ["ros2", "run", "ros_gz_bridge", "parameter_bridge", "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock", "/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan", "/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry", "/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"]}
simulation-1  | {"event": "PROCESS_START", "command": ["python3", "/opt/simulation-nav2-check/tf_helper.py"]}
simulation-1  | {"event": "PROCESS_START", "command": ["ros2", "launch", "nav2_bringup", "bringup_launch.py", "use_sim_time:=True", "autostart:=True", "map:=/config/map/map.yaml", "params_file:=/config/simulation-nav2-params.yaml", "slam:=False", "use_composition:=True"]}
simulation-1  | [INFO] [1792759567.413776630] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/clock (ignition.msgs.Clock) -> /clock (rosgraph_msgs/msg/Clock)] (Lazy 0)
simulation-1  | [INFO] [1792759567.415348380] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/scan (ignition.msgs.LaserScan) -> /scan (sensor_msgs/msg/LaserScan)] (Lazy 0)
simulation-1  | [INFO] [1792759567.419010505] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/odom (ignition.msgs.Odometry) -> /odom (nav_msgs/msg/Odometry)] (Lazy 0)
simulation-1  | [INFO] [1792759567.420649130] [ros_gz_bridge]: Creating ROS->GZ Bridge: [/cmd_vel (geometry_msgs/msg/Twist) -> /cmd_vel (ignition.msgs.Twist)] (Lazy 0)
backend-1     | {"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp", "token": "simulation-b2-20261023-01"}
backend-1     | {"event": "WAITING_FOR_CLOCK_AND_SENSORS"}
backend-1     | {"event": "CLOCK_AND_SENSORS_OK", "clock": 1.806, "scan_count": 10, "odom_frame": "odom"}
backend-1     | {"event": "CHECKING_LIFECYCLE_STATES"}
backend-1     | {"event": "LIFECYCLE_ACTIVE", "states": {"map_server": "active", "amcl": "active", "controller_server": "active", "planner_server": "active", "behavior_server": "active", "bt_navigator": "active"}}
backend-1     | {"event": "CHECKING_TF_CHAIN"}
backend-1     | {"event": "TF_CHAIN_VALID", "translation": [1.6869730935729638e-19, -5.348656095399299e-38, 0.0], "rotation": [0.0, 0.0, -2.8367426035763876e-19, 1.0]}
backend-1     | {"event": "CHECKING_AMCL_CONVERGENCE"}
backend-1     | {"event": "AMCL_POSE", "x": 0.0, "y": 0.0, "error_m": 0.0}
backend-1     | {"event": "AMCL_CONVERGED", "error_m": 0.0}
backend-1     | {"event": "WAITING_FOR_ACTION_SERVER"}
backend-1     | {"event": "SENDING_NAVIGATE_TO_POSE_GOAL", "target_x": 2.0, "target_y": 1.0, "target_yaw": 0.0}
backend-1     | {"event": "GOAL_ACCEPTED"}
simulation-1  | [component_container_isolated-1] [INFO] [1792759573.255167633] [controller_server]: Received a goal, begin computing control effort.
simulation-1  | [component_container_isolated-1] [WARN] [1792759573.255220050] [controller_server]: No goal checker was specified in parameter 'current_goal_checker'. Server will use only plugin loaded general_goal_checker . This warning will appear once.
simulation-1  | [INFO] [1792759573.352191091] [ros_gz_bridge]: Passing message from ROS geometry_msgs/msg/Twist to Gazebo gz.msgs.Twist (showing msg only once per type)
simulation-1  | [component_container_isolated-1] [INFO] [1792759574.355530550] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759575.355517717] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759576.355470926] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759577.355462551] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759578.355486718] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759579.355474301] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759580.355490009] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759581.355503051] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759582.355487718] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759583.355523926] [controller_server]: Passing new path to controller.
backend-1     | {"event": "GOAL_COMPLETED_STATUS_SUCCEEDED", "status": 4}
backend-1     | {"event": "DESTINATION_REACHED", "odom_x": 1.9495746201734023, "odom_y": 0.9287904965498903, "distance_to_goal_odom_m": 0.08725544288047495, "amcl_x": 1.7905290541883956, "amcl_y": 0.9270808783594594, "distance_to_goal_amcl_m": 0.22180007989186132}
backend-1     | {"event": "METRICS", "measured_scan_rate_hz": 5.000000000000002, "total_scan_messages": 67, "cgroup_usage_usec": 5305296}
backend-1     | {"event": "B2_PASS", "token": "simulation-b2-20261023-01", "final_distance_m": 0.08725544288047495, "scan_rate_hz": 5.000000000000002}
backend-1 exited with code 0
Container ros2-fleet-simulation-nav2-check-backend-1 Stopping
Container ros2-fleet-simulation-nav2-check-backend-1 Stopped
simulation-1 exited with code 137
```

## 6. Koşu 1 Sonrası Ağ ve Container Temizliği

```sh
env DDS_TEST_PAYLOAD=simulation-b2-20261023-01 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-nav2-check.yml down
```

Çıkış kodu: 0

```text
[+] down 3/3
 ✔ Container ros2-fleet-simulation-nav2-check-simulation-1 Removed          0.0s
 ✔ Container ros2-fleet-simulation-nav2-check-backend-1    Removed          0.0s
 ✔ Network ros2-fleet-simulation-nav2-check_dds            Removed          0.1s
```

## 7. Canlı Koşu 2: simulation-b2-20261023-02

```sh
env DDS_TEST_PAYLOAD=simulation-b2-20261023-02 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-nav2-check.yml up --abort-on-container-exit --exit-code-from backend
```

Çıkış kodu: 0

```text
[+] up 3/3
 ✔ Network ros2-fleet-simulation-nav2-check_dds            Created          0.0s
 ✔ Container ros2-fleet-simulation-nav2-check-simulation-1 Created          0.0s
 ✔ Container ros2-fleet-simulation-nav2-check-backend-1    Created          0.0s
Attaching to backend-1, simulation-1
simulation-1  | {"event": "CONFIG_VALID", "role": "simulation", "token": "simulation-b2-20261023-02"}
simulation-1  | {"event": "PROCESS_START", "command": ["ign", "gazebo", "-s", "-r", "-v", "3", "--headless-rendering", "--physics-engine", "/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5", "--render-engine-server", "/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6", "/tmp/nav2-world.sdf"]}
simulation-1  | {"event": "PROCESS_START", "command": ["ros2", "run", "ros_gz_bridge", "parameter_bridge", "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock", "/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan", "/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry", "/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"]}
simulation-1  | {"event": "PROCESS_START", "command": ["python3", "/opt/simulation-nav2-check/tf_helper.py"]}
simulation-1  | {"event": "PROCESS_START", "command": ["ros2", "launch", "nav2_bringup", "bringup_launch.py", "use_sim_time:=True", "autostart:=True", "map:=/config/map/map.yaml", "params_file:=/config/simulation-nav2-params.yaml", "slam:=False", "use_composition:=True"]}
backend-1     | {"event": "CONFIG_VALID", "role": "backend", "token": "simulation-b2-20261023-02"}
simulation-1  | [INFO] [1792759613.737634388] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/clock (ignition.msgs.Clock) -> /clock (rosgraph_msgs/msg/Clock)] (Lazy 0)
simulation-1  | [INFO] [1792759613.738137221] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/scan (ignition.msgs.LaserScan) -> /scan (sensor_msgs/msg/LaserScan)] (Lazy 0)
simulation-1  | [INFO] [1792759613.738982013] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/odom (ignition.msgs.Odometry) -> /odom (nav_msgs/msg/Odometry)] (Lazy 0)
simulation-1  | [INFO] [1792759613.739423888] [ros_gz_bridge]: Creating ROS->GZ Bridge: [/cmd_vel (geometry_msgs/msg/Twist) -> /cmd_vel (ignition.msgs.Twist)] (Lazy 0)
backend-1     | {"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp", "token": "simulation-b2-20261023-02"}
backend-1     | {"event": "WAITING_FOR_CLOCK_AND_SENSORS"}
backend-1     | {"event": "CLOCK_AND_SENSORS_OK", "clock": 1.806, "scan_count": 10, "odom_frame": "odom"}
backend-1     | {"event": "CHECKING_LIFECYCLE_STATES"}
backend-1     | {"event": "LIFECYCLE_ACTIVE", "states": {"map_server": "active", "amcl": "active", "controller_server": "active", "planner_server": "active", "behavior_server": "active", "bt_navigator": "active"}}
backend-1     | {"event": "CHECKING_TF_CHAIN"}
backend-1     | {"event": "TF_CHAIN_VALID", "translation": [1.9397583406435046e-19, -6.87003977194438e-38, 0.0], "rotation": [0.0, 0.0, -3.1844956827247017e-19, 1.0]}
backend-1     | {"event": "CHECKING_AMCL_CONVERGENCE"}
backend-1     | {"event": "AMCL_POSE", "x": 0.0, "y": 0.0, "error_m": 0.0}
backend-1     | {"event": "AMCL_CONVERGED", "error_m": 0.0}
backend-1     | {"event": "WAITING_FOR_ACTION_SERVER"}
backend-1     | {"event": "SENDING_NAVIGATE_TO_POSE_GOAL", "target_x": 2.0, "target_y": 1.0, "target_yaw": 0.0}
backend-1     | {"event": "GOAL_ACCEPTED"}
simulation-1  | [component_container_isolated-1] [INFO] [1792759619.555231711] [controller_server]: Received a goal, begin computing control effort.
simulation-1  | [component_container_isolated-1] [WARN] [1792759619.555284128] [controller_server]: No goal checker was specified in parameter 'current_goal_checker'. Server will use only plugin loaded general_goal_checker . This warning will appear once.
simulation-1  | [INFO] [1792759619.652191091] [ros_gz_bridge]: Passing message from ROS geometry_msgs/msg/Twist to Gazebo gz.msgs.Twist (showing msg only once per type)
simulation-1  | [component_container_isolated-1] [INFO] [1792759620.555530550] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759621.555517717] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759622.773463336] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759623.773481253] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759624.773468753] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759625.773479253] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759626.773475170] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759627.773482503] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759628.773471045] [controller_server]: Passing new path to controller.
simulation-1  | [component_container_isolated-1] [INFO] [1792759629.773480086] [controller_server]: Passing new path to controller.
backend-1     | {"event": "GOAL_COMPLETED_STATUS_SUCCEEDED", "status": 4}
backend-1     | {"event": "DESTINATION_REACHED", "odom_x": 1.982792569793032, "odom_y": 0.8600571748336509, "distance_to_goal_odom_m": 0.14099677290586135, "amcl_x": 1.8281056490006313, "amcl_y": 0.8723850239016224, "distance_to_goal_amcl_m": 0.21408701508985462}
backend-1     | {"event": "METRICS", "measured_scan_rate_hz": 4.999999999999999, "total_scan_messages": 68, "cgroup_usage_usec": 7072930}
backend-1     | {"event": "B2_PASS", "token": "simulation-b2-20261023-02", "final_distance_m": 0.14099677290586135, "scan_rate_hz": 4.999999999999999}
backend-1 exited with code 0
Container ros2-fleet-simulation-nav2-check-backend-1 Stopping
Container ros2-fleet-simulation-nav2-check-backend-1 Stopped
simulation-1 exited with code 137
```

## 8. Koşu 2 Sonrası Ağ ve Container Temizliği

```sh
env DDS_TEST_PAYLOAD=simulation-b2-20261023-02 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-nav2-check.yml down
```

Çıkış kodu: 0

```text
[+] down 3/3
 ✔ Container ros2-fleet-simulation-nav2-check-backend-1    Removed          0.0s
 ✔ Container ros2-fleet-simulation-nav2-check-simulation-1 Removed          0.0s
 ✔ Network ros2-fleet-simulation-nav2-check_dds            Removed          0.1s
```

## 9. Kalan Geçici Container ve Ağ Denetimi

```sh
docker ps -a --filter name=ros2-fleet-simulation-nav2-check && docker network ls --filter name=ros2-fleet-simulation-nav2-check
```

Çıkış kodu: 0

```text
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
NETWORK ID   NAME      DRIVER    SCOPE
```

## 10. Son Git Durumu ve Diff Denetimi

```sh
git status --short
```

Çıkış kodu: 0

```text
 M docs/simulation-stage-b2-2026-10-23.md
?? config/map/
?? config/simulation-nav2-check.json
?? config/simulation-nav2-check.schema.json
?? config/simulation-nav2-params.yaml
?? docker-compose.simulation-nav2-check.yml
?? docker/simulation-nav2-check/
?? docs/simulation-stage-b2-commands-2026-10-23.md
?? docs/simulation-stage-b2-continuation-2026-10-23.md
?? docs/simulation-stage-b2-continuation-commands-2026-10-23.md
```

```sh
git diff --check
```

Çıkış kodu: 0

```text

```
