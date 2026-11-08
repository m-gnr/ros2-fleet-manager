import { memo, useMemo } from 'react'
import { Boxes } from './Warehouse'
import { FloorSigns, type Sign } from './FloorSigns'
import { rectangle, type GridLayout } from './gridLayout'
import type { DecorBox } from './warehouseLayout'

const finish = {
  pickup: ['#b9d7ec', '#477fad'],
  dropoff: ['#dbcae8', '#80599d'],
  charging: ['#b8d9ce', '#408172'],
  parking: ['#ccd4dd', '#627789'],
} as const

function rackBoxes(rack: GridLayout['racks'][number]): DecorBox[] {
  const { x, z, width, depth } = rectangle(rack.bounds)
  const { height, bays } = rack
  const frame = '#526977'
  const boxes: DecorBox[] = []
  const bay = width / bays
  for (let i = 0; i <= bays; i++) {
    for (const side of [-1, 1]) {
      boxes.push([x - width / 2 + .045 + i * (width - .09) / bays, height / 2,
        z + side * (depth / 2 - .045), .09, height, .09, frame])
    }
  }
  for (const level of [.14, .46, .78]) {
    const h = level * height
    boxes.push([x, h, z, width, .052, depth, '#9dabb4'])
    for (const side of [-1, 1]) boxes.push([x, h, z + side * (depth / 2 - .028), width, .075, .056, frame])
    for (let i = 0; i < bays; i++) {
      const px = x - width / 2 + (i + .5) * bay
      boxes.push([px, h + .095 * height, z, bay * .69, .14 * height, depth * .69, i % 2 ? '#b1bbc3' : '#8297a5'])
      boxes.push([px, h + .173 * height, z, bay * .62, .016 * height, depth * .65, '#b9c5cb'])
    }
  }
  return boxes
}

