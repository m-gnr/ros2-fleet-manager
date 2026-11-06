// Cold, local production loads in separate browser contexts using the same fixture pose.
import assert from 'node:assert/strict'
import { chromium } from 'playwright-core'

const urls = process.argv.slice(2)
const executablePath = process.env.CHROME_EXECUTABLE
assert(executablePath && urls.length, 'Set CHROME_EXECUTABLE and pass production URLs with ?trace')

const browser = await chromium.launch({ executablePath, args: ['--enable-webgl', '--enable-unsafe-swiftshader'] })
const results = []
try {
  for (const url of urls) {
    for (let iteration = 1; iteration <= 3; iteration++) {
      const page = await browser.newPage({ viewport: { width: 1280, height: 850 } })
      await page.addInitScript(() => {
        document.addEventListener('fleet-visualizer:rendered', () => {
          window.firstPoseAt = performance.now()
        }, { once: true })
      })
      await page.routeWebSocket('**/telemetry', socket => {
        const identity = { version: 1, robot_id: 'test_robot', frame_id: 'map', source: 'tf', epoch: 0,
          stream_id: 'b0800df7-63ee-4281-a509-cdf5ca44a69e' }
        socket.send(JSON.stringify({ ...identity, type: 'hello', after_stamp_ns: '0', stale_after_ms: 2000 }))
        socket.send(JSON.stringify({ ...identity, type: 'robot_pose', stamp_ns: '1', x: 0.2, y: -0.3, yaw: 0 }))
      })
      await page.goto(url)
      await page.waitForFunction(() => window.firstPoseAt && performance.getEntriesByName('first-contentful-paint').length)
      const metrics = await page.evaluate(() => {
        const scripts = performance.getEntriesByType('resource').filter(resource => new URL(resource.name).pathname.endsWith('.js'))
        return {
          first_contentful_paint_ms: performance.getEntriesByName('first-contentful-paint')[0].startTime,
          first_exact_pose_frame_ms: window.firstPoseAt,
          js_requests: scripts.length,
          js_decoded_bytes: scripts.reduce((sum, script) => sum + script.decodedBodySize, 0),
        }
      })
      results.push({ url, iteration, ...metrics })
      await page.close()
    }
  }
  console.log(JSON.stringify({ chrome: browser.version(), fixture: true, results }, null, 2))
} finally {
  await browser.close()
}
