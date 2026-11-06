import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { createWriteStream, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { chromium, expect } from "@playwright/test";

const { C5_UI_ORIGIN: origin, C43_EVIDENCE_DIR: evidence, DDS_TEST_PAYLOAD: project } = process.env;
if (!origin || !evidence || !project) throw new Error("Set the C5 acceptance environment");
mkdirSync(evidence, { recursive: true });
const runner = "./scripts/run_c5_dashboard.sh";
const chrome = await chromium.launch({ channel: "chrome", headless: true });
const context = await chrome.newContext({ viewport: { width: 1440, height: 900 } });
const system = await chrome.newBrowserCDPSession();
const errors = [];
const initial = new Map();
const moved = new Set();
const chargeOwners = new Set();
const taskStates = new Map();
let last, frames = [];
let apiServer;
const metrics = {};

function startApi() {
  const output = createWriteStream(join(evidence, "api.log"), { flags: "a" });
  apiServer = spawn(runner, ["api"], { stdio: ["ignore", "pipe", "pipe"] });
  apiServer.stdout.pipe(output, { end: false });
  apiServer.stderr.pipe(output, { end: false });
  apiServer.on("close", () => output.end());
}

async function stopApi() {
  if (!apiServer || apiServer.exitCode !== null) return;
  const ended = new Promise((resolve) => apiServer.once("close", resolve));
  execFileSync(runner, ["stop-api"]);
  await Promise.race([ended, delay(5000).then(() => {
    if (apiServer.exitCode === null) throw new Error("API shutdown timeout");
  })]);
}

async function until(probe, label, timeout = 120_000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (await probe()) return;
    await delay(100);
  }
  throw new Error(label);
}

async function pageForFleet() {
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error" && !/WebSocket connection|ERR_CONNECTION_REFUSED|502/.test(message.text())) {
      errors.push({ message: message.text(), location: message.location() });
    }
  });
  page.on("websocket", (socket) => {
    if (!socket.url().endsWith("/ws/fleet")) return;
    socket.on("framereceived", ({ payload }) => {
      const snapshot = JSON.parse(payload.toString());
      last = snapshot;
      frames.push({ time: performance.now(), bytes: Buffer.byteLength(payload) });
      for (const robot of snapshot.robots) {
        if (robot.pose_reliability !== "LIVE") continue;
        assert.equal(robot.pose.frame_id, snapshot.map_frame);
        if (!initial.has(robot.robot_id)) initial.set(robot.robot_id, robot.pose);
        const first = initial.get(robot.robot_id);
        if (Math.hypot(robot.pose.x - first.x, robot.pose.y - first.y) > 0.25) moved.add(robot.robot_id);
      }
      for (const station of snapshot.stations) {
        if (station.charging === "CHARGING") {
          assert.equal(station.charging_robot_id, station.occupied_by_robot_id);
          const owner = snapshot.robots.find((robot) => robot.robot_id === station.charging_robot_id);
          assert.equal(owner.charging_station_id, station.station_id);
          assert.equal(owner.battery_reliability, "LIVE");
          chargeOwners.add(owner.robot_id);
        }
      }
      for (const task of snapshot.tasks) {
        if (!taskStates.has(task.task_id)) taskStates.set(task.task_id, new Set());
        taskStates.get(task.task_id).add(task.status);
      }
    });
  });
  await page.goto(origin);
  return page;
}

function apiUsage() {
  const response = execFileSync("docker", ["exec", `${project}-backend-1`, "bash", "-ec",
    'pid=$(cat /run/fleet-dashboard/api.pid); read -r -a proc < "/proc/$pid/stat"; '
      + 'read -r _ resident _ < "/proc/$pid/statm"; echo "$((proc[13]+proc[14])) $resident $(getconf CLK_TCK) $(getconf PAGESIZE)"'],
  { encoding: "utf8" }).trim();
  const [ticks, pages, clockTicks, pageSize] = response.split(/\s+/).map(Number);
  return { seconds: ticks / clockTicks, rssBytes: pages * pageSize };
}

