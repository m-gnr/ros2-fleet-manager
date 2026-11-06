import { Component, lazy, Suspense, useMemo, useRef, useState, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { cameraLabels, cameraModes, resetCamera, selectCamera, type CameraCommand } from './camera'
import { freshnessLabels, robotColor, schematicLabel, telemetryFields } from './presentation'
import { initial, stampLabel, type Telemetry } from './telemetry'
import type { Fleet } from './fleet'
import { useTelemetry } from './useTelemetry'
import './style.css'

const Scene = lazy(() => import('./Scene'))
const url = import.meta.env.VITE_VISUALIZER_WS_URL || 'ws://127.0.0.1:8765/telemetry/fleet'
const options = new URLSearchParams(window.location.search)

const iconPaths = {
  warehouse: 'M3 9l9-5 9 5v11H3z M8 20v-8h8v8 M8 16h8 M6 9h12',
  free: 'M12 3l9 5v8l-9 5-9-5V8z M3 8l9 5 9-5 M12 13v8',
  follow: 'M12 8v8 M8 12h8 M12 3v2 M12 19v2 M3 12h2 M19 12h2 M19 12a7 7 0 1 1-14 0 7 7 0 0 1 14 0',
  top: 'M4 4h16v16H4z M4 9h16 M9 9v11 M14 9v11',
  fit: 'M9 4H4v5 M15 4h5v5 M20 15v5h-5 M4 15v5h5 M8 12h8',
  reset: 'M3 4v6h6 M3 10a9 9 0 1 1 2 8',
}

function Icon({ name }: { name: keyof typeof iconPaths }) {
  return <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true" fill="none"
    stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round">
    <path d={iconPaths[name]} />
  </svg>
}

class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed
      ? <p className="scene-message" role="alert">3D sahne açılamadı. Chrome WebGL desteğini kontrol edin.</p>
      : this.props.children
  }
}

function StateBadge({ kind, value }: { kind: string; value: string }) {
  const symbol = value === 'LIVE' || value === 'CONNECTED' ? '●' : value === 'NO_DATA' ? '○' : '▲'
  return <strong className="state-badge" data-state={value}>
    <span aria-hidden="true">{symbol}</span><span data-testid={kind}>{value}</span>
  </strong>
}

function TelemetryPanel({ fleet, selected, onSelect, mode }: {
  fleet: Fleet; selected?: string; onSelect: (id: string) => void; mode: CameraCommand['mode']
}) {
  const view = (selected && fleet.robots.get(selected)) || initial
  const { status } = view
  const { connection } = fleet
  const fields = telemetryFields(view)
  return <aside className="panel" aria-label="Robot telemetrisi">
    <div className="panel-head">
      <p className="eyebrow">02 / TELEMETRİ</p>
      <h2>Robot verisi</h2>
    </div>
    <ul className="fleet-list" aria-label="Filo robotları">
      {[...fleet.robots].map(([id, robot]) => <li key={id}>
        <button type="button" aria-pressed={id === selected} onClick={() => onSelect(id)}>
          <span><strong>{id}</strong><small>{robot.pose ? stampLabel(robot.pose.stamp_ns) + ' sn' : '—'}</small></span>
          <StateBadge kind={`freshness-${id}`} value={robot.status} />
        </button>
      </li>)}
    </ul>
    <div className="unit-card">
      <div className="unit-icon" aria-hidden="true"><Icon name="follow" /></div>
      <div><p className="subtle">SEÇİLİ ROBOT</p><p className="unit-id" data-testid="robot-id">{selected ?? fields.robot}</p></div>
    </div>
    <section className="signals" aria-label="Bağlantı ve tazelik" aria-live="polite">
      <div><span>WebSocket</span><StateBadge kind="connection" value={connection} /></div>
      <div><span>ROS tazeliği</span><StateBadge kind="freshness" value={status} /></div>
      <p>{freshnessLabels[status]}</p>
    </section>
    <section className="readings" aria-label="ROS pozu">
      <p className="subtle">SON DOĞRULANAN POZ</p>
      <dl className="metrics">
        <div><dt>X <small>m</small></dt><dd>{fields.x}</dd></div>
        <div><dt>Y <small>m</small></dt><dd>{fields.y}</dd></div>
        <div><dt>Yaw <small>rad</small></dt><dd>{fields.yaw}</dd></div>
      </dl>
      <dl className="details">
        <div><dt>Poz kaynağı</dt><dd>{fields.source}</dd></div>
        <div><dt>Çerçeve</dt><dd>{fields.frame}</dd></div>
        <div><dt>Kamera</dt><dd>{cameraLabels[mode]}</dd></div>
        <div><dt>Son ölçüm</dt><dd data-testid="stamp">{fields.stamp}</dd></div>
      </dl>
      <p className="clock">ROS simülasyon saati <code>/clock</code></p>
    </section>
  </aside>
}

