export type PlanarPose = { x: number; y: number; yaw: number }
export const blendMs = 45

export function toScene({ x, y, yaw }: PlanarPose): [number, number, number] {
  return [x, -y, yaw]
}

export function blendPose(from: PlanarPose, to: PlanarPose, elapsedMs: number): PlanarPose {
  const fraction = Math.min(1, Math.max(0, elapsedMs / blendMs))
  if (fraction === 1) return to
  if (fraction === 0) return from
  const delta = Math.atan2(Math.sin(to.yaw - from.yaw), Math.cos(to.yaw - from.yaw))
  const yaw = from.yaw + fraction * delta
  return {
    x: from.x + fraction * (to.x - from.x),
    y: from.y + fraction * (to.y - from.y),
    yaw: Math.atan2(Math.sin(yaw), Math.cos(yaw)),
  }
}
