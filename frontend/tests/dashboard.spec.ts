import { expect, test, type Page, type WebSocketRoute } from "@playwright/test";
import { PerspectiveCamera, Vector3 } from "three";
import type { Fleet, Robot } from "../src/fleet";
import { blendPose, toScene } from "../src/scene/coordinates";
import { frameWarehouse } from "../src/scene/framing";
import { simTime, telemetryAge } from "../src/presentation";

const backend = "c98d630d-85a8-4173-955d-430ac96d6049";
const producer = "acdc62c6-569f-4eec-aa8e-fe3fd5bb32d2";
const restarted = "7f54a72b-be30-420f-a82b-e1f7212bde7b";
const pose = { x: 0, y: 1, yaw: Math.PI / 2, frame_id: "map" };
const valid: Robot = {
  robot_id: "robot_alpha", state: "CHARGING", telemetry: "LIVE", status_sim_ns: "1000000000",
  status_age_sec: 0.1, pose, pose_reliability: "LIVE", pose_sim_ns: "900000000", initial_status_verified: true,
  battery_soc_percent: 72.5, battery_energy_wh: 72.5, battery_sim_ns: "900000000", battery_reliability: "LIVE",
  charging: "CHARGING", charging_station_id: "dock_test", active_task_id: null,
};
const invalid: Robot = {
  ...valid, robot_id: "robot_beta", state: "EXECUTING_TASK", pose: { ...pose, x: -1, frame_id: "odom" },
  battery_reliability: "UNAVAILABLE", battery_soc_percent: null, battery_energy_wh: null, battery_sim_ns: null,
  charging: "UNAVAILABLE", charging_station_id: null, active_task_id: "task_test",
};
const fixture: Fleet = {
  schema_version: 1, backend_session_id: backend, source_session_id: producer, sequence: 8,
  generated_at_utc: "2026-11-06T16:00:00Z", map_frame: "map", robots: [valid, invalid],
  tasks: [{ task_id: "task_test", status: "ASSIGNED", priority: "HIGH", pickup: pose, dropoff: pose,
    assigned_robot_id: "robot_beta", created_at_source_seconds: 4, review_hold: false }],
  task_counts: { total: 1, queued: 0, active: 1 },
  stations: [{ station_id: "dock_test", station_type: "CHARGING", pose: { ...pose, x: 1 },
    state: "OCCUPIED", reserved_by_robot_id: "robot_alpha", occupied_by_robot_id: "robot_alpha",
    charging: "CHARGING", charging_robot_id: "robot_alpha" }],
};

async function feed(page: Page, handler: (socket: WebSocketRoute) => void) {
  await page.routeWebSocket("**/ws/fleet", handler);
}

function telemetry(socket: WebSocketRoute) {
  const ids = [valid.robot_id, invalid.robot_id];
  const send = (packet: object) => socket.send(JSON.stringify({ type: "scene", packet }));
  let stamp = 1_000_000_000;
  let epoch = 0;
  const identity = (id: string) => ({ robot_id: id, frame_id: "map", source: "tf", version: 1, epoch,
    stream_id: id === valid.robot_id ? backend : producer });
  const sample = (id: string, x: number, y: number, sourceStamp = stamp) => send({
    ...identity(id), type: "robot_pose", stamp_ns: String(sourceStamp), x, y, yaw: Math.PI / 2,
  });
  const status = (id: string, value: string) => send({ ...identity(id), type: "data_status", status: value });
  const plan = (id: string, topic = `/${id}/plan`) => send({
    ...identity(id), type: "robot_path", stamp_ns: String(stamp), source_topic: topic,
    plan_source: "nav2_observed_plan", ttl_ms: 2000, points: [[-2, 1], [-1, 0]],
  });
  function connect() {
    socket.send('{"type":"scene_connected"}');
    send({ type: "fleet_hello", version: 1, robot_ids: ids });
    for (const id of ids) send({ ...identity(id), type: "hello", after_stamp_ns: "0",
      stale_after_ms: 2000, path_topic: `/${id}/plan` });
  }
  function poses() {
    stamp += 100_000_000;
    sample(valid.robot_id, -2, 1);
    sample(invalid.robot_id, 2, -1);
  }
  function rewind() {
    epoch++;
    stamp = 1_000_000_000;
    status(valid.robot_id, "NO_DATA");
  }
  return { connect, poses, sample, status, plan, rewind };
}

