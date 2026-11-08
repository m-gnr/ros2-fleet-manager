import { z } from 'zod'

const bounds = z.object({ x_min: z.number(), y_min: z.number(), x_max: z.number(), y_max: z.number() })
const pose = z.object({ x: z.number(), y: z.number(), yaw: z.number() })
const transferKind = z.enum(['pickup', 'dropoff'])
const side = z.enum(['north', 'south', 'east', 'west'])
const area = z.object({ id: z.string(), label: z.string(), bounds })
const layout = z.object({
  frame_id: z.literal('map'), grid_m: z.number().positive(), bounds,
  wall_thickness_m: z.number().positive(), wall_height_m: z.number().positive(),
  door: z.object({ side: side, center: z.number(), width: z.number().positive() }),
  walls: z.array(z.object({ id: z.string(), side, edge: z.number(), bounds })),
  racks: z.array(z.object({ id: z.string(), bounds, height: z.number().positive(), bays: z.number().int().positive() })),
  aisles: z.array(area.extend({ axis: z.enum(['x', 'y']) })),
  zones: z.array(area.extend({ kind: z.enum(['pickup', 'dropoff', 'charging', 'parking']), callout: pose.pick({ x: true, y: true }).nullable().optional() })),
  dock_approach_m: z.number().nullable().optional(),
  transfer_points: z.array(z.object({ id: z.string(), kind: transferKind, pose })),
})

export const layoutResponse = z.object({
  layout: layout.nullable(),
  backend_session_id: z.string().optional(),
  source_session_id: z.string().optional(),
  profile_mismatch: z.boolean().optional(),
})
export type GridLayout = z.infer<typeof layout>
export type MapBounds = z.infer<typeof bounds>

export function rectangle(bounds: MapBounds) {
  return {
    x: (bounds.x_min + bounds.x_max) / 2, z: -(bounds.y_min + bounds.y_max) / 2,
    width: bounds.x_max - bounds.x_min, depth: bounds.y_max - bounds.y_min,
  }
}

export function wallDistance({ bounds }: GridLayout, x: number, z: number, yaw: number) {
  const dx = Math.cos(yaw), dz = -Math.sin(yaw)
  const xHit = Math.abs(dx) < 1e-8 ? Infinity : ((dx > 0 ? bounds.x_max : bounds.x_min) - x) / dx
  const zHit = Math.abs(dz) < 1e-8 ? Infinity : ((dz > 0 ? -bounds.y_min : -bounds.y_max) - z) / dz
  return Math.min(xHit, zHit)
}
