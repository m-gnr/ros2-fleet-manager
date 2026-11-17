import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { memo, useLayoutEffect, useRef, type RefObject } from 'react'
import { Box3, Group, PerspectiveCamera, Quaternion, Ray, Vector3, type Object3D } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { Burger, burgerSize, frontMarkerX, robotVisualScale } from './Burger'
import {
  followDistance, followTarget, maxCameraDistance, minCameraDistance, startOffset, targetHeight, topAngle,
  type CameraCommand,
} from './camera'
import { blendMs, blendPose, toScene } from './coordinates'
import { frameWarehouse, warehouseCorners } from './framing'
import { markerDiameter } from './marker'
import { RouteLayers } from './RouteLayers'
import type { RouteOptions } from './routes'
import type { Pose } from './telemetry'
import type { SceneFeed } from './sceneFeed'
import { Exterior, exteriorGround } from './Exterior'
import { GridWarehouse } from './GridWarehouse'
import { crossesRack } from './gridClearance'
import type { GridLayout } from './gridLayout'
import { WarehouseEnvironment } from './Warehouse'
import { OperationMarkers } from './OperationMarkers'
import { Costmap, type CostmapGrid } from './Costmap'
import type { ScreenRect } from './calloutPlacement'
import type { OperationPoint } from './operationPoints'
import type { RobotVisualState } from './robotPresentation'

type SceneProps = {
  layout?: GridLayout
  costmap?: CostmapGrid
  feed: SceneFeed
  command: CameraCommand
  lowQuality: boolean
  showExterior: boolean
  labels: Map<string, HTMLSpanElement>
  markers: Map<string, HTMLButtonElement>
  parkLabels: Map<string, HTMLSpanElement>
  points: OperationPoint[]
  activePointKey?: string
  tooltip: RefObject<HTMLDivElement | null>
  onPointHover: (key: string) => void
  onPointLeave: (key: string) => void
  onPointClick: (key: string) => void
  onClearPoint: () => void
  robotIds: string[]
  robotStates: ReadonlyMap<string, RobotVisualState>
  selected?: string
  onSelect: (id: string) => void
  trace: boolean
  routes: RouteOptions
}

const polarLimit = Math.PI / 2 - 0.045
const fov = 42
const calloutOverview = [0.40, 1.50, 0.94] as const

type LabelPlacement = { label: HTMLSpanElement; candidates: ScreenRect[]; scale: number }

function overlaps(a: ScreenRect, b: ScreenRect) {
  return a.left < b.right + 4 && a.right + 4 > b.left && a.top < b.bottom + 3 && a.bottom + 3 > b.top
}

