import { BatteryCharging, Bot, ChevronRight, CircleAlert, LocateFixed, Radio } from "lucide-react";
import type { Fleet, Reliability, Robot } from "./fleet";
import { currentBattery, displayNumber, labels, poseLabel, reliabilityLabel, robotReliability, simTime } from "./presentation";

export function ReliabilityBadge({ value }: { value: Reliability }) {
  return <span className={`status-badge ${value.toLowerCase()}`}><i />{reliabilityLabel[value]}</span>;
}

function Battery({ robot, connected }: { robot: Robot; connected: boolean }) {
  const soc = currentBattery(robot, connected);
  return (
    <div className="battery">
      <div className="battery-line"><span><BatteryCharging size={15} /> Batarya</span>
        <strong>{soc === null ? "Kullanılamıyor" : `%${displayNumber(soc)}`}</strong></div>
      <div className={`battery-track ${soc === null ? "unknown" : ""}`}
        role={soc === null ? undefined : "meter"} aria-label="Batarya SoC" aria-valuenow={soc ?? undefined}
        aria-valuemin={0} aria-valuemax={100}>
        {soc !== null && <div style={{ width: `${soc}%` }} />}
      </div>
    </div>
  );
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="empty"><Radio size={24} /><strong>{title}</strong><p>{detail}</p></div>;
}

export function RobotDetails({ robot, connected }: { robot: Robot | undefined; connected: boolean }) {
  return (
    <details className="card robot-details" open>
      <summary className="card-heading"><div><h2>Robot ayrıntıları</h2><p>Seçili birimin telemetrisi</p></div><ChevronRight size={18} /></summary>
      {robot ? <div className="details-body">
        <div className="detail-identity"><span className="robot-icon"><Bot size={22} /></span>
          <div><h3>{robot.robot_id}</h3><p>{robot.state ? labels[robot.state] : "Durum bilinmiyor"}</p></div>
          <ReliabilityBadge value={robotReliability(robot, connected)} /></div>
        <Battery robot={robot} connected={connected} />
        <dl className="detail-grid">
          <div><dt>Enerji</dt><dd>{connected && robot.battery_energy_wh !== null && robot.battery_reliability === "LIVE"
            ? `${displayNumber(robot.battery_energy_wh, 2)} Wh` : "—"}</dd></div>
          <div><dt>Şarj</dt><dd>{connected ? labels[robot.charging] : "Kullanılamıyor"}</dd></div>
          <div><dt>Aktif görev</dt><dd>{robot.active_task_id ?? "—"}</dd></div>
          <div><dt>Son telemetri</dt><dd title="Gazebo simülasyon saati">{simTime(robot.status_sim_ns)}</dd></div>
          <div><dt><LocateFixed size={13} /> Son doğrulanmış poz</dt><dd>{poseLabel(robot.pose)}</dd></div>
          <div><dt>Batarya ölçümü</dt><dd title="Gazebo simülasyon saati">{simTime(robot.battery_sim_ns)}</dd></div>
        </dl>
        {(!connected || robot.telemetry !== "LIVE" || robot.pose_reliability !== "LIVE" || robot.battery_reliability !== "LIVE") &&
          <div className="detail-warning"><CircleAlert size={16} /><span>
            {robot.telemetry === "BLOCKED" ? "Kaynak oturumu değişti. Telemetri blokeli."
              : !connected ? "Bağlantı kesildi. Son doğrulanmış konum korunuyor."
                : "Poz veya batarya ölçümünün güncelliği doğrulanamadı."}
          </span></div>}
      </div> : <EmptyState title="Robot verisi bekleniyor" detail="Filo eşitlendiğinde bir robot seçebilirsin." />}
    </details>
  );
}

