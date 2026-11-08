import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { PerspectiveCamera, Vector3 } from 'three'
import { chromium } from '@playwright/test'

const [before, after, input, output, earlier, livePath, inspectionPath] = process.argv.slice(2)
assert.ok(output, 'Usage: warehouse-grid-acceptance.mjs <before URL> <after URL> <fixture JSON> <evidence dir> [earlier fixture JSON] [live.json] [inspection.json]')
const read = file => JSON.parse(readFileSync(file, 'utf8'))
const scenarios = read(input)
const earlierData = earlier ? read(earlier).original : scenarios.original
const live = livePath ? read(livePath) : undefined
const inspection = inspectionPath ? read(inspectionPath) : undefined
mkdirSync(output, { recursive: true })
const chrome = await chromium.launch({ channel: 'chrome', headless: true })
const evidence = { chrome: chrome.version() }

async function capture(url, data, grid, screenshots, { modern = false, recorded, routeOverride, topBefore = false } = {}) {
  const page = await chrome.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const { fleet, layout } = structuredClone(data)
  if (recorded) {
    for (const robot of fleet.robots) {
      const [, x, y, yaw] = recorded.final_pose[robot.robot_id]
      robot.pose = { x, y, yaw, frame_id: 'map' }
      robot.charging = 'NOT_CHARGING'
      robot.state = 'IDLE'
      robot.charging_station_id = null
    }
    for (const station of fleet.stations) {
      if (station.station_type === 'CHARGING') {
        station.charging = 'NOT_CHARGING'
        station.charging_robot_id = null
      }
    }
  }
  const { pickup, dropoff, assigned_robot_id: carrier } = fleet.tasks[0]
  const cross = layout.layout.aisles.find(aisle => aisle.axis === 'y').bounds
  const crossX = (cross.x_min + cross.x_max) / 2
  const waypoints = routeOverride ?? recorded?.paths[carrier] ?? [[pickup.x, pickup.y], [crossX, pickup.y], [crossX, dropoff.y], [dropoff.x, dropoff.y]]
  let stamp = 1_000_000_000
  let publishPath
  let timer, updates
  await page.addInitScript(() => {
    window.addEventListener('fleet-visualizer:frame', event => {
      window.warehouseFrame = event.detail
      if (window.recording) window.recording.push(event.detail.at)
    })
    window.addEventListener('fleet-visualizer:decor-bounds', event => { window.decor = event.detail.boxes })
    window.addEventListener('fleet-visualizer:warehouse-bounds', event => { window.corners = event.detail })
    window.addEventListener('fleet-visualizer:routes', event => {
      (window.warehouseRoutes ??= {})[event.detail.robot_id] = event.detail
    })
  })
  await page.route('**/api/warehouse-layout', route => route.fulfill({ json: layout }))
  await page.routeWebSocket('**/ws/fleet', socket => {
    const send = packet => socket.send(JSON.stringify({ type: 'scene', packet }))
    const identity = id => ({ version: 1, stream_id: fleet.source_session_id, robot_id: id, epoch: 0,
      frame_id: 'map', source: 'tf' })
    let sequence = fleet.sequence
    const product = () => socket.send(JSON.stringify({ ...fleet, sequence: ++sequence }))
    product()
    clearInterval(updates)
    updates = setInterval(product, 500)
    socket.send('{"type":"scene_connected"}')
    send({ type: 'fleet_hello', version: 1, robot_ids: fleet.robots.map(robot => robot.robot_id) })
    const samples = []
    for (const { robot_id: id, pose } of fleet.robots) {
      send({ ...identity(id), type: 'hello', after_stamp_ns: '0', stale_after_ms: 10000, path_topic: `/${id}/plan` })
      const sample = (x, y, yaw = pose.yaw) => send({ ...identity(id), type: 'robot_pose', x, y, yaw, stamp_ns: String(stamp += 100_000_000) })
      if (recorded) {
        for (const [, x, y, yaw] of recorded.traces[id].slice(-40)) sample(x, y, yaw)
      } else if (id === carrier) {
        for (let i = 5; i >= 1; i--) sample(pose.x - i * .16, pose.y)
      }
      sample(pose.x, pose.y)
      samples.push(() => sample(pose.x, pose.y))
    }
    publishPath = points => send({ ...identity(carrier), type: 'robot_path',
      stamp_ns: String(stamp += 100_000_000), source_topic: `/${carrier}/plan`, plan_source: 'nav2_observed_plan',
      ttl_ms: 2000, points })
    publishPath(waypoints)
    clearInterval(timer)
    timer = setInterval(() => samples.forEach(sample => sample()), 100)
  })

  try {
    await page.goto(url + '/?trace=1')
    await page.waitForFunction(expected => window.warehouseFrame?.warehouse === expected &&
      window.warehouseFrame.robots.filter(robot => robot.visible && robot.status === 'LIVE').length === 2,
    grid ? 'grid' : 'glb')
    const snapshot = () => page.evaluate(() => window.warehouseFrame)
    const frame = await snapshot()
    const position = p => [p.x, 0, -p.y].map(n => n || 0)
    for (const record of fleet.robots) {
      const robot = frame.robots.find(robot => robot.robot_id === record.robot_id)
      assert.deepEqual(robot.pose, position(record.pose))
      assert.equal(robot.yaw, record.pose.yaw)
    }
    for (const station of fleet.stations) {
      const point = frame.points.find(point => point.key === 'station:' + station.station_id)
      assert.deepEqual(point.position, position(station.pose))
      assert.equal(point.yaw, station.pose.yaw)
    }
    for (const [kind, pose] of [['pickup', pickup], ['dropoff', dropoff]]) {
      assert.deepEqual(frame.points.find(point => point.key === kind + ':delivery-01').position, position(pose))
    }
    await page.waitForFunction(([id, count]) => window.warehouseRoutes?.[id]?.plan_vertices?.length === count, [carrier, waypoints.length])
    const route = await page.evaluate(id => window.warehouseRoutes[id], carrier)
    const pathErrorM = Math.max(...route.plan_vertices.map(([x, , z], i) =>
      Math.hypot(x-waypoints[i][0], z+waypoints[i][1])))
    assert.ok(pathErrorM < 1e-6, 'Path vertices differ beyond WebGL float precision')
    assert.ok(route.trail_vertices.length >= 2)
    if (grid) {
      assert.equal(frame.points.filter(point => point.layoutBay).length, layout.layout.transfer_points.length - 2)
      assert.deepEqual(frame.routeHiddenRacks, [])
      const [dock] = fleet.stations
      const marker = frame.points.find(point => point.key === 'station:' + dock.station_id)
      assert.ok(Math.abs(marker.dockBounds.min[2] + layout.layout.bounds.y_max - layout.layout.wall_thickness_m / 2) < 1e-6)
      if (modern) {
        await page.locator('[data-operation-point="zone:charge_zone"]').waitFor({ timeout: 7000 })
        await page.locator('[data-operation-point="zone:park_zone"]').waitFor({ timeout: 7000 })
        assert.equal(await page.locator('[data-operation-point^="station:dock_"]').count(), 0)
        const bounds = await page.evaluate(() => window.decor)
        for (const item of [...layout.layout.walls, ...layout.layout.racks]) {
          const box = bounds.find(box => box.name === item.id)
          const actual = [box.min[0], box.max[0], -box.max[2], -box.min[2]]
          const expected = ['x_min','x_max','y_min','y_max'].map(key => item.bounds[key])
          assert.ok(actual.every((value, i) => Math.abs(value-expected[i])<1e-5), item.id)
        }
      }
      const overlapping = await page.locator('.scene-label:visible, .scene-point-label:visible').evaluateAll(elements => {
        const rects = elements.map(element => element.getBoundingClientRect())
        return rects.some((a, index) => rects.slice(index + 1).some(b =>
          a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top))
      })
      assert.equal(overlapping, false)
    }
    const checkFrame = async () => {
      const { width, height } = await page.locator('canvas').boundingBox()
      const { camera, target } = await snapshot()
      const corners = await page.evaluate(() => window.corners)
      const lens = new PerspectiveCamera(42, width / height, .035, 90)
      lens.position.fromArray(camera)
      lens.lookAt(new Vector3(...target))
      lens.updateMatrixWorld()
      assert.ok(corners.every(point => {
        const { x, y, z } = new Vector3(...point).project(lens)
        return Math.max(Math.abs(x), Math.abs(y), Math.abs(z)) < 1
      }), 'Warehouse geometry clipped')
    }
    await checkFrame()
    assert.equal(await page.evaluate(() => document.documentElement.scrollHeight), 900)
    let performance
    if (screenshots === 'before' || screenshots === 'after') {
      const { width, height } = await page.locator('canvas').boundingBox()
      assert.ok(width > 0 && height > 0)
      await page.evaluate(() => { window.recording = [] })
      await page.waitForTimeout(3000)
      const samples = await page.evaluate(() => {
        const samples = window.recording
        window.recording = null
        return samples
      })
      const intervals = samples.slice(1).map((time, i) => time-samples[i]).sort((a,b) => a-b)
      performance = { frames: samples.length, fps: (samples.length-1)*1000/(samples.at(-1)-samples[0]),
        p95Ms: intervals[Math.floor(intervals.length*.95)], calls: frame.calls, geometries: frame.geometries,
        textures: frame.textures }
      publishPath(waypoints)
    }
    if (screenshots) await page.screenshot({ path: join(output, screenshots + '.png') })

    if (topBefore) {
      await page.getByRole('button', { name: 'Üstten', exact: true }).click()
      await page.waitForFunction(() => window.warehouseFrame.mode === 'top' && !window.warehouseFrame.transitioning)
      publishPath(waypoints)
      await page.screenshot({ path: join(output, 'before-top.png') })
    }
    if (grid && screenshots === 'after') {
      await page.getByRole('button', { name: 'Üstten', exact: true }).click()
      await page.waitForFunction(() => window.warehouseFrame.mode === 'top' && !window.warehouseFrame.transitioning)
      publishPath(waypoints)
      await page.waitForFunction(([id, count]) => window.warehouseRoutes?.[id]?.plan_vertices?.length === count, [carrier, waypoints.length])
      await checkFrame()
      const callouts = layout.layout.zones.filter(zone => zone.callout)
      if (callouts.length) {
        const { camera, target } = await snapshot()
        const canvas = await page.locator('canvas').boundingBox()
        const lens = new PerspectiveCamera(42, canvas.width / canvas.height, .035, 90)
        lens.position.fromArray(camera)
        lens.lookAt(new Vector3(...target))
        lens.updateMatrixWorld()
        const projected = (bounds, height) => {
          const points = []
          for (const x of [bounds.x_min, bounds.x_max]) for (const y of [bounds.y_min, bounds.y_max]) {
            for (const h of [0, height]) points.push(new Vector3(x, h, -y).project(lens))
          }
          const xs = points.map(point => canvas.x + (point.x + 1) * canvas.width / 2)
          const ys = points.map(point => canvas.y + (1 - point.y) * canvas.height / 2)
          return { left: Math.min(...xs), right: Math.max(...xs), top: Math.min(...ys), bottom: Math.max(...ys) }
        }
        const blocked = [...layout.layout.racks.map(rack => projected(rack.bounds, rack.height)),
          ...layout.layout.zones.map(zone => projected(zone.bounds, 0))]
        for (const zone of callouts) {
          const label = page.locator(`[data-operation-point="zone:${zone.id}"]`)
          await label.waitFor({ timeout: 7000 })
          const rect = await label.evaluate(node => node.getBoundingClientRect().toJSON())
          assert.equal(await label.getAttribute('data-detailed'), null)
          assert.ok(blocked.every(b => rect.right <= b.left || rect.left >= b.right ||
            rect.bottom <= b.top || rect.top >= b.bottom), zone.id)
          const line = page.locator(`[data-leader="zone:${zone.id}"]`)
          assert.equal(await line.evaluate(node => getComputedStyle(node).visibility), 'visible')
        }
      }
      await page.screenshot({ path: join(output, 'after-top.png') })
      const cameraBefore = (await snapshot()).camera
      const canvas = await page.locator('canvas').boundingBox()
      if (callouts.length) {
        const park = await page.locator('[data-operation-point="zone:park_zone"]').boundingBox()
        await page.mouse.move(park.x + park.width/2, park.y + park.height/2)
        await page.mouse.down({ button: 'right' })
        await page.mouse.move(canvas.x + canvas.width/2, canvas.y + canvas.height/2, { steps: 10 })
        await page.mouse.up({ button: 'right' })
      }
      await page.mouse.move(canvas.x + canvas.width/2, canvas.y + canvas.height/2)
      await page.mouse.wheel(0, callouts.length ? -720 : -250)
      await page.waitForFunction(before => window.warehouseFrame.camera.some((value, i) => value !== before[i]), cameraBefore)
      if (layout.layout.zones.some(zone => zone.callout)) {
        const label = page.locator('[data-operation-point="zone:park_zone"][data-detailed]:visible')
        await label.waitFor({ timeout: 5000 })
        await page.screenshot({ path: join(output, 'after-zoom.png') })
      }
      const normal = (await snapshot()).calls
      await page.getByLabel('Düşük kalite').check()
      await page.waitForFunction(calls => window.warehouseFrame.calls < calls, normal)
      await page.getByLabel('Düşük kalite').uncheck()

      const rack = layout.layout.racks[0]
      const y = (rack.bounds.y_min + rack.bounds.y_max) / 2
      const conflict = [[rack.bounds.x_min - 1, y], [rack.bounds.x_max + 1, y]]
      publishPath(conflict)
      await page.waitForFunction(id => window.warehouseFrame.routeHiddenRacks.includes(id), rack.id)
      const conflicting = await page.evaluate(id => window.warehouseRoutes[id].plan_vertices, carrier)
      assert.deepEqual(conflicting.map(([x, , z]) => [x, -z]), conflict)
      await page.getByRole('button', { name: 'Kamerayı sıfırla', exact: true }).click()
      await page.waitForFunction(() => window.warehouseFrame.mode === 'free' && !window.warehouseFrame.transitioning)
      const previous = (await snapshot()).camera
      await page.mouse.move(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2)
      await page.mouse.down()
      await page.mouse.move(canvas.x + canvas.width * .6, canvas.y + canvas.height * .5, { steps: 8 })
      await page.mouse.up()
      await page.waitForFunction(before => window.warehouseFrame.camera.some((value, i) => value !== before[i]), previous)
      await page.setViewportSize({ width: 390, height: 844 })
      const resetBefore = (await snapshot()).reset
      await page.getByRole('button', { name: 'Kamerayı sıfırla', exact: true }).click()
      await page.waitForFunction(reset => window.warehouseFrame.reset > reset && !window.warehouseFrame.transitioning, resetBefore)
      await checkFrame()
      await page.screenshot({ path: join(output, 'after-mobile.png') })
      await page.getByRole('link', { name: 'Görevler', exact: true }).click()
      await page.getByRole('table').getByText('delivery-01', { exact: true }).waitFor()
    }
    assert.deepEqual(errors, [])
    return { warehouse: frame.warehouse, robots: frame.robots, points: frame.points, route: waypoints, pathErrorM, calls: frame.calls, performance }
  } catch (error) {
    if (screenshots) {
      await page.screenshot({ path: join(output, screenshots + '-debug.png') })
      const debug = await page.evaluate(() => ({
        frame: window.warehouseFrame, canvas: document.querySelector('canvas').getBoundingClientRect().toJSON(),
        labels: [...document.querySelectorAll('[data-callout]')].map(node => ({
          key: node.dataset.operationPoint, width: node.offsetWidth, height: node.offsetHeight,
          rect: node.getBoundingClientRect().toJSON(),
        })),
      }))
      writeFileSync(join(output, screenshots + '-debug.json'), JSON.stringify(debug))
    }
    throw error
  } finally {
    clearInterval(timer)
    clearInterval(updates)
    await page.close()
  }
}

try {
  evidence.before = await capture(before, earlierData, !!earlier, 'before', { topBefore: !!inspection })
  evidence.after = await capture(after, scenarios.original, true, 'after', { modern: true, routeOverride: inspection?.nav2.path })
  evidence.moved = await capture(after, scenarios.moved, true, undefined, { modern: true })
  if (live) evidence.recorded = await capture(after, scenarios.original, true, 'after-recorded',
    { modern: true, recorded: live })
  const dock = section => section.points.find(point => point.key === 'station:dock_1')
  assert.notEqual(dock(evidence.after).position[0], dock(evidence.moved).position[0])
  assert.equal(dock(evidence.moved).position[0], scenarios.moved.fleet.stations[0].pose.x)
  writeFileSync(join(output, 'chrome-evidence.json'), JSON.stringify(evidence, null, 2) + '\n')
  console.log('Chrome warehouse grid acceptance passed')
} finally {
  await chrome.close()
}
