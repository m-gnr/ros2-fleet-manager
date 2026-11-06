import { expect, test, type Page, type WebSocketRoute } from "@playwright/test";
import type { Fleet, Robot } from "../src/fleet";
import { fitCamera, projectPose, zoomCamera } from "../src/mapMath";

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

test("lists robots, selects by map and keyboard, and masks invalid battery", async ({ page }) => {
  await feed(page, (socket) => socket.send(JSON.stringify(fixture)));
  await page.goto("/");
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
  const viewport = page.locator(".map-viewport");
  const bounds = (await viewport.boundingBox())!;
  const camera = await viewport.evaluate((element) => ({
    x: Number(element.dataset.cameraX), y: Number(element.dataset.cameraY), scale: Number(element.dataset.scale),
  }));
  await page.mouse.click(bounds.x + camera.x, bounds.y + camera.y - camera.scale);
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

test("fits and pans a responsive Konva map", async ({ page }) => {
  await feed(page, (socket) => socket.send(JSON.stringify(fixture)));
  await page.goto("/");
  await expect(page.getByRole("meter").first()).toBeVisible();
  const viewport = page.locator(".map-viewport");
  const scale = async () => Number(await viewport.getAttribute("data-scale"));
  const x = async () => Number(await viewport.getAttribute("data-camera-x"));
  const fitted = await scale();
  await page.getByRole("button", { name: "Yakınlaştır" }).click();
  expect(await scale()).toBeGreaterThan(fitted);
  const originalX = await x();
  const bounds = (await viewport.boundingBox())!;
  await page.mouse.move(bounds.x + 95, bounds.y + 80);
  await page.mouse.down();
  await page.mouse.move(bounds.x + 143, bounds.y + 103, { steps: 6 });
  await page.mouse.up();
  await expect.poll(x).toBeGreaterThan(originalX + 30);
  await page.getByRole("button", { name: "Filoyu kadraja al" }).click();
  await expect.poll(scale).toBeCloseTo(fitted);
  for (const [width, height] of [[1280, 850], [1440, 900], [1920, 1080], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await expect(page.locator(".map-viewport canvas")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  }
  await page.locator(".robot-details summary").click();
  await expect(page.locator(".robot-details .details-body")).toBeHidden();
});

test("transforms metres and ROS yaw, refuses other frames and anchors zoom", () => {
  expect(projectPose(pose, "map")).toEqual({ x: 0, y: -1, rotation: -90 });
  expect(projectPose({ ...pose, frame_id: "odom" }, "map")).toBeNull();
  expect(projectPose({ ...pose, yaw: Infinity }, "map")).toBeNull();
  expect(projectPose({ ...pose, yaw: -Math.PI }, "map")?.rotation).toBe(180);
  const view = fitCamera([], 640, 460);
  const point = { x: 212, y: 140 };
  const zoomed = zoomCamera(view, point, 1.2);
  expect((point.x - zoomed.x) / zoomed.scale).toBeCloseTo((point.x - view.x) / view.scale);
  expect((point.y - zoomed.y) / zoomed.scale).toBeCloseTo((point.y - view.y) / view.scale);
});
