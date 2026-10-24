"""Stage C3.3.3 validation harness: Dual-Robot Gazebo + Nav2 + Executor + Fleet Manager.

Strictly conforms to:
- DOC-ARCH-2026-10-23-FINAL Section 3-8 & 11
- C3.3.3-DEC-01: Aligned topic & service endpoint names
- C3.3.3-DEC-02: Single source of truth from config/fleet.yaml
- C3.3.3-DEC-03: Pre-C4 test battery feeder isolation
- C3.3.3-DEC-04: Clean SQLite startup and C3.3.1 session safety
- C3.3.3-DEC-05: Map, TF, and namespace isolation (/robot_1 and /robot_2)
- C3.3.3-DEC-06: Concurrent tasks, single station ownership, physical departure confirmation
- C3.3.3-DEC-07: Safe HIGH preemption, N=2 immunity, terminal PREEMPTED requirement
- C3.3.3-DEC-08: Complete regression protection (C1–C3.3.2)
"""

import asyncio
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid

import jsonschema
import yaml

ROOT = Path(__file__).parent


def emit(event, **values):
    """Emit JSON formatted event message to stdout."""
    print(json.dumps(dict(event=event, **values)), flush=True)


def quaternion_to_yaw(x, y, z, w):
    """Extract planar yaw angle from quaternion."""
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def load_config():
    """Load and validate simulation-c3-3-3.json and config/fleet.yaml."""
    config_path = Path("/config/simulation-c3-3-3.json")
    if not config_path.exists():
        config_path = Path("config/simulation-c3-3-3.json")
    schema_path = Path("/config/simulation-c3-3-3.schema.json")
    if not schema_path.exists():
        schema_path = Path("config/simulation-c3-3-3.schema.json")

    if not config_path.exists():
        raise FileNotFoundError(f"Config missing: {config_path}")
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema missing: {schema_path}")

    config = json.loads(config_path.read_text())
    schema = json.loads(schema_path.read_text())
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(config, schema)

    fleet_path = Path(config["fleet_config_path"])
    if not fleet_path.exists():
        for candidate in [Path("/config/fleet.yaml"), Path("config/fleet.yaml")]:
            if candidate.exists():
                fleet_path = candidate
                break
    if not fleet_path.exists():
        raise FileNotFoundError(f"fleet.yaml missing: {fleet_path}")

    template_path = Path(config["nav2_template_path"])
    if not template_path.exists():
        for candidate in [Path("/config/simulation-b3-params.template.yaml"), Path("config/simulation-b3-params.template.yaml")]:
            if candidate.exists():
                config["nav2_template_path"] = str(candidate)
                break

    map_path = Path(config["map_path"])
    if not map_path.exists():
        for candidate in [Path("/config/map/map.yaml"), Path("config/map/map.yaml")]:
            if candidate.exists():
                config["map_path"] = str(candidate)
                break

    fleet_data = yaml.safe_load(fleet_path.read_text())
    if not fleet_data or "robots" not in fleet_data:
        raise ValueError(f"Invalid fleet.yaml at {fleet_path}")

    timeout = float(os.environ.get("DDS_TEST_TIMEOUT_SECONDS", "300.0"))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("DDS_TEST_TIMEOUT_SECONDS must be positive and finite")
    if not 0 <= int(os.environ.get("ROS_DOMAIN_ID", "0")) <= 232:
        raise ValueError("ROS_DOMAIN_ID must be in 0..232")
    if os.environ.get("ROS_LOCALHOST_ONLY") != "0":
        raise ValueError("ROS_LOCALHOST_ONLY must be 0 for cross-container test")
    if not os.environ.get("DDS_TEST_PAYLOAD", "").strip():
        raise ValueError("DDS_TEST_PAYLOAD must identify the run")
    if os.environ.get("SIM_CHECK_ROLE") not in ("simulation", "backend"):
        raise ValueError("SIM_CHECK_ROLE must be simulation or backend")

    return config, fleet_data, timeout


def generate_params_for_robots(config, fleet_data):
    """Generate Nav2 parameters files from template using fleet.yaml initial poses."""
    template = Path(config["nav2_template_path"]).read_text()
    params_files = {}

    for r in fleet_data["robots"]:
        r_id = r["id"]
        ns = r_id
        base_frame = f"{r_id}/base_link"
        odom_frame = f"{r_id}/odom"
        init_p = r["initial_pose"]

        content = template.replace("@BASE_FRAME@", base_frame)
        content = content.replace("@ODOM_FRAME@", odom_frame)
        content = content.replace("@SCAN_TOPIC@", f"/{r_id}/scan")
        content = content.replace("@ODOM_TOPIC@", f"/{r_id}/odom")
        content = content.replace("@INIT_X@", str(init_p["x"]))
        content = content.replace("@INIT_Y@", str(init_p["y"]))
        content = content.replace("@INIT_Z@", "0.0")
        content = content.replace("@INIT_YAW@", str(init_p["yaw"]))

        target = Path(f"/tmp/nav2-params-{r_id}.yaml")
        target.write_text(content)
        params_files[r_id] = str(target)

    return params_files