function App() {
  const [command, setCommand] = useState<CameraCommand>({ mode: 'free', reset: 0 })
  const [lowQuality, setLowQuality] = useState(options.get('quality') === 'low')
  const { view, feed } = useTelemetry(url)
  const [choice, setChoice] = useState<string>()
  const selected = choice && view.robots.has(choice) ? choice : view.robots.keys().next().value
  const roster = view.roster ?? view.robots
  const robotIds = useMemo(() => [...roster.keys()], [roster])
  const labels = useRef(new Map<string, HTMLSpanElement>()).current
  return <main className="layout">
    <header className="masthead">
      <div className="brand-mark"><Icon name="warehouse" /></div>
      <div><p className="eyebrow">ROS 2 FLEET MANAGER</p><h1>Fleet Visualizer</h1></div>
      <div className="prototype"><span aria-hidden="true">◇</span> SALT OKUNUR <span className="edition">/ AŞAMA 03</span></div>
    </header>
    <section className="workspace">
      <section className="viewport" aria-label="Etkileşimli 3D depo">
        <div className="viewport-top">
          <div><p className="eyebrow">01 / GÖRÜNÜM</p><h2>Depo sahnesi</h2></div>
          <div className="quality-control">
            <label htmlFor="quality">Görsel kalite</label>
            <select id="quality" value={lowQuality ? 'low' : 'standard'}
              onChange={event => setLowQuality(event.target.value === 'low')}>
              <option value="standard">Standart</option>
              <option value="low">Düşük</option>
            </select>
          </div>
        </div>
        <div className="stage">
          <SceneBoundary>
            <Suspense fallback={<p className="scene-message" role="status">3D sahne yükleniyor…</p>}>
              <Scene feed={feed} command={command} lowQuality={lowQuality} labels={labels} robotIds={robotIds} selected={selected} onSelect={setChoice} trace={options.has('trace')} />
            </Suspense>
          </SceneBoundary>
          <div className="stage-overlay">
            <span className="schematic" data-testid="schematic"><span aria-hidden="true">◇</span> {schematicLabel}</span>
            <span className="scale"><span aria-hidden="true">▦</span> 1 m ızgara</span>
          </div>
          {robotIds.map((id, index) => <span key={id} className="robot-label"
            data-robot-id={id} data-selected={id === selected} style={{ borderColor: robotColor(index) }}
            ref={node => { if (node) labels.set(id, node); else labels.delete(id) }} hidden aria-hidden="true">{id}</span>)}
          <div className="camera-toolbar" role="group" aria-label="Kamera modu">
            {cameraModes.map(mode => <button key={mode} aria-pressed={command.mode === mode}
              onClick={() => setCommand(current => selectCamera(current, mode))}>
              <Icon name={mode} />{cameraLabels[mode]}
            </button>)}
            <button aria-label="Kamerayı sıfırla" onClick={() => setCommand(resetCamera)}>
              <Icon name="reset" /><span>Sıfırla</span>
            </button>
          </div>
        </div>
        <div className="viewport-bottom">
          <span className="heading-key"><span aria-hidden="true">▲</span> Robotun önü</span>
          <span>Sürükle · Orbit / Sağ tuş · Pan / Tekerlek · Zoom</span>
        </div>
      </section>
      <TelemetryPanel fleet={view} selected={selected} onSelect={setChoice} mode={command.mode} />
    </section>
    <footer><span>ROS 2 Humble <b>·</b> Gazebo Fortress</span><span>Deneysel görselleştirme <b>·</b> Filo</span></footer>
  </main>
}

createRoot(document.getElementById('root')!).render(<App />)