async function trace(page: Page) {
  await page.addInitScript(() => {
    for (const name of ["frame", "routes"]) {
      window.addEventListener("fleet-visualizer:" + name, (event) => {
        const detail = (event as CustomEvent).detail;
        Reflect.set(window, "scene_" + name, detail);
        if (name === "routes") {
          if (detail.plan_vertices?.length) Reflect.set(window, "plan_" + detail.robot_id, detail.plan_vertices);
          if (detail.trail) Reflect.set(window, "trail_" + detail.robot_id, detail.trail);
        }
      });
    }
  });
}

test("lists robots, selects by 3D scene and keyboard, and masks invalid battery", async ({ page }) => {
  await trace(page);
  await feed(page, (socket) => {
    socket.send(JSON.stringify(fixture));
    const tf = telemetry(socket);
    tf.connect();
    tf.poses();
  });
  await page.goto("/?trace=1");
  const details = page.locator(".robot-details");
  await expect(page.getByRole("button", { name: /^Robot seç:/ })).toHaveCount(2);
  await expect(details.getByRole("heading", { name: "robot_alpha" })).toBeVisible();
  await expect(details.getByRole("meter")).toHaveAttribute("aria-valuenow", "72.5");
  const beta = page.getByRole("button", { name: "Robot seç: robot_beta" });
  await beta.focus();
  await page.keyboard.press("Enter");
  await expect(details.getByRole("heading", { name: "robot_beta" })).toBeVisible();
  await expect(beta).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator('.scene-label[data-robot-id="robot_beta"]')).toHaveClass(/selected/);
  await expect(details.getByRole("meter")).toHaveCount(0);
  await expect(details.getByText("Kullanılamıyor").first()).toBeVisible();
  await expect(details.getByText("task_test")).toBeVisible();
  const canvas = page.locator(".scene-viewport canvas");
  const root = () => page.evaluate(() => Reflect.get(window, "scene_frame")?.robots.find(
    (entry: { robot_id: string }) => entry.robot_id === "robot_alpha"));
  await expect.poll(async () => (await root())?.visible).toBe(true);
  const anchor = await root();
  expect(anchor.pose).toEqual([-2, 0, -1]);
  expect(anchor.yaw).toBeCloseTo(Math.PI / 2);
  const bounds = (await canvas.boundingBox())!;
  await page.mouse.click(bounds.x + bounds.width * anchor.screen[0], bounds.y + bounds.height * anchor.screen[1]);
  await expect(details.getByRole("heading", { name: "robot_alpha" })).toBeVisible();
  await expect(beta).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator('.scene-label[data-robot-id="robot_alpha"]')).toHaveClass(/selected/);
  await page.getByRole("link", { name: "Görevler" }).click();
  await expect(page.getByRole("rowheader", { name: "task_test" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Atandı" })).toBeVisible();
  await page.getByRole("link", { name: "İstasyonlar / Şarj" }).click();
  await expect(page.getByRole("rowheader", { name: "dock_test" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "İşgal altında" })).toBeVisible();
});

test("displays loading, empty and protocol error states", async ({ page }) => {
  let socket: WebSocketRoute | undefined;
  await feed(page, (route) => { socket = route; });
  await page.goto("/");
  await expect(page.getByText("Bağlanıyor", { exact: true })).toBeVisible();
  await expect.poll(() => !!socket).toBe(true);
  socket!.send(JSON.stringify({ ...fixture, robots: [], tasks: [], stations: [] }));
  await expect(page.getByText("Robot kaydı yok")).toBeVisible();
  socket!.send('{"schema_version":2}');
  await expect(page.getByRole("alert")).toContainText("Filo akışı doğrulanamadı");
});

test("rejects older snapshots and resynchronizes after a disconnected socket", async ({ page }) => {
  const sockets: WebSocketRoute[] = [];
  await feed(page, (socket) => { sockets.push(socket); });
  await page.goto("/");
  await expect.poll(() => sockets.length).toBeGreaterThan(0);
  sockets.at(-1)!.send(JSON.stringify(fixture));
  await expect(page.getByText("Bağlı", { exact: true })).toBeVisible();
  const details = page.locator(".robot-details");
  const inactive = { ...valid, state: "ERROR", battery_reliability: "STALE", battery_soc_percent: null };
  sockets.at(-1)!.send(JSON.stringify({ ...fixture, sequence: 7, robots: [inactive] }));
  await expect(details.getByRole("meter")).toHaveAttribute("aria-valuenow", "72.5");
  const priorSockets = sockets.length;
  sockets.at(-1)!.close();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(details.getByText("Bayat veri", { exact: true })).toBeVisible();
  await expect(details.getByRole("meter")).toHaveCount(0);
  await expect.poll(() => sockets.length).toBeGreaterThan(priorSockets);
  sockets.at(-1)!.send(JSON.stringify({ ...fixture, sequence: 7 }));
  await expect(details.getByRole("meter")).toHaveCount(0);
  sockets.at(-1)!.send(JSON.stringify({ ...fixture, backend_session_id: restarted, sequence: 1,
    robots: [{ ...valid, pose_reliability: "STALE", telemetry: "STALE", battery_reliability: "STALE" }] }));
  await expect(page.getByText("Bağlı", { exact: true })).toBeVisible();
  await expect(details.getByText("Bayat veri", { exact: true })).toBeVisible();
  await expect(details.getByRole("meter")).toHaveCount(0);
});

test("fits, follows, orbits, pans, zooms and displays at mobile widths", async ({ page }) => {
  await trace(page);
  let timer: ReturnType<typeof setInterval> | undefined;
  await feed(page, (socket) => {
    socket.send(JSON.stringify(fixture));
    const tf = telemetry(socket);
    tf.connect();
    tf.poses();
    let sequence = fixture.sequence;
    timer = setInterval(() => {
      tf.poses();
      socket.send(JSON.stringify({ ...fixture, sequence: ++sequence }));
    }, 200);
  });
  try {
    await page.goto("/?trace=1");
    const frame = () => page.evaluate(() => Reflect.get(window, "scene_frame"));
    await expect.poll(async () => (await frame())?.robots.filter((entry: { visible: boolean }) => entry.visible).length).toBe(2);
    const viewport = page.locator(".scene-viewport");
    const bounds = (await viewport.boundingBox())!;
    const camera = (await frame()).camera;
    await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
    await page.mouse.wheel(0, -150);
    await expect.poll(async () => (await frame()).camera).not.toEqual(camera);
    const target = (await frame()).target;
    await page.mouse.down({ button: "right" });
    await page.mouse.move(bounds.x + bounds.width / 2 + 50, bounds.y + bounds.height / 2 + 30, { steps: 6 });
    await page.mouse.up({ button: "right" });
    await expect.poll(async () => (await frame()).target).not.toEqual(target);
    const rotation = (await frame()).camera;
    await page.mouse.down();
    await page.mouse.move(bounds.x + bounds.width / 2 - 55, bounds.y + bounds.height / 2, { steps: 6 });
    await page.mouse.up();
    await expect.poll(async () => (await frame()).camera).not.toEqual(rotation);
    for (const [button, mode] of [
      ["Robotu takip et", "follow"], ["Üstten", "top"], ["Filoyu kadraja al", "fit"], ["Kamerayı sıfırla", "free"],
    ]) {
      await page.getByRole("button", { name: button }).click();
      await expect.poll(async () => {
        const current = await frame();
        return [current.mode, current.transitioning];
      }).toEqual([mode, false]);
    }
    for (const [width, height] of [[1280, 850], [1440, 900], [1920, 1080], [390, 844]]) {
      await page.setViewportSize({ width, height });
      await expect(viewport.locator("canvas")).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    }
    await page.locator(".robot-details > summary").click();
    await expect(page.locator(".robot-details .details-body")).toBeHidden();
  } finally {
    clearInterval(timer);
  }
});

test("keeps product and TF validity separate, clears the observed plan at an epoch fence", async ({ page }) => {
  await trace(page);
  let socket!: WebSocketRoute;
  await feed(page, (route) => { socket = route; });
  await page.goto("/?trace=1");
  await expect.poll(() => !!socket).toBe(true);
  const tf = telemetry(socket);
  socket.send('{"type":"heartbeat"}');
  const details = page.locator(".robot-details");
  const state = details.getByTestId("tf-status");
  socket.send(JSON.stringify(fixture));
  await expect(details.getByRole("meter")).toBeVisible();
  await expect(state).toHaveText("NO_DATA");
  await expect(page.locator(".scene-label:visible")).toHaveCount(0);
  tf.connect();
  tf.poses();
  await expect(state).toHaveText("LIVE");
  tf.plan(valid.robot_id, "/robot_beta/plan");
  await expect(details.getByText("Durum B", { exact: true })).toHaveCount(0);
  tf.plan(valid.robot_id);
  await expect(details.getByText("Durum B", { exact: true })).toBeVisible();
  await expect(details.getByTestId("plan-status")).toContainText("Güncel");
  await expect.poll(() => page.evaluate(() => Reflect.get(window, "plan_robot_alpha")))
    .toEqual([[-2, expect.closeTo(0.039), -1], [-1, expect.closeTo(0.039), -0]]);
  await page.getByLabel(/Gözlemlenen Nav2 planı/).uncheck();
  await expect(page.getByLabel(/Gözlemlenen Nav2 planı/)).not.toBeChecked();
  tf.sample(valid.robot_id, -1.9, 1, 1_200_000_000);
  tf.status(valid.robot_id, "STALE");
  tf.sample(valid.robot_id, -1.8, 1, 1_300_000_000);
  await expect.poll(() => page.evaluate(() => Reflect.get(window, "trail_robot_alpha")?.length)).toBe(3);
  expect(await page.evaluate(() => Reflect.get(window, "trail_robot_alpha")?.at(-1)?.start)).toBe(true);
  tf.status(valid.robot_id, "STALE");
  tf.poses();
  await expect(state).toHaveText("STALE");
  await expect(page.locator('.scene-label[data-robot-id="robot_alpha"]')).toHaveText("robot_alphaSTALE");
  await expect(details.getByTestId("plan-status")).toHaveText("Bayat / Gizli");
  await expect(page.locator(".scene-indicator")).toHaveText("1 / 2 TF LIVE");
  socket.send(JSON.stringify({ ...fixture, sequence: fixture.sequence + 1 }));
  await expect(details.getByRole("meter")).toBeVisible();
  tf.rewind();
  await expect(state).toHaveText("NO_DATA");
  await expect(details.getByText("Durum B", { exact: true })).toHaveCount(0);
  socket.send('{"type":"product_unavailable"}');
  tf.poses();
  await expect(state).toHaveText("LIVE");
  await expect(details.getByRole("meter")).toHaveCount(0);
  await expect(details.getByText(/Ürün akışı kesildi/)).toBeVisible();
  socket.send(JSON.stringify({ ...fixture, sequence: fixture.sequence + 2 }));
  await expect(details.getByRole("meter")).toBeVisible();
  socket.send('{"type":"scene_disconnected"}');
  await expect(state).toHaveText("STALE");
  tf.connect();
  tf.poses();
  await expect(state).toHaveText("LIVE");
});

test("transforms measured ROS axes and yaw and bounds interpolation", () => {
  expect(toScene({ ...pose, x: 4 })).toEqual([4, -1, Math.PI / 2]);
  expect(blendPose(pose, { x: 2, y: 3, yaw: Math.PI }, 22.5)).toEqual({ x: 1, y: 2, yaw: 3 * Math.PI / 4 });
  expect(blendPose(pose, { x: 2, y: 3, yaw: Math.PI }, 500)).toEqual({ x: 2, y: 3, yaw: Math.PI });
});


test("keeps the snapshot strip, warehouse, and fleet cards in view across responsive layouts", async ({ page }) => {
  let peer!: WebSocketRoute;
  const current = { ...fixture, robots: [valid, { ...invalid, charging: "NOT_CHARGING" as const }],
    task_counts: { total: 5, queued: 1, active: 2 } };
  await feed(page, (socket) => {
    peer = socket;
    socket.send(JSON.stringify(current));
    const tf = telemetry(socket);
    tf.connect();
    tf.poses();
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Fleet Manager" })).toBeVisible();
  await expect(page.getByText("SALT OKUNUR", { exact: true })).toBeVisible();
  await expect(page.getByText(/C5 · AŞAMA/)).toHaveCount(0);
  const metrics = page.getByLabel("Filo göstergeleri");
  await expect(metrics.locator(".metric").filter({ hasText: "Canlı telemetri" })).toHaveAttribute("title", /^Doğrulanmış kaynak/);
  await expect(metrics.locator(".metric").filter({ hasText: "Şarjda" })).toHaveAttribute("title", /^Doğrulanmış C4 ölçümü/);
  const metric = (label: string) => metrics.locator(".metric").filter({ hasText: label }).locator("dd");
  for (const [label, value] of [["Toplam robot", "2"], ["Canlı telemetri", "2"], ["Görevler", "52 aktif"], ["Şarjda", "1"]]) {
    await expect(metric(label)).toHaveText(value);
  }
  peer.send(JSON.stringify({ ...current, sequence: current.sequence + 1, task_counts: { total: 6, queued: 2, active: 2 } }));
  await expect(metric("Görevler")).toHaveText("62 aktif");
  const canvas = page.locator(".scene-viewport canvas");
  const cards = page.getByRole("button", { name: /^Robot seç:/ });
  for (const [width, height, minSceneHeight] of [[1440, 900, 535], [1280, 850, 485], [1920, 1080, 715], [390, 844, 300]]) {
    await page.setViewportSize({ width, height });
    await expect(canvas).toBeVisible();
    await expect.poll(async () => (await canvas.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(minSceneHeight);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await expect(page.getByRole("button", { name: "Kamerayı sıfırla" })).toBeInViewport();
    if (width > 900) {
      expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBe(height);
      expect((await metrics.boundingBox())!.height).toBeLessThan(52);
      expect((await cards.nth(0).boundingBox())!.y).toBe((await cards.nth(1).boundingBox())!.y);
      for (const card of await cards.all()) await expect(card).toBeInViewport({ ratio: 1 });
      const details = page.locator(".robot-details");
      await expect(details).toBeInViewport({ ratio: 1 });
      const scene = (await page.locator(".scene-panel").boundingBox())!;
      expect(Math.abs((await details.boundingBox())!.height - scene.height)).toBeLessThanOrEqual(1);
      expect(height - (await cards.nth(1).boundingBox())!.y - (await cards.nth(1).boundingBox())!.height).toBeGreaterThan(0);
    } else {
      const secondCard = (await cards.nth(1).boundingBox())!;
      expect(secondCard.x + secondCard.width).toBeLessThanOrEqual(width);
    }
  }
  await cards.nth(1).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".robot-details").getByRole("heading", { name: invalid.robot_id })).toBeVisible();

  const extra = { ...valid, robot_id: "robot_gamma" };
  peer.send(JSON.stringify({ ...current, sequence: current.sequence + 2, robots: [...current.robots, extra] }));
  await expect(metric("Toplam robot")).toHaveText("3");
  expect(await page.locator(".robot-list").evaluate((list) => list.scrollWidth > list.clientWidth)).toBe(true);
  await cards.nth(2).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".robot-details").getByRole("heading", { name: extra.robot_id })).toBeVisible();
});

test("scrolls expanded details while keeping the panel heading and robot identity fixed", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await feed(page, (socket) => socket.send(JSON.stringify(fixture)));
  await page.goto("/");
  const panel = page.locator(".robot-details");
  await panel.getByText("Konum ve ölçüm zamanı", { exact: true }).click();
  const identity = panel.getByRole("heading", { name: valid.robot_id });
  const title = panel.getByRole("heading", { name: "Robot ayrıntıları" });
  const before = await Promise.all([identity.boundingBox(), title.boundingBox()]);
  const scroller = panel.locator(".details-scroll");
  expect(await scroller.evaluate(e => {
    const details = e.querySelector(".measurement-details dl")!;
    for (let index = 0; index < 6; index++) details.append(...Array.from(details.children).slice(0, 6).map(row => row.cloneNode(true)));
    e.scrollTop = e.scrollHeight;
    return e.scrollTop;
  })).toBeGreaterThan(0);
  expect(await Promise.all([identity.boundingBox(), title.boundingBox()])).toEqual(before);
  expect(await panel.evaluate(e => e.scrollTop)).toBe(0);
  expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBe(720);
});

