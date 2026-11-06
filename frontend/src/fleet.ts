import { z } from "zod";

const reliability = z.enum(["LIVE", "STALE", "NO_DATA", "BLOCKED", "UNAVAILABLE"]);
const simStamp = z.string().regex(/^\d+$/).nullable();
const chargeState = z.enum(["CHARGING", "NOT_CHARGING", "UNAVAILABLE"]);
const pose = z.object({ x: z.number(), y: z.number(), yaw: z.number(), frame_id: z.string() });

const robot = z.object({
  robot_id: z.string(),
  state: z.enum(["IDLE", "EXECUTING_TASK", "CHARGING", "RETURNING_TO_CHARGE", "RETURNING_TO_PARK", "ERROR"]).nullable(),
  telemetry: reliability,
  initial_status_verified: z.boolean(),
  status_sim_ns: simStamp,
  status_age_sec: z.number().nonnegative().nullable(),
  pose: pose.nullable(),
  pose_sim_ns: simStamp,
  pose_reliability: reliability,
  battery_reliability: reliability,
  battery_soc_percent: z.number().min(0).max(100).nullable(),
  battery_energy_wh: z.number().nonnegative().nullable(),
  battery_sim_ns: simStamp,
  charging: chargeState,
  charging_station_id: z.string().nullable(),
  active_task_id: z.string().nullable(),
});

const task = z.object({
  task_id: z.string(), status: z.string(), priority: z.enum(["HIGH", "MEDIUM", "LOW"]),
  pickup: pose, dropoff: pose, assigned_robot_id: z.string().nullable(),
  created_at_source_seconds: z.number().nullable(), review_hold: z.boolean(),
});

const station = z.object({
  station_id: z.string(), station_type: z.enum(["CHARGING", "PARKING", "SAFE_WAITING"]),
  pose: pose.nullable(), state: z.enum(["FREE", "RESERVED", "OCCUPIED", "RELEASING", "BLOCKED"]),
  reserved_by_robot_id: z.string().nullable(), occupied_by_robot_id: z.string().nullable(),
  charging: z.enum(["CHARGING", "NOT_CHARGING", "UNAVAILABLE", "NOT_APPLICABLE"]),
  charging_robot_id: z.string().nullable(),
});

export const fleetSchema = z.object({
  schema_version: z.literal(1),
  backend_session_id: z.uuid(),
  source_session_id: z.uuid(),
  sequence: z.number().int().positive(),
  generated_at_utc: z.iso.datetime({ offset: true }),
  map_frame: z.literal("map"),
  robots: z.array(robot),
  tasks: z.array(task).max(100),
  task_counts: z.object({ total: z.number().int().nonnegative(), queued: z.number().int().nonnegative(),
    active: z.number().int().nonnegative() }),
  stations: z.array(station),
});

export type Fleet = z.infer<typeof fleetSchema>;
export type Robot = z.infer<typeof robot>;
export type Station = z.infer<typeof station>;
export type Pose = z.infer<typeof pose>;
export type Reliability = z.infer<typeof reliability>;

export function compareSnapshot(next: Fleet, previous: Fleet | null, firstOnSocket: boolean) {
  if (!previous) return "apply";
  const sameSession = next.backend_session_id === previous.backend_session_id
    && next.source_session_id === previous.source_session_id;
  if (!sameSession) return firstOnSocket ? "apply" : "resync";
  if (next.sequence > previous.sequence) return "apply";
  if (firstOnSocket && next.sequence === previous.sequence) return "confirm";
  return "ignore";
}
