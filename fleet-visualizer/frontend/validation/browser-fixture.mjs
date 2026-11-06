// Test-only WebSocket routes. No fixture data is reachable from the application bundle.
import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { chromium } from 'playwright-core'
import { assertFollow, checkLayout, closeTo, performanceProbe, recordWebGL, settledFrame } from './webgl.mjs'

const directory = process.env.VISUALIZER_EVIDENCE
const executablePath = process.env.CHROME_EXECUTABLE
assert(directory && executablePath, 'Set VISUALIZER_EVIDENCE and CHROME_EXECUTABLE')
mkdirSync(directory, { recursive: true })

const browser = await chromium.launch({ executablePath, args: ['--enable-webgl', '--enable-unsafe-swiftshader'] })
const page = await browser.newPage({ viewport: { width: 1280, height: 850 }, deviceScaleFactor: 2 })
const errors = await recordWebGL(page)
await page.addInitScript(() => {
  window.poseFrames = []
  document.addEventListener('fleet-visualizer:rendered', event => window.poseFrames.push(event.detail))
})

const identity = { version: 1, robot_id: 'configured_bot', frame_id: 'map', source: 'tf', epoch: 0,
  stream_id: 'b0800df7-63ee-4281-a509-cdf5ca44a69e' }
let socket
let opens = 0
let stamp = 0
const send = (type, body) => socket.send(JSON.stringify({ ...identity, type, ...body }))
const pose = (x, y, yaw) => send('robot_pose', { x, y, yaw, stamp_ns: String(++stamp * 100_000_000) })
const move = () => pose(0.9, -1.3, Math.PI / 2)
const state = (name, expected) => page.waitForFunction(([name, expected]) =>
  document.querySelector(`[data-testid="${name}"]`)?.textContent === expected, [name, expected])
const screenshot = name => page.screenshot({ path: join(directory, name + '.png') })
const latest = () => page.evaluate(() => window.sceneFrames.at(-1))

await page.routeWebSocket('**/telemetry', route => {
  socket = route
  opens++
  send('hello', { after_stamp_ns: String(stamp * 100_000_000), stale_after_ms: 1500 })
})

