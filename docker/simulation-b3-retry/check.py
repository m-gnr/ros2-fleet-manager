"""Stage B3 retry validation harness: dual-robot Nav2 simulation probe.
Verifies multi-robot navigation in a shared Gazebo Fortress world with independent
namespaces (/robot_1, /robot_2), separated TF trees, and parallel goal execution.

Success criteria:
- Primary: Nav2 STATUS_SUCCEEDED and Gazebo ground truth distance <= 0.35m for both robots.
- Secondary (diagnostic only): AMCL distance is reported; does not determine pass/fail.
- Invalid: dist_odom is invalid due to frame mismatch (origin at robot start vs map target).
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
    print(json.dumps(dict(event=event, **values)), flush=True)


def quaternion_to_yaw(x, y, z, w):
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def load_config():
    config_path = Path('/config/simulation-b3.json')
    schema_path = Path('/config/simulation-b3.schema.json')
    if not config_path.exists():
        raise FileNotFoundError(f'Config missing: {config_path}')
    if not schema_path.exists():
        raise FileNotFoundError(f'Schema missing: {schema_path}')
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
        raise ValueError('All numeric config fields must be finite')

    if not Path(config['map_path']).exists():
        raise FileNotFoundError(f'Map yaml not found at {config["map_path"]}')
    if not Path(config['nav2_template_path']).exists():
        raise FileNotFoundError(f'Nav2 template not found at {config["nav2_template_path"]}')

    timeout = float(os.environ.get('DDS_TEST_TIMEOUT_SECONDS', '120.0'))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('DDS_TEST_TIMEOUT_SECONDS must be positive and finite')
    if not 0 <= int(os.environ.get('ROS_DOMAIN_ID', '0')) <= 232:
        raise ValueError('ROS_DOMAIN_ID must be in 0..232')
    if os.environ.get('ROS_LOCALHOST_ONLY') != '0':
        raise ValueError('ROS_LOCALHOST_ONLY must be 0 for cross-container test')
    if not os.environ.get('DDS_TEST_PAYLOAD', '').strip():
        raise ValueError('DDS_TEST_PAYLOAD must identify the run')
    if os.environ.get('SIM_CHECK_ROLE') not in ('simulation', 'backend'):
        raise ValueError('SIM_CHECK_ROLE must be simulation or backend')

    return config, timeout


def generate_params_for_robot(config, robot):
    template = Path(config['nav2_template_path']).read_text()
    ns = robot['namespace']
    base_frame = robot['base_frame']
    odom_frame = robot['odom_frame']
    init_p = robot['initial_pose']

    content = template.replace('@BASE_FRAME@', base_frame)
    content = content.replace('@ODOM_FRAME@', odom_frame)
    content = content.replace('@SCAN_TOPIC@', f'/{ns}/scan')
    content = content.replace('@ODOM_TOPIC@', f'/{ns}/odom')
    content = content.replace('@INIT_X@', str(init_p[0]))
    content = content.replace('@INIT_Y@', str(init_p[1]))
    content = content.replace('@INIT_Z@', '0.0')
    content = content.replace('@INIT_YAW@', str(init_p[5]))

    target = Path(f'/tmp/nav2-params-{robot["name"]}.yaml')
    target.write_text(content)
    return str(target)


def prepare_world(config):
    room = config['room']
    sensor = config['sensor']
    w_size = room['size_m']
    thick = room['wall_thickness_m']
    w_h = room['wall_height_m']
    hw_x = w_size[0] / 2.0 - thick / 2.0
    hw_y = w_size[1] / 2.0 - thick / 2.0

    robot_models_sdf = []
    for r in config['robots']:
        name = r['name']
        ns = r['namespace']
        pose_str = ' '.join(map(str, r['initial_pose']))
        sensor_pose_str = ' '.join(map(str, sensor['pose']))
        r_sdf = f"""
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
        <frame_id>{r['odom_frame']}</frame_id>
        <child_frame_id>{r['base_frame']}</child_frame_id>
        <odom_publish_frequency>30</odom_publish_frequency>
      </plugin>
    </model>
