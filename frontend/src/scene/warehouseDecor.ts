import { Box3, BufferAttribute, BufferGeometry, Group, Mesh, MeshStandardMaterial, Object3D } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'
import { palletRow, rearRack, sideRack, type StorageBounds } from './warehouseLayout'
import warehouseUrl from './assets/warehouse-aisle.glb?url'

const rearParts = /^(00[6-9]|01[0-9]|02[0-46])-/
const sideParts = /^(00[6-9]|010|013|014|018|019|021)-/

export async function loadWarehouseDecor() {
  const { scene } = await new GLTFLoader().loadAsync(warehouseUrl)
  const geometries = new Set<BufferGeometry>()
  const materials = new Set<MeshStandardMaterial>()
  const batches = new Map<MeshStandardMaterial, BufferGeometry[]>()
  const group = new Group()
  group.name = 'warehouse-decor'

  const storageBounds: StorageBounds[] = []
  group.userData.storageBounds = storageBounds

  function bake(part: Object3D, name: string, x: number, z: number,
    scale: readonly [number, number, number], yaw = 0) {
    const bounds = new Box3()
    part.position.set(x, 0, z)
    part.scale.set(...scale)
    part.rotation.y = yaw
    part.updateMatrixWorld(true)
    part.traverse(object => {
      if (!(object instanceof Mesh)) return
      const geometry = new BufferGeometry()
      geometries.add(geometry)
      // Decode quantized attributes before baking transforms into world-space vertices.
      for (const name of ['position', 'normal']) {
        const source = object.geometry.getAttribute(name)
        const values = new Float32Array(source.count * 3)
        for (let i = 0; i < source.count; i++) {
          values[i * 3] = source.getX(i)
          values[i * 3 + 1] = source.getY(i)
          values[i * 3 + 2] = source.getZ(i)
        }
        geometry.setAttribute(name, new BufferAttribute(values, 3))
      }
      geometry.setIndex(object.geometry.index)
      geometry.applyMatrix4(object.matrixWorld)
      geometry.computeBoundingBox()
      bounds.union(geometry.boundingBox!)
      const material = object.material as MeshStandardMaterial
      const batch = batches.get(material) ?? []
      batch.push(geometry)
      batches.set(material, batch)
    })
    if (!bounds.isEmpty()) storageBounds.push({ name, min: bounds.min.toArray(), max: bounds.max.toArray() })
  }

  function dispose() {
    group.traverse(object => {
      if (object instanceof Mesh) {
        object.geometry.dispose()
        object.material.dispose()
      }
    })
  }

  try {
    scene.traverse(object => {
      if (object instanceof Mesh) {
        geometries.add(object.geometry)
        materials.add(object.material)
      }
    })
    const source = scene.getObjectByName('warehouse-aisle')
    if (!source) throw new Error('Warehouse asset is missing its aisle')
    const rear = new Group()
    const side = new Group()
    const pallets = new Group()
    for (const part of source.children) {
      if (rearParts.test(part.name)) {
        const rack = part.clone()
        // The source beams span half the gap between the supplied uprights.
        if (part.name.includes('pallet-rack-beam-level')) rack.scale.x *= 2
        rear.add(rack)
        if (part.name.startsWith('017-')) {
          const topShelf = rack.clone()
          topShelf.position.x = 6.75
          rear.add(topShelf)
        }
        if (sideParts.test(part.name)) side.add(rack.clone())
      }
      if (part.name.startsWith('024-')) {
        const crate = part.clone()
        crate.position.set(4.05, 1.45, 0)
        side.add(crate)
      }
      if (/^(020|026)-/.test(part.name)) {
        const stock = part.clone()
        stock.position.set(palletRow.x[pallets.children.length], 0, 0)
        pallets.add(stock)
      }
    }
    bake(rear, 'rear-rack', rearRack.x, rearRack.z, rearRack.scale)
    bake(side, 'side-rack', sideRack.x, sideRack.z, sideRack.scale, Math.PI / 2)
    bake(pallets, 'pallet-row', 0, palletRow.z, [1, 0.44, 0.70])
    for (const [sourceMaterial, batch] of batches) {
      const geometry = mergeGeometries(batch)
      if (!geometry) throw new Error('Warehouse geometry could not be batched')
      const material = sourceMaterial.clone()
      // Static display lighting has no environment map for fully metallic glTF materials.
      material.metalness = Math.min(material.metalness, 0.24)
      const mesh = new Mesh(geometry, material)
      mesh.name = `warehouse-decor:${material.name}`
      group.add(mesh)
    }
    if (!group.children.length) throw new Error('Warehouse asset has no matching parts')
    return { group, dispose }
  } catch (error) {
    dispose()
    throw error
  } finally {
    for (const geometry of geometries) geometry.dispose()
    for (const material of materials) material.dispose()
  }
}
