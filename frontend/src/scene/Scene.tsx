import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { memo, useLayoutEffect, useRef } from 'react'
import { Box3, Group, PerspectiveCamera, Quaternion, Vector3 } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { Burger, burgerSize, frontMarkerX } from './Burger'
import {
  followTarget, maxCameraDistance, minCameraDistance, startOffset, targetHeight, topAngle,
  type CameraCommand,
} from './camera'
import { blendMs, blendPose, toScene } from './coordinates'
import { frameWarehouse, warehouseCorners } from './framing'
import { markerDiameter } from './marker'
import { RouteLayers } from './RouteLayers'
import type { RouteOptions } from './routes'
import type { Pose } from './telemetry'
import type { SceneFeed } from './sceneFeed'
import { WarehouseEnvironment } from './Warehouse'
import { OperationMarkers } from './OperationMarkers'
import type { OperationPoint } from './operationPoints'

type SceneProps = {
  feed: SceneFeed
  command: CameraCommand
  lowQuality: boolean
  labels: Map<string, HTMLSpanElement>
  markers: Map<string, HTMLButtonElement>
  points: OperationPoint[]
  pointLabels: Map<string, HTMLSpanElement>
  robotIds: string[]
  selected?: string
  onSelect: (id: string) => void
  trace: boolean
  routes: RouteOptions
}

const polarLimit = Math.PI / 2 - 0.045
const fov = 42

type ScreenRect = { left: number; top: number; right: number; bottom: number }
type LabelPlacement = { label: HTMLSpanElement; candidates: ScreenRect[] }

function overlaps(a: ScreenRect, b: ScreenRect) {
  return a.left < b.right + 4 && a.right + 4 > b.left && a.top < b.bottom + 3 && a.bottom + 3 > b.top
}

