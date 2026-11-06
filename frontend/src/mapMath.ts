import type { Pose } from "./fleet";

export type Point = { x: number; y: number };
export type Camera = Point & { scale: number };

export function projectPose(pose: Pose, frame: string) {
  if (pose.frame_id !== frame || ![pose.x, pose.y, pose.yaw].every(Number.isFinite)) return null;
  return { x: pose.x, y: -pose.y, rotation: -pose.yaw * 180 / Math.PI };
}

export function fitCamera(points: Point[], width: number, height: number): Camera {
  let minX = -4.8, maxX = 4.8, minY = -3.5, maxY = 3.5;
  for (const point of points) {
    minX = Math.min(minX, point.x - 0.5);
    maxX = Math.max(maxX, point.x + 0.5);
    minY = Math.min(minY, point.y - 0.5);
    maxY = Math.max(maxY, point.y + 0.5);
  }
  const scale = Math.max(1, Math.min(Math.max(1, width - 64) / (maxX - minX),
    Math.max(1, height - 60) / (maxY - minY), 90));
  return { scale, x: width / 2 - (minX + maxX) / 2 * scale, y: height / 2 - (minY + maxY) / 2 * scale };
}

export function zoomCamera(camera: Camera, anchor: Point, factor: number): Camera {
  const scale = Math.min(180, Math.max(12, camera.scale * factor));
  const ratio = scale / camera.scale;
  return { scale, x: anchor.x - (anchor.x - camera.x) * ratio, y: anchor.y - (anchor.y - camera.y) * ratio };
}
