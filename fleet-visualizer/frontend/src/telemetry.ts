import { hidePath, readObservedPath, recordTrail, type ObservedPath, type TrailPoint } from './routes'

export type Status = 'NO_DATA' | 'LIVE' | 'STALE' | 'FRAME_ERROR'
type Source = 'tf' | 'diagnostic_odom'
type Identity = { stream_id: string; robot_id: string; frame_id: string; source: Source; epoch: number }
type Session = Identity & { watermark: bigint; staleMs: number; pathTopic?: string }
export type Pose = Identity & { x: number; y: number; yaw: number; stamp_ns: string; receivedAt: number }
export type Telemetry = {
  connection: 'CONNECTED' | 'DISCONNECTED'
  status: Status
  session?: Session
  awaitingHello: boolean
  pose?: Pose
  previous?: Pose
  trail?: readonly TrailPoint[]
  path?: ObservedPath
}

const statuses: readonly string[] = ['NO_DATA', 'LIVE', 'STALE', 'FRAME_ERROR']
const maxStamp = 2_147_483_647_999_999_999n
export const initial: Telemetry = { connection: 'DISCONNECTED', status: 'NO_DATA', awaitingHello: true }

export function connected(state: Telemetry): Telemetry {
  return { ...state, connection: 'CONNECTED', awaitingHello: true,
    status: state.pose ? 'STALE' : 'NO_DATA', previous: undefined, path: undefined }
}

export function disconnected(state: Telemetry): Telemetry {
  return { ...state, connection: 'DISCONNECTED', awaitingHello: true,
    status: state.pose ? 'STALE' : 'NO_DATA', previous: undefined, path: undefined }
}

export function expire(state: Telemetry, now: number): Telemetry {
  if (state.status === 'LIVE' && state.pose && state.session && now - state.pose.receivedAt >= state.session.staleMs) {
    return { ...state, status: 'STALE', previous: undefined, path: hidePath(state.path) }
  }
  return state.path?.points && now >= state.path.expiresAt ? { ...state, path: hidePath(state.path) } : state
}

function validStamp(value: unknown): value is string {
  return typeof value === 'string' && /^(0|[1-9]\d{0,18})$/.test(value) && BigInt(value) <= maxStamp
}

function identity(value: Record<string, unknown>): Identity | undefined {
  const { version, stream_id, robot_id, frame_id, source, epoch } = value
  if (version !== 1 || typeof stream_id !== 'string' ||
      !/^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/.test(stream_id) ||
      typeof robot_id !== 'string' || !/^[\w-]{1,128}$/.test(robot_id) ||
      typeof frame_id !== 'string' || !/^[\w/]{1,256}$/.test(frame_id) ||
      (source !== 'tf' && source !== 'diagnostic_odom') ||
      (source === 'tf' ? frame_id !== 'map' : !frame_id.endsWith('/odom')) ||
      typeof epoch !== 'number' || !Number.isSafeInteger(epoch) || epoch < 0) return undefined
  return { stream_id, robot_id, frame_id, source, epoch }
}

function sameSource(a: Identity, b: Identity) {
  return a.robot_id === b.robot_id && a.frame_id === b.frame_id && a.source === b.source
}

export function decodePacket(raw: unknown, maxLength = 2048): Record<string, unknown> | undefined {
  if (typeof raw !== 'string' || raw.length > maxLength) return undefined
  let value: unknown
  try { value = JSON.parse(raw) } catch { return undefined }
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined
  return value as Record<string, unknown>
}

export function receive(state: Telemetry, raw: unknown, now: number): Telemetry {
  const packet = decodePacket(raw)
  return packet ? receivePacket(state, packet, now) : state
}

export function receivePacket(state: Telemetry, packet: Record<string, unknown>, now: number): Telemetry {
  if (state.connection !== 'CONNECTED') return state
  const id = identity(packet)
  if (!id) return state

  const { session } = state
  if (state.awaitingHello) {
    const staleMs = packet.stale_after_ms
    const pathTopic = packet.path_topic
    if (packet.type !== 'hello' || !validStamp(packet.after_stamp_ns) ||
        typeof staleMs !== 'number' || !Number.isFinite(staleMs) ||
        staleMs < 1 || staleMs > 10_000 ||
        (pathTopic !== undefined && (id.source !== 'tf' || typeof pathTopic !== 'string' ||
          pathTopic.length > 256 || !/^\/(?:[\w]+\/)+plan$/.test(pathTopic)))) return state
    let watermark = BigInt(packet.after_stamp_ns)
    if (session?.stream_id === id.stream_id) {
      if (!sameSource(session, id) || id.epoch < session.epoch) return state
      if (id.epoch === session.epoch && session.watermark > watermark) watermark = session.watermark
    }
    const pose = state.pose && sameSource(state.pose, id) ? state.pose : undefined
    return { ...state, pose, previous: undefined, awaitingHello: false,
      status: pose ? 'STALE' : 'NO_DATA', path: undefined,
      trail: session?.stream_id === id.stream_id && session.epoch === id.epoch ? state.trail : undefined,
      session: { ...id, watermark, staleMs, pathTopic } }
  }

  if (!session || id.stream_id !== session.stream_id || !sameSource(session, id) ||
      id.epoch < session.epoch) return state
  if (packet.type === 'data_status' && typeof packet.status === 'string' && statuses.includes(packet.status)) {
    const nextEpoch = id.epoch > session.epoch
    const status = packet.status as Status
    // A server heartbeat alone cannot promote a cached pose to LIVE.
    if (status === 'LIVE' && !nextEpoch) return { ...state }
    return { ...state, previous: undefined, status: status === 'LIVE' ? 'NO_DATA' : status,
      trail: nextEpoch ? undefined : state.trail,
      path: nextEpoch ? undefined : hidePath(state.path),
      session: nextEpoch ? { ...session, epoch: id.epoch, watermark: 0n } : session }
  }
  if (packet.type === 'robot_path' || packet.type === 'robot_path_clear') {
    const stamp = packet.stamp_ns
    if (id.epoch !== session.epoch || session.pathTopic === undefined ||
        packet.source_topic !== session.pathTopic || packet.plan_source !== 'nav2_observed_plan' ||
        !validStamp(stamp) || stamp === '0') return state
    if (packet.type === 'robot_path_clear') {
      return state.path?.points && state.path.stamp === stamp ? { ...state, path: hidePath(state.path) } : state
    }
    if (state.status !== 'LIVE' || (state.path && BigInt(stamp) <= BigInt(state.path.stamp))) return state
    const path = readObservedPath(packet, stamp, now)
    return path ? { ...state, path } : state
  }
  if (packet.type !== 'robot_pose' || id.epoch !== session.epoch ||
      !validStamp(packet.stamp_ns) || BigInt(packet.stamp_ns) <= session.watermark) return state
  const { x, y, yaw } = packet
  if (typeof x !== 'number' || !Number.isFinite(x) || typeof y !== 'number' || !Number.isFinite(y) ||
      typeof yaw !== 'number' || !Number.isFinite(yaw) || Math.abs(yaw) > Math.PI) return state

  const pose = { ...id, x, y, yaw, stamp_ns: packet.stamp_ns, receivedAt: now }
  const previous = state.status === 'LIVE' ? state.pose : undefined
  return { ...state, status: 'LIVE', previous, pose,
    trail: recordTrail(state.trail ?? [], pose, previous),
    session: { ...session, watermark: BigInt(packet.stamp_ns) } }
}

export function stampLabel(stamp: string) {
  const padded = stamp.padStart(10, '0')
  return padded.slice(0, -9) + '.' + padded.slice(-9)
}
