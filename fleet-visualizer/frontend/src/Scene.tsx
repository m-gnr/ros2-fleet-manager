import { OrbitControls } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useRef, type ComponentRef } from 'react'
import { Group, Vector3 } from 'three'
import { blendPose, toScene } from './coordinates'
import type { Pose } from './telemetry'

type SceneProps = { pose?: Pose; previous?: Pose; follow: boolean }

function Vehicle({ pose, previous, follow }: SceneProps) {
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null)
  const model = useRef<Group>(null)
  const centered = useRef(false)
  const traced = useRef<Pose>(undefined)
  const shift = useRef(new Vector3())
  const trace = new URLSearchParams(window.location.search).has('trace')

  useFrame(({ camera, gl, invalidate }) => {
    const robot = model.current
    if (!pose || !robot) return

    const now = performance.now()
    const displayed = previous ? blendPose(previous, pose, now - pose.receivedAt) : pose
    const [x, z, heading] = toScene(displayed)
    robot.position.set(x, 0, z)
    robot.rotation.y = heading

    const orbit = controls.current
    if (orbit && (follow || !centered.current)) {
      shift.current.set(x - orbit.target.x, 0, z - orbit.target.z)
      camera.position.add(shift.current)
      orbit.target.add(shift.current)
      orbit.update()
      centered.current = true
    }

    if (displayed !== pose) invalidate()
    if (trace && displayed === pose && traced.current !== pose) {
      traced.current = pose
      // Sample the actual Three object at frame submission, on the browser's own clock.
      const front = new Vector3(1, 0, 0).applyQuaternion(robot.quaternion)
      gl.domElement.dispatchEvent(new CustomEvent('fleet-visualizer:rendered', {
        bubbles: true,
        detail: { stamp_ns: pose.stamp_ns, x: robot.position.x, z: robot.position.z,
          heading_x: front.x, heading_z: front.z, receive_to_frame_ms: now - pose.receivedAt },
      }))
    }
  })

  return <>
    <OrbitControls ref={controls} makeDefault minDistance={1.2} maxDistance={24}
      maxPolarAngle={Math.PI / 2 - 0.06} />
    <group ref={model} visible={!!pose}>
      <mesh position={[0, 0.15, 0]}>
        <cylinderGeometry args={[0.225, 0.24, 0.16, 32]} />
        <meshStandardMaterial color="#2d7888" roughness={0.55} />
      </mesh>
      <mesh position={[0, 0.245, 0]}>
        <cylinderGeometry args={[0.19, 0.19, 0.035, 32]} />
        <meshStandardMaterial color="#c8e5e3" />
      </mesh>
      <mesh position={[-0.06, 0.285, 0]}>
        <cylinderGeometry args={[0.069, 0.069, 0.064, 24]} />
        <meshStandardMaterial color="#172e3a" />
      </mesh>
      {[-0.225, 0.225].map(z => <mesh key={z} position={[0, 0.09, z]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.086, 0.086, 0.046, 20]} />
        <meshStandardMaterial color="#14232c" />
      </mesh>)}
      <mesh position={[0.25, 0.165, 0]}>
        <boxGeometry args={[0.05, 0.055, 0.14]} />
        <meshStandardMaterial color="#f5b767" emissive="#cb7b36" emissiveIntensity={0.7} />
      </mesh>
      <mesh position={[0.37, 0.032, 0]} rotation={[0, 0, -Math.PI / 2]}>
        <coneGeometry args={[0.11, 0.23, 3]} />
        <meshBasicMaterial color="#ffb967" />
      </mesh>
    </group>
  </>
}

export function Scene(props: SceneProps) {
  return <Canvas frameloop="demand" dpr={[1, 1.75]} camera={{ position: [4.8, 6.6, 6.5], fov: 42 }}
    fallback={<p className="scene-error">3D görünüm için WebGL desteği gerekiyor.</p>}>
    <color attach="background" args={['#15252e']} />
    <ambientLight intensity={1.9} />
    <directionalLight position={[4, 7, -2]} intensity={2.2} />
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.012, 0]}>
      <planeGeometry args={[14, 14]} />
      <meshStandardMaterial color="#263d47" roughness={1} />
    </mesh>
    <gridHelper args={[14, 28, '#699097', '#395760']} />
    <axesHelper args={[0.65]} position={[0, 0.006, 0]} />
    <Vehicle {...props} />
  </Canvas>
}
