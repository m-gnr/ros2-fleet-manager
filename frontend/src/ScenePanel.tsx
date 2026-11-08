import { Box, Crosshair, Layers, Maximize, Orbit, PackageCheck, PackageOpen, RotateCcw, Scan, SquareParking, Zap } from "lucide-react";
import { Component, Fragment, lazy, Suspense, useMemo, useRef, useState, type ReactNode } from "react";
import { cameraLabels, resetCamera, selectCamera, type CameraCommand, type CameraMode } from "./scene/camera";
import type { Fleet as SceneView } from "./scene/fleet";
import { robotColor } from "./scene/presentation";
import type { RouteOptions } from "./scene/routes";
import { markerDiameter } from "./scene/marker";
import type { SceneFeed } from "./scene/sceneFeed";

import type { Fleet } from "./fleet";
import { useGridLayout } from "./scene/useGridLayout";
import { operationLabels, operationPoints, pointStyle } from "./scene/operationPoints";

const Scene = lazy(() => import("./scene/Scene"));
const modes = [
  ["free", Orbit], ["follow", Crosshair], ["top", Layers], ["fit", Maximize],
] as const;
const pointIcons = { CHARGING: Zap, PARKING: SquareParking, pickup: PackageOpen, dropoff: PackageCheck, SAFE_WAITING: Box };
const shortTaskId = (id: string) => {
  const chars = Array.from(id);
  return chars.length > 13 ? `${chars.slice(0, 7).join("")}…${chars.slice(-4).join("")}` : id;
};
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
  const [routes, setRoutes] = useState<RouteOptions>({ plan: true, trail: true, selectedOnly: false, highlight: false });
  const markers = useRef(new Map<string, HTMLButtonElement>()).current;
  const labels = useRef(new Map<string, HTMLSpanElement>()).current;
  const pointLabels = useRef(new Map<string, HTMLSpanElement>()).current;
  const leaders = useRef(new Map<string, SVGLineElement>()).current;
  const profile = useGridLayout(fleet?.backend_session_id, fleet?.source_session_id);
  const layout = profile?.layout;
  const points = useMemo(() => operationPoints(fleet, selected, connected, layout), [fleet, selected, connected, layout]);
  const operationTags = useMemo(() => operationLabels(points, layout), [points, layout]);
  const live = robotIds.filter((id) => view.robots.get(id)?.status === "LIVE").length;

  function chooseMode(mode: CameraMode) {
    setCommand((current) => selectCamera(current, mode));
  }

  return <section className="card scene-panel" aria-labelledby="scene-heading">
    <div className="card-heading">
      <div className="scene-heading"><span className="scene-icon"><Box size={17} /></span>
        <div><h2 id="scene-heading">Depo görünümü</h2><p>ROS TF · map çerçevesi</p></div></div>
      <div className="scene-legend"><span className="tag map-tag">TEMSİLİ 3D DEPO</span>
        <small>{profile?.mismatch ? "Izgara profili filo snapshot’ıyla eşleşmedi." :
          "Raflar ve sınırlar görsel temsildir."}</small></div>
    </div>
    <div className="scene-viewport" aria-label="Etkileşimli 3D depo">
      <SceneBoundary>
        <Suspense fallback={<p className="scene-message" role="status">3D depo yükleniyor…</p>}>
          <Scene layout={layout} feed={feed} command={command} lowQuality={lowQuality} labels={labels} markers={markers}
            robotIds={robotIds} points={points} labelPoints={operationTags} pointLabels={pointLabels} leaders={leaders} selected={selected} onSelect={onSelect} routes={routes} trace={trace} />
        </Suspense>
      </SceneBoundary>
      <div className="scene-labels">
        <svg className="scene-leaders" aria-hidden="true">
          {operationTags.filter(tag => tag.leader).map(({ key, kind }) => <line key={key}
            data-leader={key} stroke={pointStyle[kind].color} ref={node => {
              if (node) leaders.set(key, node);
              else leaders.delete(key);
            }} />)}
        </svg>
        {robotIds.map((id, index) => {
          const status = view.robots.get(id)?.status ?? "NO_DATA";
          const isSelected = id === selected;
          const color = robotColor(index);
          return <Fragment key={id}>
            <button type="button" className={`scene-marker ${status.toLowerCase()}`} data-robot-id={id} tabIndex={-1}
              aria-label={`3D işaretiyle seç: ${id}`} aria-pressed={isSelected} title={`${id} · ${status}`}
              data-charging={points.some(point => point.chargingRobot === id) || undefined}
              style={{ color, width: markerDiameter, height: markerDiameter }} onClick={() => onSelect(id)}
              ref={(node) => { if (node) markers.set(id, node); else markers.delete(id); }}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 7l8 5-8 5 2-5z" fill="currentColor" /></svg>
            </button>
            <span data-robot-id={id} title={`${id} · ${status}`} ref={(node) => {
              if (node) labels.set(id, node);
              else labels.delete(id);
            }} className={`scene-label ${status.toLowerCase()} ${isSelected ? "selected" : ""}`}>
              <i style={{ background: color }} /><span>{id}</span>{(isSelected || status !== "LIVE") && <small>{status}</small>}
            </span>
          </Fragment>;
        })}
        {operationTags.map(({ key, id, kind, detail, owner, chargingRobot, groupText, compact }) => {
          const { name, color } = pointStyle[kind];
          const Icon = pointIcons[kind];
          const task = kind === "pickup" || kind === "dropoff";
          return <span key={key} className={groupText ? "scene-point-label grouped" : "scene-point-label"} data-operation-point={key} data-callout={compact ? "" : undefined} title={[name, groupText ?? id, detail, owner].filter(Boolean).join(" · ")}
            ref={(node) => { if (node) pointLabels.set(key, node); else pointLabels.delete(key); }}>
            <strong style={{ color }}><Icon size={12} aria-hidden="true" />{name}</strong> {groupText ? <>{compact && <small className="zone-summary">{compact}</small>}
              <small className={compact ? "zone-details" : undefined}>{groupText.split(" · ").map(member =>
                <span className="zone-member" key={member}>{member}</span>)}</small></> : task
              ? <span>{shortTaskId(id)}</span>
              : <small>{layout && <span>{id} · </span>}{chargingRobot ? "Aktif" : detail}</small>}
          </span>;
        })}
      </div>
      <span className="scene-indicator"><i data-live={live > 0} />{live} / {robotIds.length} TF LIVE</span>
      <span className="scene-hint"><Scan size={13} /> Sürükle · sağ tuşla kaydır · kaydırarak yakınlaş</span>
    </div>
    <div className="scene-footer">
      <label><input type="checkbox" checked={routes.plan} onChange={(e) => setRoutes({ ...routes, plan: e.target.checked })} />
        <i className="plan-key" />Gözlemlenen Nav2 planı <small>Durum B</small></label>
      <label><input type="checkbox" checked={routes.trail} onChange={(e) => setRoutes({ ...routes, trail: e.target.checked })} />
        <i className="trail-key" />TF hareket izi</label>
      <label className="scene-quality"><input type="checkbox" checked={lowQuality} onChange={(e) => setLowQuality(e.target.checked)} />
        Düşük kalite</label>
      <div className="scene-controls" aria-label="Kamera kontrolleri">
        {modes.map(([mode, Icon]) => <button type="button" key={mode} aria-pressed={command.mode === mode}
          aria-label={cameraLabels[mode]} title={cameraLabels[mode]} onClick={() => chooseMode(mode)}><Icon size={17} /></button>)}
        <button type="button" aria-label="Kamerayı sıfırla" title="Kamerayı sıfırla"
          onClick={() => setCommand(resetCamera)}><RotateCcw size={16} /></button>
      </div>
    </div>
  </section>;
}
