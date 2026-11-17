import type { GridLayout, MapBounds } from './gridLayout'
import type { OperationPoint } from './operationPoints'
import type { Sign } from './FloorSigns'

type Rect = MapBounds

function overlaps(a: Rect, b: Rect, gap = 0) {
  return a.x_min < b.x_max + gap && a.x_max + gap > b.x_min &&
    a.y_min < b.y_max + gap && a.y_max + gap > b.y_min
}

function signBounds(x: number, y: number, width: number, height: number, vertical: boolean): Rect {
  const halfX = (vertical ? height : width) / 2
  const halfY = (vertical ? width : height) / 2
  return { x_min: x - halfX, x_max: x + halfX, y_min: y - halfY, y_max: y + halfY }
}

function inside(inner: Rect, outer: Rect, margin = 0) {
  return inner.x_min >= outer.x_min + margin && inner.x_max <= outer.x_max - margin &&
    inner.y_min >= outer.y_min + margin && inner.y_max <= outer.y_max - margin
}

function candidates(bounds: Rect) {
  const x = (bounds.x_min + bounds.x_max) / 2
  const y = (bounds.y_min + bounds.y_max) / 2
  const halfX = (bounds.x_max - bounds.x_min) / 2 + 1.2
  const halfY = (bounds.y_max - bounds.y_min) / 2 + 1.2
  const result: { x: number; y: number; cost: number }[] = []
  for (let dx = -halfX; dx <= halfX; dx += .25) {
    for (let dy = -halfY; dy <= halfY; dy += .25) {
      result.push({ x: x + dx, y: y + dy, cost: dx * dx + dy * dy })
    }
  }
  return result.sort((a, b) => a.cost - b.cost)
}

export function floorSignLayout(layout: GridLayout, points: OperationPoint[]): Sign[] {
  const signs: Sign[] = []
  const placed: Rect[] = []
  const obstacles = [
    ...layout.transfer_points.map(point => signBounds(point.pose.x, point.pose.y, 1.3, 1.3, false)),
    ...points.filter(point => point.kind === 'CHARGING' || point.kind === 'PARKING' ||
      point.kind === 'SAFE_WAITING').map(point =>
      signBounds(point.position[0], -point.position[2], 1.3, 1.3, false)),
  ]
  const racks = layout.racks.map(rack => rack.bounds)
  const add = (text: string, area: Rect, width: number, height: number, vertical: boolean,
    sourceZoneId?: string) => {
    for (const candidate of candidates(area)) {
      const box = signBounds(candidate.x, candidate.y, width, height, vertical)
      if (!inside(box, layout.bounds, .12) || racks.some(rack => overlaps(box, rack, .12)) ||
        obstacles.some(point => overlaps(box, point, .08)) || placed.some(other => overlaps(box, other, .2)) ||
        (sourceZoneId && layout.zones.some(zone => zone.id !== sourceZoneId && overlaps(box, zone.bounds, .02)))) continue
      signs.push({ text: text.toLocaleUpperCase('tr'), x: candidate.x, z: -candidate.y,
        width, height, yaw: vertical ? Math.PI / 2 : 0 })
      placed.push(box)
      return
    }
  }
  for (const zone of layout.zones.filter(zone => !layout.transfer_points.some(point =>
    point.zone_id === zone.id && point.rack_id) &&
    !(zone.kind === 'parking' && points.some(point => point.kind === 'PARKING')))) {
    const vertical = zone.kind !== 'parking' &&
      zone.bounds.y_max - zone.bounds.y_min > (zone.bounds.x_max - zone.bounds.x_min) * 1.35
    const width = Math.max(zone.kind === 'charging' ? 2.4 : 1.7, Math.min(3.1, zone.label.length * .21))
    add(zone.label, zone.bounds, width, zone.kind === 'parking' ? .48 : .64, vertical, zone.id)
  }
  for (const aisle of layout.aisles.filter(aisle => aisle.role === 'main')) {
    add(aisle.label, aisle.bounds, 2.75, .58, false)
  }
  return signs
}
