import { memo, useMemo } from 'react'
import { Boxes } from './Warehouse'
import { FloorSigns } from './FloorSigns'
import { rectangle, type GridLayout } from './gridLayout'
import { floorSignLayout } from './floorSignLayout'
import type { OperationPoint } from './operationPoints'
import { FloorGuideGrid, RackContactShadows } from './SurfaceTreatment'
import { shippingOpening, visualWallSections } from './exteriorLayout'
import type { DecorBox } from './warehouseLayout'

const finish = {
  pickup: ['#e5eced', '#a9b9bd'],
  dropoff: ['#e5eced', '#a9b9bd'],
  charging: ['#dce7e3', '#96ada5'],
  parking: ['#e1e6e8', '#a8b6bc'],
} as const

function rackBoxes(rack: GridLayout['racks'][number]): DecorBox[] {
  const { x, z, width, depth } = rectangle(rack.bounds)
  const { height, bays } = rack
  const frame = '#9AAAB6'
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
    boxes.push([x, h, z, width, .044, depth, '#C7D0D7'])
    for (const side of [-1, 1]) boxes.push([x, h, z + side * (depth / 2 - .024), width, .054, .044, frame])
    for (let i = 0; i < bays; i++) {
      const px = x - width / 2 + (i + .5) * bay
      boxes.push([px, h + .095 * height, z, bay * .69, .14 * height, depth * .69, i % 2 ? '#D9E0E5' : '#C8D3DA'])
      boxes.push([px, h + .173 * height, z, bay * .62, .016 * height, depth * .65, '#E1E7EB'])
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
  const deck = rectangle(layout.bounds)
  const doorSide = sides.find(side => side.side === door.side)!
  const inward = door.side === 'north' || door.side === 'east' ? -1 : 1
  const doorX = doorSide.horizontal ? door.center : doorSide.edge + inward * .62
  const doorZ = doorSide.horizontal ? -(doorSide.edge + inward * .62) : -door.center
  paint.push([doorX, -.023, doorZ, doorSide.horizontal ? door.width : 1.24, .008,
    doorSide.horizontal ? 1.24 : door.width, '#c9d3d9'])
  const walls = visualWallSections(layout).map(({ id, side, edge, bounds }) => {
    const { x, z, width, depth } = rectangle(bounds)
    const base: DecorBox[] = [[x, .05, z, width, .10, depth, '#91a2ad']]
    const panels: DecorBox[] = [
      [x, (h+.10)/2, z, width, h-.10, depth, '#b9c6ce'],
      [x, h-.035, z, width, .07, depth, '#8297a4'],
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
  }
  // The former service strip is only floor paint; it has no station or reservation.
  const parkingZone = layout.zones.find(zone => zone.kind === 'parking')
  if (parkingZone && parkingZone.bounds.x_min > 10) {
    paint.push([5.25, -.020, -6.625, 1.38, .006, 3.63, '#e3e9eb'])
  }
  const racks = layout.racks.map(rack => {
    return { id: rack.id, boxes: rackBoxes(rack) }
  })
  return { deck, walls, racks, paint }
}

export const GridWarehouse = memo(function GridWarehouse({ layout, points, softShadows }: {
  layout: GridLayout; points: OperationPoint[]; softShadows: boolean
}) {
  const { deck, walls, racks, paint } = useMemo(() => warehouseGeometry(layout), [layout])
  const pointLocations = points.filter(point => point.kind === 'CHARGING' || point.kind === 'PARKING' ||
    point.kind === 'SAFE_WAITING').map(point => `${point.position[0]},${point.position[2]}`).join(';')
  const signs = useMemo(() => floorSignLayout(layout, points), [layout, pointLocations])
  const opening = shippingOpening(layout)
  const parkZone = layout.zones.find(zone => zone.kind === 'parking')
  const parkPoints = points.filter(point => point.kind === 'PARKING' && parkZone &&
    point.position[0] > parkZone.bounds.x_min && point.position[0] < parkZone.bounds.x_max &&
    -point.position[2] > parkZone.bounds.y_min && -point.position[2] < parkZone.bounds.y_max)
  const parkBays: DecorBox[] = parkPoints.flatMap(point => {
    const [x, , z] = point.position
    const border = '#9eafb7'
    return [
      [x - .75, -.008, z, .025, .005, 1, border],
      [x + .75, -.008, z, .025, .005, 1, border],
      [x, -.008, z - .5, 1.5, .005, .025, border],
      [x, -.008, z + .5, 1.5, .005, .025, border],
    ] as DecorBox[]
  })
  const waitingSign = parkZone && parkZone.bounds.x_min > 10
    ? [{ text: 'BEKLEME ALANI', x: 5.25, z: -6.625, width: 1.15, height: .20 }]
    : []
  return <group name="warehouse-environment">
    <group name="warehouse-grid">
      <mesh name="warehouse-floor" position={[deck.x, -.107, deck.z]}>
        <boxGeometry args={[deck.width, .15, deck.depth]} />
        <meshStandardMaterial color="#e9eff2" roughness={.98} metalness={0} />
      </mesh>
      <FloorGuideGrid bounds={layout.bounds} />
      <Boxes name="grid-markings" boxes={paint} />
      <Boxes name="parking-bays" boxes={parkBays} />
      {walls.map(({ id, side, edge, base, panels }) => <group key={id}>
        <Boxes name={id + '-base'} boxes={base} />
        <group name={id} userData={{ cutaway: true, side, edge }}>
          <Boxes name={id + '-panels'} boxes={panels} />
        </group>
      </group>)}
      {opening && <group name="shipping-visual-opening" userData={{ presentationOnly: true,
        physicalWallUnchanged: true, center: opening.center, width: opening.width }}>
        <Boxes name="shipping-threshold" boxes={[[layout.bounds.x_max, .05, -opening.center,
          layout.wall_thickness_m, .1, opening.width, '#91a2ad']]} />
        <Boxes name="shipping-lintel" boxes={[[layout.bounds.x_max, layout.wall_height_m - .10, -opening.center,
          layout.wall_thickness_m, .20, opening.width, '#8297a4']]} />
      </group>}
      {softShadows && <RackContactShadows racks={layout.racks} />}
      {racks.map(({ id, boxes }) => <group name={id} key={id} userData={{ cutaway: true, gridRack: true }}>
        <Boxes name={id + '-structure'} boxes={boxes} />
      </group>)}
      <FloorSigns custom={[...signs, ...waitingSign]} />
    </group>
  </group>
})