async function measure(page) {
  frames = [];
  const time = performance.now();
  const apiStart = apiUsage();
  const before = await system.send("SystemInfo.getProcessInfo");
  const browserStats = await page.evaluate(async () => {
    const frameTimes = [];
    const canvasTimes = [];
    const original = CanvasRenderingContext2D.prototype.clearRect;
    CanvasRenderingContext2D.prototype.clearRect = function (...args) {
      if (this.canvas.isConnected && this.canvas.closest(".map-viewport")) canvasTimes.push(performance.now());
      return original.apply(this, args);
    };
    try {
      await new Promise((resolve) => {
        const start = performance.now();
        function frame(now) {
          frameTimes.push(now);
          if (now - start < 5000) requestAnimationFrame(frame);
          else resolve();
        }
        requestAnimationFrame(frame);
      });
      const intervals = (times) => times.slice(1).map((at, index) => at - times[index]).sort((a, b) => a - b);
      const compositor = intervals(frameTimes);
      const render = intervals(canvasTimes);
      return { frames: frameTimes.length, fps: (frameTimes.length - 1) * 1000 / (frameTimes.at(-1) - frameTimes[0]),
        rafIntervalP95Ms: compositor[Math.floor(compositor.length * 0.95)],
        canvasDraws: canvasTimes.length, canvasIntervalP95Ms: render[Math.floor(render.length * 0.95)] ?? null };
    } finally {
      CanvasRenderingContext2D.prototype.clearRect = original;
    }
  });
  const elapsed = (performance.now() - time) / 1000;
  const after = await system.send("SystemInfo.getProcessInfo");
  const apiEnd = apiUsage();
  const devtools = await context.newCDPSession(page);
  const heap = await devtools.send("Runtime.getHeapUsage");
  const priorCpu = new Map(before.processInfo.map(({ id, cpuTime }) => [id, cpuTime]));
  const usedCpu = after.processInfo.reduce((sum, p) => sum + p.cpuTime - (priorCpu.get(p.id) ?? p.cpuTime), 0);
  const chromePids = new Set(after.processInfo.map((process) => process.id));
  const chromeRssKiB = execFileSync("ps", ["-ax", "-o", "pid=,rss="], { encoding: "utf8" })
    .trim().split("\n").map((line) => line.trim().split(/\s+/).map(Number))
    .filter(([pid]) => chromePids.has(pid)).reduce((sum, [, rss]) => sum + rss, 0);
  return { ...browserStats, seconds: elapsed, jsHeapUsedBytes: heap.usedSize,
    chromeCpuPercentOneCore: usedCpu / elapsed * 100, chromeRssSumBytes: chromeRssKiB * 1024,
    apiCpuPercentOneCore: (apiEnd.seconds - apiStart.seconds) / elapsed * 100, apiRssBytes: apiEnd.rssBytes,
    wsHz: frames.length / elapsed, wsFrames: frames.length,
    wsMeanBytes: frames.reduce((sum, frame) => sum + frame.bytes, 0) / frames.length,
    wsMaxBytes: Math.max(...frames.map(({ bytes }) => bytes)) };
}

