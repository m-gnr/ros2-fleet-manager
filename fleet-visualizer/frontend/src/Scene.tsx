import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { memo, useLayoutEffect, useRef, type RefObject } from 'react'
import { Group, Quaternion, Vector3 } from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { Burger, burgerSize } from './Burger'
import {
  followTarget, maxCameraDistance, minCameraDistance, startOffset, targetHeight,
  type CameraCommand,
} from './camera'
import { blendMs, blendPose, toScene } from './coordinates'
import type { Pose } from './telemetry'
import type { SceneFeed } from './useTelemetry'
import { Warehouse } from './Warehouse'

type SceneProps = {
  feed: SceneFeed
  command: CameraCommand
  lowQuality: boolean
  label: RefObject<HTMLSpanElement | null>
  trace: boolean
}

const polarLimit = Math.PI / 2 - 0.045
const topAngle = 0.001
const topHeight = 19.8

function Vehicle({ feed, command, lowQuality, label, trace }: SceneProps) {
  const model = useRef<Group>(null)
  const orbit = useRef<OrbitControls | null>(null)
  const lastPose = useRef<Pose>(undefined)
  const tracedPose = useRef<Pose>(undefined)
  const cameraCommand = useRef(command)
  const transitioning = useRef(false)
  const goalTarget = useRef(new Vector3(0, targetHeight, 0))
  const goalOffset = useRef(new Vector3(...startOffset))
  const scratch = useRef({
    shift: new Vector3(), destination: new Vector3(), screen: new Vector3(),
    front: new Vector3(), rotation: new Quaternion(),
  })
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
    const requestFrame = () => invalidate()
    controls.addEventListener('change', requestFrame)
    orbit.current = controls
    const unsubscribe = feed.subscribe(invalidate)
    invalidate()
    return () => {
      unsubscribe()
      controls.removeEventListener('change', requestFrame)
      controls.dispose()
      orbit.current = null
    }
  }, [camera, gl, feed, invalidate])

  useLayoutEffect(() => { invalidate() }, [command, lowQuality, invalidate])

  useFrame(({ size, scene }, delta) => {
    const robot = model.current
    const controls = orbit.current
    if (!robot || !controls) return

    const { pose, previous, status } = feed.read()
    const now = performance.now()
    const displayed = pose && previous ? blendPose(previous, pose, now - pose.receivedAt) : pose
    const { shift, destination, screen, front, rotation } = scratch.current
    const nextMode = command.mode
    const oldCommand = cameraCommand.current
    const priorPose = lastPose.current
    robot.visible = !!displayed
    if (displayed) {
      const [x, z, heading] = toScene(displayed)
      robot.position.set(x, 0, z)
      robot.rotation.y = heading
      if (pose && !priorPose && nextMode === 'free' && !transitioning.current) {
        shift.set(x - controls.target.x, 0, z - controls.target.z)
        camera.position.add(shift)
        controls.target.add(shift)
      }
    }
    lastPose.current = pose

    if (oldCommand !== command) {
      cameraCommand.current = command
      goalTarget.current.copy(controls.target)
      goalOffset.current.copy(camera.position).sub(controls.target)
      if (nextMode === 'top') {
        goalTarget.current.set(0, targetHeight, 0)
        goalOffset.current.set(0, topHeight, topAngle * topHeight)
      } else if (command.reset !== oldCommand.reset || oldCommand.mode === 'top') {
        if (command.reset !== oldCommand.reset) {
          goalTarget.current.set(robot.position.x, targetHeight, robot.position.z)
          if (!pose) goalTarget.current.set(0, targetHeight, 0)
        }
        goalOffset.current.set(...startOffset)
      }
      if (nextMode === 'follow' && goalOffset.current.length() > 3.2) goalOffset.current.setLength(3.2)
      controls.minPolarAngle = 0
      controls.maxPolarAngle = Math.PI / 2
      controls.enableDamping = false
      controls.enabled = false
      transitioning.current = true
    }

    if (nextMode === 'follow' && displayed) {
      const [x, y, z] = followTarget(robot.position.x, robot.position.z)
      goalTarget.current.set(x, y, z)
      if (!transitioning.current && pose !== priorPose && !previous && status === 'LIVE' &&
          controls.target.distanceToSquared(goalTarget.current) > 0.0144) {
        goalOffset.current.copy(camera.position).sub(controls.target)
        if (!priorPose && goalOffset.current.length() > 3.2) goalOffset.current.setLength(3.2)
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
      if ((nextMode === 'follow' && status !== 'LIVE' && displayed) ||
          (camera.position.distanceToSquared(destination) < 0.000025 &&
          controls.target.distanceToSquared(goalTarget.current) < 0.000025)) {
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
    } else if (nextMode === 'follow' && displayed) {
      shift.copy(goalTarget.current).sub(controls.target)
      camera.position.add(shift)
      controls.target.copy(goalTarget.current)
    }
    controls.update()

    if (label.current) {
      if (displayed) {
        screen.copy(robot.position).addScaledVector(camera.up, burgerSize.height + 0.055).project(camera)
      }
      const onScreen = displayed && screen.z >= -1 && screen.z <= 1 &&
        Math.abs(screen.x) < 0.89 && Math.abs(screen.y) < 0.89
      label.current.hidden = !onScreen
      if (onScreen) {
        label.current.style.left = (screen.x + 1) / 2 * size.width + 'px'
        label.current.style.top = (1 - screen.y) / 2 * size.height + 'px'
      }
    }
    if (transitioning.current || displayed !== pose) invalidate()

    if (trace) {
      gl.render(scene, camera)
      if (pose && displayed === pose && tracedPose.current !== pose) {
        tracedPose.current = pose
        // Read the local +Y of the cone, which its own transform turns into the model's +X.
        const marker = robot.getObjectByName('robot-front-marker')!
        front.set(0, 1, 0).applyQuaternion(marker.getWorldQuaternion(rotation))
        gl.domElement.dispatchEvent(new CustomEvent('fleet-visualizer:rendered', {
          bubbles: true,
          detail: { stamp_ns: pose.stamp_ns, stream_id: pose.stream_id, epoch: pose.epoch, x: robot.position.x, z: robot.position.z,
            heading_x: front.x, heading_z: front.z, receive_to_frame_ms: now - pose.receivedAt },
        }))
      }
      gl.domElement.dispatchEvent(new CustomEvent('fleet-visualizer:frame', {
        bubbles: true,
        detail: {
          at: now, interpolating: !!displayed && displayed !== pose, visible: robot.visible,
          blend: displayed && displayed !== pose && pose && previous ? {
            stream_id: pose.stream_id, epoch: pose.epoch, from: previous.stamp_ns, to: pose.stamp_ns,
            fraction: Math.max(0, (now - pose.receivedAt) / blendMs),
          } : undefined,
          pose: robot.position.toArray(), yaw: robot.rotation.y, mode: nextMode, transitioning: transitioning.current,
          target: controls.target.toArray(), camera: camera.position.toArray(),
          calls: gl.info.render.calls, triangles: gl.info.render.triangles,
          geometries: gl.info.memory.geometries, textures: gl.info.memory.textures,
          dpr: gl.getPixelRatio(),
        },
      }))
    }
  }, trace ? 1 : 0)

  return <group ref={model} name="robot-ros-pose" visible={false}>
    <Burger softShadows={!lowQuality} />
  </group>
}

const initialCamera = { position: [startOffset[0], startOffset[1] + targetHeight, startOffset[2]] as [number, number, number], fov: 42, near: 0.035, far: 90 }

export default memo(function Scene(props: SceneProps) {
  return <Canvas frameloop="demand" dpr={props.lowQuality ? 1 : [1, 1.5]} camera={initialCamera}
    fallback={<p className="scene-message">3D görünüm için WebGL desteği gerekiyor.</p>}>
    <color attach="background" args={['#141c27']} />
    <hemisphereLight args={['#d4e6fa', '#657383', 2.3]} />
    <directionalLight position={[2, 8, -3]} intensity={2.2} color="#ffe8ce" />
    <directionalLight position={[-6, 3, 5]} intensity={0.7} color="#bedaff" />
    <Warehouse softShadows={!props.lowQuality} />
    <Vehicle {...props} />
  </Canvas>
})
