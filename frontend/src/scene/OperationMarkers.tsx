import { memo, useMemo } from 'react'
import { Path, Shape, Vector2 } from 'three'
import { pointStyle, type OperationPoint } from './operationPoints'
import { bay, taskPad, taskSquare, type Vertex } from './taskPad'

function outline(vertices: Vertex[]) {
  return new Shape().setFromPoints(vertices.map(([x, y]) => new Vector2(x, y)))
}

function panel(vertices: Vertex[], fill: string, symbols: Shape[]) {
  const border = outline(vertices)
  // Inset towards the polygon centroid so the border also works for clipped pads.
  const center = vertices.reduce(([x, y], [vx, vy]) => [x + vx / vertices.length, y + vy / vertices.length], [0, 0])
  border.holes.push(new Path().setFromPoints([...vertices].reverse().map(([x, y]) =>
    new Vector2(center[0] + (x - center[0]) * .90, center[1] + (y - center[1]) * .90))))
  return { pad: outline(vertices), border, fill, symbols }
}

// Keep the bolt alongside the TF root so a docked robot leaves it visible.
const lightning = outline([[-.33, .20], [-.15, .20], [-.245, .04], [-.14, .04],
  [-.37, -.20], [-.30, -.02], [-.42, -.02]])
const parking = outline([[-.12, -.19], [-.12, .19], [.08, .19], [.16, .13], [.16, .02],
  [.08, -.04], [-.035, -.04], [-.035, .035], [.055, .035], [.08, .06], [.08, .095],
  [.055, .115], [-.035, .115], [-.035, -.19]])
const heading = outline([[.20, -.033], [.30, -.033], [.30, -.095], [.41, 0], [.30, .095], [.30, .033], [.20, .033]])
const pickupArrow = outline([[-.09, .105], [0, .20], [.09, .105], [.034, .105], [.034, .025], [-.034, .025], [-.034, .105]])
const dropoffArrow = outline([[-.09, .12], [0, .025], [.09, .12], [.034, .12], [.034, .20], [-.034, .20], [-.034, .12]])
const carton = outline([[-.13, -.175], [.13, -.175], [.13, -.012], [-.13, -.012]])
carton.holes.push(new Path().moveTo(-.085, -.051).lineTo(-.085, -.136).lineTo(.085, -.136).lineTo(.085, -.051))

const panels = {
  CHARGING: panel(bay(.46, .46), '#a4d8cb', [lightning]),
  PARKING: panel(bay(.46, .46), '#bccbd6', [parking, heading]),
  SAFE_WAITING: panel(bay(.44, .35), '#c4ced1', []),
  pickup: panel(taskSquare, '#9dc8ef', [pickupArrow, carton]),
  dropoff: panel(taskSquare, '#d4b7ec', [dropoffArrow, carton]),
}

function serviceFrame(x: number, y: number) {
  const shape = outline(bay(x, y))
  shape.holes.push(new Path().setFromPoints(bay(x - .04, y - .04).reverse().map(([u, v]) => new Vector2(u, v))))
  return shape
}
const chargingFrame = serviceFrame(.68, 1.02)
const parkFrame = serviceFrame(.75, .64)
const gridCharging = panel(bay(.44, .345), '#a4d8cb', [lightning])
const serviceBorders = {
  CHARGING: [panels.CHARGING.border, chargingFrame],
  PARKING: [panels.PARKING.border, parkFrame],
}

function ChargingUnit({ charging, offset }: { charging: boolean; offset?: number }) {
  return <group name="charging-unit" position={[offset ?? 0, -.032, offset === undefined ? .88 : 0]}
    rotation-y={offset === undefined ? 0 : Math.PI / 2}>
    <mesh position-y={.018}>
      <boxGeometry args={[.62, .036, .21]} />
      <meshStandardMaterial color="#284d4c" roughness={.84} />
    </mesh>
    <mesh position={[0, .134, .022]}>
      <boxGeometry args={[.49, .24, .145]} />
      <meshStandardMaterial color="#2a665f" roughness={.64} />
    </mesh>
    <mesh position={[0, .251, .022]}>
      <boxGeometry args={[.45, .014, .15]} />
      <meshBasicMaterial color={charging ? '#80e8b9' : '#a4bfba'} />
    </mesh>
  </group>
}

