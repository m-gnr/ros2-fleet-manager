import type { Fleet } from '../fleet'
import { labels } from '../presentation'
import { rectangle, wallDistance, type GridLayout } from './gridLayout'
import { toScene } from './coordinates'

export const pointStyle = {
  CHARGING: { name: 'Şarj', color: '#0a806e' },
  PARKING: { name: 'Park', color: '#415e77' },
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
  layoutBay?: boolean
  dockOffset?: number
}

export function operationPoints(fleet: Fleet | null, selected: string | undefined, connected: boolean, layout?: GridLayout) {
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
    const dockOffset = layout && station.station_type === 'CHARGING'
      ? wallDistance(layout, x, z, yaw) - layout.wall_thickness_m / 2 - .105 : undefined
    points.push({ key: `station:${station.station_id}`, id: station.station_id, kind: station.station_type,
      position: [x, 0, z], yaw, owner: owner?.robot_id, chargingRobot, dockOffset,
      detail: connected ? [labels[station.state], chargingRobot && labels.CHARGING].filter(Boolean).join(' · ') : 'Son eşitleme' })
  }
  for (const bay of layout?.transfer_points ?? []) {
    const [x, z, yaw] = toScene(bay.pose)
    if (points.some(point => point.kind === bay.kind && point.position[0] === x && point.position[2] === z)) continue
    points.push({ key: `bay:${bay.id}`, id: bay.id, kind: bay.kind, position: [x, 0, z], yaw, layoutBay: true })
  }
  return points
}

export type OperationLabel = OperationPoint & {
  groupText?: string
  compact?: string
  leader?: OperationPoint['position']
}

export function operationLabels(points: OperationPoint[], layout?: GridLayout): OperationLabel[] {
  const available = points.filter(point => !point.layoutBay)
  if (!layout) return available
  const zones = [['CHARGING', 'charging'], ['PARKING', 'parking'], ['pickup', 'pickup']] as const
  const labels: OperationLabel[] = [...available]
  for (const [kind, zoneKind] of zones) {
    const zone = layout.zones.find(zone => zone.kind === zoneKind)
    if (!zone || (kind === 'pickup' && !zone.callout)) continue
    const { callout, bounds } = zone
    const inZone = ({ position: [x, , z] }: OperationPoint) =>
      x >= bounds.x_min && x <= bounds.x_max && -z >= bounds.y_min && -z <= bounds.y_max
    const members = (kind === 'pickup' ? points : available)
      .filter(point => point.kind === kind && (kind !== 'pickup' || inZone(point)))
    if (!members.length) continue
    const { x, z, depth } = rectangle(bounds)
    const groupText = members.map(point => {
      const status = point.chargingRobot ? 'aktif' : (point.detail ?? '').toLocaleLowerCase('tr')
      const bay = kind === 'pickup' && !point.layoutBay ? layout.transfer_points.find(bay =>
        bay.kind === kind && bay.pose.x === point.position[0] && -bay.pose.y === point.position[2]) : undefined
      const id = bay ? `${bay.id} (${point.id})` : point.id
      return [id, status].filter(Boolean).join(' ')
    }).join(' · ')
    const active = members.filter(point => point.chargingRobot).length
    const compact = kind === 'CHARGING' ? (active ? `${active}/${members.length} aktif` : `${members.length} yuva`)
      : kind === 'PARKING' ? `${members.length} yer` : `${members.length} nokta`
    const leader: OperationPoint['position'] | undefined = callout
      ? [Math.max(bounds.x_min, Math.min(bounds.x_max, callout.x)), .01,
        -Math.max(bounds.y_min, Math.min(bounds.y_max, callout.y))] : undefined
    // Keep live task labels for goals which are outside the configured pickup area.
    for (let index = labels.length - 1; index >= 0; index--) {
      const item = labels[index]
      if (item.kind !== kind) continue
      if (kind !== 'pickup' || inZone(item)) {
        labels.splice(index, 1)
      }
    }
    labels.push({ key: 'zone:' + zone.id, id: zone.id, kind,
      position: callout ? [callout.x, 0, -callout.y] : [x, 0, z + depth * .20],
      yaw: 0, groupText, compact: callout ? compact : undefined, leader })
  }
  return labels
}
