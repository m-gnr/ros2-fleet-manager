import { BatteryCharging, Bot, ChevronRight, CircleAlert, Radio } from "lucide-react";
import burgerPreview from "./scene/assets/burger-preview.webp";
import type { Telemetry } from "./scene/telemetry";
import type { Fleet, Reliability, Robot } from "./fleet";
import { currentBattery, displayNumber, labels, poseLabel, reliabilityLabel, robotReliability, simTime, telemetryAge } from "./presentation";

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

export function RobotDetails({ robot, robotId, tf, connected, preview, stations = [] }: {
  robot: Robot | undefined; robotId?: string; tf?: Telemetry; connected: boolean; preview?: boolean; stations?: Fleet["stations"];
}) {
  const pose = tf?.pose;
  const tfStatus = tf?.status ?? "NO_DATA";
  const plan = tf?.path;
  const age = robot && telemetryAge(robot.status_age_sec, robotReliability(robot, connected));
  const charging = connected && robot?.telemetry === "LIVE" && robot.battery_reliability === "LIVE" &&
    robot.charging === "CHARGING";
  const resources = robot && stations.filter(station => station.reserved_by_robot_id === robot.robot_id ||
    station.occupied_by_robot_id === robot.robot_id);
  const tfFields = robotId && <>
    <dl className="detail-grid tf-fields">
      <div><dt>TF poz durumu</dt><dd data-testid="tf-status">{tfStatus}</dd></div>
      <div><dt>Gözlemlenen Nav2 planı</dt><dd data-testid="plan-status">
        {plan?.points ? <>Güncel <small className="tag" title="Aktif Nav2 hedefiyle ilişki doğrulanmadı">Durum B</small></> : plan ? "Bayat / Gizli" : "Plan yok"}
      </dd></div>
    </dl>
    <details className="measurement-details">
      <summary>Konum ve ölçüm zamanı</summary>
      <dl className="detail-grid">
        <div><dt>TF konumu (x, y)</dt><dd>{poseLabel(pose ?? null)}</dd></div>
        <div><dt>TF yönü (yaw)</dt><dd>{pose ? `${displayNumber(pose.yaw, 3)} rad` : "Ölçüm yok"}</dd></div>
        <div><dt>TF ölçümü</dt><dd>{simTime(pose?.stamp_ns ?? null)}</dd></div>
        {robot && <>
          <div><dt>Son ürün pozu</dt><dd>{poseLabel(robot.pose)}</dd></div>
          <div><dt>Ürün ölçümü</dt><dd>{simTime(robot.status_sim_ns)}</dd></div>
          <div><dt>Batarya ölçümü</dt><dd>{simTime(robot.battery_sim_ns)}</dd></div>
        </>}
        {plan?.points && <div><dt>Nav2 plan ölçümü</dt><dd>{simTime(plan.stamp)}</dd></div>}
      </dl>
    </details>
  </>;
  return (
    <details className="card robot-details" open>
      <summary className="card-heading"><h2>Robot ayrıntıları</h2><ChevronRight size={16} /></summary>
      {robot ? <div className="details-body">
        <div className="detail-identity"><span className="robot-icon"><Bot size={20} /></span>
          <div><h3>{robot.robot_id}</h3><p>{robot.state ? `${labels[robot.state]}${connected && robot.telemetry === "LIVE" ? "" : " · son kayıt"}` : "Durum bilinmiyor"}</p></div>
          <ReliabilityBadge value={robotReliability(robot, connected)} /></div>
        <div className="details-scroll">
          {(!connected || robot.telemetry !== "LIVE" || robot.pose_reliability !== "LIVE" || robot.battery_reliability !== "LIVE") &&
            <div className="detail-warning"><CircleAlert size={16} /><span>
              {robot.telemetry === "BLOCKED" ? "Kaynak oturumu değişti. Telemetri blokeli."
                : !connected ? "Ürün akışı kesildi. Görev ve durum son eşitlemeden."
                  : "Ürün telemetrisi, poz veya batarya ölçümünün güncelliği doğrulanamadı."}
            </span></div>}
          <Battery robot={robot} connected={connected} />
          <dl className="detail-grid">
            <div><dt>{connected ? "Aktif görev" : "Görev · son eşitleme"}</dt><dd>{robot.active_task_id ?? "—"}</dd></div>
            <div><dt>Şarj</dt><dd>{connected ? labels[robot.charging] : "Kullanılamıyor"}
              {connected && robot.charging_station_id && <small>{robot.charging_station_id}</small>}</dd></div>
            {connected && robot.battery_energy_wh !== null && robot.battery_reliability === "LIVE" &&
              <div><dt>Kalan enerji</dt><dd>{displayNumber(robot.battery_energy_wh, 2)} Wh</dd></div>}
            <div><dt>Ürün telemetrisi</dt><dd title="Snapshot alınırken kaynağın bildirdiği alım yaşı">{age}</dd></div>
          </dl>
          {resources && resources.length > 0 && <details className="measurement-details">
            <summary>İstasyon sahipliği{connected ? "" : " · son eşitleme"}</summary>
            {resources.map(station => <dl className="detail-grid" key={station.station_id}>
              <div><dt>İstasyon</dt><dd>{station.station_id} · {labels[station.state]}</dd></div>
              <div><dt>Rezerve eden</dt><dd>{station.reserved_by_robot_id ?? "—"}</dd></div>
              <div><dt>İşgal eden</dt><dd>{station.occupied_by_robot_id ?? "—"}</dd></div>
            </dl>)}
          </details>}
          {tfFields}
          {preview && <figure className="robot-model-preview">
            <figcaption><small>MODEL ÖNİZLEMESİ</small><strong>TurtleBot3<br />Burger</strong>
              {charging && <span><BatteryCharging size={14} /> Şarj oluyor</span>}
            </figcaption>
            <img src={burgerPreview} alt="TurtleBot3 Burger modelinin izometrik görünümü" width={278} height={313} />
          </figure>}
        </div>
      </div> : robotId ? <div className="details-body"><h3>{robotId}</h3>
        <p className="tf-note">Ürün snapshot’ı bekleniyor.</p><div className="details-scroll">{tfFields}</div></div>
        : <EmptyState title="Robot verisi bekleniyor" detail="Filo eşitlendiğinde bir robot seçebilirsin." />}
    </details>
  );
}

