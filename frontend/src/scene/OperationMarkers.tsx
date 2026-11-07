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
  const corner = .09
  return [[-x + corner, -y], [x - corner, -y], [x, -y + corner], [x, y - corner],
    [x - corner, y], [-x + corner, y], [-x, y - corner], [-x, -y + corner]]
}

// Keep the bolt alongside the TF root so a docked robot leaves it visible.
const lightning = outline([[-.425, .20], [-.24, .20], [-.345, .04], [-.23, .04],
  [-.46, -.20], [-.39, -.02], [-.51, -.02]])
const parking = outline([[-.12, -.19], [-.12, .19], [.08, .19], [.16, .13], [.16, .02],
  [.08, -.04], [-.035, -.04], [-.035, .035], [.055, .035], [.08, .06], [.08, .095],
  [.055, .115], [-.035, .115], [-.035, -.19]])
const heading = outline([[.27, -.035], [.37, -.035], [.37, -.105], [.49, 0], [.37, .105], [.37, .035], [.27, .035]])
const pickupArrow = outline([[-.09, .105], [0, .20], [.09, .105], [.034, .105], [.034, .025], [-.034, .025], [-.034, .105]])
const dropoffArrow = outline([[-.09, .12], [0, .025], [.09, .12], [.034, .12], [.034, .20], [-.034, .20], [-.034, .12]])
const carton = outline([[-.13, -.175], [.13, -.175], [.13, -.012], [-.13, -.012]])
carton.holes.push(new Path().moveTo(-.085, -.051).lineTo(-.085, -.136).lineTo(.085, -.136).lineTo(.085, -.051))

const panels = {
  CHARGING: panel(bay(.68, .46), '#b0dcd1', [lightning]),
  PARKING: panel(bay(.59, .40), '#b9cfdf', [parking, heading]),
  SAFE_WAITING: panel(bay(.44, .35), '#c4ced1', []),
  pickup: panel(bay(.33, .30), '#3372ad', [pickupArrow, carton]),
  dropoff: panel([[0, -.40], [.39, 0], [0, .40], [-.39, 0]], '#8058a7', [dropoffArrow, carton]),
}

function ChargingUnit({ charging }: { charging: boolean }) {
  return <group name="charging-unit" position-x={.57}>
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
  return <group name="operation-points">
    {points.map(({ key, kind, position, yaw, chargingRobot }) => {
      const { pad, border, fill, symbols } = panels[kind]
      const isTask = kind === 'pickup' || kind === 'dropoff'
      return <group key={key} name={key} position={position} rotation-y={yaw}>
        <group rotation-x={-Math.PI / 2}>
          <mesh name="operation-pad" position-z={.006}>
            <shapeGeometry args={[pad]} />
            <meshBasicMaterial color={chargingRobot ? '#87ccba' : fill} />
          </mesh>
          <mesh position-z={.010}>
            <shapeGeometry args={[border]} />
            <meshBasicMaterial color={isTask ? '#f8f4ef' : pointStyle[kind].color} />
          </mesh>
          {symbols.length > 0 && <mesh name="operation-symbol" position-z={.013} rotation-z={isTask ? -yaw : 0}>
            <shapeGeometry args={[symbols]} />
            <meshBasicMaterial color={isTask ? '#fffaf1' : pointStyle[kind].color} />
          </mesh>}
        </group>
        {kind === 'CHARGING' && <ChargingUnit charging={!!chargingRobot} />}
      </group>
    })}
  </group>
})
