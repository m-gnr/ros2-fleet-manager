import { writeFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'
import { PerspectiveCamera, Vector3 } from 'three'
import { fixture, valid } from './dashboard-fixtures'
import { staticWarehouse } from '../src/scene/warehouseProfile.generated'
import { exteriorSite } from '../src/scene/exteriorSite'
import { exteriorMotionPose } from '../src/scene/exteriorMotion'
import { robotStateColors, robotVisualState } from '../src/scene/robotPresentation'
import { trailFade, trailFadeMs } from '../src/scene/routes'
import { burgerSize, robotVisualScale } from '../src/scene/Burger'

const layout = staticWarehouse.layout
const bay = (id: string) => layout.transfer_points.find(point => point.id === id)!
const mapPose = (id: string) => ({ ...bay(id).pose, frame_id: 'map' })

test('three live robots and task roles survive camera and label changes', async ({ page }, testInfo) => {
  test.setTimeout(60_000)
  await page.addInitScript(() => window.addEventListener('fleet-visualizer:frame', event => {
    Reflect.set(window, 'scene_frame', (event as CustomEvent).detail)
    const frames = Reflect.get(window, 'scene_samples')
    if (frames) frames.push((event as CustomEvent).detail)
  }))
  await page.route('**/api/warehouse-layout', route => route.fulfill({ json: { layout: null } }))
  const ids = ['robot_alpha', 'robot_beta', 'robot_gamma']
  const states = ['IDLE', 'EXECUTING_TASK', 'CHARGING'] as const
  const yaws = [0, Math.PI / 2, -Math.PI / 2]
  const robots = ids.map((robot_id, index) => ({ ...valid, robot_id, state: states[index],
    charging: 'NOT_CHARGING' as const, charging_station_id: null, active_task_id: index === 1 ? 'visual-task' : null,
    pose: { x: -2 + index * 2, y: 1, yaw: 0, frame_id: 'map' } }))
  const stations = [
    ...[1.5, 2.75, 4].map((y, index) => ({ ...fixture.stations[0], station_id: `park_${index + 1}`,
      station_type: 'PARKING' as const, pose: { x: 13.5, y, yaw: Math.PI, frame_id: 'map' },
      state: 'RESERVED' as const, charging: 'NOT_APPLICABLE' as const,
      reserved_by_robot_id: ['robot_beta', 'robot_gamma', 'robot_alpha'][index],
      occupied_by_robot_id: null, charging_robot_id: null })),
    ...[7, 8.25, 9.5, 10.75, 12, 13.25].map((x, index) => ({ ...fixture.stations[0], station_id: `dock_${index + 1}`,
      pose: { x, y: 8.25, yaw: Math.PI / 2, frame_id: 'map' }, state: 'FREE' as const,
      charging: 'NOT_CHARGING' as const, reserved_by_robot_id: null, occupied_by_robot_id: null,
      charging_robot_id: null })),
  ]
  const snapshot = { ...fixture, robots, tasks: [{ ...fixture.tasks[0], task_id: 'visual-task',
    status: 'EXECUTING', pickup: mapPose('pick_E1'), dropoff: mapPose('packing_1'),
    assigned_robot_id: 'robot_beta' }], stations }
  await page.routeWebSocket('**/ws/fleet', socket => {
    socket.send(JSON.stringify(snapshot))
    socket.send(JSON.stringify({ type: 'scene_connected' }))
    const send = (packet: object) => socket.send(JSON.stringify({ type: 'scene', packet }))
    send({ type: 'fleet_hello', version: 1, robot_ids: ids })
    let stamp = 1_000_000_000
    let sequence = snapshot.sequence
    const sendPoses = () => ids.forEach((robot_id, index) => {
      const base = { robot_id, frame_id: 'map', source: 'tf', version: 1, epoch: 0,
        stream_id: `c98d630d-85a8-4173-955d-430ac96d604${index}` }
      if (stamp === 1_000_000_000) send({ ...base, type: 'hello', after_stamp_ns: '0', stale_after_ms: 2000,
        path_topic: `/${robot_id}/plan` })
      send({ ...base, type: 'robot_pose', stamp_ns: String(stamp), x: -2 + index * 2, y: 1, yaw: yaws[index] })
    })
    sendPoses()
    const timer = setInterval(() => {
      stamp += 100_000_000
      sendPoses()
      socket.send(JSON.stringify({ ...snapshot, sequence: ++sequence }))
    }, 250)
    socket.onClose(() => clearInterval(timer))
  })
  await page.goto('/?trace=1')
  await expect(page.locator('.scene-point-label')).toHaveCount(0)
  await expect(page.locator('.scene-point-tooltip')).toHaveCount(0)
  await expect(page.locator('.scene-indicator')).toContainText('3 / 3 TF LIVE')
  await expect.poll(() => page.evaluate(() => Reflect.get(window, 'scene_frame')?.surface)).toEqual({
    floorGridSegments: 50,
    rackContactShadows: layout.racks.length,
    shadowMapEnabled: false,
  })
  for (const [id, state, color] of [
    ['robot_alpha', 'idle', 'rgb(100, 116, 139)'],
    ['robot_beta', 'active', 'rgb(101, 84, 181)'],
    ['robot_gamma', 'charging', 'rgb(68, 132, 107)'],
  ] as const) {
    const marker = page.locator(`button.scene-marker[data-robot-id="${id}"]`)
    await expect(marker).toHaveAttribute('data-robot-state', state)
    await expect(marker).toHaveCSS('color', color)
    await expect(marker).toHaveCSS('width', '34px')
    await expect(marker).toHaveCSS('height', '34px')
  }
  await expect.poll(() => page.evaluate(() => Reflect.get(window, 'scene_frame')?.robots
    .map((robot: { yaw: number }) => Number(robot.yaw.toFixed(4))))).toEqual(yaws.map(yaw => Number(yaw.toFixed(4))))
  const robotOverlaps = () => page.evaluate(() => {
    const elements = [...document.querySelectorAll<HTMLElement>('.scene-marker, .scene-label')]
      .filter(element => getComputedStyle(element).visibility === 'visible')
      .map(element => ({ id: `${element.className}:${element.dataset.robotId}`, rect: element.getBoundingClientRect() }))
    const overlaps: string[] = []
    for (let i = 0; i < elements.length; i++) for (let j = i + 1; j < elements.length; j++) {
      const a = elements[i].rect
      const b = elements[j].rect
      if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) {
        overlaps.push(`${elements[i].id}/${elements[j].id}`)
      }
    }
    return overlaps
  })
  await expect.poll(robotOverlaps).toEqual([])
  await page.locator('button.scene-marker[data-robot-id="robot_beta"]').click()
  await expect(page.locator('button.scene-marker[data-robot-id="robot_beta"]')).toHaveAttribute('aria-pressed', 'true')
  await expect.poll(() => page.evaluate(() => Reflect.get(window, 'scene_frame')?.points
    .find((point: { id: string }) => point.id === 'visual-task')?.kind)).toBe('pickup')
  const points = await page.evaluate(() => Reflect.get(window, 'scene_frame').points)
  expect(points.filter((point: { kind: string }) => point.kind === 'PARKING')
    .map((point: { owner: string }) => point.owner)).toEqual(['robot_beta', 'robot_gamma', 'robot_alpha'])
  await expect(page.locator('.scene-park-label')).toHaveCount(3)
  for (const [station, robot] of [['park_1', 'robot_beta'], ['park_2', 'robot_gamma'],
    ['park_3', 'robot_alpha']]) {
    await expect(page.locator(`.scene-park-label[data-park-id="${station}"]`)).toHaveText(robot)
  }
  const taskPads = points.filter((point: { id: string }) => point.id === 'visual-task')
  expect(taskPads.map((point: { kind: string; padSize: number[]; footprintSize: number[] }) =>
    [point.kind, ...[point.padSize[0], point.padSize[2], point.footprintSize[0], point.footprintSize[2]]
      .map(value => Number(value.toFixed(2)))]))
    .toEqual([['pickup', .92, .92, 1.24, 1.24], ['dropoff', .92, .92, 1.24, 1.24]])
  expect(points.filter((point: { id: string }) => point.id === 'pick_E1')).toHaveLength(0)
  expect(points.find((point: { id: string }) => point.id === 'pick_E2')?.kind).toBe('neutral')
  expect(points.find((point: { id: string }) => point.id === 'inbound_1')?.kind).toBe('pickup')
  expect(points.find((point: { id: string }) => point.id === 'packing_2')?.kind).toBe('dropoff')
  const environmentToggle = page.getByRole('checkbox', { name: 'Çevreyi göster' })
  const frame = () => page.evaluate(() => Reflect.get(window, 'scene_frame'))
  const toggleWithoutCameraChange = async () => {
    await expect.poll(async () => (await frame()).transitioning).toBe(false)
    const before = await frame()
    await environmentToggle.uncheck()
    await expect.poll(async () => (await frame()).exterior).toEqual({
      visible: false, shippingOpening: true, cameraBoundsExcludeExterior: true,
    })
    const after = await frame()
    after.camera.forEach((value: number, index: number) => expect(value).toBeCloseTo(before.camera[index], 10))
    after.target.forEach((value: number, index: number) => expect(value).toBeCloseTo(before.target[index], 10))
    expect(after.mode).toBe(before.mode)
    expect(after.points).toEqual(before.points)
    await environmentToggle.check()
    await expect.poll(async () => (await frame()).exterior.visible).toBe(true);
    (await frame()).camera.forEach((value: number, index: number) => expect(value).toBeCloseTo(before.camera[index], 10))
  }
  await toggleWithoutCameraChange()
  const measure = async (visible: boolean) => {
    await environmentToggle.setChecked(visible)
    await expect.poll(async () => (await frame()).exterior.visible).toBe(visible)
    await page.evaluate(() => Reflect.set(window, 'scene_samples', []))
    await page.evaluate(() => new Promise<void>(resolve => {
      const start = performance.now()
      const next = () => {
        document.querySelector('canvas')!.dispatchEvent(new Event('fleet-visualizer:benchmark-frame'))
        if (performance.now() - start < 2500) requestAnimationFrame(next)
        else resolve()
      }
      requestAnimationFrame(next)
    }))
    return page.evaluate(() => {
      const samples = Reflect.get(window, 'scene_samples')
      Reflect.deleteProperty(window, 'scene_samples')
      const middle = samples[Math.floor(samples.length / 2)]
      const duration = samples.at(-1).at - samples[0].at
      return { traceFrames: samples.length, windowMs: duration,
        renderedFps: (samples.length - 1) * 1000 / duration,
        calls: middle.calls, triangles: middle.triangles, geometries: middle.geometries }
    })
  }
  const renderCost = { hidden: await measure(false), visible: await measure(true) }
  await writeFile(testInfo.outputPath('exterior-render-cost.json'), JSON.stringify(renderCost, null, 2))
  expect(renderCost.visible.calls - renderCost.hidden.calls).toBeLessThan(20)
  expect(renderCost.visible.triangles - renderCost.hidden.triangles).toBeLessThan(12000)
  const running = (await frame()).exteriorMotion
  await expect.poll(async () => (await frame()).exteriorMotion.ticks).toBeGreaterThan(running.ticks)
  expect((await frame()).exteriorMotion.roadVehicles).toBeLessThanOrEqual(1)
  await environmentToggle.uncheck()
  await expect.poll(async () => (await frame()).exteriorMotion.running).toBe(false)
  const paused = (await frame()).exteriorMotion
  await page.waitForTimeout(300)
  expect((await frame()).exteriorMotion).toEqual(paused)
  await environmentToggle.check()
  await expect.poll(async () => (await frame()).exteriorMotion.running).toBe(true)
  // Exercise the browser's visibility handler while TF rendering continues independently.
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, get: () => true })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await expect.poll(async () => (await frame()).exteriorMotion.running).toBe(false)
  const background = (await frame()).exteriorMotion
  await page.waitForTimeout(300)
  expect((await frame()).exteriorMotion).toEqual(background)
  await page.evaluate(() => {
    Reflect.deleteProperty(document, 'hidden')
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await expect.poll(async () => (await frame()).exteriorMotion.running).toBe(true)
  await expect.poll(async () => (await frame()).exteriorMotion.ticks).toBeGreaterThan(background.ticks)
  expect((await frame()).exteriorMotion.elapsed - background.elapsed).toBeLessThan(.5)
  const viewport = page.locator('.scene-viewport')
  await viewport.screenshot({ path: testInfo.outputPath('overview.png') })
  await page.getByRole('button', { name: 'Üstten' }).click()
  await expect.poll(() => page.evaluate(() => Reflect.get(window, 'scene_frame')?.mode)).toBe('top')
  await expect.poll(() => page.evaluate(() => Reflect.get(window, 'scene_frame')?.transitioning)).toBe(false)
  await toggleWithoutCameraChange()
  await environmentToggle.uncheck()
  await expect.poll(async () => (await frame()).exterior.visible).toBe(false)
  await viewport.screenshot({ path: testInfo.outputPath('top-environment-off.png') })
  await environmentToggle.check()
  await viewport.screenshot({ path: testInfo.outputPath('top.png') })
  for (const id of ids) {
    await expect(page.locator(`button.scene-marker[data-robot-id="${id}"]`)).toHaveCSS('width', '34px')
  }
  await expect.poll(robotOverlaps).toEqual([])
  const hoverPoint = async (id: string) => {
    const frame = await page.evaluate(() => Reflect.get(window, 'scene_frame'))
    const point = frame.points.find((item: { id: string }) => item.id === id)
    const canvas = (await page.locator('canvas').boundingBox())!
    const camera = new PerspectiveCamera(42, canvas.width / canvas.height, .035, 240)
    camera.position.fromArray(frame.camera)
    camera.lookAt(new Vector3(...frame.target))
    camera.updateMatrixWorld()
    const screen = new Vector3(...point.position).project(camera)
    await page.mouse.move(canvas.x + (screen.x + 1) / 2 * canvas.width,
      canvas.y + (1 - screen.y) / 2 * canvas.height)
  }
  await hoverPoint('visual-task')
  await expect(page.locator('.scene-point-tooltip:visible')).toContainText('pick_E1')
  await expect(page.locator('.scene-point-tooltip:visible')).toContainText('Durum: Yürütülüyor')
  await page.mouse.move(20, 20)
  await expect(page.locator('.scene-point-tooltip')).toHaveCount(0)
  await hoverPoint('inbound_1')
  await expect(page.locator('.scene-point-tooltip:visible')).toContainText('inbound_1')
  await expect(page.locator('.scene-point-tooltip:visible')).toContainText('Alma')
  await viewport.screenshot({ path: testInfo.outputPath('pickup-hover.png') })
  await page.mouse.down()
  await page.mouse.up()
  await page.mouse.move(20, 20)
  await expect(page.locator('.scene-point-tooltip:visible')).toContainText('inbound_1')
  const canvasBox = (await page.locator('canvas').boundingBox())!
  await page.mouse.click(canvasBox.x + canvasBox.width * .92, canvasBox.y + canvasBox.height * .86)
  await expect(page.locator('.scene-point-tooltip')).toHaveCount(0)
  await hoverPoint('pick_B2')
  await expect(page.locator('.scene-point-tooltip:visible')).toContainText('Çift rollü')
  await viewport.screenshot({ path: testInfo.outputPath('dual-hover.png') })
  await page.mouse.move(20, 20)
  await expect(page.locator('.scene-point-tooltip')).toHaveCount(0)
  await environmentToggle.uncheck()
  await hoverPoint('park_1')
  await expect(page.locator('.scene-point-tooltip:visible')).toContainText('park_1')
  await expect(page.locator('.scene-point-tooltip:visible')).toContainText('Durum: Rezerve')
  await page.mouse.move(20, 20)
  await expect(page.locator('.scene-point-tooltip')).toHaveCount(0)

  await environmentToggle.check()
  const grayscale = await page.addStyleTag({ content: '.scene-viewport canvas { filter: grayscale(1) }' })
  await viewport.screenshot({ path: testInfo.outputPath('top-grayscale.png') })
  await grayscale.evaluate(node => (node as HTMLElement).remove())
  await page.getByRole('button', { name: 'Kamerayı sıfırla' }).click()
  await expect.poll(() => page.evaluate(() => Reflect.get(window, 'scene_frame')?.mode)).toBe('free')
  await expect.poll(() => page.evaluate(() => Reflect.get(window, 'scene_frame')?.transitioning)).toBe(false)
  await page.locator('canvas').hover()
  await page.mouse.wheel(0, -1800)
  await page.waitForTimeout(500)
  await viewport.screenshot({ path: testInfo.outputPath('near.png') })
  for (const id of ids) {
    await expect(page.locator(`button.scene-marker[data-robot-id="${id}"]`)).toHaveCSS('width', '34px')
  }
  await expect.poll(robotOverlaps).toEqual([])
  await expect(page.locator('.scene-point-tooltip')).toHaveCount(0)
  await page.mouse.wheel(0, 1800)
  await expect(page.locator('.scene-point-label')).toHaveCount(0)
  await viewport.screenshot({ path: testInfo.outputPath('far.png') })
  for (const [mode, expectedMode] of [['Robotu takip et', 'follow'], ['Filoyu kadraja al', 'fit']]) {
    await page.getByRole('button', { name: mode, exact: true }).click()
    await expect.poll(async () => (await frame()).mode).toBe(expectedMode)
    await toggleWithoutCameraChange()
  }
  await page.getByRole('button', { name: 'Kamerayı sıfırla' }).click()
  await expect.poll(async () => (await frame()).transitioning).toBe(false)
  await expect.poll(async () => (await frame()).mode).toBe('free')
  await expect.poll(async () => (await frame()).transitioning).toBe(false)
  // Manually zoom out for the exterior inspection; default framing remains unchanged.
  await page.locator('canvas').hover()
  await page.mouse.wheel(0, 1500)
  await page.waitForTimeout(500)
  await viewport.screenshot({ path: testInfo.outputPath('exterior-wide.png') })
  await page.screenshot({ path: testInfo.outputPath('panel-controls.png'), fullPage: true })
  await page.getByRole('button', { name: 'Üstten', exact: true }).click()
  await expect.poll(async () => (await frame()).mode).toBe('top')
  await expect.poll(async () => (await frame()).transitioning).toBe(false)
  await page.locator('canvas').hover()
  await page.mouse.wheel(0, 1500)
  await page.waitForTimeout(500)
  await viewport.screenshot({ path: testInfo.outputPath('exterior-wide-top.png') })
  await expect(page.locator('.scene-indicator')).toContainText('3 / 3 TF LIVE')
})

