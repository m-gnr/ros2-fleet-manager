import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { createWriteStream, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { chromium, expect } from "@playwright/test";

const { C5_UI_ORIGIN: origin, C43_EVIDENCE_DIR: evidence, DDS_TEST_PAYLOAD: project } = process.env;
const startupTimeout = Number(process.env.C5_STARTUP_TIMEOUT_MS ?? 120_000);
if (!Number.isFinite(startupTimeout) || startupTimeout <= 0) throw new Error("Invalid C5 startup timeout");
if (!origin || !evidence || !project) throw new Error("Set the C5 acceptance environment");
mkdirSync(evidence, { recursive: true });
const runner = "./scripts/run_c5_dashboard.sh";
const chrome = await chromium.launch({ channel: "chrome", headless: true });
const context = await chrome.newContext({ viewport: { width: 1440, height: 900 } });
const system = await chrome.newBrowserCDPSession();
const errors = [];
const sceneEnabled = Boolean(process.env.C5_SCENE_PORT);
const scenePackets = [];
const rendered = [];
const routeEvents = [];
const traceFrames = [];
let decorBounds;
const operationSources = new Map();
const pointChecks = new Map();
const verifyWarehouse = process.env.C5_VERIFY_WAREHOUSE === "1";
const urls = new Set();
const pct = (items, fraction) => [...items].sort((a, b) => a - b).at(Math.floor((items.length - 1) * fraction)) ?? null;
if (sceneEnabled) {
  await context.exposeFunction("recordScene", (type, detail) => {
    if (type === "rendered") rendered.push(detail);
    if (type === "routes") routeEvents.push(detail);
    if (type === "frame") traceFrames.push(detail);
    if (type === "decor-bounds" && detail.layout === "glb") decorBounds = detail.boxes;
  });
  await context.addInitScript(() => {
    for (const type of ["rendered", "routes", "frame", "decor-bounds"]) {
      window.addEventListener("fleet-visualizer:" + type, (e) => window.recordScene(type, e.detail));
    }
  });
}
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
    urls.add(socket.url());
    if (!socket.url().endsWith("/ws/fleet")) return;
    socket.on("framereceived", ({ payload }) => {
      const snapshot = JSON.parse(payload.toString());
      frames.push({ time: performance.now(), bytes: Buffer.byteLength(payload), type: snapshot.type ?? "product" });
      if (snapshot.type) {
        if (snapshot.type === "scene") scenePackets.push(snapshot.packet);
        return;
      }
      last = snapshot;
      if (verifyWarehouse) {
        for (const station of snapshot.stations) operationSources.set(`station:${station.station_id}`, station.pose);
        for (const task of snapshot.tasks) {
          for (const kind of ["pickup", "dropoff"]) operationSources.set(`${kind}:${task.task_id}`, task[kind]);
        }
      }
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
  await page.goto(sceneEnabled ? origin + "/?trace=1" : origin);
  return page;
}

function bridgeUsage() {
  if (!sceneEnabled) return null;
  const result = execFileSync("docker", ["exec", `${project}-scene-1`, "bash", "-ec",
    'pid=$(pgrep -f "^python3 /gated_bridge.py "); read -r -a proc < "/proc/$pid/stat"; read -r _ resident _ < "/proc/$pid/statm"; '
      + 'echo "$((proc[13]+proc[14])) $resident $(getconf CLK_TCK) $(getconf PAGESIZE)"'], { encoding: "utf8" });
  const [ticks, pages, clockTicks, pageSize] = result.trim().split(/\s+/).map(Number);
  return { seconds: ticks / clockTicks, rssBytes: pages * pageSize };
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
  const bridgeStart = bridgeUsage();
  const sceneStart = traceFrames.length;
  const browserStats = await page.evaluate(async () => {
    const frameTimes = [];
    await new Promise((resolve) => {
      const start = performance.now();
      function frame(now) {
        frameTimes.push(now);
        if (now - start < 5000) requestAnimationFrame(frame);
        else resolve();
      }
      requestAnimationFrame(frame);
    });
    const intervals = frameTimes.slice(1).map((at, index) => at - frameTimes[index]).sort((a, b) => a - b);
    return { rafFps: (frameTimes.length - 1) * 1000 / (frameTimes.at(-1) - frameTimes[0]),
      rafIntervalP95Ms: intervals[Math.floor(intervals.length * 0.95)] };
  });
  const bridgeEnd = bridgeUsage();
  const draws = traceFrames.slice(sceneStart);
  const latestDraw = draws.at(-1);
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
    sceneFps: draws.length / elapsed, sceneIntervalP95Ms: pct(draws.slice(1).map((draw, i) => draw.at - draws[i].at), .95),
    drawCallsP95: pct(draws.map((draw) => draw.calls), .95), geometries: latestDraw?.geometries, textures: latestDraw?.textures,
    bridgeCpuPercentOneCore: bridgeEnd && (bridgeEnd.seconds - bridgeStart.seconds) / elapsed * 100,
    bridgeRssBytes: bridgeEnd?.rssBytes,
    wsHzByType: Object.fromEntries([...new Set(frames.map(({ type }) => type))].map((type) =>
      [type, frames.filter((frame) => frame.type === type).length / elapsed])),
    chromeCpuPercentOneCore: usedCpu / elapsed * 100, chromeRssSumBytes: chromeRssKiB * 1024,
    apiCpuPercentOneCore: (apiEnd.seconds - apiStart.seconds) / elapsed * 100, apiRssBytes: apiEnd.rssBytes,
    wsHz: frames.length / elapsed, wsFrames: frames.length,
    wsMeanBytes: frames.reduce((sum, frame) => sum + frame.bytes, 0) / frames.length,
    wsMaxBytes: Math.max(...frames.map(({ bytes }) => bytes)) };
}

async function recordLayout(page) {
  const result = await page.evaluate(() => {
    const box = (selector) => {
      const { x, y, width, height, bottom } = document.querySelector(selector).getBoundingClientRect();
      return { x, y, width, height, bottom };
    };
    return {
      width: window.innerWidth, height: window.innerHeight,
      scrollWidth: document.documentElement.scrollWidth, scrollHeight: document.documentElement.scrollHeight,
      scene: box(".scene-viewport"), metrics: box(".metrics"), panel: box(".robot-details"),
      fleet: box(".robot-list"), cards: [...document.querySelectorAll(".robot-card")].map((card) => ({
        top: card.getBoundingClientRect().top, bottom: card.getBoundingClientRect().bottom,
      })),
    };
  });
  metrics.layout ??= {};
  metrics.layout[result.width] = result;
  assert.ok(result.scrollWidth <= result.width);
  if (process.env.C5_REQUIRE_COMPACT === "1" && result.width >= 1280) {
    assert.equal(result.scrollHeight, result.height);
    assert.ok(result.scene.height >= result.height * 0.57);
    assert.ok(result.metrics.height <= 52);
    assert.ok(result.cards.every(({ top, bottom }) => top === result.cards[0].top && bottom <= result.height));
  }
}

try {
  startApi();
  let page = await pageForFleet();
  await until(() => last?.robots.length === 2 && last.robots.every((robot) => robot.battery_reliability === "LIVE"
    && robot.pose_reliability === "LIVE"), "Two verified live robots unavailable", startupTimeout);
  const details = () => page.locator(".robot-details");
  const capture = (name) => page.screenshot({ path: join(evidence, name + ".png"), fullPage: true });
  const ids = last.robots.map(({ robot_id }) => robot_id);
  await expect(page.getByRole("button", { name: /^Robot seç:/ })).toHaveCount(2);
  if (sceneEnabled) {
    if (verifyWarehouse) await until(() => traceFrames.at(-1)?.warehouse === "glb",
      "Local GLB did not render in Chrome", 10000);
    await until(() => traceFrames.at(-1)?.robots.filter((robot) => robot.visible && robot.status === "LIVE").length === 2,
      "Chrome did not render two live TF robots");
    await expect(page.locator(".scene-viewport canvas")).toBeVisible();
    metrics.firstSceneFrameMs = traceFrames[0].at;
    await recordLayout(page);
    await capture("isometric-two-robots");
    await page.screenshot({ path: join(evidence, "startup-1440.png") });
    metrics.initialLoad = await page.evaluate(() => ({
      domInteractiveMs: performance.getEntriesByType("navigation")[0].domInteractive,
      sceneChunkMs: performance.getEntriesByType("resource").find((item) => /assets\/Scene-/.test(item.name))?.responseEnd,
    }));
  }
  const selectionAt = performance.now();
  const selected = page.getByRole("button", { name: `Robot seç: ${ids[1]}` });
  await selected.focus();
  await page.keyboard.press("Enter");
  await expect(details().getByRole("heading", { name: ids[1] })).toBeVisible();
  await expect(details().getByRole("meter")).toBeVisible();
  const accepted = Number(await details().getByRole("meter").getAttribute("aria-valuenow"));
  assert.ok(Math.abs(accepted - last.robots.find((robot) => robot.robot_id === ids[1]).battery_soc_percent) < 0.25);
  metrics.selectionMs = performance.now() - selectionAt;
  await capture("selected-robot");

  if (process.env.C5_REQUIRE_COMPACT === "1") {
    const canvas = page.locator(".scene-viewport canvas");
    const bounds = await canvas.boundingBox();
    const first = traceFrames.at(-1)?.robots.find((robot) => robot.robot_id === ids[0]);
    assert.ok(bounds && first?.visible);
    await page.mouse.click(bounds.x + bounds.width * first.screen[0], bounds.y + bounds.height * first.screen[1]);
    await expect(details().getByRole("heading", { name: ids[0] })).toBeVisible();
    await expect(page.getByRole("button", { name: `Robot seç: ${ids[0]}` })).toHaveAttribute("aria-pressed", "true");
    await selected.click();
  }

  if (sceneEnabled) {
    const tf = details().getByTestId("tf-status");
    const gate = join(evidence, "gates", ids[1]);
    writeFileSync(gate, "");
    try {
      await expect(tf).toHaveText("STALE", { timeout: 8000 });
      await expect(page.locator(".scene-indicator")).toHaveText("1 / 2 TF LIVE");
      await expect(details().getByRole("meter")).toBeVisible();
      await capture("isolated-tf-stale");
    } finally {
      rmSync(gate, { force: true });
    }
    await expect(tf).toHaveText("LIVE", { timeout: 10000 });
    const bridge = `${project}-scene-1`;
    const source = last.source_session_id;
    const sequence = last.sequence;
    execFileSync("docker", ["stop", bridge]);
    await expect(tf).toHaveText("STALE");
    await expect(details().getByRole("meter")).toBeVisible();
    await until(() => last.sequence > sequence + 2, "Product source stopped with bridge", 8000);
    assert.equal(last.source_session_id, source);
    execFileSync("docker", ["start", bridge]);
    await expect(tf).toHaveText("LIVE", { timeout: 10000 });
  }

  const previous = last;
  const outage = performance.now();
  await stopApi();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(details().getByRole("meter")).toHaveCount(0);
  await expect(details().getByText(/Ürün akışı kesildi/)).toBeVisible();
  if (verifyWarehouse) await expect(page.locator(".scene-marker[data-charging=true]")).toHaveCount(0);
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
  const chargingStation = last.stations.find((station) => station.charging === "CHARGING");
  const chargingId = chargingStation.charging_robot_id;
  await page.getByRole("button", { name: `Robot seç: ${chargingId}` }).click();
  await expect(details().getByText("Şarj oluyor", { exact: true }).first()).toBeVisible();
  if (verifyWarehouse) {
    const key = `station:${chargingStation.station_id}`;
    await until(() => traceFrames.at(-1)?.points?.some(point =>
      point.key === key && point.chargingRobot === chargingId && point.owner === chargingId && point.dockPosition),
    "Verified C4 owner did not appear on the 3D dock", 8000);
    await expect(page.locator(".scene-marker[data-charging=true]")).toHaveAttribute("data-robot-id", chargingId);
    await expect(page.locator(".robot-model-preview")).toContainText("Şarj oluyor");
  }
  await capture("charging-scene");
  await page.getByRole("link", { name: "İstasyonlar / Şarj", exact: true }).click();
  await expect(page.getByRole("cell", { name: /Şarj oluyor/ })).toBeVisible();
  await page.screenshot({ path: join(evidence, "charging.png"), fullPage: true });
  await page.getByRole("link", { name: "Genel görünüm", exact: true }).click();

  await until(() => moved.size === 2 && chargeOwners.size === 2 && last.task_counts.active > 0,
    "Live movement, charging or task assignment not visible", 150_000);
  if (sceneEnabled) {
    await until(() => scenePackets.some(({ type }) => type === "robot_path") &&
      routeEvents.some(({ plan_vertices }) => plan_vertices?.length > 1) &&
      routeEvents.some(({ trail_vertices }) => trail_vertices?.length > 1),
    "Live plan and TF trail did not render", 20000);
    await until(async () => {
      for (const id of ids) {
        const path = routeEvents.findLast(event => event.robot_id === id && event.plan_vertices !== undefined);
        if (!path?.plan_vertices?.length) continue;
        await page.getByRole("button", { name: `Robot seç: ${id}` }).click();
        if (/Güncel.*Durum B/.test(await details().getByTestId("plan-status").textContent())) return true;
      }
      return false;
    }, "Observed Nav2 plan label did not match a visible ROS plan", 20000);
    if (verifyWarehouse) {
      await until(() => traceFrames.at(-1)?.points?.some(point => point.kind === "pickup"),
        "Pickup/dropoff did not render during an active task", 8000);
    }
    await capture("active-task-plan");
    await page.getByRole("button", { name: "Robotu takip et" }).click();
    await until(() => traceFrames.at(-1)?.mode === "follow" && !traceFrames.at(-1).transitioning, "Follow camera did not settle", 10000);
    await capture("camera-follow");
    await page.getByRole("button", { name: "Üstten" }).click();
    await until(() => traceFrames.at(-1)?.mode === "top" && !traceFrames.at(-1).transitioning, "Top camera did not settle", 10000);
    if (verifyWarehouse) await capture("camera-top");
    await page.getByRole("button", { name: "Filoyu kadraja al" }).click();
    await until(() => traceFrames.at(-1)?.mode === "fit" && !traceFrames.at(-1).transitioning, "Fleet camera did not settle", 10000);
    await capture("camera-fit");
    await page.getByRole("button", { name: "Kamerayı sıfırla" }).click();
    await until(() => traceFrames.at(-1)?.mode === "free" && !traceFrames.at(-1).transitioning, "Reset did not settle", 10000);
    await capture("camera-reset");
    metrics.layersOn = await measure(page);
    await page.getByLabel(/Gözlemlenen Nav2 planı/).uncheck();
    await page.getByLabel("TF hareket izi").uncheck();
    metrics.layersOff = await measure(page);
    await page.getByLabel(/Gözlemlenen Nav2 planı/).check();
    await page.getByLabel("TF hareket izi").check();
  }
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
    await recordLayout(page);
    await page.screenshot({ path: join(evidence, `viewport-${width}.png`) });
    await page.screenshot({ path: join(evidence, `overview-${width}.png`), fullPage: true });
  }
  assert.ok([...taskStates.values()].some((states) => states.has("ASSIGNED") || states.has("EXECUTING")));
  assert.deepEqual(errors, []);
  if (sceneEnabled) {
    assert.deepEqual([...urls], [origin.replace(/^http/, "ws") + "/ws/fleet"]);
    const poses = new Map(scenePackets.filter((p) => p.type === "robot_pose").map((p) =>
      [`${p.robot_id}:${p.stream_id}:${p.epoch}:${p.stamp_ns}`, p]));
    for (const frame of rendered) {
      const key = `${frame.robot_id}:${frame.stream_id}:${frame.epoch}:${frame.stamp_ns}`;
      const packet = poses.get(key);
      assert.ok(packet, key);
      assert.ok(Math.hypot(frame.x - packet.x, frame.z + packet.y) < 1e-7);
      assert.ok(Math.hypot(frame.heading_x - Math.cos(packet.yaw), frame.heading_z + Math.sin(packet.yaw)) < 1e-7);
    }
    const paths = new Map(scenePackets.filter((p) => p.type === "robot_path").map((p) =>
      [`${p.robot_id}:${p.stamp_ns}`, p.points]));
    const vertexMatches = ([x, , z], [px, py]) => Math.hypot(x - px, z + py) < 1e-6;
    for (const route of routeEvents) {
      if (route.trail) {
        const anchors = route.trail.map((point) => {
          const sample = poses.get(`${route.robot_id}:${point.stream_id}:${point.epoch}:${point.stamp_ns}`);
          assert.ok(sample, point.stamp_ns);
          return [sample.x, sample.y];
        });
        const expected = anchors.flatMap((anchor, index) => index && !route.trail[index].start
          ? [anchors[index - 1], anchor] : []);
        assert.equal(expected.length, route.trail_vertices.length);
        assert.ok(route.trail_vertices.every((vertex, i) => vertexMatches(vertex, expected[i])));
      }
      if (route.plan_vertices?.length) {
        const points = paths.get(`${route.robot_id}:${route.plan}`);
        assert.equal(points?.length, route.plan_vertices.length);
        assert.ok(route.plan_vertices.every((vertex, i) => vertexMatches(vertex, points[i])));
      }
    }
    assert.ok(ids.every((id) => rendered.some((frame) => frame.robot_id === id)));
    metrics.renderedAnchorChecks = rendered.length;
    if (verifyWarehouse) {
      let checked = 0;
      for (const frame of traceFrames) {
        if (frame.warehouse !== "glb") continue;
        for (const point of frame.points) {
          const source = operationSources.get(point.key);
          assert.equal(source?.frame_id, "map", point.key);
          assert.deepEqual(point.position, [source.x, 0, -source.y].map(value => value || 0), point.key);
          assert.equal(point.yaw, source.yaw, point.key);
          pointChecks.set(point.key, { ...point, source });
          checked++;
        }
      }
      for (const kind of ["pickup", "dropoff", "station"]) {
        assert.ok([...pointChecks.keys()].some(key => key.startsWith(kind + ":")), kind);
      }
      metrics.operationPointChecks = checked;
      writeFileSync(join(evidence, "chrome-operation-points.json"), JSON.stringify([...pointChecks.values()], null, 2));
    }
  }
  console.log(JSON.stringify({ result: sceneEnabled ? "C5_3D_CHROME_PASSED" : "C5_CHROME_PASSED", chrome: chrome.version(), moved: [...moved],
    chargeOwners: [...chargeOwners], tasks: Object.fromEntries([...taskStates].map(([id, states]) => [id, [...states]])) }));
} finally {
  if (sceneEnabled) {
    if (decorBounds) writeFileSync(join(evidence, "decor-bounds.json"), JSON.stringify(decorBounds, null, 2));
    writeFileSync(join(evidence, "scene-packets.json"), JSON.stringify(scenePackets));
    writeFileSync(join(evidence, "scene-rendered.json"), JSON.stringify(rendered));
    writeFileSync(join(evidence, "scene-routes.json"), JSON.stringify(routeEvents));
  }
  writeFileSync(join(evidence, "browser-metrics.json"), JSON.stringify(metrics, null, 2));
  await chrome.close();
  try {
    await stopApi();
  } catch (error) {
    if (apiServer?.exitCode === null) throw error;
  }
}
