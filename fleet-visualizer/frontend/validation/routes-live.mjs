// C4.5 charging moves both robots using the existing acceptance profile.
import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { promisify } from 'node:util'
import { chromium } from 'playwright-core'
import { closeTo, performanceProbe, recordWebGL, settledFrame } from './webgl.mjs'

const { CHROME_EXECUTABLE: executablePath, VISUALIZER_EVIDENCE: directory,
  VISUALIZER_GATE_DIR: gates, VISUALIZER_BRIDGE: bridge, VISUALIZER_SIMULATION: simulation,
  VISUALIZER_BACKEND_DONE: backendDone,
} = process.env
assert(executablePath && directory && gates && bridge && simulation)
mkdirSync(directory, { recursive: true })
const mark = (name, value) => writeFileSync(join(directory, name + '.json'), JSON.stringify(value, null, 2))
const docker = promisify(execFile)
const browser = await chromium.launch({ executablePath, args: ['--enable-webgl', '--enable-unsafe-swiftshader'] })
const page = await browser.newPage({ viewport: { width: 1280, height: 850 } })
const errors = await recordWebGL(page)
const packets = []
page.on('websocket', socket => {
  if (!socket.url().endsWith('/telemetry/fleet')) return
  socket.on('framereceived', ({ payload }) => packets.push({
    ...JSON.parse(String(payload)), wall_ms: Date.now(), bytes: Buffer.byteLength(payload),
  }))
})
await page.addInitScript(() => {
  window.routeEvents = []
  window.poseFrames = []
  document.addEventListener('fleet-visualizer:routes', event => window.routeEvents.push(event.detail))
  document.addEventListener('fleet-visualizer:rendered', event => window.poseFrames.push(event.detail))
})
const [first, second] = ['robot_1', 'robot_2']
const gate = join(gates, first)
const state = (name, expected) => page.waitForFunction(([name, expected]) =>
  document.querySelector(`[data-testid="${name}"]`)?.textContent === expected,
[name, expected], { timeout: 45_000 })
const live = id => state('freshness-' + id, 'LIVE')
const select = id => page.getByRole('list', { name: 'Filo robotları' }).getByRole('button', { name: new RegExp(id) }).click()
const screenshot = name => page.screenshot({ path: join(directory, name + '.png'), fullPage: true })
const checkbox = name => page.getByRole('checkbox', { name, exact: true })
const planToggle = checkbox('Gözlemlenen Nav2 planı')
const trailToggle = checkbox('Gerçekleşen iz')
const onlyToggle = checkbox('Yalnız seçili robot')
const highlightToggle = checkbox('Seçili rotayı vurgula')
const latest = (id, field) => page.evaluate(([id, field]) =>
  window.routeEvents.findLast(event => event.robot_id === id && event[field] !== undefined), [id, field])
const geometry = (id, field, minimum, after = 0) => page.waitForFunction(({ id, field, minimum, after }) =>
  window.routeEvents.slice(after).some(event => event.robot_id === id && event[field]?.length >= minimum),
{ id, field, minimum, after }, { timeout: 180_000 })
const index = () => page.evaluate(() => window.routeEvents.length)

async function measure(name) {
  const start = Date.now()
  const finish = await performanceProbe(browser, page)
  await page.waitForTimeout(4500)
  const perf = await finish()
  const elapsed = (Date.now() - start) / 1000
  const rates = {}
  for (const id of [first, second]) {
    const current = packets.filter(p => p.robot_id === id && p.wall_ms >= start)
    const plans = current.filter(p => p.type === 'robot_path')
    rates[id] = { poses_hz: current.filter(p => p.type === 'robot_pose').length / elapsed,
      plans_hz: plans.length / elapsed, plan_max_bytes: Math.max(0, ...plans.map(p => p.bytes)),
      trail_points: (await latest(id, 'trail'))?.trail.length ?? 0 }
  }
  mark(name, { ...perf, rates })
}

