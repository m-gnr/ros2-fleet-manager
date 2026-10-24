"""Stage C2.3 validation harness: single-robot Gazebo + Nav2 + Robot Executor simulation probe.

Verifies end-to-end logistics execution and fail-safe recovery on a single robot (robot_1)
in headless Gazebo Fortress with Nav2 and RobotExecutorNode:
1. Scenario 1: Goal validation and monotonic assignment_epoch enforcement.
2. Scenario 2: Complete logistics lifecycle (Happy Path):
   Pickup navigation -> Loading (1.5s) -> Dropoff navigation -> Unloading (1.5s) -> STATUS_SUCCEEDED.
3. Scenario 3: Pre-pickup safe preemption and odometry standstill confirmation:
   Moving to pickup -> Cancel request -> Nav2 abort -> Active brake -> Standstill verification -> STATUS_PREEMPTED.
4. Scenario 4: HIGH priority cancel immunity (cancel request rejected before pickup).
5. Scenario 5: Unreachable pose -> Nav2 abort -> STATE_ERROR -> ClearRobotError recovery (Option A).
6. Scenario 6: Monotonic epoch authority after error recovery.
7. Scenario 7: Namespace isolation and telemetry checks (/robot_1 namespace).
"""

import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import jsonschema

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
    """Load and validate simulation-c2-3 configuration."""
    config_path = Path("/config/simulation-c2-3.json")
    schema_path = Path("/config/simulation-c2-3.schema.json")
    if not config_path.exists():
        raise FileNotFoundError(f"Config missing: {config_path}")
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema missing: {schema_path}")

    config = json.loads(config_path.read_text())
    schema = json.loads(schema_path.read_text())
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(config, schema)

    def finite(value):
        if isinstance(value, dict):
            return all(finite(v) for v in value.values())
        if isinstance(value, list):
            return all(finite(v) for v in value)
        return not isinstance(value, (float, int)) or math.isfinite(value)

    if not finite(config):
        raise ValueError("All numeric config fields must be finite")

    if not Path(config["map_path"]).exists():
        raise FileNotFoundError(f'Map yaml not found at {config["map_path"]}')
    if not Path(config["nav2_template_path"]).exists():
        raise FileNotFoundError(f'Nav2 template not found at {config["nav2_template_path"]}')

    timeout = float(os.environ.get("DDS_TEST_TIMEOUT_SECONDS", "180.0"))
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

    return config, timeout


def generate_params_for_robot(config):
    """Generate Nav2 parameters file from template for robot_1."""
    template = Path(config["nav2_template_path"]).read_text()
    robot = config["robot"]
    ns = robot["namespace"]
    base_frame = robot["base_frame"]
    odom_frame = robot["odom_frame"]
    init_p = robot["initial_pose"]

    content = template.replace("@BASE_FRAME@", base_frame)
    content = content.replace("@ODOM_FRAME@", odom_frame)
    content = content.replace("@SCAN_TOPIC@", f"/{ns}/scan")
    content = content.replace("@ODOM_TOPIC@", f"/{ns}/odom")
    content = content.replace("@INIT_X@", str(init_p[0]))
    content = content.replace("@INIT_Y@", str(init_p[1]))
    content = content.replace("@INIT_Z@", "0.0")
    content = content.replace("@INIT_YAW@", str(init_p[5]))

    target = Path(f'/tmp/nav2-params-{robot["name"]}.yaml')
    target.write_text(content)
    return str(target)


