// Isolated real ROS BatterySimulator -> API -> Chrome acceptance. No Gazebo/FM claim.
import { chromium } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const token = (await readFile(process.env.C5_BATTERY_TOKEN_FILE ?? '/tmp/fleet-battery-control-token', 'utf8')).trim();
const uiURL = `http://127.0.0.1:${process.env.C5_UI_PORT}`;
const apiURL = `http://127.0.0.1:${process.env.C5_API_PORT}`;
if (!process.env.C5_UI_PORT || !process.env.C5_API_PORT) throw Error('C5_UI_PORT and C5_API_PORT required');
const evidence = process.env.C5_BATTERY_EVIDENCE;
if (!evidence) throw Error('C5_BATTERY_EVIDENCE required');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  await page.goto(`${uiURL}/#stations`);
  const panel = page.locator('.battery-simulation');
  await panel.getByLabel('Simülasyon erişim anahtarı').fill(token);
  await page.waitForFunction(() => document.querySelectorAll('[aria-label="Batarya robotu"] option').length === 2);
  await panel.getByLabel('Batarya robotu').selectOption('robot_1');
  await panel.getByLabel('SoC değişikliğini dahil et').check();
  await panel.getByRole('button', { name: '%25', exact: true }).click();
  await panel.getByLabel('Güvenli test ortamında çalıştığımı onaylıyorum.').check();
  await panel.getByRole('button', { name: 'Seçili robota uygula' }).click();
  await panel.getByRole('status').filter({ hasText: 'robot_1: doğrulandı' }).waitFor();
  await page.waitForFunction(() => {
    const p = [...document.querySelectorAll('.battery-simulation p')].find(p => p.textContent.startsWith('Gerçek BatteryState'));
    return p?.textContent.includes('24.') || p?.textContent.includes('25.');
  });
  const individual = await panel.getByRole('status').innerText();
  const fleet = await (await page.request.get(`${apiURL}/api/fleet`)).json();
  assert(fleet.robots.find(r => r.robot_id === 'robot_2').battery_soc_percent > 99);
  // Bulk profile only: no implicit SoC reset and no bulk SoC consent required.
  await panel.getByLabel('SoC değişikliğini dahil et').uncheck();
  await panel.getByLabel('Tükenme süresi').fill('5');
  await panel.getByLabel('Şarj süresi').fill('15');
  await panel.getByRole('button', { name: 'Tüm robotlara uygula' }).click();
  await panel.getByRole('status').filter({ hasText: 'robot_2: doğrulandı' }).waitFor();
  const bulk = await panel.getByRole('status').innerText();
  const inventory = await (await page.request.get(`${apiURL}/api/sim/batteries`,
    { headers: { Authorization: `Bearer ${token}` } })).json();
  assert(inventory.robots.every(r => r.state.idle_power_w === 900 && r.state.charge_power_w === 1120));
  assert(inventory.robots.find(r => r.robot_id === 'robot_1').state.soc_percent < 26);
  assert(inventory.robots.find(r => r.robot_id === 'robot_2').state.soc_percent > 99);
  const denied = await page.request.get(`${apiURL}/api/sim/batteries`);
  assert.equal(denied.status(), 401);
  await page.waitForTimeout(1700);
  await page.screenshot({ path: `${evidence}/live-chrome.png`, fullPage: true });
  await writeFile(`${evidence}/live-chrome.json`, JSON.stringify({ individual, bulk, inventory, errors,
    scope: 'Two real BatterySimulator nodes, controlled ROS clock, real API and Chrome; no Gazebo, FM or physical charging acceptance' }, null, 2));
  assert.deepEqual(errors, []);
  console.log('PASS: real two-robot ROS -> API -> Chrome control and BatteryState readback; identity isolation; bulk profile; auth');
} finally { await browser.close(); }
