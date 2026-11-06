// Opt-in acceptance probe against the running visualizer and real ROS data.
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { chromium } from 'playwright-core'

const directory = process.env.VISUALIZER_EVIDENCE
const executablePath = process.env.CHROME_EXECUTABLE
assert(directory && executablePath, 'Set VISUALIZER_EVIDENCE and CHROME_EXECUTABLE')
mkdirSync(directory, { recursive: true })

const browser = await chromium.launch({ executablePath, args: ['--enable-webgl', '--enable-unsafe-swiftshader'] })
const page = await browser.newPage({ viewport: { width: 1280, height: 850 } })
const packets = []
const errors = []
page.on('pageerror', error => errors.push(error.message))
page.on('websocket', socket => {
  if (!socket.url().endsWith('/telemetry')) return
  socket.on('framereceived', ({ payload }) => packets.push(JSON.parse(String(payload))))
})
await page.addInitScript(() => {
  window.poseFrames = []
  document.addEventListener('fleet-visualizer:rendered', event => window.poseFrames.push(event.detail))
})

function mark(name, value) {
  writeFileSync(join(directory, name + '.json'), JSON.stringify(value, null, 2))
}

async function hasState(name, expected) {
  await page.waitForFunction(([name, expected]) =>
    document.querySelector(`[data-testid="${name}"]`)?.textContent === expected,
  [name, expected], { timeout: 180_000 })
}

async function frames() {
  return page.evaluate(() => window.poseFrames)
}

async function latestFrame() {
  return (await frames()).at(-1)
}

async function screenshot(name) {
  await page.screenshot({ path: join(directory, name + '.png') })
}

try {
  await page.goto(process.env.VISUALIZER_URL || 'http://127.0.0.1:5173/?trace')
  await hasState('connection', 'CONNECTED')
  await hasState('freshness', 'LIVE')
  await page.waitForFunction(() => window.poseFrames.length > 0)
  const initial = await latestFrame()
  await screenshot('initial')

  // Exercise browser interactions before starting the movement fixture.
  const canvas = page.locator('canvas')
  const box = await canvas.boundingBox()
  assert(box && box.width > 300 && box.height > 200)
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
  await page.mouse.down()
  await page.mouse.move(box.x + box.width / 2 + 36, box.y + box.height / 2 + 8, { steps: 4 })
  await page.mouse.up()
  await page.mouse.wheel(0, -110)
  const follow = page.getByRole('button', { name: 'Robotu takip et' })
  await follow.click()
  assert.equal(await follow.getAttribute('aria-pressed'), 'true')
  mark('ready', initial)

  await page.waitForFunction(initial => window.poseFrames.some(frame =>
    Math.hypot(frame.x - initial.x, frame.z - initial.z) > 0.4 &&
    Math.abs(Math.atan2(frame.heading_z, frame.heading_x) -
             Math.atan2(initial.heading_z, initial.heading_x)) > 0.2
  ), initial, { timeout: 150_000 })
  await screenshot('moving')
  mark('moving', await latestFrame())

  if (process.env.VISUALIZER_CUTS === '1') {
    await hasState('freshness', 'STALE')
    await hasState('connection', 'CONNECTED')
    const held = await latestFrame()
    const stamp = await page.getByTestId('stamp').textContent()
    await screenshot('stale')
    assert.equal(await page.getByTestId('stamp').textContent(), stamp)
    assert.deepEqual(await latestFrame(), held)
    mark('stale', held)

    await hasState('freshness', 'LIVE')
    const recovered = await latestFrame()
    mark('ros-recovered', recovered)

    await hasState('connection', 'DISCONNECTED')
    await screenshot('disconnected')
    mark('disconnected', await latestFrame())

    await hasState('connection', 'CONNECTED')
    await hasState('freshness', 'LIVE')
    await page.waitForFunction(stamp =>
      BigInt(window.poseFrames.at(-1)?.stamp_ns ?? '0') > BigInt(stamp), recovered.stamp_ns)
    await screenshot('reconnected')
    mark('reconnected', await latestFrame())
  }

  const byStamp = new Map(packets.filter(packet => packet.type === 'robot_pose')
    .map(packet => [packet.stamp_ns, packet]))
  const matched = (await frames()).filter(frame => byStamp.has(frame.stamp_ns))
  assert(matched.length > 5, 'Expected frames with matching WebSocket measurements')
  for (const frame of matched) {
    const pose = byStamp.get(frame.stamp_ns)
    assert(Math.abs(frame.x - pose.x) < 1e-8 && Math.abs(frame.z + pose.y) < 1e-8)
    assert(Math.abs(frame.heading_x - Math.cos(pose.yaw)) < 1e-8)
    assert(Math.abs(frame.heading_z + Math.sin(pose.yaw)) < 1e-8)
  }
  assert.deepEqual(errors, [])
  mark('result', { renderedMatchingWebSocket: matched.length, errors })
} finally {
  mark('packets', packets)
  mark('frames', await frames())
  await browser.close()
}
