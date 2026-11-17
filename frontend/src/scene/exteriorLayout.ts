import type { GridLayout } from './gridLayout'

// Presentation only: this never changes the shared wall, map or navigation payload.
export function shippingOpening(layout: GridLayout) {
  const zone = layout.zones.find(zone => zone.id === 'shipping_zone')
  if (!zone || layout.door.side === 'east') return undefined
  const center = (zone.bounds.y_min + zone.bounds.y_max) / 2
  const width = Math.min(2.4, zone.bounds.y_max - zone.bounds.y_min)
  const wall = layout.walls.find(wall => wall.side === 'east' &&
    wall.bounds.y_min < center - width / 2 && wall.bounds.y_max > center + width / 2)
  return wall ? { center, width, wall } : undefined
}

export function visualWallSections(layout: GridLayout) {
  const opening = shippingOpening(layout)
  return layout.walls.flatMap(wall => wall !== opening?.wall ? [wall] : [
    { ...wall, id: wall.id + '-shipping-a', bounds: { ...wall.bounds, y_max: opening.center - opening.width / 2 } },
    { ...wall, id: wall.id + '-shipping-b', bounds: { ...wall.bounds, y_min: opening.center + opening.width / 2 } },
  ])
}
