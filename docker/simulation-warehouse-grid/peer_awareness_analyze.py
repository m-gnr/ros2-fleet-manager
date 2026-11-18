"""Replay peer evidence without ROS; counts are observations, not safety guarantees."""
import argparse
import array
import base64
import collections
import gzip
import json
import math
from pathlib import Path
import zlib


def records(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as stream:
        for line in stream:
            yield json.loads(line)


def summarize(root):
    live = root / "live"
    result = dict(contact_messages=0, first_contact=None, action_results=[],
                  physical_pair_minimum_m={}, all_three_executing_observed=False)
    positions, states, minimum = {}, {}, {}
    raw = live / "ros.jsonl"
    if not raw.exists():
        raw = raw.with_suffix(".jsonl.gz")
    for row in records(raw):
        kind = row["kind"]
        if kind == "UNSAFE_CONTACT":
            result["contact_messages"] += 1
            if result["first_contact"] is None:
                result["first_contact"] = row
                result["physical_pair_minimum_before_first_contact_m"] = dict(minimum)
        elif kind == "ACTION_RESULT":
            result["action_results"].append(row)
        elif kind == "ROBOT_STATUS":
            states[row["robot"]] = row["message"]["state"]
        elif kind == "PHYSICAL_POSE":
            p = row["message"]["pose"]["position"]
            stamp = row["message"]["header"]["stamp"]
            stamp = stamp["sec"]*10**9 + stamp["nanosec"]
            rid = row["robot"]
            positions[rid] = (stamp, p["x"], p["y"])
            for other, (s, x, y) in positions.items():
                if other != rid and abs(s-stamp) <= 50_000_000:
                    key = "/".join(sorted((rid, other)))
                    d = math.hypot(p["x"]-x, p["y"]-y)
                    if key not in minimum or d < minimum[key]["distance_m"]:
                        minimum[key] = dict(distance_m=d, stamp_ns=stamp,
                                            pairing_gap_ns=abs(s-stamp))
        elif kind == "PRODUCT_SNAPSHOT":
            snapshot = row["snapshot"].get("fleet", row["snapshot"])
            tasks = snapshot.get("tasks", [])
            if isinstance(tasks, dict): tasks = tasks.get("tasks", [])
            if sum(t.get("status") == "EXECUTING" for t in tasks) >= 3:
                result["all_three_executing_observed"] = True
    result["physical_pair_minimum_m"] = minimum
    result["last_physical_pose"] = positions
    result["last_robot_state"] = states
    counts, seen_plans, latest, marking = collections.Counter(), {}, {}, collections.Counter()
    # Input streams are sequential runs; the baseline probe was restarted once
    # to reduce recording overhead. Neither restart changes the runtime.
    probes = sorted(p for p in live.glob("peer-probe*.jsonl*") if p.is_file())
    first_time, last_time = None, None
    for probe in probes:
        for row in records(probe):
            stamp = row["monotonic"]
            first_time = stamp if first_time is None else min(first_time, stamp)
            last_time = stamp if last_time is None else max(last_time, stamp)
            if row["kind"] == "OBSERVED":
                counts[(row["robot"], row["status"])] += 1
                if row.get("plan"):
                    seen_plans.setdefault(row["robot"], set()).add(row["plan"]["stamp_ns"])
            elif row["kind"] == "PEER_LAYER":
                key = (row["robot"], row["layer"])
                latest[key] = row["report"]
                counts[key + (str(row["report"]["current"]),)] += 1
            elif row["kind"] == "GRID":
                report = latest.get((row["robot"], row["layer"]))
                if (not report or not report["current"] or report["frame"] != row["frame"]
                        or not 0 <= row["stamp_ns"]-report["stamp_ns"] <= 50_000_000):
                    continue
                # Generated costmaps use an unrotated origin; reject other data
                # rather than silently indexing in the wrong coordinate frame.
                if row["orientation"] != [0., 0., 0., 1.]:
                    continue
                if "data_int8_zlib" in row:
                    cells = array.array("b", zlib.decompress(base64.b64decode(row["data_int8_zlib"])))
                else:
                    cells = row["data"]
                for peer in report["robots"]:
                    if peer["robot_id"] == row["robot"] or not peer["live"] or "x" not in peer:
                        continue
                    col = math.floor((peer["x"]-row["origin"][0])/row["resolution"])
                    rr = math.floor((peer["y"]-row["origin"][1])/row["resolution"])
                    if not 0 <= col < row["width"] or not 0 <= rr < row["height"]:
                        continue
                    key = (row["robot"], row["layer"], peer["robot_id"])
                    marking[key + ("matched",)] += 1
                    marking[key + ("lethal",)] += int(cells[rr*row["width"]+col] == 100)
    result["probe_counts"] = {"/".join(k): v for k, v in sorted(counts.items())}
    result["distinct_observed_plans"] = {k: len(v) for k, v in seen_plans.items()}
    result["peer_centre_grid_samples"] = {"/".join(k): v for k, v in sorted(marking.items())}
    result["probe_wall_duration_s"] = last_time-first_time if first_time is not None else None
    result["limits"] = ["50 ms physical stamp pairing; sampled distances are not continuous separation bounds",
                        "50 ms report-to-grid matching; grid matches are not actuator or permit evidence",
                        "Path observation has no child UUID binding; no traffic grants inferred"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(summarize(args.evidence), indent=2) + "\n")


if __name__ == "__main__":
    main()