"""
        robot_models_sdf.append(r_sdf)

    sdf = f"""<?xml version="1.0"?>
<sdf version="1.8">
  <world name="b3_validation_world">
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

    <!-- 4 Walls of the Room -->
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
        <collision name="col"><geometry><box><size>{thick} {w_size[1] - 2 * thick} {w_h}</size></box></geometry></collision>
        <visual name="vis"><geometry><box><size>{thick} {w_size[1] - 2 * thick} {w_h}</size></box></geometry></visual>
      </link>
    </model>
    <model name="west_wall">
      <static>true</static>
      <pose>{-hw_x} 0 {w_h / 2.0} 0 0 0</pose>
      <link name="link">
        <collision name="col"><geometry><box><size>{thick} {w_size[1] - 2 * thick} {w_h}</size></box></geometry></collision>
        <visual name="vis"><geometry><box><size>{thick} {w_size[1] - 2 * thick} {w_h}</size></box></geometry></visual>
      </link>
    </model>

    {''.join(robot_models_sdf)}
  </world>
</sdf>
"""
    Path('/tmp/b3-world.sdf').write_text(sdf)


def read_cgroup_metrics():
    peak_mem_mb = None
    curr_mem_mb = None
    cpu_usec = None

    mem_peak_file = Path('/sys/fs/cgroup/memory.peak')
    mem_curr_file = Path('/sys/fs/cgroup/memory.current')
    cpu_stat_file = Path('/sys/fs/cgroup/cpu.stat')

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
                if line.startswith('usage_usec'):
                    cpu_usec = int(line.split()[1])
                    break
        except Exception:
            pass

    return {
        'peak_memory_mb': round(peak_mem_mb, 2) if peak_mem_mb is not None else None,
        'current_memory_mb': round(curr_mem_mb, 2) if curr_mem_mb is not None else None,
        'cpu_usage_usec': cpu_usec,
    }


def simulation(config):
    engines = list(Path('/usr/lib').glob('*/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5'))
    if len(engines) != 1:
        raise RuntimeError(f'Expected one packaged Fortress DART engine, found {engines}')
    render_engines = list(Path('/usr/lib').glob('*/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6'))
    if len(render_engines) != 1:
        raise RuntimeError(f'Expected one packaged Fortress OGRE2 engine, found {render_engines}')

    prepare_world(config)

    params_files = {}
    for r in config['robots']:
        params_files[r['name']] = generate_params_for_robot(config, r)

    commands = [
        ['ign', 'gazebo', '-s', '-r', '-v', '3', '--headless-rendering',
         '--physics-engine', str(engines[0]),
         '--render-engine-server', str(render_engines[0]),
         '/tmp/b3-world.sdf'],
        ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
         '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
         '/world/b3_validation_world/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
         '/robot_1/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
         '/robot_1/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
         '/robot_1/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
         '/robot_2/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
         '/robot_2/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
         '/robot_2/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist'],
        ['python3', '/opt/simulation-b3-retry/tf_helper.py'],
        ['ros2', 'launch', 'nav2_bringup', 'bringup_launch.py',
         'use_sim_time:=True',
         'autostart:=True',
         'use_namespace:=True',
         'namespace:=robot_1',
         'map:=' + config['map_path'],
         'params_file:=' + params_files['robot_1'],
         'slam:=False',
         'use_composition:=True'],
        ['ros2', 'launch', 'nav2_bringup', 'bringup_launch.py',
         'use_sim_time:=True',
         'autostart:=True',
         'use_namespace:=True',
         'namespace:=robot_2',
         'map:=' + config['map_path'],
         'params_file:=' + params_files['robot_2'],
         'slam:=False',
         'use_composition:=True'],
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
            emit('PROCESS_START', command=command)
            children.append(subprocess.Popen(command, start_new_session=True))
        while not stopped:
            for child in children:
                if child.poll() is not None:
                    raise RuntimeError(f'Child {child.args[0]} exited unexpectedly: {child.returncode}')
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
                child.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=1.0)
                    emit('FORCED_KILL', command=child.args[0])
                except Exception:
                    pass
            emit('PROCESS_EXIT', command=child.args[0], code=child.returncode)

        sim_cgroup = read_cgroup_metrics()
        emit('SIMULATION_CONTAINER_CGROUP',
             source='simulation_container_cgroup',
             **sim_cgroup)


def backend(config, timeout):
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.parameter import Parameter
    from rclpy.qos import qos_profile_sensor_data
    from rclpy.utilities import get_rmw_implementation_identifier
    from action_msgs.msg import GoalStatus
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from tf2_msgs.msg import TFMessage
    from nav2_msgs.action import NavigateToPose
    from lifecycle_msgs.srv import GetState
    import tf2_ros

    rclpy.init()
    node = rclpy.create_node(
        'b3_retry_client',
        parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, True)]
    )

    tf_buffer = tf2_ros.Buffer()
    tf_listener = tf2_ros.TransformListener(tf_buffer, node)

    def namespaced_tf_cb(msg: TFMessage):
        for t in msg.transforms:
            try:
                tf_buffer.set_transform(t, 'namespaced_tf')
            except Exception:
                pass

    node.create_subscription(TFMessage, '/robot_1/tf', namespaced_tf_cb, 10)
    node.create_subscription(TFMessage, '/robot_2/tf', namespaced_tf_cb, 10)

    clock_val = None
    scans = {'robot_1': [], 'robot_2': []}
    odom_msgs = {'robot_1': None, 'robot_2': None}
    amcl_msgs = {'robot_1': None, 'robot_2': None}
    gt_poses = {'robot_1': None, 'robot_2': None}

    def clock_cb(msg: Clock):
        nonlocal clock_val
        clock_val = msg.clock.sec + msg.clock.nanosec / 1e9

    def make_scan_cb(robot_name):
        def cb(msg: LaserScan):
            scans[robot_name].append((msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9, len(msg.ranges)))
        return cb

    def make_odom_cb(robot_name):
        def cb(msg: Odometry):
            odom_msgs[robot_name] = msg
        return cb

    def make_amcl_cb(robot_name):
        def cb(msg: PoseWithCovarianceStamped):
            amcl_msgs[robot_name] = msg
        return cb

    def dynamic_pose_cb(msg: TFMessage):
        for t in msg.transforms:
            for rname in ('robot_1', 'robot_2'):
                if t.child_frame_id == rname or t.child_frame_id.endswith('/' + rname):
                    tx = t.transform.translation.x
                    ty = t.transform.translation.y
                    tz = t.transform.translation.z
                    qx = t.transform.rotation.x
                    qy = t.transform.rotation.y
                    qz = t.transform.rotation.z
                    qw = t.transform.rotation.w
                    yaw = quaternion_to_yaw(qx, qy, qz, qw)
                    gt_poses[rname] = (tx, ty, tz, yaw)

    node.create_subscription(Clock, '/clock', clock_cb, qos_profile_sensor_data)
    node.create_subscription(TFMessage, '/world/b3_validation_world/dynamic_pose/info', dynamic_pose_cb, 10)

    for r in config['robots']:
        rname = r['name']
        ns = r['namespace']
        node.create_subscription(LaserScan, f'/{ns}/scan', make_scan_cb(rname), qos_profile_sensor_data)
        node.create_subscription(Odometry, f'/{ns}/odom', make_odom_cb(rname), qos_profile_sensor_data)
        node.create_subscription(PoseWithCovarianceStamped, f'/{ns}/amcl_pose', make_amcl_cb(rname), qos_profile_sensor_data)

    action_clients = {
        'robot_1': ActionClient(node, NavigateToPose, '/robot_1/navigate_to_pose'),
        'robot_2': ActionClient(node, NavigateToPose, '/robot_2/navigate_to_pose'),
    }

    deadline = time.monotonic() + timeout

    def spin_while(predicate, interval=0.1):
        while predicate():
            if time.monotonic() > deadline:
                raise TimeoutError('Validation deadline exceeded while waiting on condition')
            rclpy.spin_once(node, timeout_sec=interval)

    test_start_monotonic = time.monotonic()

    try:
        emit('BACKEND_START', rmw=get_rmw_implementation_identifier(), token=os.environ['DDS_TEST_PAYLOAD'])

        # Step 1: Wait for clock, scans, and odom for both robots
        emit('WAITING_FOR_CLOCK_AND_SENSORS')
        min_scans = config['check']['minimum_scan_messages']
        spin_while(lambda: (clock_val is None or
                            len(scans['robot_1']) < min_scans or
                            len(scans['robot_2']) < min_scans or
                            odom_msgs['robot_1'] is None or
                            odom_msgs['robot_2'] is None or
                            gt_poses['robot_1'] is None or
                            gt_poses['robot_2'] is None))

        emit('CLOCK_AND_SENSORS_OK',
             clock=clock_val,
             robot_1_scans=len(scans['robot_1']),
             robot_2_scans=len(scans['robot_2']),
             robot_1_odom_frame=odom_msgs['robot_1'].header.frame_id,
             robot_2_odom_frame=odom_msgs['robot_2'].header.frame_id,
             robot_1_gt=gt_poses['robot_1'],
             robot_2_gt=gt_poses['robot_2'])

        # Step 2: Validate Nav2 Lifecycle states for both robots (6/6 each = 12 nodes)
        emit('CHECKING_LIFECYCLE_STATES')
        managed_node_names = [
            'map_server',
            'amcl',
            'controller_server',
            'planner_server',
            'behavior_server',
            'bt_navigator',
        ]
        all_lifecycle_clients = {}
        for r in config['robots']:
            ns = r['namespace']
            for n in managed_node_names:
                full_name = f'/{ns}/{n}'
                all_lifecycle_clients[full_name] = node.create_client(GetState, f'{full_name}/get_state')

        for name, client in all_lifecycle_clients.items():
            spin_while(lambda: not client.wait_for_service(timeout_sec=0.2))

        def check_all_active():
            states = {}
            for name, client in all_lifecycle_clients.items():
                future = client.call_async(GetState.Request())
                spin_while(lambda: not future.done(), interval=0.05)
                res = future.result()
                if res is None or res.current_state.label != 'active':
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
            raise RuntimeError(f'Not all 12 Nav2 lifecycle nodes active: {final_states}')

        emit('LIFECYCLE_ACTIVE', total_nodes=len(final_states), states=final_states)

        # Step 3: Validate separated TF chains for both robots
        emit('CHECKING_TF_CHAINS')
        tf_ok = False
        while not tf_ok and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            can_r1_odom = tf_buffer.can_transform('map', 'robot_1/odom', rclpy.time.Time())
            can_r1_base = tf_buffer.can_transform('robot_1/odom', 'robot_1/base_link', rclpy.time.Time())
            can_r1_map_base = tf_buffer.can_transform('map', 'robot_1/base_link', rclpy.time.Time())

            can_r2_odom = tf_buffer.can_transform('map', 'robot_2/odom', rclpy.time.Time())
            can_r2_base = tf_buffer.can_transform('robot_2/odom', 'robot_2/base_link', rclpy.time.Time())
            can_r2_map_base = tf_buffer.can_transform('map', 'robot_2/base_link', rclpy.time.Time())

            if (can_r1_odom and can_r1_base and can_r1_map_base and
                    can_r2_odom and can_r2_base and can_r2_map_base):
                tf_ok = True
                break
            time.sleep(0.2)

        if not tf_ok:
            raise RuntimeError('TF chains could not be verified')

        t_r1 = tf_buffer.lookup_transform('map', 'robot_1/base_link', rclpy.time.Time())
        t_r2 = tf_buffer.lookup_transform('map', 'robot_2/base_link', rclpy.time.Time())
        emit('TF_CHAINS_VALID',
             robot_1_trans=[t_r1.transform.translation.x, t_r1.transform.translation.y],
             robot_2_trans=[t_r2.transform.translation.x, t_r2.transform.translation.y])

        # Step 4: Validate AMCL Initial Poses
        emit('CHECKING_AMCL_INITIAL_POSES')
        spin_while(lambda: amcl_msgs['robot_1'] is None or amcl_msgs['robot_2'] is None)

        amcl_tol = config['check']['amcl_tolerance_m']
        for r in config['robots']:
            rname = r['name']
            amcl_p = amcl_msgs[rname].pose.pose.position
            init_p = r['initial_pose']
            err = math.hypot(amcl_p.x - init_p[0], amcl_p.y - init_p[1])
            emit('AMCL_INITIAL_POSE', robot=rname, x=amcl_p.x, y=amcl_p.y, error_m=err)
            if err > amcl_tol:
                raise ValueError(f'Robot {rname} initial AMCL error {err:.4f}m exceeds tolerance {amcl_tol:.4f}m')

        emit('AMCL_INITIAL_POSES_VALID')

        # Step 5: Send Separate NavigateToPose Goals to both robots
        emit('WAITING_FOR_ACTION_SERVERS')
        for rname, client in action_clients.items():
            spin_while(lambda: not client.wait_for_server(timeout_sec=0.5))

        goal_futures = {}
        for r in config['robots']:
            rname = r['name']
            goal_cfg = r['goal_pose']
            goal_msg = NavigateToPose.Goal()
            goal_msg.pose.header.frame_id = 'map'
            goal_msg.pose.header.stamp = node.get_clock().now().to_msg()
            goal_msg.pose.pose.position.x = float(goal_cfg[0])
            goal_msg.pose.pose.position.y = float(goal_cfg[1])
            goal_msg.pose.pose.position.z = 0.0
            yaw = float(goal_cfg[2])
            goal_msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
            goal_msg.pose.pose.orientation.w = math.cos(yaw / 2.0)

            emit('SENDING_NAVIGATE_TO_POSE_GOAL', robot=rname, target_x=goal_cfg[0], target_y=goal_cfg[1], target_yaw=yaw)
            goal_futures[rname] = action_clients[rname].send_goal_async(goal_msg)

        # Wait for both goals to be accepted
        for rname, future in goal_futures.items():
            spin_while(lambda: not future.done())
            handle = future.result()
            if not handle.accepted:
                raise RuntimeError(f'NavigateToPose goal rejected by action server for {rname}')
            emit('GOAL_ACCEPTED', robot=rname)

        # Mark NAVIGATION WINDOW START
        emit('NAVIGATION_WINDOW_START', monotonic=time.monotonic(), wall_time=time.time())

        goal_handles = {rname: f.result() for rname, f in goal_futures.items()}
        result_futures = {rname: handle.get_result_async() for rname, handle in goal_handles.items()}

        # Step 6: Monitor Execution, Collision Distance, and Cross-Talk
        emit('MONITORING_PARALLEL_NAVIGATION')
        min_collision_dist_cfg = config['check']['min_collision_distance_m']
        min_inter_robot_distance = float('inf')

        last_check_time = time.monotonic()
        while not all(rf.done() for rf in result_futures.values()):
            if time.monotonic() > deadline:
                raise TimeoutError('Timeout waiting for both robot navigation goals to complete')
            rclpy.spin_once(node, timeout_sec=0.1)

            # Check inter-robot distance using Gazebo ground truth
            gt1 = gt_poses['robot_1']
            gt2 = gt_poses['robot_2']
            if gt1 is not None and gt2 is not None:
                d = math.hypot(gt1[0] - gt2[0], gt1[1] - gt2[1])
                if d < min_inter_robot_distance:
                    min_inter_robot_distance = d
                if d < min_collision_dist_cfg:
                    raise RuntimeError(f'Collision violation: inter-robot distance {d:.4f}m < {min_collision_dist_cfg:.4f}m')

            now = time.monotonic()
            if now - last_check_time >= 2.0:
                last_check_time = now
                emit('NAVIGATION_PROGRESS',
                     robot_1_done=result_futures['robot_1'].done(),
                     robot_2_done=result_futures['robot_2'].done(),
                     inter_robot_dist_m=d,
                     min_inter_robot_dist_m=min_inter_robot_distance)

        # Mark NAVIGATION WINDOW END
        emit('NAVIGATION_WINDOW_END', monotonic=time.monotonic(), wall_time=time.time())

        # Step 7: Validate Action Results and Final Distance to Target
        emit('GOALS_COMPLETED_CHECKING_RESULTS')
        xy_tol = config['goals']['xy_tolerance_m']

        final_distances = {}
        for r in config['robots']:
            rname = r['name']
            res_wrap = result_futures[rname].result()
            if res_wrap.status != GoalStatus.STATUS_SUCCEEDED:
                raise RuntimeError(f'Robot {rname} navigation failed with status: {res_wrap.status}')

            goal_p = r['goal_pose']
            odom_p = odom_msgs[rname].pose.pose.position
            amcl_p = amcl_msgs[rname].pose.pose.position
            gt_p = gt_poses[rname]

            # dist_odom is relative to odom origin (starting pose), invalid as map-frame metric
            dist_odom = math.hypot(odom_p.x - goal_p[0], odom_p.y - goal_p[1])
            # dist_amcl is secondary diagnostic metric
            dist_amcl = math.hypot(amcl_p.x - goal_p[0], amcl_p.y - goal_p[1])
            # dist_gt is PRIMARY metric
            dist_gt = math.hypot(gt_p[0] - goal_p[0], gt_p[1] - goal_p[1])

            final_distances[rname] = {
                'dist_gt_m': dist_gt,
                'dist_amcl_m': dist_amcl,
                'dist_odom_m': dist_odom,
            }

            emit('DESTINATION_REACHED',
                 robot=rname, status=res_wrap.status,
                 dist_gt_m=dist_gt, dist_amcl_m=dist_amcl, dist_odom_m=dist_odom,
                 tolerance_m=xy_tol,
                 primary_eval='PASS' if dist_gt <= xy_tol else 'FAIL')

            # Primary success criterion check
            if dist_gt > xy_tol:
                raise ValueError(f'Robot {rname} ground truth distance {dist_gt:.4f}m exceeds tolerance {xy_tol:.4f}m')

        # Step 8: Measure Resource Stats inside backend container
        run_duration_s = time.monotonic() - test_start_monotonic

        # Scan rates
        measured_scan_hz = {}
        for rname in ('robot_1', 'robot_2'):
            stamps = [s[0] for s in scans[rname][-20:]]
            if len(stamps) >= 2:
                dt = stamps[-1] - stamps[0]
                measured_scan_hz[rname] = (len(stamps) - 1) / dt if dt > 0 else 0.0
            else:
                measured_scan_hz[rname] = 0.0

        backend_cgroup = read_cgroup_metrics()
        emit('BACKEND_CONTAINER_CGROUP',
             source='backend_container_cgroup',
             run_duration_s=round(run_duration_s, 2),
             scan_rates_hz=measured_scan_hz,
             total_scans={'robot_1': len(scans['robot_1']), 'robot_2': len(scans['robot_2'])},
             min_inter_robot_distance_m=round(min_inter_robot_distance, 4),
             **backend_cgroup)

        emit('B3_PASS',
             token=os.environ['DDS_TEST_PAYLOAD'],
             robot_1_gt_m=final_distances['robot_1']['dist_gt_m'],
             robot_2_gt_m=final_distances['robot_2']['dist_gt_m'],
             robot_1_amcl_m=final_distances['robot_1']['dist_amcl_m'],
             robot_2_amcl_m=final_distances['robot_2']['dist_amcl_m'],
             min_inter_robot_distance_m=round(min_inter_robot_distance, 4),
             backend_cgroup_peak_mb=backend_cgroup.get('peak_memory_mb'))
        return 0

    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def main():
    try:
        config, timeout = load_config()
        role = os.environ['SIM_CHECK_ROLE']
        emit('CONFIG_VALID', role=role, token=os.environ.get('DDS_TEST_PAYLOAD'))
        if role == 'simulation':
            return simulation(config)
        else:
            return backend(config, timeout)
    except Exception as error:
        emit('FAIL', error=str(error), error_type=type(error).__name__)
        return 1


if __name__ == '__main__':
    sys.exit(main())
