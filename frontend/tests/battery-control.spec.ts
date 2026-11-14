import { test, expect } from '@playwright/test';
import { feed, fixture, valid } from './dashboard-fixtures';

const state = (id: string) => ({ robot_id: id, session_id: `session-${id}`, revision: 0, soc_percent: 72.5,
  energy_wh: 72.5, capacity_wh: 100, mode: 'NORMAL' as const, discharge_minutes: 0, charge_minutes: 0,
  idle_power_w: 2, charge_power_w: 20, consumption_wh_per_meter: .2 });
const robot = (id: string, available = true) => ({ robot_id: id, namespace: `/fleet/${id}`, available,
  ...(available ? { state: state(id) } : { error: 'BatteryState telemetry stale or unavailable' }) });

test('third config robot, explicit bulk consent, distinct telemetry and partial outcome', async ({ page }) => {
  const ids = ['robot_alpha', 'robot_beta', 'synthetic_third'];
  await feed(page, socket => {
    let sequence = 1;
    const timer = setInterval(() => socket.send(JSON.stringify({ ...fixture, sequence: ++sequence,
      robots: ids.map(robot_id => ({ ...valid, robot_id })) })), 200);
    socket.onClose(() => clearInterval(timer));
  });
  await page.route('**/api/sim/batteries', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: { enabled: true, robots: [robot(ids[0]), robot(ids[1], false), robot(ids[2])] } });
    } else {
      const payload = route.request().postDataJSON();
      expect(payload.confirm_bulk_soc).toBe(true);
      expect(Object.keys(payload.sessions)).toHaveLength(3);
      await route.fulfill({ json: { atomic: false, all_verified: false, results: [
        { robot_id: ids[0], outcome: 'VERIFIED', readback: { ...state(ids[0]), soc_percent: 25 } },
        { robot_id: ids[1], outcome: 'REJECTED', error: 'Service disconnected' },
        { robot_id: ids[2], outcome: 'VERIFIED', readback: { ...state(ids[2]), soc_percent: 25 } },
      ] } });
    }
  });
  await page.goto('/#stations');
  const panel = page.locator('.battery-simulation');
  await panel.getByLabel('Simülasyon erişim anahtarı').fill('test-secret-only');
  await expect(panel.getByLabel('Batarya robotu').locator('option')).toHaveCount(3);
  await panel.getByLabel('Batarya robotu').selectOption('synthetic_third');
  await panel.getByLabel('SoC değişikliğini dahil et').check();
  await panel.getByRole('button', { name: '%25', exact: true }).click();
  await panel.getByLabel('Güvenli test ortamında çalıştığımı onaylıyorum.').check();
  const all = panel.getByRole('button', { name: 'Tüm robotlara uygula' });
  await expect(all).toBeDisabled();
  await panel.getByLabel('Tüm robotların SoC değerini değiştirmeyi açıkça onaylıyorum.').check();
  await all.click();
  await expect(panel.getByRole('status')).toContainText('synthetic_third: doğrulandı');
  await expect(panel.getByRole('status')).toContainText('robot_beta: reddedildi');
  await expect(panel.getByText(/Gerçek BatteryState telemetrisi/)).toContainText('72.50%');
  // Selecting the unavailable robot must disable its individual action.
  await panel.getByLabel('Batarya robotu').selectOption('robot_beta');
  await expect(panel.getByRole('button', { name: 'Seçili robota uygula' })).toBeDisabled();
  await page.screenshot({ path: process.env.C5_BATTERY_SCREENSHOT ?? '/tmp/c5-battery-panel.png', fullPage: true });
});
