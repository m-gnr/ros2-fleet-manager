import { describe, expect, it } from 'vitest'
import { connectFleet, disconnectFleet, expireFleet, initialFleet, receiveFleet, type Fleet } from './fleet'
import { telemetryFields } from './presentation'
import { blendPose } from './coordinates'

const ids = ['a', 'b']
const identity = (id: string) => ({
  version: 1, robot_id: id, frame_id: 'map', source: 'tf', epoch: 0,
  stream_id: id === 'a' ? '11111111-1111-1111-1111-111111111111' : '22222222-2222-2222-2222-222222222222',
})
const send = (state: Fleet, packet: object, now = 0) => receiveFleet(state, JSON.stringify(packet), now)
const roster = { type: 'fleet_hello', version: 1, robot_ids: ids }
const hello = (id: string, after = '0') => ({
  ...identity(id), type: 'hello', after_stamp_ns: after, stale_after_ms: 1000,
})
const pose = (id: string, stamp: number, x: number, yaw = 0) => ({
  ...identity(id), type: 'robot_pose', stamp_ns: String(stamp), x, y: x / 2, yaw,
})

function start() {
  return ids.reduce((state, id) => send(state, hello(id)), send(connectFleet(initialFleet), roster))
}

describe('fleet telemetry', () => {
  it('announces NO_DATA before poses and rejects unlisted or unauthenticated identities', () => {
    let state = send(connectFleet(initialFleet), roster)
    expect([...state.robots.values()].map(robot => robot.status)).toEqual(['NO_DATA', 'NO_DATA'])
    expect(send(state, pose('b', 1, 1))).toBe(state)
    state = send(state, hello('b'))
    expect(send(state, hello('unlisted'))).toBe(state)
    expect(send(state, { ...pose('b', 1, 1), frame_id: 'odom' })).toBe(state)
    const updated = send(state, pose('b', 1, 1))
    expect(updated.robots.get('a')).toBe(state.robots.get('a'))
    expect(updated.robots.get('b')?.status).toBe('LIVE')
  })

  it('keeps independent ordering, last pose and freshness when another robot moves', () => {
    const a = send(start(), pose('a', 50, 2), 1)
    const both = send(a, pose('b', 2, -2), 400)
    expect(both.robots.get('a')).toBe(a.robots.get('a'))
    expect(send(both, pose('a', 50, 99), 900)).toBe(both)
    expect(send(both, pose('a', 49, 99), 950)).toBe(both)
    const stale = expireFleet(both, 1001)
    expect(stale.robots.get('a')?.status).toBe('STALE')
    expect(stale.robots.get('b')).toBe(both.robots.get('b'))
    expect(telemetryFields(stale.robots.get('a')!).x).toBe('2.000')
    expect(telemetryFields(stale.robots.get('b')!).x).toBe('-2.000')
    const recovered = send(stale, pose('a', 51, 3), 1100)
    expect(recovered.robots.get('a')).toMatchObject({ status: 'LIVE', previous: undefined })
  })

  it('interpolates from each robot’s own pose and keeps yaw on the short arc', () => {
    let state = send(start(), pose('a', 100, 0, Math.PI - 0.05))
    state = send(state, pose('b', 5, -9))
    state = send(state, pose('a', 101, 4, -Math.PI + 0.05), 50)
    state = send(state, pose('b', 6, -7), 60)
    const a = state.robots.get('a')!
    const b = state.robots.get('b')!
    expect(blendPose(a.previous!, a.pose!, 22.5)).toMatchObject({ x: 2, yaw: Math.PI })
    expect(blendPose(b.previous!, b.pose!, 22.5).x).toBe(-8)
    expect(blendPose(a.previous!, a.pose!, 200)).toBe(a.pose)
  })

  it('accepts a lower stamp only in the announced epoch for that robot', () => {
    let state = send(send(start(), pose('a', 100, 2)), pose('b', 50, 5))
    const b = state.robots.get('b')
    state = send(state, { ...identity('a'), type: 'data_status', status: 'NO_DATA', epoch: 1 })
    expect(state.robots.get('b')).toBe(b)
    expect(send(state, pose('a', 101, 77))).toBe(state)
    state = send(state, { ...pose('a', 1, 4), epoch: 1 }, 70)
    expect(state.robots.get('a')).toMatchObject({ status: 'LIVE', previous: undefined, pose: { x: 4, epoch: 1 } })
    expect(state.robots.get('b')).toBe(b)
  })

  it('holds both poses over reconnect and waits for each robot’s own cutoff', () => {
    let state = send(send(start(), pose('a', 100, 2)), pose('b', 50, 5))
    state = send(connectFleet(disconnectFleet(state)), roster)
    state = send(send(state, hello('a', '99')), hello('b', '51'))
    expect([...state.robots.values()].map(robot => robot.status)).toEqual(['STALE', 'STALE'])
    expect(send(state, pose('a', 100, 77))).toBe(state)
    expect(send(state, pose('b', 51, 88))).toBe(state)
    state = send(state, pose('b', 52, 6))
    expect(state.robots.get('b')?.status).toBe('LIVE')
    expect(state.robots.get('a')?.status).toBe('STALE')
    const legacy = send(connectFleet(disconnectFleet(state)), hello('a'))
    expect([...legacy.robots.keys()]).toEqual(['a'])
  })
})
