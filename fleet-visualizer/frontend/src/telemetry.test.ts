import { describe, expect, it } from 'vitest'
import { blendMs, blendPose, toScene } from './coordinates'
import { connected, disconnected, expire, initial, receive, stampLabel } from './telemetry'
import type { Telemetry } from './telemetry'

const id = { version: 1, robot_id: 'robot_1', frame_id: 'map', source: 'tf', epoch: 0,
  stream_id: 'b0800df7-63ee-4281-a509-cdf5ca44a69e' }
const hello = { ...id, type: 'hello', after_stamp_ns: '1', stale_after_ms: 1000 }
const pose = { ...id, type: 'robot_pose', stamp_ns: '2', x: 4, y: -2, yaw: Math.PI }
const apply = (state: Telemetry, packet: object, now = 0) => receive(state, JSON.stringify(packet), now)
const started = apply(connected(initial), hello)
const live = apply(started, pose)

describe('telemetry contract', () => {
  it('accepts the exact valid measurement after hello', () => {
    expect(live.pose).toMatchObject({ x: 4, y: -2, yaw: Math.PI, stamp_ns: '2' })
    expect(live.status).toBe('LIVE')
    expect(stampLabel('123456789123456789')).toBe('123456789.123456789')
    expect(apply(connected(initial), pose).pose).toBeUndefined()
  })

  it('ignores malformed, nonfinite, duplicate, reordered and unrelated measurements', () => {
    expect(receive(started, 'garbage', 0)).toBe(started)
    expect(receive(started, JSON.stringify(pose).replace('"x":4', '"x":1e999'), 0)).toBe(started)
    for (const fields of [{ x: NaN }, { y: undefined }, { yaw: 4 }, { version: 2 },
      { robot_id: 'robot_2' }, { frame_id: 'robot_1/odom' }, { stamp_ns: 3 }, { epoch: 1 }]) {
      expect(apply(started, { ...pose, ...fields })).toBe(started)
    }
    expect(apply(live, pose, 500)).toBe(live)
    expect(apply(live, { ...pose, stamp_ns: '1' })).toBe(live)
  })

  it('keeps transport and ROS freshness separate and holds last verified position', () => {
    const stale = expire(live, 1000)
    expect(stale).toMatchObject({ connection: 'CONNECTED', status: 'STALE', pose: live.pose })
    const closed = disconnected(stale)
    expect(closed).toMatchObject({ connection: 'DISCONNECTED', status: 'STALE', pose: live.pose })
    const error = apply(live, { ...id, type: 'data_status', status: 'FRAME_ERROR' })
    expect(error).toMatchObject({ connection: 'CONNECTED', status: 'FRAME_ERROR', pose: live.pose })
    expect(apply(stale, { ...id, type: 'data_status', status: 'LIVE' }).status).toBe('STALE')
  })

  it('rejects replay after reconnect and gates backward timestamps on the ROS epoch', () => {
    const reopened = apply(connected(disconnected(live)), hello)
    expect(reopened.status).toBe('STALE')
    expect(apply(reopened, pose)).toBe(reopened)
    expect(apply(reopened, { ...pose, stamp_ns: '3' }).status).toBe('LIVE')
    const rewind = apply(live, { ...id, type: 'data_status', status: 'NO_DATA', epoch: 1 })
    expect(apply(rewind, pose)).toBe(rewind)
    expect(apply(rewind, { ...pose, epoch: 1, stamp_ns: '1' }).pose?.stamp_ns).toBe('1')
  })

  it('resets ordering on a new bridge session without transferring poses across frames', () => {
    const stream_id = 'fb02ea91-5e25-40be-9238-03c0d5ef814d'
    const open = connected(disconnected(live))
    const restarted = apply(open, { ...hello, stream_id, after_stamp_ns: '0' })
    expect(apply(restarted, { ...pose, stream_id, stamp_ns: '1' }).status).toBe('LIVE')
    expect(apply(open, { ...hello, stream_id, source: 'diagnostic_odom',
      frame_id: 'robot_1/odom' }).pose).toBeUndefined()
  })
})

describe('scene transform', () => {
  it('maps ROS x and y and keeps yaw about positive Three Y', () => {
    expect(toScene(pose)).toEqual([4, 2, Math.PI])
  })

  it('bounds interpolation to the endpoints and takes the short path at pi', () => {
    const from = { x: 0, y: 4, yaw: Math.PI - 0.1 }
    const to = { x: 2, y: 2, yaw: -Math.PI + 0.1 }
    expect(blendPose(from, to, -1)).toBe(from)
    expect(blendPose(from, to, blendMs * 5)).toBe(to)
    const middle = blendPose(from, to, blendMs / 2)
    expect(middle).toMatchObject({ x: 1, y: 3 })
    expect(Math.abs(middle.yaw)).toBeCloseTo(Math.PI)
  })
})
