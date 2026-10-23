"""Stage B AMCL verification harness: offset convergence test.
Verifies that AMCL map->odom correction converges toward Gazebo ground truth
when initialized with an intentional offset.
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
    config_path = Path('/config/simulation-amcl-test.json')
    schema_path = Path('/config/simulation-amcl-test.schema.json')
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
    if not Path(config['nav2_parameters']).exists():
        raise FileNotFoundError(f'Nav2 parameters not found at {config["nav2_parameters"]}')

    timeout = float(os.environ.get('DDS_TEST_TIMEOUT_SECONDS', '90.0'))
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


def prepare_world(config):
    robot = config['robot']
    room = config['room']
    sensor = config['sensor']
    w_size = room['size_m']
    thick = room['wall_thickness_m']
    w_h = room['wall_height_m']
    hw_x = w_size[0] / 2.0 - thick / 2.0
    hw_y = w_size[1] / 2.0 - thick / 2.0

    sdf = f"""<?xml version="1.0"?>
<sdf version="1.8">
  <world name="amcl_validation_world">
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

    <!-- Robot model -->
    <model name="{robot['name']}">
      <pose>{' '.join(map(str, robot['initial_pose']))}</pose>
      <link name="base_link">
        <inertial><mass>2.0</mass><inertia><ixx>0.04</ixx><iyy>0.06</iyy><izz>0.08</izz></inertia></inertial>
        <collision name="body"><geometry><box><size>0.5 0.3 0.1</size></box></geometry></collision>
        <visual name="body"><geometry><box><size>0.5 0.3 0.1</size></box></geometry></visual>
        <sensor name="lidar" type="gpu_lidar">
          <pose>{' '.join(map(str, sensor['pose']))}</pose>
          <topic>/scan</topic>
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
        <topic>/cmd_vel</topic>
        <odom_topic>/odom</odom_topic>
        <frame_id>odom</frame_id>
        <child_frame_id>base_link</child_frame_id>
        <odom_publish_frequency>30</odom_publish_frequency>
      </plugin>
    </model>
  </world>
