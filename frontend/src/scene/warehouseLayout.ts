// Display geometry only. The current map's free floor is inside ±4.4 m.
// Keep tall storage behind or beside that floor, and the foreground stock low.
export const warehouseSize = [11.35, 10.95] as const
export const rearRack = { x: -3.8, z: -4.96, scale: [0.94, 0.49, 0.72] } as const
export const sideRack = { x: -4.99, z: 2.28, scale: [0.79, 0.34, 0.72] } as const
export const palletRow = { x: [2.55, 4.02], z: 5.08 } as const

export type StorageBounds = { name: string; min: number[]; max: number[] }

export type DecorBox = [x: number, y: number, z: number, width: number, height: number, depth: number, color: string]

const cladding = '#c3ccce'
const base = '#8d9c9f'
const frame = '#7e9196'
const safety = '#e8b445'

const rearWall: DecorBox[] = [
  [-.83, .25, -5.40, 9.58, .50, .12, base],
  [-.83, 1.43, -5.40, 9.58, 1.86, .11, cladding],
  [0, 2.37, -5.39, 11.25, .085, .16, frame],
  [-.83, .52, -5.33, 9.58, .035, .02, safety],
  // Closed roller shutter and its jambs behind the open staging strip.
  [4.75, 1.13, -5.40, 1.55, 2.26, .10, '#a0b4ba'],
  [4.75, 2.07, -5.30, 1.52, .30, .09, '#395963'],
]
for (const x of [-5.58, -3.24, -.85, 1.54, 3.94, 5.57]) {
  rearWall.push([x, 1.17, -5.30, .09, 2.34, .13, frame])
}
for (let row = 1; row <= 10; row++) {
  rearWall.push([4.75, row * .17, -5.34, 1.54, .022, .022, '#839ba3'])
}
for (const x of [4.03, 5.47]) {
  for (let stripe = 0; stripe < 5; stripe++) {
    rearWall.push([x, .065 + stripe * .09, -5.22, .075, .045, .02, safety])
  }
}

const leftWall: DecorBox[] = [
  [-5.59, .22, -.04, .13, .44, 10.72, base],
  [-5.59, 1.07, -1.45, .12, 1.26, 7.82, cladding],
  [-5.58, 1.73, -1.45, .16, .065, 7.82, frame],
  [-5.50, .47, -1.45, .026, .035, 7.82, safety],
]
for (const z of [-5.30, -3.38, -1.45, .47, 2.42]) {
  leftWall.push([-5.50, .86, z, .12, 1.72, .075, frame])
}

const rightWall: DecorBox[] = [
  [5.60, .14, -2.00, .13, .28, 6.75, base],
  [5.60, .30, -2.00, .15, .045, 6.75, safety],
  [5.60, .60, -4.42, .12, .67, 1.87, cladding],
  [5.59, .96, -4.42, .16, .055, 1.87, frame],
]

export const wallSections = [
  { name: 'rear-wall', boxes: rearWall },
  { name: 'left-wall', boxes: leftWall },
  { name: 'right-wall', boxes: rightWall },
]
