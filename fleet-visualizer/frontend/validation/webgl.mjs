import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'

export async function recordWebGL(page) {
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => {
    if (message.type() === 'error' && !/^WebSocket connection to .* failed:/.test(message.text())) {
      errors.push(`${message.text()} (${message.location().url})`)
    }
  })
  await page.addInitScript(() => {
    window.sceneFrames = []
    document.addEventListener('fleet-visualizer:frame', event => window.sceneFrames.push(event.detail))
  })
  return errors
}

export async function settledFrame(page, mode) {
  await page.waitForFunction(mode => {
    const frame = window.sceneFrames.at(-1)
    return frame?.mode === mode && !frame.transitioning && frame.calls > 0
  }, mode)
  return page.evaluate(() => window.sceneFrames.at(-1))
}

export function closeTo(actual, expected, tolerance = 1e-7) {
  assert(Math.abs(actual - expected) < tolerance, `${actual} != ${expected} (±${tolerance})`)
}

export function assertFollow(frame) {
  assert.equal(frame.mode, 'follow')
  assert(frame.visible)
  closeTo(frame.target[0], frame.pose[0])
  closeTo(frame.target[2], frame.pose[2])
}

export async function checkLayout(page, viewport) {
  await page.setViewportSize(viewport)
  const box = await page.locator('canvas').boundingBox()
  assert(box && box.width >= 250 && box.height >= 300)
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
  const controls = await page.getByRole('group', { name: 'Kamera modu' }).boundingBox()
  assert(controls && controls.x >= box.x && controls.x + controls.width <= box.x + box.width)
  assert(await page.getByTestId('schematic').isVisible())
}

export async function performanceProbe(browser, page) {
  const browserCdp = await browser.newBrowserCDPSession()
  const pageCdp = await page.context().newCDPSession(page)
  await pageCdp.send('Performance.enable')
  const start = await browserCdp.send('SystemInfo.getProcessInfo')
  const before = await page.evaluate(() => performance.now())
  return async () => {
    const sample = await page.evaluate(before => ({
      elapsedMs: performance.now() - before,
      frames: window.sceneFrames.filter(frame => frame.at >= before),
    }), before)
    const end = await browserCdp.send('SystemInfo.getProcessInfo')
    const { metrics } = await pageCdp.send('Performance.getMetrics')
    await pageCdp.detach()
    await browserCdp.detach()
    const durations = sample.frames.slice(1).map((frame, index) => frame.at - sample.frames[index].at)
      .sort((left, right) => left - right)
    const beforeByPid = new Map(start.processInfo.map(process => [process.id, process.cpuTime]))
    const cpuTime = end.processInfo.reduce((total, process) =>
      total + process.cpuTime - (beforeByPid.get(process.id) ?? 0), 0)
    let rssMiB
    try {
      const pids = end.processInfo.map(process => process.id).join(',')
      const rows = execFileSync('ps', ['-o', 'rss=', '-p', pids], { encoding: 'utf8' })
      rssMiB = rows.trim().split(/\s+/).reduce((sum, row) => sum + Number(row) / 1024, 0)
    } catch { /* RSS is optional on platforms without ps. */ }

    const fields = ['calls', 'triangles', 'geometries', 'textures', 'dpr']
    const renderer = Object.fromEntries(fields.map(key => [key, Math.max(0, ...sample.frames.map(frame => frame[key]))]))
    return {
      samples: sample.frames.length, elapsed_ms: sample.elapsedMs,
      mean_fps: sample.frames.length * 1000 / sample.elapsedMs,
      p95_frame_interval_ms: durations[Math.ceil(durations.length * 0.95) - 1] ?? null,
      interpolating_frames: sample.frames.filter(frame => frame.interpolating).length,
      chrome_cpu_percent: cpuTime * 100_000 / sample.elapsedMs, chrome_rss_mib: rssMiB,
      js_heap_mib: metrics.find(metric => metric.name === 'JSHeapUsedSize')?.value / 2 ** 20,
      renderer,
    }
  }
}
