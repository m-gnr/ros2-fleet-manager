import type { Pose } from './telemetry'

export type Point = readonly [number, number]
export type TrailPoint = { pose: Pose; start: boolean }
export type ObservedPath = {
  stamp: string
  receivedAt: number
  expiresAt: number
  points?: readonly Point[]
}

export const maxPlanPoints = 1024
export const maxTrailPoints = 512
const trailWindowNs = 60_000_000_000n
const gapNs = 500_000_000n
const minimumStep = 0.025
const maxStep = 0.30

function distance(a: Pose, b: Pose) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

export function recordTrail(trail: readonly TrailPoint[], pose: Pose, previous?: Pose): readonly TrailPoint[] {
  if (pose.source !== 'tf' || pose.frame_id !== 'map') return trail
  const stamp = BigInt(pose.stamp_ns)
  const last = trail.at(-1)?.pose
  if (last && stamp <= BigInt(last.stamp_ns)) return trail
  const start = !last || !previous || distance(previous, pose) > maxStep ||
    stamp - BigInt(previous.stamp_ns) > gapNs || pose.receivedAt - previous.receivedAt > 500
  const first = trail.findIndex(point => BigInt(point.pose.stamp_ns) >= stamp - trailWindowNs)
  const retained = first === 0 ? trail : first === -1 ? [] : trail.slice(first)
  if (retained.length && last && !start && distance(last, pose) < minimumStep) return retained
  return [...retained.slice(1 - maxTrailPoints), { pose, start: start || retained.length === 0 }]
}

export function readObservedPath(packet: Record<string, unknown>, stamp: string, now: number): ObservedPath | undefined {
  const { points, ttl_ms: ttl } = packet
  if (typeof ttl !== 'number' || !Number.isInteger(ttl) || ttl < 1 || ttl > 2000 ||
      !Array.isArray(points) || points.length < 2 || points.length > maxPlanPoints) return
  const decoded: Point[] = []
  for (const point of points) {
    if (!Array.isArray(point) || point.length !== 2 ||
        !point.every(value => typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= 10_000)) return
    decoded.push([point[0], point[1]])
  }
  return { stamp, receivedAt: now, expiresAt: now + ttl, points: decoded }
}

export function hidePath(path?: ObservedPath): ObservedPath | undefined {
  return path?.points ? { ...path, points: undefined } : path
}

export function groundPoint([x, y]: Point, height: number): [number, number, number] {
  return [x, height, -y]
}

export type RouteOptions = { plan: boolean; trail: boolean; selectedOnly: boolean; highlight: boolean }

export function routeVisibility(options: RouteOptions, selected: boolean) {
  const visible = !options.selectedOnly || selected
  return { plan: visible && options.plan, trail: visible && options.trail,
    opacity: !options.highlight || selected ? 1 : 0.48 }
}
