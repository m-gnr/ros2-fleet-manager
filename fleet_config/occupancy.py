"""Shared static occupancy raster and collision checks for approach poses."""
from itertools import groupby
from hashlib import sha256
import json
from math import ceil, floor, hypot, isclose


def raster(layout):
    solids = list(layout.obstacles())
    resolution = next((step for step in (.05, .025, .01, .005)
                       if all(isclose(edge / step, round(edge / step), abs_tol=1e-7)
                              for _, bounds, _ in solids
                              for edge in (bounds.x_min, bounds.x_max, bounds.y_min, bounds.y_max))), None)
    if resolution is None:
        raise ValueError("wall/rack edges must align exactly with a supported map resolution")
    b = layout.bounds
    origin = [b.x_min - 1.5, b.y_min - 1.5]
    width = round((b.x_max - b.x_min + 3) / resolution)
    height = round((b.y_max - b.y_min + 3) / resolution)
    if width * height > 4_000_000:
        raise ValueError("generated occupancy image exceeds 4 million cells")
    cells = bytearray(width * height)
    for _, rect, _ in solids:
        left, right = (round((x - origin[0]) / resolution) for x in (rect.x_min, rect.x_max))
        bottom, top = (round((y - origin[1]) / resolution) for y in (rect.y_min, rect.y_max))
        for row in range(bottom, top):
            cells[row*width+left:row*width+right] = bytes([100]) * (right - left)
    return dict(frame_id="map", resolution=resolution, width=width, height=height, origin=origin), cells


def encode_grid(metadata, cells, source):
    return {**metadata, "source": source, "runs": [[value, sum(1 for _ in group)]
                                                  for value, group in groupby(cells)]}


def profile_digest(config):
    return sha256(json.dumps(config.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()


def check_approaches(config, metadata, cells):
    """Reject poses whose conservative circular footprint touches an occupied cell."""
    radius = config.warehouse.approach_clearance_m
    if radius is None:
        return
    poses = [(point.id, point.pose) for point in config.warehouse.transfer_points]
    poses += [(station.id, station.pose) for group in (
        config.stations.charging_stations, config.stations.parking_stations, config.stations.safe_waiting_areas
    ) for station in group]
    poses += [(robot.id, robot.initial_pose) for robot in config.robots]
    step, width, height = metadata["resolution"], metadata["width"], metadata["height"]
    x0, y0 = metadata["origin"]
    for name, pose in poses:
        if not config.warehouse.bounds.contains(pose.x, pose.y, radius):
            raise ValueError(f"{name}: approach footprint leaves the warehouse")
        for row in range(floor((pose.y - radius - y0) / step), ceil((pose.y + radius - y0) / step)):
            for col in range(floor((pose.x - radius - x0) / step), ceil((pose.x + radius - x0) / step)):
                dx = max(x0 + col*step - pose.x, pose.x - x0 - (col+1)*step, 0)
                dy = max(y0 + row*step - pose.y, pose.y - y0 - (row+1)*step, 0)
                if hypot(dx, dy) <= radius and (
                    not 0 <= row < height or not 0 <= col < width or cells[row*width+col] != 0
                ):
                    raise ValueError(f"{name}: approach footprint is blocked in the generated costmap")
