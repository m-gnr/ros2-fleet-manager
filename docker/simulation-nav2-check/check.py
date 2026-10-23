"""Stage B2 validation harness: single-robot Nav2 simulation probe.
No application lifecycle policy; validation only.
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


def load_config():
    config_path = Path('/config/simulation-nav2-check.json')
    schema_path = Path('/config/simulation-nav2-check.schema.json')
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
  <world name="b2_validation_world">
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
    Path('/tmp/nav2-world.sdf').write_text(sdf)


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
         '/tmp/nav2-world.sdf'],
        ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
         '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
         '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
         '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
         '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist'],
        ['python3', '/opt/simulation-nav2-check/tf_helper.py'],
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
    from rclpy.action import ActionClient
    from rclpy.parameter import Parameter
    from rclpy.qos import qos_profile_sensor_data
    from rclpy.utilities import get_rmw_implementation_identifier
    from action_msgs.msg import GoalStatus
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import LaserScan
    from nav_msgs.msg import Odometry
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from nav2_msgs.action import NavigateToPose
    from lifecycle_msgs.srv import GetState
    import tf2_ros

    rclpy.init()
    node = rclpy.create_node(
        'nav2_validation_client',
        parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, True)]
    )

    tf_buffer = tf2_ros.Buffer()
    tf_listener = tf2_ros.TransformListener(tf_buffer, node)

    clock_val = None
    scans = []
    odom_msg = None
    amcl_msg = None

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

    node.create_subscription(Clock, '/clock', clock_cb, qos_profile_sensor_data)
    node.create_subscription(LaserScan, '/scan', scan_cb, qos_profile_sensor_data)
    node.create_subscription(Odometry, '/odom', odom_cb, qos_profile_sensor_data)
    node.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', amcl_cb, qos_profile_sensor_data)

    action_client = ActionClient(node, NavigateToPose, 'navigate_to_pose')

    deadline = time.monotonic() + timeout

    def spin_while(predicate, interval=0.1):
        while predicate():
            if time.monotonic() > deadline:
                raise TimeoutError('Validation deadline exceeded while waiting on condition')
            rclpy.spin_once(node, timeout_sec=interval)

    try:
        emit('BACKEND_START', rmw=get_rmw_implementation_identifier(), token=os.environ['DDS_TEST_PAYLOAD'])

        # Step 1: Wait for clock advance and basic sensor data
        emit('WAITING_FOR_CLOCK_AND_SENSORS')
        spin_while(lambda: clock_val is None or len(scans) < config['check']['minimum_scan_messages'] or odom_msg is None)
        emit('CLOCK_AND_SENSORS_OK', clock=clock_val, scan_count=len(scans), odom_frame=odom_msg.header.frame_id)

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

        t_map_base = tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
        emit('TF_CHAIN_VALID',
             translation=[t_map_base.transform.translation.x,
                          t_map_base.transform.translation.y,
                          t_map_base.transform.translation.z],
             rotation=[t_map_base.transform.rotation.x,
                       t_map_base.transform.rotation.y,
                       t_map_base.transform.rotation.z,
                       t_map_base.transform.rotation.w])

        # Step 4: Validate AMCL convergence at initial pose
        emit('CHECKING_AMCL_CONVERGENCE')
        spin_while(lambda: amcl_msg is None)
        amcl_p = amcl_msg.pose.pose.position
        init_p = config['robot']['initial_pose']
        amcl_error = math.hypot(amcl_p.x - init_p[0], amcl_p.y - init_p[1])
        emit('AMCL_POSE', x=amcl_p.x, y=amcl_p.y, error_m=amcl_error)
        if amcl_error > config['check']['amcl_tolerance_m']:
            raise ValueError(f'AMCL pose error {amcl_error:.4f}m exceeds tolerance {config["check"]["amcl_tolerance_m"]:.4f}m')
        emit('AMCL_CONVERGED', error_m=amcl_error)

        # Step 5: Send NavigateToPose Goal
        emit('WAITING_FOR_ACTION_SERVER')
        spin_while(lambda: not action_client.wait_for_server(timeout_sec=0.5))

        goal_cfg = config['goal']
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = node.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = float(goal_cfg['pose'][0])
        goal_msg.pose.pose.position.y = float(goal_cfg['pose'][1])
        goal_msg.pose.pose.position.z = 0.0
        yaw = float(goal_cfg['pose'][2])
        goal_msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
        goal_msg.pose.pose.orientation.w = math.cos(yaw / 2.0)

        emit('SENDING_NAVIGATE_TO_POSE_GOAL', target_x=goal_cfg['pose'][0], target_y=goal_cfg['pose'][1], target_yaw=yaw)
        send_goal_future = action_client.send_goal_async(goal_msg)
        spin_while(lambda: not send_goal_future.done())
        goal_handle = send_goal_future.result()

        if not goal_handle.accepted:
            raise RuntimeError('NavigateToPose goal was rejected by action server')
        emit('GOAL_ACCEPTED')

        # Step 6: Wait for Result
        get_result_future = goal_handle.get_result_async()
        spin_while(lambda: not get_result_future.done())
        result_wrapper = get_result_future.result()

        if result_wrapper.status != GoalStatus.STATUS_SUCCEEDED:
            raise RuntimeError(f'NavigateToPose failed with status code: {result_wrapper.status}')
        emit('GOAL_COMPLETED_STATUS_SUCCEEDED', status=result_wrapper.status)

        # Step 7: Verify final destination via odometry and AMCL
        final_odom_p = odom_msg.pose.pose.position
        final_amcl_p = amcl_msg.pose.pose.position
        dist_odom = math.hypot(final_odom_p.x - goal_cfg['pose'][0], final_odom_p.y - goal_cfg['pose'][1])
        dist_amcl = math.hypot(final_amcl_p.x - goal_cfg['pose'][0], final_amcl_p.y - goal_cfg['pose'][1])

        emit('DESTINATION_REACHED',
             odom_x=final_odom_p.x, odom_y=final_odom_p.y, distance_to_goal_odom_m=dist_odom,
             amcl_x=final_amcl_p.x, amcl_y=final_amcl_p.y, distance_to_goal_amcl_m=dist_amcl)

        if dist_odom > goal_cfg['xy_tolerance_m'] and dist_amcl > goal_cfg['xy_tolerance_m']:
            raise ValueError(f'Final position too far from goal: odom_err={dist_odom:.4f}m, amcl_err={dist_amcl:.4f}m, tol={goal_cfg["xy_tolerance_m"]}m')

        # Step 8: Measure scan rate and container resource stats
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

        emit('B2_PASS',
             token=os.environ['DDS_TEST_PAYLOAD'],
             final_distance_m=min(dist_odom, dist_amcl),
             scan_rate_hz=measured_scan_hz)
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
