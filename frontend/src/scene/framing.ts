import { Box3, Mesh, Vector3, type Object3D } from 'three'
import { maxCameraDistance, minCameraDistance, topOffset, warehouseOffset } from './camera'

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
  const [x, y, z] = top ? topOffset : warehouseOffset
  const back = offset.set(x, y, z).normalize()
  const right = new Vector3(back.z, 0, -back.x).normalize()
  const up = new Vector3().crossVectors(back, right)
  const point = new Vector3()
  const halfFov = Math.tan(fov * Math.PI / 360)
  const horizontal = halfFov * aspect * 0.90
  const vertical = halfFov * (top ? 0.90 : 0.94)
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
  // At distance d, a corner at depth z has a frustum half-span of (d - z) * tan(halfFov).
  // Center between the opposite constraints and use the more restrictive distance.
  const horizontalDistance = (maxX - minX) / (2 * horizontal)
  const verticalDistance = (maxY - minY) / (2 * vertical)
  const distance = Math.max(minCameraDistance, horizontalDistance, verticalDistance)
  target.addScaledVector(right, (maxX + minX) / 2).addScaledVector(up, (maxY + minY) / 2)
  offset.multiplyScalar(Math.min(maxCameraDistance, distance))
}
