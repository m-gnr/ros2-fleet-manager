import type { Page, WebSocketRoute } from "@playwright/test";
import type { Fleet, Robot } from "../src/fleet";

export const backend = "c98d630d-85a8-4173-955d-430ac96d6049";
export const producer = "acdc62c6-569f-4eec-aa8e-fe3fd5bb32d2";
export const restarted = "7f54a72b-be30-420f-a82b-e1f7212bde7b";
export const pose = { x: 0, y: 1, yaw: Math.PI / 2, frame_id: "map" };
export const valid: Robot = {
  robot_id: "robot_alpha", state: "CHARGING", telemetry: "LIVE", status_sim_ns: "1000000000",
  status_age_sec: 0.1, pose, pose_reliability: "LIVE", pose_sim_ns: "900000000", initial_status_verified: true,
  battery_soc_percent: 72.5, battery_energy_wh: 72.5, battery_sim_ns: "900000000", battery_reliability: "LIVE",
  charging: "CHARGING", charging_station_id: "dock_test", active_task_id: null,
};
export const invalid: Robot = {
  ...valid, robot_id: "robot_beta", state: "EXECUTING_TASK", pose: { ...pose, x: -1, frame_id: "odom" },
  battery_reliability: "UNAVAILABLE", battery_soc_percent: null, battery_energy_wh: null, battery_sim_ns: null,
  charging: "UNAVAILABLE", charging_station_id: null, active_task_id: "task_test",
};
export const fixture: Fleet = {
  schema_version: 1, backend_session_id: backend, source_session_id: producer, sequence: 8,
  generated_at_utc: "2026-11-06T16:00:00Z", map_frame: "map", robots: [valid, invalid],
  tasks: [{ task_id: "task_test", status: "ASSIGNED", priority: "HIGH", pickup: pose, dropoff: pose,
    assigned_robot_id: "robot_beta", created_at_source_seconds: 4, review_hold: false }],
  task_counts: { total: 1, queued: 0, active: 1 },
  stations: [{ station_id: "dock_test", station_type: "CHARGING", pose: { ...pose, x: 1 },
    state: "OCCUPIED", reserved_by_robot_id: "robot_alpha", occupied_by_robot_id: "robot_alpha",
    charging: "CHARGING", charging_robot_id: "robot_alpha" }],
};

export async function feed(page: Page, handler: (socket: WebSocketRoute) => void) {
  await page.routeWebSocket("**/ws/fleet", handler);
}

export function telemetry(socket: WebSocketRoute) {
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