try {
  await page.goto(process.env.VISUALIZER_URL || 'http://127.0.0.1:5173/?trace')
  await state('connection', 'CONNECTED')
  await state('freshness', 'NO_DATA')
  assert.equal(await page.getByTestId('robot-id').textContent(), identity.robot_id)
  assert.equal((await settledFrame(page, 'free')).visible, false)
  pose(0.2, -0.3, 0)
  await state('freshness', 'LIVE')
  await page.waitForFunction(() => window.poseFrames.length === 1)
  const first = await latest()
  assert.deepEqual(first.pose, [0.2, 0, 0.3])
  assert.equal(first.visible, true)
  assert(first.calls >= 20 && first.triangles > 1000 && first.geometries > 20)
  assert(await page.locator('.robot-label').isVisible())
  await checkLayout(page, { width: 1280, height: 850 })
  await screenshot('free-1280x850')

  const canvas = await page.locator('canvas').boundingBox()
  const x = canvas.x + canvas.width * 0.45
  const y = canvas.y + canvas.height * 0.42
  await page.mouse.move(x, y)
  await page.mouse.down()
  await page.mouse.move(x + 40, y - 17, { steps: 6 })
  await page.mouse.up()
  assert.notDeepEqual((await latest()).camera, first.camera)
  const orbitCamera = (await latest()).camera
  await page.mouse.wheel(0, -180)
  await page.waitForFunction(position =>
    window.sceneFrames.at(-1).camera.some((value, i) => Math.abs(value - position[i]) > 0.25), orbitCamera)
  const beforePan = (await latest()).target
  await page.mouse.move(x, y)
  await page.mouse.down({ button: 'right' })
  await page.mouse.move(x - 40, y + 20, { steps: 6 })
  await page.mouse.up({ button: 'right' })
  assert.notDeepEqual((await latest()).target, beforePan)

  await page.getByRole('button', { name: 'Robotu takip et' }).focus()
  await page.keyboard.press('Enter')
  move()
  assertFollow(await settledFrame(page, 'follow'))
  const stopProbe = await performanceProbe(browser, page)
  for (let i = 0; i < 40; i++) {
    pose(0.9 + i * 0.008, -1.3, Math.PI / 2)
    await new Promise(resolve => setTimeout(resolve, 50))
  }
  const performance = await stopProbe()
  assertFollow(await settledFrame(page, 'follow'))
  const sample = await page.evaluate(() => window.poseFrames.at(-1))
  closeTo(sample.heading_x, 0)
  closeTo(sample.heading_z, -1)
  await screenshot('follow-1280x850')

  const stampBeforeCut = await page.getByTestId('stamp').textContent()
  await state('freshness', 'STALE')
  await state('connection', 'CONNECTED')
  const held = await settledFrame(page, 'follow')
  assertFollow(held)
  send('data_status', { status: 'FRAME_ERROR' })
  await state('freshness', 'FRAME_ERROR')
  assert(await page.getByText('TF zinciri veya koordinat çerçevesi doğrulanamadı.').isVisible())
  await screenshot('frame-error')
  await socket.close()
  await state('connection', 'DISCONNECTED')
  assert.deepEqual((await latest()).pose, held.pose)
  assert.deepEqual((await latest()).target, held.target)
  assert.equal(await page.getByTestId('stamp').textContent(), stampBeforeCut)
  await state('connection', 'CONNECTED')
  assert(opens >= 2)
  await state('freshness', 'STALE')
  pose(1.45, 0.45, -Math.PI / 2)
  await state('freshness', 'LIVE')
  await page.waitForFunction(() => window.sceneFrames.at(-1).pose[0] === 1.45)
  const recovered = await settledFrame(page, 'follow')
  assertFollow(recovered)
  assert.deepEqual(recovered.pose, [1.45, 0, -0.45])

  await page.getByRole('button', { name: 'Üstten' }).click()
  const top = await settledFrame(page, 'top')
  assert(top.camera[1] - top.target[1] > 18 && Math.hypot(top.camera[0], top.camera[2]) < 0.05)
  await checkLayout(page, { width: 1440, height: 900 })
  await screenshot('top-1440x900')
  await page.getByRole('button', { name: 'Kamerayı sıfırla' }).click()
  const reset = await settledFrame(page, 'free')
  for (const [i, offset] of [6.4, 8.5, 8.4].entries()) closeTo(reset.camera[i] - reset.target[i], offset)
  assert.equal(await page.getByRole('button', { name: 'Serbest' }).getAttribute('aria-pressed'), 'true')
  await checkLayout(page, { width: 1920, height: 1080 })
  await screenshot('reset-1920x1080')

  const standard = await latest()
  await page.getByLabel('Görsel kalite').selectOption('low')
  await page.waitForFunction(calls => {
    const frame = window.sceneFrames.at(-1)
    return frame?.dpr === 1 && frame.calls < calls
  }, standard.calls)
  const low = await latest()
  await checkLayout(page, { width: 390, height: 844 })
  await screenshot('low-390x844')
  assert.equal((await latest()).dpr, 1)

  send('data_status', { status: 'NO_DATA', epoch: 1 })
  await state('freshness', 'NO_DATA')
  pose(4, 4, 0) // This later packet still has the old epoch.
  assert.deepEqual((await latest()).pose, recovered.pose)
  send('robot_pose', { epoch: 1, stamp_ns: '1', x: -0.25, y: 0.35, yaw: 0 })
  await state('freshness', 'LIVE')
  await page.waitForFunction(() => window.sceneFrames.at(-1).pose[0] === -0.25)
  assert.equal((await latest()).interpolating, false)
  assert.deepEqual((await latest()).pose, [-0.25, 0, -0.35])
  assert.deepEqual(errors, [])
  writeFileSync(join(directory, 'result.json'), JSON.stringify({
    chrome: browser.version(), fixture: true, errors, performance, opens,
    lowQuality: { dpr: low.dpr, calls: low.calls, geometries: low.geometries, textures: low.textures },
  }, null, 2))
} finally {
  await browser.close()
}
