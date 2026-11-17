import type { Fleet } from '../fleet'
import { labels } from '../presentation'
import { wallDistance, type GridLayout } from './gridLayout'
import { toScene } from './coordinates'

export const pointStyle = {
  CHARGING: { name: 'Şarj', color: '#68877e' },
  PARKING: { name: 'Park', color: '#74848c' },
  SAFE_WAITING: { name: 'Bekleme', color: '#576875' },
  pickup: { name: 'Alım', color: '#168DA4' },
  dropoff: { name: 'Teslim', color: '#D18A28' },
  neutral: { name: 'Çift rol', color: '#8799a2' },
  unknown: { name: 'Rol bilinmiyor', color: '#9aaab0' },
}

export type OperationPoint = {
  key: string
  id: string
  kind: keyof typeof pointStyle
  position: [x: number, y: number, z: number]
  yaw: number
  detail?: string
  owner?: string
  chargingRobot?: string
  chargingKnown?: boolean
  layoutBay?: boolean
  dockOffset?: number
  catalogId?: string
  catalogRoles?: ('pickup' | 'dropoff')[]
}

export function operationPoints(fleet: Fleet | null, selected: string | undefined, connected: boolean, layout?: GridLayout) {
  const points: OperationPoint[] = []
  if (!fleet) return points
  const chargingKnown = connected && fleet.robots.length > 0 && fleet.robots.every(robot =>
    robot.telemetry === 'LIVE' && robot.battery_reliability === 'LIVE' && robot.charging !== 'UNAVAILABLE')

  const active = fleet.tasks.filter(task => task.status === 'ASSIGNED' || task.status === 'EXECUTING')
  const selectedTaskId = fleet.robots.find(robot => robot.robot_id === selected)?.active_task_id
  const task = active.find(item => item.task_id === selectedTaskId) ?? active[0] ??
    fleet.tasks.find(item => item.status === 'QUEUED')
  for (const kind of ['pickup', 'dropoff'] as const) {
    const pose = task?.[kind]
    if (!task || !pose || pose.frame_id !== fleet.map_frame) continue
    const [x, z, yaw] = toScene(pose)
    points.push({ key: `${kind}:${task.task_id}`, id: task.task_id, kind, position: [x, 0, z], yaw,
      detail: connected ? labels[task.status] : 'Son eşitleme' })
  }
  for (const station of fleet.stations) {
    if (!station.pose || station.pose.frame_id !== fleet.map_frame) continue
    const [x, z, yaw] = toScene(station.pose)
    const ownerId = station.occupied_by_robot_id ?? station.reserved_by_robot_id
    const owner = connected ? fleet.robots.find(robot => robot.robot_id === ownerId && robot.telemetry === 'LIVE') : undefined
    const chargingRobot = station.station_type === 'CHARGING' &&
      (station.state === 'OCCUPIED' || station.state === 'RELEASING') &&
      station.charging === 'CHARGING' && owner && station.charging_robot_id === owner.robot_id &&
      owner.battery_reliability === 'LIVE' && owner.charging === 'CHARGING' &&
      owner.charging_station_id === station.station_id ? owner.robot_id : undefined
    const dockOffset = layout && station.station_type === 'CHARGING'
      ? wallDistance(layout, x, z, yaw) - layout.wall_thickness_m / 2 - .105 : undefined
    points.push({ key: `station:${station.station_id}`, id: station.station_id, kind: station.station_type,
      position: [x, 0, z], yaw, owner: owner?.robot_id, chargingRobot, dockOffset,
      chargingKnown: station.station_type === 'CHARGING' ? chargingKnown : undefined,
      detail: connected ? [labels[station.state], chargingRobot && labels.CHARGING].filter(Boolean).join(' · ') : 'Son eşitleme' })
  }
  for (const bay of layout?.transfer_points ?? []) {
    const [x, z, yaw] = toScene(bay.pose)
    // A catalog role is permission, not the current job of a reusable point.
    const roles = [...new Set(bay.roles ?? [bay.kind])]
    const current = points.find(point => !point.layoutBay &&
      point.position[0] === x && point.position[2] === z)
    if (current) {
      current.catalogId = bay.id
      current.catalogRoles = roles
      continue
    }
    const kind = roles.length === 2 ? 'neutral' : roles.length === 1 ? roles[0] : 'unknown'
    points.push({ key: `bay:${bay.id}`, id: bay.id, kind, position: [x, 0, z], yaw,
      layoutBay: true, catalogId: bay.id, catalogRoles: roles })
  }
  return points
}
