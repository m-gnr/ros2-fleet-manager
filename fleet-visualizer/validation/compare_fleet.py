"""Compare independent ROS, WebSocket and Chrome observations by robot and timestamp."""
import argparse
from collections import defaultdict
import json
from math import cos, hypot, sin
from pathlib import Path

from compare import difference, load_lines, stats


def key(pose):
    return pose["robot_id"], pose["stream_id"], pose["epoch"], pose["stamp_ns"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("browser", type=Path)
    parser.add_argument("ros", type=Path)
    parser.add_argument("bridge", type=Path)
    args = parser.parse_args()
    frames = {key(frame): frame for frame in json.loads((args.browser / "frames.json").read_text())}
    packets = defaultdict(list)
    for packet in json.loads((args.browser / "packets.json").read_text()):
        if packet["type"] == "robot_pose":
            packets[packet["robot_id"]].append(packet)
    ros = {(ref["base_frame"], ref["stamp_ns"]): ref for ref in load_lines(args.ros)}
    bridge = {key(pose): pose for pose in load_lines(args.bridge) if pose.get("event") == "WS_POSE"}
    if len(packets) < 2:
        parser.error("Expected packets for at least two robots")
    result = {}
    for robot_id, samples in packets.items():
        # These acceptance namespaces equal robot IDs. The bridge uses the configured namespace.
        base_frame = robot_id + "/base_link"
        matched = [(packet, ros[(base_frame, packet["stamp_ns"])], frames[key(packet)])
                   for packet in samples if (base_frame, packet["stamp_ns"]) in ros and key(packet) in frames]
        if len(matched) < 6:
            parser.error(f"{robot_id}: fewer than six same-stamp ROS, WebSocket and render samples")
        errors = [difference(packet, ref) for packet, ref, _ in matched]
        position, yaw = map(max, zip(*errors))
        if position > 1e-6 or yaw > 1e-6 or any(p["frame_id"] != r["frame_id"] for p, r, _ in matched):
            parser.error(f"{robot_id}: ROS reference disagrees ({position:g} m, {yaw:g} rad)")
        scene_position = max(hypot(frame["x"] - p["x"], frame["z"] + p["y"]) for p, _, frame in matched)
        scene_heading = max(hypot(frame["heading_x"] - cos(p["yaw"]),
                                  frame["heading_z"] + sin(p["yaw"])) for p, _, frame in matched)
        if scene_position > 1e-8 or scene_heading > 1e-8:
            parser.error(f"{robot_id}: Chrome root disagrees ({scene_position:g} m, {scene_heading:g} heading)")
        timing = [bridge[key(p)] for p in samples if key(p) in bridge]
        if not timing:
            parser.error(f"{robot_id}: no matching bridge trace")
        example = max(matched, key=lambda triple: difference(matched[0][0], triple[0])[0])
        result[robot_id] = dict(
            matched=len(matched), max_ros_position_error_m=position, max_ros_yaw_error_rad=yaw,
            max_ws_to_3d_position_error_m=scene_position, max_ws_to_3d_heading_vector_error=scene_heading,
            max_distance_m=difference(matched[0][0], example[0])[0],
            tf_receipt_to_ws_send_complete_ms=stats([p["rx_to_sent_ms"] for p in timing]),
            browser_receipt_to_exact_scene_frame_ms=stats([frame["receive_to_frame_ms"] for _, _, frame in matched]),
            example=dict(websocket=example[0], ros=example[1], render=example[2]),
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
