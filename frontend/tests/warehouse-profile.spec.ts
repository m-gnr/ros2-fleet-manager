import { expect, test } from '@playwright/test'
import { staticWarehouse } from '../src/scene/warehouseProfile.generated'
import { warehouseLayoutSchema, type GridLayout, layoutResponse } from '../src/scene/gridLayout'
import { resolveWarehouseProfile } from '../src/scene/useGridLayout'
import { operationPoints, pointStyle } from '../src/scene/operationPoints'
import { floorSignLayout } from '../src/scene/floorSignLayout'
import type { Fleet } from '../src/fleet'

const initialLayout = warehouseLayoutSchema.parse(staticWarehouse.layout)
const initial = { layout: initialLayout, profileId: staticWarehouse.profile_id,
  profileDigest: staticWarehouse.profile_digest }

test('C5-A starts on the validated warehouse profile without live robot data', async ({ page }) => {
  await page.addInitScript(() => {
    window.addEventListener('fleet-visualizer:frame', event => {
      (window as typeof window & { warehouseFrame?: { warehouse: string; robots: { visible: boolean; status?: string }[] } })
        .warehouseFrame = (event as CustomEvent).detail
    })
  })
  await page.goto('/?trace=1')
  await page.waitForFunction(() => (window as typeof window & { warehouseFrame?: { warehouse: string } })
    .warehouseFrame?.warehouse === 'grid')
  expect(await page.locator('.scene-legend').innerText()).toContain('warehouse_distributed_30x18')
  expect(await page.locator('.scene-indicator').innerText()).toBe('0 / 0 TF LIVE')
  await expect(page.getByRole('status').filter({ hasText: 'Bağlantı kesildi' })).toBeVisible()
  const frame = await page.evaluate(() => (window as typeof window & {
    warehouseFrame?: { warehouse: string; robots: { visible: boolean }[] }
  }).warehouseFrame)
  expect(frame?.robots.every(robot => !robot.visible)).toBe(true)
})

test('profile hash retains the verified scene on outage and switches only to verified geometry', () => {
  const outage = layoutResponse.parse({ layout: null, profile_digest: staticWarehouse.profile_digest })
  expect(resolveWarehouseProfile(initial, outage, 'backend/source').layout).toEqual(initialLayout)

  const otherLayout: GridLayout = { ...initialLayout,
    bounds: { ...initialLayout.bounds, x_min: -14.5, x_max: 14.5 } }
  const otherDigest = 'a'.repeat(64)
  const switched = resolveWarehouseProfile(initial,
    layoutResponse.parse({ layout: otherLayout, profile_digest: otherDigest }), 'backend/source')
  expect(switched.layout).toEqual(otherLayout)
  expect(switched.profileDigest).toBe(otherDigest)

  const unavailable = resolveWarehouseProfile(switched,
    layoutResponse.parse({ layout: null, profile_digest: 'b'.repeat(64) }), 'backend/source')
  expect(unavailable.layout).toBeUndefined()
  expect(unavailable.mismatch).toBe(true)
})


test('catalog permissions stay separate from the current pickup and dropoff role', () => {
  const fleet = { map_frame: 'map', robots: [], stations: [], tasks: [] } as unknown as Fleet
  const points = operationPoints(fleet, undefined, true, initialLayout)
  expect(points.find(point => point.id === 'pick_E1')?.kind).toBe('neutral')
  expect(points.find(point => point.id === 'inbound_1')?.kind).toBe('pickup')
  expect(points.find(point => point.id === 'packing_1')?.kind).toBe('dropoff')
  expect(pointStyle.pickup.color).toBe('#168DA4')
  expect(pointStyle.dropoff.color).toBe('#D18A28')
  const bay = initialLayout.transfer_points.find(point => point.id === 'pick_E1')!
  const active = { ...fleet, tasks: [{ task_id: 'job', status: 'EXECUTING',
    pickup: { ...bay.pose, frame_id: 'map' },
    dropoff: { x: 0, y: 0, yaw: 0, frame_id: 'map' } }] } as Fleet
  const activePoints = operationPoints(active, undefined, true, initialLayout)
  expect(activePoints.filter(point => point.position[0] === bay.pose.x && point.position[2] === -bay.pose.y)
    .map(point => point.kind)).toEqual(['pickup'])
  const noRole = { ...initialLayout, transfer_points: initialLayout.transfer_points.map(point =>
    point.id === 'pick_E1' ? { ...point, roles: [] } : point) }
  expect(operationPoints(fleet, undefined, true, noRole).find(point => point.id === 'pick_E1')?.kind)
    .toBe('unknown')
})


test('floor text names all operational zones and four main aisles', () => {
  const fleet = { map_frame: 'map', robots: [], stations: [], tasks: [] } as unknown as Fleet
  const points = operationPoints(fleet, undefined, true, initialLayout)
  for (const y of [1.5, 2.75, 4]) points.push({ key: `park:${y}`, id: `park:${y}`,
    kind: 'PARKING', position: [13.5, 0, -y], yaw: Math.PI })
  for (const x of [6.75, 8, 9.25, 10.5, 11.75, 13]) points.push({ key: `dock:${x}`, id: `dock:${x}`,
    kind: 'CHARGING', position: [x, 0, -8.25], yaw: 0 })
  const signs = floorSignLayout(initialLayout, points)
  expect(signs.map(sign => sign.text).sort()).toEqual([
    'MAL KABUL', 'PAKETLEME', 'SEVKİYAT', 'KALİTE KONTROL', 'ŞARJ',
    'ANA KORİDOR A', 'ANA KORİDOR B', 'ANA KORİDOR C', 'ANA KORİDOR D',
  ].sort())
  const box = (x: number, y: number, width: number, height: number) => ({
    x_min: x - width / 2, x_max: x + width / 2, y_min: y - height / 2, y_max: y + height / 2,
  })
  const overlaps = (a: ReturnType<typeof box>, b: ReturnType<typeof box>) =>
    a.x_min < b.x_max && a.x_max > b.x_min && a.y_min < b.y_max && a.y_max > b.y_min
  for (const sign of signs) {
    const vertical = !!sign.yaw
    const area = box(sign.x, -sign.z, vertical ? sign.height! : sign.width,
      vertical ? sign.width : sign.height!)
    expect(initialLayout.racks.some(rack => overlaps(area, rack.bounds))).toBe(false)
    expect(points.some(point => overlaps(area, box(point.position[0], -point.position[2], 1.24, 1.24)))).toBe(false)
  }
})
