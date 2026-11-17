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
import { groundPoint, maxPlanPoints, maxTrailPoints, routeVisibility, trailFade, type RouteOptions } from './routes'
import type { Telemetry } from './telemetry'
import type { SceneFeed } from './sceneFeed'

function positionBuffer(capacity: number) {
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(new Float32Array(capacity * 3), 3).setUsage(DynamicDrawUsage))
  geometry.setDrawRange(0, 0)
  return geometry
}

const trailColor = '#64748B'
const planColor = '#7C8798'
const trailMaxAgeMs = 9000
const trailMaxDistance = 2.8

export function createRouteLayers() {
  const trail = new LineSegments(positionBuffer(2 * (maxTrailPoints - 1)),
    new LineBasicMaterial({ color: trailColor, transparent: true, depthWrite: false }))
  const planGeometry = new LineSegmentsGeometry().setPositions(new Float32Array((maxPlanPoints - 1) * 6))
  const positions = planGeometry.getAttribute('instanceStart') as InterleavedBufferAttribute
  positions.data.setUsage(DynamicDrawUsage)
  const distances = new InstancedInterleavedBuffer(new Float32Array((maxPlanPoints - 1) * 2), 2, 1)
    .setUsage(DynamicDrawUsage)
  planGeometry.setAttribute('instanceDistanceStart', new InterleavedBufferAttribute(distances, 1, 0))
  planGeometry.setAttribute('instanceDistanceEnd', new InterleavedBufferAttribute(distances, 1, 1))
  planGeometry.instanceCount = 0
  const plan = new LineSegments2(planGeometry, new LineMaterial({
    color: planColor, transparent: true, depthWrite: false, linewidth: 1.25,
    dashed: true, dashSize: 0.09, gapSize: 0.08,
  }))
  const ends = new Points(positionBuffer(2), new PointsMaterial({
    color: planColor, transparent: true, depthWrite: false, size: 0.055,
  }))
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
  let startIndex = Math.max(1, (points?.length ?? 0) - 1)
  let distance = 0
  if (points?.length) {
    const newest = points.at(-1)!
    while (startIndex > 1 && points.length - startIndex < 48) {
      const current = points[startIndex]
      const prior = points[startIndex - 1]
      const nextDistance = distance + Math.hypot(current.pose.x - prior.pose.x, current.pose.y - prior.pose.y)
      const age = newest.pose.receivedAt - prior.pose.receivedAt
      if (prior.start || age > trailMaxAgeMs || nextDistance > trailMaxDistance) break
      distance = nextDistance
      startIndex--
    }
  }
  for (let index = startIndex; points && index < points.length; index++) {
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

export function RouteLayers({ feed, id, moving, selected, options, trace }: {
  feed: SceneFeed; id: string; moving: boolean; selected: boolean; options: RouteOptions; trace: boolean
}) {
  const layers = useMemo(() => createRouteLayers(), [])
  const previous = useRef<{ layers?: typeof layers; path?: Telemetry['path']; trail?: Telemetry['trail'] }>({})
  useEffect(() => () => layers.dispose(), [layers])
  useFrame(({ gl, invalidate }) => {
    const { trail, path } = feed.read().robots.get(id) ?? {}
    const changedTrail = previous.current.layers !== layers || previous.current.trail !== trail
    const changedPlan = previous.current.layers !== layers || previous.current.path !== path
    if (changedTrail) writeTrail(layers.trail.geometry, trail)
    if (changedPlan) writePlan(layers, path)
    if (changedTrail || changedPlan) previous.current = { layers, trail, path }

    const visibility = routeVisibility(options, selected)
    const lastMovement = trail?.at(-1)?.pose.receivedAt
    const fade = trailFade(lastMovement, performance.now())
    layers.trail.visible = visibility.trail && (moving || fade > 0) && fade > 0 &&
      layers.trail.geometry.drawRange.count > 0
    layers.plan.visible = layers.ends.visible = visibility.plan && layers.plan.geometry.instanceCount > 0
    layers.trail.material.opacity = visibility.opacity * fade * 0.34
    layers.plan.material.opacity = visibility.opacity * 0.32
    layers.ends.material.opacity = visibility.opacity * 0.38
    if (layers.trail.visible && fade < 1) invalidate()
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
