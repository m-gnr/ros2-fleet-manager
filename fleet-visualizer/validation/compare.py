"""Join independent ROS, WebSocket and Chrome scene samples by ROS timestamp."""
import argparse
import json
import math
from pathlib import Path
from statistics import median


def load_lines(path):
    with path.open() as lines:
        for line in lines:
            if line.startswith("{"):
                yield json.loads(line)


def stats(samples):
    ordered = sorted(samples)
    return dict(n=len(ordered), p50=median(ordered), p95=ordered[math.ceil(len(ordered) * 0.95) - 1],
                max=ordered[-1])


def difference(left, right):
    yaw_delta = left["yaw"] - right["yaw"]
    return (math.hypot(left["x"] - right["x"], left["y"] - right["y"]),
            abs(math.atan2(math.sin(yaw_delta), math.cos(yaw_delta))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("browser", type=Path)
    parser.add_argument("ros", type=Path)
    parser.add_argument("bridge", type=Path)
    args = parser.parse_args()

    frames = json.loads((args.browser / "frames.json").read_text())
    packets = [packet for packet in json.loads((args.browser / "packets.json").read_text())
               if packet["type"] == "robot_pose"]
    ros = {pose["stamp_ns"]: pose for pose in load_lines(args.ros)}
    rendered = {frame["stamp_ns"]: frame for frame in frames}
    matched = [(packet, ros[packet["stamp_ns"]], rendered[packet["stamp_ns"]])
               for packet in packets if packet["stamp_ns"] in ros and packet["stamp_ns"] in rendered]
    if len(matched) < 6:
        parser.error("Fewer than six same-stamp ROS, WebSocket and render samples")
    initial = matched[0][0]
    moving = max(matched, key=lambda triple: difference(initial, triple[0])[0])
    position_error, yaw_error = map(max, zip(*(difference(packet, ref) for packet, ref, _ in matched)))
    if position_error > 1e-6 or yaw_error > 1e-6:
        parser.error(f"ROS and WebSocket disagree: {position_error:g} m, {yaw_error:g} rad")
    if any(packet["frame_id"] != ref["frame_id"] for packet, ref, _ in matched):
        parser.error("ROS and WebSocket use different frames")

    # ROS TF stamp is unique within these no-rewind acceptance runs.
    browser_keys = {(pose["stream_id"], pose["epoch"], pose["stamp_ns"]) for pose in packets}
    bridge = [pose for pose in load_lines(args.bridge) if pose.get("event") == "WS_POSE"
              and (pose["stream_id"], pose["epoch"], pose["stamp_ns"]) in browser_keys]
    if not bridge:
        parser.error("No bridge trace corresponds to browser packets")
    print(json.dumps(dict(
        websocket_poses=len(packets), rendered_frames=len(frames), matched=len(matched),
        max_ros_position_error_m=position_error, max_ros_yaw_error_rad=yaw_error,
        max_distance_m=difference(initial, moving[0])[0],
        ros_stamp_to_send_sim_ms=stats([p["ros_age_at_send_ms"] for p in bridge
                                       if p["ros_age_at_send_ms"] is not None]),
        tf_receipt_to_ws_send_complete_ms=stats([p["rx_to_sent_ms"] for p in bridge]),
        browser_receipt_to_exact_scene_frame_ms=stats([f["receive_to_frame_ms"] for f in frames]),
        moving_example=dict(websocket=moving[0], ros=moving[1], render=moving[2]),
    ), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
