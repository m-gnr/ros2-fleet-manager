import { Box, Crosshair, Layers, Maximize, Orbit, RotateCcw, Scan } from "lucide-react";
import { Component, lazy, Suspense, useRef, useState, type ReactNode } from "react";
import { cameraLabels, resetCamera, selectCamera, type CameraCommand, type CameraMode } from "./scene/camera";
import type { Fleet as SceneView } from "./scene/fleet";
import { robotColor } from "./scene/presentation";
import type { RouteOptions } from "./scene/routes";
import type { SceneFeed } from "./scene/sceneFeed";

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

export function ScenePanel({ feed, view, robotIds, selected, onSelect }: {
  feed: SceneFeed; view: SceneView; robotIds: string[]; selected?: string; onSelect: (id: string) => void;
}) {
  const [command, setCommand] = useState<CameraCommand>({ mode: "free", reset: 0 });
  const [lowQuality, setLowQuality] = useState(false);
  const [routes, setRoutes] = useState<RouteOptions>({ plan: true, trail: true, selectedOnly: false, highlight: false });
  const labels = useRef(new Map<string, HTMLSpanElement>()).current;
  const live = robotIds.filter((id) => view.robots.get(id)?.status === "LIVE").length;

  function chooseMode(mode: CameraMode) {
    setCommand((current) => selectCamera(current, mode));
  }

  return <section className="card scene-panel" aria-labelledby="scene-heading">
    <div className="card-heading">
      <div className="scene-heading"><span className="scene-icon"><Box size={17} /></span>
        <div><h2 id="scene-heading">Depo görünümü</h2><p>ROS TF · map çerçevesi</p></div></div>
      <span className="tag map-tag">TEMSİLİ 3D DEPO</span>
    </div>
    <div className="scene-viewport" aria-label="Etkileşimli 3D depo">
      <SceneBoundary>
        <Suspense fallback={<p className="scene-message" role="status">3D depo yükleniyor…</p>}>
          <Scene feed={feed} command={command} lowQuality={lowQuality} labels={labels}
            robotIds={robotIds} selected={selected} onSelect={onSelect} routes={routes} trace={trace} />
        </Suspense>
      </SceneBoundary>
      <div className="scene-labels">
        {robotIds.map((id, index) => {
          const status = view.robots.get(id)?.status ?? "NO_DATA";
          return <span key={id} ref={(node) => {
            if (node) labels.set(id, node);
            else labels.delete(id);
          }} hidden={!view.robots.get(id)?.pose} className={`scene-label ${status.toLowerCase()} ${id === selected ? "selected" : ""}`}>
            <i style={{ background: robotColor(index) }} />{id}<small>{status}</small>
          </span>;
        })}
      </div>
      <span className="scene-indicator"><i data-live={live > 0} />{live} / {robotIds.length} TF LIVE</span>
      <div className="scene-controls" aria-label="Kamera kontrolleri">
        {modes.map(([mode, Icon]) => <button type="button" key={mode} aria-pressed={command.mode === mode}
          aria-label={cameraLabels[mode]} title={cameraLabels[mode]} onClick={() => chooseMode(mode)}><Icon size={17} /></button>)}
        <button type="button" aria-label="Kamerayı sıfırla" title="Kamerayı sıfırla"
          onClick={() => setCommand(resetCamera)}><RotateCcw size={16} /></button>
      </div>
      <span className="scene-hint"><Scan size={13} /> Sürükle · sağ tuşla kaydır · kaydırarak yakınlaş</span>
    </div>
    <div className="scene-footer">
      <label><input type="checkbox" checked={routes.plan} onChange={(e) => setRoutes({ ...routes, plan: e.target.checked })} />
        <i className="plan-key" />Gözlemlenen Nav2 planı <small>Durum B</small></label>
      <label><input type="checkbox" checked={routes.trail} onChange={(e) => setRoutes({ ...routes, trail: e.target.checked })} />
        <i className="trail-key" />TF hareket izi</label>
      <label className="scene-quality"><input type="checkbox" checked={lowQuality} onChange={(e) => setLowQuality(e.target.checked)} />
        Düşük kalite</label>
    </div>
  </section>;
}
