// Opt-in acceptance probe against the running visualizer and real ROS data.
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
const page = await browser.newPage({ viewport: { width: 1280, height: 850 } })
const packets = []
const errors = await recordWebGL(page)
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

let evidence
try {
  await page.goto(process.env.VISUALIZER_URL || 'http://127.0.0.1:5173/?trace')
  await hasState('connection', 'CONNECTED')
  await hasState('freshness', 'LIVE')
  await page.waitForFunction(() => window.poseFrames.length > 0)
  const initial = await latestFrame()
  await checkLayout(page, { width: 1280, height: 850 })
  await screenshot('initial')

  // Exercise browser interactions before starting the movement fixture.
  const canvas = page.locator('canvas')
  const box = await canvas.boundingBox()
  assert(box && box.width > 300 && box.height > 200)
  const initialCamera = (await settledFrame(page, 'free')).camera
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
  await page.mouse.down()
  await page.mouse.move(box.x + box.width / 2 + 36, box.y + box.height / 2 + 8, { steps: 4 })
  await page.mouse.up()
  await page.mouse.wheel(0, -110)
  assert.notDeepEqual((await settledFrame(page, 'free')).camera, initialCamera)
  const follow = page.getByRole('button', { name: 'Robotu takip et' })
  await follow.click()
  assert.equal(await follow.getAttribute('aria-pressed'), 'true')
  assertFollow(await settledFrame(page, 'follow'))
  const endProbe = await performanceProbe(browser, page)
  mark('ready', initial)

  await page.waitForFunction(initial => window.poseFrames.some(frame =>
    Math.hypot(frame.x - initial.x, frame.z - initial.z) > 0.4 &&
    Math.abs(Math.atan2(frame.heading_z, frame.heading_x) -
             Math.atan2(initial.heading_z, initial.heading_x)) > 0.2
  ), initial, { timeout: 150_000 })
  assertFollow(await settledFrame(page, 'follow'))
  const performance = await endProbe()
  assert(performance.interpolating_frames > 0, 'Expected bounded interpolation during real movement')
  await screenshot('moving')
  mark('moving', await latestFrame())
  mark('performance', performance)

  if (process.env.VISUALIZER_CUTS === '1') {
    await hasState('freshness', 'STALE')
    await hasState('connection', 'CONNECTED')
    const held = await latestFrame()
    const heldScene = await settledFrame(page, 'follow')
    assertFollow(heldScene)
    const stamp = await page.getByTestId('stamp').textContent()
    await screenshot('stale')
    assert.equal(await page.getByTestId('stamp').textContent(), stamp)
    assert.deepEqual(await latestFrame(), held)
    const staleScene = await settledFrame(page, 'follow')
    assert.deepEqual(staleScene.pose, heldScene.pose)
    assert.deepEqual(staleScene.target, heldScene.target)
    mark('stale', { ...held, scene: staleScene })

    await hasState('freshness', 'LIVE')
    const recovered = await latestFrame()
    mark('ros-recovered', recovered)

    await hasState('connection', 'DISCONNECTED')
    const disconnectedScene = await settledFrame(page, 'follow')
    assertFollow(disconnectedScene)
    await screenshot('disconnected')
    assert.deepEqual((await settledFrame(page, 'follow')).pose, disconnectedScene.pose)
    assert.deepEqual((await settledFrame(page, 'follow')).target, disconnectedScene.target)
    mark('disconnected', { ...await latestFrame(), scene: disconnectedScene })

    await hasState('connection', 'CONNECTED')
    await hasState('freshness', 'LIVE')
    await page.waitForFunction(stamp =>
      BigInt(window.poseFrames.at(-1)?.stamp_ns ?? '0') > BigInt(stamp), recovered.stamp_ns)
    assertFollow(await settledFrame(page, 'follow'))
    await screenshot('reconnected')
    mark('reconnected', await latestFrame())

    await page.getByRole('button', { name: 'Üstten' }).click()
    const top = await settledFrame(page, 'top')
    assert(top.camera[1] - top.target[1] > 18)
    await checkLayout(page, { width: 1440, height: 900 })
    await screenshot('top-1440x900')

    await page.getByRole('button', { name: 'Kamerayı sıfırla' }).click()
    const reset = await settledFrame(page, 'free')
    for (const [i, offset] of [6.4, 8.5, 8.4].entries()) closeTo(reset.camera[i] - reset.target[i], offset)
    await checkLayout(page, { width: 1920, height: 1080 })
    await screenshot('reset-1920x1080')
  }

  // Freeze both browser arrays before reading the independently captured socket packets.
  evidence = await page.evaluate(() => ({ poseFrames: window.poseFrames, sceneFrames: window.sceneFrames }))
  const key = (sample, stamp = sample.stamp_ns) => JSON.stringify([sample.stream_id, sample.epoch, stamp])
  const byStamp = new Map(packets.filter(packet => packet.type === 'robot_pose')
    .map(packet => [key(packet), packet]))
  const matched = evidence.poseFrames.filter(frame => byStamp.has(key(frame)))
  assert(matched.length > 5, 'Expected frames with matching WebSocket measurements')
  let maxPositionError = 0
  let maxHeadingError = 0
  for (const frame of matched) {
    const pose = byStamp.get(key(frame))
    const positionError = Math.hypot(frame.x - pose.x, frame.z + pose.y)
    const headingError = Math.hypot(frame.heading_x - Math.cos(pose.yaw), frame.heading_z + Math.sin(pose.yaw))
    maxPositionError = Math.max(maxPositionError, positionError)
    maxHeadingError = Math.max(maxHeadingError, headingError)
    assert(positionError < 1e-8 && headingError < 1e-8)
  }

  let checkedBlends = 0
  for (const frame of evidence.sceneFrames) {
    if (!frame.blend) continue
    const { fraction, from, to } = frame.blend
    const start = byStamp.get(key(frame.blend, from))
    const end = byStamp.get(key(frame.blend, to))
    assert(start && end && BigInt(from) < BigInt(to) && fraction >= 0 && fraction < 1)
    closeTo(frame.pose[0], start.x + fraction * (end.x - start.x))
    closeTo(frame.pose[2], -(start.y + fraction * (end.y - start.y)))
    const wrap = angle => Math.atan2(Math.sin(angle), Math.cos(angle))
    closeTo(wrap(frame.yaw - start.yaw - fraction * wrap(end.yaw - start.yaw)), 0)
    if (frame.mode === 'follow' && !frame.transitioning) assertFollow(frame)
    checkedBlends++
  }
  assert(checkedBlends > 5)
  assert.deepEqual(errors, [])
  mark('result', {
    chrome: browser.version(), renderedMatchingWebSocket: matched.length, checkedBlends,
    maxPositionError, maxHeadingError, errors,
  })
} finally {
  mark('packets', packets)
  mark('frames', evidence?.poseFrames ?? await frames())
  mark('scene-frames', evidence?.sceneFrames ?? await page.evaluate(() => window.sceneFrames))
  await browser.close()
}
