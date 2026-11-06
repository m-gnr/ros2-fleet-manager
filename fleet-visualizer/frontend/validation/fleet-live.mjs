// Live acceptance probe for the C4.5 energy and charging profiles.
import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { promisify } from 'node:util'
import { chromium } from 'playwright-core'
import { assertFollow, closeTo, performanceProbe, recordWebGL, settledFrame } from './webgl.mjs'

const {
  CHROME_EXECUTABLE: executablePath, VISUALIZER_EVIDENCE: directory,
  VISUALIZER_GATE_DIR: gates, VISUALIZER_BRIDGE: bridge, VISUALIZER_BACKEND_DONE: backendDone,
  VISUALIZER_PROFILE: profile = 'energy',
  VISUALIZER_URL: url = 'http://127.0.0.1:5174/?trace',
} = process.env
assert(executablePath && directory && (profile === 'charging' || (gates && bridge)))
mkdirSync(directory, { recursive: true })
const mark = (name, value) => writeFileSync(join(directory, name + '.json'), JSON.stringify(value, null, 2))
const docker = promisify(execFile)
const browser = await chromium.launch({ executablePath, args: ['--enable-webgl', '--enable-unsafe-swiftshader'] })
const page = await browser.newPage({ viewport: { width: 1280, height: 850 } })
const errors = await recordWebGL(page)
const packets = []
let connections = 0
let evidence
page.on('websocket', socket => {
  if (!socket.url().endsWith('/telemetry/fleet')) return
  connections++
  socket.on('framereceived', ({ payload }) => packets.push({ ...JSON.parse(String(payload)), wall_ms: Date.now() }))
})
await page.addInitScript(() => {
  window.poseFrames = []
  document.addEventListener('fleet-visualizer:rendered', event => window.poseFrames.push(event.detail))
})

const [first, second] = ['robot_1', 'robot_2']
const gate = gates && join(gates, first)
const state = (name, expected) => page.waitForFunction(([name, expected]) =>
  document.querySelector(`[data-testid="${name}"]`)?.textContent === expected,
[name, expected], { timeout: 45_000 })
const live = id => state('freshness-' + id, 'LIVE')
const select = id => page.getByRole('list', { name: 'Filo robotları' }).getByRole('button', { name: new RegExp(id) }).click()
const camera = name => page.getByRole('button', { name }).click()
const screenshot = name => page.screenshot({ path: join(directory, name + '.png') })
const root = (frame, id) => frame.robots.find(robot => robot.robot_id === id)
const latest = () => page.evaluate(() => window.sceneFrames.at(-1))
const samples = () => page.evaluate(() => ({ frames: window.poseFrames, scenes: window.sceneFrames }))

