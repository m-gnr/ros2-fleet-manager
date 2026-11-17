import { memo, useLayoutEffect, useMemo, useRef } from 'react'
import { BufferGeometry, Color, Float32BufferAttribute, InstancedMesh, Object3D, ShaderMaterial } from 'three'
import type { MapBounds } from './gridLayout'

const gridStep = 1
const gridElevation = -.029
const shadowElevation = -.012

function guidePositions(bounds: MapBounds) {
  const values: number[] = []
  const add = (ax: number, az: number, bx: number, bz: number) => values.push(ax, 0, az, bx, 0, bz)
  const firstX = Math.ceil(bounds.x_min / gridStep) * gridStep
  const firstY = Math.ceil(bounds.y_min / gridStep) * gridStep
  for (let x = firstX; x <= bounds.x_max; x += gridStep) add(x, -bounds.y_max, x, -bounds.y_min)
  for (let y = firstY; y <= bounds.y_max; y += gridStep) add(bounds.x_min, -y, bounds.x_max, -y)
  return new Float32Array(values)
}

export const FloorGuideGrid = memo(function FloorGuideGrid({ bounds }: { bounds: MapBounds }) {
  const positions = useMemo(() => guidePositions(bounds), [bounds])
  const geometry = useMemo(() => {
    const value = new BufferGeometry()
    value.setAttribute('position', new Float32BufferAttribute(positions, 3))
    value.computeBoundingSphere()
    return value
  }, [positions])

  return <lineSegments name="floor-guide-grid" geometry={geometry} position={[0, gridElevation, 0]}
    userData={{ segmentCount: positions.length / 6 }}>
    <lineBasicMaterial color="#9babb5" transparent opacity={.16} depthWrite={false} />
  </lineSegments>
})

const shadowVertex = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);
  }
`

const shadowFragment = `
  uniform vec3 shadowColor;
  uniform float shadowOpacity;
  varying vec2 vUv;
  void main() {
    vec2 edge = abs(vUv - 0.5) * 2.0;
    float distanceToEdge = max(edge.x, edge.y);
    float fade = 1.0 - smoothstep(0.58, 1.0, distanceToEdge);
    gl_FragColor = vec4(shadowColor, fade * shadowOpacity);
  }
`

export const RackContactShadows = memo(function RackContactShadows({ racks }: {
  racks: readonly { bounds: MapBounds }[]
}) {
  const mesh = useRef<InstancedMesh>(null)
  const geometry = useMemo(() => {
    const value = new BufferGeometry()
    value.setAttribute('position', new Float32BufferAttribute([
      -.5, 0, -.5, .5, 0, -.5, .5, 0, .5,
      -.5, 0, -.5, .5, 0, .5, -.5, 0, .5,
    ], 3))
    value.setAttribute('uv', new Float32BufferAttribute([
      0, 0, 1, 0, 1, 1,
      0, 0, 1, 1, 0, 1,
    ], 2))
    value.computeVertexNormals()
    return value
  }, [])
  const material = useMemo(() => new ShaderMaterial({
    transparent: true,
    depthWrite: false,
    vertexShader: shadowVertex,
    fragmentShader: shadowFragment,
    uniforms: {
      shadowColor: { value: new Color('#8295a2') },
      shadowOpacity: { value: .15 },
    },
  }), [])

  useLayoutEffect(() => {
    const instance = new Object3D()
    racks.forEach(({ bounds }, index) => {
      const width = bounds.x_max - bounds.x_min
      const depth = bounds.y_max - bounds.y_min
      instance.position.set((bounds.x_min + bounds.x_max) / 2, shadowElevation,
        -(bounds.y_min + bounds.y_max) / 2)
      instance.scale.set(width + .28, 1, depth + .24)
      instance.updateMatrix()
      mesh.current!.setMatrixAt(index, instance.matrix)
    })
    mesh.current!.instanceMatrix.needsUpdate = true
    mesh.current!.computeBoundingBox()
    mesh.current!.computeBoundingSphere()
  }, [racks])

  return <instancedMesh name="grid-rack-contact-shadows" ref={mesh} args={[geometry, material, racks.length]}
    userData={{ contactShadowCount: racks.length }} />
})