function Vehicles({ feed, command, lowQuality, labels, markers, points, pointLabels, robotIds, selected, onSelect, trace, routes }: SceneProps) {
  const models = useRef(new Map<string, Group>()).current
  const orbit = useRef<OrbitControls | null>(null)
  const lastPose = useRef<Pose>(undefined)
  const tracedPoses = useRef(new WeakSet<Pose>()).current
  const previousSelection = useRef<string>(undefined)
  const fitted = useRef(false)
  const cameraCommand = useRef(command)
  const warehouseLayout = useRef<Group>(undefined)
  const warehouseFrame = useRef<Vector3[]>(undefined)
  const aspect = useRef(0)
  const preset = useRef(true)
  const transitioning = useRef(false)
  const goalTarget = useRef(new Vector3(0, targetHeight, 0))
  const goalOffset = useRef(new Vector3(...startOffset))
  const scratch = useRef({
    shift: new Vector3(), destination: new Vector3(), screen: new Vector3(),
    front: new Vector3(), rotation: new Quaternion(), bounds: new Box3(), extent: new Vector3(),
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

  useLayoutEffect(() => { invalidate() }, [command, lowQuality, selected, routes, points, invalidate])
  useLayoutEffect(() => { fitted.current = false }, [routes.selectedOnly, filteredId])

  useFrame(({ size, scene }, delta) => {
    const controls = orbit.current
    if (!controls) return

    const { robots } = feed.read()
    const now = performance.now()
    const { shift, destination, screen, front, rotation, bounds, extent } = scratch.current
    const nextMode = command.mode
    const nextAspect = size.width / size.height
    if (!Number.isFinite(nextAspect) || nextAspect <= 0) return
    const resized = aspect.current !== nextAspect
    const firstFrame = aspect.current === 0
    aspect.current = nextAspect
    const environment = scene.getObjectByName('warehouse-environment')!
    const layout = environment.getObjectByName('warehouse-layout') as Group | undefined
    const layoutChanged = warehouseLayout.current !== layout
    if (!warehouseFrame.current || layoutChanged) {
      warehouseLayout.current = layout
      warehouseFrame.current = warehouseCorners(environment)
      if (trace) gl.domElement.dispatchEvent(new CustomEvent('fleet-visualizer:warehouse-bounds', {
        bubbles: true, detail: warehouseFrame.current.map(corner => corner.toArray()),
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
      if (nextMode === 'follow' && goalOffset.current.length() > 3.2) goalOffset.current.setLength(3.2)
      controls.minPolarAngle = 0
      controls.maxPolarAngle = Math.PI / 2
      controls.enableDamping = false
      controls.enabled = false
      transitioning.current = true
    }

    if (warehouseMode && (restoreWarehouse || ((resized || layoutChanged) && preset.current))) {
      frameWarehouse(warehouseFrame.current, fov, nextAspect, nextMode === 'top', goalTarget.current, goalOffset.current)
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
        if (goalOffset.current.length() > 3.2) goalOffset.current.setLength(3.2)
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

    const placements: LabelPlacement[] = []
    const occupied: ScreenRect[] = []
    const radius = markerDiameter / 2
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

      occupied.push({ left: x - radius, right: x + radius, top: y - radius, bottom: y + radius })
      const left = x - label.offsetWidth / 2
      const right = x + label.offsetWidth / 2
      const height = label.offsetHeight
      const above = y - radius - 4
      const below = y + radius + 4
      const placement = { label, candidates: [{ left, right, top: above - height, bottom: above }] }
      if (id === selected) {
        placement.candidates.push({ left, right, top: below, bottom: below + height })
        placements.unshift(placement)
      } else placements.push(placement)
    }
    for (const point of points) {
      const label = pointLabels.get(point.key)
      if (!label) continue
      screen.fromArray(point.position).project(camera)
      if (Math.abs(screen.x) > 1 || Math.abs(screen.y) > 1 || Math.abs(screen.z) > 1) {
        label.style.visibility = 'hidden'
        continue
      }
      const x = (screen.x + 1) / 2 * size.width
      const y = (1 - screen.y) / 2 * size.height
      const width = label.offsetWidth
      const height = label.offsetHeight
      const gap = 18
      placements.push({ label, candidates: [
        { left: x + gap, right: x + gap + width, top: y - height / 2, bottom: y + height / 2 },
        { left: x - gap - width, right: x - gap, top: y - height / 2, bottom: y + height / 2 },
        { left: x - width / 2, right: x + width / 2, top: y + gap, bottom: y + gap + height },
        { left: x - width / 2, right: x + width / 2, top: y - gap - height, bottom: y - gap },
      ] })
    }
    for (const { label, candidates } of placements) {
      const slot = candidates.find(rect => rect.left >= 3 && rect.right <= size.width - 3 &&
        rect.top >= 3 && rect.bottom <= size.height - 3 && !occupied.some(other => overlaps(rect, other)))
      label.style.visibility = slot ? 'visible' : 'hidden'
      if (!slot) continue
      label.style.transform = `translate(${slot.left}px, ${slot.top}px)`
      occupied.push(slot)
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
          robots: roots, selected, mode: nextMode, transitioning: transitioning.current,
          target: controls.target.toArray(), camera: camera.position.toArray(),
          calls: gl.info.render.calls, triangles: gl.info.render.triangles,
          geometries: gl.info.memory.geometries, textures: gl.info.memory.textures,
          dpr: gl.getPixelRatio(), warehouse: layout ? 'glb' : 'schematic',
          points: points.map(point => {
            const root = scene.getObjectByName(point.key)!
            return { ...point, position: root.getWorldPosition(screen).toArray(), yaw: root.rotation.y }
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
    <Burger softShadows={!lowQuality} />
  </group>)
}

const initialCamera = { position: [8, 11, 10] as [number, number, number], fov, near: 0.035, far: 90 }

export default memo(function Scene(props: SceneProps) {
  return <Canvas frameloop="demand" dpr={props.lowQuality ? 1 : [1, 1.5]} camera={initialCamera}
    fallback={<p className="scene-message">3D görünüm için WebGL desteği gerekiyor.</p>}>
    <color attach="background" args={['#eef2f3']} />
    <hemisphereLight args={['#ffffff', '#c2cbd1', 1.65]} />
    <directionalLight position={[2, 8, -3]} intensity={1.95} color="#fff6e9" />
    <directionalLight position={[-6, 3, 5]} intensity={0.42} color="#e0ecfc" />
    <WarehouseEnvironment softShadows={!props.lowQuality} />
    <OperationMarkers points={props.points} />
    {props.robotIds.map((id, index) => <RouteLayers key={id} feed={props.feed} id={id} colorIndex={index}
      selected={id === props.selected} options={props.routes} trace={props.trace} />)}
    <Vehicles {...props} />
  </Canvas>
})