test("keeps close robots aligned to TF roots at multiple camera distances", async ({ page }) => {
  await trace(page);
  await feed(page, (socket) => {
    socket.send(JSON.stringify(fixture));
    const tf = telemetry(socket);
    tf.connect();
    tf.sample(valid.robot_id, 0, 0);
    tf.sample(invalid.robot_id, 0.01, 0);
  });
  await page.goto("/?trace=1");
  const alpha = page.locator('.scene-label[data-robot-id="robot_alpha"]');
  const beta = page.locator('.scene-label[data-robot-id="robot_beta"]');
  const details = page.locator(".robot-details");
  const canvas = page.locator("canvas");
  const checkMarkers = async (selected: string) => {
    const frame = await page.evaluate(() => Reflect.get(window, "scene_frame"));
    const view = (await canvas.boundingBox())!;
    const camera = new PerspectiveCamera(42, view.width / view.height, .035, 90);
    camera.position.fromArray(frame.camera);
    camera.lookAt(new Vector3(...frame.target));
    camera.updateMatrixWorld();
    expect(frame.robots.map((entry: { pose: number[] }) => entry.pose)).toEqual([[0, 0, -0], [.01, 0, -0]]);
    for (const root of frame.robots) {
      const marker = page.getByRole("button", { name: `3D işaretiyle seç: ${root.robot_id}` });
      await expect(marker).toBeVisible();
      await expect(marker).toHaveAttribute("aria-pressed", String(root.robot_id === selected));
      const rect = (await marker.boundingBox())!;
      const projected = new Vector3(...root.pose).project(camera);
      expect(rect.width).toBeGreaterThanOrEqual(24);
      expect(rect.height).toBeGreaterThanOrEqual(24);
      expect(Math.abs(rect.x + rect.width / 2 - view.x - (projected.x + 1) / 2 * view.width)).toBeLessThan(.05);
      expect(Math.abs(rect.y + rect.height / 2 - view.y - (1 - projected.y) / 2 * view.height)).toBeLessThan(.05);
      const forward = new Vector3(...root.pose).add(new Vector3(.27 * Math.cos(root.yaw), 0, -.27 * Math.sin(root.yaw))).project(camera);
      const heading = Math.atan2((projected.y - forward.y) * view.height, (forward.x - projected.x) * view.width);
      expect(await marker.evaluate(e => parseFloat(e.style.getPropertyValue("--heading")))).toBeCloseTo(heading, 5);
    }
    const label = selected === valid.robot_id ? alpha : beta;
    await expect(label).toHaveText(`${selected}LIVE`);
    await expect(selected === valid.robot_id ? beta : alpha).toBeHidden();
    expect((await label.boundingBox())!.height).toBeLessThanOrEqual(26 * .8);
  };
  await expect(alpha).toBeVisible();
  await checkMarkers(valid.robot_id);
  const bounds = (await canvas.boundingBox())!;
  const camera = await page.evaluate(() => Reflect.get(window, "scene_frame").camera);
  await page.mouse.move(bounds.x + bounds.width / 3, bounds.y + bounds.height / 3);
  await page.mouse.wheel(0, 420);
  await expect.poll(() => page.evaluate(() => Reflect.get(window, "scene_frame").camera)).not.toEqual(camera);
  await page.getByRole("button", { name: "Robot seç: robot_beta" }).click();
  await expect(details.getByRole("heading", { name: invalid.robot_id })).toBeVisible();
  await expect(beta).toBeVisible();
  await checkMarkers(invalid.robot_id);
});