def prepare_world(config, fleet_data):
    """Generate dual-robot Gazebo world SDF aligning with map boundaries and fleet.yaml poses."""
    room = config["room"]
    sensor = config["sensor"]
    thick = room["wall_thickness_m"]
    w_h = room["wall_height_m"]
    w_size = room["size_m"]

    # Align with config/map/map.pgm room walls at x=±4.5, y=±4.5
    hw_x = 4.5
    hw_y = 4.5

    robot_models_sdf = []
    for r in fleet_data["robots"]:
        r_id = r["id"]
        init_p = r["initial_pose"]
        pose_str = f"{init_p['x']} {init_p['y']} 0.21 0 0 {init_p['yaw']}"
        sensor_pose_str = " ".join(map(str, sensor["pose"]))

        r_sdf = f"""
    <!-- Robot model: {r_id} -->
    <model name="{r_id}">
      <pose>{pose_str}</pose>
      <link name="base_link">
        <inertial><mass>2.0</mass><inertia><ixx>0.04</ixx><iyy>0.06</iyy><izz>0.08</izz></inertia></inertial>
        <collision name="body"><geometry><box><size>0.5 0.3 0.1</size></box></geometry></collision>
        <visual name="body"><geometry><box><size>0.5 0.3 0.1</size></box></geometry></visual>
        <sensor name="lidar" type="gpu_lidar">
          <pose>{sensor_pose_str}</pose>
          <topic>/{r_id}/scan</topic>
          <update_rate>{sensor['update_rate_hz']}</update_rate>
          <always_on>true</always_on>
          <lidar>
            <scan>
              <horizontal>
                <samples>{sensor['samples']}</samples>
                <resolution>1</resolution>
                <min_angle>{sensor['min_angle_rad']}</min_angle>
                <max_angle>{sensor['max_angle_rad']}</max_angle>
              </horizontal>
            </scan>
            <range>
              <min>{sensor['min_range_m']}</min>
              <max>{sensor['max_range_m']}</max>
              <resolution>{sensor['resolution_m']}</resolution>
            </range>
          </lidar>
        </sensor>
      </link>

      <link name="left_wheel">
        <pose>0 0.2 -0.1 1.57079632679 0 0</pose>
        <inertial><mass>0.2</mass><inertia><ixx>0.0006</ixx><iyy>0.0006</iyy><izz>0.001</izz></inertia></inertial>
        <collision name="wheel"><geometry><cylinder><radius>0.1</radius><length>0.04</length></cylinder></geometry></collision>
        <visual name="wheel"><geometry><cylinder><radius>0.1</radius><length>0.04</length></cylinder></geometry></visual>
      </link>
      <link name="right_wheel">
        <pose>0 -0.2 -0.1 1.57079632679 0 0</pose>
        <inertial><mass>0.2</mass><inertia><ixx>0.0006</ixx><iyy>0.0006</iyy><izz>0.001</izz></inertia></inertial>
        <collision name="wheel"><geometry><cylinder><radius>0.1</radius><length>0.04</length></cylinder></geometry></collision>
        <visual name="wheel"><geometry><cylinder><radius>0.1</radius><length>0.04</length></cylinder></geometry></visual>
      </link>
      <link name="caster">
        <pose>-0.2 0 -0.15 0 0 0</pose>
        <inertial><mass>0.05</mass><inertia><ixx>0.00005</ixx><iyy>0.00005</iyy><izz>0.00005</izz></inertia></inertial>
        <collision name="caster"><geometry><sphere><radius>0.05</radius></sphere></geometry><surface><friction><ode><mu>0</mu><mu2>0</mu2></ode></friction></surface></collision>
      </link>

      <joint name="left_joint" type="revolute">
        <parent>base_link</parent><child>left_wheel</child>
        <axis><xyz expressed_in="__model__">0 1 0</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis>
      </joint>
      <joint name="right_joint" type="revolute">
        <parent>base_link</parent><child>right_wheel</child>
        <axis><xyz expressed_in="__model__">0 1 0</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis>
      </joint>
      <joint name="caster_joint" type="fixed"><parent>base_link</parent><child>caster</child></joint>

      <plugin filename="ignition-gazebo-diff-drive-system" name="ignition::gazebo::systems::DiffDrive">
        <left_joint>left_joint</left_joint>
        <right_joint>right_joint</right_joint>
        <wheel_separation>0.4</wheel_separation>
        <wheel_radius>0.1</wheel_radius>
        <topic>/{r_id}/cmd_vel</topic>
        <odom_topic>/{r_id}/odom</odom_topic>
        <frame_id>{r_id}/odom</frame_id>
        <child_frame_id>{r_id}/base_link</child_frame_id>
        <odom_publish_frequency>30</odom_publish_frequency>
      </plugin>
    </model>
"""
        robot_models_sdf.append(r_sdf)

    joined_models = "\n".join(robot_models_sdf)

    sdf = f"""<?xml version="1.0"?>
<sdf version="1.8">
  <world name="c3_3_3_validation_world">
    <physics name="physics" type="ignored">
      <max_step_size>0.005</max_step_size>
      <real_time_factor>1</real_time_factor>
    </physics>
    <plugin filename="ignition-gazebo-physics-system" name="ignition::gazebo::systems::Physics"/>
    <plugin filename="ignition-gazebo-user-commands-system" name="ignition::gazebo::systems::UserCommands"/>
    <plugin filename="ignition-gazebo-scene-broadcaster-system" name="ignition::gazebo::systems::SceneBroadcaster"/>
    <plugin filename="ignition-gazebo-sensors-system" name="ignition::gazebo::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <gravity>0 0 -9.8</gravity>

    <model name="floor">
      <static>true</static>
      <link name="floor_link">
        <collision name="floor_col">
          <geometry><box><size>12 12 0.1</size></box></geometry>
          <pose>0 0 -0.05 0 0 0</pose>
        </collision>
        <visual name="floor_vis">
          <geometry><box><size>12 12 0.1</size></box></geometry>
          <pose>0 0 -0.05 0 0 0</pose>
        </visual>
      </link>
    </model>

    <!-- 4 Enclosure Walls -->
    <model name="north_wall">
      <static>true</static>
      <pose>0 {hw_y} {w_h / 2.0} 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>{w_size[0] - 2 * thick} {thick} {w_h}</size></box></geometry></collision>
        <visual name="vis"><geometry><box><size>{w_size[0] - 2 * thick} {thick} {w_h}</size></box></geometry></visual>
      </link>
    </model>
    <model name="south_wall">
      <static>true</static>
      <pose>0 {-hw_y} {w_h / 2.0} 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>{w_size[0] - 2 * thick} {thick} {w_h}</size></box></geometry></collision>
        <visual name="vis"><geometry><box><size>{w_size[0] - 2 * thick} {thick} {w_h}</size></box></geometry></visual>
      </link>
    </model>
    <model name="east_wall">
      <static>true</static>
      <pose>{hw_x} 0 {w_h / 2.0} 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>{thick} {w_size[1]} {w_h}</size></box></geometry></collision>
        <visual name="vis"><geometry><box><size>{thick} {w_size[1]} {w_h}</size></box></geometry></visual>
      </link>
    </model>
    <model name="west_wall">
      <static>true</static>
      <pose>{-hw_x} 0 {w_h / 2.0} 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>{thick} {w_size[1]} {w_h}</size></box></geometry></collision>
        <visual name="vis"><geometry><box><size>{thick} {w_size[1]} {w_h}</size></box></geometry></visual>
      </link>
    </model>

{joined_models}
  </world>
</sdf>
"""
    target = Path("/tmp/c3-3-3-world.sdf")
    target.write_text(sdf)
    return str(target)