try {
  await page.goto(url)
  await live(first)
  await live(second)
  assert.equal(connections, 1)
  await camera('Filoyu kadraja al')
  const fitted = await settledFrame(page, 'fit')
  assert.equal(fitted.robots.filter(robot => robot.visible).length, 2)
  assert.notDeepEqual(root(fitted, first).pose, root(fitted, second).pose)
  for (const id of [first, second]) {
    assert(root(fitted, id).screen.every(value => value > 0 && value < 1))
    assert(await page.locator(`.robot-label[data-robot-id="${id}"]`).isVisible())
  }
  await screenshot('two-robots-fit')

  if (profile === 'charging') {
    mark('ready', fitted)
    await page.waitForFunction(initial => initial.every(start => window.poseFrames.some(frame =>
      frame.robot_id === start.robot_id && Math.hypot(frame.x - start.pose[0], frame.z - start.pose[2]) > 0.15,
    )), fitted.robots, { timeout: 420_000 })
    await live(first)
    await live(second)
    await camera('Filoyu kadraja al')
    const moved = await settledFrame(page, 'fit')
    mark('both-moved', moved)
    await screenshot('charging-both-moved')
  } else {
    const box = await page.locator('canvas').boundingBox()
    const [x, y] = root(fitted, second).screen
    await page.mouse.click(box.x + box.width * x, box.y + box.height * y)
    await state('robot-id', second)
    const xReading = await page.locator('.metrics dd').first().textContent()
    closeTo(Number(xReading), root(fitted, second).pose[0], 0.002)
    await camera('Robotu takip et')
    assertFollow(await settledFrame(page, 'follow'))

    const oldTarget = (await latest()).target
    await select(first)
    await state('robot-id', first)
    await page.waitForFunction(() => window.sceneFrames.some(frame => frame.selected === 'robot_1' &&
      frame.mode === 'follow' && frame.transitioning))
    const followed = await settledFrame(page, 'follow')
    assert.equal(followed.selected, first)
    assert.notDeepEqual(followed.target, oldTarget)
    assertFollow(followed)

    writeFileSync(gate, '')
    await state('freshness-' + first, 'STALE')
    await live(second)
    const held = await settledFrame(page, 'follow')
    assertFollow(held)
    const heldStamp = await page.getByTestId('stamp').textContent()
    mark('ready', held)
    await page.waitForFunction(start => {
      const frame = window.sceneFrames.at(-1)
      const robot = frame.robots.find(robot => robot.robot_id === 'robot_2')
      return robot?.status === 'LIVE' && Math.hypot(robot.pose[0] - start[0], robot.pose[2] - start[2]) > 0.23
    }, root(held, second).pose, { timeout: 420_000 })
    await state('freshness-' + first, 'STALE')
    await live(second)
    await state('connection', 'CONNECTED')
    const cut = await latest()
    assert.deepEqual(root(cut, first).pose, root(held, first).pose)
    assert.deepEqual(cut.target, held.target)
    assert.equal(await page.getByTestId('stamp').textContent(), heldStamp)
    mark('isolated-cut', { before: held, after: cut, heldStamp })
    await camera('Filoyu kadraja al')
    await settledFrame(page, 'fit')
    await screenshot('robot-1-stale-robot-2-live')

    rmSync(gate)
    await live(first)
    await live(second)
    assert.notEqual(await page.getByTestId('stamp').textContent(), heldStamp)
    await select(second)
    await camera('Robotu takip et')
    assertFollow(await settledFrame(page, 'follow'))
    const performanceStart = Date.now()
    const stopProbe = await performanceProbe(browser, page)
    await page.waitForTimeout(4000)
    const performance = await stopProbe()
    const performanceEnd = Date.now()
    performance.websocket_hz = Object.fromEntries([first, second].map(id => [id,
      packets.filter(p => p.type === 'robot_pose' && p.robot_id === id &&
        p.wall_ms >= performanceStart && p.wall_ms < performanceEnd).length * 1000 /
        (performanceEnd - performanceStart),
    ]))
    mark('performance', performance)
    await screenshot('robot-2-follow')
    mark('moving', await latest())

    await docker('docker', ['stop', bridge])
    await state('connection', 'DISCONNECTED')
    await state('freshness-' + first, 'STALE')
    await state('freshness-' + second, 'STALE')
    mark('bridge-off', { at: new Date().toISOString(), frame: await latest() })
    if (backendDone) {
      for (let i = 0; i < 300 && !existsSync(backendDone); i++) await page.waitForTimeout(200)
      assert(existsSync(backendDone), 'C4.5 backend did not exit while bridge was stopped')
    } else {
      await page.waitForTimeout(2000)
    }
    await docker('docker', ['start', bridge])
    await live(first)
    await live(second)
    mark('bridge-on', { at: new Date().toISOString(), frame: await latest() })
    assert(connections >= 2)
  }
  assert.deepEqual(errors, [])

  const key = (sample, stamp = sample.stamp_ns) => JSON.stringify([sample.stream_id, sample.epoch, stamp])
  evidence = await samples()
  const { frames, scenes } = evidence
  const byStamp = new Map(packets.filter(packet => packet.type === 'robot_pose').map(packet => [key(packet), packet]))
  const compared = {}
  for (const id of [first, second]) {
    const rendered = frames.filter(frame => frame.robot_id === id)
    let maxPositionError = 0
    let maxHeadingError = 0
    let checkedBlends = 0
    for (const frame of rendered) {
      const packet = byStamp.get(key(frame))
      assert.equal(packet?.robot_id, id)
      maxPositionError = Math.max(maxPositionError, Math.hypot(frame.x - packet.x, frame.z + packet.y))
      maxHeadingError = Math.max(maxHeadingError, Math.hypot(
        frame.heading_x - Math.cos(packet.yaw), frame.heading_z + Math.sin(packet.yaw)))
    }
    assert(rendered.length > 5 && maxPositionError < 1e-8 && maxHeadingError < 1e-8)
    for (const frame of scenes) {
      const model = root(frame, id)
      if (!model?.blend) continue
      const { fraction, from, to } = model.blend
      const start = byStamp.get(key(model.blend, from))
      const end = byStamp.get(key(model.blend, to))
      assert(start?.robot_id === id && end?.robot_id === id && BigInt(from) < BigInt(to) &&
        fraction >= 0 && fraction < 1)
      closeTo(model.pose[0], start.x + fraction * (end.x - start.x))
      closeTo(model.pose[2], -(start.y + fraction * (end.y - start.y)))
      const wrap = angle => Math.atan2(Math.sin(angle), Math.cos(angle))
      closeTo(wrap(model.yaw - start.yaw - fraction * wrap(end.yaw - start.yaw)), 0)
      checkedBlends++
    }
    assert(checkedBlends > 0)
    compared[id] = { rendered: rendered.length, maxPositionError, maxHeadingError, checkedBlends }
  }
  mark('result', { chrome: browser.version(), connections, compared, errors })
} finally {
  if (gate) rmSync(gate, { force: true })
  const { frames, scenes } = evidence ?? await samples()
  mark('packets', packets)
  mark('frames', frames)
  mark('scene-frames', scenes)
  await browser.close()
}