test("refits an untouched camera but preserves zoom, orbit and pan across resize until reset", async ({ page }) => {
  await trace(page);
  await feed(page, (socket) => socket.send(JSON.stringify(fixture)));
  await page.goto("/?trace=1");
  const frame = () => page.evaluate(() => Reflect.get(window, "scene_frame"));
  await expect.poll(frame).toBeTruthy();
  const wide = await frame();
  const viewport = page.locator("canvas");
  await page.setViewportSize({ width: 1280, height: 850 });
  await expect.poll(async () => (await frame()).camera).not.toEqual(wide.camera);
  const compact = await frame();
  await page.setViewportSize({ width: 1440, height: 900 });
  const distance = (a: number[], b: number[]) => new Vector3(...a).distanceTo(new Vector3(...b));
  await expect.poll(async () => distance((await frame()).camera, wide.camera)).toBeLessThan(.005);
  const bounds = (await viewport.boundingBox())!;
  const x = bounds.x + bounds.width / 3, y = bounds.y + bounds.height / 3;
  for (const action of ["zoom", "orbit", "pan"]) {
    const before = await frame();
    await page.mouse.move(x, y);
    if (action === "zoom") await page.mouse.wheel(0, 250);
    else {
      const button = action === "pan" ? "right" : "left";
      await page.mouse.down({ button });
      await page.mouse.move(x + 35, y + 24, { steps: 5 });
      await page.mouse.up({ button });
    }
    await expect.poll(async () => distance((await frame()).camera, before.camera)).toBeGreaterThan(.1);
    // Let OrbitControls' damping settle before measuring the resize delta.
    await expect.poll(async () => {
      const prior = await frame();
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      const next = await frame();
      return distance(prior.camera, next.camera) + distance(prior.target, next.target);
    }).toBeLessThan(.00001);
    const manual = await frame();
    await page.setViewportSize({ width: 1280, height: 850 });
    await expect.poll(async () => (await frame()).at).toBeGreaterThan(manual.at);
    expect(distance((await frame()).camera, manual.camera)).toBeLessThan(.005);
    expect(distance((await frame()).target, manual.target)).toBeLessThan(.005);
    await page.getByRole("button", { name: "Kamerayı sıfırla" }).click();
    await expect.poll(async () => distance((await frame()).camera, compact.camera)).toBeLessThan(.005);
    expect(distance((await frame()).target, compact.target)).toBeLessThan(.005);
    await page.setViewportSize({ width: 1440, height: 900 });
    await expect.poll(async () => distance((await frame()).camera, wide.camera)).toBeLessThan(.005);
  }
});

