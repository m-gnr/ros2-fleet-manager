import { Vector3, type Camera } from 'three'
import type { MapBounds } from './gridLayout'

type Point = [number, number]
export type ScreenRect = { left: number; top: number; right: number; bottom: number }

export function screenPoint(point: Vector3, camera: Camera, width: number, height: number): Point {
  point.project(camera)
  return [(point.x + 1) * width / 2, (1 - point.y) * height / 2]
}

function hull(points: Point[]) {
  const sorted = points.sort((a, b) => a[0] - b[0] || a[1] - b[1])
  const chain = (items: Point[]) => {
    const edge: Point[] = []
    for (const point of items) {
      while (edge.length > 1) {
        const a = edge[edge.length - 2], b = edge[edge.length - 1]
        if ((b[0] - a[0]) * (point[1] - a[1]) > (b[1] - a[1]) * (point[0] - a[0])) break
        edge.pop()
      }
      edge.push(point)
    }
    edge.pop()
    return edge
  }
  return [...chain(sorted), ...chain(sorted.reverse())]
}

export function projectedArea(bounds: MapBounds, top: number, camera: Camera, width: number, height: number) {
  const points: Point[] = []
  const point = new Vector3()
  for (const x of [bounds.x_min, bounds.x_max]) {
    for (const z of [-bounds.y_min, -bounds.y_max]) {
      for (const y of top ? [0, top] : [0]) points.push(screenPoint(point.set(x, y, z), camera, width, height))
    }
  }
  return hull(points)
}

const corners = ({ left, top, right, bottom }: ScreenRect): Point[] =>
  [[left, top], [right, top], [right, bottom], [left, bottom]]

export function insideFloor(rect: ScreenRect, polygon: Point[]) {
  return corners(rect).every(point => polygon.every((a, i) => {
    const b = polygon[(i + 1) % polygon.length]
    return (b[0] - a[0]) * (point[1] - a[1]) >= (b[1] - a[1]) * (point[0] - a[0])
  }))
}

export function hitsArea(rect: ScreenRect, polygon: Point[]) {
  const box = corners(rect)
  const axes: Point[] = [[1, 0], [0, 1]]
  polygon.forEach((a, i) => {
    const b = polygon[(i + 1) % polygon.length]
    axes.push([a[1] - b[1], b[0] - a[0]])
  })
  return axes.every(([x, y]) => {
    const projection = (point: Point) => point[0] * x + point[1] * y
    const a = box.map(projection), b = polygon.map(projection)
    return Math.min(...a) < Math.max(...b) && Math.min(...b) < Math.max(...a)
  })
}

const offsets = [0, -12, 12, -24, 24, -38, 38, -54, 54]
const candidates = offsets.flatMap(y => offsets.map(x => [x, y] as Point))
  .sort((a, b) => Math.hypot(...a) - Math.hypot(...b))

export function calloutCandidates(x: number, y: number, width: number, height: number) {
  return candidates.map(([dx, dy]) => ({ left: x + dx - width / 2, right: x + dx + width / 2,
    top: y + dy - height / 2, bottom: y + dy + height / 2 }))
}
