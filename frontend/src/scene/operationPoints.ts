import type { Fleet } from '../fleet'
import { labels } from '../presentation'
import { toScene } from './coordinates'

export const pointStyle = {
  CHARGING: { name: 'Şarj', color: '#0a806e' },
  PARKING: { name: 'Park', color: '#3263ab' },
  SAFE_WAITING: { name: 'Bekleme', color: '#576875' },
  pickup: { name: 'Alım', color: '#275c99' },
  dropoff: { name: 'Teslim', color: '#7850a9' },
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
}

export function operationPoints(fleet: Fleet | null, selected: string | undefined, connected: boolean) {
  const points: OperationPoint[] = []
  if (!fleet) return points

  const active = fleet.tasks.filter(task => task.status === 'ASSIGNED' || task.status === 'EXECUTING')
  const selectedTaskId = fleet.robots.find(robot => robot.robot_id === selected)?.active_task_id
  const task = active.find(item => item.task_id === selectedTaskId) ?? active[0] ??
    fleet.tasks.find(item => item.status === 'QUEUED')
  for (const kind of ['pickup', 'dropoff'] as const) {
    const pose = task?.[kind]
    if (!task || !pose || pose.frame_id !== fleet.map_frame) continue
    const [x, z, yaw] = toScene(pose)
    points.push({ key: `${kind}:${task.task_id}`, id: task.task_id, kind, position: [x, 0, z], yaw,
      detail: connected ? undefined : 'Son eşitleme' })
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
    points.push({ key: `station:${station.station_id}`, id: station.station_id, kind: station.station_type,
      position: [x, 0, z], yaw, owner: owner?.robot_id, chargingRobot,
      detail: connected ? [labels[station.state], chargingRobot && labels.CHARGING].filter(Boolean).join(' · ') : 'Son eşitleme' })
  }
  return points
}
