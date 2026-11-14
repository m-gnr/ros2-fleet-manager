import { useState } from 'react';
import type { Fleet } from './fleet';
import { useBatteryControl } from './batteryControl';

export function BatterySimulation({ fleet, connected }: { fleet: Fleet | null; connected: boolean }) {
  const [token, setToken] = useState('');
  const { data, updated, error, busy, apply } = useBatteryControl(token);
  const [selected, setSelected] = useState('');
  const [soc, setSoc] = useState(100);
  const [changeSoc, setChangeSoc] = useState(false);
  const [mode, setMode] = useState<'NORMAL' | 'FAST'>('FAST');
  const [discharge, setDischarge] = useState(10);
  const [charge, setCharge] = useState(10);
  const [safe, setSafe] = useState(false);
  const [confirmBulk, setConfirmBulk] = useState(false);
  const [result, setResult] = useState('');
  const robots = data?.robots ?? [];
  const activeId = robots.some(r => r.robot_id === selected) ? selected : robots[0]?.robot_id;
  const active = robots.find(r => r.robot_id === activeId);
  const live = fleet?.robots.find(r => r.robot_id === activeId);
  const fresh = connected && live?.battery_reliability === 'LIVE';
  const valid = safe && Number.isFinite(soc) && soc >= 0 && soc <= 100 &&
    [discharge, charge].every(v => Number.isFinite(v) && v >= 1 && v <= 1440);

  async function submit(all: boolean) {
    setResult('Servis uygulaması ve geri okuma bekleniyor…');
    const response = await apply(all ? undefined : activeId,
      { soc_percent: changeSoc ? soc : undefined, mode, discharge_minutes: discharge, charge_minutes: charge }, safe, confirmBulk);
    if (response) setResult(response);
  }
  return <section className="card battery-simulation" aria-labelledby="battery-simulation-title">
    <div className="card-heading"><div><h2 id="battery-simulation-title">Batarya Simülasyonu</h2>
      <p>Yalnız güvenli simülasyon testleri. Politika eşikleri ve dock koşulları korunur.</p></div></div>
    <label>Simülasyon erişim anahtarı<input type="password" value={token} autoComplete="off"
      onChange={e => { setToken(e.target.value); setResult(''); }} placeholder="Yetkili yerel test anahtarı" /></label>
    {error && <p role="alert">{error}</p>}
    <fieldset disabled={busy || !data}>
      <label>Robot<select aria-label="Batarya robotu" value={activeId ?? ''} onChange={e => { setSelected(e.target.value); setResult(''); }}>
        {robots.map(r => <option key={r.robot_id} value={r.robot_id}>{r.robot_id}{r.available ? '' : ' · kontrol kapalı'}</option>)}
      </select></label>
      <p>Gerçek BatteryState telemetrisi: <strong>{fresh ? `${live.battery_soc_percent?.toFixed(2)}% · ${live.battery_energy_wh?.toFixed(3)} Wh` : 'Güncel veri yok'}</strong>
        {' · '}{connected ? live?.battery_reliability ?? 'NO_DATA' : 'Bağlantı kesildi'}</p>
      <p>Servis son okuması: {active?.state ? `${active.state.soc_percent.toFixed(2)}% · ${active.state.energy_wh.toFixed(3)} / ${active.state.capacity_wh} Wh · ${active.state.mode} · ${active.state.idle_power_w.toFixed(2)} W bekleme · ${active.state.charge_power_w.toFixed(2)} W şarj` : active?.error ?? 'Bekleniyor'}
        {' · Son güncelleme: '}{updated || '—'}</p>
      <label><input type="checkbox" checked={changeSoc} onChange={e => setChangeSoc(e.target.checked)} /> SoC değişikliğini dahil et</label>
      <label>İstenen SoC: %{soc}<input aria-label="İstenen SoC" type="range" min="0" max="100" step="1"
        disabled={!changeSoc} value={soc} onChange={e => setSoc(Number(e.target.value))} /></label>
      <div className="battery-presets">{[0, 25, 50, 80, 100].map(v => <button key={v} type="button" disabled={!changeSoc} onClick={() => setSoc(v)}>%{v}</button>)}</div>
      <label>Profil<select aria-label="Batarya profili" value={mode} onChange={e => setMode(e.target.value as typeof mode)}>
        <option value="NORMAL">Normal · mevcut simülasyon konfigürasyonu</option><option value="FAST">Hızlı Test</option></select></label>
      <label>Tükenme süresi (%100 → %25, dakika)<input aria-label="Tükenme süresi" type="number" min="1" max="1440" step="any"
        list="battery-minutes" disabled={mode !== 'FAST'} value={discharge} onChange={e => setDischarge(e.target.valueAsNumber)} /></label>
      <label>Şarj süresi (%25 → %80, dakika)<input aria-label="Şarj süresi" type="number" min="1" max="1440" step="any"
        list="battery-minutes" disabled={mode !== 'FAST'} value={charge} onChange={e => setCharge(e.target.valueAsNumber)} /></label>
      <datalist id="battery-minutes">{[5, 10, 15, 30].map(v => <option key={v} value={v} />)}</datalist>
      <p>Tükenme süresi hareketsiz robot içindir; hareket tüketimi ayrıca eklenir. Şarj fiziksel dock kanıtı gerektirir.</p>
      <label><input type="checkbox" checked={safe} onChange={e => setSafe(e.target.checked)} /> Güvenli test ortamında çalıştığımı onaylıyorum.</label>
      <label><input type="checkbox" checked={confirmBulk} onChange={e => setConfirmBulk(e.target.checked)} /> Tüm robotların SoC değerini değiştirmeyi açıkça onaylıyorum.</label>
      <div className="battery-presets"><button type="button" disabled={!valid || !active?.available || !fresh} onClick={() => void submit(false)}>Seçili robota uygula</button>
        <button type="button" disabled={!valid || !connected || !robots.length || (changeSoc && !confirmBulk)} onClick={() => void submit(true)}>Tüm robotlara uygula</button></div>
    </fieldset>
    <p>Toplu uygulama atomik değildir. Servis yanıtı canlı telemetrinin yerine geçmez.</p>
    {result && <pre className="battery-result" role="status">{result}</pre>}
  </section>;
}
