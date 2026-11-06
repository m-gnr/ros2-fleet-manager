import { memo, useLayoutEffect, useRef } from 'react'
import { DataTexture, LinearFilter, RGBAFormat } from 'three'
import type { Mesh } from 'three'

// Visual envelope in metres, based on the ROBOTIS Burger dimensions.
export const burgerSize = { length: 0.138, width: 0.178, height: 0.192 } as const
export const frontMarkerX = 0.27
const wheelRadius = 0.033
const wheelWidth = 0.024

function ContactShadow() {
  const mesh = useRef<Mesh>(null)
  useLayoutEffect(() => {
    const size = 32
    const pixels = new Uint8Array(size * size * 4)
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const radius = Math.hypot(x + 0.5 - size / 2, y + 0.5 - size / 2) / (size / 2)
        pixels[(y * size + x) * 4 + 3] = Math.round(140 * Math.max(0, 1 - radius) ** 2)
      }
    }
    const texture = new DataTexture(pixels, size, size, RGBAFormat)
    texture.magFilter = LinearFilter
    texture.minFilter = LinearFilter
    texture.needsUpdate = true
    const material = mesh.current!.material
    if (Array.isArray(material) || !('map' in material)) return
    material.map = texture
    material.needsUpdate = true
    return () => { texture.dispose() }
  }, [])

  return <mesh ref={mesh} position={[0, 0.001, 0]} rotation={[-Math.PI / 2, 0, 0]}>
    <planeGeometry args={[0.58, 0.58]} />
    <meshBasicMaterial transparent depthWrite={false} />
  </mesh>
}

export const Burger = memo(function Burger({ softShadows, color, selected }: { softShadows: boolean; color: string; selected: boolean }) {
  return <>
    {softShadows && <ContactShadow />}
    <group name="burger-body">
      {[0.032, 0.088, 0.136].map((y, index) => <mesh key={y} position={[0, y, 0]}>
        <boxGeometry args={[burgerSize.length, 0.009, 0.128]} />
        <meshStandardMaterial color={index === 1 ? '#4c626d' : '#d5a653'} roughness={0.52} />
      </mesh>)}
      <mesh position={[-0.008, 0.061, 0]}>
        <boxGeometry args={[0.104, 0.048, 0.085]} />
        <meshStandardMaterial color="#243441" />
      </mesh>
      <mesh position={[0.015, 0.108, 0]}>
        <boxGeometry args={[0.072, 0.022, 0.078]} />
        <meshStandardMaterial color="#386961" />
      </mesh>
      {[-0.05, 0.05].flatMap(x => [-0.049, 0.049].map(z =>
        <mesh key={x + ':' + z} position={[x, 0.086, z]}>
          <cylinderGeometry args={[0.004, 0.004, 0.1, 8]} />
          <meshStandardMaterial color="#bec6c7" metalness={0.35} roughness={0.42} />
        </mesh>))}
      {[-1, 1].map(side => <group key={side}
        position={[0, wheelRadius, side * (burgerSize.width - wheelWidth) / 2]}
        rotation={[Math.PI / 2, 0, 0]}>
        <mesh>
          <cylinderGeometry args={[wheelRadius, wheelRadius, wheelWidth, 24]} />
          <meshStandardMaterial color="#151d24" />
        </mesh>
        <mesh position={[0, side * 0.011, 0]}>
          <cylinderGeometry args={[0.019, 0.019, 0.004, 16]} />
          <meshStandardMaterial color="#778895" />
        </mesh>
      </group>)}
      <mesh position={[-0.014, 0.155, 0]}>
        <cylinderGeometry args={[0.037, 0.04, 0.03, 24]} />
        <meshStandardMaterial color="#1e2c36" />
      </mesh>
      <mesh position={[-0.014, burgerSize.height - 0.011, 0]}>
        <cylinderGeometry args={[0.033, 0.033, 0.022, 24]} />
        <meshStandardMaterial color="#637e89" roughness={0.42} />
      </mesh>
      <mesh position={[0.069, 0.136, 0]}>
        <boxGeometry args={[0.002, 0.007, 0.049]} />
        <meshBasicMaterial color="#ffd487" />
      </mesh>
    </group>
    <mesh name="robot-locator" position={[0, 0.004, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[selected ? 0.181 : 0.208, 0.238, 48]} />
      <meshBasicMaterial color={color} transparent opacity={selected ? 1 : 0.88} />
    </mesh>
    <mesh name="robot-front-marker" position={[frontMarkerX, 0.015, 0]} rotation={[0, 0, -Math.PI / 2]}>
      <coneGeometry args={[0.058, 0.13, 3]} />
      <meshBasicMaterial color="#ffd487" />
    </mesh>
  </>
})
