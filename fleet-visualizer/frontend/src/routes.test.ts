import { describe, expect, it, vi } from 'vitest'
import { connectFleet, disconnectFleet, expireFleet, initialFleet, receiveFleet, type Fleet } from './fleet'
import { createRouteLayers } from './RouteLayers'
import { groundPoint, maxPlanPoints, maxTrailPoints, recordTrail, routeVisibility, type TrailPoint } from './routes'
import type { Pose } from './telemetry'

const identity = (robot_id: string, epoch = 0) => ({
  version: 1, robot_id, epoch, frame_id: 'map', source: 'tf' as const,
  stream_id: robot_id === 'a' ? '11111111-1111-1111-1111-111111111111' : '22222222-2222-2222-2222-222222222222',
})
const hello = (id: string, epoch = 0) => ({
  ...identity(id, epoch), type: 'hello', after_stamp_ns: '0', path_topic: `/${id}/plan`, stale_after_ms: 1000,
})
const pose = (id: string, stamp: number, x = 0, epoch = 0) => ({
  ...identity(id, epoch), type: 'robot_pose', stamp_ns: String(stamp), x, y: 0, yaw: 0,
})
const plan = (id: string, stamp: number) => ({
  ...identity(id), type: 'robot_path', stamp_ns: String(stamp), plan_source: 'nav2_observed_plan',
  source_topic: `/${id}/plan`, ttl_ms: 500, points: [[1, -2], [2, -1]],
})
const receive = (state: Fleet, packet: object, now = 0) => receiveFleet(state, JSON.stringify(packet), now)
const roster = { type: 'fleet_hello', version: 1, robot_ids: ['a', 'b'] }
function start() {
  return receive(receive(receive(connectFleet(initialFleet), roster), hello('a')), hello('b'))
}

describe('observed path and measured trail', () => {
  it('requires live matching TF, namespaced source, epoch and increasing plan stamps', () => {
    let state = start()
    expect(receive(state, plan('a', 1))).toBe(state)
    state = receive(receive(state, pose('a', 1)), pose('b', 1))
    const prior = state
    const a = state.robots.get('a')
    state = receive(state, plan('a', 3))
    expect(state.robots.get('b')).toBe(prior.robots.get('b'))
    expect(state.robots.get('a')?.trail).toBe(a?.trail)
    expect(state.robots.get('a')?.path?.points).toEqual([[1, -2], [2, -1]])
    for (const invalid of [plan('a', 2), plan('a', 3), { ...plan('a', 4), source_topic: '/b/plan' },
      { ...plan('a', 4), epoch: 1 }, { ...plan('a', 4), frame_id: 'odom' },
      { ...plan('a', 4), points: [[Infinity, 1], [2, 3]] }, { ...plan('a', 4), points: [[1, 1], [NaN, 3]] },
      { ...plan('a', 4), points: Array(maxPlanPoints + 1).fill([0, 0]) }, { ...plan('a', 4), ttl_ms: 5000 }]) {
      expect(receive(state, invalid)).toBe(state)
    }
    expect(groundPoint([1, -2], 0.021)).toEqual([1, 0.021, 2])
  })

  it('hides expired and cleared paths without accepting their stamps again', () => {
    let state = receive(receive(start(), pose('a', 1)), plan('a', 2))
    expect(expireFleet(state, 499)).toBe(state)
    state = expireFleet(state, 500)
    expect(state.robots.get('a')?.path).toMatchObject({ stamp: '2', points: undefined })
    expect(receive(state, plan('a', 2), 501)).toBe(state)
    state = receive(state, plan('a', 3), 505)
    expect(receive(state, { ...plan('a', 2), type: 'robot_path_clear' })).toBe(state)
    state = receive(state, { ...plan('a', 3), type: 'robot_path_clear' }, 510)
    expect(state.robots.get('a')?.path?.points).toBeUndefined()
    state = receive(state, plan('a', 4), 511)
    state = receive(state, { ...identity('a'), type: 'data_status', status: 'FRAME_ERROR' })
    expect(state.robots.get('a')?.path?.points).toBeUndefined()
  })

  it('breaks trails after cuts, jumps and temporal gaps and clears on epoch or stream changes', () => {
    let state = receive(receive(start(), pose('a', 1)), pose('b', 1))
    state = receive(state, pose('a', 2, 0.1), 50)
    state = receive(state, pose('a', 3, 2), 100)
    state = receive(state, pose('a', 4, 2.1), 150)
    state = receive(state, pose('a', 500_000_005, 2.2), 200)
    const trail = () => state.robots.get('a')?.trail
    expect(trail()?.map(point => point.start)).toEqual([true, false, true, false, true])
    expect(receive(state, pose('a', 3, 8))).toBe(state)
    state = expireFleet(state, 1250)
    state = receive(state, pose('a', 500_000_006, 2.2), 1270)
    expect(trail()?.at(-1)?.start).toBe(true)
    expect(state.robots.get('b')?.trail).toHaveLength(1)
    state = receive(state, plan('a', 500_000_007), 1271)
    state = disconnectFleet(state)
    expect(state.robots.get('a')?.path).toBeUndefined()
    state = receive(receive(connectFleet(state), roster), hello('a'))
    state = receive(state, pose('a', 500_000_008, 2.2), 1280)
    expect(trail()?.at(-1)?.start).toBe(true)
    state = receive(state, { ...identity('a', 1), type: 'data_status', status: 'NO_DATA' })
    expect(trail()).toBeUndefined()
    state = receive(state, pose('a', 1, 5, 1), 1290)
    expect(trail()).toHaveLength(1)
    state = receive(receive(connectFleet(disconnectFleet(state)), roster), {
      ...hello('a'), stream_id: '33333333-3333-3333-3333-333333333333',
    })
    expect(trail()).toBeUndefined()
  })

  it('bounds retained points and sim-time history and excludes diagnostic odometry', () => {
    let trail: readonly TrailPoint[] = []
    let previous: Pose | undefined
    for (let i = 1; i <= 1000; i++) {
      const pose = { ...identity('a'), stamp_ns: String(i * 100_000_000), x: i / 20,
        y: 0, yaw: 0, receivedAt: i * 10 }
      trail = recordTrail(trail, pose, previous)
      previous = pose
    }
    expect(trail).toHaveLength(maxTrailPoints)
    const newest = { ...previous!, stamp_ns: '160200000000', receivedAt: 10200 }
    trail = recordTrail(trail, newest, previous)
    expect(trail).toEqual([{ pose: newest, start: true }])
    expect(recordTrail(trail, { ...newest, source: 'diagnostic_odom', stamp_ns: '160300000000' })).toBe(trail)
  })

  it('filters layers by selection and disposes all GPU objects', () => {
    const options = { plan: true, trail: true, highlight: true, selectedOnly: true }
    expect(routeVisibility(options, false)).toEqual({ plan: false, trail: false, opacity: 0.48 })
    expect(routeVisibility({ ...options, plan: false, trail: false }, true)).toEqual({ plan: false, trail: false, opacity: 1 })
    const layers = createRouteLayers('#79d6c8')
    const disposed = [layers.plan, layers.trail, layers.ends].flatMap(layer => {
      const geometry = vi.fn()
      const material = vi.fn()
      layer.geometry.addEventListener('dispose', geometry)
      layer.material.addEventListener('dispose', material)
      return [geometry, material]
    })
    layers.dispose()
    disposed.forEach(spy => expect(spy).toHaveBeenCalledTimes(1))
  })
})