for (const [state, taskId] of [["IDLE", null], ["EXECUTING_TASK", "task_test"]] as const) {
  test(`shows absent, fresh and expired observed plans with robot state ${state}`, async ({ page }) => {
    const product = { ...fixture, robots: [{ ...valid, state, active_task_id: taskId }, invalid] };
    let tf!: ReturnType<typeof telemetry>;
    let timer: ReturnType<typeof setInterval> | undefined;
    await feed(page, (socket) => {
      socket.send(JSON.stringify(product));
      tf = telemetry(socket);
      tf.connect();
      tf.poses();
      let sequence = product.sequence;
      timer = setInterval(() => {
        tf.poses();
        socket.send(JSON.stringify({ ...product, sequence: ++sequence }));
      }, 200);
    });
    try {
      await page.goto("/");
      const details = page.locator(".robot-details");
      const status = details.getByTestId("plan-status");
      await expect(details.getByTestId("tf-status")).toHaveText("LIVE");
      await expect(status).toHaveText("Plan yok");
      tf.plan(valid.robot_id);
      await expect(status).toHaveText("Güncel Durum B");
      await expect(status.getByText("Durum B")).toHaveAttribute("title", "Aktif Nav2 hedefiyle ilişki doğrulanmadı");
      await expect(status).toHaveText("Bayat / Gizli");
      await expect(details.getByTestId("tf-status")).toHaveText("LIVE");
    } finally {
      clearInterval(timer);
    }
  });
}

