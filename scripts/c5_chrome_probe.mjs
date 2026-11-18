// Read-only Chrome timing probe for the isolated C5 demo UI.
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const [url, outputPath, seconds = '60'] = process.argv.slice(2)
if (!url || !outputPath) throw new Error('usage: node c5_chrome_probe.mjs URL OUTPUT [SECONDS]')
const output = fs.createWriteStream(outputPath)
const record = (kind, fields = {}) => output.write(JSON.stringify({ kind, utc: new Date().toISOString(), ...fields }) + '\n')
const browser = await chromium.launch({ channel: 'chrome', headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl'] })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  page.on('websocket', socket => {
    if (!socket.url().includes('/ws/fleet')) return
    record('ws_open')
    socket.on('framereceived', event => {
      try {
        const data = JSON.parse(event.payload.toString())
        if (data.type === 'scene' && ['robot_pose', 'data_status'].includes(data.packet?.type)) {
          record('ws_scene', { robot_id: data.packet.robot_id, type: data.packet.type,
            stamp_ns: data.packet.stamp_ns, status: data.packet.status })
        } else if (data.type === 'heartbeat') record('ws_heartbeat')
        else if (data.sequence) record('ws_product', { sequence: data.sequence,
          generated_at_utc: data.generated_at_utc })
      } catch (error) { record('ws_parse_error', { error: String(error) }) }
    })
    socket.on('close', () => record('ws_close'))
  })
  page.on('console', message => { if (message.type() === 'error') record('console_error', { text: message.text() }) })
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
  record('page_loaded')
  await page.evaluate(() => {
    window.__fleetLongTasks = []
    new PerformanceObserver(list => {
      for (const entry of list.getEntries()) window.__fleetLongTasks.push(entry.duration)
    }).observe({ entryTypes: ['longtask'] })
  })
  const stop = Date.now() + Number(seconds) * 1000
  while (Date.now() < stop) {
    const state = await page.evaluate(() => ({
      indicator: document.querySelector('.scene-indicator')?.textContent,
      robots: [...document.querySelectorAll('.scene-marker')].map(node => ({
        id: node.getAttribute('data-robot-id'), status: [...node.classList].find(x => ['live', 'stale', 'no_data', 'frame_error'].includes(x))
      })),
      longTasks: window.__fleetLongTasks.splice(0),
    }))
    record('dom', state)
    await page.waitForTimeout(250)
  }
} finally {
  await browser.close()
  output.end()
}
