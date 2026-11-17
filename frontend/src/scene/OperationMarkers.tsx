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
const pickupArrow = outline([[-.15, .04], [0, .21], [.15, .04], [.055, .04], [.055, -.19], [-.055, -.19], [-.055, .04]])
const dropoffArrow = outline([[-.15, -.04], [0, -.21], [.15, -.04], [.055, -.04], [.055, .19], [-.055, .19], [-.055, -.04]])

// Equal visual footprints keep floor marks legible beside racks without moving task poses.
const taskFootprint = panel(bay(.62, .62), '#e9eef0', [])
const dualInnerFrame = panel(bay(.34, .34), '#e7edf0', []).border

const panels = {
  CHARGING: panel(bay(.46, .46), '#dce7e3', [lightning]),
  PARKING: panel(bay(.46, .46), '#e1e6e8', [parking, heading]),
  SAFE_WAITING: panel(bay(.44, .35), '#e1e6e8', []),
  pickup: panel(taskSquare, '#168DA4', [pickupArrow]),
  dropoff: panel(taskSquare, '#e7edf0', [dropoffArrow]),
  neutral: panel(taskSquare, '#e1e6e8', []),
  unknown: panel(taskSquare, '#e7edf0', []),
}

function serviceFrame(x: number, y: number) {
  const shape = outline(bay(x, y))
  shape.holes.push(new Path().setFromPoints(bay(x - .04, y - .04).reverse().map(([u, v]) => new Vector2(u, v))))
  return shape
}
const chargingFrame = serviceFrame(.68, 1.02)
const parkFrame = serviceFrame(.75, .64)
const gridCharging = panel(bay(.44, .345), '#dce7e3', [lightning])
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
      <meshBasicMaterial color={charging ? '#719d8a' : '#a4bfba'} />
    </mesh>
  </group>
}

export const OperationMarkers = memo(function OperationMarkers({ points, grid = false, dockApproach, onPointHover, onPointLeave, onPointClick }: {
  points: OperationPoint[]; grid?: boolean; dockApproach?: number | null
  onPointHover?: (key: string) => void
  onPointLeave?: (key: string) => void
  onPointClick?: (key: string) => void
}) {
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
      const isTransfer = isTask || kind === 'neutral' || kind === 'unknown'
      const clip = isTask && !layoutBay ? clipped?.[kind] : undefined
      const { pad, border, fill, symbols } = clip?.panel ?? (grid && kind === 'CHARGING' ? gridCharging : panels[kind])
      const borderShapes = !grid && (kind === 'CHARGING' || kind === 'PARKING') ? serviceBorders[kind] : border
      // Raise overlapping paint layers by millimetres to keep their depths distinct.
      const height = layoutBay ? -.015 : kind === 'dropoff' ? -.002 : isTask ? -.006 : -.010
      const color = pointStyle[kind].color
      const borderColor = kind === 'neutral' ? pointStyle.pickup.color : color
      return <group key={key} name={key} position={position} rotation-y={yaw}
        onPointerOver={event => {
          event.stopPropagation()
          onPointHover?.(key)
        }}
        onPointerOut={event => { event.stopPropagation(); onPointLeave?.(key) }}
        onClick={event => {
          if (event.delta <= 4) {
            event.stopPropagation()
            onPointClick?.(key)
          }
        }}>
        <group position-y={height} rotation-y={isTransfer ? -yaw : 0}>
          <group rotation-x={-Math.PI / 2}>
            {isTransfer && !clip && <>
              <mesh name="operation-footprint" position-z={-.004}>
                <shapeGeometry args={[taskFootprint.pad]} />
                <meshBasicMaterial color={taskFootprint.fill} />
              </mesh>
              <mesh name="operation-footprint-border" position-z={-.003}>
                <shapeGeometry args={[taskFootprint.border]} />
                <meshBasicMaterial color={borderColor} transparent opacity={.42} />
              </mesh>
            </>}
            <mesh name="operation-pad">
              <shapeGeometry args={[pad]} />
              <meshBasicMaterial color={chargingRobot ? '#b6d1c5' : fill} transparent={kind === 'neutral'} opacity={kind === 'neutral' ? .55 : 1} />
            </mesh>
            <mesh name="operation-border" position-z={.001}>
              <shapeGeometry args={[borderShapes]} />
              <meshBasicMaterial color={borderColor} />
            </mesh>
            {kind === 'neutral' && <mesh name="operation-dual-frame" position-z={.002}>
              <shapeGeometry args={[dualInnerFrame]} />
              <meshBasicMaterial color={pointStyle.dropoff.color} />
            </mesh>}
            {symbols.length > 0 && <mesh name="operation-symbol" position={[clip?.symbolX ?? 0, clip?.symbolY ?? 0, .002]} scale={clip ? .72 : 1}>
              <shapeGeometry args={[symbols]} />
              <meshBasicMaterial color={kind === 'pickup' ? '#ffffff' : color} />
            </mesh>}
          </group>
        </group>
        {grid && kind === 'CHARGING' && <mesh name="approach-arrow" position-y={height + .003} rotation-x={-Math.PI / 2}>
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
