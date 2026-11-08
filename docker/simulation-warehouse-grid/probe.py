"""Send concurrent NavigateToPose goals and measure physical Fortress positions."""
import argparse
import json
from math import atan2, cos, hypot, isfinite, sin
from pathlib import Path
import time

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import OccupancyGrid, Path as NavPath
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import DurabilityPolicy, QoSProfile
from ros_gz_interfaces.msg import Contacts
import yaml

from fleet_config import load_config


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("profile", type=Path)
    cli.add_argument("generated", type=Path)
    cli.add_argument("scenario", choices=("delivery", "passing"))
    args = cli.parse_args()
    cfg = load_config(args.profile)
    targets = json.loads((args.generated / "goals.json").read_text())
    report = {"scenario": args.scenario, "goals": targets, "result": "doğrulanamadı"}
    rclpy.init()
    node = rclpy.create_node("warehouse_acceptance", parameter_overrides=[
        rclpy.parameter.Parameter("use_sim_time", value=True)
    ])
    positions, traces, maps, costmaps, paths, dock_contacts = {}, {}, {}, {}, {}, set()
    clients, lifecycles = {}, {}
    alpha, beta = (robot.id for robot in cfg.robots)
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    for robot in cfg.robots:
        id_, ns = robot.id, robot.namespace
        traces[id_] = []

        def physical(message, id_=id_):
            p, q = message.pose.position, message.pose.orientation
            stamp = message.header.stamp.sec + message.header.stamp.nanosec/1e9
            yaw = atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
            value = (stamp, p.x, p.y, yaw)
            positions[id_] = value
            if not traces[id_] or stamp - traces[id_][-1][0] >= .095:
                traces[id_].append(value)

        def path(message, id_=id_):
            if message.header.frame_id == "map":
                paths[id_] = [[p.pose.position.x,p.pose.position.y] for p in message.poses]

        node.create_subscription(PoseStamped, ns+"/physical_pose", physical, 20)
        node.create_subscription(NavPath, ns+"/plan", path, 10)
        node.create_subscription(OccupancyGrid, ns+"/map", lambda m, i=id_: maps.update({i:m}), qos)
        node.create_subscription(OccupancyGrid, ns+"/global_costmap/costmap", lambda m, i=id_: costmaps.update({i:m}), 10)
        clients[id_] = ActionClient(node, NavigateToPose, robot.nav2_action_name)
        lifecycles[id_] = node.create_client(GetState, ns+"/bt_navigator/get_state")

    dock = next(item for item in cfg.stations.charging_stations if item.id == "dock_1")

    def contact(message):
        for event in message.contacts:
            names = event.collision1.name, event.collision2.name
            if any(alpha in name for name in names):
                dock_contacts.add(tuple(sorted(names)))

    node.create_subscription(Contacts, f"/dock/{dock.id}/contacts", contact, 10)

    def wait(predicate, timeout, what):
        until = time.monotonic()+timeout
        while time.monotonic()<until:
            rclpy.spin_once(node, timeout_sec=.06)
            if predicate():
                return
        raise TimeoutError(what)

    try:
        wait(lambda: len(positions)==2 and len(maps)==2 and len(costmaps)==2 and
             all(client.server_is_ready() for client in clients.values()) and
             all(client.service_is_ready() for client in lifecycles.values()), 100, "Nav2 readiness")
        active = set()
        deadline = time.monotonic()+35
        while len(active)<2 and time.monotonic()<deadline:
            requests = {name: client.call_async(GetState.Request()) for name, client in lifecycles.items() if name not in active}
            wait(lambda: all(f.done() for f in requests.values()), 5, "lifecycle")
            active.update(name for name,f in requests.items() if f.result().current_state.label=="active")
        if len(active)!=2:
            raise TimeoutError("Nav2 lifecycle not active")

        resolution = yaml.safe_load((args.generated/"map.yaml").read_text())["resolution"]
        image = (args.generated/"map.pgm").read_bytes().split(b"\n", 3)[3]
        for id_, msg in maps.items():
            width = msg.info.width
            occupied = [100 if pix==0 else 0 for offset in range(len(image)-width,-1,-width)
                        for pix in image[offset:offset+width]]
            assert abs(msg.info.resolution-resolution)<1e-7 and list(msg.data)==occupied, id_
        for id_, msg in costmaps.items():
            for rack in cfg.warehouse.racks:
                b = rack.bounds
                col = int(((b.x_min+b.x_max)/2-msg.info.origin.position.x)/msg.info.resolution)
                row = int(((b.y_min+b.y_max)/2-msg.info.origin.position.y)/msg.info.resolution)
                assert msg.data[row*msg.info.width+col] == 100, (id_,rack.id)
        report["map_exact_cells"] = len(image)
        report["global_costmap_rack_centres"] = len(cfg.warehouse.racks)*len(costmaps)
        pending = {}
        for id_, goal in targets.items():
            command = NavigateToPose.Goal()
            command.pose.header.frame_id = "map"
            command.pose.header.stamp = node.get_clock().now().to_msg()
            command.pose.pose.position.x, command.pose.pose.position.y = goal["x"],goal["y"]
            command.pose.pose.orientation.z = sin(goal["yaw"]/2)
            command.pose.pose.orientation.w = cos(goal["yaw"]/2)
            pending[id_] = clients[id_].send_goal_async(command)
        wait(lambda: all(f.done() for f in pending.values()), 12, "goal response")
        handles = {id_:f.result() for id_,f in pending.items()}
        assert all(handle.accepted for handle in handles.values()), "Nav2 rejected goal"
        results = {id_:handle.get_result_async() for id_,handle in handles.items()}
        closest = float("inf")
        crossed = False
        deadline = time.monotonic()+85
        while time.monotonic()<deadline:
            rclpy.spin_once(node, timeout_sec=.05)
            a,b = positions[alpha], positions[beta]
            if abs(a[0]-b[0])<.12:
                closest = min(closest,hypot(a[1]-b[1],a[2]-b[2]))
                if args.scenario=="passing":
                    aisle = next(aisle.bounds for aisle in cfg.warehouse.aisles if aisle.id=="aisle_c")
                    crossed |= a[1]>b[1] and aisle.contains(*a[1:3]) and aisle.contains(*b[1:3])
            if all(f.done() for f in results.values()):
                break
        report["status"] = {id_:f.result().status if f.done() else None for id_,f in results.items()}
        report["goal_error_m"] = {id_:hypot(positions[id_][1]-goal["x"],positions[id_][2]-goal["y"])
                                  for id_,goal in targets.items()}
        report["final_pose"] = positions
        report["closest_centres_m"] = closest if isfinite(closest) else None
        report["crossed_inside_aisle"] = crossed
        report["dock_contact_pairs"] = sorted(dock_contacts)
        success = (all(v == GoalStatus.STATUS_SUCCEEDED for v in report["status"].values()) and
                   max(report["goal_error_m"].values()) <= .35)
        if args.scenario=="passing":
            # Each physical footprint fits inside a 0.45 m radius about base_link.
            report["result"] = "geçti" if success and crossed and closest > .9 else (
                "bekledi" if not crossed and isfinite(closest) and closest > .9 else "doğrulanamadı")
        else:
            report["result"] = "geçti" if success and report["goal_error_m"][alpha] <= dock.tolerance_radius else "başarısız"
        for id_, future in results.items():
            if not future.done():
                handles[id_].cancel_goal_async()
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        report["paths"] = paths
        report["traces"] = traces
        (args.generated/"live.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps({k:v for k,v in report.items() if k not in ("paths","traces")}, ensure_ascii=False),flush=True)
        node.destroy_node()
        rclpy.shutdown()
    return 0 if report["result"]=="geçti" else 1


if __name__ == "__main__":
    raise SystemExit(main())
