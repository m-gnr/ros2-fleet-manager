import type { MapBounds } from './gridLayout'

// Conservative horizontal envelope of the validation robot, including its front support.
const clearance = .45

export function crossesRack(b: MapBounds, ax: number, ay: number, bx: number, by: number) {
  let first = 0, last = 1
  for (const [a, end, lower, upper] of [
    [ax, bx, b.x_min - clearance, b.x_max + clearance],
    [ay, by, b.y_min - clearance, b.y_max + clearance],
  ]) {
    const delta = end - a
    if (delta === 0) {
      if (a < lower || a > upper) return false
      continue
    }
    const enter = (lower - a) / delta, leave = (upper - a) / delta
    first = Math.max(first, Math.min(enter, leave))
    last = Math.min(last, Math.max(enter, leave))
    if (first > last) return false
  }
  return true
}
