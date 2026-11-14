import { z } from 'zod';
import { useEffect, useState } from 'react';

const state = z.object({
  robot_id: z.string(), session_id: z.string(), revision: z.number(),
  soc_percent: z.number(), energy_wh: z.number(), capacity_wh: z.number(),
  mode: z.enum(['NORMAL', 'FAST']), discharge_minutes: z.number(), charge_minutes: z.number(),
  idle_power_w: z.number(), charge_power_w: z.number(), consumption_wh_per_meter: z.number(),
});
const inventory = z.object({ enabled: z.boolean(), robots: z.array(z.object({
  robot_id: z.string(), namespace: z.string(), available: z.boolean(), state: state.optional(), error: z.string().optional(),
})) });
export type BatteryInventory = z.infer<typeof inventory>;
export type Settings = { soc_percent?: number; mode: 'NORMAL' | 'FAST'; discharge_minutes: number; charge_minutes: number };

export function useBatteryControl(token: string) {
  const [data, setData] = useState<BatteryInventory>();
  const [updated, setUpdated] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setData(undefined);
    setError('');
    if (!token) return;
    let active = true;
    const abort = new AbortController();
    async function poll() {
      try {
        const response = await fetch('/api/sim/batteries', { headers: { Authorization: `Bearer ${token}` },
          signal: AbortSignal.any([abort.signal, AbortSignal.timeout(6000)]) });
        if (!response.ok) throw Error(response.status === 404 ? 'Simülasyon kontrolü kapalı.' : 'Kontrol erişimi veya servisi kullanılamıyor.');
        const result = inventory.parse(await response.json());
        if (active) { setData(result); setUpdated(new Date().toLocaleTimeString('tr-TR')); setError(''); }
      } catch (reason) {
        if (active) { setData(undefined); setError(reason instanceof Error ? reason.message : 'Kontrol bağlantısı kesildi.'); }
      }
      if (active) timer = window.setTimeout(() => void poll(), 1500);
    }
    let timer: number;
    void poll();
    return () => { active = false; abort.abort(); clearTimeout(timer); };
  }, [token]);

  async function apply(robotId: string | undefined, settings: Settings, safe: boolean, confirmBulk: boolean) {
    if (!data || busy) return undefined;
    const targets = robotId ? data.robots.filter(r => r.robot_id === robotId) : data.robots;
    const sessions = Object.fromEntries(targets.map(r => [r.robot_id, r.state?.session_id ?? 'unavailable']));
    setBusy(true);
    try {
      const response = await fetch('/api/sim/batteries', { method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ request_id: crypto.randomUUID(), robot_id: robotId ?? null,
          all_robots: !robotId, safe_test_environment: safe, confirm_bulk_soc: confirmBulk, sessions, ...settings }),
        signal: AbortSignal.timeout(12000) });
      const body = await response.json();
      if (!response.ok) throw Error(typeof body.detail === 'string' ? body.detail : 'İstek reddedildi.');
      return body.results.map((item: { robot_id: string; outcome: string; error?: string; readback?: z.infer<typeof state> }) => {
        const value = item.readback;
        return value ? `${item.robot_id}: doğrulandı · geri okunan %${value.soc_percent.toFixed(2)} · ${value.energy_wh.toFixed(3)} Wh · ${value.mode} · bekleme ${value.idle_power_w.toFixed(2)} W · şarj ${value.charge_power_w.toFixed(2)} W · ${value.discharge_minutes}/${value.charge_minutes} dk`
          : `${item.robot_id}: ${item.outcome === 'REJECTED' ? 'reddedildi' : 'sonuç doğrulanamadı'} · ${item.error ?? ''}`;
      }).join('\n');
    } catch (reason) {
      return `Uygulama doğrulanamadı; otomatik tekrar gönderilmedi. ${reason instanceof Error ? reason.message : ''}`;
    } finally { setBusy(false); }
  }
  return { data, updated, error, busy, apply };
}
