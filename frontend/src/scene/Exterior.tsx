import { memo, useLayoutEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Box3, Group, Mesh, Ray, Vector3 } from 'three'
import { Boxes } from './Warehouse'
import type { DecorBox } from './warehouseLayout'
import type { GridLayout } from './gridLayout'
import { shippingOpening } from './exteriorLayout'

import { carBoxes, exteriorPalette, exteriorSite } from './exteriorSite'
import { ExteriorScenery } from './ExteriorScenery'
import { useExteriorMotion } from './exteriorMotion'
export { exteriorGround } from './exteriorSite'
import { exteriorGround } from './exteriorSite'
const gray = '#b4bfbb'
const dark = '#75817e'

function Dock({ width, shipping = false }: { width: number; shipping?: boolean }) {
  const boxes = useMemo<DecorBox[]>(() => [
    // Raised apron and closed shutter indicate freight handling, never a robot corridor.
    [1, .11, 0, 1.9, .34, width + .5, gray],
    ...(shipping ? [[.09, .78, 0, .12, 1.35, width, '#a2afac'] as DecorBox,
    [.18, 1.51, 0, .24, .12, width + .25, dark] as DecorBox,
    ...[-1, 1].map(sign => [.18, .77, sign * (width / 2 + .07), .24, 1.5, .14, dark] as DecorBox),
    ...[.40, .68, .96, 1.24].map(y => [.16, y, 0, .02, .025, width - .12, '#8d9c97'] as DecorBox)] : []),
    [1.95, .26, 0, .14, .12, width + .5, dark],
    ...(shipping ? [[.23, .26, -width / 2 + .2, .28, .18, .14, dark] as DecorBox,
      [.23, .26, width / 2 - .2, .28, .18, .14, dark] as DecorBox] : []),
  ], [width, shipping])
  return <Boxes name={shipping ? 'shipping-loading-dock' : 'receiving-loading-dock'} boxes={boxes} />
}

function Truck({ name = "receiving-stationary-truck" }: { name?: string }) {
  const boxes = useMemo<DecorBox[]>(() => [
    [0, .87, 0, 3.5, 1.35, 1.55, '#c2cbc7'],
    [.2, .19, 0, 4.4, .22, 1.42, dark],
    [2.22, .66, 0, 1.1, .98, 1.48, '#a8b8ae'],
    [2.5, .91, 0, .36, .40, 1.5, '#7d8d89'],
    [2.82, .35, 0, .12, .16, 1.5, gray],
    ...[-1.06, 1.99].flatMap(x => [-1, 1].map(sign =>
      [x, .12, sign * .74, .52, .45, .16, '#67716e'] as DecorBox)),
  ], [])
  return <Boxes name={name} boxes={boxes} />
}

// Hide foreground props when their silhouettes would cover a robot or operation point.
function SightlineProp({ children, position, rotation = 0, name, enabled }: {
  children: React.ReactNode; position: [number, number, number]; rotation?: number; name: string; enabled: boolean
}) {
  const root = useRef<Group>(null)
  const { scene, camera } = useThree()
  const scratch = useMemo(() => ({ box: new Box3(), ray: new Ray(), hit: new Vector3(), point: new Vector3() }), [])
  useFrame(() => {
    if (!enabled) return
    const group = root.current!
    group.visible = true
    const { box, ray, hit, point } = scratch
    box.setFromObject(group).expandByScalar(.12)
    ray.origin.copy(camera.position)
    const targets = [...(scene.getObjectByName('operation-points')?.children ?? []),
      ...scene.children.filter(object => object.name.startsWith('robot-ros-pose:') && object.visible)]
    for (const object of targets) {
      if (!group.visible) break
      object.getWorldPosition(point)
      const distance = ray.direction.copy(point).sub(ray.origin).length()
      ray.direction.normalize()
      if (box.containsPoint(ray.origin) || ray.intersectBox(box, hit) && hit.distanceTo(ray.origin) < distance) {
        group.visible = false
      }
    }
  }, 0)
  return <group ref={root} name={name} position={position} rotation-y={rotation}>{children}</group>
}

