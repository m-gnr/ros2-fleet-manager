"""Reconstruct accepted poses from independently observed planar TF edges."""
import argparse
from bisect import bisect_left
import json
from math import atan2, cos, hypot, sin
from pathlib import Path

from compare_routes import rows


def interpolate(stamp, left, right):
    factor = 0 if left is right else (stamp - left["stamp_ns"]) / (right["stamp_ns"] - left["stamp_ns"])
    x = left["x"] + factor * (right["x"] - left["x"])
    y = left["y"] + factor * (right["y"] - left["y"])
    delta = right["yaw"] - left["yaw"]
    yaw = left["yaw"] + factor * atan2(sin(delta), cos(delta))
    return x, y, yaw


def compare(directory, robot):
    raw = rows(directory / f"edges-{robot}.jsonl")
    anchors, odometry = {}, {}
    for edge in raw:
        frames = edge["parent"], edge["child"]
        if frames == ("map", f"{robot}/odom"):
            anchors.setdefault(edge["stamp_ns"], edge)
        elif frames == (f"{robot}/odom", f"{robot}/base_link"):
            odometry.setdefault(edge["stamp_ns"], edge)
    ref = {int(row["stamp_ns"]): row for row in rows(directory / f"tf-{robot}.jsonl")}
    with (directory / "bridge.log").open() as stream:
        records = [json.loads(line) for line in stream if line.startswith('{"event":')]
    chosen = []
    composed = []
    independent_differences = []
    outliers = []
    for record in records:
        if record["robot"] != robot:
            continue
        stamp = record["stamp_ns"]
        if record["event"] == "anchor":
            chosen.append(stamp)
            continue
        if stamp in ref:
            expected = ref[stamp]
            difference = hypot(record["x"] - expected["x"], record["y"] - expected["y"])
            independent_differences.append(difference)
        index = bisect_left(chosen, stamp)
        if index == len(chosen) or (index == 0 and chosen[index] != stamp):
            continue
        right = chosen[index]
        left = right if right == stamp else chosen[index - 1]
        if left not in anchors or right not in anchors or stamp not in odometry:
            continue
        x, y, yaw = interpolate(stamp, anchors[left], anchors[right])
        odom = odometry[stamp]
        expected_x = x + cos(yaw) * odom["x"] - sin(yaw) * odom["y"]
        expected_y = y + sin(yaw) * odom["x"] + cos(yaw) * odom["y"]
        error = hypot(record["x"] - expected_x, record["y"] - expected_y)
        composed.append(error)
        if stamp in ref and difference > 1e-6 and len(outliers) < 8:
            outliers.append({"stamp_ns": stamp, "ref_lookup_error_m": difference, "recomposed_error_m": error,
                             "accepted_anchors_ns": [left, right]})
    assert len(composed) >= 100 and max(composed) < 1e-6, (robot, len(composed), max(composed, default=None))
    return dict(reconstructed=len(composed), reconstruction_max_error_m=max(composed),
                reference_lookup_count=len(independent_differences),
                reference_lookup_max_error_m=max(independent_differences),
                reference_lookup_over_1um=sum(e >= 1e-6 for e in independent_differences),
                examples=outliers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    directory = parser.parse_args().evidence
    print(json.dumps({robot: compare(directory, robot) for robot in ("robot_1", "robot_2")}, indent=2))
