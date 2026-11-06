import { expect, test, type Page, type WebSocketRoute } from "@playwright/test";
import type { Fleet, Robot } from "../src/fleet";
import { blendPose, toScene } from "../src/scene/coordinates";

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
    await page.locator(".robot-details summary").click();
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