export const Exterior = memo(function Exterior({ layout, visible }: { layout: GridLayout; visible: boolean }) {
  const root = useRef<Group>(null)
  const opening = shippingOpening(layout)
  const b = layout.bounds
  const site = useMemo(() => exteriorSite(layout), [layout])
  const road = useMemo(() => ({ left: site.left, right: site.right, roadZ: site.roadZ,
    truckX: b.x_max + 4.05 }), [site, b.x_max])
  useExteriorMotion(root, visible, road)
  const movingCar = useMemo(() => carBoxes(0, 0), [])
  useLayoutEffect(() => {
    // No exterior object participates in R3F pointer picking, even if a parent later adds handlers.
    root.current?.traverse(object => { if (object instanceof Mesh) object.raycast = () => {} })
  }, [])
  // This root is deliberately a sibling of warehouse-environment, outside all camera framing bounds.
  return <group ref={root} name="warehouse-exterior" visible={visible}>
    <mesh name="exterior-ground" position={[0, -.185, 0]} rotation-x={-Math.PI / 2}>
      <planeGeometry args={[2000, 2000]} />
      <meshBasicMaterial color={exteriorGround} />
    </mesh>
    <mesh name="exterior-courtyard" position={[(site.left + site.right) / 2, -.17, (site.back + site.front) / 2]}
      rotation-x={-Math.PI / 2}>
      <planeGeometry args={[site.right - site.left + 1, site.front - site.back + 1]} />
      <meshBasicMaterial color={exteriorPalette.courtyard} />
    </mesh>
    <mesh name="exterior-two-lane-road" position={[0, -.16, site.roadZ]} rotation-x={-Math.PI / 2}>
      <planeGeometry args={[240, 5.6]} /><meshBasicMaterial color={exteriorPalette.road} />
    </mesh>
    <Boxes name="exterior-sidewalk" unlit boxes={[
      [0, -.13, site.roadZ - 3.25, 240, .08, .85, exteriorPalette.sidewalk],
      [site.gateX, -.155, (site.front + site.roadZ - 3) / 2, 5, .02, site.roadZ - 3 - site.front, exteriorPalette.courtyard],
    ]} />
    <Boxes name="exterior-road-parking-paint" boxes={site.paint} />
    <ExteriorScenery parts={site.parts} enabled={visible} />
    <SightlineProp enabled={visible} name="parked-car-cutaway" position={[0, 0, 0]}>
      <Boxes name="five-parked-cars" boxes={site.parkedCars} />
    </SightlineProp>
    <group name="road-car-motion" rotation-y={Math.PI / 2}>
      <SightlineProp enabled={visible} name="road-car-cutaway" position={[0, 0, 0]}>
        <Boxes name="single-decorative-road-car" boxes={movingCar} />
      </SightlineProp>
    </group>
    {opening && <group name="shipping-truck-motion" position={[road.truckX, 0, -opening.center]}>
      <SightlineProp enabled={visible} name="shipping-truck-cutaway" position={[0, 0, 0]}>
        <Truck name="decorative-shipping-truck" />
      </SightlineProp>
    </group>}
    {layout.door.side === 'west' && <>
      <SightlineProp enabled={visible} name="receiving-dock" position={[b.x_min - .06, 0, -layout.door.center]} rotation={Math.PI}>
        <Dock width={layout.door.width} />
      </SightlineProp>
      <SightlineProp enabled={visible} name="receiving-truck" position={[b.x_min - 4.05, 0, -layout.door.center]} rotation={Math.PI}>
        <Truck />
      </SightlineProp>
    </>}
    {opening && <SightlineProp enabled={visible} name="shipping-dock" position={[b.x_max + .06, 0, -opening.center]}>
      <Dock width={opening.width} shipping />
    </SightlineProp>}

  </group>
})
