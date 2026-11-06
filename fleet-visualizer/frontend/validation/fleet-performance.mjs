// Measure the standard-quality fleet with all configured roots in view.
import assert from 'node:assert/strict'
import { chromium } from 'playwright-core'
import { performanceProbe, recordWebGL, settledFrame } from './webgl.mjs'

const executablePath = process.env.CHROME_EXECUTABLE
assert(executablePath)
const browser = await chromium.launch({ executablePath, args: ['--enable-webgl', '--enable-unsafe-swiftshader'] })
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 850 } })
  const errors = await recordWebGL(page)
  const arrivals = []
  page.on('websocket', socket => {
    if (!socket.url().endsWith('/telemetry/fleet')) return
    socket.on('framereceived', ({ payload }) => {
      const packet = JSON.parse(String(payload))
      if (packet.type === 'robot_pose') arrivals.push({ id: packet.robot_id, at: Date.now() })
    })
  })
  await page.goto(process.env.VISUALIZER_URL || 'http://127.0.0.1:5173/?trace')
  await page.waitForFunction(() => {
    const models = window.sceneFrames.at(-1)?.robots
    return models?.length >= 2 && models.every(model => model.visible && model.status === 'LIVE')
  })
  await page.getByRole('button', { name: 'Filoyu kadraja al' }).click()
  const frame = await settledFrame(page, 'fit')
  assert(frame.robots.every(robot => robot.screen.every(value => value > 0 && value < 1)))
  const start = Date.now()
  const finish = await performanceProbe(browser, page)
  await page.waitForTimeout(5000)
  const perf = await finish()
  const end = Date.now()
  assert.deepEqual(errors, [])
  console.log(JSON.stringify({
    chrome: browser.version(), ...perf,
    websocket_hz: Object.fromEntries(frame.robots.map(({ robot_id: id }) => [id,
      arrivals.filter(a => a.id === id && a.at >= start && a.at < end).length * 1000 / (end - start),
    ])),
  }, null, 2))
} finally {
  await browser.close()
}