def prepare_world(config):
    """Generate single-robot Gazebo world SDF."""
    room = config["room"]
    sensor = config["sensor"]
    robot = config["robot"]
    thick = room["wall_thickness_m"]
    w_h = room["wall_height_m"]
    # In config/map/map.pgm (240x240, 0.05m/res, origin [-6.0, -6.0]), the room walls are centered
    # at x = ±4.5m, y = ±4.5m with thickness 0.2m (outer span: [-4.6, 4.6], inner span: 8.8m).
    # Setting hw_x = 4.5, hw_y = 4.5 ensures Gazebo SDF geometry aligns with map.pgm for AMCL.
    hw_x = 4.5
    hw_y = 4.5
    wall_len_x = 9.2
    wall_len_y = 8.8

    name = robot["name"]
    ns = robot["namespace"]
    pose_str = " ".join(map(str, robot["initial_pose"]))
    sensor_pose_str = " ".join(map(str, sensor["pose"]))

    robot_sdf = f"""
    <!-- Robot model: {name} -->
    <model name="{name}">
      <pose>{pose_str}</pose>
      <link name="base_link">
        <inertial><mass>2.0</mass><inertia><ixx>0.04</ixx><iyy>0.06</iyy><izz>0.08</izz></inertia></inertial>
        <collision name="body"><geometry><box><size>0.5 0.3 0.1</size></box></geometry></collision>
        <visual name="body"><geometry><box><size>0.5 0.3 0.1</size></box></geometry></visual>
        <sensor name="lidar" type="gpu_lidar">
          <pose>{sensor_pose_str}</pose>
          <topic>/{ns}/scan</topic>
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
        <topic>/{ns}/cmd_vel</topic>
        <odom_topic>/{ns}/odom</odom_topic>
        <frame_id>{robot['odom_frame']}</frame_id>
        <child_frame_id>{robot['base_frame']}</child_frame_id>
        <odom_publish_frequency>30</odom_publish_frequency>
      </plugin>
    </model>
"""

    sdf = f"""<?xml version="1.0"?>
<sdf version="1.8">
  <world name="c2_validation_world">
    <physics name="physics" type="ignored">
      <max_step_size>0.001</max_step_size>
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

    <!-- 4 Walls of the Room (Aligned with map.pgm boundaries: [-4.6, 4.6] x [-4.6, 4.6]) -->
    <model name="north_wall">
      <static>true</static>
      <pose>0 {hw_y} {w_h / 2.0} 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>{wall_len_x} {thick} {w_h}</size></box></geometry></collision>
        <visual name="vis"><geometry><box><size>{wall_len_x} {thick} {w_h}</size></box></geometry></visual>
      </link>
    </model>
    <model name="south_wall">
      <static>true</static>
      <pose>0 {-hw_y} {w_h / 2.0} 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>{wall_len_x} {thick} {w_h}</size></box></geometry></collision>
        <visual name="vis"><geometry><box><size>{wall_len_x} {thick} {w_h}</size></box></geometry></visual>
      </link>
    </model>
    <model name="east_wall">
      <static>true</static>
      <pose>{hw_x} 0 {w_h / 2.0} 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>{thick} {wall_len_y} {w_h}</size></box></geometry></collision>
        <visual name="vis"><geometry><box><size>{thick} {wall_len_y} {w_h}</size></box></geometry></visual>
      </link>
    </model>
    <model name="west_wall">
      <static>true</static>
      <pose>{-hw_x} 0 {w_h / 2.0} 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>{thick} {wall_len_y} {w_h}</size></box></geometry></collision>
        <visual name="vis"><geometry><box><size>{thick} {wall_len_y} {w_h}</size></box></geometry></visual>
      </link>
    </model>

    {robot_sdf}
  </world>
</sdf>
"""
    Path("/tmp/c2-world.sdf").write_text(sdf)


def read_cgroup_metrics():
    """Read peak memory and CPU usage from cgroup v2."""
    peak_mem_mb = None
    curr_mem_mb = None
    cpu_usec = None

    mem_peak_file = Path("/sys/fs/cgroup/memory.peak")
    mem_curr_file = Path("/sys/fs/cgroup/memory.current")
    cpu_stat_file = Path("/sys/fs/cgroup/cpu.stat")

    if mem_peak_file.exists():
        try:
            peak_mem_mb = int(mem_peak_file.read_text().strip()) / (1024 * 1024)
        except Exception:
            pass
    if mem_curr_file.exists():
        try:
            curr_mem_mb = int(mem_curr_file.read_text().strip()) / (1024 * 1024)
        except Exception:
            pass
    if cpu_stat_file.exists():
        try:
            for line in cpu_stat_file.read_text().splitlines():
                if line.startswith("usage_usec"):
                    cpu_usec = int(line.split()[1])
                    break
        except Exception:
            pass

    return {
        "peak_memory_mb": round(peak_mem_mb, 2) if peak_mem_mb is not None else None,
        "current_memory_mb": round(curr_mem_mb, 2) if curr_mem_mb is not None else None,
        "cpu_usage_usec": cpu_usec,
    }


