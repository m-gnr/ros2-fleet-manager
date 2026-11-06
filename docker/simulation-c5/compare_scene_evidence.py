"""Match Chrome scene packets against independent live ROS subscribers."""
import argparse
import json
from math import atan2, cos, hypot, sin
from pathlib import Path


def records(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def compare(directory):
    packets = json.loads((directory / "scene-packets.json").read_text())
    paths = {(row["topic"], str(row["stamp"])): row["points"]
             for row in records(directory / "nav2.jsonl") if row.get("points")}
    results = {}
    ids = sorted({p["robot_id"] for p in packets if p["type"] == "robot_pose"})
    assert len(ids) >= 2, ids
    for robot_id in ids:
        tf = {row["stamp_ns"]: row for row in records(directory / f"tf-{robot_id}.jsonl")
              if row["frame_id"] == "map" and row["base_frame"].endswith("/base_link")}
        position_errors, heading_errors = [], []
        compared_paths = 0
        for packet in packets:
            if packet.get("robot_id") != robot_id:
                continue
            if packet["type"] == "robot_pose" and packet["stamp_ns"] in tf:
                measured = tf[packet["stamp_ns"]]
                position_errors.append(hypot(measured["x"] - packet["x"], measured["y"] - packet["y"]))
                delta = measured["yaw"] - packet["yaw"]
                heading_errors.append(abs(atan2(sin(delta), cos(delta))))
            if packet["type"] == "robot_path":
                points = paths.get((packet["source_topic"], packet["stamp_ns"]))
                if points is not None:
                    assert packet["points"] == points, packet["stamp_ns"]
                    compared_paths += 1
        exact_tf = sum(xy < 1e-6 and yaw < 1e-6 for xy, yaw in zip(position_errors, heading_errors))
        assert exact_tf >= 5 and compared_paths >= 2, (robot_id, exact_tf, compared_paths)
        results[robot_id] = {
            "tf_stamp_matches": len(position_errors),
            "tf_equal_under_1um_and_1urad": exact_tf,
            "tf_max_position_error_m": max(position_errors),
            "tf_max_heading_error_rad": max(heading_errors),
            "nav2_exact_paths": compared_paths,
        }
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    print(json.dumps(compare(parser.parse_args().evidence), indent=2))
