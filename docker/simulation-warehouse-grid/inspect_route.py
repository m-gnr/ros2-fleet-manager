"""Measure a Nav2 corridor plan and grid access from the generated warehouse."""
import argparse
import json
from math import hypot
from pathlib import Path
import time

from fleet_config import load_config
from fleet_config.warehouse_assets import blocks


def point_to_segment(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = min(1, max(0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2)) if length2 else 0
    return hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def segment_to_rect(a, b, rect):
    first, last = 0.0, 1.0
    for v, end, lower, upper in (
        (a[0], b[0], rect.x_min, rect.x_max),
        (a[1], b[1], rect.y_min, rect.y_max),
    ):
        delta = end - v
        if delta:
            lo, hi = sorted(((lower - v) / delta, (upper - v) / delta))
            first, last = max(first, lo), min(last, hi)
        elif not lower <= v <= upper:
            first, last = 1.0, 0.0
    if first <= last:
        return 0.0
    distances = [point_to_segment((x, y), a, b) for x in (rect.x_min, rect.x_max)
                 for y in (rect.y_min, rect.y_max)]
    distances.extend(hypot(max(rect.x_min - x, x - rect.x_max, 0),
                           max(rect.y_min - y, y - rect.y_max, 0)) for x, y in (a, b))
    return min(distances)


def closest(a, b, obstacles):
    distance, name = min((segment_to_rect(a, b, rect), name) for name, rect, _ in obstacles)
    return {"m": distance, "obstacle": name}


def measure_layout(config):
    layout = config.warehouse
    racks = [(rack.id, rack.bounds, rack.height) for rack in layout.racks]
    obstacles = list(blocks(layout))
    access = next(a.bounds for a in layout.aisles if a.id == "pickup_access")
    spine = (access.x_min + access.x_max) / 2
    entrance = [layout.bounds.x_min - .65, layout.door.center]
    trunk = [spine, layout.door.center]
    docks = {}
    for dock in config.stations.charging_stations:
        x, y = dock.pose.x, dock.pose.y
        # New profile docks face north. Search the full one-metre-wide lane.
        facing = [(r.y_max, name) for name, r, _ in obstacles
                  if r.x_max > x - .5 and r.x_min < x + .5 and r.y_max < y]
        edge, obstacle = max(facing)
        forward = y - dock.tolerance_radius - edge
        docks[dock.id] = {"center": closest([x, y], [x, y], racks), "approach_from_pad_m": forward,
                          "approach_obstacle": obstacle,
                          "pose": [x, y]}
    pickups = {}
    for bay in layout.transfer_points:
        if bay.kind != "pickup":
            continue
        route = [entrance, trunk, [spine, bay.pose.y], [bay.pose.x, bay.pose.y]]
        minimum = min((closest(a, b, obstacles) for a, b in zip(route, route[1:])), key=lambda d: d["m"])
        pickups[bay.id] = {"route": route, "minimum": minimum}
    return {"docks": docks, "pickups": pickups}


def nav2_route(config):
    from geometry_msgs.msg import PoseStamped
    from lifecycle_msgs.srv import GetState
    from nav2_msgs.action import ComputePathToPose
    import rclpy
    from rclpy.action import ActionClient

    layout = config.warehouse
    access = {a.id: a.bounds for a in layout.aisles}
    north, cross, south = (access[key] for key in ("aisle_a", "aisle_cross_w", "aisle_c"))
    y_a = (north.y_min + north.y_max) / 2
    x_cross = (cross.x_min + cross.x_max) / 2
    y_c = (south.y_min + south.y_max) / 2
    pickup = next(p.pose for p in layout.transfer_points if p.id == "pickup_1")
    delivery = next(p.pose for p in layout.transfer_points if p.id == "delivery-01")
    points = [[pickup.x, pickup.y], [pickup.x + .25, y_a], [x_cross, y_a],
              [x_cross, y_c], [delivery.x - .75, y_c], [delivery.x, delivery.y]]
    names = ["alım bağlantısı", "ana koridor A", "enine geçit 1", "ana koridor C", "teslim bağlantısı"]
    axes = [None, (1, y_a), (0, x_cross), (1, y_c), None]
    obstacles = list(blocks(layout))

    rclpy.init()
    node = rclpy.create_node("warehouse_route_inspection", parameter_overrides=[
        rclpy.parameter.Parameter("use_sim_time", value=True)
    ])
    namespace = config.robots[1].namespace
    client = ActionClient(node, ComputePathToPose, namespace + "/compute_path_to_pose")
    lifecycle = node.create_client(GetState, namespace + "/planner_server/get_state")

    def wait(future, seconds):
        rclpy.spin_until_future_complete(node, future, timeout_sec=seconds)
        if not future.done():
            raise TimeoutError("planner response")
        return future.result()

    def pose(point):
        result = PoseStamped()
        result.header.frame_id = "map"
        result.header.stamp = node.get_clock().now().to_msg()
        result.pose.position.x, result.pose.position.y = point
        result.pose.orientation.w = 1.
        return result

    try:
        if not client.wait_for_server(timeout_sec=90) or not lifecycle.wait_for_service(timeout_sec=10):
            raise TimeoutError("planner unavailable")
        until = time.monotonic() + 40
        while wait(lifecycle.call_async(GetState.Request()), 5).current_state.label != "active":
            if time.monotonic() >= until:
                raise TimeoutError("planner inactive")
            rclpy.spin_once(node, timeout_sec=.25)

        legs, path, below = [], [], []
        for name, a, b, axis in zip(names, points, points[1:], axes):
            goal = ComputePathToPose.Goal(start=pose(a), goal=pose(b), planner_id="GridBased", use_start=True)
            handle = wait(client.send_goal_async(goal), 10)
            if not handle.accepted:
                raise RuntimeError(f"{name}: rejected")
            response = wait(handle.get_result_async(), 20)
            if response.status != 4:
                raise RuntimeError(f"{name}: Nav2 status {response.status}")
            plan = [[p.pose.position.x, p.pose.position.y] for p in response.result.path.poses]
            if len(plan) < 2 or response.result.path.header.frame_id != "map":
                raise RuntimeError(f"{name}: invalid plan")
            previous_end = path[-1] if path else None
            path.extend(plan)
            segments = list(zip(plan, plan[1:]))
            if previous_end:
                segments.append((previous_end, plan[0]))
            measurements = [(a, b, closest(a, b, obstacles)) for a, b in segments]
            for a, b, measure in measurements:
                if measure["m"] < .5:
                    below.append({"leg": name, "from": a, "to": b, **measure})
            deviation = max(abs(p[axis[0]] - axis[1]) for p in plan) if axis else None
            legs.append({"name": name, "points": len(plan), "center_deviation_m": deviation,
                         "minimum": min((m for _, _, m in measurements), key=lambda d: d["m"])})
        return {"legs": legs, "path": path, "below_half_m": below}
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    config = load_config(args.profile)
    result = measure_layout(config)
    result["nav2"] = nav2_route(config)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({**result, "nav2": result["nav2"]["legs"]}, ensure_ascii=False))
