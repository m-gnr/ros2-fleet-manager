// Display geometry only. The current map's free floor is inside ±4.4 m.
// Keep tall storage behind or beside that floor, and the foreground stock low.
export const warehouseSize = [11.35, 10.95] as const
export const rearRack = { x: -3.8, z: -4.96, scale: [0.94, 0.49, 0.72] } as const
export const sideRack = { x: -4.99, z: 2.28, scale: [0.79, 0.34, 0.72] } as const
export const palletRow = { x: [2.55, 4.02], z: 4.92 } as const

export type StorageBounds = { name: string; min: number[]; max: number[] }