function warehouseGeometry(layout: GridLayout) {
  const { x_min, x_max, y_min, y_max } = layout.bounds
  const { door, wall_height_m: h } = layout
  const sides = [
    { side: 'north', horizontal: true, edge: y_max, start: x_min, end: x_max },
    { side: 'south', horizontal: true, edge: y_min, start: x_min, end: x_max },
    { side: 'west', horizontal: false, edge: x_min, start: y_min, end: y_max },
    { side: 'east', horizontal: false, edge: x_max, start: y_min, end: y_max },
  ] as const
  const paint: DecorBox[] = []
  const shadows: DecorBox[] = []
  const signs: Sign[] = []
  const deck = rectangle(layout.bounds)
  const doorSide = sides.find(side => side.side === door.side)!
  const inward = door.side === 'north' || door.side === 'east' ? -1 : 1
  const doorX = doorSide.horizontal ? door.center : doorSide.edge + inward * .62
  const doorZ = doorSide.horizontal ? -(doorSide.edge + inward * .62) : -door.center
  paint.push([doorX, -.023, doorZ, doorSide.horizontal ? door.width : 1.24, .008,
    doorSide.horizontal ? 1.24 : door.width, '#c9d3d9'])
  signs.push({ text: 'GİRİŞ', x: doorX, z: doorZ + (door.side === 'west' ? .57 : 0), width: 1.24 })
  const walls = layout.walls.map(({ id, side, edge, bounds }) => {
    const { x, z, width, depth } = rectangle(bounds)
    const base: DecorBox[] = [[x, .05, z, width, .10, depth, '#6f8390']]
    const panels: DecorBox[] = [
      [x, (h+.10)/2, z, width, h-.10, depth, '#a4b5c0'],
      [x, h-.035, z, width, .07, depth, '#607a8a'],
    ]
    return { id, side, edge, base, panels }
  })

  for (const aisle of layout.aisles) {
    const { x, z, width, depth } = rectangle(aisle.bounds)
    const alongX = aisle.axis === 'x'
    const pickupAccess = aisle.id === 'pickup_access' || aisle.id === 'pickup_entry'
    const span = alongX ? width : depth
    const edges = alongX ? depth : width
    paint.push([x, alongX ? -.028 : -.023, z, width, .006, depth, pickupAccess ? '#a5c5db' : alongX ? '#d1dce3' : '#dce6eb'])
    for (const side of [-1, 1]) {
      for (let at = -.5 * span + .28; at < .5 * span - .12; at += .50) {
        paint.push(alongX ? [x + at, -.016, z + side * (edges / 2 - .08), .28, .005, .024, '#829ba9']
          : [x + side * (edges / 2 - .08), -.016, z + at, .024, .005, .28, '#829ba9'])
      }
    }
    const signZ = alongX ? z - depth * .25
      : aisle.id === 'aisle_cross_e' ? z + depth / 2 - .29 : z - depth / 2 + .29
    if (!pickupAccess) signs.push({ text: aisle.label, x: alongX ? x + width * (z < 0 ? .24 : -.24) : x,
      z: signZ, width: alongX ? 2.65 : Math.min(1.35, width - .12) })
  }
  const pickupSpine = layout.aisles.find(aisle => aisle.id === 'pickup_access')
  if (pickupSpine) {
    const spine = rectangle(pickupSpine.bounds).x
    for (const point of layout.transfer_points) {
      if (point.kind !== 'pickup') continue
      const { x, y } = point.pose
      paint.push([(spine + x) / 2, -.016, -y, Math.abs(x - spine), .005, .18, '#7fa9c6'])
    }
  }
  for (const zone of layout.zones) {
    const { x, z, width, depth } = rectangle(zone.bounds)
    const [color, border] = finish[zone.kind]
    paint.push([x, -.021, z, width - .12, .006, depth - .12, color])
    for (const side of [-1, 1]) {
      paint.push([x + side * (width / 2 - .06), -.015, z, .032, .006, depth - .12, border],
        [x, -.015, z + side * (depth / 2 - .06), width - .12, .006, .032, border])
    }
    const zoneZ = zone.kind === 'pickup' ? z + depth * .11 :
      zone.kind === 'charging' ? z + depth * .36 : z - depth * (zone.kind === 'dropoff' ? .13 : .36)
    if (!zone.callout) signs.push({ text: zone.label, x, z: zoneZ, width: Math.min(width - .25, 1.65) })
  }
  const racks = layout.racks.map(rack => {
    const { x, z, width, depth } = rectangle(rack.bounds)
    shadows.push([x, -.019, z, width + .025, .005, depth + .025, '#aab9c4'])
    return { id: rack.id, boxes: rackBoxes(rack) }
  })
  return { deck, walls, racks, paint, shadows, signs }
}

export const GridWarehouse = memo(function GridWarehouse({ layout, softShadows }: {
  layout: GridLayout; softShadows: boolean
}) {
  const { deck, walls, racks, paint, shadows, signs } = useMemo(() => warehouseGeometry(layout), [layout])
  return <group name="warehouse-environment">
    <group name="warehouse-grid">
      <mesh name="warehouse-floor" position={[deck.x, -.107, deck.z]}>
        <boxGeometry args={[deck.width, .15, deck.depth]} />
        <meshStandardMaterial color="#e7edf0" roughness={.97} />
      </mesh>
      <Boxes name="grid-markings" boxes={paint} />
      {walls.map(({ id, side, edge, base, panels }) => <group key={id}>
        <Boxes name={id + '-base'} boxes={base} />
        <group name={id} userData={{ cutaway: true, side, edge }}>
          <Boxes name={id + '-panels'} boxes={panels} />
        </group>
      </group>)}
      {softShadows && <Boxes name="grid-rack-shadows" boxes={shadows} />}
      {racks.map(({ id, boxes }) => <group name={id} key={id} userData={{ cutaway: true, gridRack: true }}>
        <Boxes name={id + '-structure'} boxes={boxes} />
      </group>)}
      <FloorSigns custom={signs} />
    </group>
  </group>
})
