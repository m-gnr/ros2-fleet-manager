// Coordinates are local to the unchanged task root, in the horizontal scene plane.
export type Vertex = [number, number]

export function bay(x: number, y: number): Vertex[] {
  const corner = .055
  return [[-x + corner, -y], [x - corner, -y], [x, -y + corner], [x, y - corner],
    [x - corner, y], [-x + corner, y], [-x, y - corner], [-x, -y + corner]]
}

export const taskSquare = bay(.46, .46)

export function taskPad(dx: number, dy: number, pickup: boolean) {
  if (Math.abs(dx) >= .92 || Math.abs(dy) >= .92) return undefined
  // Each point keeps its side of the perpendicular bisector. Coincident points
  // get a stable left/right split. The two ROS positions are never changed.
  const distance = Math.hypot(dx, dy)
  const nx = distance ? dx / distance : pickup ? 1 : -1
  const ny = distance ? dy / distance : 0
  const side = ([x, y]: Vertex) => x * nx + y * ny - distance / 2
  const vertices: Vertex[] = []
  for (let i = 0; i < taskSquare.length; i++) {
    const a = taskSquare[i]
    const b = taskSquare[(i + 1) % taskSquare.length]
    const da = side(a), db = side(b)
    if (da <= 0) vertices.push(a)
    if ((da < 0 && db > 0) || (da > 0 && db < 0)) {
      const t = da / (da - db)
      vertices.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
    }
  }
  const shift = Math.max(0, .20 - distance / 2)
  return { vertices, symbolX: -nx * shift, symbolY: -ny * shift }
}
