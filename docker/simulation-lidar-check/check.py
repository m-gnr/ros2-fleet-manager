"""Real lidar decision gate; reuse the unchanged Stage A robot and config."""
import json
import math
import os
from pathlib import Path
import sys
import time
import signal
import subprocess
import xml.etree.ElementTree as ET
from string import Template

import importlib.util

_spec = importlib.util.spec_from_file_location('stage_a_check', '/opt/simulation-check/check.py')
stage_a = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage_a)
import jsonschema


def load_config():
    base, timeout = stage_a.load_config()
    config = json.loads(Path('/config/simulation-lidar-check.json').read_text())
    schema = json.loads(Path('/config/simulation-lidar-check.schema.json').read_text())
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(config, schema)
    def finite(value):
        if isinstance(value, dict):
            return all(finite(v) for v in value.values())
        if isinstance(value, list):
            return all(finite(v) for v in value)
        return not isinstance(value, (float, int)) or math.isfinite(value)
    if not finite(config):
        raise ValueError('All lidar config numbers must be finite')
    s = config['sensor']
    if not s['min_range_m'] < s['max_range_m'] or not s['min_angle_rad'] < s['max_angle_rad']:
        raise ValueError('Sensor minimum must be below maximum')
    # The analytic wall oracle requires aligned, stationary geometry.
    if any(base['robot']['initial_pose'][3:]) or any(s['pose'][3:]) or any(config['wall']['pose'][3:]):
        raise ValueError('B1 wall oracle requires zero initial and sensor/wall rotation')
    return base, config, timeout


def prepare_world(base, config):
    root = ET.fromstring(Template((stage_a.ROOT / 'world.sdf.in').read_text()).substitute(
        robot_name=base['robot']['name'], namespace=base['robot']['namespace'],
        initial_pose=' '.join(map(str, base['robot']['initial_pose']))))
    world = root.find('world')
    plugin = ET.SubElement(world, 'plugin', filename='ignition-gazebo-sensors-system', name='ignition::gazebo::systems::Sensors')
    ET.SubElement(plugin, 'render_engine').text = config['render']['engine']
    wall = ET.SubElement(world, 'model', name='lidar_wall')
    ET.SubElement(wall, 'static').text = 'true'
    ET.SubElement(wall, 'pose').text = ' '.join(map(str, config['wall']['pose']))
    link = ET.SubElement(wall, 'link', name='wall')
    for tag in ('collision', 'visual'):
        shape = ET.SubElement(link, tag, name='wall')
        box = ET.SubElement(ET.SubElement(shape, 'geometry'), 'box')
        ET.SubElement(box, 'size').text = ' '.join(map(str, config['wall']['size_m']))
    body = world.find("model[@name='%s']/link[@name='base_link']" % base['robot']['name'])
    sensor = ET.SubElement(body, 'sensor', name='lidar', type='gpu_lidar')
    s = config['sensor']
    ET.SubElement(sensor, 'pose').text = ' '.join(map(str, s['pose']))
    ET.SubElement(sensor, 'topic').text = '/' + base['robot']['namespace'] + '/scan'
    ET.SubElement(sensor, 'update_rate').text = str(s['update_rate_hz'])
    ET.SubElement(sensor, 'always_on').text = 'true'
    lidar = ET.SubElement(sensor, 'lidar')
    horizontal = ET.SubElement(ET.SubElement(lidar, 'scan'), 'horizontal')
    for tag, key in [('samples','samples'),('min_angle','min_angle_rad'),('max_angle','max_angle_rad')]:
        ET.SubElement(horizontal, tag).text = str(s[key])
    ranges = ET.SubElement(lidar, 'range')
    for tag, key in [('min','min_range_m'),('max','max_range_m'),('resolution','resolution_m')]:
        ET.SubElement(ranges, tag).text = str(s[key])
    Path('/tmp/lidar-world.sdf').write_text(ET.tostring(root, encoding='unicode'))


def backend(base, config, timeout):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from rclpy.utilities import get_rmw_implementation_identifier
    rclpy.init()
    node = rclpy.create_node('lidar_probe')
    messages = []
    node.create_subscription(LaserScan, '/' + base['robot']['namespace'] + '/scan', messages.append, qos_profile_sensor_data)
    stage_a.emit('BACKEND_START', rmw=get_rmw_implementation_identifier())
    deadline = time.monotonic() + timeout
    previous = None
    count = 0
    try:
        while count < config['check']['minimum_messages']:
            if time.monotonic() >= deadline:
                raise RuntimeError(f'Lidar deadline exceeded; received={count}')
            rclpy.spin_once(node, timeout_sec=0.1)
            while messages:
                msg = messages.pop(0)
                stamp = msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9
                if previous is not None and stamp <= previous:
                    raise ValueError('Scan timestamps did not increase')
                previous = stamp
                s = config['sensor']
                if len(msg.ranges) != s['samples']:
                    raise ValueError('Unexpected scan sample count')
                wall = config['wall']
                origin = [base['robot']['initial_pose'][i] + s['pose'][i] for i in range(3)]
                distance = wall['pose'][0] - wall['size_m'][0]/2 - origin[0]
                errors = []
                for i, value in enumerate(msg.ranges):
                    angle = msg.angle_min + i * msg.angle_increment
                    expected = distance / math.cos(angle)
                    hit_y = origin[1] + distance * math.tan(angle)
                    if distance <= 0 or abs(hit_y-wall['pose'][1]) >= wall['size_m'][1]/2:
                        raise ValueError('Configured wall does not cover scan rays')
                    if not math.isfinite(value) or not s['min_range_m'] <= value <= s['max_range_m']:
                        raise ValueError('Nonfinite or out of range lidar return')
                    errors.append(abs(value-expected))
                stage_a.emit('SCAN', count=count+1, stamp=stamp, frame=msg.header.frame_id,
                             samples=len(msg.ranges), minimum=min(msg.ranges), maximum=max(msg.ranges), max_wall_error_m=max(errors))
                if max(errors) > config['check']['range_tolerance_m']:
                    raise ValueError('Scan inconsistent with actual wall geometry')
                count += 1
        stage_a.emit('B1_PASS', messages=count, token=os.environ['DDS_TEST_PAYLOAD'])
        return 0
    finally:
        node.destroy_node()
        stage_a.emit('SCAN_SUMMARY', validated_messages=count, queued_messages=len(messages))
        if rclpy.ok():
            rclpy.shutdown()


def main():
    try:
        base, config, timeout = load_config()
        stage_a.emit('CONFIG_VALID', role=os.environ['SIM_CHECK_ROLE'])
        if os.environ['SIM_CHECK_ROLE'] == 'backend':
            return backend(base, config, timeout)
        prepare_world(base, config)
        return simulation(base)
    except Exception as error:
        stage_a.emit('FAIL', error=str(error), error_type=type(error).__name__)
        return 1

def simulation(config):
    ns = '/' + config['robot']['namespace']
    # The runtime package ships the ABI soname, not the unversioned dev alias.
    engines = list(Path('/usr/lib').glob('*/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5'))
    if len(engines) != 1:
        raise RuntimeError(f'Expected one packaged Fortress DART engine, found {engines}')
    commands = [
        ['ign', 'gazebo', '-s', '-r', '-v', '4', '--headless-rendering', '--physics-engine', str(engines[0]), '/tmp/lidar-world.sdf'],
        ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
         ns + '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
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
            stage_a.emit('PROCESS_START', command=command)
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
                stage_a.emit('FORCED_KILL', command=child.args)
            stage_a.emit('PROCESS_EXIT', command=child.args, code=child.returncode)


if __name__ == "__main__":
    sys.exit(main())
