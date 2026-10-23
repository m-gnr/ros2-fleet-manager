"""Stage A validation harness; no application lifecycle policy."""
import json
import math
import os
from pathlib import Path
import signal
from string import Template
import subprocess
import sys
import time

import jsonschema

ROOT = Path(__file__).parent


def emit(event, **values):
    print(json.dumps(dict(event=event, **values)), flush=True)


def load_config():
    config = json.loads(Path('/config/simulation-check.json').read_text())
    schema = json.loads(Path('/config/simulation-check.schema.json').read_text())
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(config, schema)
    numbers = config['robot']['initial_pose'] + list(config['probe'].values())
    if not all(math.isfinite(v) for v in numbers):
        raise ValueError('All numeric config fields must be finite')
    if config['probe']['maximum_distance_m'] <= config['probe']['minimum_distance_m']:
        raise ValueError('maximum_distance_m must exceed minimum_distance_m')
    timeout = float(os.environ['DDS_TEST_TIMEOUT_SECONDS'])
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('DDS_TEST_TIMEOUT_SECONDS must be positive and finite')
    if not 0 <= int(os.environ['ROS_DOMAIN_ID']) <= 232:
        raise ValueError('ROS_DOMAIN_ID must be in 0..232')
    if os.environ['ROS_LOCALHOST_ONLY'] != '0':
        raise ValueError('ROS_LOCALHOST_ONLY must be 0 for this cross-container test')
    if not os.environ['DDS_TEST_PAYLOAD'].strip():
        raise ValueError('DDS_TEST_PAYLOAD must identify the run')
    if os.environ['SIM_CHECK_ROLE'] not in ('simulation', 'backend'):
        raise ValueError('SIM_CHECK_ROLE must be simulation or backend')
    return config, timeout


def simulation(config):
    robot = config['robot']
    world = Template((ROOT / 'world.sdf.in').read_text()).substitute(
        robot_name=robot['name'], namespace=robot['namespace'],
        initial_pose=' '.join(map(str, robot['initial_pose'])))
    Path('/tmp/validation-world.sdf').write_text(world)
    ns = '/' + robot['namespace']
    # The runtime package ships the ABI soname, not the unversioned dev alias.
    engines = list(Path('/usr/lib').glob('*/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5'))
    if len(engines) != 1:
        raise RuntimeError(f'Expected one packaged Fortress DART engine, found {engines}')
    commands = [
        ['ign', 'gazebo', '-s', '-r', '-v', '3', '--physics-engine', str(engines[0]), '/tmp/validation-world.sdf'],
        ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
         '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
         ns + '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
         ns + '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist'],
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
                    raise RuntimeError(f'Child {child.args} exited unexpectedly: {child.returncode}')
            time.sleep(0.1)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGINT)
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                emit('FORCED_KILL', command=child.args)
            emit('PROCESS_EXIT', command=child.args, code=child.returncode)


def backend(config, timeout):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from rclpy.utilities import get_rmw_implementation_identifier
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from rosgraph_msgs.msg import Clock

    rclpy.init()
    ns = '/' + config['robot']['namespace']
    node = rclpy.create_node('motion_probe', namespace=ns)
    publisher = node.create_publisher(Twist, ns + '/cmd_vel', 10)
    odom = None
    clock = None
    count = 0

    def receive_odom(msg):
        nonlocal odom, count
        odom = msg
        count += 1

    def receive_clock(msg):
        nonlocal clock
        clock = msg.clock.sec + msg.clock.nanosec / 1e9

    node.create_subscription(Odometry, ns + '/odom', receive_odom, qos_profile_sensor_data)
    node.create_subscription(Clock, '/clock', receive_clock, qos_profile_sensor_data)
    deadline = time.monotonic() + timeout

    def spin_until(predicate, velocity=0.0):
        while not predicate():
            if time.monotonic() > deadline:
                raise RuntimeError('Validation deadline exceeded; missing clock/odometry/motion evidence')
            msg = Twist()
            msg.linear.x = velocity
            publisher.publish(msg)
            rclpy.spin_once(node, timeout_sec=0.05)

    def snapshot():
        p = odom.pose.pose.position
        return dict(x=p.x, y=p.y, z=p.z, clock=clock,
                    odom_stamp=odom.header.stamp.sec + odom.header.stamp.nanosec / 1e9,
                    frame=odom.header.frame_id, child_frame=odom.child_frame_id, samples=count)

    try:
        emit('BACKEND_START', namespace=ns, rmw=get_rmw_implementation_identifier())
        spin_until(lambda: odom is not None and clock is not None and publisher.get_subscription_count() > 0)
        probe = config['probe']
        start_clock = clock
        spin_until(lambda: clock - start_clock >= probe['settle_seconds'])
        before = snapshot()
        emit('BEFORE', **before)
        spin_until(lambda: clock - before['clock'] >= probe['drive_seconds'], probe['linear_velocity_mps'])
        end_clock = clock
        spin_until(lambda: clock - end_clock >= probe['settle_seconds'])
        after = snapshot()
        distance = math.hypot(after['x'] - before['x'], after['y'] - before['y'])
        emit('AFTER', **after, distance_m=distance)
        assert all(math.isfinite(v) for v in (before['x'], before['y'], after['x'], after['y'], distance))
        assert before['frame'] == after['frame'] == ns[1:] + '/odom'
        assert before['child_frame'] == after['child_frame'] == ns[1:] + '/base_link'
        assert after['odom_stamp'] > before['odom_stamp'] and after['samples'] > before['samples']
        assert probe['minimum_distance_m'] <= distance <= probe['maximum_distance_m'], 'Displacement out of configured bounds'
        emit('PASS', token=os.environ['DDS_TEST_PAYLOAD'], distance_m=distance,
             clock_advance_seconds=after['clock'] - before['clock'])
        return 0
    finally:
        publisher.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


def main():
    try:
        config, timeout = load_config()
        emit('CONFIG_VALID', role=os.environ['SIM_CHECK_ROLE'], token=os.environ['DDS_TEST_PAYLOAD'])
        return simulation(config) if os.environ['SIM_CHECK_ROLE'] == 'simulation' else backend(config, timeout)
    except Exception as error:
        emit('FAIL', error=str(error), error_type=type(error).__name__)
        return 1


if __name__ == '__main__':
    sys.exit(main())
