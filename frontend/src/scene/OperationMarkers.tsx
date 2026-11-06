import { memo } from 'react'
import { Shape } from 'three'
import { pointStyle, type OperationPoint } from './operationPoints'

function icon(vertices: [number, number][]) {
  const shape = new Shape()
  shape.moveTo(...vertices[0])
  for (const vertex of vertices.slice(1)) shape.lineTo(...vertex)
  return shape
}

const lightning = icon([[-.045, .2], [.14, .2], [.035, .04], [.15, .04], [-.08, -.2], [-.01, -.02], [-.13, -.02]])
const parking = icon([[-.12, -.19], [-.12, .19], [.08, .19], [.16, .13], [.16, .02],
  [.08, -.04], [-.035, -.04], [-.035, .035], [.055, .035], [.08, .06], [.08, .095],
  [.055, .115], [-.035, .115], [-.035, -.19]])

export const OperationMarkers = memo(function OperationMarkers({ points }: { points: OperationPoint[] }) {
  return <group name="operation-points">
    {points.map(({ key, kind, position, yaw }) => {
      const segments = kind === 'pickup' ? 3 : kind === 'dropoff' ? 4 : 32
      const radius = segments === 32 ? 0.43 : kind === 'dropoff' ? 0.49 : 0.34
      const color = pointStyle[kind].color
      return <group key={key} name={key} position={position} rotation-y={yaw}>
        <group rotation-x={-Math.PI / 2}>
          <mesh position-z={kind === 'dropoff' ? 0.014 : 0.009}>
            {kind === 'dropoff'
              ? <ringGeometry args={[radius * 0.68, radius, segments]} />
              : <circleGeometry args={[radius, segments]} />}
            <meshBasicMaterial color={color} />
          </mesh>
          <mesh position-z={kind === 'dropoff' ? 0.016 : 0.011}>
            <ringGeometry args={[radius * 0.78, radius * 0.89, segments]} />
            <meshBasicMaterial color="#fffaf1" />
          </mesh>
          {(kind === 'CHARGING' || kind === 'PARKING') &&
            <mesh position-z={0.013}>
              <shapeGeometry args={[kind === 'CHARGING' ? lightning : parking]} />
              <meshBasicMaterial color="#fffaf1" />
            </mesh>}
        </group>
      </group>
    })}
  </group>
})
