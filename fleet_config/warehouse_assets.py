"""Generate Fortress SDF, occupancy map, and per-robot Nav2 parameters from one fleet profile."""
import argparse
from decimal import Decimal
import json
from math import isclose, pi
from pathlib import Path
import sys
import tempfile
from xml.etree import ElementTree as ET

import yaml

from fleet_config import load_config

ROOT = Path(__file__).resolve().parents[1]
for component in ("simulation-c3-3-3", "simulation-c4-4"):
    sys.path.insert(0, str(ROOT / "docker" / component))
from check import prepare_world
from dock_world import install_docks


def blocks(layout):
    for wall in layout.walls():
        yield wall["id"], wall["bounds"], layout.wall_height_m
    for rack in layout.racks:
        yield rack.id, rack.bounds, rack.height


def static_box(world, name, x, y, z, width, depth, height, color):
    model = ET.SubElement(world, "model", name=name)
    ET.SubElement(model, "static").text = "true"
    ET.SubElement(model, "pose").text = f"{x} {y} {z} 0 0 0"
    link = ET.SubElement(model, "link", name="geometry")
    for kind in ("collision", "visual"):
        item = ET.SubElement(link, kind, name=kind)
        ET.SubElement(ET.SubElement(ET.SubElement(item, "geometry"), "box"), "size").text = f"{width} {depth} {height}"
        if kind == "visual":
            mat = ET.SubElement(item, "material")
            ET.SubElement(mat, "ambient").text = color
            ET.SubElement(mat, "diffuse").text = color


def make_map(layout, solids, out):
    b = layout.bounds
    resolution = next((value for value in (.05, .025, .01, .005)
                       if all(isclose(edge / value, round(edge / value), abs_tol=1e-7)
                              for _, bounds, _ in solids
                              for edge in (bounds.x_min, bounds.x_max, bounds.y_min, bounds.y_max))), None)
    if resolution is None:
        raise ValueError("wall/rack edges must align exactly with a supported map resolution")
    # Exterior apron has a physical floor. Cells beyond it stay occupied to bound planning.
    border = 1.5
    x0, y0 = b.x_min-border, b.y_min-border
    cols, rows = round((b.x_max-b.x_min+2*border)/resolution), round((b.y_max-b.y_min+2*border)/resolution)
    if rows * cols > 4_000_000:
        raise ValueError("generated occupancy image exceeds 4 million cells")
    image = bytearray([254]) * (cols*rows)
    for _, rect, _ in solids:
        left, right = (round((x-x0)/resolution) for x in (rect.x_min, rect.x_max))
        bottom, top = (round((y-y0)/resolution) for y in (rect.y_min, rect.y_max))
        for row in range(rows-top, rows-bottom):
            image[row*cols+left:row*cols+right] = bytes(right-left)
    (out / "map.pgm").write_bytes(f"P5\n{cols} {rows}\n255\n".encode() + image)
    (out / "map.yaml").write_text(yaml.safe_dump(dict(
        image="map.pgm", mode="trinary", resolution=resolution, origin=[x0,y0,0.0],
        negate=0, occupied_thresh=.65, free_thresh=.25,
    ), sort_keys=False))
    return resolution


def passing(config):
    aisle = next(aisle for aisle in config.warehouse.aisles if aisle.id == "aisle_c").bounds
    step = config.warehouse.grid_m
    lane_s = round((aisle.y_min+.5)/step)*step
    lane_n = round((aisle.y_max-.5)/step)*step
    left, right = max(-3.5, aisle.x_min+1), min(3.5, aisle.x_max-1)
    return [(dict(x=left,y=lane_s,yaw=0.0),dict(x=right,y=lane_s,yaw=0.0)),
            (dict(x=right,y=lane_n,yaw=pi),dict(x=left,y=lane_n,yaw=pi))]


def generate(path, out, scenario="delivery"):
    config = load_config(path)
    layout = config.warehouse
    if layout is None:
        raise ValueError("fleet profile has no warehouse")
    out.mkdir(parents=True, exist_ok=True)
    data = config.model_dump()
    if scenario == "passing":
        pairs = passing(config)
        for robot, (start, _) in zip(data["robots"], pairs, strict=True):
            robot["initial_pose"] = start
        goals = {robot["id"]: goal for robot, (_, goal) in zip(data["robots"], pairs, strict=True)}
    else:
        dock = next(item for item in config.stations.charging_stations if item.id == "dock_1")
        delivery = next(point for point in layout.transfer_points
                        if point.kind == "dropoff" and point.id in {"delivery-01", "delivery_1"})
        goals = {
            config.robots[0].id: dock.pose.model_dump(),
            config.robots[1].id: delivery.pose.model_dump(),
        }
    solids = list(blocks(layout))
    resolution = make_map(layout, solids, out)
    settings = json.loads((ROOT / "config/simulation-c3-3-3.json").read_text())
    with tempfile.TemporaryDirectory() as folder:
        original = prepare_world(settings, data, Path(folder) / "robots.sdf")
        tree = ET.parse(original)
    world = tree.getroot().find("world")
    world.set("name", "warehouse_grid")
    for name in ("floor","north_wall","south_wall","east_wall","west_wall"):
        world.remove(world.find(f"model[@name='{name}']"))
    b = layout.bounds
    width, depth = b.x_max-b.x_min, b.y_max-b.y_min
    static_box(world, "floor", (b.x_min+b.x_max)/2, (b.y_min+b.y_max)/2, -.05,
               width+3, depth+3, .10, ".76 .81 .84 1")
    for name, r, height in solids:
        static_box(world, name, (r.x_min+r.x_max)/2, (r.y_min+r.y_max)/2, height/2,
                   float(Decimal(str(r.x_max))-Decimal(str(r.x_min))),
                   float(Decimal(str(r.y_max))-Decimal(str(r.y_min))), height, ".49 .58 .65 1")
    sdf = out / "warehouse.sdf"
    tree.write(sdf, encoding="utf-8", xml_declaration=True)
    install_docks(sdf, config.stations.charging_stations, config.robots)

    for robot in data["robots"]:
        name, ns, start = robot["id"], robot["namespace"], robot["initial_pose"]
        text = (path.parent / robot["nav2_params_path"]).read_text()
        for field, value in dict(BASE_FRAME=f"{name}/base_link", ODOM_FRAME=f"{name}/odom",
                                 SCAN_TOPIC=f"{ns}/scan", ODOM_TOPIC=f"{ns}/odom",
                                 INIT_X=start["x"], INIT_Y=start["y"], INIT_YAW=start["yaw"], INIT_Z=0.0).items():
            text = text.replace(f"@{field}@", str(value))
        params = yaml.safe_load(text)
        params["map_server"]["ros__parameters"]["yaml_filename"] = str(out.resolve() / "map.yaml")
        for layer in ("local_costmap", "global_costmap"):
            cost = params[layer][layer]["ros__parameters"]
            cost["resolution"] = resolution
            if "static_layer" not in cost:
                cost["plugins"].insert(0, "static_layer")
                cost["static_layer"] = {"plugin":"nav2_costmap_2d::StaticLayer",
                                        "map_subscribe_transient_local":True}
        (out / f"nav2-{name}.yaml").write_text(yaml.safe_dump(params, sort_keys=False))
    (out / "scene.json").write_text(json.dumps(layout.scene_payload(), ensure_ascii=False, indent=2)+"\n")
    (out / "goals.json").write_text(json.dumps(goals, indent=2)+"\n")
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scenario", choices=("delivery","passing"), default="delivery")
    args = parser.parse_args()
    generate(args.profile, args.output, args.scenario)
