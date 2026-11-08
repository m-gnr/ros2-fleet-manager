import json
import sqlite3
import sys
from pathlib import Path

import yaml

evidence = Path(sys.argv[1])
rendered = json.loads((evidence / "chrome-operation-points.json").read_text())
fleet = yaml.safe_load(Path("config/fleet.yaml").read_text())
stations = {
    station["id"]: station
    for group in fleet["stations"].values()
    for station in group
}
with sqlite3.connect(f"file:{evidence / 'c5-charging.sqlite3'}?mode=ro", uri=True) as database:
    tasks = dict(database.execute("SELECT task_id, snapshot FROM tasks"))
    result = []
    for point in rendered:
        kind = point["kind"]
        if kind in ("pickup", "dropoff"):
            reference = json.loads(tasks[point["id"]])[kind + "_pose"]
            assert reference["frame_id"] == "map"
            source = "SQLite tasks.snapshot"
        else:
            reference = stations[point["id"]]["pose"]
            saved = database.execute("SELECT snapshot FROM reservations WHERE station_id=?", (point["id"],)).fetchone()
            assert saved
            station_pose = json.loads(saved[0])["pose"]
            assert station_pose["frame_id"] == "map"
            assert all(station_pose[key] == reference[key] for key in ("x", "y", "yaw"))
            source = "fleet.yaml + SQLite reservations.snapshot"
        assert point["source"]["frame_id"] == "map"
        assert point["position"] == [reference["x"], 0, -reference["y"]], point
        assert point["yaw"] == reference["yaw"], point
        result.append({"key": point["key"], "source": source, "scene_position": point["position"], "yaw": point["yaw"]})
    def scene_pose(pose):
        return [pose["x"], 0, -pose["y"]]

    station_clearance = [
        {"key": "station:" + station_id, "scene_position": scene_pose(station["pose"]),
         "radius_m": station.get("tolerance_radius", 0)}
        for station_id, station in stations.items()
    ]
    task_clearance = []
    for task_id, snapshot in tasks.items():
        for kind in ("pickup", "dropoff"):
            pose = json.loads(snapshot)[kind + "_pose"]
            assert pose["frame_id"] == "map"
            task_clearance.append({"key": f"{kind}:{task_id}", "scene_position": scene_pose(pose)})

print(json.dumps({"chrome": result, "stations": station_clearance, "tasks": task_clearance},
                 indent=2, ensure_ascii=False))