export function RobotList({ fleet, connected, selected, onSelect, tfRobots }: {
  fleet: Fleet | null; connected: boolean; selected: string | undefined; onSelect: (id: string) => void; tfRobots?: ReadonlyMap<string, Telemetry>;
}) {
  return <section className="fleet-panel" aria-labelledby="robots-heading">
    <div className="section-heading"><h2 id="robots-heading">Filo robotları</h2>
      {fleet && <span className="tag">{fleet.robots.length} robot</span>}</div>
    {fleet?.robots.length ? <div className="robot-list">
      {fleet.robots.map((robot) => <button key={robot.robot_id} type="button" onClick={() => onSelect(robot.robot_id)}
        className="card robot-card" aria-pressed={selected === robot.robot_id} aria-label={`Robot seç: ${robot.robot_id}`}>
        <div className="robot-card-top"><span className="robot-icon"><Bot size={20} /></span>
          <div><strong>{robot.robot_id}</strong><p>{robot.state ? `${labels[robot.state]}${connected && robot.telemetry === "LIVE" ? "" : " · son kayıt"}` : "Durum bilinmiyor"}</p></div>
        </div>
        <Battery robot={robot} connected={connected} />
        <div className="robot-card-task"><span>{connected ? "Aktif görev" : "Görev · son eşitleme"}</span><strong>{robot.active_task_id ?? "—"}</strong></div>
        <div className="robot-card-status"><ReliabilityBadge value={robotReliability(robot, connected)} />
          {tfRobots && <small>TF · {tfRobots.get(robot.robot_id)?.status ?? "NO_DATA"}</small>}</div>
      </button>)}
    </div> : <div className="card"><EmptyState title="Robot kaydı yok" detail="Yetkili filo snapshot’ı bekleniyor." /></div>}
  </section>;
}

export function TaskList({ fleet, connected }: { fleet: Fleet | null; connected: boolean }) {
  const tasks = fleet?.tasks ?? [];
  return <section className="card table-panel">
    <div className="card-heading"><div><h2>Taşıma görevleri</h2><p>{connected ? "Fleet Manager görev ve sahiplik kayıtları" : "Görev kayıtları · son eşitleme"}</p></div>
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
    <div className="card-heading"><div><h2>İstasyonlar ve şarj</h2><p>{connected ? "Rezervasyon yöneticisinin sahiplik kayıtları" : "Rezervasyonlar · son eşitleme"}</p></div>
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
