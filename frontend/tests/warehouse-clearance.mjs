import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Box3, Line3, Ray, Vector3 } from "three";

const [evidence, browserMetrics, sourceFile] = process.argv.slice(2);
assert.ok(evidence && browserMetrics && sourceFile,
  "Usage: warehouse-clearance.mjs <live-evidence-dir> <browser-metrics.json> <verified-operation-sources.json>");

const read = (path) => readFileSync(path, "utf8");
const rows = (file) => read(join(evidence, file)).trim().split("\n").map(row => JSON.parse(row));
const measured = JSON.parse(read(browserMetrics));
const view = measured.windows.find(window => window.width === 1440);
const sources = JSON.parse(read(sourceFile));
const pointFrames = JSON.parse(read(join(evidence, "chrome-operation-points.json")));
const dock = pointFrames.find(point => point.kind === "CHARGING" && point.dockBounds);
assert.ok(dock, "No measured 3D dock footprint");
// The SDF front support is centered 0.40 m ahead of base_link with radius
// 0.05 m. Its enclosing circle also covers the chassis, wheels and rear caster.
const robotRadiusM = .45;
const visualMarginM = .12;
const sweptRadiusM = robotRadiusM + visualMarginM;
assert.equal(view.frame.mode, "free");
const camera = new Vector3(...view.frame.camera);

const decor = [...JSON.parse(read(join(evidence, "decor-bounds.json"))),
  { name: "dock-unit", ...dock.dockBounds }].map(({ name, min, max }) => ({
  name,
  bounds: new Box3(new Vector3(...min), new Vector3(...max)),
  footprint: new Box3(new Vector3(min[0], -1, min[2]), new Vector3(max[0], 1, max[2])),
}));
for (const name of ["rear-wall", "left-wall", "right-wall", "rear-rack", "side-rack", "inner-rack", "pallet-row",
  "loading-divider", "park-divider-north", "park-divider-south"]) {
  assert.ok(decor.some(section => section.name === name), name);
}

const tf = ["robot_1", "robot_2"].map(id => rows(`tf-${id}.jsonl`).map(({ x, y }) => [x, y]));
const plans = rows("nav2.jsonl").filter(row => row.frame === "map" && row.points?.length).map(row => row.points);
const ray = new Ray();
const line = new Line3();
const hit = new Vector3();
const delta = new Vector3();
const sample = new Vector3();
const corner = new Vector3();

function segmentClearance(footprint, start, end, length) {
  if (footprint.containsPoint(start) || footprint.containsPoint(end)) return 0;
  if (length && ray.set(start, delta.normalize()).intersectBox(footprint, hit) &&
      hit.distanceTo(start) <= length) return 0;
  let distance = Math.min(footprint.distanceToPoint(start), footprint.distanceToPoint(end));
  if (!length) return distance;

  // For a disjoint segment and rectangle, a closest pair includes an endpoint or corner.
  line.set(start, end);
  for (const x of [footprint.min.x, footprint.max.x]) {
    for (const z of [footprint.min.z, footprint.max.z]) {
      corner.set(x, 0, z);
      distance = Math.min(distance, line.closestPointToPoint(corner, true, hit).distanceTo(corner));
    }
  }
  return distance;
}

function inspect(paths, height) {
  assert.ok(paths.length && paths.every(path => path.length >= 2));
  const result = {
    polylines: paths.length, vertices: 0, segments: 0, sightlines: 0, occludedSightlines: 0, occlusionsByDecor: {}, violations: 0,
    minimumFootprintDistanceM: Object.fromEntries(decor.map(({ name }) => [name, Infinity])),
  };
  const position = new Vector3();
  function sightline(point) {
    sample.copy(point).setY(height);
    const distance = ray.direction.copy(sample).sub(camera).length();
    ray.set(camera, ray.direction.normalize());
    result.sightlines++;
    const occluders = decor.filter(({ bounds }) =>
      ray.intersectBox(bounds, hit) && hit.distanceTo(camera) < distance);
    if (occluders.length) result.occludedSightlines++;
    for (const { name } of occluders) result.occlusionsByDecor[name] = (result.occlusionsByDecor[name] ?? 0) + 1;
  }
  for (const path of paths) {
    const vertices = path.map(([x, y]) => new Vector3(x, 0, -y));
    result.vertices += vertices.length;
    sightline(vertices[0]);
    for (let i = 1; i < vertices.length; i++) {
      const start = vertices[i - 1], end = vertices[i];
      const length = start.distanceTo(end);
      result.segments++;
      let intersects = false;
      for (const { name, footprint } of decor) {
        delta.copy(end).sub(start);
        const clearance = segmentClearance(footprint, start, end, length);
        result.minimumFootprintDistanceM[name] = Math.min(result.minimumFootprintDistanceM[name], clearance);
        if (clearance <= sweptRadiusM) intersects = true;
      }
      if (intersects) result.violations++;
      const subdivisions = Math.max(1, Math.ceil(length / .05));
      for (let j = 1; j <= subdivisions; j++) sightline(position.lerpVectors(start, end, j / subdivisions));
    }
  }
  return result;
}

function inspectPoints(points) {
  assert.ok(points.length, "No operation points checked");
  return points.map(({ key, scene_position: [x, , z], radius_m = 0 }) => {
    const center = new Vector3(x, 0, z);
    const distances = decor.map(({ name, footprint }) => {
      // The unit belongs to its own docking bay. Check its clearance from the
      // exact pose and recorded trajectories; reserve the full capture radius
      // around the station against unrelated warehouse walls and racks.
      const ownUnit = name === "dock-unit" && key === dock.key;
      const requiredM = sweptRadiusM + (ownUnit ? 0 : radius_m);
      const distanceM = footprint.distanceToPoint(center);
      return { name, distanceM, requiredM, remainingM: distanceM - requiredM };
    });
    const nearest = distances.reduce((a, b) => a.remainingM < b.remainingM ? a : b);
    return { key, x, z, radius_m, nearest };
  });
}
const fixtures = measured.fixtureTaskPoints.map(({ key, pose }) => {
  assert.equal(pose.frame_id, "map");
  return { key, scene_position: [pose.x, 0, -pose.y] };
});
const result = { camera: camera.toArray(), robotRadiusM, visualMarginM, sweptRadiusM,
  decor: decor.map(({ name, bounds }) => ({ name, min: bounds.min.toArray(), max: bounds.max.toArray() })),
  tf: inspect(tf, .10), nav2: inspect(plans, .039),
  stations: inspectPoints(sources.stations), tasks: inspectPoints(sources.tasks), fixtures: inspectPoints(fixtures) };
console.log(JSON.stringify(result, null, 2));
for (const { violations, occludedSightlines } of [result.tf, result.nav2]) {
  assert.equal(violations, 0, "Raised decor intersects a recorded swept segment");
  assert.equal(occludedSightlines, 0, "Decor occludes a recorded segment from the default camera");
}
for (const point of [...result.stations, ...result.tasks, ...result.fixtures]) {
  assert.ok(point.nearest.remainingM > 0, point.key + " intersects raised decor");
}
