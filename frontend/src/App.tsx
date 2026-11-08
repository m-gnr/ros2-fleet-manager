import { useEffect, useMemo, useState } from "react";
import {
  Activity, BatteryCharging, Bot, ClipboardList, LayoutDashboard,
  ListTodo, LockKeyhole, Network, RotateCw, Signal, WifiOff,
} from "lucide-react";
import { EmptyState, RobotDetails, RobotList, StationOverview, TaskList } from "./Operations";
import { ScenePanel } from "./ScenePanel";
import { useFleet, type Connection } from "./useFleet";

const views = [
  { id: "overview", label: "Genel görünüm", icon: LayoutDashboard },
  { id: "robots", label: "Robotlar", icon: Bot },
  { id: "tasks", label: "Görevler", icon: ClipboardList },
  { id: "stations", label: "İstasyonlar / Şarj", icon: BatteryCharging },
] as const;
type View = (typeof views)[number];

const connectionLabels: Record<Connection, string> = {
  CONNECTING: "Bağlanıyor", CONNECTED: "Bağlı", RECONNECTING: "Yeniden bağlanıyor", DISCONNECTED: "Bağlantı kesildi",
};

function activeView() {
  return views.find((view) => `#${view.id}` === window.location.hash) ?? views[0];
}

function Metric({ label, value, detail, description, icon: Icon }: {
  label: string; value: number | null; detail?: string; description?: string; icon: typeof Bot;
}) {
  return <div className="metric" title={description}><dt><Icon size={15} aria-hidden="true" />{label}</dt>
    <dd><strong>{value ?? "—"}</strong>{detail && <small>{detail}</small>}</dd></div>;
}

export default function App() {
  const [view, setView] = useState<View>(activeView);
  const [selectedId, setSelectedId] = useState<string>();
  const { fleet, connection, error, scene, sceneFeed, reconnect } = useFleet();
  const connected = connection === "CONNECTED";
  const productIds = fleet?.robots.map((robot) => robot.robot_id).join("\0") ?? "";
  const robotIds = useMemo(() => [...new Set([
    ...(productIds ? productIds.split("\0") : []), ...(scene.roster ?? []),
  ])].sort(), [productIds, scene.roster]);
  const activeId = selectedId && robotIds.includes(selectedId) ? selectedId : robotIds[0];
  const selected = fleet?.robots.find((robot) => robot.robot_id === activeId);
  const selectedTf = activeId ? scene.robots.get(activeId) : undefined;
  const sync = fleet ? new Date(fleet.generated_at_utc) : null;

  useEffect(() => {
    const onHash = () => setView(activeView());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div className="shell">
      <a className="skip-link" href="#workspace">İçeriğe geç</a>
      <header className="topbar">
        <a className="brand" href="#overview"><span className="brand-mark"><Network size={19} /></span>
          <span>{view.id === "overview" ? <h1>Fleet Manager</h1> : <strong>Fleet Manager</strong>}
            <small>FİLO OPERASYONLARI</small></span></a>
        <nav aria-label="Operasyon görünümleri">
          {views.map(({ id, label, icon: Icon }) => <a href={`#${id}`} key={id}
            aria-current={view.id === id ? "page" : undefined}><Icon size={15} /><span>{label}</span></a>)}
        </nav>
        <div className="top-status">
          <div className="sync"><span>Son eşitleme</span><time dateTime={sync?.toISOString()}>
            {sync ? sync.toLocaleTimeString("tr-TR") : "—"}</time></div>
          <span className={`connection ${connection.toLowerCase()}`} role="status">
            {connected ? <Signal size={14} /> : <WifiOff size={14} />}
            <strong>{connectionLabels[connection]}</strong></span>
          <span className="tag readonly"><LockKeyhole size={13} /> SALT OKUNUR</span>
        </div>
      </header>
      <main id="workspace" tabIndex={-1} className={`workspace ${view.id === "overview" ? "overview" : ""}`}>
      {view.id !== "overview" && <div className="page-heading">
        <h1>{view.label}</h1><p>Fleet Manager tarafından yayınlanan yetkili operasyon verileri.</p>
      </div>}

      {error && <div className="connection-banner" role="alert"><WifiOff size={17} /><span>{error}
        {fleet && " Görev ve rezervasyon kayıtları son eşitlemeden."}</span>
        <button type="button" onClick={reconnect}><RotateCw size={15} /> Yeniden bağlan</button></div>}

      {view.id === "overview" && <>
        <dl className="card metrics" aria-label="Filo göstergeleri">
          <Metric label="Toplam robot" value={fleet?.robots.length ?? null} icon={Bot} />
          <Metric label="Canlı telemetri" value={connected && fleet ? fleet.robots.filter((r) => r.telemetry === "LIVE").length : null}
            description="Doğrulanmış kaynak. Canlı ürün telemetrisi bulunan robotların sayısı." icon={Activity} />
          <Metric label="Görevler" value={fleet?.task_counts.total ?? null}
            detail={fleet ? `${fleet.task_counts.active} aktif${connected ? "" : " · son eşitleme"}` : undefined} icon={ListTodo} />
          <Metric label="Şarjda" value={connected && fleet && !fleet.robots.some((r) => r.charging === "UNAVAILABLE")
            ? fleet.robots.filter((r) => r.charging === "CHARGING").length : null} description="Doğrulanmış C4 ölçümü. Şarj olduğu doğrulanan robotların sayısı." icon={BatteryCharging} />
        </dl>
        <div className="operations-grid">
          <ScenePanel fleet={fleet} connected={connected} feed={sceneFeed} view={scene} robotIds={robotIds} selected={activeId} onSelect={setSelectedId} />
          <RobotList fleet={fleet} connected={connected} selected={activeId} onSelect={setSelectedId} tfRobots={scene.robots} />
          <RobotDetails robot={selected} robotId={activeId} tf={selectedTf} stations={fleet?.stations} connected={connected} preview />
        </div>
      </>}
      {view.id === "robots" && <div className="operations-grid robot-view">
        <RobotList fleet={fleet} connected={connected} selected={activeId} onSelect={setSelectedId} />
        <RobotDetails robot={selected} robotId={activeId} tf={selectedTf} stations={fleet?.stations} connected={connected} />
      </div>}
      {view.id === "tasks" && <TaskList fleet={fleet} connected={connected} />}
      {view.id === "stations" && <StationOverview fleet={fleet} connected={connected} />}
      {!fleet && !error && view.id !== "overview" && <div role="status" className="initial-note">
        <EmptyState title="İlk eşitleme" detail="Fleet Manager snapshot’ı bekleniyor." /></div>}
      {view.id !== "overview" && <footer className="workspace-footer"><span>ROS 2 FLEET MANAGER</span>
        <span>Operasyon paneli {fleet && `· Veri sözleşmesi v${fleet.schema_version}`}</span></footer>}
      </main>
    </div>
  );
}
