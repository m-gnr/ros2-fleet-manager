import { memo, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Color, Group, InstancedMesh, Object3D } from 'three'
import { FloorSigns } from './FloorSigns'
import { loadWarehouseDecor } from './warehouseDecor'
import { palletRow, rearRack, sideRack, wallSections, warehouseSize, type DecorBox } from './warehouseLayout'

function Boxes({ name, boxes, cutaway = false }: { name: string; boxes: DecorBox[]; cutaway?: boolean }) {
  const mesh = useRef<InstancedMesh>(null)
  useLayoutEffect(() => {
    const instance = new Object3D()
    const color = new Color()
    boxes.forEach(([x, y, z, w, h, d, paint], index) => {
      instance.position.set(x, y, z)
      instance.scale.set(w, h, d)
      instance.updateMatrix()
      mesh.current!.setMatrixAt(index, instance.matrix)
      mesh.current!.setColorAt(index, color.set(paint))
    })
    mesh.current!.instanceMatrix.needsUpdate = true
    mesh.current!.computeBoundingBox()
    mesh.current!.computeBoundingSphere()
  }, [boxes])

  return <instancedMesh name={name} userData={{ cutaway }} ref={mesh} args={[undefined, undefined, boxes.length]}>
    <boxGeometry />
    <meshStandardMaterial roughness={0.88} />
  </instancedMesh>
}

const paint: DecorBox[] = []
const trim: DecorBox[] = []
const shadows: DecorBox[] = []
const cartons: DecorBox[] = [
  [-2.06, 1.473, -4.95, .36, .26, .42, '#b99568'],
  [1.97, 1.473, -4.97, .41, .26, .47, '#c7a77c'],
  [2.46, 1.505, -4.96, .43, .324, .49, '#b7956d'],
  [2.92, 1.449, -4.95, .36, .212, .39, '#cfb18a'],
]
const fallbackRear: DecorBox[] = []
const fallbackSide: DecorBox[] = []
const fallbackPallets: DecorBox[] = []
const safety = '#bb8a38'
const stripe = '#dcb36b'

function bay(x: number, z: number, width: number, depth: number) {
  paint.push([x, -0.025, z, width, 0.008, depth, '#bfcacc'])
  for (const side of [-1, 1]) {
    paint.push([x + side * width / 2, -0.017, z, 0.034, 0.006, depth, safety])
    paint.push([x, -0.017, z + side * depth / 2, width, 0.006, 0.034, safety])
  }
  shadows.push([x, -0.013, z, width - .14, 0.003, depth - .10, '#a5b2b5'])
}

bay(0, rearRack.z, 8.65, 1.0)
bay(sideRack.x, 0.14, 1.02, 4.74)
bay(3.28, palletRow.z, 3.05, 0.75)

for (const x of [-4.42, 4.43]) {
  paint.push([x, -0.019, 0, 0.031, 0.006, 8.88, stripe])
}
for (const z of [-4.43, 4.42]) {
  paint.push([0, -0.019, z, 8.86, 0.006, 0.031, stripe])
}
for (let index = 0; index < 8; index++) {
  paint.push([-3.75 + index * 0.21, -0.014, 4.94, 0.1, 0.006, 0.54, '#f9f4e6'])
  paint.push([4.92, -0.014, -2.13 + index * 0.21, 0.46, 0.006, 0.1, '#f9f4e6'])
}

// Painted aisle edges and a striped staging apron. These never constrain navigation.
for (const z of [-3.88, 3.56]) {
  for (let x = -3.70; x <= 3.72; x += .74) {
    paint.push([x, -.019, z, .44, .005, .030, '#d4a454'])
  }
}
for (let index = 0; index < 7; index++) {
  paint.push([4.26 + index * .16, -.017, -4.83, .066, .006, .55, '#e8bb61'])
}
paint.push([-2.85, -.019, 4.60, 2.08, .005, .034, stripe],
  [-2.85, -.019, 5.27, 2.08, .005, .034, stripe])
for (const x of [-5.45, 5.45]) {
  trim.push([x, .058, 5.25, .18, .195, .18, '#7d9296'], [x, .157, 5.25, .17, .048, .17, stripe])
}

function schematicRack(x: number, z: number, length: number, height: number, count: number, side = false) {
  const boxes = side ? fallbackSide : fallbackRear
  const box = (along: number, y: number, across: number, w: number, h: number, d: number, color: string) =>
    boxes.push(side ? [x + across, y, z - along, d, h, w, color] : [x + along, y, z + across, w, h, d, color])
  for (let index = 0; index <= count; index++) {
    for (const across of [-.29, .29]) {
      box(length * (index / count - .5), height / 2, across, .065, height, .065, '#738c97')
    }
  }
  for (const level of [.16, .50, .82]) {
    for (const across of [-.29, .29]) box(0, level * height, across, length, .053, .062, '#b78042')
    box(0, level * height, 0, length, .03, .54, '#c2b6a0')
    for (let index = 0; index < count; index++) {
      const middle = length * ((index + .5) / count - .5)
      box(middle, level * height + .035, 0, .74, .038, .49, '#9b815e')
      box(middle, level * height + .14, 0, .66, .18, .45, index % 2 ? '#b9c4c4' : '#c6aa83')
    }
  }
}

schematicRack(0, rearRack.z, 7.6, 1.94, 3)
schematicRack(sideRack.x, .15, 4.25, 1.34, 2, true)
for (const x of palletRow.x) {
  fallbackPallets.push([x, .04, palletRow.z, .94, .09, .61, '#a7875a'],
    [x, .17, palletRow.z, .81, .17, .53, '#b7c3c5'])
}

export const WarehouseEnvironment = memo(function WarehouseEnvironment({ softShadows }: { softShadows: boolean }) {
  const [decor, setDecor] = useState<Group>()
  useEffect(() => {
    let mounted = true
    let release: (() => void) | undefined
    loadWarehouseDecor().then(({ group, dispose }) => {
      if (!mounted) dispose()
      else {
        release = dispose
        setDecor(group)
      }
    }).catch(() => {
      // The schematic remains mounted if the optional local asset cannot be used.
    })
    return () => {
      mounted = false
      release?.()
    }
  }, [])

  return <group name="warehouse-environment">
    <mesh name="warehouse-floor" position={[0, -.107, 0]}>
      <boxGeometry args={[warehouseSize[0], .15, warehouseSize[1]]} />
      <meshStandardMaterial color="#e0e4e3" roughness={0.97} />
    </mesh>
    <gridHelper args={[10.7, 11, '#cbd2d2', '#d3d9d8']} position={[0, -.030, 0]} />
    <Boxes name="safety-markings" boxes={paint} />
    <Boxes name="corner-bollards" boxes={trim} />
    {wallSections.map(({ name, boxes }) => <group key={name} name={name} userData={{ cutaway: true }}>
      <Boxes name={`${name}-panels`} boxes={boxes} />
      {name === 'rear-wall' && <FloorSigns loadingDoor />}
    </group>)}
    {softShadows && <Boxes name="storage-shadows" boxes={shadows} />}
    <FloorSigns />
    {decor ? <group name="warehouse-layout">
      <primitive object={decor} />
      <Boxes name="rear-shelf-cartons" boxes={cartons} cutaway />
    </group>
      : <group name="schematic-warehouse">
        <Boxes name="schematic-rear-rack" boxes={fallbackRear} cutaway />
        <Boxes name="schematic-side-rack" boxes={fallbackSide} cutaway />
        <Boxes name="schematic-pallet-row" boxes={fallbackPallets} cutaway />
      </group>}
  </group>
})
