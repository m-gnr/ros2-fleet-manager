"""Read-only stationary peer scan, ObservationBuffer, and local-costmap probe."""
import argparse
import xml.etree.ElementTree as ET
import json
import math
from pathlib import Path
import time
from collections import Counter
from rosidl_runtime_py.convert import message_to_ordereddict

import rclpy
from rclpy.duration import Duration
from rclpy.time import Time
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from tf2_msgs.msg import TFMessage
from geometry_msgs.msg import PoseStamped
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformException, TransformListener
from fleet_interfaces.msg import ObservationHealth
from fleet_config import load_config
from fleet_config.obstacle_sensors import sensor_contracts


def stamp_ns(value):
    return value.sec * 1_000_000_000 + value.nanosec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--world", type=Path, required=True, help="Actual generated SDF for peer body dimensions")
    parser.add_argument("--duration", type=float, default=20.0)
    args = parser.parse_args()
    cfg = load_config(args.profile)
    if len(cfg.robots) != 2:
        raise ValueError("peer probe requires exactly two configured robots")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    world = ET.parse(args.world)
    body_half = {}
    for robot in cfg.robots:
        box = world.find(f'.//model[@name="{robot.id}"]/link[@name="base_link"]/collision[@name="body"]/geometry/box/size')
        body_half[robot.id] = [float(v)/2 for v in box.text.split()]
    rows = []
    scans, health, maps, poses, states = {}, {}, {}, {}, {}
    counts = {}
    raw = args.output.with_suffix(".raw.jsonl").open("w")

    def capture(kind, key, msg):
        raw.write(json.dumps(dict(kind=kind, key=key, message=message_to_ordereddict(msg)), allow_nan=True)+"\n")
        if kind == "SCAN":
            counts.setdefault(key[0], Counter())["scan_messages"] += 1
            scans.setdefault(tuple(key), []).append(msg)
        elif kind == "HEALTH":
            health.setdefault(key, []).append(msg)
        elif kind == "GRID":
            maps[key] = msg
        elif kind == "POSE":
            poses[key] = msg
    rclpy.init()
    node = rclpy.create_node("stationary_peer_costmap_probe", parameter_overrides=[
        rclpy.parameter.Parameter("use_sim_time", value=True)])
    tf = Buffer(cache_time=Duration(seconds=30))
    listener = TransformListener(tf, node, spin_thread=False)

    def emit(kind, **data):
        rows.append(dict(wall_monotonic=time.monotonic(), sim_ns=node.get_clock().now().nanoseconds,
                         kind=kind, **data))

    node.create_subscription(TFMessage, "/tf", lambda m: raw.write(json.dumps(dict(kind="TF", message=message_to_ordereddict(m)))+"\n"), 100)
    node.create_subscription(TFMessage, "/tf_static", lambda m: raw.write(json.dumps(dict(kind="TF_STATIC", message=message_to_ordereddict(m)))+"\n"), QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    clients = {}
    for robot in cfg.robots:
        rid, ns = robot.id, robot.namespace.rstrip("/")
        clients[rid] = node.create_client(GetState, ns + "/bt_navigator/get_state")
        node.create_subscription(PoseStamped, ns + "/physical_pose",
            lambda msg, rid=rid: capture("POSE", rid, msg), qos_profile_sensor_data)
        node.create_subscription(OccupancyGrid, ns + "/local_costmap/costmap",
            lambda msg, rid=rid: capture("GRID", rid, msg), 10)
        for health_topic in (ns + "/perception_observations", ns + "/local_costmap/perception_observations"):
            node.create_subscription(ObservationHealth, health_topic,
                lambda msg, rid=rid: capture("HEALTH", rid, msg), qos_profile_sensor_data)
        for sensor in sensor_contracts(cfg, robot):
            key = (rid, sensor["topic"])
            node.create_subscription(LaserScan, sensor["topic"],
                lambda msg, key=key: capture("SCAN", key, msg), qos_profile_sensor_data)

    def pump(seconds=0.02):
        rclpy.spin_once(node, timeout_sec=seconds)

    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        pump()
        if all(client.service_is_ready() for client in clients.values()):
            requests = {rid: client.call_async(GetState.Request()) for rid, client in clients.items()}
            end = time.monotonic() + 3
            while time.monotonic() < end and not all(f.done() for f in requests.values()):
                pump()
            if all(f.done() for f in requests.values()):
                states = {rid: f.result().current_state.label for rid, f in requests.items()}
                if all(v == "active" for v in states.values()):
                    break
    emit("LIFECYCLE", states=states, ready=(len(states) == 2 and all(v == "active" for v in states.values())))
    if len(states) != 2 or not all(v == "active" for v in states.values()):
        emit("SUMMARY", result="NAV2_NOT_READY", reason="lifecycle root cause is in launcher simulation.log")
    else:
        stop_at = time.monotonic() + args.duration
        missing_tf, processed = {}, set()
        attempted = set()
        while time.monotonic() < stop_at:
            pump()
            for robot in cfg.robots:
                rid = robot.id
                grid = maps.get(rid)
                if not health.get(rid) or grid is None or rid not in poses:
                    continue
                frame = grid.header.frame_id
                origin = grid.info.origin.position
                yawq = grid.info.origin.orientation
                origin_yaw = math.atan2(2*(yawq.w*yawq.z+yawq.x*yawq.y),
                                        1-2*(yawq.y*yawq.y+yawq.z*yawq.z))
                source_robot = robot
                for sensor in sensor_contracts(cfg, source_robot):
                    topic = sensor["topic"]
                    topic_scans = {stamp_ns(item.header.stamp): item for item in scans.get((source_robot.id, topic), [])}
                    for observations in health[rid][-5:]:
                        try:
                            idx = observations.topics.index(topic)
                        except ValueError:
                            continue
                        if idx >= len(observations.used) or not observations.used[idx]:
                            continue
                        if idx >= len(observations.measurement_stamps):
                            continue
                        scan_ns = stamp_ns(observations.measurement_stamps[idx])
                        scan = topic_scans.get(scan_ns)
                        if scan is None or (rid, topic, scan_ns) in processed:
                            continue
                        # Only compare an observation with a subsequent published grid.
                        if not 0 <= stamp_ns(grid.header.stamp)-scan_ns <= 1_000_000_000:
                            continue
                        identity = (rid, topic, scan_ns)
                        first_attempt = identity not in attempted
                        attempted.add(identity)
                        # This listener is pumped on this thread: a blocking wait
                        # prevents the TF callback needed to satisfy that wait.
                        try:
                            transform = tf.lookup_transform(frame, scan.header.frame_id,
                                Time(nanoseconds=scan_ns), timeout=Duration(seconds=0))
                        except TransformException as exc:
                            missing_tf[topic] = str(exc)
                            if first_attempt:
                                counts[rid]["scan_tf_error"] += 1
                                emit("TF_ERROR", robot=rid, topic=topic, scan_stamp_ns=scan_ns, stage="scan", error=str(exc))
                            # Data older than this listener's first dynamic TF
                            # cannot be recovered by retrying the same scan.
                            if "past" in str(exc):
                                processed.add(identity)
                            continue
                        if first_attempt:
                            counts[rid]["scan_tf_success"] += 1
                        tr = transform.transform.translation
                        q = transform.transform.rotation
                        tyaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
                        # Test endpoints against the actual generated peer body, not the navigation footprint.
                        peer = next((r for r in cfg.robots if r.id != source_robot.id), None)
                        peer_tf = None
                        try:
                            peer_tf = tf.lookup_transform(frame, poses[peer.id].header.frame_id,
                                Time(nanoseconds=scan_ns), timeout=Duration(seconds=0))
                        except TransformException as exc:
                            missing_tf[poses[peer.id].header.frame_id+"_to_"+frame] = str(exc)
                            if first_attempt:
                                counts[rid]["peer_tf_error"] += 1
                                emit("TF_ERROR", robot=rid, topic=topic, scan_stamp_ns=scan_ns, stage="peer", error=str(exc))
                            if "past" in str(exc):
                                processed.add(identity)
                            continue
                        counts[rid]["peer_tf_success"] += 1
                        ptrans, prot = peer_tf.transform.translation, peer_tf.transform.rotation
                        map_yaw = math.atan2(2*(prot.w*prot.z+prot.x*prot.y), 1-2*(prot.y*prot.y+prot.z*prot.z))
                        physical = poses[peer.id].pose
                        actual_yaw = math.atan2(2*(physical.orientation.w*physical.orientation.z+
                            physical.orientation.x*physical.orientation.y),
                            1-2*(physical.orientation.y**2+physical.orientation.z**2))
                        peer_x = math.cos(map_yaw)*physical.position.x-math.sin(map_yaw)*physical.position.y+ptrans.x
                        peer_y = math.sin(map_yaw)*physical.position.x+math.cos(map_yaw)*physical.position.y+ptrans.y
                        peer_yaw = map_yaw + actual_yaw
                        best = None
                        hit_count = lethal_count = 0
                        for i, distance in enumerate(scan.ranges):
                            if not math.isfinite(distance) or distance < scan.range_min or distance > scan.range_max:
                                continue
                            angle = scan.angle_min + i*scan.angle_increment
                            sx = tr.x + math.cos(tyaw)*distance*math.cos(angle) - math.sin(tyaw)*distance*math.sin(angle)
                            sy = tr.y + math.sin(tyaw)*distance*math.cos(angle) + math.cos(tyaw)*distance*math.sin(angle)
                            dx, dy = sx-peer_x, sy-peer_y
                            bx = math.cos(peer_yaw)*dx + math.sin(peer_yaw)*dy
                            by = -math.sin(peer_yaw)*dx + math.cos(peer_yaw)*dy
                            # Sensor beam endpoint must fall on/within a 2 cm tolerance of the peer body.
                            if (abs(bx) <= body_half[peer.id][0]+0.02 and
                                    abs(by) <= body_half[peer.id][1]+0.02 and
                                    min(abs(abs(bx)-body_half[peer.id][0]),
                                        abs(abs(by)-body_half[peer.id][1])) <= 0.02):
                                hit_count += 1
                                dxg, dyg = sx-origin.x, sy-origin.y
                                col = math.floor((math.cos(origin_yaw)*dxg + math.sin(origin_yaw)*dyg)/grid.info.resolution)
                                row = math.floor((-math.sin(origin_yaw)*dxg + math.cos(origin_yaw)*dyg)/grid.info.resolution)
                                inside = 0 <= col < grid.info.width and 0 <= row < grid.info.height
                                cost = int(grid.data[row*grid.info.width+col]) if inside else None
                                lethal_count += int(cost == 100)
                                point = dict(grid_stamp_ns=stamp_ns(grid.header.stamp), physical_stamp_ns=stamp_ns(poses[peer.id].header.stamp),scan_stamp_ns=scan_ns, source_topic=topic, sensor_frame=scan.header.frame_id,
                                    buffer_used=True, buffer_stamp_ns=stamp_ns(observations.measurement_stamps[idx]),
                                    buffer_frame=frame, beam_index=i, range_m=distance,
                                    peer_body_local_xy_m=[round(bx,4),round(by,4)], endpoint_odom_xy_m=[sx,sy],
                                    costmap_cell=[col,row], cost=cost, lethal=(cost == 100),
                                    grid_frame=frame, grid_resolution=grid.info.resolution)
                                if best is None or distance < best["range_m"]:
                                    best = point
                        counts[rid]["processed_scans"] += 1
                        counts[rid]["peer_hit_points"] += hit_count
                        counts[rid]["lethal_matched_points"] += lethal_count
                        if best:
                            counts[rid]["peer_hit_scans"] += 1
                            emit("PEER_SAMPLE", observing_robot=rid, peer_robot=peer.id, **best)
                        processed.add((rid, topic, scan_ns))
        samples = [r for r in rows if r["kind"] == "PEER_SAMPLE"]
        # Count latest per-source samples and require a matched lethal local cell for PASS.
        relevant = set()
        for robot in cfg.robots:
            peer = next(r for r in cfg.robots if r.id != robot.id)
            dx, dy = peer.initial_pose.x-robot.initial_pose.x, peer.initial_pose.y-robot.initial_pose.y
            distance = math.hypot(dx, dy)
            for sensor in sensor_contracts(cfg, robot):
                yaw = robot.initial_pose.yaw + sensor["base_pose"][5]
                if (math.cos(yaw)*dx + math.sin(yaw)*dy) / max(distance, 1e-9) > 0.5:
                    relevant.add(sensor["topic"])
        if len(relevant) != 2:
            raise ValueError(f"expected two peer-facing side sensors, found {sorted(relevant)}")
        per_topic = {topic: [r for r in samples if r["source_topic"] == topic] for topic in relevant}
        peer_hit = all(any(v for v in per_topic[t]) for t in relevant)
        local_mark = all(any(v["lethal"] for v in per_topic[t]) for t in relevant)
        emit("SUMMARY", result="PASS" if peer_hit and local_mark else "FAIL", peer_hit=peer_hit,
             observation_buffer="PASS" if peer_hit else "FAIL", local_marking="PASS" if local_mark else "FAIL",
             clearing="configured; stationary clearing effect not measured", sample_counts={t:len(v) for t,v in per_topic.items()},
             tf_errors=missing_tf, counters=counts)
    args.output.write_text("\n".join(json.dumps(row, allow_nan=False) for row in rows)+"\n")
    raw.close()
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
