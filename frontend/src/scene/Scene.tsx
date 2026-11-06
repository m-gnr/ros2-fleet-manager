import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { memo, useLayoutEffect, useRef } from 'react'
import { Box3, Group, PerspectiveCamera, Quaternion, Vector3 } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { Burger, burgerSize } from './Burger'
import {
  followTarget, maxCameraDistance, minCameraDistance, startOffset, targetHeight, topAngle,
  type CameraCommand,
} from './camera'
import { blendMs, blendPose, toScene } from './coordinates'
import { frameWarehouse, warehouseCorners } from './framing'
import { robotColor } from './presentation'
import { RouteLayers } from './RouteLayers'
import type { RouteOptions } from './routes'
import type { Pose } from './telemetry'
import type { SceneFeed } from './sceneFeed'
import { Warehouse } from './Warehouse'

type SceneProps = {
  feed: SceneFeed
  command: CameraCommand
  lowQuality: boolean
  labels: Map<string, HTMLSpanElement>
  robotIds: string[]
  selected?: string
  onSelect: (id: string) => void
  trace: boolean
  routes: RouteOptions
}

const polarLimit = Math.PI / 2 - 0.045
const fov = 42

type LabelPlacement = { label: HTMLSpanElement; left: number; top: number; right: number; bottom: number }

function overlaps(a: LabelPlacement, b: LabelPlacement) {
  return a.left < b.right + 4 && a.right + 4 > b.left && a.top < b.bottom + 3 && a.bottom + 3 > b.top
}

function Vehicles({ feed, command, lowQuality, labels, robotIds, selected, onSelect, trace, routes }: SceneProps) {
  const models = useRef(new Map<string, Group>()).current
  const orbit = useRef<OrbitControls | null>(null)
  const lastPose = useRef<Pose>(undefined)
  const tracedPoses = useRef(new WeakSet<Pose>()).current
  const previousSelection = useRef<string>(undefined)
  const fitted = useRef(false)
  const cameraCommand = useRef(command)
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

  useLayoutEffect(() => { invalidate() }, [command, lowQuality, selected, routes, invalidate])
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
    warehouseFrame.current ??= warehouseCorners(scene.getObjectByName('schematic-warehouse')!)
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

    if (warehouseMode && (restoreWarehouse || (resized && preset.current))) {
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
    for (const [id, root] of models) {
      const label = labels.get(id)
      if (!label) continue
      if (!root.visible) {
        label.style.visibility = 'hidden'
        continue
      }
      screen.copy(root.position).addScaledVector(camera.up, burgerSize.height + 0.055).project(camera)
      const x = (screen.x + 1) / 2 * size.width
      const y = (1 - screen.y) / 2 * size.height - 5
      const width = label.offsetWidth
      const left = x - width / 2
      const top = y - label.offsetHeight
      if (screen.z < -1 || screen.z > 1 || left < 3 || left + width > size.width - 3 || top < 3 || y > size.height) {
        label.style.visibility = 'hidden'
        continue
      }
      const placement = { label, left, top, right: left + width, bottom: y }
      if (id === selected) placements.unshift(placement)
      else placements.push(placement)
    }
    const visible: LabelPlacement[] = []
    for (const placement of placements) {
      const { label, left, top } = placement
      const covered = visible.some(other => overlaps(placement, other))
      label.style.visibility = covered ? 'hidden' : 'visible'
      if (covered) continue
      label.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`
      visible.push(placement)
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
          dpr: gl.getPixelRatio(),
        },
      }))
    }
  }, trace ? 1 : 0)

  return robotIds.map((id, index) => <group key={id}
    ref={root => { if (root) models.set(id, root); else models.delete(id) }}
    name={`robot-ros-pose:${id}`} visible={false}
    onClick={event => {
      if (event.eventObject.visible && event.delta <= 4) {
        event.stopPropagation()
        onSelect(id)
      }
    }}>
    <Burger softShadows={!lowQuality} color={robotColor(index)} selected={id === selected} />
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
    <Warehouse softShadows={!props.lowQuality} />
    {props.robotIds.map((id, index) => <RouteLayers key={id} feed={props.feed} id={id} colorIndex={index}
      selected={id === props.selected} options={props.routes} trace={props.trace} />)}
    <Vehicles {...props} />
  </Canvas>
})
