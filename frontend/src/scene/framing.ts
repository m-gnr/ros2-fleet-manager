import { Box3, Mesh, Vector3, type Object3D } from 'three'
import { maxCameraDistance, minCameraDistance, startOffset, topOffset } from './camera'

export function warehouseCorners(warehouse: Object3D) {
  const corners: Vector3[] = []
  const bounds = new Box3()
  warehouse.traverse(object => {
    if (!(object instanceof Mesh)) return
    bounds.setFromObject(object)
    for (const x of [bounds.min.x, bounds.max.x]) {
      for (const y of [bounds.min.y, bounds.max.y]) {
        for (const z of [bounds.min.z, bounds.max.z]) corners.push(new Vector3(x, y, z))
      }
    }
  })
  return corners
}

export function frameWarehouse(corners: Vector3[], fov: number, aspect: number, top: boolean, target: Vector3, offset: Vector3) {
  new Box3().setFromPoints(corners).getCenter(target)
  const [x, y, z] = top ? topOffset : startOffset
  const back = offset.set(x, y, z).normalize()
  const right = new Vector3(back.z, 0, -back.x).normalize()
  const up = new Vector3().crossVectors(back, right)
  const point = new Vector3()
  const vertical = Math.tan(fov * Math.PI / 360) * 0.90
  const horizontal = vertical * aspect
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
  for (const corner of corners) {
    point.copy(corner).sub(target)
    const depth = point.dot(back)
    const px = point.dot(right), py = point.dot(up)
    minX = Math.min(minX, px - depth * horizontal)
    maxX = Math.max(maxX, px + depth * horizontal)
    minY = Math.min(minY, py - depth * vertical)
    maxY = Math.max(maxY, py + depth * vertical)
  }
  // Opposite frustum planes meet at the minimum distance for each axis.
  const distance = Math.max(minCameraDistance, (maxX - minX) / (2 * horizontal), (maxY - minY) / (2 * vertical))
  target.addScaledVector(right, (maxX + minX) / 2).addScaledVector(up, (maxY + minY) / 2)
  offset.multiplyScalar(Math.min(maxCameraDistance, distance))
}