try {
  startApi();
  let page = await pageForFleet();
  await until(() => last?.robots.length === 2 && last.robots.every((robot) => robot.battery_reliability === "LIVE"
    && robot.pose_reliability === "LIVE"), "Two verified live robots unavailable");
  const details = () => page.locator(".robot-details");
  const ids = last.robots.map(({ robot_id }) => robot_id);
  await expect(page.getByRole("button", { name: /^Robot seç:/ })).toHaveCount(2);
  const selected = page.getByRole("button", { name: `Robot seç: ${ids[1]}` });
  await selected.focus();
  await page.keyboard.press("Enter");
  await expect(details().getByRole("heading", { name: ids[1] })).toBeVisible();
  await expect(details().getByRole("meter")).toBeVisible();
  const accepted = Number(await details().getByRole("meter").getAttribute("aria-valuenow"));
  assert.ok(Math.abs(accepted - last.robots.find((robot) => robot.robot_id === ids[1]).battery_soc_percent) < 0.25);
  await page.screenshot({ path: join(evidence, "overview-1440.png"), fullPage: true });

  const previous = last;
  const outage = performance.now();
  await stopApi();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(details().getByRole("meter")).toHaveCount(0);
  await expect(details().getByText(/Son doğrulanmış konum korunuyor/)).toBeVisible();
  await page.screenshot({ path: join(evidence, "connection-loss.png"), fullPage: true });
  const reconnect = performance.now();
  startApi();
  await until(() => last.backend_session_id !== previous.backend_session_id, "API restart did not resynchronize", 12000);
  assert.equal(last.source_session_id, previous.source_session_id);
  assert.ok(last.sequence > previous.sequence);
  metrics.restart = { fromStopMs: performance.now() - outage, fromStartMs: performance.now() - reconnect,
    oldSequence: previous.sequence, newSequence: last.sequence, producerPreserved: true };

  await until(() => last?.stations.some((station) => station.charging === "CHARGING"),
    "Verified charging not displayed", 60000);
  await page.getByRole("link", { name: "İstasyonlar / Şarj", exact: true }).click();
  await expect(page.getByRole("cell", { name: /Şarj oluyor/ })).toBeVisible();
  await page.screenshot({ path: join(evidence, "charging.png"), fullPage: true });
  await page.getByRole("link", { name: "Genel görünüm", exact: true }).click();

  await until(() => moved.size === 2 && chargeOwners.size === 2 && last.task_counts.active > 0,
    "Live movement, charging or task assignment not visible", 150_000);
  const beforeClose = last;
  await page.close();
  await delay(2200);
  page = await pageForFleet();
  await until(() => last.sequence > beforeClose.sequence + 2, "Fleet source stopped when Chrome page closed", 8000);
  assert.equal(last.source_session_id, beforeClose.source_session_id);
  assert.ok(Object.values(last.task_counts).some((count) => count > 0));
  await page.getByRole("link", { name: "Görevler", exact: true }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await until(() => last?.tasks.length === 3 && last.tasks.every((task) => task.status === "COMPLETED"),
    "Completion not visible in the browser", 140_000);
  await expect(page.getByRole("cell", { name: "Tamamlandı" })).toHaveCount(3);
  await page.screenshot({ path: join(evidence, "tasks.png"), fullPage: true });
  await page.getByRole("link", { name: "İstasyonlar / Şarj", exact: true }).click();
  await expect(page.getByRole("rowheader", { name: "dock_1" })).toBeVisible();
  await page.screenshot({ path: join(evidence, "stations.png"), fullPage: true });
  await page.getByRole("link", { name: "Genel görünüm", exact: true }).click();
  const response = await page.request.get(`${origin}/api/fleet`);
  assert.equal(response.status(), 200);
  assert.equal((await page.request.post(`${origin}/api/tasks`, { data: {} })).status(), 405);
  writeFileSync(join(evidence, "chrome-fleet.json"), JSON.stringify(await response.json(), null, 2));
  metrics.open = await measure(page);
  for (const [width, height] of [[1280, 850], [1920, 1080], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await expect(page.getByRole("heading", { name: "Depo görünümü" })).toBeVisible();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    await page.screenshot({ path: join(evidence, `overview-${width}.png`), fullPage: true });
  }
  assert.ok([...taskStates.values()].some((states) => states.has("ASSIGNED") || states.has("EXECUTING")));
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ result: "C5_CHROME_PASSED", chrome: chrome.version(), moved: [...moved],
    chargeOwners: [...chargeOwners], tasks: Object.fromEntries([...taskStates].map(([id, states]) => [id, [...states]])) }));
} finally {
  writeFileSync(join(evidence, "browser-metrics.json"), JSON.stringify(metrics, null, 2));
  await chrome.close();
  try {
    await stopApi();
  } catch (error) {
    if (apiServer?.exitCode === null) throw error;
  }
}
