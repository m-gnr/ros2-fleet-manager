import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Box3, Line3, Ray, Vector3 } from "three";

const [evidence, browserMetrics] = process.argv.slice(2);
assert.ok(evidence && browserMetrics, "Usage: warehouse-clearance.mjs <live-evidence-dir> <browser-metrics.json>");

const read = (path) => readFileSync(path, "utf8");
const rows = (file) => read(join(evidence, file)).trim().split("\n").map(row => JSON.parse(row));
const view = JSON.parse(read(browserMetrics)).windows.find(window => window.width === 1440);
assert.equal(view.frame.mode, "free");
const camera = new Vector3(...view.frame.camera);

const decor = JSON.parse(read(join(evidence, "decor-bounds.json"))).map(({ name, min, max }) => ({
  name,
  bounds: new Box3(new Vector3(...min), new Vector3(...max)),
  footprint: new Box3(new Vector3(min[0], -1, min[2]), new Vector3(max[0], 1, max[2])),
}));
for (const name of ["rear-wall", "left-wall", "right-wall", "rear-rack", "side-rack", "pallet-row"]) {
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
    polylines: paths.length, vertices: 0, segments: 0, sightlines: 0, occludedSightlines: 0,
    minimumFootprintDistanceM: Object.fromEntries(decor.map(({ name }) => [name, Infinity])),
  };
  const position = new Vector3();
  function sightline(point) {
    sample.copy(point).setY(height);
    const distance = ray.direction.copy(sample).sub(camera).length();
    ray.set(camera, ray.direction.normalize());
    result.sightlines++;
    if (decor.some(({ bounds }) => ray.intersectBox(bounds, hit) && hit.distanceTo(camera) < distance)) {
      result.occludedSightlines++;
    }
  }
  for (const path of paths) {
    const vertices = path.map(([x, y]) => new Vector3(x, 0, -y));
    result.vertices += vertices.length;
    sightline(vertices[0]);
    for (let i = 1; i < vertices.length; i++) {
      const start = vertices[i - 1], end = vertices[i];
      const length = start.distanceTo(end);
      result.segments++;
      for (const { name, footprint } of decor) {
        delta.copy(end).sub(start);
        result.minimumFootprintDistanceM[name] = Math.min(result.minimumFootprintDistanceM[name],
          segmentClearance(footprint, start, end, length));
      }
      const subdivisions = Math.max(1, Math.ceil(length / .05));
      for (let j = 1; j <= subdivisions; j++) sightline(position.lerpVectors(start, end, j / subdivisions));
    }
  }
  return result;
}

const result = { camera: camera.toArray(), decor: decor.map(({ name, bounds }) =>
  ({ name, min: bounds.min.toArray(), max: bounds.max.toArray() })),
  tf: inspect(tf, .10), nav2: inspect(plans, .039) };
console.log(JSON.stringify(result, null, 2));
for (const { minimumFootprintDistanceM, occludedSightlines } of [result.tf, result.nav2]) {
  assert.ok(Object.values(minimumFootprintDistanceM).every(distance => distance > 0), "Decor intersects a recorded segment");
  assert.equal(occludedSightlines, 0, "Decor occludes recorded points from the default camera");
}