test("shows source-reported reception age separately from ROS timestamps", async ({ page }) => {
  let socket!: WebSocketRoute;
  await feed(page, (route) => {
    socket = route;
    route.send(JSON.stringify(fixture));
  });
  await page.goto("/");
  const details = page.locator(".robot-details");
  await expect(details.getByText("Az önce")).toBeVisible();
  const older = { ...valid, status_age_sec: 2.8 };
  socket.send(JSON.stringify({ ...fixture, sequence: 9, robots: [older] }));
  await expect(details.getByText("2 sn önce")).toBeVisible();
  await details.getByText("Konum ve ölçüm zamanı").click();
  await expect(details.getByText("1,000 sn · ROS zamanı")).toBeVisible();
  await expect(details.getByText("Ölçüm yok").first()).toBeVisible();
  socket.send('{"type":"product_unavailable"}');
  await expect(page.getByText("Bağlantı kesildi", { exact: true })).toBeVisible();
  await expect(details.getByText("Veri eski")).toBeVisible();
  await expect(details.getByText("2 sn önce")).toHaveCount(0);
});

test("frames the warehouse bounds at desktop and mobile aspect ratios", () => {
  const corners: Vector3[] = [];
  for (const x of [-7, 7]) for (const y of [-.175, 1.7]) for (const z of [-7, 7]) corners.push(new Vector3(x, y, z));
  for (const aspect of [1.65, 1.8, 2, 1.1, .8]) {
    for (const top of [false, true]) {
      const target = new Vector3();
      const offset = new Vector3();
      const camera = new PerspectiveCamera(42, aspect, .035, 90);
      frameWarehouse(corners, camera.fov, aspect, top, target, offset);
      camera.position.copy(target).add(offset);
      camera.lookAt(target);
      camera.updateMatrixWorld();
      const projected = corners.map((point) => point.clone().project(camera));
      const verticalLimit = top ? .90 : .94;
      expect(projected.every(({ x, y, z }) => Math.abs(x) <= .901 && Math.abs(y) <= verticalLimit + .001 && Math.abs(z) < 1)).toBe(true);
      const limitingAxis = Math.max(...projected.map(({ x, y }) => Math.max(Math.abs(x) / .90, Math.abs(y) / verticalLimit)));
      expect(limitingAxis).toBeCloseTo(1, 5);
    }
  }
});

