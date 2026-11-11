"""Generate Fortress SDF, occupancy map, and per-robot Nav2 parameters from one fleet profile."""
import argparse
from decimal import Decimal
import json
from math import pi
from pathlib import Path
import sys
import tempfile
from xml.etree import ElementTree as ET

import yaml

from fleet_config import load_config
from fleet_config.occupancy import encode_grid, raster

ROOT = Path(__file__).resolve().parents[1]
for component in ("simulation-c3-3-3", "simulation-c4-4"):
    sys.path.insert(0, str(ROOT / "docker" / component))
from check import prepare_world
from dock_world import install_docks


def blocks(layout):
    return layout.obstacles()


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


def make_map(layout, out):
    metadata, cells = raster(layout)
    resolution = metadata["resolution"]
    x0, y0 = metadata["origin"]
    cols, rows = metadata["width"], metadata["height"]
    image = bytearray(0 if value else 254 for row in range(rows-1, -1, -1)
                      for value in cells[row*cols:(row+1)*cols])
    (out / "map.pgm").write_bytes(f"P5\n{cols} {rows}\n255\n".encode() + image)
    (out / "map.yaml").write_text(yaml.safe_dump(dict(
        image="map.pgm", mode="trinary", resolution=resolution, origin=[x0,y0,0.0],
        negate=0, occupied_thresh=.65, free_thresh=.25,
    ), sort_keys=False))
    (out / "occupancy.json").write_text(json.dumps(encode_grid(metadata, cells, "generated_occupancy")))
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
    elif scenario == "routes":
        goals = {task.id: task.model_dump() for task in layout.example_tasks}
    else:
        dock = next(item for item in config.stations.charging_stations if item.id == "dock_1")
        delivery = next(point for point in layout.transfer_points
                        if point.kind == "dropoff" and point.id in {"delivery-01", "delivery_1"})
        goals = {
            config.robots[0].id: dock.pose.model_dump(),
            config.robots[1].id: delivery.pose.model_dump(),
        }
    solids = list(blocks(layout))
    resolution = make_map(layout, out)
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
    tree = ET.parse(sdf)
    for robot in config.robots:
        model = tree.getroot().find(f".//model[@name='{robot.id}']")
        for link in model.findall("link"):
            for collision in link.findall("collision"):
                sensor = ET.SubElement(link, "sensor", name="acceptance_contact_" + collision.get("name"), type="contact")
                ET.SubElement(sensor, "always_on").text = "true"
                contact = ET.SubElement(sensor, "contact")
                ET.SubElement(contact, "collision").text = collision.get("name")
                ET.SubElement(contact, "topic").text = robot.namespace + '/contact_' + link.get("name")
    tree.write(sdf, encoding="utf-8", xml_declaration=True)

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
    parser.add_argument("--scenario", choices=("delivery", "passing", "routes"), default="delivery")
    args = parser.parse_args()
    generate(args.profile, args.output, args.scenario)
