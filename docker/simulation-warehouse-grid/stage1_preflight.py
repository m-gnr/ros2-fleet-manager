"""Read-only startup checks; never start ROS nodes or Gazebo."""
import importlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import xml.etree.ElementTree as ET


def preflight(args, commands):
    # Match child startup: Python sys.path and the ELF loader read the sourced
    # environment only in a fresh process. No ROS node is instantiated.
    payload = dict(profile=str(args.profile), output=str(args.output),
                   api_port=args.api_port, scene_port=args.scene_port, commands=commands)
    subprocess.run([sys.executable, __file__, json.dumps(payload)], check=True, timeout=90)


def _preflight(args, commands):
    report = dict(result='FAIL', commands=dict(commands), checks=[])
    target = args.output / 'preflight.json'
    try:
        schema = Path('config/fleet.schema.json').resolve(strict=True)
        from fleet_config import load_config
        load_config(args.profile, schema_path=schema)
        report['schema'] = str(schema)
        report['checks'].append('canonical schema and profile')
        from ament_index_python.packages import get_package_prefix
        prefix = Path(get_package_prefix('fleet_perception'))
        marker = prefix / 'share/ament_index/resource_index/nav2_costmap_2d__pluginlib__plugin/fleet_perception'
        xml = prefix / marker.read_text().strip()
        root = ET.parse(xml).getroot()
        if not any(c.get('type') == 'fleet_perception::ObservedObstacleLayer' for c in root.iter('class')):
            raise ValueError('ObservedObstacleLayer plugin registration missing')
        library = prefix / 'lib' / ('lib' + root.get('path') + '.so')
        # A fresh interpreter sees the sourced LD_LIBRARY_PATH at dynamic-loader startup.
        subprocess.run([sys.executable, "-c",
                        "import ctypes, sys; ctypes.CDLL(sys.argv[1])", str(library)],
                       check=True, timeout=15)
        report['plugin'] = dict(prefix=str(prefix), xml=str(xml), library=str(library))
        report['checks'].append('ROS overlay, plugin registration and shared library dependencies')
        modules = ['uvicorn', 'websockets', 'fleet_robot_executor.node',
                   'fleet_battery_simulator.node', 'backend.dashboard.runtime',
                   'backend.dashboard.api', 'backend.fleet_manager.adapters.ros2_adapter_node',
                   'fleet_interfaces.msg', 'fleet_interfaces.srv', 'fleet_interfaces.action']
        for module in modules:
            importlib.import_module(module)
        for script in ['docker/simulation-warehouse-grid/serve.py',
                       'docker/simulation-warehouse-grid/stage1_observer.py',
                       'docker/simulation-warehouse-grid/peer_costmap_probe.py',
                       'fleet-visualizer/bridge/run.py']:
            runpy.run_path(script, run_name='preflight_import')
        report['checks'].append('all child and peer probe Python imports')
        # Ask the actual child parsers to validate the planned flags, without starting nodes.
        for name, command in commands:
            if name.startswith(('battery_', 'executor_')):
                if str(args.profile) not in command and 'fleet_config_path:='+str(args.profile) not in command:
                    raise ValueError(f'{name}: profile argument missing')
                continue
            result = subprocess.run(command + ['--help'], capture_output=True, text=True, timeout=15)
            if result.returncode:
                raise RuntimeError(f'{name} argument/import check: {result.stderr}')
            flags = [item.split('=')[0] for item in command if item.startswith('--')]
            if any(flag not in result.stdout for flag in flags):
                raise ValueError(f'{name}: unsupported startup argument')
        from fleet_robot_executor.config_loader import load_all_robots_from_fleet
        load_all_robots_from_fleet(args.profile)
        for port in (args.api_port, args.scene_port):
            if not 1 <= int(port) <= 65535:
                raise ValueError('Invalid startup port')
        if args.api_port == args.scene_port:
            raise ValueError('API and scene ports must differ')
        report['checks'].append('planned child arguments and Executor profile reader')
        report['result'] = 'PASS'
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        target.write_text(json.dumps(report, indent=2)+'\n')
        print('PREFLIGHT '+report['result'], flush=True)


if __name__ == '__main__':
    from types import SimpleNamespace
    payload = json.loads(sys.argv[1])
    commands = payload.pop('commands')
    payload['profile'] = Path(payload['profile'])
    payload['output'] = Path(payload['output'])
    _preflight(SimpleNamespace(**payload), commands)
