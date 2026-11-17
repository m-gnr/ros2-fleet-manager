import { useLayoutEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Box3, Color, InstancedMesh, Matrix4, Object3D, Ray, Vector3 } from 'three'
import type { SitePart } from './exteriorSite'

// Three draw calls for the entire static site; cut away each prop's instances together.
export function ExteriorScenery({ parts, enabled }: { parts: SitePart[]; enabled: boolean }) {
  const meshes = useRef(new Map<string, InstancedMesh>()).current
  const { scene, camera } = useThree()
  const batches = useMemo(() => ['box', 'cone', 'round'].map(shape => ({ shape,
    parts: parts.filter(part => part.shape === shape) })), [parts])
  const state = useMemo(() => {
    const props = new Map<string, { box: Box3; hidden: boolean; instances: { shape: string; index: number; matrix: Matrix4 }[] }>()
    const object = new Object3D()
    for (const batch of batches) batch.parts.forEach(({ box, prop }, index) => {
      const [x, y, z, w, h, d] = box
      object.position.set(x, y, z); object.scale.set(w, h, d); object.updateMatrix()
      let record = props.get(prop)
      if (!record) { record = { box: new Box3(), hidden: false, instances: [] }; props.set(prop, record) }
      record.box.expandByPoint(new Vector3(x - w / 2, y - h / 2, z - d / 2))
      record.box.expandByPoint(new Vector3(x + w / 2, y + h / 2, z + d / 2))
      record.instances.push({ shape: batch.shape, index, matrix: object.matrix.clone() })
    })
    for (const record of props.values()) record.box.expandByScalar(.25)
    return { props, ray: new Ray(), hit: new Vector3(), empty: new Matrix4().makeScale(0, 0, 0), signature: '' }
  }, [batches])
  useLayoutEffect(() => {
    const color = new Color()
    for (const batch of batches) {
      const mesh = meshes.get(batch.shape)!
      mesh.raycast = () => {}
      batch.parts.forEach(({ box }, index) => mesh.setColorAt(index, color.set(box[6])))
      for (const record of state.props.values()) for (const instance of record.instances) {
        if (instance.shape === batch.shape) mesh.setMatrixAt(instance.index, record.hidden ? state.empty : instance.matrix)
      }
      mesh.instanceMatrix.needsUpdate = true
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
      mesh.computeBoundingSphere()
    }
  }, [batches, meshes, state])
  useFrame(() => {
    if (!enabled) return
    const targets = [...(scene.getObjectByName('operation-points')?.children ?? []),
      ...scene.children.filter(object => object.name.startsWith('robot-ros-pose:') && object.visible)]
      .map(object => object.getWorldPosition(new Vector3()).add(new Vector3(0, .12, 0)))
    const signature = camera.position.toArray().concat(targets.flatMap(point => point.toArray())).join(',')
    if (signature === state.signature) return
    state.signature = signature
    state.ray.origin.copy(camera.position)
    for (const record of state.props.values()) {
      const hidden = record.box.containsPoint(camera.position) || targets.some(point => {
        const distance = state.ray.direction.copy(point).sub(camera.position).length()
        state.ray.direction.normalize()
        return state.ray.intersectBox(record.box, state.hit) !== null && state.hit.distanceTo(camera.position) < distance
      })
      if (hidden === record.hidden) continue
      record.hidden = hidden
      for (const instance of record.instances) {
        const mesh = meshes.get(instance.shape)!
        mesh.setMatrixAt(instance.index, hidden ? state.empty : instance.matrix)
        mesh.instanceMatrix.needsUpdate = true
      }
    }
  })
  return <group name="exterior-instanced-scenery">
    {batches.map(batch => <instancedMesh key={batch.shape} name={`exterior-${batch.shape}-instances`}
      ref={mesh => { if (mesh) meshes.set(batch.shape, mesh); else meshes.delete(batch.shape) }}
      args={[undefined, undefined, batch.parts.length]} frustumCulled={false}>
      {batch.shape === 'box' ? <boxGeometry /> : batch.shape === 'cone'
        ? <coneGeometry args={[.5, 1, 5]} /> : <icosahedronGeometry args={[.5, 0]} />}
      <meshStandardMaterial roughness={1} metalness={0} flatShading />
    </instancedMesh>)}
  </group>
}
