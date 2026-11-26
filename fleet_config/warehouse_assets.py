"""Generate Fortress SDF, occupancy map, and per-robot Nav2 parameters from one fleet profile."""
import argparse
from decimal import Decimal
import json
import re
from itertools import product
from math import pi
from pathlib import Path
import sys
import tempfile
from xml.etree import ElementTree as ET

import yaml

from fleet_config import load_config
from fleet_config.obstacle_sensors import (
    compose, install_sensors, configure_observations, pose, shape_bound, validate_clear_fov,
)
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


def configure_peer_observations(params, config, robot, radii):
    """Opt-in experiment: reuse geometry and timing from the validated profile.

    This observes occupancy, not another traffic scheduler or movement permit.
    The default launcher deliberately does not opt into unqualified behavior.
    """
    safety = config.fleet.perception_safety
    if safety is None:
        raise ValueError("peer observation experiment requires explicit perception_safety")
    amcl = params["amcl"]["ros__parameters"]
    for layer in ("local_costmap", "global_costmap"):
        cost = params[layer][layer]["ros__parameters"]
        cost["plugins"].insert(cost["plugins"].index("inflation_layer"), "peer_robot_layer")
        cost["peer_robot_layer"] = dict(
            plugin="fleet_perception::PeerRobotLayer", self_id=robot.id,
            map_frame=amcl["global_frame_id"], robot_ids=[r.id for r in config.robots],
            tf_topics=[r.namespace + "/tf" for r in config.robots],
            radii=[radii[r.id] for r in config.robots],
            pose_age_sec=safety.odometry_freshness_sec,
            transport_sec=safety.transport_sec,
            localization_age_sec=safety.observation_age_sec,
            future_tolerance_sec=amcl["transform_tolerance"],
        )


def projected_collision_hull(model):
    """Enclose the projection of all SDF collision shapes, including sensor housings."""
    points = set()
    for link in model.findall("link"):
        for collision in link.findall("collision"):
            center, matrix = compose(pose(link), pose(collision))
            _, bounds = shape_bound(collision.find("geometry"), center, matrix)
            points.update(product(*bounds[:2]))

    def half_hull(ordered):
        hull = []
        for point in ordered:
            while len(hull) > 1:
                a, b = hull[-2:]
                if (b[0] - a[0]) * (point[1] - a[1]) > (b[1] - a[1]) * (point[0] - a[0]):
                    break
                hull.pop()
            hull.append(point)
        return hull[:-1]

    ordered = sorted(points)
    hull = half_hull(ordered) + half_hull(reversed(ordered))
    if len(hull) < 3:
        raise ValueError("Recovery requires a physical collision footprint")
    return [coordinate for point in hull for coordinate in point]


