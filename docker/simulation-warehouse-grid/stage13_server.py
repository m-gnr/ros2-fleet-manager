"""Isolated single-variable AMCL and subtractive landmark experiments."""
import json
import os
import yaml
import serve
from fleet_config.warehouse import WarehouseLayout, MapRectangle

original_generate = serve.generate
original_obstacles = WarehouseLayout.obstacles


def landmark_obstacles(layout):
    # A blind notch stays inside rack_A2's original solid envelope. The south
    # service face and all aisle widths remain intact; there is no through route.
    for name, bounds, height in original_obstacles(layout):
        if name != 'rack_A2':
            yield name, bounds, height
            continue
        yield name + '_south', MapRectangle(x_min=bounds.x_min, x_max=bounds.x_max,
            y_min=bounds.y_min, y_max=bounds.y_max - .5), height
        yield name + '_north', MapRectangle(x_min=bounds.x_min, x_max=bounds.x_max - 1.,
            y_min=bounds.y_max - .5, y_max=bounds.y_max), height


def generate(*args, **kwargs):
    variant = json.loads(os.environ.get('STAGE13_OVERRIDE', '{}'))
    if variant.get('landmark'):
        WarehouseLayout.obstacles = landmark_obstacles
    cfg = original_generate(*args, **kwargs)
    out = args[1]
    change = variant.get('amcl', {})
    if len(change) > 1:
        raise ValueError('Sensitivity runs must change exactly one AMCL parameter')
    for robot in cfg.robots:
        path = out / f'nav2-{robot.id}.yaml'
        params = yaml.safe_load(path.read_text())
        params['amcl']['ros__parameters'].update(change)
        for layer in ('local_costmap', 'global_costmap'):
            assert params[layer][layer]['ros__parameters']['robot_radius'] == .30
        path.write_text(yaml.safe_dump(params, sort_keys=False))
    (out/'experiment.json').write_text(json.dumps(variant, indent=2))
    (out/'solids.json').write_text(json.dumps([
        dict(name=n,bounds=b.model_dump(),height=h) for n,b,h in cfg.warehouse.obstacles()],indent=2))
    return cfg

serve.generate = generate
if __name__ == '__main__':
    raise SystemExit(serve.main())