function Vehicles({ layout: grid, feed, command, lowQuality, labels, markers, parkLabels, points, activePointKey, tooltip, robotIds, selected, onSelect, trace, routes }: SceneProps) {
  const models = useRef(new Map<string, Group>()).current
  const orbit = useRef<OrbitControls | null>(null)
  const lastPose = useRef<Pose>(undefined)
  const tracedPoses = useRef(new WeakSet<Pose>()).current
  const previousSelection = useRef<string>(undefined)
  const fitted = useRef(false)
  const cameraCommand = useRef(command)
  const warehouseLayout = useRef<Group>(undefined)
  const warehouseFrame = useRef<Vector3[]>(undefined)
  const cutaways = useRef<{ object: Object3D; bounds: Box3 }[]>([])
  const rackConflicts = useRef(new WeakMap<object, Set<string>>())
  const aspect = useRef(0)
  const preset = useRef(true)
  const transitioning = useRef(false)
  const goalTarget = useRef(new Vector3(0, targetHeight, 0))
  const goalOffset = useRef(new Vector3(...startOffset))
  const scratch = useRef({
    shift: new Vector3(), destination: new Vector3(), screen: new Vector3(),
    front: new Vector3(), rotation: new Quaternion(), bounds: new Box3(), extent: new Vector3(),
    ray: new Ray(), body: new Vector3(), obstruction: new Vector3(),
  })
  const filteredId = routes.selectedOnly ? selected : undefined
  const { camera, gl, invalidate } = useThree()

  useLayoutEffect(() => {
    const controls = new OrbitControls(camera, gl.domElement)
    controls.target.set(0, targetHeight, 0)
    controls.minDistance = minCameraDistance
    controls.maxDistance = maxCameraDistance
    controls.maxPolarAngle = polarLimit
    controls.enableDamping = true
    controls.dampingFactor = 0.16
    controls.update()
    let interacting = false
    const startInteraction = () => { interacting = true }
    const endInteraction = () => { interacting = false }
    const requestFrame = () => {
      if (interacting) preset.current = false
      invalidate()
    }
    controls.addEventListener('change', requestFrame)
    controls.addEventListener('start', startInteraction)
    controls.addEventListener('end', endInteraction)
    orbit.current = controls
    const unsubscribe = feed.subscribe(invalidate)
    invalidate()
    return () => {
      unsubscribe()
      controls.removeEventListener('change', requestFrame)
      controls.removeEventListener('start', startInteraction)
      controls.removeEventListener('end', endInteraction)
      controls.dispose()
      orbit.current = null
    }
  }, [camera, gl, feed, invalidate])

  useLayoutEffect(() => {
    if (!trace) return
    // Trace-only measurement lets Chrome request equal render loads with decoration on/off.
    const request = () => invalidate()
    gl.domElement.addEventListener('fleet-visualizer:benchmark-frame', request)
    return () => gl.domElement.removeEventListener('fleet-visualizer:benchmark-frame', request)
  }, [trace, gl, invalidate])

  useLayoutEffect(() => { invalidate() }, [command, lowQuality, selected, routes, points, activePointKey, invalidate])
  useLayoutEffect(() => { fitted.current = false }, [routes.selectedOnly, filteredId])

  useFrame(({ size, scene }, delta) => {
    const controls = orbit.current
    if (!controls) return

    const { robots } = feed.read()
    const now = performance.now()
    const { shift, destination, screen, front, rotation, bounds, extent, ray, body, obstruction } = scratch.current
    const nextMode = command.mode
    const nextAspect = size.width / size.height
    if (!Number.isFinite(nextAspect) || nextAspect <= 0) return
    const resized = aspect.current !== nextAspect
    const firstFrame = aspect.current === 0
    aspect.current = nextAspect
    const environment = scene.getObjectByName('warehouse-environment')!
    const layout = (environment.getObjectByName('warehouse-grid') ??
      environment.getObjectByName('warehouse-layout')) as Group | undefined
    const layoutChanged = warehouseLayout.current !== layout
    if (!warehouseFrame.current || layoutChanged) {
      warehouseLayout.current = layout
      rackConflicts.current = new WeakMap()
      warehouseFrame.current = warehouseCorners(environment)
      cutaways.current = []
      const decorBounds: { name: string; min: number[]; max: number[] }[] = []
      environment.traverse(object => {
        if (!object.userData.cutaway) return
        const box = new Box3().setFromObject(object)
        if (trace) decorBounds.push({ name: object.name, min: box.min.toArray(), max: box.max.toArray() })
        // Expand the sightline test by the Burger envelope so partial cover also triggers a cutaway.
        box.expandByScalar(Math.hypot(burgerSize.length, burgerSize.width, burgerSize.height) * robotVisualScale / 2)
        cutaways.current.push({ object, bounds: box })
      })
      if (trace) gl.domElement.dispatchEvent(new CustomEvent('fleet-visualizer:warehouse-bounds', {
        bubbles: true, detail: warehouseFrame.current.map(corner => corner.toArray()),
      }))
      if (trace) gl.domElement.dispatchEvent(new CustomEvent('fleet-visualizer:decor-bounds', {
        bubbles: true, detail: { layout: grid ? 'grid' : layout ? 'glb' : 'schematic', boxes: decorBounds },
      }))
      if (trace) gl.domElement.dispatchEvent(new CustomEvent('fleet-visualizer:storage', {
        bubbles: true, detail: layout?.getObjectByName('warehouse-decor')?.userData.storageBounds ?? [],
      }))
    }
    if (resized && preset.current && nextMode === 'fit') fitted.current = false
    const oldCommand = cameraCommand.current
    const priorPose = lastPose.current
    const selectionChanged = selected !== previousSelection.current
    previousSelection.current = selected
    const target = selected ? robots.get(selected) : undefined
    const robot = selected ? models.get(selected) : undefined
    const { pose, previous, status } = target ?? {}
    let interpolating = false
    bounds.makeEmpty()
    for (const [id, root] of models) {
      const sample = robots.get(id)
      const measured = sample?.pose
      const displayed = measured && sample.previous
        ? blendPose(sample.previous, measured, now - measured.receivedAt) : measured
      root.visible = !!displayed && (!routes.selectedOnly || id === selected)
      if (!displayed || !root.visible) continue
      const [x, z, heading] = toScene(displayed)
      root.position.set(x, 0, z)
      root.rotation.y = heading
      bounds.expandByPoint(root.position)
      interpolating ||= displayed !== measured
    }
    lastPose.current = pose

    const changed = oldCommand !== command
    const warehouseMode = nextMode === 'free' || nextMode === 'top'
    const restoreWarehouse = changed && (nextMode === 'top' || command.reset !== oldCommand.reset ||
      (oldCommand.mode === 'top' && nextMode === 'free'))
    if (restoreWarehouse) preset.current = true

    if (changed) {
      cameraCommand.current = command
      goalTarget.current.copy(controls.target)
      goalOffset.current.copy(camera.position).sub(controls.target)
      if (nextMode === 'free' && !restoreWarehouse) preset.current = false
      if (nextMode === 'fit') {
        preset.current = true
        fitted.current = false
      }
      if (nextMode === 'follow' && goalOffset.current.length() > followDistance) goalOffset.current.setLength(followDistance)
      controls.minPolarAngle = 0
      controls.maxPolarAngle = Math.PI / 2
      controls.enableDamping = false
      controls.enabled = false
      transitioning.current = true
    }

    if (warehouseMode && (restoreWarehouse || ((resized || layoutChanged) && preset.current))) {
      frameWarehouse(warehouseFrame.current, fov, nextAspect, nextMode === 'top', goalTarget.current,
        goalOffset.current, grid?.zones.some(zone => zone.callout) ? calloutOverview : undefined)
      if (firstFrame || !transitioning.current) {
        controls.target.copy(goalTarget.current)
        camera.position.copy(goalTarget.current).add(goalOffset.current)
      }
    }

    if (nextMode === 'fit' && !fitted.current && !bounds.isEmpty()) {
      bounds.getCenter(goalTarget.current).setY(targetHeight)
      const radius = bounds.getSize(extent).length() / 2 + 0.55
      const vertical = (camera as PerspectiveCamera).fov * Math.PI / 360
      const horizontal = Math.atan(Math.tan(vertical) * size.width / size.height)
      const distance = radius / Math.sin(Math.min(vertical, horizontal))
      goalOffset.current.set(...startOffset).setLength(Math.min(maxCameraDistance, distance))
      controls.enableDamping = false
      controls.enabled = false
      transitioning.current = true
      fitted.current = true
    }

    if (nextMode === 'follow' && robot?.visible) {
      const [x, y, z] = followTarget(robot.position.x, robot.position.z)
      if (transitioning.current && !changed && !selectionChanged && previous) {
        // Keep the transition converging relative to a continuously moving target.
        shift.set(x, y, z).sub(goalTarget.current)
        controls.target.add(shift)
        camera.position.add(shift)
      }
      goalTarget.current.set(x, y, z)
      if (!transitioning.current && (selectionChanged || (pose !== priorPose && !previous && status === 'LIVE')) &&
          controls.target.distanceToSquared(goalTarget.current) > 0.0144) {
        goalOffset.current.copy(camera.position).sub(controls.target)
        if (goalOffset.current.length() > followDistance) goalOffset.current.setLength(followDistance)
        controls.enableDamping = false
        controls.enabled = false
        transitioning.current = true
      }
    }

    if (transitioning.current) {
      const fraction = 1 - Math.exp(-Math.min(delta, 0.05) * 14)
      destination.copy(goalTarget.current).add(goalOffset.current)
      controls.target.lerp(goalTarget.current, fraction)
      camera.position.lerp(destination, fraction)
      if (camera.position.distanceToSquared(destination) < 0.000025 &&
          controls.target.distanceToSquared(goalTarget.current) < 0.000025) {
        camera.position.copy(destination)
        controls.target.copy(goalTarget.current)
        controls.minPolarAngle = nextMode === 'top' ? topAngle : 0
        controls.maxPolarAngle = nextMode === 'top' ? topAngle : polarLimit
        controls.enableRotate = nextMode !== 'top'
        controls.enablePan = nextMode !== 'follow'
        controls.enableDamping = true
        controls.enabled = true
        transitioning.current = false
      }
    } else if (nextMode === 'follow' && robot?.visible) {
      shift.copy(goalTarget.current).sub(controls.target)
      camera.position.add(shift)
      controls.target.copy(goalTarget.current)
    }
    controls.update()
    camera.updateMatrixWorld()

    const hiddenRacks = new Set<string>()
    if (grid && !grid.approach_clearance_m) {
      const record = <T,>(samples: readonly T[], point: (sample: T) => readonly [number, number],
        starts?: (sample: T) => boolean) => {
        let hits = rackConflicts.current.get(samples)
        if (!hits) {
          hits = new Set()
          for (let i = 0; i < samples.length; i++) {
            const [x, y] = point(samples[i])
            const [a, b] = i && !starts?.(samples[i]) ? point(samples[i - 1]) : [x, y]
            for (const rack of grid.racks) {
              if (!hits.has(rack.id) && crossesRack(rack.bounds, a, b, x, y)) hits.add(rack.id)
            }
          }
          rackConflicts.current.set(samples, hits)
        }
        for (const id of hits) hiddenRacks.add(id)
      }
      for (const sample of robots.values()) {
        if (sample.pose) {
          const { x, y } = sample.pose
          for (const rack of grid.racks) if (crossesRack(rack.bounds, x, y, x, y)) hiddenRacks.add(rack.id)
        }
        if (sample.path?.points) record(sample.path.points, point => point)
        if (sample.trail) record(sample.trail, ({ pose }) => [pose.x, pose.y], point => point.start)
      }
    }
    for (const { object } of cutaways.current) {
      const { side, edge } = object.userData
      const nearWall = (side === 'north' && -camera.position.z > edge) ||
        (side === 'south' && -camera.position.z < edge) ||
        (side === 'east' && camera.position.x > edge) || (side === 'west' && camera.position.x < edge)
      object.visible = !nearWall && !hiddenRacks.has(object.name)
    }
    for (const root of models.values()) {
      if (!root.visible) continue
      body.copy(root.position).addScaledVector(camera.up, burgerSize.height / 2)
      const distance = ray.direction.copy(body).sub(camera.position).length()
      ray.direction.normalize()
      ray.origin.copy(camera.position)
      for (const { object, bounds } of cutaways.current) {
        if (object.visible && (bounds.containsPoint(ray.origin) ||
            (ray.intersectBox(bounds, obstruction) && obstruction.distanceTo(ray.origin) < distance))) {
          object.visible = false
        }
      }
    }

    const placements: LabelPlacement[] = []
    const occupied: ScreenRect[] = []
    const radius = markerDiameter / 2
    const labelScale = (anchor: Vector3) => grid
      ? Math.max(.82, Math.min(1.15, 1.15 - camera.position.distanceTo(anchor) / 65)) : 1
    for (const [id, root] of models) {
      const label = labels.get(id)
      const marker = markers.get(id)
      if (!label || !marker) continue
      screen.copy(root.position).project(camera)
      if (!root.visible || Math.abs(screen.x) > 1 || Math.abs(screen.y) > 1 || Math.abs(screen.z) > 1) {
        marker.style.visibility = label.style.visibility = 'hidden'
        continue
      }

      const x = (screen.x + 1) / 2 * size.width
      const y = (1 - screen.y) / 2 * size.height
      const yaw = root.rotation.y
      front.copy(root.position)
      front.x += frontMarkerX * Math.cos(yaw)
      front.z -= frontMarkerX * Math.sin(yaw)
      front.project(camera)
      const heading = Math.atan2((screen.y - front.y) * size.height, (front.x - screen.x) * size.width)
      marker.style.visibility = 'visible'
      marker.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`
      marker.style.setProperty('--heading', `${heading}rad`)

      const scale = labelScale(root.position)
      const left = x - label.offsetWidth * scale / 2
      const right = x + label.offsetWidth * scale / 2
      const height = label.offsetHeight * scale
      front.copy(root.position)
      front.y += burgerSize.height * robotVisualScale
      front.project(camera)
      const bodyTop = (1 - front.y) / 2 * size.height
      const bodyRadius = grid ? Math.max(radius, Math.abs(y - bodyTop) * 1.45) : radius
      occupied.push({ left: x - bodyRadius, right: x + bodyRadius, top: grid ? Math.min(y - radius, bodyTop) : y - radius,
        bottom: y + radius })
      const above = Math.min(y - radius, bodyTop) - 4
      const below = y + radius + 4
      const sideGap = bodyRadius + 6
      const placement = { label, scale, candidates: [
        { left, right, top: above - height, bottom: above },
        { left, right, top: below, bottom: below + height },
        { left: x - sideGap - label.offsetWidth * scale, right: x - sideGap,
          top: y - height / 2, bottom: y + height / 2 },
        { left: x + sideGap, right: x + sideGap + label.offsetWidth * scale,
          top: y - height / 2, bottom: y + height / 2 },
      ] }
      if (id === selected) {
        placements.unshift(placement)
      } else placements.push(placement)
    }
    for (const { label, candidates, scale } of placements) {
      const slot = candidates.find(rect => rect.left >= 3 && rect.right <= size.width - 3 &&
        rect.top >= 3 && rect.bottom <= size.height - 3 && !occupied.some(other => overlaps(rect, other)))
      label.style.visibility = slot ? 'visible' : 'hidden'
      if (!slot) continue
      label.style.transformOrigin = 'top left'
      label.style.transform = `translate(${slot.left}px, ${slot.top}px) scale(${scale})`
      occupied.push(slot)
    }
    for (const point of points.filter(item => item.kind === 'PARKING')) {
      const label = parkLabels.get(point.key)
      if (!label) continue
      screen.set(point.position[0], 0, point.position[2] - .38).project(camera)
      if (Math.abs(screen.x) > 1 || Math.abs(screen.y) > 1 || Math.abs(screen.z) > 1) {
        label.style.visibility = 'hidden'
        continue
      }
      const x = (screen.x + 1) / 2 * size.width
      const y = (1 - screen.y) / 2 * size.height
      const rect = { left: x - label.offsetWidth / 2, right: x + label.offsetWidth / 2,
        top: y - label.offsetHeight / 2, bottom: y + label.offsetHeight / 2 }
      const visible = rect.left >= 3 && rect.right <= size.width - 3 &&
        rect.top >= 3 && rect.bottom <= size.height - 3 && !occupied.some(other => overlaps(rect, other))
      label.style.visibility = visible ? 'visible' : 'hidden'
      if (visible) {
        label.style.transform = `translate(${rect.left}px, ${rect.top}px)`
        occupied.push(rect)
      }
    }
    const activePoint = points.find(point => point.key === activePointKey)
    const bubble = tooltip.current
    if (bubble && activePoint) {
      screen.fromArray(activePoint.position).project(camera)
      if (Math.abs(screen.x) > 1 || Math.abs(screen.y) > 1 || Math.abs(screen.z) > 1) {
        bubble.style.visibility = 'hidden'
      } else {
        const x = (screen.x + 1) / 2 * size.width
        const y = (1 - screen.y) / 2 * size.height
        const width = bubble.offsetWidth
        const height = bubble.offsetHeight
        const gap = 17
        const candidates: ScreenRect[] = [
          { left: x + gap, right: x + gap + width, top: y - height / 2, bottom: y + height / 2 },
          { left: x - gap - width, right: x - gap, top: y - height / 2, bottom: y + height / 2 },
          { left: x - width / 2, right: x + width / 2, top: y + gap, bottom: y + gap + height },
          { left: x - width / 2, right: x + width / 2, top: y - gap - height, bottom: y - gap },
        ]
        const slot = candidates.find(rect => rect.left >= 3 && rect.right <= size.width - 3 &&
          rect.top >= 3 && rect.bottom <= size.height - 3 && !occupied.some(other => overlaps(rect, other)))
        bubble.style.visibility = slot ? 'visible' : 'hidden'
        if (slot) bubble.style.transform = `translate(${slot.left}px, ${slot.top}px)`
      }
    }
    if (transitioning.current || interpolating) invalidate()

    if (trace) {
      gl.render(scene, camera)
      const roots = []
      for (const [id, root] of models) {
        const sample = robots.get(id)
        const measured = sample?.pose
        const blending = measured && sample.previous && now - measured.receivedAt < blendMs
        const blend = blending && sample.previous ? {
          stream_id: measured.stream_id, epoch: measured.epoch, from: sample.previous.stamp_ns, to: measured.stamp_ns,
          fraction: Math.max(0, (now - measured.receivedAt) / blendMs),
        } : undefined
        screen.copy(root.position).addScaledVector(camera.up, burgerSize.height / 2).project(camera)
        roots.push({ robot_id: id, pose: root.position.toArray(), yaw: root.rotation.y, visible: root.visible,
          status: sample?.status, blend, screen: [(screen.x + 1) / 2, (1 - screen.y) / 2] })
        if (!root.visible || !measured || blending || tracedPoses.has(measured)) continue
        tracedPoses.add(measured)
        const marker = root.getObjectByName('robot-front-marker')!
        front.set(0, 1, 0).applyQuaternion(marker.getWorldQuaternion(rotation))
        gl.domElement.dispatchEvent(new CustomEvent('fleet-visualizer:rendered', {
          bubbles: true,
          detail: { robot_id: id, stamp_ns: measured.stamp_ns, stream_id: measured.stream_id,
            epoch: measured.epoch, x: root.position.x, z: root.position.z,
            heading_x: front.x, heading_z: front.z, receive_to_frame_ms: now - measured.receivedAt },
        }))
      }
      const selectedRoot = roots.find(root => root.robot_id === selected)
      gl.domElement.dispatchEvent(new CustomEvent('fleet-visualizer:frame', {
        bubbles: true,
        detail: {
          at: now, interpolating: !!selectedRoot?.blend, visible: !!selectedRoot?.visible,
          blend: selectedRoot?.blend, pose: selectedRoot?.pose ?? [0, 0, 0], yaw: selectedRoot?.yaw ?? 0,
          robots: roots, selected, mode: nextMode, reset: command.reset, transitioning: transitioning.current,
          target: controls.target.toArray(), camera: camera.position.toArray(),
          calls: gl.info.render.calls, triangles: gl.info.render.triangles,
          geometries: gl.info.memory.geometries, textures: gl.info.memory.textures,
          dpr: gl.getPixelRatio(), warehouse: grid ? 'grid' : layout ? 'glb' : 'schematic',
          exterior: {
            visible: scene.getObjectByName('warehouse-exterior')?.visible ?? false,
            shippingOpening: !!environment.getObjectByName('shipping-visual-opening'),
            cameraBoundsExcludeExterior: !environment.getObjectByName('warehouse-exterior'),
          },
          exteriorMotion: { ...scene.getObjectByName('warehouse-exterior')?.userData.motion },
          surface: {
            floorGridSegments: environment.getObjectByName('floor-guide-grid')?.userData.segmentCount ?? 0,
            rackContactShadows: environment.getObjectByName('grid-rack-contact-shadows')
              ?.userData.contactShadowCount ?? 0,
            shadowMapEnabled: gl.shadowMap.enabled,
          },
          routeHiddenRacks: [...hiddenRacks],
          cutaway: cutaways.current.filter(({ object }) => !object.visible).map(({ object }) => object.name),
          points: points.map(point => {
            const root = scene.getObjectByName(point.key)!
            const dock = root.getObjectByName('charging-unit')
            const pad = root.getObjectByName('operation-pad')!
            const footprint = root.getObjectByName('operation-footprint')
            const symbol = root.getObjectByName('operation-symbol')
            return { ...point,
              padSize: bounds.setFromObject(pad, true).getSize(extent).toArray(),
              footprintSize: footprint ? bounds.setFromObject(footprint, true).getSize(extent).toArray() : undefined,
              padPosition: pad.getWorldPosition(screen).toArray(),
              symbol: !!symbol,
              position: root.getWorldPosition(screen).toArray(), yaw: root.rotation.y,
              dockPosition: dock?.getWorldPosition(screen).toArray(),
              dockBounds: dock ? (() => {
                bounds.setFromObject(dock)
                return { min: bounds.min.toArray(), max: bounds.max.toArray() }
              })() : undefined }
          }),
        },
      }))
    }
  }, trace ? 1 : 0)

  return robotIds.map(id => <group key={id}
    ref={root => { if (root) models.set(id, root); else models.delete(id) }}
    name={`robot-ros-pose:${id}`} visible={false}
    onClick={event => {
      if (event.eventObject.visible && event.delta <= 4) {
        event.stopPropagation()
        onSelect(id)
      }
    }}>
    <group scale={robotVisualScale} name="robot-visual-scale">
      <Burger softShadows={!lowQuality} />
    </group>
  </group>)
}

const initialCamera = { position: [8, 11, 10] as [number, number, number], fov, near: 0.035, far: 240 }

export default memo(function Scene(props: SceneProps) {
  return <Canvas frameloop="demand" dpr={props.lowQuality ? 1 : [1, 1.5]} camera={initialCamera}
    onPointerMissed={props.onClearPoint}
    fallback={<p className="scene-message">3D görünüm için WebGL desteği gerekiyor.</p>}>
    <color attach="background" args={[props.showExterior ? exteriorGround : '#eff4f5']} />
    <hemisphereLight name="warehouse-hemisphere" args={['#f8fbfd', '#c4cfd6', 1.35]} />
    <directionalLight name="warehouse-key-light" position={[-6, 10, 5]} intensity={1.05} color="#f4f8fa" />
    {props.layout ? <GridWarehouse layout={props.layout} points={props.points} softShadows={!props.lowQuality} />
      : <WarehouseEnvironment softShadows={!props.lowQuality} />}
    {props.layout && <Exterior layout={props.layout} visible={props.showExterior} />}
    <OperationMarkers points={props.points} grid={!!props.layout} dockApproach={props.layout?.dock_approach_m}
      onPointHover={props.onPointHover} onPointLeave={props.onPointLeave} onPointClick={props.onPointClick} />
    {props.costmap && <Costmap grid={props.costmap} />}
    {props.robotIds.map(id => <RouteLayers key={id} feed={props.feed} id={id}
      moving={props.robotStates.get(id) === 'active'} selected={id === props.selected}
      options={props.routes} trace={props.trace} />)}
    <Vehicles {...props} />
  </Canvas>
})
