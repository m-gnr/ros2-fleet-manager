import { Box, Crosshair, Layers, Maximize, Orbit, RotateCcw, Scan } from "lucide-react";
import { Component, Fragment, lazy, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { cameraLabels, resetCamera, selectCamera, type CameraCommand, type CameraMode } from "./scene/camera";
import type { Fleet as SceneView } from "./scene/fleet";
import { robotStateColor, robotVisualState } from "./scene/robotPresentation";
import type { RouteOptions } from "./scene/routes";
import { markerDiameter } from "./scene/marker";
import type { SceneFeed } from "./scene/sceneFeed";

import type { Fleet } from "./fleet";
import { useGridLayout } from "./scene/useGridLayout";
import { useCostmap } from "./scene/Costmap";
import { operationPoints } from "./scene/operationPoints";

const Scene = lazy(() => import("./scene/Scene"));
const modes = [
  ["free", Orbit], ["follow", Crosshair], ["top", Layers], ["fit", Maximize],
] as const;
const trace = new URLSearchParams(window.location.search).get("trace") === "1";

class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? <p className="scene-message" role="status">3D görünüm başlatılamadı.</p> : this.props.children;
  }
}

export function ScenePanel({ fleet, connected, feed, view, robotIds, selected, onSelect }: {
  fleet: Fleet | null; connected: boolean;
  feed: SceneFeed; view: SceneView; robotIds: string[]; selected?: string; onSelect: (id: string) => void;
}) {
  const [command, setCommand] = useState<CameraCommand>({ mode: "free", reset: 0 });
  const [lowQuality, setLowQuality] = useState(false);
  const [showExterior, setShowExterior] = useState(true);
  const [showCostmap, setShowCostmap] = useState(false);
  const [routes, setRoutes] = useState<RouteOptions>({ plan: true, trail: true, selectedOnly: false, highlight: false });
  const markers = useRef(new Map<string, HTMLButtonElement>()).current;
  const labels = useRef(new Map<string, HTMLSpanElement>()).current;
  const parkLabels = useRef(new Map<string, HTMLSpanElement>()).current;
  const tooltip = useRef<HTMLDivElement>(null);
  const [pointPopup, setPointPopup] = useState<{ key: string; pinned: boolean } | null>(null);
  const profile = useGridLayout(fleet?.backend_session_id, fleet?.source_session_id);
  const layout = profile?.layout;
  const costmap = useCostmap(showCostmap && layout ? fleet?.backend_session_id + '/' + fleet?.source_session_id : undefined);
  const points = useMemo(() => operationPoints(fleet, selected, connected, layout), [fleet, selected, connected, layout]);
  const robotStates = useMemo(() => new Map(robotIds.map(id => {
    const robot = fleet?.robots.find(item => item.robot_id === id);
    const reliable = connected && robot?.telemetry === 'LIVE';
    return [id, reliable ? robotVisualState(robot.state) : 'unknown'] as const;
  })), [connected, fleet, robotIds]);
  const popupPoint = points.find(point => point.key === pointPopup?.key);
  const popupRole = popupPoint?.kind === 'pickup' ? 'Alma' : popupPoint?.kind === 'dropoff' ? 'Bırakma' :
    popupPoint?.kind === 'neutral' ? 'Çift rollü' : popupPoint?.kind === 'unknown' ? 'Rol bilinmiyor' :
    popupPoint?.kind === 'CHARGING' ? 'Şarj alanı' : popupPoint?.kind === 'PARKING' ? 'Park alanı' : 'Güvenli bekleme';
  const live = robotIds.filter((id) => view.robots.get(id)?.status === "LIVE").length;

  useEffect(() => {
    const dismiss = (event: KeyboardEvent) => { if (event.key === 'Escape') setPointPopup(null); };
    window.addEventListener('keydown', dismiss);
    return () => window.removeEventListener('keydown', dismiss);
  }, []);
  useEffect(() => {
    if (pointPopup && !points.some(point => point.key === pointPopup.key)) setPointPopup(null);
  }, [pointPopup, points]);

  function chooseMode(mode: CameraMode) {
    setCommand((current) => selectCamera(current, mode));
  }

  return <section className="card scene-panel" aria-labelledby="scene-heading">
    <div className="card-heading">
      <div className="scene-heading"><span className="scene-icon"><Box size={17} /></span>
        <div><h2 id="scene-heading">Depo görünümü</h2><p>ROS TF · map çerçevesi</p></div></div>
      <div className="scene-legend"><span className="tag map-tag">{layout ? 'DOĞRULANMIŞ DEPO HARİTASI' : 'HARİTA BEKLENİYOR'}</span>
        <small>{profile?.mismatch ? "Izgara profili filo snapshot’ıyla eşleşmedi." :
          layout ? `Ortak YAML · ${profile.profileId} · ${profile.profileDigest.slice(0, 12)}` : "Seçili profil için doğrulanmış harita yok."}</small></div>
    </div>
    <div className="scene-viewport" aria-label="Etkileşimli 3D depo">
      {layout ? <>
        <SceneBoundary>
          <Suspense fallback={<p className="scene-message" role="status">3D depo yükleniyor…</p>}>
            <Scene showExterior={showExterior} layout={layout} costmap={showCostmap ? costmap : undefined} feed={feed} command={command} lowQuality={lowQuality} labels={labels} markers={markers} parkLabels={parkLabels}
              robotIds={robotIds} robotStates={robotStates} points={points} activePointKey={popupPoint?.key} tooltip={tooltip} selected={selected} onSelect={onSelect} routes={routes} trace={trace}
              onPointHover={key => setPointPopup(current => current?.pinned ? current : { key, pinned: false })}
              onPointLeave={key => setPointPopup(current => current?.key === key && !current.pinned ? null : current)}
              onPointClick={key => setPointPopup(current => current?.key === key && current.pinned ? null : { key, pinned: true })}
              onClearPoint={() => setPointPopup(null)} />
          </Suspense>
        </SceneBoundary>
      <div className="scene-labels">
        {points.filter(point => point.kind === 'PARKING').map(point =>
          <span key={point.key} className="scene-park-label" data-park-id={point.id}
            ref={node => { if (node) parkLabels.set(point.key, node); else parkLabels.delete(point.key); }}>
            {point.owner ?? point.id}
          </span>)}
        {robotIds.map((id, index) => {
          const status = view.robots.get(id)?.status ?? "NO_DATA";
          const isSelected = id === selected;
          const visualState = robotStates.get(id) ?? 'unknown';
          const color = robotStateColor(visualState);
          return <Fragment key={id}>
            <button type="button" className={`scene-marker ${status.toLowerCase()} state-${visualState}`} data-robot-id={id} data-robot-state={visualState} tabIndex={-1}
              aria-label={`3D işaretiyle seç: ${id}`} aria-pressed={isSelected} title={`${id} · ${status}`}
              style={{ color, width: markerDiameter, height: markerDiameter }} onClick={() => onSelect(id)}
              ref={(node) => { if (node) markers.set(id, node); else markers.delete(id); }}>
              <svg viewBox="0 0 36 36" aria-hidden="true">
                <circle cx="17" cy="18" r="10.5" fill="none" stroke="currentColor" />
                <path d="M28 14.5L35 18l-7 3.5z" fill="currentColor" />
              </svg>
            </button>
            <span data-robot-id={id} title={`${id} · ${status}`} ref={(node) => {
              if (node) labels.set(id, node);
              else labels.delete(id);
            }} className={`scene-label ${status.toLowerCase()} ${isSelected ? "selected" : ""}`}>
              <span>{id}</span>{(isSelected || status !== "LIVE") && <small>{status}</small>}
            </span>
          </Fragment>;
        })}
        {popupPoint && <div className="scene-point-tooltip" role="tooltip" data-operation-point={popupPoint.key} ref={tooltip}>
          <strong>{popupPoint.catalogId ?? popupPoint.id}</strong>
          <span>{popupRole}{popupPoint.catalogRoles?.length === 2 && popupPoint.kind !== 'neutral' ? ' · çift rollü nokta' : ''}</span>
          {popupPoint.detail && <small>Durum: {popupPoint.detail}</small>}
          {popupPoint.owner && <small>Robot: {popupPoint.owner}</small>}
        </div>}
      </div>
      <span className="scene-indicator" role="status"><i data-live={robotIds.length > 0 && live === robotIds.length} />
        {robotIds.length > 0 && live === robotIds.length ? `${live}/${robotIds.length} TF LIVE` : "WAITING FOR TF"}</span>
      </> : <p className="scene-message" role="status">Seçili depo profili için harita doğrulanamadı.</p>}
      {showCostmap && <span className="costmap-key">{costmap ? costmap.source === 'nav2_recorded'
        ? 'Nav2 global costmap · kayıt' : 'Üretilen statik harita' : 'Costmap bekleniyor'} · Engel / şişirme</span>}
      <span className="scene-hint"><Scan size={13} /> Sürükle · sağ tuşla kaydır · kaydırarak yakınlaş</span>
    </div>
    <div className="scene-footer">
      <label><input type="checkbox" checked={routes.plan} onChange={(e) => setRoutes({ ...routes, plan: e.target.checked })} />
        <i className="plan-key" />Gözlemlenen Nav2 planı <small>Durum B</small></label>
      <label><input type="checkbox" checked={routes.trail} onChange={(e) => setRoutes({ ...routes, trail: e.target.checked })} />
        <i className="trail-key" />TF hareket izi</label>
      {layout && <label><input type="checkbox" checked={showExterior}
        onChange={e => setShowExterior(e.target.checked)} />Çevreyi göster</label>}
      <label className="scene-quality"><input type="checkbox" checked={lowQuality} onChange={(e) => setLowQuality(e.target.checked)} />
        Düşük kalite</label>
      {layout && <label><input type="checkbox" checked={showCostmap} onChange={e => {
        setShowCostmap(e.target.checked);
        if (e.target.checked) chooseMode('top');
      }} />Costmap katmanı</label>}
      <div className="scene-controls" aria-label="Kamera kontrolleri">
        {modes.map(([mode, Icon]) => <button type="button" key={mode} aria-pressed={command.mode === mode}
          aria-label={cameraLabels[mode]} title={cameraLabels[mode]} onClick={() => chooseMode(mode)}><Icon size={17} /></button>)}
        <button type="button" aria-label="Kamerayı sıfırla" title="Kamerayı sıfırla"
          onClick={() => setCommand(resetCamera)}><RotateCcw size={16} /></button>
      </div>
    </div>
  </section>;
}
