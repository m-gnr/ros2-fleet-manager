"""Compare live browser geometry and bridge packets with independent ROS observations."""
import argparse
import json
from math import hypot
from pathlib import Path
from statistics import median


def rows(path):
    with path.open() as stream:
        return [json.loads(line) for line in stream]


def percentile(values, fraction):
    values = sorted(values)
    return values[round((len(values) - 1) * fraction)]


def compare(directory):
    browser = directory / "browser"
    packets = json.loads((browser / "packets.json").read_text())
    events = json.loads((browser / "route-events.json").read_text())
    rendered = json.loads((browser / "frames.json").read_text())
    ref_paths = {(row["topic"], str(row["stamp"])): row["points"] for row in rows(directory / "nav2.jsonl")
                 if row.get("points")}
    ref_tf = {(row["base_frame"].split("/")[0], row["stamp_ns"]): row for row in rows(directory / "tf.jsonl")}
    bridge_rows = [json.loads(line[line.index("{"):]) for line in (directory / "bridge.log").read_text().splitlines()
                   if '"event": "WS_' in line]

    output = {}
    for id in ("robot_1", "robot_2"):
        trail_keys = {point["stamp_ns"] for event in events if event["robot_id"] == id
                      for point in event.get("trail", [])}
        ws_poses = {p["stamp_ns"]: p for p in packets if p["type"] == "robot_pose" and p["robot_id"] == id}
        tf_errors = [hypot(ws_poses[stamp]["x"] - ref_tf[id, stamp]["x"], ws_poses[stamp]["y"] - ref_tf[id, stamp]["y"])
                     for stamp in trail_keys if (id, stamp) in ref_tf and stamp in ws_poses]
        root_errors = [hypot(frame["x"] - ref_tf[id, frame["stamp_ns"]]["x"],
                             frame["z"] + ref_tf[id, frame["stamp_ns"]]["y"])
                       for frame in rendered if frame["robot_id"] == id and (id, frame["stamp_ns"]) in ref_tf]
        path_packets = [p for p in packets if p["type"] == "robot_path" and p["robot_id"] == id]
        path_matches = [p for p in path_packets if (p["source_topic"], p["stamp_ns"]) in ref_paths]
        assert len(tf_errors) >= 5 and len(root_errors) >= 5, id
        assert len(path_matches) >= 2, id
        for packet in path_matches:
            assert packet["points"] == ref_paths[packet["source_topic"], packet["stamp_ns"]], packet["stamp_ns"]
        poses_delay = [row["rx_to_sent_ms"] for row in bridge_rows
                       if row["event"] == "WS_POSE" and row["robot_id"] == id]
        paths_delay = [row["rx_to_sent_ms"] for row in bridge_rows
                       if row["event"] == "WS_PATH" and row["robot_id"] == id]
        path_to_frame = [event["path_receive_to_frame_ms"] for event in events
                         if event["robot_id"] == id and "path_receive_to_frame_ms" in event]
        pose_to_frame = [frame["receive_to_frame_ms"] for frame in rendered if frame["robot_id"] == id]
        output[id] = {
            "trail_unique_stamps": len(trail_keys), "trail_ref_matches": len(tf_errors),
            "trail_ref_max_error_m": max(tf_errors),
            "trail_ref_equal_under_1um": sum(error < 1e-6 for error in tf_errors),
            "root_ref_matches": len(root_errors),
            "root_ref_equal_under_1um": sum(error < 1e-6 for error in root_errors),
            "root_ref_max_error_m": max(root_errors), "path_packets": len(path_packets),
            "path_ref_exact_matches": len(path_matches),
            "path_max_bytes": max(p["bytes"] for p in path_packets),
            "path_max_points": max(len(p["points"]) for p in path_packets),
            "pose_rx_to_sent_ms_p50_p95": [median(poses_delay), percentile(poses_delay, 0.95)],
            "path_rx_to_sent_ms_p50_p95": [median(paths_delay), percentile(paths_delay, 0.95)],
            "pose_browser_rx_to_frame_ms_p50_p95": [median(pose_to_frame), percentile(pose_to_frame, 0.95)],
            "path_browser_rx_to_frame_ms_p50_p95": (
                [median(path_to_frame), percentile(path_to_frame, 0.95)] if path_to_frame else None),
        }
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    print(json.dumps(compare(parser.parse_args().evidence), indent=2))