try {
  await page.goto('http://127.0.0.1:5174/?trace')
  await live(first)
  await live(second)
  await page.getByRole('button', { name: 'Filoyu kadraja al' }).click()
  const initial = await settledFrame(page, 'fit')
  assert(initial.robots.every(robot => robot.visible && robot.screen.every(value => value > 0 && value < 1)))
  mark('ready', initial)

  await geometry(first, 'plan_vertices', 2)
  await state('plan-status', 'LIVE')
  await screenshot('robot-1-observed-plan')
  await geometry(first, 'trail_vertices', 6)
  await state('plan-status', 'STALE')
  await select(second)
  await geometry(second, 'plan_vertices', 2)
  await geometry(second, 'trail_vertices', 6)
  await state('plan-status', 'LIVE')
  await screenshot('two-live-trails-observed-plan')
  await measure('layers-on')
  await planToggle.uncheck()
  await trailToggle.uncheck()
  assert((await page.getByTestId('trail-summary').textContent()).endsWith('Gizli'))
  await measure('layers-off')
  await planToggle.check()
  await trailToggle.check()
  await onlyToggle.check()
  await page.waitForFunction(id => window.sceneFrames.at(-1)?.robots.filter(robot => robot.visible)
    .map(robot => robot.robot_id).join() === id, second)
  await highlightToggle.uncheck()
  await onlyToggle.uncheck()
  await select(first)

  const before = await index()
  writeFileSync(gate, '')
  await state('freshness-' + first, 'STALE')
  await live(second)
  const frozen = (await latest(first, 'trail')).trail
  await geometry(second, 'trail_vertices', 6, before)
  assert.deepEqual((await latest(first, 'trail')).trail, frozen)
  await screenshot('robot-1-stale-robot-2-trail')
  const resumedAt = await index()
  rmSync(gate)
  await live(first)
  await page.waitForFunction(({ robot, at }) => window.routeEvents.slice(at).some(event =>
    event.robot_id === robot && event.trail?.at(-1)?.start === true), { robot: first, at: resumedAt })
  mark('isolated-cut', { frozen: frozen.at(-1), resumed: (await latest(first, 'trail')).trail,
    second: (await latest(second, 'trail')).trail })

  await docker('docker', ['stop', bridge])
  await state('connection', 'DISCONNECTED')
  await state('freshness-' + first, 'STALE')
  await state('freshness-' + second, 'STALE')
  const { stdout: nodes } = await docker('docker', ['exec', simulation, 'bash', '-c',
    'source /opt/ros/humble/setup.bash; ros2 node list --no-daemon'])
  for (const id of [first, second]) assert(nodes.includes(`/${id}/planner_server`) && nodes.includes(`/${id}/bt_navigator`))
  assert(!nodes.includes('/fleet_visualizer') && nodes.includes('/c44_fleet_manager'))
  for (const id of [first, second]) assert(nodes.includes(`/${id}/battery_simulator`))
  mark('bridge-off', { at: new Date().toISOString(), nodes })
  await docker('docker', ['start', bridge])
  await live(first)
  await live(second)
  mark('bridge-on', { at: new Date().toISOString() })
  if (backendDone) {
    for (let i = 0; i < 600 && !existsSync(backendDone); i++) await page.waitForTimeout(250)
    assert(existsSync(backendDone), 'C4.5 backend did not finish')
    assert.equal(readFileSync(backendDone, 'utf8').trim(), '0')
  }

  const events = await page.evaluate(() => window.routeEvents)
  const key = (sample, stamp = sample.stamp_ns) => [sample.stream_id, sample.epoch, stamp].join('/')
  const poses = new Map(packets.filter(p => p.type === 'robot_pose').map(p => [key(p), p]))
  const paths = packets.filter(p => p.type === 'robot_path')
  const totals = {}
  for (const id of [first, second]) {
    const stats = { plans: 0, trailSegments: 0, maxGroundError: 0, clearPackets: 0 }
    const compare = (vertex, x, y) => {
      stats.maxGroundError = Math.max(stats.maxGroundError, Math.hypot(vertex[0] - x, vertex[2] + y))
    }
    for (const event of events.filter(event => event.robot_id === id)) {
      if (event.plan_vertices?.length) {
        const path = paths.find(p => p.robot_id === id && p.stamp_ns === event.plan)
        assert.equal(path?.source_topic, `/${id}/plan`)
        assert.equal(path.points.length, event.plan_vertices.length)
        event.plan_vertices.forEach((vertex, i) => compare(vertex, ...path.points[i]))
        stats.plans++
      }
      if (!event.trail) continue
      let vertex = 0
      for (let i = 1; i < event.trail.length; i++) {
        if (event.trail[i].start) continue
        for (const sample of event.trail.slice(i - 1, i + 1)) {
          const pose = poses.get(key(sample))
          assert.equal(pose?.robot_id, id)
          compare(event.trail_vertices[vertex++], pose.x, pose.y)
        }
        stats.trailSegments++
      }
      assert.equal(vertex, event.trail_vertices.length)
    }
    stats.clearPackets = packets.filter(p => p.robot_id === id && p.type === 'robot_path_clear').length
    assert(stats.plans >= 2 && stats.trailSegments > 0 && stats.clearPackets > 0)
    closeTo(stats.maxGroundError, 0, 1e-6)
    totals[id] = stats
  }
  assert.deepEqual(errors, [])
  mark('routes-result', { chrome: browser.version(), totals, errors })
} finally {
  rmSync(gate, { force: true })
  const capture = await page.evaluate(() => ({ events: window.routeEvents, poses: window.poseFrames }))
  mark('route-events', capture.events)
  mark('frames', capture.poses)
  mark('packets', packets)
  await browser.close()
}
