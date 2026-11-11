"""Backend/config checks and deterministic browser evidence for the warehouse profile."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
import yaml

from backend.dashboard.api import create_app
from backend.dashboard.models import Pose, SourceSnapshot, Task, TaskCounts
from backend.dashboard.publisher import project
from backend.fleet_manager.builder import build_fleet_manager_from_config
from fleet_config import load_config
from fleet_config.loader import read_yaml
from fleet_config.anchored import AnchoredFleetConfig
from fleet_config.warehouse_assets import generate

PROFILE = Path("config/fleet.warehouse-grid.yaml").resolve()
OLD_PROFILE = PROFILE.with_name("fleet.warehouse-grid-12x8.yaml")
ORIGIN = "http://127.0.0.1:19847"


def scenario(path):
    config = load_config(path)
    core, ids = build_fleet_manager_from_config(path)
    snapshot = project((core, {}, 0.0, None), str(uuid4()), 1, datetime.now(timezone.utc))
    pickup = next(point for point in config.warehouse.transfer_points if point.kind == "pickup")
    delivery = next(point for point in config.warehouse.transfer_points if point.kind == "dropoff")
    dock = config.stations.charging_stations[0]

    def pose(item):
        return Pose(**item.pose.model_dump(), frame_id="map")

    # Only telemetry and the example task are synthetic. Resource IDs, types and poses come from Fleet Manager.
    a, b = snapshot.robots
    alpha, beta = ids
    a = a.model_copy(update=dict(
        state="CHARGING", pose=pose(dock), telemetry="LIVE", pose_reliability="LIVE", battery_reliability="LIVE",
        battery_soc_percent=72.5, battery_energy_wh=72.5, initial_status_verified=True,
        charging="CHARGING", charging_station_id=dock.id, status_sim_ns="1000000000", status_age_sec=.1,
    ))
    b = b.model_copy(update=dict(
        state="EXECUTING_TASK", pose=pose(delivery), telemetry="LIVE", pose_reliability="LIVE",
        battery_reliability="LIVE", battery_soc_percent=90.0, battery_energy_wh=90.0,
        initial_status_verified=True, active_task_id="delivery-01", charging="NOT_CHARGING",
        status_sim_ns="1000000000", status_age_sec=.1,
    ))
    task = Task(task_id="delivery-01", status="EXECUTING", priority="HIGH", pickup=pose(pickup),
                dropoff=pose(delivery), assigned_robot_id=beta, created_at_source_seconds=1, review_hold=False)
    stations = tuple(station.model_copy(update=dict(
        state="OCCUPIED", reserved_by_robot_id=alpha, occupied_by_robot_id=alpha,
        charging="CHARGING", charging_robot_id=alpha,
    )) if station.station_id == dock.id else station for station in snapshot.stations)
    return config, snapshot.model_copy(update=dict(robots=(a, b), stations=stations, tasks=(task,),
                                                   task_counts=TaskCounts(total=1, active=1, queued=0)))


def read_app(folder, config, snapshot):
    path = folder / "snapshot.json"
    path.write_text(SourceSnapshot(captured_monotonic_ns=time.monotonic_ns(), fleet=snapshot).model_dump_json())
    with TestClient(create_app(path, origins={ORIGIN}, fleet_config=config), base_url=ORIGIN) as client:
        for _ in range(50):
            fleet = client.get("/api/fleet")
            if fleet.is_success:
                layout = client.get("/api/warehouse-layout")
                assert layout.is_success and layout.headers["cache-control"] == "no-store"
                return {"fleet": fleet.json(), "layout": layout.json()}
            time.sleep(.015)
    raise AssertionError("Dashboard did not read the fixture snapshot")


def moved_config(folder, profile=PROFILE):
    profile = profile.resolve()
    raw = read_yaml(profile)
    raw["stations"]["charging_stations"][0]["pose"]["x"] = load_config(profile).stations.charging_stations[0].pose.x + .25
    if raw["fleet"]["map_path"] != "warehouse:generated":
        raw["fleet"]["map_path"] = str(profile.parent / raw["fleet"]["map_path"])
    for robot in raw["robots"]:
        robot["nav2_params_path"] = str(PROFILE.parent / robot["nav2_params_path"])
    path = folder / PROFILE.name
    path.write_text(yaml.safe_dump(raw, allow_unicode=True))
    return path


def test_grid_source_and_moved_station_share_backend_coordinates(tmp_path):
    config, snapshot = scenario(PROFILE)
    before = read_app(tmp_path, config, snapshot)
    assert before["layout"]["layout"] == config.warehouse.scene_payload()
    moved, new_snapshot = scenario(moved_config(tmp_path))
    after = read_app(tmp_path, moved, new_snapshot)
    assert after["layout"]["layout"] == before["layout"]["layout"]
    assert after["fleet"]["stations"][0]["pose"]["x"] == 5.5
    assert before["fleet"]["stations"][0]["pose"]["x"] == 5.25
    mismatch = read_app(tmp_path, moved, snapshot)
    assert mismatch["layout"]["profile_mismatch"] and mismatch["layout"]["layout"] is None


def test_layout_rejects_rack_across_an_aisle():
    raw = read_yaml(PROFILE)
    raw["warehouse"]["racks"][0]["bounds"]["y_min"] = 1.25
    with pytest.raises(ValueError, match="rack overlaps an aisle"):
        AnchoredFleetConfig.model_validate(raw).resolve()


def test_resize_keeps_rack_size_and_updates_world_map_and_station(tmp_path):
    from xml.etree import ElementTree as ET

    raw = read_yaml(PROFILE)
    raw["warehouse"]["width"] += 2
    raw["warehouse"]["depth"] += 2
    for robot in raw["robots"]:
        robot["nav2_params_path"] = str(PROFILE.parent / robot["nav2_params_path"])
    resized = tmp_path / "resized.yaml"
    resized.write_text(yaml.safe_dump(raw, allow_unicode=True))
    for source, name, width, depth, dock_x in ((PROFILE, "base", 20, 12, 5.25), (resized, "resize", 22, 14, 6.25)):
        out = tmp_path / name
        cfg = generate(source, out)
        assert cfg.stations.charging_stations[0].pose.x == dock_x
        layout = json.loads((out/"scene.json").read_text())
        assert layout["bounds"] == dict(x_min=-width/2, x_max=width/2, y_min=-depth/2, y_max=depth/2)
        pgm = (out/"map.pgm").read_bytes().split(b"\n", 3)
        cols, rows = map(int, pgm[1].split())
        info = yaml.safe_load((out/"map.yaml").read_text())
        x0, y0, _ = info["origin"]
        cell = info["resolution"]
        assert (cols * cell, rows * cell) == pytest.approx((width+3, depth+3))
        xml = ET.parse(out/"warehouse.sdf")
        for robot in cfg.robots:
            params = yaml.safe_load((out/f"nav2-{robot.id}.yaml").read_text())
            assert Path(params["map_server"]["ros__parameters"]["yaml_filename"]) == out/"map.yaml"
            for layer in ("local_costmap", "global_costmap"):
                costmap = params[layer][layer]["ros__parameters"]
                assert costmap["resolution"] == cell and "static_layer" in costmap["plugins"]
        for obj in layout["walls"]+layout["racks"]:
            b = obj["bounds"]
            x, y = (b["x_min"]+b["x_max"])/2, (b["y_min"]+b["y_max"])/2
            expected = b["x_max"]-b["x_min"], b["y_max"]-b["y_min"]
            model = xml.find(f".//model[@name='{obj['id']}']")
            assert list(map(float,model.findtext("pose").split()))[:2] == pytest.approx((x,y))
            assert list(map(float,model.findtext(".//collision/geometry/box/size").split()))[:2] == pytest.approx(expected)
            col, row = int((x-x0)/cell), rows-1-int((y-y0)/cell)
            assert pgm[3][row*cols+col] == 0
            if obj in layout["racks"]:
                rack = obj["id"]
                assert expected == pytest.approx((2.75 if rack.endswith("1") else 3.25,
                                                  .5 if rack == "rack_a4" else 1.0))
        # Both sides of the wall are free through the only door.
        col, row = int((-width/2-x0)/cell), rows-1-int((0-y0)/cell)
        assert pgm[3][row*cols+col] == 254


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--profile", type=Path, default=PROFILE)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        before = read_app(folder, *scenario(args.profile))
        after = read_app(folder, *scenario(moved_config(folder, args.profile)))
        args.output.write_text(json.dumps({"original": before, "moved": after}, ensure_ascii=False))