export const OperationMarkers = memo(function OperationMarkers({ points, grid = false, dockApproach }: { points: OperationPoint[]; grid?: boolean; dockApproach?: number | null }) {
  const pickup = points.find(point => point.kind === 'pickup' && !point.layoutBay)
  const dropoff = points.find(point => point.kind === 'dropoff' && !point.layoutBay)
  const dx = pickup && dropoff ? dropoff.position[0] - pickup.position[0] : undefined
  const dy = pickup && dropoff ? pickup.position[2] - dropoff.position[2] : undefined
  const clipped = useMemo(() => {
    if (dx === undefined || dy === undefined) return undefined
    const make = (kind: 'pickup' | 'dropoff', x: number, y: number) => {
      const clip = taskPad(x, y, kind === 'pickup')
      return clip && { ...clip, panel: panel(clip.vertices, panels[kind].fill, panels[kind].symbols) }
    }
    return { pickup: make('pickup', dx, dy), dropoff: make('dropoff', -dx, -dy) }
  }, [dx, dy])

  return <group name="operation-points">
    {points.map(({ key, kind, position, yaw, chargingRobot, layoutBay, dockOffset }) => {
      const isTask = kind === 'pickup' || kind === 'dropoff'
      const clip = isTask && !layoutBay ? clipped?.[kind] : undefined
      const { pad, border, fill, symbols } = clip?.panel ?? (grid && kind === 'CHARGING' ? gridCharging : panels[kind])
      const borderShapes = !grid && (kind === 'CHARGING' || kind === 'PARKING') ? serviceBorders[kind] : border
      // Raise overlapping paint layers by millimetres to keep their depths distinct.
      const height = layoutBay ? -.015 : kind === 'dropoff' ? -.002 : isTask ? -.006 : -.010
      const color = pointStyle[kind].color
      return <group key={key} name={key} position={position} rotation-y={yaw}>
        <group position-y={height} rotation-y={isTask ? -yaw : 0}>
          <group rotation-x={-Math.PI / 2}>
            <mesh name="operation-pad">
              <shapeGeometry args={[pad]} />
              <meshBasicMaterial color={chargingRobot ? '#88d5bc' : fill} transparent={layoutBay} opacity={layoutBay ? .38 : 1} />
            </mesh>
            <mesh name="operation-border" position-z={.001}>
              <shapeGeometry args={[borderShapes]} />
              <meshBasicMaterial color={color} />
            </mesh>
            {symbols.length > 0 && <mesh name="operation-symbol" position={[clip?.symbolX ?? 0, clip?.symbolY ?? 0, .002]} scale={clip ? .72 : 1}>
              <shapeGeometry args={[symbols]} />
              <meshBasicMaterial color={color} />
            </mesh>}
          </group>
        </group>
        {grid && kind !== 'PARKING' && <mesh name="approach-arrow" position-y={height + .003} rotation-x={-Math.PI / 2}>
          <shapeGeometry args={[heading]} />
          <meshBasicMaterial color={color} />
        </mesh>}
        {kind === 'CHARGING' && dockApproach && [-.5, .5].map(side =>
          <mesh key={side} position={[-.44 - dockApproach / 2, -.014, side]} rotation-x={-Math.PI / 2}>
            <planeGeometry args={[dockApproach, .025]} />
            <meshBasicMaterial color="#508a7c" />
          </mesh>)}
        {kind === 'CHARGING' && <ChargingUnit charging={!!chargingRobot} offset={dockOffset} />}
      </group>
    })}
  </group>
})
