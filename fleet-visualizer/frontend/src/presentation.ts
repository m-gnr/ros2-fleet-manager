import { stampLabel, type Telemetry } from './telemetry'

export const freshnessLabels = {
  LIVE: 'Güncel ve doğrulanmış ROS ölçümü.',
  NO_DATA: 'Bu akış için geçerli ROS ölçümü bekleniyor.',
  STALE: 'Son doğrulanmış poz gösteriliyor.',
  FRAME_ERROR: 'TF zinciri veya koordinat çerçevesi doğrulanamadı.',
}

export const schematicLabel = 'TEMSİLİ DEPO'

export function telemetryFields({ pose, session }: Telemetry) {
  return {
    robot: session?.robot_id ?? 'Robot bekleniyor',
    frame: session?.frame_id ?? '—',
    source: session?.source === 'tf' ? 'TF' : session ? 'Tanılama odometrisi' : '—',
    x: pose?.x.toFixed(3) ?? '—',
    y: pose?.y.toFixed(3) ?? '—',
    yaw: pose?.yaw.toFixed(3) ?? '—',
    stamp: pose ? stampLabel(pose.stamp_ns) + ' sn' : '—',
  }
}