</sdf>
"""
    Path('/tmp/amcl-world.sdf').write_text(sdf)


def simulation(config):
    engines = list(Path('/usr/lib').glob('*/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5'))
    if len(engines) != 1:
        raise RuntimeError(f'Expected one packaged Fortress DART engine, found {engines}')
    render_engines = list(Path('/usr/lib').glob('*/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6'))
    if len(render_engines) != 1:
        raise RuntimeError(f'Expected one packaged Fortress OGRE2 engine, found {render_engines}')

    prepare_world(config)

    commands = [
        ['ign', 'gazebo', '-s', '-r', '-v', '3', '--headless-rendering',
         '--physics-engine', str(engines[0]),
         '--render-engine-server', str(render_engines[0]),
         '/tmp/amcl-world.sdf'],
        ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
         '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
         '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
         '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
         '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
         '/world/amcl_validation_world/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V'],
        ['python3', '/opt/simulation-amcl-test/tf_helper.py'],
        ['ros2', 'launch', 'nav2_bringup', 'bringup_launch.py',
         'use_sim_time:=True',
         'autostart:=True',
         'map:=' + config['map_path'],
         'params_file:=' + config['nav2_parameters'],
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
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                    emit('FORCED_KILL', command=child.args[0])
                except ProcessLookupError:
                    pass
            emit('PROCESS_EXIT', command=child.args[0], code=child.returncode)


def backend(config, timeout):
    import rclpy
    from rclpy.parameter import Parameter
    from rclpy.qos import qos_profile_sensor_data
    from rclpy.utilities import get_rmw_implementation_identifier
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
    from tf2_msgs.msg import TFMessage
    from lifecycle_msgs.srv import GetState
    import tf2_ros

    rclpy.init()
    node = rclpy.create_node(
        'amcl_validation_client',
        parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, True)]
    )

    tf_buffer = tf2_ros.Buffer()
    tf_listener = tf2_ros.TransformListener(tf_buffer, node)

    clock_val = None
    scans = []
    odom_msg = None
    amcl_msg = None
    ground_truth_pose = None  # (x, y, yaw) from Gazebo dynamic_pose/info

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
        nonlocal ground_truth_pose
        target_name = config['robot']['name']
        for t in msg.transforms:
            if t.child_frame_id == target_name or t.child_frame_id.endswith('/' + target_name):
                tx = t.transform.translation.x
                ty = t.transform.translation.y
                tz = t.transform.translation.z
                qx = t.transform.rotation.x
                qy = t.transform.rotation.y
                qz = t.transform.rotation.z
                qw = t.transform.rotation.w
                yaw = quaternion_to_yaw(qx, qy, qz, qw)
                ground_truth_pose = (tx, ty, tz, yaw)
                break

    node.create_subscription(Clock, '/clock', clock_cb, qos_profile_sensor_data)
    node.create_subscription(LaserScan, '/scan', scan_cb, qos_profile_sensor_data)
    node.create_subscription(Odometry, '/odom', odom_cb, qos_profile_sensor_data)
    node.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', amcl_cb, qos_profile_sensor_data)
    node.create_subscription(TFMessage, '/world/amcl_validation_world/dynamic_pose/info', dynamic_pose_cb, 10)

    cmd_pub = node.create_publisher(Twist, '/cmd_vel', 10)

    deadline = time.monotonic() + timeout

    def spin_while(predicate, interval=0.1):
        while predicate():
            if time.monotonic() > deadline:
                raise TimeoutError('Validation deadline exceeded while waiting on condition')
            rclpy.spin_once(node, timeout_sec=interval)

    try:
        emit('BACKEND_START', rmw=get_rmw_implementation_identifier(), token=os.environ['DDS_TEST_PAYLOAD'])

        # Step 1: Wait for clock, sensors, and Gazebo ground truth
        emit('WAITING_FOR_CLOCK_AND_SENSORS')
        spin_while(lambda: clock_val is None or len(scans) < config['check']['minimum_scan_messages'] or odom_msg is None or ground_truth_pose is None)
        emit('CLOCK_AND_SENSORS_OK', clock=clock_val, scan_count=len(scans),
             ground_truth_x=ground_truth_pose[0], ground_truth_y=ground_truth_pose[1], ground_truth_yaw=ground_truth_pose[3])

        # Step 2: Validate Nav2 Lifecycle states
        emit('CHECKING_LIFECYCLE_STATES')
        managed_nodes = [
            'map_server',
            'amcl',
            'controller_server',
            'planner_server',
            'behavior_server',
            'bt_navigator',
        ]
        clients = {name: node.create_client(GetState, f'/{name}/get_state') for name in managed_nodes}

        for name, client in clients.items():
            spin_while(lambda: not client.wait_for_service(timeout_sec=0.2))

        def check_all_active():
            states = {}
            for name, client in clients.items():
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
            raise RuntimeError(f'Nav2 lifecycle nodes not all active: {final_states}')

        emit('LIFECYCLE_ACTIVE', states=final_states)

        # Step 3: Validate TF chain map -> odom -> base_link
        emit('CHECKING_TF_CHAIN')
        tf_ok = False
        while not tf_ok and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            can_map_odom = tf_buffer.can_transform('map', 'odom', rclpy.time.Time())
            can_odom_base = tf_buffer.can_transform('odom', 'base_link', rclpy.time.Time())
            can_map_base = tf_buffer.can_transform('map', 'base_link', rclpy.time.Time())
            if can_map_odom and can_odom_base and can_map_base:
                tf_ok = True
                break
            time.sleep(0.2)

        if not tf_ok:
            raise RuntimeError('TF chain map -> odom -> base_link could not be verified')

        # Step 4: Record Initial Poses and Offset
        emit('WAITING_FOR_INITIAL_AMCL_POSE')
        spin_while(lambda: amcl_msg is None)

        amcl_p0 = amcl_msg.pose.pose.position
        amcl_q0 = amcl_msg.pose.pose.orientation
        amcl_yaw0 = quaternion_to_yaw(amcl_q0.x, amcl_q0.y, amcl_q0.z, amcl_q0.w)

        gt_x0, gt_y0, _, gt_yaw0 = ground_truth_pose
        initial_error = math.hypot(amcl_p0.x - gt_x0, amcl_p0.y - gt_y0)
        initial_yaw_error = abs((amcl_yaw0 - gt_yaw0 + math.pi) % (2 * math.pi) - math.pi)

        t_map_odom0 = tf_buffer.lookup_transform('map', 'odom', rclpy.time.Time())
        map_odom_trans0 = [
            t_map_odom0.transform.translation.x,
            t_map_odom0.transform.translation.y,
            t_map_odom0.transform.translation.z,
        ]

        emit('INITIAL_AMCL_POSE_WITH_OFFSET',
             ground_truth_x=gt_x0, ground_truth_y=gt_y0, ground_truth_yaw=gt_yaw0,
             amcl_x=amcl_p0.x, amcl_y=amcl_p0.y, amcl_yaw=amcl_yaw0,
             initial_error_m=initial_error,
             initial_yaw_error_rad=initial_yaw_error,
             map_to_odom_translation=map_odom_trans0)

        min_err_expected = config['check']['minimum_initial_error_m']
        if initial_error < min_err_expected:
            raise ValueError(f'Initial AMCL error {initial_error:.4f}m is less than expected offset threshold {min_err_expected:.4f}m')

        # Step 5: Drive the robot to trigger AMCL particle filter convergence
        drive_cfg = config['drive_test']
        duration = drive_cfg['duration_seconds']
        linear_v = drive_cfg['linear_vel_mps']
        angular_w = drive_cfg['angular_vel_radps']
        emit('STARTING_DRIVE_MOTION', linear_v=linear_v, angular_w=angular_w, duration_s=duration)

        twist = Twist()
        twist.linear.x = float(linear_v)
        twist.angular.z = float(angular_w)

        start_time = time.monotonic()
        last_log_time = start_time
        while (time.monotonic() - start_time) < duration:
            cmd_pub.publish(twist)
            rclpy.spin_once(node, timeout_sec=0.1)

            now = time.monotonic()
            if now - last_log_time >= 1.0:
                last_log_time = now
                curr_amcl = amcl_msg.pose.pose.position
                gt_x, gt_y, _, _ = ground_truth_pose
                curr_err = math.hypot(curr_amcl.x - gt_x, curr_amcl.y - gt_y)
                emit('DRIVE_PROGRESS', elapsed_s=round(now - start_time, 2),
                     gt_x=gt_x, gt_y=gt_y, amcl_x=curr_amcl.x, amcl_y=curr_amcl.y, error_m=curr_err)

        # Step 6: Stop robot and settle
        stop_twist = Twist()
        for _ in range(5):
            cmd_pub.publish(stop_twist)
            rclpy.spin_once(node, timeout_sec=0.05)

        emit('MOTION_STOPPED_WAITING_SETTLE')
        settle_start = time.monotonic()
        while time.monotonic() - settle_start < 3.0:
            cmd_pub.publish(stop_twist)
            rclpy.spin_once(node, timeout_sec=0.1)

        # Step 7: Final Measurement and Convergence Check
        final_amcl_p = amcl_msg.pose.pose.position
        final_amcl_q = amcl_msg.pose.pose.orientation
        final_amcl_yaw = quaternion_to_yaw(final_amcl_q.x, final_amcl_q.y, final_amcl_q.z, final_amcl_q.w)

        gt_xf, gt_yf, _, gt_yawf = ground_truth_pose
        final_error = math.hypot(final_amcl_p.x - gt_xf, final_amcl_p.y - gt_yf)
        final_yaw_error = abs((final_amcl_yaw - gt_yawf + math.pi) % (2 * math.pi) - math.pi)

        t_map_odom_f = tf_buffer.lookup_transform('map', 'odom', rclpy.time.Time())
        map_odom_trans_f = [
            t_map_odom_f.transform.translation.x,
            t_map_odom_f.transform.translation.y,
            t_map_odom_f.transform.translation.z,
        ]

        error_reduction = initial_error - final_error
        tolerance = config['check']['amcl_tolerance_m']
        passed = (final_error <= tolerance)

        emit('FINAL_AMCL_EVALUATION',
             ground_truth_x=gt_xf, ground_truth_y=gt_yf, ground_truth_yaw=gt_yawf,
             amcl_x=final_amcl_p.x, amcl_y=final_amcl_p.y, amcl_yaw=final_amcl_yaw,
             initial_error_m=initial_error,
             final_error_m=final_error,
             error_reduction_m=error_reduction,
             tolerance_m=tolerance,
             passed=passed,
             initial_map_to_odom=map_odom_trans0,
             final_map_to_odom=map_odom_trans_f)

        if not passed:
            raise ValueError(f'AMCL failed to converge within tolerance: final error {final_error:.4f}m exceeds {tolerance:.4f}m')

        # Step 8: Metrics
        stamps = [s[0] for s in scans[-20:]]
        if len(stamps) >= 2:
            dt = stamps[-1] - stamps[0]
            measured_scan_hz = (len(stamps) - 1) / dt if dt > 0 else 0.0
        else:
            measured_scan_hz = 0.0

        cpu_usage_usec = None
        cgroup_cpu = Path('/sys/fs/cgroup/cpu.stat')
        if cgroup_cpu.exists():
            for line in cgroup_cpu.read_text().splitlines():
                if line.startswith('usage_usec'):
                    cpu_usage_usec = int(line.split()[1])
                    break

        emit('METRICS',
             measured_scan_rate_hz=measured_scan_hz,
             total_scan_messages=len(scans),
             cgroup_usage_usec=cpu_usage_usec)

        emit('AMCL_TEST_PASS',
             token=os.environ['DDS_TEST_PAYLOAD'],
             initial_error_m=initial_error,
             final_error_m=final_error,
             error_reduction_m=error_reduction,
             tolerance_m=tolerance)
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
