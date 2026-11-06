import { connected, decodePacket, disconnected, expire, initial, receivePacket, type Telemetry } from './telemetry'

export type Fleet = {
  connection: Telemetry['connection']
  robots: ReadonlyMap<string, Telemetry>
  roster?: ReadonlySet<string>
}

export const initialFleet: Fleet = { connection: 'DISCONNECTED', robots: new Map() }

function updateRobots(state: Fleet, apply: (robot: Telemetry) => Telemetry) {
  const robots = new Map(state.robots)
  let changed = false
  for (const [id, robot] of state.robots) {
    const next = apply(robot)
    if (next !== robot) {
      changed = true
      robots.set(id, next)
    }
  }
  return changed ? { ...state, robots } : state
}

export function connectFleet(state: Fleet): Fleet {
  return { ...updateRobots(state, connected), connection: 'CONNECTED', roster: undefined }
}

export function disconnectFleet(state: Fleet): Fleet {
  return { ...updateRobots(state, disconnected), connection: 'DISCONNECTED' }
}

export function expireFleet(state: Fleet, now: number) {
  return updateRobots(state, robot => expire(robot, now))
}

export function receiveFleet(state: Fleet, raw: unknown, now: number): Fleet {
  if (state.connection !== 'CONNECTED') return state
  const packet = decodePacket(raw, 64 * 1024)
  if (!packet) return state

  if (packet.type === 'fleet_hello' && packet.version === 1 && !state.roster &&
      Array.isArray(packet.robot_ids) && packet.robot_ids.length > 0 &&
      packet.robot_ids.every(id => typeof id === 'string' && /^[\w-]{1,128}$/.test(id))) {
    const roster = new Set<string>(packet.robot_ids)
    if (roster.size !== packet.robot_ids.length) return state
    const robots = new Map([...roster].map(id => [id, state.robots.get(id) ?? connected(initial)]))
    return { ...state, robots, roster }
  }

  const id = packet.robot_id
  if (typeof id !== 'string' || (state.roster && !state.roster.has(id))) return state
  const robot = state.robots.get(id) ?? connected(initial)
  const next = receivePacket(robot, packet, now)
  if (next === robot) return state

  // A server on the legacy endpoint announces its sole robot with hello.
  const roster = state.roster ?? new Set([id])
  const robots = new Map([...state.robots].filter(([key]) => roster.has(key)))
  robots.set(id, next)
  return { ...state, robots, roster }
}
