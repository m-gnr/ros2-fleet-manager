import type { Pose, Reliability, Robot } from "./fleet";

export const reliabilityLabel: Record<Reliability, string> = {
  LIVE: "Canlı", STALE: "Bayat veri", NO_DATA: "Veri bekleniyor", BLOCKED: "Oturum blokeli",
  UNAVAILABLE: "Kullanılamıyor",
};

export const labels: Record<string, string> = {
  IDLE: "Boşta", EXECUTING_TASK: "Görevde", CHARGING: "Şarj oluyor",
  RETURNING_TO_CHARGE: "Şarja gidiyor", RETURNING_TO_PARK: "Parka gidiyor", ERROR: "Hata",
  NOT_CHARGING: "Şarj olmuyor", UNAVAILABLE: "Kullanılamıyor", NOT_APPLICABLE: "Uygulanmaz",
  PARKING: "Park", SAFE_WAITING: "Güvenli bekleme", FREE: "Serbest", RESERVED: "Rezerve",
  OCCUPIED: "İşgal altında", RELEASING: "Ayrılma bekleniyor", BLOCKED: "Blokeli",
  QUEUED: "Kuyrukta", ASSIGNED: "Atandı", EXECUTING: "Yürütülüyor", COMPLETED: "Tamamlandı",
  FAILED: "Başarısız", PREEMPTED: "Kesildi", CANCELED: "İptal edildi",
  HIGH: "Yüksek", MEDIUM: "Orta", LOW: "Düşük",
};

export const displayNumber = (value: number, maximumFractionDigits = 1) =>
  value.toLocaleString("tr-TR", { maximumFractionDigits });

export function poseLabel(pose: Pose | null) {
  return pose ? `${displayNumber(pose.x, 2)}, ${displayNumber(pose.y, 2)} m · ${pose.frame_id}` : "Kullanılamıyor";
}

export function simTime(value: string | null) {
  if (value === null) return "Ölçüm yok";
  const ns = BigInt(value);
  return `${ns / 1000000000n},${(ns % 1000000000n / 1000000n).toString().padStart(3, "0")} sn · ROS zamanı`;
}

export function telemetryAge(age: number | null, reliability: Reliability) {
  if (reliability === "STALE") return "Veri eski";
  if (reliability !== "LIVE" || age === null) return reliability === "BLOCKED" ? "Oturum blokeli" : "Ölçüm yok";
  return age < 1 ? "Az önce" : `${displayNumber(Math.floor(age), 0)} sn önce`;
}

export function robotReliability(robot: Robot, connected: boolean): Reliability {
  return connected || ["BLOCKED", "NO_DATA"].includes(robot.telemetry) ? robot.telemetry : "STALE";
}

export function currentBattery(robot: Robot, connected: boolean) {
  return connected && robot.battery_reliability === "LIVE" ? robot.battery_soc_percent : null;
}