test("formats ROS time without clock conversion and masks an invalid age", () => {
  expect(simTime("1234567890123456789")).toBe("1234567890,123 sn · ROS zamanı");
  expect(simTime(null)).toBe("Ölçüm yok");
  expect(telemetryAge(15.8, "LIVE")).toBe("15 sn önce");
  expect(telemetryAge(.1, "STALE")).toBe("Veri eski");
  expect(telemetryAge(.1, "BLOCKED")).toBe("Oturum blokeli");
  expect(telemetryAge(null, "LIVE")).toBe("Ölçüm yok");
});

test("disposes orbit listeners and the WebGL context when leaving the overview", async ({ page }) => {
  await page.addInitScript(() => {
    const remove = HTMLCanvasElement.prototype.removeEventListener;
    HTMLCanvasElement.prototype.removeEventListener = function (type: string, listener: EventListenerOrEventListenerObject, options?: boolean | EventListenerOptions) {
      if (type === "pointerdown") this.dataset.orbitDisposed = "true";
      remove.call(this, type, listener, options);
    };
  });
  await trace(page);
  await feed(page, (socket) => socket.send(JSON.stringify(fixture)));
  await page.goto("/?trace=1");
  await expect.poll(() => page.evaluate(() => Boolean(Reflect.get(window, "scene_frame")))).toBe(true);
  const canvas = await page.locator(".scene-viewport canvas").elementHandle();
  await canvas.evaluate((node) => node.addEventListener("webglcontextlost", () => { node.dataset.contextLost = "true"; }));
  await page.getByRole("link", { name: "Görevler" }).click();
  await expect.poll(() => canvas.evaluate((node) => [node.isConnected, node.dataset.orbitDisposed, node.dataset.contextLost]))
    .toEqual([false, "true", "true"]);
  await page.getByRole("link", { name: "Genel görünüm" }).click();
  await expect(page.locator(".scene-viewport canvas")).toBeVisible();
});
