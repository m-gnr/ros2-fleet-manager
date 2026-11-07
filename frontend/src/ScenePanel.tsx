import { Box, Crosshair, Layers, Maximize, Orbit, PackageCheck, PackageOpen, RotateCcw, Scan, SquareParking, Zap } from "lucide-react";
import { Component, Fragment, lazy, Suspense, useMemo, useRef, useState, type ReactNode } from "react";
import { cameraLabels, resetCamera, selectCamera, type CameraCommand, type CameraMode } from "./scene/camera";
import type { Fleet as SceneView } from "./scene/fleet";
import { robotColor } from "./scene/presentation";
import type { RouteOptions } from "./scene/routes";
import { markerDiameter } from "./scene/marker";
import type { SceneFeed } from "./scene/sceneFeed";

import type { Fleet } from "./fleet";
import { operationPoints, pointStyle } from "./scene/operationPoints";

const Scene = lazy(() => import("./scene/Scene"));
const modes = [
  ["free", Orbit], ["follow", Crosshair], ["top", Layers], ["fit", Maximize],
] as const;
const pointIcons = { CHARGING: Zap, PARKING: SquareParking, pickup: PackageOpen, dropoff: PackageCheck, SAFE_WAITING: Box };
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
  const points = useMemo(() => operationPoints(fleet, selected, connected), [fleet, selected, connected]);
  const live = robotIds.filter((id) => view.robots.get(id)?.status === "LIVE").length;

  function chooseMode(mode: CameraMode) {
    setCommand((current) => selectCamera(current, mode));
  }

  return <section className="card scene-panel" aria-labelledby="scene-heading">
    <div className="card-heading">
      <div className="scene-heading"><span className="scene-icon"><Box size={17} /></span>
        <div><h2 id="scene-heading">Depo görünümü</h2><p>ROS TF · map çerçevesi</p></div></div>
      <div className="scene-legend"><span className="tag map-tag">TEMSİLİ 3D DEPO</span>
        <small>Raflar ve sınırlar görsel temsildir.</small></div>
    </div>
    <div className="scene-viewport" aria-label="Etkileşimli 3D depo">
      <SceneBoundary>
        <Suspense fallback={<p className="scene-message" role="status">3D depo yükleniyor…</p>}>
          <Scene feed={feed} command={command} lowQuality={lowQuality} labels={labels} markers={markers}
            robotIds={robotIds} points={points} pointLabels={pointLabels} selected={selected} onSelect={onSelect} routes={routes} trace={trace} />
        </Suspense>
      </SceneBoundary>
      <div className="scene-labels">
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
            <span data-robot-id={id} title={id} ref={(node) => {
              if (node) labels.set(id, node);
              else labels.delete(id);
            }} className={`scene-label ${status.toLowerCase()} ${isSelected ? "selected" : ""}`}>
              <i style={{ background: color }} /><span>{id}</span><small>{status}</small>
            </span>
          </Fragment>;
        })}
        {points.map(({ key, id, kind, detail, owner }) => {
          const { name, color } = pointStyle[kind];
          const Icon = pointIcons[kind];
          return <span key={key} className="scene-point-label" data-operation-point={key} title={[name, id, detail, owner].filter(Boolean).join(" · ")}
            ref={(node) => { if (node) pointLabels.set(key, node); else pointLabels.delete(key); }}>
            <strong style={{ color }}><Icon size={12} aria-hidden="true" />{name}</strong> <span>{id}</span>{detail && <small>{detail}</small>}{owner && <small>{owner}</small>}
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