test('robot state palette is derived only from real states', () => {
  expect(robotVisualState('IDLE')).toBe('idle')
  expect(robotVisualState('EXECUTING_TASK')).toBe('active')
  expect(robotVisualState('RETURNING_TO_CHARGE')).toBe('active')
  expect(robotVisualState('RETURNING_TO_PARK')).toBe('active')
  expect(robotVisualState('CHARGING')).toBe('charging')
  expect(robotVisualState('ERROR')).toBe('error')
  expect(robotVisualState(null)).toBe('unknown')
  expect(robotStateColors).toEqual({
    idle: '#64748B', active: '#6554B5', charging: '#44846B', error: '#C45151',
  })
  expect(trailFade(undefined, 10_000)).toBe(0)
  expect(trailFade(10_000, 10_000)).toBe(1)
  expect(trailFade(10_000, 10_000 + trailFadeMs / 2)).toBe(.5)
  expect(trailFade(10_000, 10_000 + trailFadeMs)).toBe(0)
  expect(Math.max(burgerSize.length, burgerSize.width) * robotVisualScale).toBeLessThan(.92)
})

test('decorative vehicles wait, leave and return without entering the warehouse', () => {
  const site = exteriorSite(layout)
  const b = layout.bounds
  for (const { box: [x, , z, width, , depth, color] } of site.parts) {
    expect(x + width / 2 <= b.x_min || x - width / 2 >= b.x_max ||
      z + depth / 2 <= -b.y_max || z - depth / 2 >= -b.y_min).toBe(true)
    expect(['#168DA4', '#F2AD43']).not.toContain(color.toUpperCase())
  }
  expect(site.parkedCars).toHaveLength(5 * 7)

  expect(exteriorMotionPose(0).offset).toBe(0)
  expect(exteriorMotionPose(12).offset).toBe(0)
  expect(exteriorMotionPose(22).offset).toBeCloseTo(1.4)
  expect(exteriorMotionPose(32).offset).toBe(2.8)
  expect(exteriorMotionPose(62).offset).toBeCloseTo(1.4)
  expect(exteriorMotionPose(72).offset).toBe(0)
  expect(exteriorMotionPose(80).offset).toBe(0)
  for (let t = 0; t < 160; t += .25) {
    expect(exteriorMotionPose(t).offset).toBeGreaterThanOrEqual(0)
    expect(exteriorMotionPose(t).offset).toBeLessThanOrEqual(2.8)
  }
  expect(exteriorMotionPose(15).roadPhase).toBeLessThan(16)
  expect(exteriorMotionPose(17).roadPhase).toBeGreaterThan(16)
  expect(exteriorMotionPose(56).roadPhase).toBe(0)
})
