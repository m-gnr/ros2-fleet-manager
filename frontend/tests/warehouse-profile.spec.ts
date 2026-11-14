import { expect, test } from '@playwright/test'
import { staticWarehouse } from '../src/scene/warehouseProfile.generated'
import { warehouseLayoutSchema, type GridLayout, layoutResponse } from '../src/scene/gridLayout'
import { resolveWarehouseProfile } from '../src/scene/useGridLayout'

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
