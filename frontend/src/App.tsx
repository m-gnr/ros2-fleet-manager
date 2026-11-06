import { useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowUpRight, BatteryCharging, Bot, ClipboardList, Grid2X2, LayoutDashboard,
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

function Metric({ label, value, detail, icon: Icon, tone }: {
  label: string; value: number | null; detail: string; icon: typeof Bot; tone: string;
}) {
  return <div className="card metric"><span className={`metric-icon ${tone}`}><Icon size={18} /></span>
    <div><p>{label}</p><strong>{value ?? "—"}</strong><small>{detail}</small></div></div>;
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
      <aside className="sidebar">
        <a className="brand" href="#overview"><span className="brand-mark"><Network size={23} /></span>
          <span><strong>Fleet Manager</strong><small>ROS 2 OPERATIONS</small></span></a>
        <nav aria-label="Operasyon görünümleri">
          <p className="sidebar-label">ÇALIŞMA ALANI</p>
          {views.map(({ id, label, icon: Icon }) => <a href={`#${id}`} key={id}
            aria-current={view.id === id ? "page" : undefined}><Icon size={18} /><span>{label}</span></a>)}
        </nav>
        <div className="sidebar-footer"><span className="environment-icon"><Grid2X2 size={17} /></span>
          <div><strong>Operasyon ortamı</strong><small>C5 / Aşama 1.5</small></div></div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="top-breadcrumb"><span>ROS 2 Fleet Manager</span><i>/</i><strong>{view.label}</strong></div>
          <div className="top-status">
            <div className="sync"><span>Son eşitleme</span><time dateTime={sync?.toISOString()}>
              {sync ? sync.toLocaleTimeString("tr-TR") : "—"}</time></div>
            <span className={`connection ${connection.toLowerCase()}`} role="status">
              {connected ? <Signal size={15} /> : <WifiOff size={15} />}{connectionLabels[connection]}</span>
          </div>
        </header>
        <main id="workspace" tabIndex={-1} className="workspace">
          <div className="page-heading">
            <div><p className="eyebrow"><span /> FİLO OPERASYONLARI</p>
              <h1>{view.id === "overview" ? "Operasyon genel görünümü" : view.label}</h1>
              <p>{view.id === "overview" ? "Robotları, taşıma görevlerini ve istasyonları tek ekrandan izle."
                : "Fleet Manager tarafından yayınlanan yetkili operasyon verileri."}</p></div>
            <div className="readonly"><span><LockKeyhole size={14} /> Salt okunur</span><small>Görev oluşturma · sonraki aşama <ArrowUpRight size={13} /></small></div>
          </div>

          {error && <div className="connection-banner" role="alert"><WifiOff size={17} /><span>{error}
            {fleet && " Görev ve rezervasyon kayıtları son eşitlemeden."}</span>
            <button type="button" onClick={reconnect}><RotateCw size={15} /> Yeniden bağlan</button></div>}

          {view.id === "overview" && <>
            <section className="metrics" aria-label="Filo göstergeleri">
              <Metric label="Filo robotları" value={fleet?.robots.length ?? null} detail="Kayıtlı birim" icon={Bot} tone="mint" />
              <Metric label="Canlı telemetri" value={connected && fleet ? fleet.robots.filter((r) => r.telemetry === "LIVE").length : null}
                detail="Doğrulanmış kaynak" icon={Activity} tone="blue" />
              <Metric label="Aktif görevler" value={fleet?.task_counts.active ?? null} detail={connected ? "Taşıma ataması" : "Son eşitlemeden"} icon={ListTodo} tone="violet" />
              <Metric label="Şarjda" value={connected && fleet
                ? fleet.robots.some((r) => r.charging === "UNAVAILABLE") ? null : fleet.robots.filter((r) => r.charging === "CHARGING").length
                : null} detail="Doğrulanmış C4 ölçümü" icon={BatteryCharging} tone="amber" />
            </section>
            <div className="operations-grid">
              <ScenePanel feed={sceneFeed} view={scene} robotIds={robotIds} selected={activeId} onSelect={setSelectedId} />
              <RobotDetails robot={selected} robotId={activeId} tf={selectedTf} connected={connected} />
            </div>
            <RobotList fleet={fleet} connected={connected} selected={activeId} onSelect={setSelectedId} tfRobots={scene.robots} />
          </>}
          {view.id === "robots" && <div className="operations-grid robot-view">
            <RobotList fleet={fleet} connected={connected} selected={activeId} onSelect={setSelectedId} />
            <RobotDetails robot={selected} robotId={activeId} tf={selectedTf} connected={connected} />
          </div>}
          {view.id === "tasks" && <TaskList fleet={fleet} connected={connected} />}
          {view.id === "stations" && <StationOverview fleet={fleet} connected={connected} />}
          {!fleet && !error && view.id !== "overview" && <div role="status" className="initial-note">
            <EmptyState title="İlk eşitleme" detail="Fleet Manager snapshot’ı bekleniyor." /></div>}
          <footer className="workspace-footer"><span>ROS 2 FLEET MANAGER</span>
            <span>Operasyon paneli {fleet && `· Veri sözleşmesi v${fleet.schema_version}`}</span></footer>
        </main>
      </div>
    </div>
  );
}
