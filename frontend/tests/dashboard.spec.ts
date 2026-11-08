import { expect, test, type Page, type WebSocketRoute } from "@playwright/test";
import { PerspectiveCamera, Vector3 } from "three";
import { blendPose, toScene } from "../src/scene/coordinates";
import { frameWarehouse } from "../src/scene/framing";
import { simTime, telemetryAge } from "../src/presentation";

import { backend, restarted, pose, valid, invalid, fixture, feed, telemetry } from "./dashboard-fixtures";
import { taskPad } from "../src/scene/taskPad";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/warehouse-layout", route => route.fulfill({ json: { layout: null } }));
});

async function trace(page: Page) {
  await page.addInitScript(() => {
    for (const name of ["frame", "routes", "storage", "warehouse-bounds", "decor-bounds"]) {
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

async function warehouseReady(page: Page) {
  await expect.poll(() => page.evaluate(() => Reflect.get(window, "scene_frame")?.warehouse)).toBe("glb");
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
  await warehouseReady(page);
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
      if (mode === "follow") {
        const { camera: position, target, pose: root } = await frame();
        const view = (await viewport.locator("canvas").boundingBox())!;
        const camera = new PerspectiveCamera(42, view.width / view.height, .035, 90);
        camera.position.fromArray(position);
        camera.lookAt(new Vector3(...target));
        camera.updateMatrixWorld();
        const bodyTop = new Vector3(root[0], .192, root[2]).project(camera);
        const label = page.locator(".scene-label.selected");
        await expect(label).toBeVisible();
        const rect = (await label.boundingBox())!;
        expect(rect.y + rect.height).toBeLessThan(view.y + (1 - bodyTop.y) * view.height / 2);
      }
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
  await warehouseReady(page);
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
  await warehouseReady(page);
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

test("places verified operation markers on map coordinates and prioritizes the selected robot's task", async ({ page }) => {
  await trace(page);
  let socket: WebSocketRoute | undefined;
  const park = { ...fixture.stations[0], station_id: "park_test", station_type: "PARKING" as const,
    pose: { ...pose, x: -2.4, y: -1.1 }, state: "FREE" as const, charging: "NOT_APPLICABLE" as const,
    occupied_by_robot_id: null, reserved_by_robot_id: null, charging_robot_id: null };
  const otherTask = { ...fixture.tasks[0], task_id: "other_task", pickup: { ...pose, x: 3.4, y: -1.8 },
    dropoff: { ...pose, x: -3.2, y: 2.4 }, assigned_robot_id: valid.robot_id };
  const snapshot = { ...fixture, robots: [{ ...valid, active_task_id: otherTask.task_id }, invalid],
    stations: [...fixture.stations, park, { ...park, station_id: "no_pose", pose: null },
      { ...park, station_id: "wrong_frame", pose: { ...pose, frame_id: "odom" } }],
    tasks: [otherTask, fixture.tasks[0]] };
  await feed(page, (route) => {
    socket = route;
    route.send(JSON.stringify(snapshot));
    const tf = telemetry(route);
    tf.connect();
    tf.poses();
  });
  await page.goto("/?trace=1");
  const point = (id: string) => page.locator(`[data-operation-point="${id}"]`);
  await expect(point("pickup:other_task")).toHaveCount(1);
  await expect(point("station:dock_test")).toHaveText("Şarj Aktif");
  await expect(point("station:dock_test")).toHaveAttribute("title", /İşgal altında · Şarj oluyor · robot_alpha/);
  const ownership = page.locator(".robot-details details").filter({ hasText: "İstasyon sahipliği" });
  await ownership.getByText("İstasyon sahipliği", { exact: true }).click();
  await expect(ownership.getByText("dock_test · İşgal altında", { exact: true })).toBeVisible();
  await expect(ownership.getByText("robot_alpha", { exact: true })).toHaveCount(2);
  const marker = page.locator('button[data-robot-id="robot_alpha"]');
  await expect(marker).toHaveAttribute("data-charging", "true");
  const preview = page.locator(".robot-model-preview");
  await expect(preview.getByRole("img")).toBeVisible();
  await expect(preview).toContainText("Şarj oluyor");
  await expect(page.locator("canvas")).toHaveCount(1);
  await expect(point("station:park_test")).toContainText("Serbest");
  await expect(point("station:no_pose")).toHaveCount(0);
  await expect(point("station:wrong_frame")).toHaveCount(0);
  const drawnPoints = () => page.evaluate(() => Reflect.get(window, "scene_frame")?.points.map(
    ({ key, position, yaw }: { key: string; position: number[]; yaw: number }) => [key, position, yaw]));
  await expect.poll(drawnPoints).toContainEqual(["pickup:other_task", [3.4, 0, 1.8], pose.yaw]);
  await expect.poll(drawnPoints).toContainEqual(["dropoff:other_task", [-3.2, 0, -2.4], pose.yaw]);
  await expect.poll(drawnPoints).toContainEqual(["station:park_test", [-2.4, 0, 1.1], pose.yaw]);
  await expect.poll(drawnPoints).toContainEqual(["station:dock_test", [1, 0, -1], pose.yaw]);
  const renderedPoints = await page.evaluate(() => Reflect.get(window, "scene_frame").points);
  const dock = renderedPoints.find((item: { key: string }) => item.key === "station:dock_test");
  const parked = renderedPoints.find((item: { key: string }) => item.key === "station:park_test");
  expect(dock.dockPosition[0]).toBeCloseTo(1.88);
  expect(dock.dockPosition[2]).toBeCloseTo(-1);
  expect(parked.dockPosition).toBeUndefined();
  for (const point of renderedPoints) {
    expect(point.padSize[0]).toBeCloseTo(.92);
    expect(point.padSize[2]).toBeCloseTo(.92);
    expect(point.padPosition[0]).toBeCloseTo(point.position[0]);
    expect(point.padPosition[2]).toBeCloseTo(point.position[2]);
    expect(point.padPosition[1]).toBeGreaterThan(-.032);
    expect(point.padPosition[1]).toBeLessThan(0);
    expect(point.symbol).toBe(true);
  }
  await page.getByRole("button", { name: "Robot seç: robot_beta", exact: true }).click();
  await expect(point("pickup:task_test")).toHaveCount(1);
  await expect(point("pickup:other_task")).toHaveCount(0);
  // This task uses the same map pose for both steps. Keep both halves and their own symbols.
  await expect.poll(() => page.evaluate(() => Reflect.get(window, "scene_frame")?.points
    .filter(({ id }: { id: string }) => id === "task_test")
    .map(({ padSize, padPosition }: { padSize: number[]; padPosition: number[] }) =>
      [Number(padSize[0].toFixed(2)), Number(padPosition[0].toFixed(2))]))).toEqual([[.46, 0], [.46, 0]]);
  await expect(preview).not.toContainText("Şarj oluyor");
  await page.getByRole("button", { name: "Robot seç: robot_alpha", exact: true }).click();
  socket!.send(JSON.stringify({ ...snapshot, sequence: snapshot.sequence + 1, tasks: [],
    robots: [{ ...valid, telemetry: "STALE", battery_reliability: "STALE" }, invalid] }));
  await expect(page.locator('[data-operation-point^="pickup:"], [data-operation-point^="dropoff:"]')).toHaveCount(0);
  await expect.poll(drawnPoints).toHaveLength(2);
  await expect(point("station:dock_test")).toContainText("İşgal altında");
  await expect(point("station:dock_test")).not.toContainText(/robot_alpha|Şarj oluyor/);
  await expect(marker).not.toHaveAttribute("data-charging", "true");
  await expect(preview).not.toContainText("Şarj oluyor");
  await socket!.close();
  await expect(point("station:dock_test")).toContainText("Son eşitleme");
  await expect(point("station:dock_test")).not.toContainText("robot_alpha");
});

test("loads the local GLB without resetting an edited camera", async ({ page }) => {
  await trace(page);
  let release: () => void = () => {};
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/warehouse-aisle*.glb", async (route) => {
    await pending;
    await route.continue();
  });
  const requests: URL[] = [];
  page.on("request", request => {
    if (request.url().endsWith(".glb")) requests.push(new URL(request.url()));
  });
  await feed(page, (route) => {
    route.send(JSON.stringify(fixture));
    const tf = telemetry(route);
    tf.connect();
    tf.poses();
  });
  await page.goto("/?trace=1");
  const frame = () => page.evaluate(() => Reflect.get(window, "scene_frame"));
  try {
    await expect.poll(async () => (await frame())?.warehouse).toBe("schematic");
    const original = await frame();
    const canvas = (await page.locator("canvas").boundingBox())!;
    await page.mouse.move(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2);
    await page.mouse.wheel(0, -260);
    await expect.poll(async () => (await frame())?.camera).not.toEqual(original.camera);
    const manual = await frame();
    release();
    await expect.poll(async () => (await frame())?.warehouse).toBe("glb");
    const loaded = await frame();
    expect(new Vector3(...loaded.camera).distanceTo(new Vector3(...manual.camera))).toBeLessThan(.005);
    expect(new Vector3(...loaded.target).distanceTo(new Vector3(...manual.target))).toBeLessThan(.005);
    expect(requests).toHaveLength(1);
    expect(requests[0].origin).toEqual(new URL(page.url()).origin);
  } finally {
    release();
  }
});

test("keeps live robots and camera controls when the local GLB fails", async ({ page }) => {
  await trace(page);
  await page.route("**/warehouse-aisle*.glb", route => route.abort());
  await feed(page, (route) => {
    route.send(JSON.stringify(fixture));
    const tf = telemetry(route);
    tf.connect();
    tf.poses();
  });
  const failed = page.waitForEvent("requestfailed", request => request.url().endsWith(".glb"));
  await page.goto("/?trace=1");
  await failed;
  await expect(page.locator(".scene-indicator")).toHaveText("2 / 2 TF LIVE");
  await page.getByRole("button", { name: "Üstten", exact: true }).click();
  await expect.poll(() => page.evaluate(() => {
    const frame = Reflect.get(window, "scene_frame");
    return [frame?.warehouse, frame?.mode, frame?.transitioning];
  })).toEqual(["schematic", "top", false]);
});

test("frames the walls and keeps raised decor outside the open operations floor", async ({ page }) => {
  await trace(page);
  await feed(page, (socket) => socket.send(JSON.stringify(fixture)));
  await page.goto("/?trace=1");
  await warehouseReady(page);
  const { storage, decor, corners, frame } = await page.evaluate(() => ({
    storage: Reflect.get(window, "scene_storage"),
    decor: Reflect.get(window, "scene_decor-bounds").boxes,
    corners: Reflect.get(window, "scene_warehouse-bounds") as number[][],
    frame: Reflect.get(window, "scene_frame"),
  }));
  expect(storage.map(({ name }: { name: string }) => name)).toEqual(["rear-rack", "side-rack", "inner-rack", "pallet-row"]);
  const [rear, side, inner, pallets] = storage;
  expect(rear.max[2]).toBeLessThan(-4.4);
  expect(rear.max[1]).toBeGreaterThan(1.8);
  expect(side.max[0]).toBeLessThan(-4.4);
  expect(side.max[2] - side.min[2]).toBeGreaterThan(4);
  expect(inner.min[0]).toBeGreaterThan(1.8);
  expect(inner.max[0]).toBeLessThan(3.55);
  expect(inner.max[2]).toBeLessThan(-1.8);
  expect(rear.max[2]).toBeLessThan(inner.min[2] - 1);
  expect(pallets.min[2]).toBeGreaterThan(4.4);
  expect(pallets.max[1]).toBeLessThan(.5);
  const section = (name: string) => decor.find((item: { name: string }) => item.name === name);
  const [rearWall, leftWall, rightWall] = ["rear-wall", "left-wall", "right-wall"].map(section);
  const partitions = ["loading-divider", "park-divider-north", "park-divider-south"].map(section);
  expect(partitions.every(item => item.max[1] < .30)).toBe(true);
  expect(partitions[2].min[2] - partitions[1].max[2]).toBeGreaterThan(1.1);
  expect(rearWall.name).toBe("rear-wall");
  expect(rearWall.max[2]).toBeLessThan(-5.1);
  expect(rearWall.max[1]).toBeGreaterThan(2.3);
  expect(leftWall.name).toBe("left-wall");
  expect(leftWall.max[0]).toBeLessThan(-5.4);
  expect(rightWall.name).toBe("right-wall");
  expect(rightWall.min[0]).toBeGreaterThan(5.4);
  expect(rightWall.max[1]).toBeLessThan(1.0);
  expect(frame.cutaway).toEqual([]);

  const view = (await page.locator("canvas").boundingBox())!;
  const camera = new PerspectiveCamera(42, view.width / view.height, .035, 90);
  camera.position.fromArray(frame.camera);
  camera.lookAt(new Vector3(...frame.target));
  camera.updateMatrixWorld();
  const projected = corners.map(point => new Vector3().fromArray(point).project(camera));
  expect(Math.max(...projected.map(({ x }) => Math.abs(x)))).toBeLessThan(.96);
  expect(Math.max(...projected.map(({ y }) => Math.abs(y)))).toBeLessThan(.96);
});

test("cuts away obstructing decor when orbiting behind the depot and restores the default view", async ({ page }) => {
  await trace(page);
  await feed(page, (socket) => {
    socket.send(JSON.stringify(fixture));
    const tf = telemetry(socket);
    tf.connect();
    tf.sample(valid.robot_id, 0, 3.8);
    tf.sample(invalid.robot_id, 1, 1);
  });
  await page.goto("/?trace=1");
  await warehouseReady(page);
  const frame = () => page.evaluate(() => Reflect.get(window, "scene_frame"));
  expect((await frame()).cutaway).toEqual([]);
  const view = (await page.locator("canvas").boundingBox())!;
  const x = view.x + view.width / 2;
  const y = view.y + view.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + .46 * view.height, y - .14 * view.height, { steps: 18 });
  await page.mouse.up();
  await expect.poll(async () => (await frame()).cutaway).toContain("rear-wall");
  await expect.poll(async () => (await frame()).cutaway).toContain("rear-rack");
  expect((await frame()).robots[0].pose).toEqual([0, 0, -3.8]);
  await page.getByRole("button", { name: "Kamerayı sıfırla", exact: true }).click();
  await expect.poll(async () => {
    const current = await frame();
    return [current.transitioning, current.cutaway];
  }).toEqual([false, []]);
  const marker = page.locator('button[data-robot-id="robot_alpha"]');
  await expect(marker).toBeVisible();
  await expect(marker).toHaveCSS("width", "26px");
});

test("keeps nearby task pads distinct and anchors the selected label to the correct robot", async ({ page }) => {
  await trace(page);
  const id = "shipment-very-long-order-0217";
  const pickup = { ...pose, x: -3.4, y: 3.20 };
  const dropoff = { ...pose, x: -3.32, y: 3.24 };
  await feed(page, (socket) => {
    socket.send(JSON.stringify({ ...fixture, tasks: [{ ...fixture.tasks[0], task_id: id, pickup, dropoff }],
      robots: [valid, { ...invalid, active_task_id: id }] }));
    const tf = telemetry(socket);
    tf.connect();
    tf.sample(valid.robot_id, pickup.x, pickup.y);
    tf.sample(invalid.robot_id, pickup.x + .01, pickup.y);
  });
  await page.goto("/?trace=1");
  await warehouseReady(page);
  const selected = page.locator(".scene-label.selected");
  await expect(selected).toHaveAttribute("data-robot-id", valid.robot_id);
  await expect(selected).toBeVisible();
  await expect(page.locator(`.scene-label[data-robot-id="${invalid.robot_id}"]`)).toBeHidden();
  const labels = page.locator('[data-operation-point^="pickup:"], [data-operation-point^="dropoff:"]');
  await expect(labels).toHaveCount(2);
  await expect(labels.first()).toContainText("shipmen…0217");
  await expect(labels.first()).toHaveAttribute("title", `Alım · ${id}`);
  await expect(labels.last()).toHaveAttribute("title", `Teslim · ${id}`);
  expect(await labels.filter({ visible: true }).count()).toBeLessThan(2);
  const frame = await page.evaluate(() => Reflect.get(window, "scene_frame"));
  expect(frame.points.filter(({ id: pointId }: { id: string }) => pointId === id).map(
    ({ position, symbol }: { position: number[]; symbol: boolean }) => [position, symbol]
  )).toEqual([[[pickup.x, 0, -pickup.y], true], [[dropoff.x, 0, -dropoff.y], true]]);
  const rects = await page.locator(".scene-label:visible, .scene-point-label:visible").evaluateAll(elements =>
    elements.map(e => e.getBoundingClientRect().toJSON()));
  for (let i = 0; i < rects.length; i++) for (const b of rects.slice(i + 1)) {
    const a = rects[i];
    expect(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top).toBe(true);
  }
});

test("cuts diagonal overlap at the shared bisector and leaves distant pads square", () => {
  const dx = .31, dy = -.14, middle = (dx * dx + dy * dy) / 2;
  const pickup = taskPad(dx, dy, true)!;
  const dropoff = taskPad(-dx, -dy, false)!;
  const projection = (x: number, y: number) => x * dx + y * dy;
  expect(pickup.vertices.every(([x, y]) => projection(x, y) <= middle + 1e-12)).toBe(true);
  expect(dropoff.vertices.every(([x, y]) => projection(x + dx, y + dy) >= middle - 1e-12)).toBe(true);
  expect(pickup.vertices.some(([x, y]) => Math.abs(projection(x, y) - middle) < 1e-12)).toBe(true);
  expect(taskPad(.95, -.14, true)).toBeUndefined();
});