def configure_escape(params, config, robot, out, radius, radii, hulls):
    local = params["local_costmap"]["local_costmap"]["ros__parameters"]
    global_cost = params["global_costmap"]["global_costmap"]["ros__parameters"]
    footprint = local.get("robot_radius")
    if (not footprint or footprint != global_cost.get("robot_radius") or
            radius + footprint + local["resolution"] >= min(local["width"], local["height"]) / 2):
        raise ValueError(f"{robot.id}: escape radius and footprint must fit the local costmap")
    for costmap in (local, global_cost):
        if costmap["plugins"][-2:] != ["peer_robot_layer", "inflation_layer"]:
            raise ValueError("Clearance requires the peer layer after all static and sensor layers")
        costmap["peer_robot_layer"]["publish_recovery_costmap"] = True
    navigator = params["bt_navigator"]["ros__parameters"]
    tree = ET.parse(ROOT / "config/navigate-to-pose-escape.xml")
    escape = tree.find(".//FleetEscape")
    physical_topics = [r.namespace + "/physical_pose" for r in config.robots]
    physical_radii = [radii[r.id] for r in config.robots]
    self_index = next(i for i, r in enumerate(config.robots) if r.id == robot.id)
    physical_hulls = [";".join(map(str, hulls[r.id])) for r in config.robots]
    controller = params["controller_server"]["ros__parameters"]
    controller["controller_plugins"].append("FleetClearance")
    controller["FleetClearance"] = dict(
        plugin="fleet_nav2_escape::ClearanceController", physical_topics=physical_topics,
        radii=physical_radii, self_index=self_index, physical_hulls=physical_hulls,
    )
    controller["goal_checker_plugins"].append("clearance_goal_checker")
    controller["clearance_goal_checker"] = dict(
        plugin="nav2_controller::StoppedGoalChecker", stateful=False, xy_goal_tolerance=0.05,
        yaw_goal_tolerance=0.18, trans_stopped_velocity=0.01, rot_stopped_velocity=0.01,
    )
    escape.attrib.update(radius=str(radius), footprint=str(footprint),
                         physical_topics=";".join(physical_topics),
                         physical_radii=";".join(map(str, physical_radii)), self_index=str(self_index),
                         physical_hulls="|".join(physical_hulls),
                         base_frame=navigator["robot_base_frame"], odom_topic=navigator["odom_topic"],
                         # A Docker Desktop host bind mount does not serialize flock.
                         lease="/tmp/fleet-nav2-escape.lock")
    bt_path = out.resolve() / f"escape-{robot.id}.xml"
    tree.write(bt_path, encoding="utf-8")
    navigator["default_nav_to_pose_bt_xml"] = str(bt_path)
    navigator["plugin_lib_names"].append("fleet_escape_bt_nodes")


def generate(path, out, scenario="delivery", *, peer_awareness=False, warehouse_escape=False):
    config = load_config(path)
    layout = config.warehouse
    if layout is None:
        raise ValueError("fleet profile has no warehouse")
    escape_radius = config.fleet.nav2_escape_radius_m if warehouse_escape else None
    if escape_radius is not None and not peer_awareness:
        raise ValueError("warehouse escape requires peer costmap observations")
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
    envelope_evidence = []
    radii = {}
    for robot in config.robots:
        raw = yaml.safe_load(re.sub(r'@[A-Z_]+@', '0', (path.parent/robot.nav2_params_path).read_text()))
        radius = raw['local_costmap']['local_costmap']['ros__parameters'].get('robot_radius')
        global_radius = raw['global_costmap']['global_costmap']['ros__parameters'].get('robot_radius')
        if peer_awareness:
            if radius != global_radius or radius is None or radius <= 0:
                raise ValueError('peer observations require matching explicit Nav2 robot_radius')
            radii[robot.id] = float(radius)
            # Verify the generated collision assembly, including sensor housings,
            # is enclosed; a convenient Nav2 radius alone is not geometry proof.
            if robot.obstacle_sensor_model is None:
                model = tree.find(f'.//model[@name="{robot.id}"]')
                for link in model.findall('link'):
                    for collision in link.findall('collision'):
                        center, matrix = compose(pose(link), pose(collision))
                        bound, _ = shape_bound(collision.find('geometry'), center, matrix)
                        if bound > radius:
                            raise ValueError(f'{robot.id}: collision exceeds peer radius')
        if robot.obstacle_sensor_model is not None:
            if radius != global_radius or radius is None:
                raise ValueError('obstacle assembly requires matching explicit Nav2 robot_radius')
            envelope_evidence += install_sensors(tree, config, robot, radius)
            validate_clear_fov(tree, config, robot)
    (out/'sensor-envelope.json').write_text(json.dumps(envelope_evidence,indent=2)+'\n')
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

    hulls = {robot.id: projected_collision_hull(tree.find(f'.//model[@name="{robot.id}"]'))
             for robot in config.robots} if escape_radius is not None else {}
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
        configured_robot = next(r for r in config.robots if r.id == name)
        configure_observations(params, config, configured_robot)
        if peer_awareness:
            configure_peer_observations(params, config, configured_robot, radii)
        if escape_radius is not None:
            configure_escape(params, config, configured_robot, out, escape_radius, radii, hulls)
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