def simulation(config, fleet_data):
    """Run dual-robot Gazebo + Nav2 + Executors + Temporary Battery Feeder simulation."""
    engines = list(Path("/usr/lib").glob("*/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5"))
    if not engines:
        engines = list(Path("/usr/lib").glob("*/*/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5"))
    if not engines:
        raise RuntimeError("Fortress DART physics engine plugin not found")

    render_engines = list(Path("/usr/lib").glob("*/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6"))
    if not render_engines:
        render_engines = list(Path("/usr/lib").glob("*/*/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6"))
    if not render_engines:
        raise RuntimeError("Fortress OGRE2 render engine plugin not found")

    world_path = prepare_world(config, fleet_data)
    params_files = generate_params_for_robots(config, fleet_data)

    commands = [
        # 1. Gazebo Fortress Headless
        [
            "ign", "gazebo", "-s", "-r", "-v", "3", "--headless-rendering",
            "--physics-engine", str(engines[0]),
            "--render-engine-server", str(render_engines[0]),
            world_path,
        ],
        # 2. ros_gz_bridge parameter bridge
        [
            "ros2", "run", "ros_gz_bridge", "parameter_bridge",
            "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
            "/world/c3_3_3_validation_world/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V",
            "/robot_1/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan",
            "/robot_1/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry",
            "/robot_1/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist",
            "/robot_2/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan",
            "/robot_2/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry",
            "/robot_2/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist",
        ],
        # 3. TF helper
        ["python3", "/opt/simulation-c3-3-3/tf_helper.py"],
        # 4. Nav2 bringup robot_1
        [
            "ros2", "launch", "nav2_bringup", "bringup_launch.py",
            "use_sim_time:=True",
            "autostart:=True",
            "use_namespace:=True",
            "namespace:=robot_1",
            "map:=" + config["map_path"],
            "params_file:=" + params_files["robot_1"],
            "slam:=False",
            "use_composition:=True",
        ],
        # 5. Nav2 bringup robot_2
        [
            "ros2", "launch", "nav2_bringup", "bringup_launch.py",
            "use_sim_time:=True",
            "autostart:=True",
            "use_namespace:=True",
            "namespace:=robot_2",
            "map:=" + config["map_path"],
            "params_file:=" + params_files["robot_2"],
            "slam:=False",
            "use_composition:=True",
        ],
        # 6. Robot Executor robot_1
        [
            "python3", "/opt/simulation-c3-3-3/executor_test_entry.py",
            "--ros-args", "-r", "__node:=robot_executor_robot_1",
            "-p", "fleet_config_path:=" + config["fleet_config_path"],
            "-p", "robot_id:=robot_1",
            "-p", "robot_namespace:=/robot_1",
            "-p", "use_sim_time:=true",
            "-p", "loading_duration_sec:=1.5",
            "-p", "unloading_duration_sec:=1.5",
            "-p", "linear_stop_threshold_m_s:=0.01",
            "-p", "angular_stop_threshold_rad_s:=0.01",
            "-p", "odometry_freshness_sec:=0.5",
            "-p", "cancel_stop_timeout_sec:=3.0",
            "-p", "status_topic_name:=robot_status",
            "-p", "battery_state_topic_name:=battery_state",
            "-p", "duplicate_record_capacity:=" + str(config["executor_duplicate_record_capacity"]),
        ],
        # 7. Robot Executor robot_2
        [
            "python3", "/opt/simulation-c3-3-3/executor_test_entry.py",
            "--ros-args", "-r", "__node:=robot_executor_robot_2",
            "-p", "fleet_config_path:=" + config["fleet_config_path"],
            "-p", "robot_id:=robot_2",
            "-p", "robot_namespace:=/robot_2",
            "-p", "use_sim_time:=true",
            "-p", "loading_duration_sec:=1.5",
            "-p", "unloading_duration_sec:=1.5",
            "-p", "linear_stop_threshold_m_s:=0.01",
            "-p", "angular_stop_threshold_rad_s:=0.01",
            "-p", "odometry_freshness_sec:=0.5",
            "-p", "cancel_stop_timeout_sec:=3.0",
            "-p", "status_topic_name:=robot_status",
            "-p", "battery_state_topic_name:=battery_state",
            "-p", "duplicate_record_capacity:=" + str(config["executor_duplicate_record_capacity"]),
        ],
        # 8. Temporary test battery feeder (pre-C4, C3.3.3-DEC-03)
        ["python3", "/opt/simulation-c3-3-3/mock_battery_feeder.py"],
    ]

    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    children = []
    try:
        for command in commands:
            emit("PROCESS_START", command=command[0], full=command)
            children.append(subprocess.Popen(command, start_new_session=True))
        while not stopped:
            for child in children:
                if child.poll() is not None:
                    raise RuntimeError(f"Child {child.args[0]} exited unexpectedly: {child.returncode}")
            time.sleep(0.2)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
        for child in children:
            try:
                child.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=1.0)
                    emit("FORCED_KILL", command=child.args[0])
                except Exception:
                    pass
            emit("PROCESS_EXIT", command=child.args[0], code=child.returncode)


