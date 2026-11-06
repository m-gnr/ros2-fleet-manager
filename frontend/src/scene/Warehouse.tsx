import { memo, useLayoutEffect, useRef } from 'react'
import { InstancedMesh, Object3D } from 'three'

type Box = [x: number, y: number, z: number, width: number, height: number, depth: number]
const warehouseSize = 14

function Boxes({ name, color, boxes }: { name: string; color: string; boxes: Box[] }) {
  const mesh = useRef<InstancedMesh>(null)
  useLayoutEffect(() => {
    const instance = new Object3D()
    boxes.forEach(([x, y, z, w, h, d], index) => {
      instance.position.set(x, y, z)
      instance.scale.set(w, h, d)
      instance.updateMatrix()
      mesh.current!.setMatrixAt(index, instance.matrix)
    })
    mesh.current!.instanceMatrix.needsUpdate = true
    mesh.current!.computeBoundingSphere()
  }, [boxes])

  return <instancedMesh name={name} ref={mesh} args={[undefined, undefined, boxes.length]}>
    <boxGeometry />
    <meshStandardMaterial color={color} roughness={0.88} />
  </instancedMesh>
}

const frames: Box[] = []
const beams: Box[] = []
const shelves: Box[] = []
const crates: Box[] = []
const cartons: Box[] = []
const crateBands: Box[] = []
const shadows: Box[] = []
const zones: Box[] = []
const edges: Box[] = []
const paint: Box[] = []
const curbs: Box[] = []
const stripes: Box[] = []
const rail: Box[] = []

for (const z of [-4.9, 4.9]) {
  zones.push([0, -0.018, z, 11.5, 0.005, 2.4])
  edges.push([0, -0.012, z - 1.2, 11.5, 0.005, 0.025], [0, -0.012, z + 1.2, 11.5, 0.005, 0.025])
  rail.push([0, 0.14, z * 1.29, 12.7, 0.28, 0.13])
  for (const x of [-3.8, 0, 3.8]) {
    shadows.push([x, -0.009, z, 2.96, 0.004, 1.27])
    for (const dx of [-1.3, 1.3]) {
      for (const dz of [-0.43, 0.43]) {
        frames.push([x + dx, 0.79, z + dz, 0.065, 1.58, 0.065])
        curbs.push([x + dx, 0.065, z + dz, 0.13, 0.13, 0.13])
      }
    }
    for (const level of [0.17, 0.75, 1.33]) {
      shelves.push([x, level, z, 2.55, 0.055, 0.84])
      for (const dz of [-0.44, 0.44]) beams.push([x, level, z + dz, 2.66, 0.075, 0.044])
      for (const offset of [-0.85, 0, 0.85]) {
        if (level === 1.33 && offset === 0) continue
        const stack = offset === 0 ? crates : cartons
        const height = offset === 0 ? 0.37 : 0.29
        stack.push([x + offset, level + 0.028 + height / 2, z, 0.65, height, 0.61])
        crateBands.push([x + offset, level + 0.029 + height, z, 0.075, 0.006, 0.615])
      }
    }
  }
}

for (const z of [-2.9, 2.9]) {
  paint.push([0, -0.008, z, 11.4, 0.004, 0.045])
  paint.push([0, -0.008, z + Math.sign(z) * 0.18, 11.4, 0.004, 0.018])
}
for (let x = -5; x <= 5; x++) {
  paint.push([x, -0.007, 0, 0.49, 0.004, 0.026])
}
for (const x of [-5.55, 5.55]) {
  for (let index = -5; index <= 5; index++) {
    stripes.push([x, -0.007, index * 0.48, 0.55, 0.004, 0.21])
  }
  rail.push([x * 1.14, 0.14, 0, 0.13, 0.28, 12.7])
}

export const Warehouse = memo(function Warehouse({ softShadows }: { softShadows: boolean }) {
  return <group name="schematic-warehouse">
    <mesh name="warehouse-floor" position={[0, -0.1, 0]}>
      <boxGeometry args={[warehouseSize, 0.15, warehouseSize]} />
      <meshStandardMaterial color="#e0e5e7" roughness={0.97} />
    </mesh>
    <gridHelper args={[warehouseSize, warehouseSize, '#c7d0d5', '#d2dade']} position={[0, -0.015, 0]} />
    <Boxes name="storage-zones" color="#ced8dc" boxes={zones} />
    <Boxes name="zone-outlines" color="#a8b8c0" boxes={edges} />
    <Boxes name="aisle-markings" color="#f7f9fa" boxes={paint} />
    <Boxes name="walkway-crossings" color="#f5f8f8" boxes={stripes} />
    <Boxes name="perimeter-curbs" color="#c8d2d7" boxes={rail} />
    {softShadows && <Boxes name="shelf-shadows" color="#b6c2c9" boxes={shadows} />}
    <Boxes name="rack-frames" color="#b3c1c9" boxes={frames} />
    <Boxes name="rack-beams" color="#dbe4e8" boxes={beams} />
    <Boxes name="rack-decks" color="#ecf0f1" boxes={shelves} />
    <Boxes name="pallet-cases" color="#c1d0d5" boxes={crates} />
    <Boxes name="pallet-cartons" color="#e8dfd1" boxes={cartons} />
    <Boxes name="case-bands" color="#d2c4b3" boxes={crateBands} />
    <Boxes name="rack-guards" color="#aebdc5" boxes={curbs} />
  </group>
})
