import type { GridLayout } from './gridLayout'
import type { DecorBox } from './warehouseLayout'
import { shippingOpening } from './exteriorLayout'

export type SitePart = { box: DecorBox; prop: string; shape: 'box' | 'cone' | 'round' }
export const exteriorGround = '#d3ddd0'

// Decorative offsets from the verified building footprint; never navigation coordinates.
export function exteriorSite(layout: GridLayout) {
  const b = layout.bounds
  const left = b.x_min - 8, right = b.x_max + 10
  const back = -b.y_max - 7, front = -b.y_min + 7
  const roadZ = front + 5
  const parts: SitePart[] = []
  const paint: DecorBox[] = []
  const add = (prop: string, box: DecorBox, shape: SitePart['shape'] = 'box') => parts.push({ prop, box, shape })
  const gray = '#afb8b1', trim = '#929f96', windows = '#929e99'
  // Fence rails and thin posts, with a 5 m vehicle gate in the front boundary.
  for (const z of [back, front]) for (let x = left; x < right; x += 2) {
    if (z === front && x > left + 1 && x < left + 7) continue
    const span = Math.min(2, right - x), id = `fence-${x}-${z}`
    add(id, [x, .38, z, .06, 1.1, .06, trim])
    for (const y of [.15, .7]) add(id, [x + span / 2, y, z, span, .045, .045, '#adb9af'])
    for (const dx of [.5, 1, 1.5]) if (dx < span) add(id, [x + dx, .42, z, .025, .8, .025, '#b4beb5'])
  }
  for (const x of [left, right]) for (let z = back; z < front; z += 2) {
    const span = Math.min(2, front - z), id = `fence-${x}-${z}`
    add(id, [x, .38, z, .06, 1.1, .06, trim])
    for (const y of [.15, .7]) add(id, [x, y, z + span / 2, .045, .045, span, '#adb9af'])
    for (const dz of [.5, 1, 1.5]) if (dz < span) add(id, [x, .42, z + dz, .025, .8, .025, '#b4beb5'])
  }
  const gateX = left + 5
  for (const x of [gateX - 2.5, gateX + 2.5]) add('gate', [x, .65, front, .18, 1.65, .18, gray])
  // Open, static sliding gate; no robot route is implied.
  add('gate', [gateX + 4.7, .4, front, 4.5, 1.0, .10, '#abb7ad'])
  const building = (id: string, x: number, z: number, w: number, d: number, h: number) => {
    add(id, [x, h / 2 - .17, z, w, h, d, '#c3c6b9'])
    add(id, [x, h - .12, z, w + .16, .12, d + .16, '#adb6ac'])
    add(id, [x, h * .52, z + d / 2 + .012, w * .7, h * .28, .025, windows])
    add(id, [x + w / 2 + .012, h * .5, z, .025, h * .3, d * .55, windows])
    add(id, [x - w * .28, .42, z + d / 2 + .025, .5, 1.1, .035, '#a3aba0'])
  }
  building('guardhouse', gateX + 4.8, front - 1.65, 1.9, 1.65, 1.65)
  building('technical-office', b.x_max + 6.6, -b.y_max - 2.7, 4.2, 3, 2.0)
  for (const [x, z] of [[left + 1, back + 1], [right - 1, back + 1],
    [left + 1, front - 2], [right - 1, front - 2]]) {
    const id = `lamp-${x}-${z}`
    add(id, [x, 1.15, z, .065, 2.6, .065, '#a4afa7'])
    add(id, [x + .25, 2.43, z, .55, .09, .2, '#b7bfb4'])
    add(id, [x + .35, 2.37, z, .28, .025, .15, '#d3d6c8'])
  }
  const palettes = ['#c0c1b6', '#cac7b9', '#b7beb8', '#c5c4b8', '#b9bbb2']
  const parkedCars: DecorBox[] = []
  for (let i = 0; i < 5; i++) {
    const x = b.x_min + 3 + i * 2.35, z = front - 2.3
    parkedCars.push(...carBoxes(x, z, palettes[i]))
    for (const edge of [-1, 1]) paint.push([x + edge, -.146, z, .035, .005, 3.4, '#d5d8cc'])
    paint.push([x, -.146, z - 1.7, 2, .005, .035, '#d5d8cc'])
  }
  for (let x = left - 20; x < right + 20; x += 4) {
    paint.push([x, -.148, roadZ, 1.8, .008, .06, '#d2d5c8'])
  }
  const opening = shippingOpening(layout)
  for (const [x, z] of [[b.x_min - 1.5, -layout.door.center + 3.2],
    [b.x_max + 1.5, -(opening?.center ?? 0) - 3.4]]) {
    for (let i = 0; i < 3; i++) {
      const id = `pallet-${x}-${i}`, pz = z + i * .65
      for (const dx of [-.35, 0, .35]) add(id, [x + dx, -.015, pz, .16, .27, .55, '#b8b19e'])
      add(id, [x, .15, pz, 1, .06, .58, '#c1bba8'])
      if (i !== 1) add(id, [x, .4, pz, .8, .44, .48, '#c5c2b4'])
    }
    add(`container-${x}`, [x + (x < 0 ? -2.2 : 2.2), .55, z - .8, 1.8, 1.45, 2.6, '#b7c0b5'])
    for (let d = -1; d <= 1; d += .4) add(`container-${x}`,
      [x + (x < 0 ? -1.28 : 1.28), .55, z - .8 + d, .04, 1.35, .035, '#aab6ab'])
  }
  // Four small groves; two or three trees each, with scattered low shrubs.
  for (const [cx, cz] of [[left - 1.6, back - 1], [right + 1.8, back - 1],
    [left - 1.8, front + .3], [right + 1.8, front + .3]]) {
    for (let i = 0; i < 3; i++) {
      const x = cx + (i - 1) * 1.15, z = cz + (i % 2) * 1.2, id = `tree-${cx}-${cz}-${i}`
      add(id, [x, .28, z, .15, .9, .15, '#a8af9f'])
      add(id, [x, 1, z, 1.25, i % 2 ? 1.25 : 1.7, 1.25, '#aab99f'], i % 2 ? 'round' : 'cone')
      add(`shrub-${id}`, [x + .6, .08, z - .8, .8, .5, .65, '#b4bfa6'], 'round')
    }
  }
  return { parts, paint, parkedCars, left, right, back, front, roadZ, gateX }
}

export function carBoxes(x: number, z: number, color = '#c9c8bb'): DecorBox[] {
  return [
    [x, .18, z, 1.45, .52, 2.65, color],
    [x, .57, z - .12, 1.22, .42, 1.35, '#a4afa8'],
    [x, .8, z - .12, 1.22, .06, .85, color],
    ...[-1, 1].flatMap(side => [-.83, .83].map(dz =>
      [x + side * .72, .03, z + dz, .12, .4, .48, '#8e978f'] as DecorBox)),
  ]
}