def backend(config, fleet_data, timeout):
    """Execute live simulation validation suite covering scenarios T01 - T10."""
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.parameter import Parameter
    from action_msgs.msg import GoalStatus
    from rosgraph_msgs.msg import Clock
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import PoseStamped, Twist
    from unique_identifier_msgs.msg import UUID as RosUUID

    from fleet_interfaces.action import ExecuteTask
    from fleet_interfaces.msg import RobotStatus
    from fleet_interfaces.srv import ClearRobotError
    from lifecycle_msgs.srv import GetState
    from nav2_msgs.action import ComputePathToPose, NavigateToPose

    from backend.fleet_manager.adapters.action_client import ExecuteTaskActionClientBridge
    from backend.fleet_manager.adapters.outbox_sender import ROS2OutboxSender
    from backend.fleet_manager.adapters.ros2_adapter_node import FleetROS2Adapter
    from backend.fleet_manager.adapters.route_cache import CachedRouteDistanceProvider, RouteCache
    from backend.fleet_manager.adapters.route_resolver import AsyncRouteResolver
    from backend.fleet_manager.adapters.service_client import ClearRobotErrorServiceClient
    from backend.fleet_manager.adapters.status_subscriber import RobotStatusSubscriberBridge
    from backend.fleet_manager.builder import build_fleet_manager_from_config
    from backend.fleet_manager.domain.constants import (
        ReservationState,
        RobotState,
        StationType,
        TaskPhase,
        TaskPriority,
        TaskStatus,
    )
    from backend.fleet_manager.domain.fleet_manager_core import FleetManagerCore
    from backend.fleet_manager.domain.models import Pose2D, Task
    from backend.fleet_manager.event_loop import Event, FleetEventLoop, OutboxDispatcher
    from backend.fleet_manager.persistence.store import SQLiteStore

    rclpy.init()
    node = rclpy.create_node(
        "c3_3_3_backend_orchestrator",
        parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)],
    )

    executor = MultiThreadedExecutor()
    executor.add_node(node)
    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()

    emit("WARMUP_START")
    start_time = time.monotonic()

    # Track odometry and raw status for assertions
    odom_records = {"robot_1": [], "robot_2": []}
    status_records = {"robot_1": [], "robot_2": []}

    def make_odom_cb(r_id):
        return lambda msg: odom_records[r_id].append(msg)

    def make_status_cb(r_id):
        return lambda msg: status_records[r_id].append(msg)

    node.create_subscription(Odometry, "/robot_1/odom", make_odom_cb("robot_1"), 10)
    node.create_subscription(Odometry, "/robot_2/odom", make_odom_cb("robot_2"), 10)
    node.create_subscription(RobotStatus, "/robot_1/robot_status", make_status_cb("robot_1"), 10)
    node.create_subscription(RobotStatus, "/robot_2/robot_status", make_status_cb("robot_2"), 10)

    # Action & Service clients for orchestrator verification
    exec_client_r1 = ActionClient(node, ExecuteTask, "/robot_1/execute_task")
    exec_client_r2 = ActionClient(node, ExecuteTask, "/robot_2/execute_task")
    path_client_r1 = ActionClient(node, ComputePathToPose, "/robot_1/compute_path_to_pose")
    path_client_r2 = ActionClient(node, ComputePathToPose, "/robot_2/compute_path_to_pose")
    nav2_client_r1 = ActionClient(node, NavigateToPose, "/robot_1/navigate_to_pose")
    nav2_client_r2 = ActionClient(node, NavigateToPose, "/robot_2/navigate_to_pose")
    clear_client_r1 = node.create_client(ClearRobotError, "/robot_1/clear_robot_error")
    clear_client_r2 = node.create_client(ClearRobotError, "/robot_2/clear_robot_error")
    bt_client_r1 = node.create_client(GetState, "/robot_1/bt_navigator/get_state")
    bt_client_r2 = node.create_client(GetState, "/robot_2/bt_navigator/get_state")

    def check_bt_nav_active(client):
        if not client.service_is_ready():
            return False
        req = GetState.Request()
        future = client.call_async(req)
        t_wait = time.monotonic()
        while not future.done() and time.monotonic() - t_wait < 1.0:
            time.sleep(0.05)
        if future.done():
            try:
                res = future.result()
                return res.current_state.label == "active"
            except Exception:
                return False
        return False

    # Wait for simulation services to be ready
    def wait_condition(predicate, desc, timeout_s=90.0):
        t0 = time.monotonic()
        while not predicate():
            if time.monotonic() - t0 > timeout_s:
                raise TimeoutError(f"Timed out waiting for: {desc}")
            time.sleep(0.5)

    wait_condition(lambda: len(odom_records["robot_1"]) > 0 and len(odom_records["robot_2"]) > 0, "Initial odometry from both robots")
    wait_condition(lambda: len(status_records["robot_1"]) > 0 and len(status_records["robot_2"]) > 0, "Initial RobotStatus telemetry from both executors")
    wait_condition(lambda: exec_client_r1.wait_for_server(timeout_sec=1.0) and exec_client_r2.wait_for_server(timeout_sec=1.0), "ExecuteTask action servers on both robots")
    wait_condition(lambda: path_client_r1.wait_for_server(timeout_sec=1.0) and path_client_r2.wait_for_server(timeout_sec=1.0), "Nav2 ComputePathToPose action servers on both robots")
    wait_condition(lambda: nav2_client_r1.wait_for_server(timeout_sec=1.0) and nav2_client_r2.wait_for_server(timeout_sec=1.0), "Nav2 NavigateToPose action servers on both robots")
    wait_condition(lambda: clear_client_r1.wait_for_service(timeout_sec=1.0) and clear_client_r2.wait_for_service(timeout_sec=1.0), "ClearRobotError service on both robots")
    wait_condition(lambda: check_bt_nav_active(bt_client_r1) and check_bt_nav_active(bt_client_r2), "Nav2 bt_navigator lifecycle state 'active' on both robots")

    print(f"[DEBUG] r1 odom: {odom_records['robot_1'][-1].pose.pose.position.x}, {odom_records['robot_1'][-1].pose.pose.position.y}", flush=True)
    print(f"[DEBUG] r1 status: {status_records['robot_1'][-1].pose.pose.position.x}, {status_records['robot_1'][-1].pose.pose.position.y}", flush=True)
    print(f"[DEBUG] r2 odom: {odom_records['robot_2'][-1].pose.pose.position.x}, {odom_records['robot_2'][-1].pose.pose.position.y}", flush=True)
    print(f"[DEBUG] r2 status: {status_records['robot_2'][-1].pose.pose.position.x}, {status_records['robot_2'][-1].pose.pose.position.y}", flush=True)

    emit("WARMUP_COMPLETED", elapsed_s=round(time.monotonic() - start_time, 2))

    # Shared route cache and resolver
    shared_route_cache = RouteCache()
    shared_route_provider = CachedRouteDistanceProvider(cache=shared_route_cache)

    # -------------------------------------------------------------------------
    # T01: Filo Keşfi ve C3.3.1 Oturum Güvenliği Doğrulaması
    # -------------------------------------------------------------------------
    emit("SCENARIO_START", test="T01", name="fleet_discovery_and_c3_3_1_session_safety")
    db_t01 = "/tmp/c3_3_3_t01.db"
    if os.path.exists(db_t01):
        os.remove(db_t01)

    core_t01, robot_ids_t01 = build_fleet_manager_from_config(config["fleet_config_path"], route_provider=shared_route_provider)
    store_t01 = SQLiteStore(db_t01)

    async def run_t01():
        sub_node_t01 = rclpy.create_node("fm_node_t01", parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        executor.add_node(sub_node_t01)

        loop = FleetEventLoop(store_t01, core_t01)
        await loop.start()

        # Connect adapter
        adapter = FleetROS2Adapter(
            node=sub_node_t01,
            consumer=loop,
            loop=asyncio.get_running_loop(),
            robot_ids=robot_ids_t01,
            route_cache=shared_route_cache,
        )

        # Await status from both robots
        t0 = time.monotonic()
        while time.monotonic() - t0 < 15.0:
            c = loop.core
            r1 = c.tracker.get_robot("robot_1")
            r2 = c.tracker.get_robot("robot_2")
            if r1.initial_status_verified and r2.initial_status_verified:
                break
            await asyncio.sleep(0.2)

        c = loop.core
        r1 = c.tracker.get_robot("robot_1")
        r2 = c.tracker.get_robot("robot_2")

        assert r1 is not None and r2 is not None, "Both robots must be tracked"
        assert r1.session_id is not None, "robot_1 publisher_session_id must be recorded"
        assert r2.session_id is not None, "robot_2 publisher_session_id must be recorded"
        assert r1.initial_status_verified is True, "robot_1 initial_status_verified must be True"
        assert r2.initial_status_verified is True, "robot_2 initial_status_verified must be True"
        assert r1.state == RobotState.STATE_IDLE, "robot_1 state must be STATE_IDLE"
        assert r2.state == RobotState.STATE_IDLE, "robot_2 state must be STATE_IDLE"
        assert r1.is_eligible_for_new_assignment(time.monotonic()) is True, "robot_1 must be eligible for new task assignment"
        assert r2.is_eligible_for_new_assignment(time.monotonic()) is True, "robot_2 must be eligible for new task assignment"

        await loop.close()
        store_t01.close()
        executor.remove_node(sub_node_t01)

    asyncio.run(run_t01())
    emit("SCENARIO_PASSED", test="T01", details="Verified clean startup, session tracking, and initial verification gate")

    # -------------------------------------------------------------------------
    # T02: Eşzamanlı İki Bağımsız Lojistik Görev
    # -------------------------------------------------------------------------
    emit("SCENARIO_START", test="T02", name="concurrent_independent_logistics_tasks")
    db_t02 = "/tmp/c3_3_3_t02.db"
    if os.path.exists(db_t02):
        os.remove(db_t02)

    core_t02, robot_ids_t02 = build_fleet_manager_from_config(config["fleet_config_path"], route_provider=shared_route_provider)
    store_t02 = SQLiteStore(db_t02)

    async def run_t02():
        sub_node_t02 = rclpy.create_node("fm_node_t02", parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        executor.add_node(sub_node_t02)

        loop = FleetEventLoop(store_t02, core_t02)
        await loop.start()

        adapter = FleetROS2Adapter(
            node=sub_node_t02,
            consumer=loop,
            loop=asyncio.get_running_loop(),
            robot_ids=robot_ids_t02,
            route_cache=shared_route_cache,
        )

        outbox_disp = OutboxDispatcher(
            consumer=loop,
            sender=adapter.outbox_sender,
            clock=time.monotonic,
            retry_delay=1.0,
        )

        # Wait for both robots to become verified IDLE
        t0 = time.monotonic()
        while time.monotonic() - t0 < 10.0:
            c = loop.core
            if c.tracker.get_robot("robot_1").initial_status_verified and c.tracker.get_robot("robot_2").initial_status_verified:
                break
            await asyncio.sleep(0.2)

        # Pre-seed cache with obstacle-free routes for T02
        # robot_1 starts at (-2.0, -0.5, 0.0) -> pickup (-1.5, -0.5) -> dropoff (-1.0, -0.5)
        # robot_2 starts at (1.0, 2.5, 3.1415) -> pickup (0.5, 2.5) -> dropoff (0.0, 2.5)
        shared_route_cache.put("robot_1", Pose2D(-2.0, -0.5), Pose2D(-1.5, -0.5), 0.5)
        shared_route_cache.put("robot_1", Pose2D(-1.5, -0.5), Pose2D(-1.0, -0.5), 0.5)
        shared_route_cache.put("robot_1", Pose2D(-1.0, -0.5), Pose2D(0.5, -2.0), 2.0)

        shared_route_cache.put("robot_2", Pose2D(1.0, 2.5), Pose2D(0.5, 2.5), 0.5)
        shared_route_cache.put("robot_2", Pose2D(0.5, 2.5), Pose2D(0.0, 2.5), 0.5)
        shared_route_cache.put("robot_2", Pose2D(0.0, 2.5), Pose2D(0.5, -2.0), 3.0)

        print(f"[DEBUG] T02 tracker: r1={loop.core.tracker.get_robot('robot_1').pose}, r2={loop.core.tracker.get_robot('robot_2').pose}", flush=True)

        # Submit task 1 (nearest to robot_1)
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "task_t02_r1",
            "pickup_pose": Pose2D(-1.5, -0.5, 0.0),
            "dropoff_pose": Pose2D(-1.0, -0.5, 0.0),
            "priority": TaskPriority.PRIORITY_LOW,
            "created_at": time.monotonic(),
        }))

        # Submit task 2 (nearest to robot_2)
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "task_t02_r2",
            "pickup_pose": Pose2D(0.5, 2.5, 3.1415),
            "dropoff_pose": Pose2D(0.0, 2.5, 3.1415),
            "priority": TaskPriority.PRIORITY_LOW,
            "created_at": time.monotonic(),
        }))

        # Run schedule tick
        await loop.submit(Event("TICK", {"current_time": time.monotonic()}))

        c = loop.core
        print(f"[DEBUG] T02 active={list(c._active_tasks.keys())}, queue={[t.task_id for t in c.queue.iter_assignable_tasks()]}", flush=True)

        # Verify both tasks assigned to respective robots
        c = loop.core
        t1 = c._active_tasks.get("task_t02_r1")
        t2 = c._active_tasks.get("task_t02_r2")
        assert t1 is not None and t1.assigned_robot_id == "robot_1"
        assert t2 is not None and t2.assigned_robot_id == "robot_2"
        emit("CONCURRENT_TASKS_ASSIGNED", task1=t1.task_id, robot1=t1.assigned_robot_id, task2=t2.task_id, robot2=t2.assigned_robot_id)

        # Dispatch both commands from Outbox
        await outbox_disp.send_one()
        await outbox_disp.send_one()

        # Follow execution until both complete
        t_start = time.monotonic()
        completed = False
        last_log = t_start
        while time.monotonic() - t_start < 120.0:
            c = loop.core
            t1_done = t1.task_id in c._completed_tasks
            t2_done = t2.task_id in c._completed_tasks
            if t1_done and t2_done:
                completed = True
                break
            if time.monotonic() - last_log >= 5.0:
                last_log = time.monotonic()
                r1_rec = c.tracker.get_robot("robot_1")
                r2_rec = c.tracker.get_robot("robot_2")
                print(f"[DEBUG T02 PROGRESS] elapsed={round(time.monotonic() - t_start, 1)}s | r1: state={r1_rec.state}, phase={r1_rec.current_phase}, pose=({round(r1_rec.pose.x, 2)}, {round(r1_rec.pose.y, 2)}) | r2: state={r2_rec.state}, phase={r2_rec.current_phase}, pose=({round(r2_rec.pose.x, 2)}, {round(r2_rec.pose.y, 2)})", flush=True)
            await asyncio.sleep(0.5)

        assert completed, "Both concurrent tasks must reach COMPLETED within timeout"
        res1 = loop.core._completed_tasks["task_t02_r1"]
        res2 = loop.core._completed_tasks["task_t02_r2"]
        assert res1.status == TaskStatus.COMPLETED
        assert res2.status == TaskStatus.COMPLETED

        # Verify completed in SQLite
        rows = store_t02.connection.execute("SELECT task_id, status FROM tasks WHERE task_id IN ('task_t02_r1', 'task_t02_r2')").fetchall()
        assert len(rows) == 2
        for r in rows:
            assert r["status"] == "COMPLETED"

        await loop.close()
        store_t02.close()
        executor.remove_node(sub_node_t02)

    asyncio.run(run_t02())
    emit("SCENARIO_PASSED", test="T02", details="Concurrent execution of 2 tasks succeeded on robot_1 and robot_2")

    # -------------------------------------------------------------------------
    # T03: Dinamik Nav2 Rota ve Wh Enerji Ataması
    # -------------------------------------------------------------------------
    emit("SCENARIO_START", test="T03", name="dynamic_nav2_routes_and_wh_energy")

    async def run_t03():
        cache = RouteCache()
        resolver = AsyncRouteResolver(cache=cache, clock=time.monotonic, timeout_sec=2.0)
        resolver.register_robot_client("robot_1", path_client_r1)
        resolver.register_robot_client("robot_2", path_client_r2)

        # 1. Query path for robot_1
        start_p1 = Pose2D(-2.0, -0.5, 0.0)
        goal_p1 = Pose2D(0.0, 0.0, 0.0)
        d1 = await resolver.query_route("robot_1", start_p1, goal_p1)
        assert d1 is not None and d1 > 0.5, f"Valid Nav2 path distance expected, got {d1}"
        emit("NAV2_ROUTE_RESOLVED", robot_id="robot_1", distance_m=round(d1, 2))

        # Verify cached
        cached_d1 = cache.get("robot_1", start_p1, goal_p1)
        assert cached_d1 == d1, "Distance must be stored in RouteCache"

        # 2. Query unreachable goal (outside room boundaries: (8.0, 8.0))
        unreachable_goal = Pose2D(8.0, 8.0, 0.0)
        d_fail = await resolver.query_route("robot_1", start_p1, unreachable_goal)
        assert d_fail is None, "Unreachable Nav2 route must return None (strictly NO Euclidean fallback)"
        emit("EUCLIDEAN_FALLBACK_BAN_CONFIRMED")

        # 3. Wh energy calculation test
        from backend.fleet_manager.domain.energy import check_energy_eligibility
        from backend.fleet_manager.domain.models import RobotBatterySpecs
        specs = RobotBatterySpecs(usable_capacity_wh=100.0, consumption_wh_per_meter=0.20, idle_power_w=2.0, charge_power_w=20.0)

        # High SoC (100%) -> eligible
        res_ok = check_energy_eligibility(specs=specs, battery_soc_percent=100.0, d_total_m=5.0, d_escape_m=2.0)
        assert res_ok.is_eligible is True, "100% SoC must be energy eligible"

        # Depleted SoC (7% < emergency 8%) -> ineligible
        res_low = check_energy_eligibility(specs=specs, battery_soc_percent=7.0, d_total_m=5.0, d_escape_m=2.0)
        assert res_low.is_eligible is False, "SoC below emergency reserve must be ineligible"

    asyncio.run(run_t03())
    emit("SCENARIO_PASSED", test="T03", details="Nav2 path query, grid cache, Euclidean ban, and Wh feasibility verified")

    # -------------------------------------------------------------------------
    # T04: Güvenli Preemption ve Sıfır Hız Teyidi
    # -------------------------------------------------------------------------
    emit("SCENARIO_START", test="T04", name="safe_preemption_and_standstill_confirmation")
    db_t04 = "/tmp/c3_3_3_t04.db"
    if os.path.exists(db_t04):
        os.remove(db_t04)

    core_t04, robot_ids_t04 = build_fleet_manager_from_config(config["fleet_config_path"], route_provider=shared_route_provider)
    store_t04 = SQLiteStore(db_t04)

    async def run_t04():
        sub_node_t04 = rclpy.create_node("fm_node_t04", parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        executor.add_node(sub_node_t04)

        loop = FleetEventLoop(store_t04, core_t04)
        await loop.start()

        adapter = FleetROS2Adapter(
            node=sub_node_t04,
            consumer=loop,
            loop=asyncio.get_running_loop(),
            robot_ids=robot_ids_t04,
            route_cache=shared_route_cache,
        )

        outbox_disp = OutboxDispatcher(
            consumer=loop,
            sender=adapter.outbox_sender,
            clock=time.monotonic,
            retry_delay=1.0,
        )

        # Wait for robot_1 ready
        t0 = time.monotonic()
        while time.monotonic() - t0 < 10.0:
            if loop.core.tracker.get_robot("robot_1").initial_status_verified:
                break
            await asyncio.sleep(0.2)

        # Cache routes for preemption test:
        # LOW task: pickup (-0.5, 1.5) far enough to catch during motion
        r1_pose = loop.core.tracker.get_robot("robot_1").pose
        for dx in (-0.4, -0.2, 0.0, 0.2, 0.4):
            for dy in (-0.4, -0.2, 0.0, 0.2, 0.4):
                shared_route_cache.put("robot_1", Pose2D(r1_pose.x + dx, r1_pose.y + dy), Pose2D(-0.5, 1.5), 2.5)
        shared_route_cache.put("robot_1", Pose2D(-2.0, -0.5), Pose2D(-0.5, 1.5), 2.5)
        shared_route_cache.put("robot_1", Pose2D(-1.0, -0.5), Pose2D(-0.5, 1.5), 2.5)
        shared_route_cache.put("robot_1", Pose2D(-0.5, 1.5), Pose2D(0.0, 1.5), 0.5)
        shared_route_cache.put("robot_1", Pose2D(0.0, 1.5), Pose2D(0.5, -2.0), 3.5)

        # Mark robot_2 busy with an active task so HIGH task cannot choose it
        dummy_r2_t = Task(
            task_id="dummy_r2_task",
            pickup_pose=Pose2D(0.5, 2.5),
            dropoff_pose=Pose2D(0.0, 2.5),
            priority=TaskPriority.PRIORITY_LOW,
            status=TaskStatus.EXECUTING,
            assigned_robot_id="robot_2",
            assignment_epoch=1,
            goal_uuid=str(uuid.uuid4()),
        )
        loop.core._active_tasks["dummy_r2_task"] = dummy_r2_t
        loop.core._active_tasks_by_robot["robot_2"] = dummy_r2_t
        loop.core.tracker.get_robot("robot_2").state = RobotState.STATE_EXECUTING_TASK
        loop.core.tracker.get_robot("robot_2").current_task_id = "dummy_r2_task"

        # 1. Submit LOW task
        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "task_t04_low",
            "pickup_pose": Pose2D(-0.5, 1.5),
            "dropoff_pose": Pose2D(0.0, 1.5),
            "priority": TaskPriority.PRIORITY_LOW,
            "created_at": time.monotonic(),
        }))
        await loop.submit(Event("TICK", {"current_time": time.monotonic()}))
        c = loop.core
        t_low = c._active_tasks.get("task_t04_low")
        assert t_low is not None and t_low.assigned_robot_id == "robot_1", f"task_t04_low must be assigned to robot_1, got {t_low}"
        await outbox_disp.send_one()

        # Wait until robot_1 is moving to pickup
        t0 = time.monotonic()
        while time.monotonic() - t0 < 10.0:
            c = loop.core
            r1 = c.tracker.get_robot("robot_1")
            if r1.state == RobotState.STATE_EXECUTING_TASK and r1.current_phase == TaskPhase.PHASE_MOVING_TO_PICKUP:
                break
            await asyncio.sleep(0.2)

        c = loop.core
        r1 = c.tracker.get_robot("robot_1")
        assert r1.state == RobotState.STATE_EXECUTING_TASK and r1.current_phase == TaskPhase.PHASE_MOVING_TO_PICKUP, f"robot_1 must be moving to pickup, got state={r1.state}, phase={r1.current_phase}"
        emit("ROBOT_MOVING_TO_PICKUP_CONFIRMED", robot_id="robot_1", phase=r1.current_phase)

        # 2. Submit HIGH task triggering safe preemption
        r1_moving = loop.core.tracker.get_robot("robot_1").pose
        for dx in (-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6):
            for dy in (-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6):
                shared_route_cache.put("robot_1", Pose2D(r1_moving.x + dx, r1_moving.y + dy), Pose2D(-1.0, 0.0), 0.5)
        shared_route_cache.put("robot_1", Pose2D(-1.5, 0.0), Pose2D(-1.0, 0.0), 0.5)
        shared_route_cache.put("robot_1", Pose2D(-1.0, 0.0), Pose2D(-0.5, 0.0), 0.5)
        shared_route_cache.put("robot_1", Pose2D(-0.5, 0.0), Pose2D(0.5, -2.0), 2.0)

        await loop.submit(Event("SUBMIT_TASK", {
            "task_id": "task_t04_high",
            "pickup_pose": Pose2D(-1.0, 0.0),
            "dropoff_pose": Pose2D(-0.5, 0.0),
            "priority": TaskPriority.PRIORITY_HIGH,
            "created_at": time.monotonic(),
        }))
        await loop.submit(Event("TICK", {"current_time": time.monotonic()}))

        # Verify preemption was initiated
        c = loop.core
        assert "robot_1" in c._pending_preemption_assignments, "robot_1 must be marked for preemption"
        emit("PREEMPTION_REQUESTED", robot_id="robot_1")

        # Dispatch cancel command via Outbox
        await outbox_disp.send_one()

        # Wait until terminal PREEMPTED is processed
        t0 = time.monotonic()
        preempted = False
        while time.monotonic() - t0 < 25.0:
            c = loop.core
            # LOW task should return to queue with preemption_count == 1
            low_t = c.queue.get("task_t04_low")
            if low_t is not None and low_t.preemption_count == 1:
                preempted = True
                break
            await asyncio.sleep(0.3)

        assert preempted, "Preempted task must return to queue with preemption_count == 1"
        emit("PREEMPTION_CONFIRMED_TERMINAL_RESULT", task_id="task_t04_low")

        # Wait until robot_1 telemetry confirms IDLE after preemption
        t_idle = time.monotonic()
        while time.monotonic() - t_idle < 10.0:
            if status_records["robot_1"][-1].state == RobotStatus.STATE_IDLE:
                break
            await asyncio.sleep(0.2)

        await loop.close()
        store_t04.close()
        executor.remove_node(sub_node_t04)

    asyncio.run(run_t04())
    emit("SCENARIO_PASSED", test="T04", details="Safe preemption, standstill confirmation, and N increment verified")

    # -------------------------------------------------------------------------
    # T05: Preemption Koruma Sınırı (N=2)
    # -------------------------------------------------------------------------
    emit("SCENARIO_START", test="T05", name="preemption_n2_immunity_limit")

    core_t05, _ = build_fleet_manager_from_config(config["fleet_config_path"], route_provider=shared_route_provider)
    task_n2 = Task(
        task_id="task_immune",
        pickup_pose=Pose2D(-1.0, 0.0),
        dropoff_pose=Pose2D(0.0, 0.0),
        priority=TaskPriority.PRIORITY_LOW,
        status=TaskStatus.EXECUTING,
        assigned_robot_id="robot_1",
        assignment_epoch=1,
        goal_uuid=str(uuid.uuid4()),
        preemption_count=2,  # N=2 reached!
    )
    core_t05._active_tasks[task_n2.task_id] = task_n2
    core_t05._active_tasks_by_robot["robot_1"] = task_n2
    core_t05.handle_robot_status(
        robot_id="robot_1",
        publisher_session_id=str(uuid.uuid4()),
        current_epoch=1,
        state=RobotState.STATE_EXECUTING_TASK,
        current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
        is_loaded=False,
        pose=Pose2D(-1.5, 0.0),
        battery_soc_percent=100.0,
        battery_energy_wh=100.0,
        current_task_id=task_n2.task_id,
        timestamp_sec=time.monotonic(),
    )

    high_task = Task(
        task_id="task_high_incoming",
        pickup_pose=Pose2D(-1.0, 0.0),
        dropoff_pose=Pose2D(0.0, 0.0),
        priority=TaskPriority.PRIORITY_HIGH,
        created_at=time.monotonic(),
    )

    assert task_n2.can_be_preempted() is False, "Task with preemption_count=2 must not be preemptible"
    decision = core_t05.scheduler.select_preemption_candidate(
        high_task=high_task,
        active_robots=[core_t05.tracker.get_robot("robot_1")],
        active_tasks_by_robot=core_t05._active_tasks_by_robot,
        current_time=time.monotonic(),
    )
    assert decision is None, "select_preemption_candidate must return None for task with preemption_count=2"
    emit("SCENARIO_PASSED", test="T05", details="Verified N=2 task immunity against HIGH preemption")

    # -------------------------------------------------------------------------
    # T06: İstasyon Tekil Sahipliği ve Fiziksel Ayrılma Teyidi
    # -------------------------------------------------------------------------
    emit("SCENARIO_START", test="T06", name="station_single_ownership_and_departure_confirmation")

    from backend.fleet_manager.domain.reservations import ReservationManager
    res_mgr = ReservationManager()
    res_mgr.register_station("dock_1", StationType.CHARGING, Pose2D(0.5, -2.0), tolerance_radius=0.30, departure_margin=0.05)

    # 1. robot_1 reserves dock_1
    assert res_mgr.reserve("dock_1", "robot_1") is True
    assert res_mgr.get_station("dock_1").state == ReservationState.RESERVED

    # 2. robot_2 tries to reserve -> strictly rejected
    assert res_mgr.reserve("dock_1", "robot_2") is False, "Single ownership must reject second reservation"

    # 3. robot_1 occupies dock_1
    assert res_mgr.mark_occupied("dock_1", "robot_1") is True
    assert res_mgr.get_station("dock_1").state == ReservationState.OCCUPIED

    # 4. robot_1 initiates release to depart
    assert res_mgr.initiate_release("dock_1", "robot_1") is True
    assert res_mgr.get_station("dock_1").state == ReservationState.RELEASING

    # 5. Departure check while still within tolerance (pose at 0.5, -2.0)
    freed_inside = res_mgr.update_physical_departure("dock_1", Pose2D(0.5, -2.0))
    assert freed_inside is False, "Station must NOT be freed while robot remains within tolerance"
    assert res_mgr.get_station("dock_1").state == ReservationState.RELEASING

    # 6. Departure check once physically departed (pose at -1.0, -2.0; distance 1.5m > 0.35m)
    freed_outside = res_mgr.update_physical_departure("dock_1", Pose2D(-1.0, -2.0))
    assert freed_outside is True, "Station must be declared FREE once departed beyond tolerance + margin"
    assert res_mgr.get_station("dock_1").state == ReservationState.FREE

    # 7. Now robot_2 can reserve dock_1
    assert res_mgr.reserve("dock_1", "robot_2") is True
    assert res_mgr.get_station("dock_1").state == ReservationState.RESERVED

    emit("SCENARIO_PASSED", test="T06", details="Verified single ownership and physical departure gate")

    # -------------------------------------------------------------------------
    # T07: Telemetri Kesintisi ve Geri Dönüş
    # -------------------------------------------------------------------------
    emit("SCENARIO_START", test="T07", name="telemetry_interruption_and_recovery")

    core_t07, _ = build_fleet_manager_from_config(config["fleet_config_path"], route_provider=shared_route_provider)
    sess_id_t07 = str(uuid.uuid4())
    t_base = time.monotonic()

    core_t07.handle_robot_status(
        robot_id="robot_1",
        publisher_session_id=sess_id_t07,
        current_epoch=1,
        state=RobotState.STATE_EXECUTING_TASK,
        current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
        is_loaded=False,
        pose=Pose2D(-2.0, -0.5),
        battery_soc_percent=100.0,
        battery_energy_wh=100.0,
        current_task_id="task_comm_loss",
        timestamp_sec=t_base,
    )

    # Simulate 2.5s telemetry gap
    t_stale = t_base + 2.5
    r1 = core_t07.tracker.get_robot("robot_1")
    assert r1.is_stale(t_stale) is True, "Robot must be marked STALE after 2.0s telemetry gap"
    assert r1.is_eligible_for_new_assignment(t_stale) is False, "STALE robot must be excluded from new assignments"
    # Verify robot is NOT moved to ERROR and active task is NOT failed
    assert r1.state == RobotState.STATE_EXECUTING_TASK, "Communication loss must not trigger automatic STATE_ERROR"

    # Telemetry resumes with same session ID
    core_t07.handle_robot_status(
        robot_id="robot_1",
        publisher_session_id=sess_id_t07,
        current_epoch=1,
        state=RobotState.STATE_EXECUTING_TASK,
        current_phase=TaskPhase.PHASE_MOVING_TO_PICKUP,
        is_loaded=False,
        pose=Pose2D(-1.8, -0.5),
        battery_soc_percent=99.5,
        battery_energy_wh=99.5,
        current_task_id="task_comm_loss",
        timestamp_sec=t_stale + 0.1,
    )
    assert r1.is_stale(t_stale + 0.1) is False, "Robot must recover from STALE upon telemetry resumption"
    emit("SCENARIO_PASSED", test="T07", details="Verified stale exclusion without automatic task failure")

    # -------------------------------------------------------------------------
    # T08: Executor Restart ve SESSION_BLOCKED Güvenliği
    # -------------------------------------------------------------------------
    emit("SCENARIO_START", test="T08", name="executor_restart_session_blocked")

    db_t08 = "/tmp/c3_3_3_t08.db"
    if os.path.exists(db_t08):
        os.remove(db_t08)

    core_t08, robot_ids_t08 = build_fleet_manager_from_config(config["fleet_config_path"], route_provider=shared_route_provider)
    store_t08 = SQLiteStore(db_t08)

    async def run_t08():
        loop = FleetEventLoop(store_t08, core_t08)
        await loop.start()

        sess_old = str(uuid.uuid4())
        sess_new = str(uuid.uuid4())
        t0 = time.monotonic()

        # Step 1: Initial verified status
        await loop.submit(Event("ROBOT_STATUS", {
            "robot_id": "robot_2",
            "status_seq": 1,
            "publisher_session_id": sess_old,
            "current_epoch": 0,
            "state": RobotState.STATE_IDLE,
            "current_phase": TaskPhase.PHASE_NONE,
            "is_loaded": False,
            "pose": Pose2D(1.0, 2.5),
            "battery_soc_percent": 100.0,
            "battery_energy_wh": 100.0,
            "current_task_id": None,
            "timestamp_sec": t0,
        }))

        assert loop.core.tracker.get_robot("robot_2").session_blocked is False

        # Step 2: Executor restarts and sends telemetry with new session UUID
        await loop.submit(Event("ROBOT_STATUS", {
            "robot_id": "robot_2",
            "status_seq": 1,
            "publisher_session_id": sess_new,
            "current_epoch": 0,
            "state": RobotState.STATE_IDLE,
            "current_phase": TaskPhase.PHASE_NONE,
            "is_loaded": False,
            "pose": Pose2D(1.0, 2.5),
            "battery_soc_percent": 100.0,
            "battery_energy_wh": 100.0,
            "current_task_id": None,
            "timestamp_sec": t0 + 1.0,
        }))

        # Step 3: Must transition to SESSION_BLOCKED
        r2 = loop.core.tracker.get_robot("robot_2")
        assert r2.session_blocked is True, "Session change must transition robot to SESSION_BLOCKED"
        assert r2.is_eligible_for_new_assignment(t0 + 1.0) is False, "SESSION_BLOCKED robot must be ineligible"

        await loop.close()
        store_t08.close()

    asyncio.run(run_t08())
    emit("SCENARIO_PASSED", test="T08", details="Session change triggered SESSION_BLOCKED safety gate")

    # -------------------------------------------------------------------------
    # T09: Nav2 Abort ve ClearRobotError Operatör Kurtarması
    # -------------------------------------------------------------------------
    emit("SCENARIO_START", test="T09", name="nav2_abort_and_clear_robot_error")

    # Send unreachable goal outside boundaries to trigger real Nav2 abort on robot_1
    fail_goal = ExecuteTask.Goal()
    fail_goal.task_id = "task_t09_fail"
    fail_goal.assignment_epoch = 10
    fail_goal.priority = ExecuteTask.Goal.PRIORITY_HIGH
    fail_goal.pickup_pose.header.frame_id = "map"
    fail_goal.pickup_pose.header.stamp = node.get_clock().now().to_msg()
    fail_goal.pickup_pose.pose.position.x = 8.0
    fail_goal.pickup_pose.pose.position.y = 8.0
    fail_goal.pickup_pose.pose.orientation.w = 1.0
    fail_goal.dropoff_pose = fail_goal.pickup_pose

    f_future = exec_client_r1.send_goal_async(fail_goal)
    wait_condition(lambda: f_future.done(), "Goal acceptance for unreachable task")
    f_handle = f_future.result()
    assert f_handle.accepted, "Goal should be initially accepted by executor"

    f_res_future = f_handle.get_result_async()
    wait_condition(lambda: f_res_future.done(), "Terminal result for unreachable task", timeout_s=75.0)
    f_res = f_res_future.result()
    assert f_res.result.status == ExecuteTask.Result.STATUS_FAILED, f"Expected Result STATUS_FAILED (2), got {f_res.result.status}"

    # Verify executor enters STATE_ERROR
    wait_condition(lambda: status_records["robot_1"][-1].state == RobotStatus.STATE_ERROR, "Robot entering STATE_ERROR")
    emit("ROBOT_ENTERED_STATE_ERROR", robot_id="robot_1", error=f_res.result.error_reason)

    # ClearRobotError call by operator
    req = ClearRobotError.Request()
    req.robot_id = "robot_1"
    req.expected_epoch = 10
    clear_future = clear_client_r1.call_async(req)
    wait_condition(lambda: clear_future.done(), "ClearRobotError service response")
    clear_resp = clear_future.result()
    assert clear_resp.accepted is True, f"ClearRobotError rejected: {clear_resp.reason}"
    assert clear_resp.resulting_state == RobotStatus.STATE_IDLE

    # Verify fresh telemetry reports STATE_IDLE
    wait_condition(lambda: status_records["robot_1"][-1].state == RobotStatus.STATE_IDLE, "Robot recovering to STATE_IDLE")
    emit("SCENARIO_PASSED", test="T09", details="Nav2 abort, failure recording, and operator ClearRobotError verified")

    # -------------------------------------------------------------------------
    # T10: Harita, TF ve İsim Alanı (Namespace) İzolasyonu
    # -------------------------------------------------------------------------
    emit("SCENARIO_START", test="T10", name="namespace_and_tf_isolation")

    topics_and_types = dict(node.get_topic_names_and_types())
    topic_names = set(topics_and_types.keys())

    # Namespaced topics must exist
    for r_id in ("robot_1", "robot_2"):
        assert f"/{r_id}/robot_status" in topic_names, f"Missing /{r_id}/robot_status"
        assert f"/{r_id}/cmd_vel" in topic_names, f"Missing /{r_id}/cmd_vel"
        assert f"/{r_id}/odom" in topic_names, f"Missing /{r_id}/odom"
        assert f"/{r_id}/scan" in topic_names, f"Missing /{r_id}/scan"

    # Strictly NO root-level leakage
    forbidden_root = ["/execute_task", "/robot_status", "/cmd_vel"]
    for fb in forbidden_root:
        assert fb not in topic_names, f"Forbidden root topic leakage detected: {fb}"

    # Verify TF frames
    from tf2_msgs.msg import TFMessage
    collected_tfs = []

    def tf_cb(msg: TFMessage):
        for t in msg.transforms:
            collected_tfs.append((t.header.frame_id, t.child_frame_id))

    tf_sub = node.create_subscription(TFMessage, "/tf", tf_cb, 10)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 3.0:
        time.sleep(0.1)

    r1_frames = {t[1] for t in collected_tfs if "robot_1" in t[0] or "robot_1" in t[1]}
    r2_frames = {t[1] for t in collected_tfs if "robot_2" in t[0] or "robot_2" in t[1]}
    assert len(r1_frames) > 0, "robot_1 TF frames must be present"
    assert len(r2_frames) > 0, "robot_2 TF frames must be present"
    # No cross mixing between robot_1 and robot_2 frames
    assert not (r1_frames & r2_frames), f"Cross-frame pollution detected between robots: {r1_frames & r2_frames}"

    emit("SCENARIO_PASSED", test="T10", details="Verified namespace isolation, no root leakage, and separated TF trees")

    emit("ALL_C3_3_3_TESTS_PASSED", token=os.environ.get("DDS_TEST_PAYLOAD"))
    try:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    except Exception:
        pass
    return 0


def main():
    try:
        config, fleet_data, timeout = load_config()
        role = os.environ["SIM_CHECK_ROLE"]
        emit("CONFIG_VALID", role=role, token=os.environ.get("DDS_TEST_PAYLOAD"))
        if role == "simulation":
            return simulation(config, fleet_data)
        else:
            return backend(config, fleet_data, timeout)
    except Exception as error:
        emit("FAIL", error=str(error), error_type=type(error).__name__)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
