import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Scene } from './Scene'
import { stampLabel } from './telemetry'
import { useTelemetry } from './useTelemetry'
import './style.css'

const url = import.meta.env.VITE_VISUALIZER_WS_URL || 'ws://127.0.0.1:8765/telemetry'
const labels = {
  LIVE: 'Güncel ölçüm',
  NO_DATA: 'Ölçüm bekleniyor',
  STALE: 'Son geçerli poz tutuluyor',
  FRAME_ERROR: 'TF zinciri veya koordinat çerçevesi doğrulanamadı',
}

function App() {
  const [follow, setFollow] = useState(false)
  const { connection, status, pose, previous, session } = useTelemetry(url)
  const source = session?.source === 'tf' ? 'TF' : session ? 'Tanılama odometrisi' : '—'
  return <main className="layout">
    <header className="masthead">
      <div className="brand-mark" aria-hidden="true">◈</div>
      <div><p className="eyebrow">ROS 2 FLEET MANAGER</p><h1>Fleet Visualizer</h1></div>
      <span className="prototype">AŞAMA 1 · TEK ROBOT</span>
    </header>
    <section className="workspace">
      <section className="viewport" aria-label="Etkileşimli 3D depo">
        <div className="viewport-top">
          <div><p className="eyebrow">GÖRÜNÜM 01</p><h2>Depo sahnesi</h2></div>
          <button aria-pressed={follow} onClick={() => setFollow(!follow)}>Robotu takip et</button>
        </div>
        <Scene pose={pose} previous={status === 'LIVE' ? previous : undefined} follow={follow} />
        <div className="viewport-bottom"><span>↗ Turuncu ok robotun önünü gösterir</span><span>Sürükle · döndür / Kaydır · yakınlaş / Sağ tuş · kaydır</span></div>
      </section>
      <aside className="panel" aria-label="Robot telemetrisi">
        <p className="eyebrow">SALT OKUNUR TELEMETRİ</p>
        <h2 data-testid="robot-id">{session?.robot_id ?? 'Robot bekleniyor'}</h2>
        <div className="indicators" aria-live="polite">
          <div><span>WebSocket</span><strong data-testid="connection" data-state={connection}>{connection}</strong></div>
          <div><span>ROS verisi</span><strong data-testid="freshness" data-state={status}>{status}</strong></div>
          <p>{labels[status]}</p>
        </div>
        <dl className="metrics">
          <div><dt>X <small>m</small></dt><dd>{pose?.x.toFixed(3) ?? '—'}</dd></div>
          <div><dt>Y <small>m</small></dt><dd>{pose?.y.toFixed(3) ?? '—'}</dd></div>
          <div><dt>Yaw <small>rad</small></dt><dd>{pose?.yaw.toFixed(3) ?? '—'}</dd></div>
        </dl>
        <dl className="details">
          <div><dt>Çerçeve</dt><dd>{session?.frame_id ?? '—'}</dd></div>
          <div><dt>Kaynak</dt><dd>{source}</dd></div>
          <div><dt>Son ölçüm</dt><dd data-testid="stamp">{pose ? stampLabel(pose.stamp_ns) + ' sn' : '—'}</dd></div>
        </dl>
        <p className="clock">ROS simülasyon saati · /clock</p>
      </aside>
    </section>
    <footer>Gazebo Fortress <span>·</span> ROS 2 Humble <span>·</span> Yerel görselleştirme</footer>
  </main>
}

createRoot(document.getElementById('root')!).render(<App />)
