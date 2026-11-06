import { useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import {
  BufferAttribute, BufferGeometry, DynamicDrawUsage, InstancedInterleavedBuffer,
  InterleavedBufferAttribute, LineBasicMaterial,
  LineSegments, Points, PointsMaterial,
} from 'three'
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'
import { robotColor } from './presentation'
import { groundPoint, maxPlanPoints, maxTrailPoints, routeVisibility, type RouteOptions } from './routes'
import type { Telemetry } from './telemetry'
import type { SceneFeed } from './useTelemetry'

function positionBuffer(capacity: number) {
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(new Float32Array(capacity * 3), 3).setUsage(DynamicDrawUsage))
  geometry.setDrawRange(0, 0)
  return geometry
}

export function createRouteLayers(color: string) {
  const trail = new LineSegments(positionBuffer(2 * (maxTrailPoints - 1)),
    new LineBasicMaterial({ color, transparent: true }))
  const planGeometry = new LineSegmentsGeometry().setPositions(new Float32Array((maxPlanPoints - 1) * 6))
  const positions = planGeometry.getAttribute('instanceStart') as InterleavedBufferAttribute
  positions.data.setUsage(DynamicDrawUsage)
  const distances = new InstancedInterleavedBuffer(new Float32Array((maxPlanPoints - 1) * 2), 2, 1)
    .setUsage(DynamicDrawUsage)
  planGeometry.setAttribute('instanceDistanceStart', new InterleavedBufferAttribute(distances, 1, 0))
  planGeometry.setAttribute('instanceDistanceEnd', new InterleavedBufferAttribute(distances, 1, 1))
  planGeometry.instanceCount = 0
  const plan = new LineSegments2(planGeometry, new LineMaterial({
    color, transparent: true, linewidth: 2.2, dashed: true, dashSize: 0.11, gapSize: 0.065,
  }))
  const ends = new Points(positionBuffer(2), new PointsMaterial({ color, transparent: true, size: 0.09 }))
  for (const layer of [trail, plan, ends]) {
    layer.frustumCulled = false
    layer.visible = false
  }
  return { trail, plan, ends, dispose() {
    for (const layer of [trail, plan, ends]) {
      layer.geometry.dispose()
      layer.material.dispose()
    }
  } }
}

function writeTrail(geometry: BufferGeometry, points: Telemetry['trail']) {
  const buffer = geometry.getAttribute('position')
  let count = 0
  for (let index = 1; points && index < points.length; index++) {
    if (points[index].start) continue
    for (const { pose } of [points[index - 1], points[index]]) {
      buffer.setXYZ(count++, ...groundPoint([pose.x, pose.y], 0.021))
    }
  }
  geometry.setDrawRange(0, count)
  buffer.needsUpdate = true
}

function writePlan(layers: ReturnType<typeof createRouteLayers>, path: Telemetry['path']) {
  const points = path?.points ?? []
  const geometry = layers.plan.geometry
  const starts = geometry.getAttribute('instanceStart')
  const ends = geometry.getAttribute('instanceEnd')
  const distanceStarts = geometry.getAttribute('instanceDistanceStart')
  const distanceEnds = geometry.getAttribute('instanceDistanceEnd')
  const endpoints = layers.ends.geometry.getAttribute('position')
  let distance = 0
  for (let i = 1; i < points.length; i++) {
    const prior = points[i - 1]
    const point = points[i]
    starts.setXYZ(i - 1, ...groundPoint(prior, 0.039))
    ends.setXYZ(i - 1, ...groundPoint(point, 0.039))
    distanceStarts.setX(i - 1, distance)
    distance += Math.hypot(point[0] - prior[0], point[1] - prior[1])
    distanceEnds.setX(i - 1, distance)
  }
  if (points.length) {
    endpoints.setXYZ(0, ...groundPoint(points[0], 0.042))
    endpoints.setXYZ(1, ...groundPoint(points[points.length - 1], 0.042))
  }
  geometry.instanceCount = Math.max(0, points.length - 1)
  layers.ends.geometry.setDrawRange(0, points.length ? 2 : 0)
  starts.needsUpdate = distanceStarts.needsUpdate = endpoints.needsUpdate = true
}

function vertices(geometry: BufferGeometry) {
  const position = geometry.getAttribute('position')
  return Array.from({ length: geometry.drawRange.count }, (_, index) =>
    [position.getX(index), position.getY(index), position.getZ(index)])
}

function planVertices(geometry: LineSegmentsGeometry) {
  if (!geometry.instanceCount) return []
  const starts = geometry.getAttribute('instanceStart')
  const ends = geometry.getAttribute('instanceEnd')
  return [[starts.getX(0), starts.getY(0), starts.getZ(0)],
    ...Array.from({ length: geometry.instanceCount }, (_, i) => [ends.getX(i), ends.getY(i), ends.getZ(i)])]
}

export function RouteLayers({ feed, id, colorIndex, selected, options, trace }: {
  feed: SceneFeed; id: string; colorIndex: number; selected: boolean; options: RouteOptions; trace: boolean
}) {
  const layers = useMemo(() => createRouteLayers(robotColor(colorIndex)), [colorIndex])
  const previous = useRef<{ layers?: typeof layers; path?: Telemetry['path']; trail?: Telemetry['trail'] }>({})
  useEffect(() => () => layers.dispose(), [layers])
  useFrame(({ gl }) => {
    const { trail, path } = feed.read().robots.get(id) ?? {}
    const changedTrail = previous.current.layers !== layers || previous.current.trail !== trail
    const changedPlan = previous.current.layers !== layers || previous.current.path !== path
    if (changedTrail) writeTrail(layers.trail.geometry, trail)
    if (changedPlan) writePlan(layers, path)
    if (changedTrail || changedPlan) previous.current = { layers, trail, path }

    const visibility = routeVisibility(options, selected)
    layers.trail.visible = visibility.trail && layers.trail.geometry.drawRange.count > 0
    layers.plan.visible = layers.ends.visible = visibility.plan && layers.plan.geometry.instanceCount > 0
    layers.trail.material.opacity = visibility.opacity * 0.94
    layers.plan.material.opacity = visibility.opacity * 0.82
    layers.ends.material.opacity = visibility.opacity
    if (trace && (changedTrail || changedPlan)) {
      gl.domElement.dispatchEvent(new CustomEvent('fleet-visualizer:routes', { bubbles: true, detail: {
        robot_id: id,
        trail: changedTrail ? trail?.map(({ pose, start }) => ({ stamp_ns: pose.stamp_ns, start,
          stream_id: pose.stream_id, epoch: pose.epoch })) ?? [] : undefined,
        trail_vertices: changedTrail ? vertices(layers.trail.geometry) : undefined,
        plan: changedPlan ? path?.stamp ?? null : undefined,
        plan_vertices: changedPlan ? planVertices(layers.plan.geometry) : undefined,
        path_receive_to_frame_ms: changedPlan && path?.points ? performance.now() - path.receivedAt : undefined,
      } }))
    }
  }, -1)

  return <>
    <primitive object={layers.trail} />
    <primitive object={layers.plan} />
    <primitive object={layers.ends} />
  </>
}