export function RobotList({ fleet, connected, selected, onSelect }: {
  fleet: Fleet | null; connected: boolean; selected: string | undefined; onSelect: (id: string) => void;
}) {
  return <section aria-labelledby="robots-heading">
    <div className="section-heading"><div><h2 id="robots-heading">Filo robotları</h2><p>Ayrıntılarını görmek için bir robot seç.</p></div>
      {fleet && <span className="tag">{fleet.robots.length} robot</span>}</div>
    {fleet?.robots.length ? <div className="robot-list">
      {fleet.robots.map((robot) => <button key={robot.robot_id} type="button" onClick={() => onSelect(robot.robot_id)}
        className="card robot-card" aria-pressed={selected === robot.robot_id} aria-label={`Robot seç: ${robot.robot_id}`}>
        <div className="robot-card-top"><span className="robot-icon"><Bot size={20} /></span>
          <div><strong>{robot.robot_id}</strong><p>{robot.state ? labels[robot.state] : "Durum bilinmiyor"}</p></div>
          <ReliabilityBadge value={robotReliability(robot, connected)} /><ChevronRight size={16} className="card-chevron" /></div>
        <Battery robot={robot} connected={connected} />
        <div className="robot-card-task"><span>Aktif görev</span><strong>{robot.active_task_id ?? "—"}</strong></div>
      </button>)}
    </div> : <div className="card"><EmptyState title="Robot kaydı yok" detail="Yetkili filo snapshot’ı bekleniyor." /></div>}
  </section>;
}

export function TaskList({ fleet }: { fleet: Fleet | null }) {
  const tasks = fleet?.tasks ?? [];
  return <section className="card table-panel">
    <div className="card-heading"><div><h2>Taşıma görevleri</h2><p>Fleet Manager görev ve sahiplik kayıtları</p></div>
      {fleet && <span className="tag">{tasks.length} / {fleet.task_counts.total} kayıt</span>}</div>
    {tasks.length ? <div className="table-scroll"><table><thead><tr>
      <th>Görev</th><th>Durum</th><th>Öncelik</th><th>Alım</th><th>Bırakma</th><th>Robot</th><th>Kuyruk zamanı¹</th>
    </tr></thead><tbody>{tasks.map((task) => <tr key={task.task_id}>
      <th scope="row">{task.task_id}</th><td><span className={`status-badge ${task.status.toLowerCase()}`}>{labels[task.status] ?? task.status}</span>
        {task.review_hold && <small className="review">İnceleme bekliyor</small>}</td>
      <td>{labels[task.priority]}</td><td>{poseLabel(task.pickup)}</td><td>{poseLabel(task.dropoff)}</td>
      <td>{task.assigned_robot_id ?? "—"}</td><td>{task.created_at_source_seconds === null ? "—"
        : `${displayNumber(task.created_at_source_seconds, 2)} sn`}</td>
    </tr>)}</tbody></table></div> : <EmptyState title="Görev kaydı yok" detail="Taşıma görevleri yetkili kaynağa ulaştığında burada görünür." />}
    {tasks.length > 0 && <p className="table-footnote">¹ Kaynakta saklanan ham zaman. Takvim saati olarak yorumlanmaz.</p>}
  </section>;
}

export function StationOverview({ fleet, connected }: { fleet: Fleet | null; connected: boolean }) {
  const stations = fleet?.stations ?? [];
  return <section className="card table-panel">
    <div className="card-heading"><div><h2>İstasyonlar ve şarj</h2><p>Rezervasyon yöneticisinin sahiplik kayıtları</p></div>
      {fleet && <span className="tag">{stations.length} istasyon</span>}</div>
    {stations.length ? <div className="table-scroll"><table><thead><tr>
      <th>İstasyon</th><th>Tip</th><th>Rezervasyon</th><th>Rezerve eden</th><th>İşgal eden</th><th>Şarj</th><th>Konum</th>
    </tr></thead><tbody>{stations.map((station) => <tr key={station.station_id}>
      <th scope="row">{station.station_id}</th>
      <td>{station.station_type === "CHARGING" ? "Şarj" : labels[station.station_type]}</td>
      <td><span className={`status-badge ${station.state.toLowerCase()}`}>{labels[station.state]}</span></td>
      <td>{station.reserved_by_robot_id ?? "—"}</td><td>{station.occupied_by_robot_id ?? "—"}</td>
      <td>{connected || station.charging === "NOT_APPLICABLE" ? labels[station.charging] : "Kullanılamıyor"}
        {connected && station.charging_robot_id && <small>{station.charging_robot_id}</small>}</td>
      <td>{poseLabel(station.pose)}</td>
    </tr>)}</tbody></table></div> : <EmptyState title="İstasyon kaydı yok" detail="Doğrulanmış filo konfigürasyonu bekleniyor." />}
    <p className="table-footnote">Anlık şarj kuyruğu sırası kullanılamıyor.</p>
  </section>;
}