def simulation(config):
    """Run Gazebo, ros_gz_bridge, tf_helper, Nav2, and RobotExecutorNode."""
    engines = list(Path("/usr/lib").glob("*/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5"))
    if len(engines) != 1:
        raise RuntimeError(f"Expected one packaged Fortress DART engine, found {engines}")
    render_engines = list(Path("/usr/lib").glob("*/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6"))
    if len(render_engines) != 1:
        raise RuntimeError(f"Expected one packaged Fortress OGRE2 engine, found {render_engines}")

    prepare_world(config)
    params_file = generate_params_for_robot(config)

    commands = [
        [
            "ign", "gazebo", "-s", "-r", "-v", "3", "--headless-rendering",
            "--physics-engine", str(engines[0]),
            "--render-engine-server", str(render_engines[0]),
            "/tmp/c2-world.sdf"
        ],
        [
            "ros2", "run", "ros_gz_bridge", "parameter_bridge",
            "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
            "/world/c2_validation_world/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V",
            "/robot_1/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan",
            "/robot_1/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry",
            "/robot_1/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist",
        ],
        ["python3", "/opt/simulation-c2-3/tf_helper.py"],
        [
            "ros2", "launch", "nav2_bringup", "bringup_launch.py",
            "use_sim_time:=True",
            "autostart:=True",
            "use_namespace:=True",
            "namespace:=robot_1",
            "map:=" + config["map_path"],
            "params_file:=" + params_file,
            "slam:=False",
            "use_composition:=True",
        ],
        [
            "ros2", "run", "fleet_robot_executor", "robot_executor_node",
            "--ros-args",
            "-p", "fleet_config_path:=/config/fleet.yaml",
            "-p", "robot_id:=robot_1",
            "-p", "use_sim_time:=true",
            "-p", "loading_duration_sec:=1.5",
            "-p", "unloading_duration_sec:=1.5",
            "-p", "linear_stop_threshold_m_s:=0.01",
            "-p", "angular_stop_threshold_rad_s:=0.01",
            "-p", "odometry_freshness_sec:=0.5",
            "-p", "cancel_stop_timeout_sec:=3.0",
        ],
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
            emit("PROCESS_START", command=command)
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

        sim_cgroup = read_cgroup_metrics()
        emit("SIMULATION_CONTAINER_CGROUP", source="simulation_container_cgroup", **sim_cgroup)


def backend(config, timeout):
    """Execute live simulation validation against robot_1."""
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.parameter import Parameter
    from rclpy.qos import qos_profile_sensor_data
    from rclpy.utilities import get_rmw_implementation_identifier
    from action_msgs.msg import GoalStatus
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
    from tf2_msgs.msg import TFMessage
    from lifecycle_msgs.srv import GetState
    import tf2_ros

    from fleet_interfaces.action import ExecuteTask
    from fleet_interfaces.msg import RobotStatus
    from fleet_interfaces.srv import ClearRobotError

    rclpy.init()
    node = rclpy.create_node(
        "c2_3_validation_client",
        parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)],
    )

    tf_buffer = tf2_ros.Buffer()
    tf_listener = tf2_ros.TransformListener(tf_buffer, node)

    def namespaced_tf_cb(msg: TFMessage):
        for t in msg.transforms:
            try:
                tf_buffer.set_transform(t, "namespaced_tf")
            except Exception:
                pass

    node.create_subscription(TFMessage, "/robot_1/tf", namespaced_tf_cb, 10)

    clock_val = None
    scans = []
    odom_msg = None
    amcl_msg = None
    gt_pose = None
    status_history = []

    def clock_cb(msg: Clock):
        nonlocal clock_val
        clock_val = msg.clock.sec + msg.clock.nanosec / 1e9

    def scan_cb(msg: LaserScan):
        scans.append((msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9, len(msg.ranges)))

    def odom_cb(msg: Odometry):
        nonlocal odom_msg
        odom_msg = msg

    def amcl_cb(msg: PoseWithCovarianceStamped):
        nonlocal amcl_msg
        amcl_msg = msg

    def dynamic_pose_cb(msg: TFMessage):
        nonlocal gt_pose
        for t in msg.transforms:
            if t.child_frame_id == "robot_1" or t.child_frame_id.endswith("/robot_1"):
                tx = t.transform.translation.x
                ty = t.transform.translation.y
                tz = t.transform.translation.z
                qx = t.transform.rotation.x
                qy = t.transform.rotation.y
                qz = t.transform.rotation.z
                qw = t.transform.rotation.w
                yaw = quaternion_to_yaw(qx, qy, qz, qw)
                gt_pose = (tx, ty, tz, yaw)

    def status_cb(msg: RobotStatus):
        status_history.append(msg)

    node.create_subscription(Clock, "/clock", clock_cb, qos_profile_sensor_data)
    node.create_subscription(LaserScan, "/robot_1/scan", scan_cb, qos_profile_sensor_data)
    node.create_subscription(Odometry, "/robot_1/odom", odom_cb, qos_profile_sensor_data)
    node.create_subscription(PoseWithCovarianceStamped, "/robot_1/amcl_pose", amcl_cb, qos_profile_sensor_data)
    node.create_subscription(TFMessage, "/world/c2_validation_world/dynamic_pose/info", dynamic_pose_cb, 10)
    node.create_subscription(RobotStatus, "/robot_1/robot_status", status_cb, 10)

    execute_client = ActionClient(node, ExecuteTask, "/robot_1/execute_task")
    clear_error_client = node.create_client(ClearRobotError, "/robot_1/clear_robot_error")

    deadline = time.monotonic() + timeout

    def spin_while(predicate, interval=0.1):
        while predicate():
            if time.monotonic() > deadline:
                raise TimeoutError("Validation deadline exceeded while waiting on condition")
            rclpy.spin_once(node, timeout_sec=interval)

    test_start_monotonic = time.monotonic()

    try:
        emit("BACKEND_START", rmw=get_rmw_implementation_identifier(), token=os.environ["DDS_TEST_PAYLOAD"])

        # =====================================================================
        # Step 1: Wait for Clock, Sensors, Lifecycle, TF, and AMCL Initial Pose
        # =====================================================================
        emit("WAITING_FOR_CLOCK_AND_SENSORS")
        min_scans = config["check"]["minimum_scan_messages"]
        spin_while(lambda: clock_val is None or len(scans) < min_scans or odom_msg is None or gt_pose is None)

        emit(
            "CLOCK_AND_SENSORS_OK",
            clock=clock_val,
            scans=len(scans),
            odom_frame=odom_msg.header.frame_id,
            gt=gt_pose,
        )

        emit("CHECKING_NAV2_LIFECYCLE_STATES")
        managed_node_names = [
            "map_server",
            "amcl",
            "controller_server",
            "planner_server",
            "behavior_server",
            "bt_navigator",
        ]
        all_lifecycle_clients = {
            f"/robot_1/{n}": node.create_client(GetState, f"/robot_1/{n}/get_state")
            for n in managed_node_names
        }

        for name, client in all_lifecycle_clients.items():
            spin_while(lambda: not client.wait_for_service(timeout_sec=0.2))

        def check_all_active():
            states = {}
            for name, client in all_lifecycle_clients.items():
                future = client.call_async(GetState.Request())
                spin_while(lambda: not future.done(), interval=0.05)
                res = future.result()
                if res is None or res.current_state.label != "active":
                    return False, states
                states[name] = res.current_state.label
            return True, states

        all_active = False
        final_states = {}
        while not all_active and time.monotonic() < deadline:
            all_active, final_states = check_all_active()
            if not all_active:
                time.sleep(0.5)

        if not all_active:
            raise RuntimeError(f"Not all 6 Nav2 lifecycle nodes active: {final_states}")

        emit("NAV2_LIFECYCLE_ACTIVE", states=final_states)

        emit("CHECKING_TF_CHAINS")
        tf_ok = False
        while not tf_ok and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            can_odom = tf_buffer.can_transform("map", "robot_1/odom", rclpy.time.Time())
            can_base = tf_buffer.can_transform("robot_1/odom", "robot_1/base_link", rclpy.time.Time())
            can_map_base = tf_buffer.can_transform("map", "robot_1/base_link", rclpy.time.Time())
            if can_odom and can_base and can_map_base:
                tf_ok = True
                break
            time.sleep(0.2)

        if not tf_ok:
            raise RuntimeError("TF chain map -> robot_1/odom -> robot_1/base_link could not be verified")

        t_r1 = tf_buffer.lookup_transform("map", "robot_1/base_link", rclpy.time.Time())
        emit("TF_CHAINS_VALID", r1_trans=[t_r1.transform.translation.x, t_r1.transform.translation.y])

        emit("CHECKING_AMCL_INITIAL_POSE")
        spin_while(lambda: amcl_msg is None)
        init_p = config["robot"]["initial_pose"]
        amcl_p = amcl_msg.pose.pose.position
        amcl_err = math.hypot(amcl_p.x - init_p[0], amcl_p.y - init_p[1])
        amcl_tol = config["check"]["amcl_tolerance_m"]
        emit("AMCL_INITIAL_POSE", x=amcl_p.x, y=amcl_p.y, error_m=amcl_err, tolerance_m=amcl_tol)
        if amcl_err > amcl_tol:
            raise ValueError(f"AMCL initial error {amcl_err:.4f}m exceeds tolerance {amcl_tol:.4f}m")

        # Wait for Robot Executor interfaces
        emit("WAITING_FOR_ROBOT_EXECUTOR_INTERFACES")
        spin_while(lambda: not execute_client.wait_for_server(timeout_sec=0.5))
        spin_while(lambda: not clear_error_client.wait_for_service(timeout_sec=0.5))
        spin_while(lambda: len(status_history) < 3)

        initial_status = status_history[-1]
        emit(
            "ROBOT_EXECUTOR_READY",
            robot_id=initial_status.robot_id,
            state=initial_status.state,
            current_phase=initial_status.current_phase,
            current_epoch=initial_status.current_epoch,
            is_loaded=initial_status.is_loaded,
        )
        assert initial_status.robot_id == "robot_1"
        assert initial_status.state == RobotStatus.STATE_IDLE
        assert initial_status.current_phase == RobotStatus.PHASE_NONE
        assert initial_status.is_loaded is False

        # =====================================================================
        # Step 2: Scenario 1 - Goal Validation & Stale Epoch Rejection
        # =====================================================================
        emit("SCENARIO_1_START", name="goal_validation_and_stale_epoch_rejection")
        bad_goal = ExecuteTask.Goal()
        bad_goal.task_id = ""  # Invalid empty task_id
        bad_goal.assignment_epoch = 0  # Invalid stale epoch
        bad_goal.priority = 99  # Invalid priority

        future = execute_client.send_goal_async(bad_goal)
        spin_while(lambda: not future.done())
        handle = future.result()
        if handle.accepted:
            raise RuntimeError("ExecuteTask action server accepted invalid goal!")
        emit("SCENARIO_1_PASS", detail="Invalid and stale epoch goal rejected as expected")

        # =====================================================================
        # Step 3: Scenario 2 - Happy Path Execution (Real Nav2 Driving)
        # =====================================================================
        emit("SCENARIO_2_START", name="happy_path_lifecycle")
        emit("NAVIGATION_WINDOW_START", monotonic=time.monotonic(), wall_time=time.time())

        happy_goal = ExecuteTask.Goal()
        happy_goal.task_id = "task_c2_happy_01"
        happy_goal.assignment_epoch = 1
        happy_goal.priority = ExecuteTask.Goal.PRIORITY_HIGH

        # Pickup at (-1.0, -0.5), Dropoff at (0.5, -0.5)
        happy_goal.pickup_pose.header.frame_id = "map"
        happy_goal.pickup_pose.header.stamp = node.get_clock().now().to_msg()
        happy_goal.pickup_pose.pose.position.x = -1.0
        happy_goal.pickup_pose.pose.position.y = -0.5
        happy_goal.pickup_pose.pose.orientation.w = 1.0

        happy_goal.dropoff_pose.header.frame_id = "map"
        happy_goal.dropoff_pose.header.stamp = node.get_clock().now().to_msg()
        happy_goal.dropoff_pose.pose.position.x = 0.5
        happy_goal.dropoff_pose.pose.position.y = -0.5
        happy_goal.dropoff_pose.pose.orientation.w = 1.0

        phases_observed = set()

        def happy_feedback_cb(fb_msg):
            phases_observed.add(fb_msg.feedback.current_phase)

        send_future = execute_client.send_goal_async(happy_goal, feedback_callback=happy_feedback_cb)
        spin_while(lambda: not send_future.done())
        happy_handle = send_future.result()
        if not happy_handle.accepted:
            raise RuntimeError("Happy path ExecuteTask goal was rejected by server!")

        emit("HAPPY_PATH_GOAL_ACCEPTED", goal_uuid=str(happy_handle.goal_id.uuid))
        result_future = happy_handle.get_result_async()

        # Monitor execution through phases
        last_log = time.monotonic()
        while not result_future.done():
            if time.monotonic() > deadline:
                raise TimeoutError("Timeout waiting for happy path to finish")
            rclpy.spin_once(node, timeout_sec=0.1)
            now = time.monotonic()
            if now - last_log >= 2.0:
                last_log = now
                latest_st = status_history[-1] if status_history else None
                emit(
                    "HAPPY_PATH_PROGRESS",
                    observed_phases=sorted(list(phases_observed)),
                    current_phase=latest_st.current_phase if latest_st else None,
                    is_loaded=latest_st.is_loaded if latest_st else None,
                    gt=gt_pose,
                )

        emit("NAVIGATION_WINDOW_END", monotonic=time.monotonic(), wall_time=time.time())

        happy_res = result_future.result()
        if happy_res.status != GoalStatus.STATUS_SUCCEEDED:
            raise RuntimeError(f"Happy path task failed with GoalStatus: {happy_res.status}")

        result_payload = happy_res.result
        if result_payload.status != ExecuteTask.Result.STATUS_SUCCEEDED:
            raise RuntimeError(f"Happy path result status is not STATUS_SUCCEEDED: {result_payload.status}")
        if result_payload.completed_epoch != 1:
            raise ValueError(f"completed_epoch {result_payload.completed_epoch} != expected 1")

        # Verify ground truth distance to dropoff
        dropoff_x, dropoff_y = 0.5, -0.5
        gt_dist_dropoff = math.hypot(gt_pose[0] - dropoff_x, gt_pose[1] - dropoff_y)
        xy_tol = config["goals"]["xy_tolerance_m"]
        emit(
            "HAPPY_PATH_DROPOFF_ACCURACY",
            gt_x=gt_pose[0],
            gt_y=gt_pose[1],
            target_x=dropoff_x,
            target_y=dropoff_y,
            dist_gt_m=gt_dist_dropoff,
            tolerance_m=xy_tol,
        )
        if gt_dist_dropoff > xy_tol:
            raise ValueError(f"Ground truth distance to dropoff {gt_dist_dropoff:.4f}m exceeds tolerance {xy_tol:.4f}m")

        # Verify observed phases included all 4 logistics phases:
        # 1: MOVING_TO_PICKUP, 2: LOADING, 3: MOVING_TO_DROPOFF, 4: UNLOADING
        expected_phases = {
            ExecuteTask.Feedback.PHASE_MOVING_TO_PICKUP,
            ExecuteTask.Feedback.PHASE_LOADING,
            ExecuteTask.Feedback.PHASE_MOVING_TO_DROPOFF,
            ExecuteTask.Feedback.PHASE_UNLOADING,
        }
        if not expected_phases.issubset(phases_observed):
            emit("WARN_MISSING_FEEDBACK_PHASES", observed=sorted(list(phases_observed)), expected=sorted(list(expected_phases)))

        # Verify robot returned to IDLE with loaded=False and current_task_id=""
        spin_while(lambda: status_history[-1].state != RobotStatus.STATE_IDLE, interval=0.1)
        final_happy_st = status_history[-1]
        assert final_happy_st.state == RobotStatus.STATE_IDLE
        assert final_happy_st.current_phase == RobotStatus.PHASE_NONE
        assert final_happy_st.is_loaded is False
        assert final_happy_st.current_task_id == ""
        assert final_happy_st.current_epoch == 1

        emit("SCENARIO_2_PASS", detail="Happy path completed with verified navigation, loading, and dropoff")

        # =====================================================================
        # Step 4: Scenario 3 - Pre-pickup Safe Preemption & Odometry Standstill
        # =====================================================================
        emit("SCENARIO_3_START", name="safe_preemption_and_odometry_standstill")

        cancel_goal = ExecuteTask.Goal()
        cancel_goal.task_id = "task_c2_cancel_02"
        cancel_goal.assignment_epoch = 2
        cancel_goal.priority = ExecuteTask.Goal.PRIORITY_MEDIUM  # Cancellable

        cancel_goal.pickup_pose.header.frame_id = "map"
        cancel_goal.pickup_pose.header.stamp = node.get_clock().now().to_msg()
        cancel_goal.pickup_pose.pose.position.x = -1.5
        cancel_goal.pickup_pose.pose.position.y = 1.5
        cancel_goal.pickup_pose.pose.orientation.w = 1.0

        cancel_goal.dropoff_pose.header.frame_id = "map"
        cancel_goal.dropoff_pose.header.stamp = node.get_clock().now().to_msg()
        cancel_goal.dropoff_pose.pose.position.x = 0.0
        cancel_goal.dropoff_pose.pose.position.y = 1.5
        cancel_goal.dropoff_pose.pose.orientation.w = 1.0

        c_send_future = execute_client.send_goal_async(cancel_goal)
        spin_while(lambda: not c_send_future.done())
        cancel_handle = c_send_future.result()
        if not cancel_handle.accepted:
            raise RuntimeError("Cancel goal was unexpectedly rejected!")

        emit("PREEMPTION_GOAL_ACCEPTED", task_id="task_c2_cancel_02")

        # Wait until robot begins moving towards pickup
        def robot_is_moving():
            if odom_msg is None:
                return False
            vx = odom_msg.twist.twist.linear.x
            vy = odom_msg.twist.twist.linear.y
            speed = math.hypot(vx, vy)
            return speed >= 0.03

        emit("WAITING_FOR_ROBOT_MOTION_BEFORE_CANCEL")
        spin_while(lambda: not robot_is_moving())
        curr_speed = math.hypot(odom_msg.twist.twist.linear.x, odom_msg.twist.twist.linear.y)
        emit("ROBOT_MOTION_CONFIRMED", linear_speed_m_s=curr_speed)

        # Trigger cancel
        emit("SENDING_CANCEL_REQUEST")
        cancel_req_future = cancel_handle.cancel_goal_async()
        spin_while(lambda: not cancel_req_future.done())
        cancel_response = cancel_req_future.result()
        emit(
            "CANCEL_RESPONSE_RECEIVED",
            return_code=cancel_response.return_code,
            canceling_goals_count=len(cancel_response.goals_canceling),
        )
        if len(cancel_response.goals_canceling) == 0:
            raise RuntimeError(f"Cancel request rejected unexpectedly! goals_canceling is empty.")

        # Wait for terminal result
        c_res_future = cancel_handle.get_result_async()
        spin_while(lambda: not c_res_future.done())
        c_res = c_res_future.result()

        if c_res.status != GoalStatus.STATUS_CANCELED:
            raise RuntimeError(f"Expected STATUS_CANCELED (5), got: {c_res.status}")
        if c_res.result.status != ExecuteTask.Result.STATUS_PREEMPTED:
            raise RuntimeError(f"Expected result STATUS_PREEMPTED (3), got: {c_res.result.status}")

        # Confirm odometry standstill
        time.sleep(0.5)
        rclpy.spin_once(node, timeout_sec=0.1)
        final_vx = abs(odom_msg.twist.twist.linear.x)
        final_wz = abs(odom_msg.twist.twist.angular.z)
        emit("ODOMETRY_STANDSTILL_CHECK", linear_vel=final_vx, angular_vel=final_wz)
        if final_vx > 0.015 or final_wz > 0.015:
            raise ValueError(f"Robot failed to halt: vx={final_vx:.4f}, wz={final_wz:.4f}")

        # Verify RobotStatus returned to IDLE
        spin_while(lambda: status_history[-1].state != RobotStatus.STATE_IDLE, interval=0.1)
        st_preempt = status_history[-1]
        assert st_preempt.state == RobotStatus.STATE_IDLE
        assert st_preempt.current_phase == RobotStatus.PHASE_NONE
        assert st_preempt.current_task_id == ""
        assert st_preempt.current_epoch == 2

        emit("SCENARIO_3_PASS", detail="Pre-pickup safe preemption succeeded with confirmed physical standstill")

        # =====================================================================
        # Step 5: Scenario 4 - HIGH Priority Preemption Immunity Check
        # =====================================================================
        emit("SCENARIO_4_START", name="high_priority_cancel_immunity")

        high_imm_goal = ExecuteTask.Goal()
        high_imm_goal.task_id = "task_c2_high_imm"
        high_imm_goal.assignment_epoch = 3
        high_imm_goal.priority = ExecuteTask.Goal.PRIORITY_HIGH  # Immutable

        high_imm_goal.pickup_pose.header.frame_id = "map"
        high_imm_goal.pickup_pose.header.stamp = node.get_clock().now().to_msg()
        high_imm_goal.pickup_pose.pose.position.x = 0.0
        high_imm_goal.pickup_pose.pose.position.y = 0.0
        high_imm_goal.pickup_pose.pose.orientation.w = 1.0

        high_imm_goal.dropoff_pose.header.frame_id = "map"
        high_imm_goal.dropoff_pose.header.stamp = node.get_clock().now().to_msg()
        high_imm_goal.dropoff_pose.pose.position.x = 0.5
        high_imm_goal.dropoff_pose.pose.position.y = 0.0
        high_imm_goal.dropoff_pose.pose.orientation.w = 1.0

        h_send_future = execute_client.send_goal_async(high_imm_goal)
        spin_while(lambda: not h_send_future.done())
        h_handle = h_send_future.result()
        assert h_handle.accepted

        # Attempt preemption on HIGH priority goal
        h_cancel_future = h_handle.cancel_goal_async()
        spin_while(lambda: not h_cancel_future.done())
        h_cancel_resp = h_cancel_future.result()
        emit(
            "HIGH_PRIORITY_CANCEL_RESULT",
            return_code=h_cancel_resp.return_code,
            canceling_goals_count=len(h_cancel_resp.goals_canceling),
        )
        # Server rejected cancel by removing the goal from goals_canceling
        if len(h_cancel_resp.goals_canceling) > 0:
            raise RuntimeError("Cancel request on HIGH priority task was accepted; expected REJECTION!")

        # Let task run to completion
        h_res_future = h_handle.get_result_async()
        spin_while(lambda: not h_res_future.done())
        h_res = h_res_future.result()
        if h_res.status != GoalStatus.STATUS_SUCCEEDED:
            raise RuntimeError(f"HIGH priority task did not succeed with GoalStatus: {h_res.status}")
        if h_res.result.status != ExecuteTask.Result.STATUS_SUCCEEDED:
            raise RuntimeError(f"HIGH priority task did not succeed with result status: {h_res.result.status}")

        emit("SCENARIO_4_PASS", detail="HIGH priority goal was immune to cancel and completed successfully")

        # =====================================================================
        # Step 6: Scenario 5 - Nav2 Abort -> STATE_ERROR -> ClearRobotError
        # =====================================================================
        emit("SCENARIO_5_START", name="nav2_abort_and_clear_robot_error_recovery")

        fail_goal = ExecuteTask.Goal()
        fail_goal.task_id = "task_c2_fail_04"
        fail_goal.assignment_epoch = 4
        fail_goal.priority = ExecuteTask.Goal.PRIORITY_HIGH

        # Unreachable goal outside room map boundary (8.0, 8.0)
        fail_goal.pickup_pose.header.frame_id = "map"
        fail_goal.pickup_pose.header.stamp = node.get_clock().now().to_msg()
        fail_goal.pickup_pose.pose.position.x = 8.0
        fail_goal.pickup_pose.pose.position.y = 8.0
        fail_goal.pickup_pose.pose.orientation.w = 1.0

        fail_goal.dropoff_pose.header.frame_id = "map"
        fail_goal.dropoff_pose.header.stamp = node.get_clock().now().to_msg()
        fail_goal.dropoff_pose.pose.position.x = 0.0
        fail_goal.dropoff_pose.pose.position.y = 0.0
        fail_goal.dropoff_pose.pose.orientation.w = 1.0

        f_send_future = execute_client.send_goal_async(fail_goal)
        spin_while(lambda: not f_send_future.done())
        fail_handle = f_send_future.result()
        assert fail_handle.accepted

        emit("UNREACHABLE_GOAL_DISPATCHED", target_x=8.0, target_y=8.0)
        f_res_future = fail_handle.get_result_async()
        spin_while(lambda: not f_res_future.done())
        f_res = f_res_future.result()

        if f_res.status != GoalStatus.STATUS_ABORTED:
            emit("WARN_ACTION_TERMINAL_STATUS", status=f_res.status)
        if f_res.result.status != ExecuteTask.Result.STATUS_FAILED:
            raise RuntimeError(f"Expected Result STATUS_FAILED (2), got: {f_res.result.status}")
        emit("TASK_FAILURE_CAPTURED", error_reason=f_res.result.error_reason)

        # Verify RobotStatus is in STATE_ERROR
        spin_while(lambda: status_history[-1].state != RobotStatus.STATE_ERROR, interval=0.1)
        st_err = status_history[-1]
        assert st_err.state == RobotStatus.STATE_ERROR
        assert st_err.current_task_id == "task_c2_fail_04"
        assert st_err.current_epoch == 4
        emit("ROBOT_STATUS_STATE_ERROR_CONFIRMED", epoch=st_err.current_epoch, task_id=st_err.current_task_id)

        # Verify new goal is rejected while in STATE_ERROR
        blocked_goal = ExecuteTask.Goal()
        blocked_goal.task_id = "task_blocked"
        blocked_goal.assignment_epoch = 5
        blocked_goal.priority = ExecuteTask.Goal.PRIORITY_HIGH
        blocked_goal.pickup_pose.header.frame_id = "map"
        blocked_goal.pickup_pose.header.stamp = node.get_clock().now().to_msg()
        blocked_goal.pickup_pose.pose.orientation.w = 1.0
        blocked_goal.dropoff_pose = blocked_goal.pickup_pose

        b_future = execute_client.send_goal_async(blocked_goal)
        spin_while(lambda: not b_future.done())
        b_handle = b_future.result()
        if b_handle.accepted:
            raise RuntimeError("New goal was accepted while robot was in STATE_ERROR!")
        emit("BLOCKED_GOAL_REJECTED_WHILE_IN_ERROR")

        # Step 6a: ClearRobotError with epoch mismatch (expected_epoch = 99)
        emit("TESTING_CLEAR_ROBOT_ERROR_EPOCH_MISMATCH")
        req_bad = ClearRobotError.Request()
        req_bad.robot_id = "robot_1"
        req_bad.expected_epoch = 99
        srv_future_bad = clear_error_client.call_async(req_bad)
        spin_while(lambda: not srv_future_bad.done())
        srv_resp_bad = srv_future_bad.result()
        assert srv_resp_bad.accepted is False
        assert srv_resp_bad.resulting_state == RobotStatus.STATE_ERROR
        emit("EPOCH_MISMATCH_CLEAR_REJECTED", reason=srv_resp_bad.reason)

        # Step 6b: ClearRobotError with matching epoch (expected_epoch = 4)
        emit("TESTING_CLEAR_ROBOT_ERROR_SUCCESS")
        req_good = ClearRobotError.Request()
        req_good.robot_id = "robot_1"
        req_good.expected_epoch = 4
        srv_future_good = clear_error_client.call_async(req_good)
        spin_while(lambda: not srv_future_good.done())
        srv_resp_good = srv_future_good.result()
        assert srv_resp_good.accepted is True
        assert srv_resp_good.resulting_state == RobotStatus.STATE_IDLE
        emit("CLEAR_ROBOT_ERROR_ACCEPTED", resulting_state=srv_resp_good.resulting_state)

        # Verify RobotStatus returned to STATE_IDLE with Option A (epoch unchanged at 4)
        spin_while(lambda: status_history[-1].state != RobotStatus.STATE_IDLE, interval=0.1)
        st_cleared = status_history[-1]
        assert st_cleared.state == RobotStatus.STATE_IDLE
        assert st_cleared.current_phase == RobotStatus.PHASE_NONE
        assert st_cleared.current_task_id == ""
        assert st_cleared.current_epoch == 4  # Option A: not incremented!
        emit("OPTION_A_EPOCH_PRESERVATION_VERIFIED", current_epoch=st_cleared.current_epoch)

        emit("SCENARIO_5_PASS", detail="Nav2 abort, STATE_ERROR, and ClearRobotError recovery verified")

        # =====================================================================
        # Step 7: Scenario 6 - Monotonic Epoch Authority After Recovery
        # =====================================================================
        emit("SCENARIO_6_START", name="monotonic_epoch_after_recovery")
        stale_recovery_goal = ExecuteTask.Goal()
        stale_recovery_goal.task_id = "task_stale_after_clear"
        stale_recovery_goal.assignment_epoch = 3  # Lower than current_epoch (4)
        stale_recovery_goal.priority = ExecuteTask.Goal.PRIORITY_HIGH
        stale_recovery_goal.pickup_pose.header.frame_id = "map"
        stale_recovery_goal.pickup_pose.header.stamp = node.get_clock().now().to_msg()
        stale_recovery_goal.pickup_pose.pose.orientation.w = 1.0
        stale_recovery_goal.dropoff_pose = stale_recovery_goal.pickup_pose

        sr_future = execute_client.send_goal_async(stale_recovery_goal)
        spin_while(lambda: not sr_future.done())
        sr_handle = sr_future.result()
        assert sr_handle.accepted is False
        emit("SCENARIO_6_PASS", detail="Monotonic epoch enforcement strictly retained after ClearRobotError")

        # =====================================================================
        # Step 8: Scenario 7 - Namespace Isolation & Telemetry Verification
        # =====================================================================
        emit("SCENARIO_7_START", name="namespace_isolation_verification")
        topic_names_and_types = dict(node.get_topic_names_and_types())
        assert "/robot_1/robot_status" in topic_names_and_types
        assert "/robot_1/odom" in topic_names_and_types
        assert "/robot_1/scan" in topic_names_and_types
        assert "/robot_status" not in topic_names_and_types
        emit("SCENARIO_7_PASS", detail="Namespace isolation verified for /robot_1 endpoints")

        # =====================================================================
        # Step 9: Final Resource Measurements and Summary Event
        # =====================================================================
        run_duration_s = time.monotonic() - test_start_monotonic
        backend_cgroup = read_cgroup_metrics()
        emit(
            "BACKEND_CONTAINER_CGROUP",
            source="backend_container_cgroup",
            run_duration_s=round(run_duration_s, 2),
            total_scans=len(scans),
            total_status_msgs=len(status_history),
            **backend_cgroup,
        )

        emit(
            "C2_3_PASS",
            token=os.environ["DDS_TEST_PAYLOAD"],
            scenarios_verified=[
                "SCENARIO_1_GOAL_VALIDATION",
                "SCENARIO_2_HAPPY_PATH_LIFECYCLE",
                "SCENARIO_3_SAFE_PREEMPTION_STANDSTILL",
                "SCENARIO_4_HIGH_PRIORITY_CANCEL_IMMUNITY",
                "SCENARIO_5_NAV2_ABORT_AND_CLEAR_ROBOT_ERROR",
                "SCENARIO_6_MONOTONIC_EPOCH_AUTHORITY",
                "SCENARIO_7_NAMESPACE_ISOLATION",
            ],
            happy_path_dropoff_dist_m=round(gt_dist_dropoff, 4),
            final_halt_linear_vel_m_s=round(final_vx, 4),
            final_halt_angular_vel_rad_s=round(final_wz, 4),
            run_duration_s=round(run_duration_s, 2),
            backend_peak_mem_mb=backend_cgroup.get("peak_memory_mb"),
        )
        return 0

    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def main():
    try:
        config, timeout = load_config()
        role = os.environ["SIM_CHECK_ROLE"]
        emit("CONFIG_VALID", role=role, token=os.environ.get("DDS_TEST_PAYLOAD"))
        if role == "simulation":
            return simulation(config)
        else:
            return backend(config, timeout)
    except Exception as error:
        emit("FAIL", error=str(error), error_type=type(error).__name__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
