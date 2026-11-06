import { describe, expect, it } from 'vitest'
import { Vector3 } from 'three'
import { burgerSize, frontMarkerX } from './Burger'
import { followTarget, resetCamera, selectCamera, type CameraCommand } from './camera'
import { toScene } from './coordinates'
import { freshnessLabels, schematicLabel, telemetryFields } from './presentation'
import { connected, disconnected, initial, receive } from './telemetry'

const id = { version: 1, robot_id: 'configured_bot', frame_id: 'map', source: 'tf', epoch: 0,
  stream_id: 'b0800df7-63ee-4281-a509-cdf5ca44a69e' }
const hello = receive(connected(initial), JSON.stringify({
  ...id, type: 'hello', after_stamp_ns: '0', stale_after_ms: 1000,
}), 0)
const live = receive(hello, JSON.stringify({
  ...id, type: 'robot_pose', x: 4.23451, y: -2.89123, yaw: Math.PI / 2, stamp_ns: '1045000000',
}), 100)

describe('visual presentation', () => {
  it('keeps model dimensions and the forward marker independent of the ROS root', () => {
    const [x, z, yaw] = toScene({ x: 2, y: -3, yaw: Math.PI / 2 })
    const root = new Vector3(x, 0, z)
    const marker = new Vector3(frontMarkerX, 0, 0).applyAxisAngle(new Vector3(0, 1, 0), yaw).add(root)
    expect(burgerSize).toEqual({ length: 0.138, width: 0.178, height: 0.192 })
    expect(root.toArray()).toEqual([2, 0, 3])
    expect(marker.x).toBeCloseTo(2)
    expect(marker.z).toBeCloseTo(3 - frontMarkerX)
  })

  it('selects camera modes, issues repeatable resets, and targets Three coordinates', () => {
    const start: CameraCommand = { mode: 'free', reset: 0 }
    const follow = selectCamera(start, 'follow')
    expect(selectCamera(follow, 'follow')).toBe(follow)
    expect(selectCamera(follow, 'top')).toEqual({ mode: 'top', reset: 0 })
    expect(resetCamera(resetCamera(follow))).toEqual({ mode: 'free', reset: 2 })
    expect(followTarget(2, -3)).toEqual([2, 0.12, -3])
  })

  it('formats verified ROS data and preserves it when transport closes', () => {
    expect(telemetryFields(initial)).toEqual({
      robot: 'Robot bekleniyor', frame: '—', source: '—', x: '—', y: '—', yaw: '—', stamp: '—',
    })
    expect(telemetryFields(live)).toEqual({
      robot: 'configured_bot', frame: 'map', source: 'TF', x: '4.235', y: '-2.891', yaw: '1.571',
      stamp: '1.045000000 sn',
    })
    expect(telemetryFields(disconnected(live))).toEqual(telemetryFields(live))
  })

  it('uses the selected diagnostic frame and explicit schematic and TF error labels', () => {
    const diagnostic = receive(connected(initial), JSON.stringify({
      ...id, type: 'hello', frame_id: 'configured_bot/odom', source: 'diagnostic_odom',
      after_stamp_ns: '0', stale_after_ms: 1000,
    }), 0)
    expect(telemetryFields(diagnostic)).toMatchObject({ frame: 'configured_bot/odom', source: 'Tanılama odometrisi' })
    expect(freshnessLabels.FRAME_ERROR).toContain('TF zinciri')
    expect(schematicLabel).toBe('TEMSİLİ DEPO')
  })
})
