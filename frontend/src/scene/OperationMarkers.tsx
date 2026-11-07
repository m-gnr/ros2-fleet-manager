import { memo } from 'react'
import { Path, Shape, Vector2 } from 'three'
import { pointStyle, type OperationPoint } from './operationPoints'

type Vertex = [number, number]

function outline(vertices: Vertex[]) {
  return new Shape().setFromPoints(vertices.map(([x, y]) => new Vector2(x, y)))
}

function inset(shape: Shape, factor: number) {
  return new Path().setFromPoints(shape.getPoints().reverse().map(({ x, y }) => new Vector2(x * factor, y * factor)))
}

function panel(vertices: Vertex[], fill: string, symbols: Shape[]) {
  const border = outline(vertices)
  border.holes.push(inset(border, .90))
  return { pad: outline(vertices), border, fill, symbols }
}

function bay(x: number, y: number): Vertex[] {
  const corner = .055
  return [[-x + corner, -y], [x - corner, -y], [x, -y + corner], [x, y - corner],
    [x - corner, y], [-x + corner, y], [-x, y - corner], [-x, -y + corner]]
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
  pickup: panel(bay(.46, .46), '#9dc8ef', [pickupArrow, carton]),
  dropoff: panel(bay(.46, .46), '#d4b7ec', [dropoffArrow, carton]),
}

function ChargingUnit({ charging }: { charging: boolean }) {
  return <group name="charging-unit" position-x={.57} position-y={-.032}>
    <mesh position-y={.018}>
      <boxGeometry args={[.21, .036, .62]} />
      <meshStandardMaterial color="#284d4c" roughness={.84} />
    </mesh>
    <mesh position={[.022, .134, 0]}>
      <boxGeometry args={[.145, .24, .49]} />
      <meshStandardMaterial color="#2a665f" roughness={.64} />
    </mesh>
    <mesh position={[.022, .251, 0]}>
      <boxGeometry args={[.15, .014, .45]} />
      <meshBasicMaterial color={charging ? '#80e8b9' : '#a4bfba'} />
    </mesh>
  </group>
}

export const OperationMarkers = memo(function OperationMarkers({ points }: { points: OperationPoint[] }) {
  const pickup = points.find(point => point.kind === 'pickup')
  const dropoff = points.find(point => point.kind === 'dropoff')
  const sharedTaskPosition = pickup && dropoff &&
    pickup.position[0] === dropoff.position[0] && pickup.position[2] === dropoff.position[2]

  return <group name="operation-points">
    {points.map(({ key, kind, position, yaw, chargingRobot }) => {
      const { pad, border, fill, symbols } = panels[kind]
      const isTask = kind === 'pickup' || kind === 'dropoff'
      const split = isTask && sharedTaskPosition
      // Raise overlapping paint layers by millimetres to keep their depths distinct.
      const height = kind === 'dropoff' ? -.002 : isTask ? -.006 : -.010
      const color = pointStyle[kind].color
      return <group key={key} name={key} position={position} rotation-y={yaw}>
        <group position-y={height} rotation-y={isTask ? -yaw : 0}>
          <group rotation-x={-Math.PI / 2} position-x={split ? (kind === 'pickup' ? -.23 : .23) : 0}
            scale-x={split ? .5 : 1}>
            <mesh name="operation-pad">
              <shapeGeometry args={[pad]} />
              <meshBasicMaterial color={chargingRobot ? '#88d5bc' : fill} />
            </mesh>
            <mesh name="operation-border" position-z={.001}>
              <shapeGeometry args={[border]} />
              <meshBasicMaterial color={color} />
            </mesh>
            {symbols.length > 0 && <mesh name="operation-symbol" position-z={.002} scale-x={split ? 1.45 : 1}>
              <shapeGeometry args={[symbols]} />
              <meshBasicMaterial color={color} />
            </mesh>}
          </group>
        </group>
        {kind === 'CHARGING' && <ChargingUnit charging={!!chargingRobot} />}
      </group>
    })}
  </group>
})
