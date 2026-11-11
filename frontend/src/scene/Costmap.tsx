import { useEffect, useMemo, useState } from 'react'
import { DataTexture, NearestFilter, RGBAFormat } from 'three'
import { z } from 'zod'

const gridSchema = z.object({
  frame_id: z.literal('map'), resolution: z.number().positive(),
  width: z.number().int().positive(), height: z.number().int().positive(),
  origin: z.tuple([z.number(), z.number()]),
  source: z.enum(['generated_occupancy', 'nav2_recorded']),
  runs: z.array(z.tuple([z.number().int().min(-1).max(100), z.number().int().positive()])),
}).refine(grid => grid.width * grid.height <= 4_000_000 &&
  grid.runs.reduce((sum, [, count]) => sum + count, 0) === grid.width * grid.height)
export type CostmapGrid = z.infer<typeof gridSchema>

export function useCostmap(session?: string) {
  const [result, setResult] = useState<{ session: string; grid: CostmapGrid }>()
  useEffect(() => {
    if (!session) return
    const request = new AbortController()
    void fetch('/api/warehouse-costmap', { signal: request.signal }).then(async response => {
      if (!response.ok) return
      const parsed = gridSchema.safeParse(await response.json())
      if (parsed.success && !request.signal.aborted) setResult({ session, grid: parsed.data })
    }).catch(() => {})
    return () => request.abort()
  }, [session])
  return result && result.session === session ? result.grid : undefined
}

export function Costmap({ grid }: { grid: CostmapGrid }) {
  const texture = useMemo(() => {
    const pixels = new Uint8Array(grid.width * grid.height * 4)
    let index = 0
    for (const [value, count] of grid.runs) {
      const color = value < 0 ? [90, 103, 125, 100] : value >= 99 ? [181, 36, 51, 225]
        : value > 0 ? [239, 156, 49, 70 + value] : [47, 160, 142, 22]
      for (let n = 0; n < count; n++) {
        pixels.set(color, index)
        index += 4
      }
    }
    const result = new DataTexture(pixels, grid.width, grid.height, RGBAFormat)
    result.magFilter = result.minFilter = NearestFilter
    result.needsUpdate = true
    return result
  }, [grid])
  useEffect(() => () => texture.dispose(), [texture])
  const width = grid.width * grid.resolution, depth = grid.height * grid.resolution
  return <mesh name="costmap-overlay" position={[grid.origin[0] + width / 2, .014, -grid.origin[1] - depth / 2]}
    rotation-x={-Math.PI / 2} renderOrder={5}>
    <planeGeometry args={[width, depth]} />
    <meshBasicMaterial map={texture} transparent depthWrite={false} />
  </mesh>
}
