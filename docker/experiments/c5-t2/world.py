"""Isolated T2 world: existing native zero-only driver and explicit BT observer."""
import importlib.util
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('native_zero_world', ROOT/'docker/experiments/c5-b6b7/server.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
original = native.server.generate


def generate(*args, **kwargs):
    cfg = original(*args, **kwargs)
    output = args[1]
    for robot in cfg.robots:
        path = output / ('nav2-'+robot.id+'.yaml')
        params = yaml.safe_load(path.read_text())
        params['bt_navigator']['ros__parameters']['plugin_lib_names'].append('fleet_observed_follow_path_bt_node')
        path.write_text(yaml.safe_dump(params, sort_keys=False))
    return cfg


native.server.generate = generate
if __name__ == '__main__':
    raise SystemExit(native.server.main())
