import { useEffect, useState, type FormEvent } from 'react';
import type { Fleet } from './fleet';
import { layoutResponse, type GridLayout } from './scene/gridLayout';

type Catalog = { session: string; layout: GridLayout; enabled: boolean; digest: string };

export function useTaskCatalog(fleet: Fleet | null) {
  const session = fleet ? fleet.backend_session_id + '/' + fleet.source_session_id : undefined;
  const [catalog, setCatalog] = useState<Catalog>();
  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    void fetch('/api/task-catalog', { signal: controller.signal }).then(async response => {
      if (!response.ok) return;
      const body = await response.json();
      const parsed = layoutResponse.safeParse(body);
      if (!parsed.success || !parsed.data.layout || controller.signal.aborted ||
        parsed.data.backend_session_id + '/' + parsed.data.source_session_id !== session) return;
      if (typeof body.profile_digest !== 'string') return;
      setCatalog({ session, layout: parsed.data.layout, enabled: body.enabled === true, digest: body.profile_digest });
    }).catch(() => {});
    return () => controller.abort();
  }, [session]);
  return catalog?.session === session ? catalog : undefined;
}

export function TaskComposer({ catalog, fleet, connected }: {
  catalog?: Catalog; fleet: Fleet | null; connected: boolean;
}) {
  const [pickup, setPickup] = useState('');
  const [dropoff, setDropoff] = useState('');
  const [priority, setPriority] = useState('LOW');
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const points = catalog?.layout.transfer_points ?? [];
  const examples = catalog?.layout.example_tasks ?? [];
  if (!catalog) return null;
  const accepts = (point: typeof points[number], role: 'pickup' | 'dropoff') =>
    (point.roles ?? [point.kind]).includes(role);
  const refreshRequest = () => { setRequestId(crypto.randomUUID()); setMessage(''); };

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!fleet || !catalog?.enabled || !connected || pending) return;
    setPending(true);
    setMessage('Görev kabulü bekleniyor…');
    try {
      const response = await fetch('/api/tasks', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: requestId, source_session_id: fleet.source_session_id,
          profile_digest: catalog.digest, pickup_id: pickup, dropoff_id: dropoff, priority }), signal: AbortSignal.timeout(8000),
      });
      const body = await response.json();
      if (!response.ok) {
        setMessage(`Görev kabul edilmedi veya kabulü doğrulanamadı. Aynı istekle tekrar deneyin. ${typeof body.detail === 'string' ? body.detail : ''}`);
        return;
      }
      setMessage(`Fleet Manager kabul etti · ${body.task_id}${body.outcome === 'DUPLICATE' ? ' · önceki istek' : ''}`);
      setRequestId(crypto.randomUUID());
    } catch {
      setMessage('Görev kabulü doğrulanamadı. Tekrar gönderimde aynı istek kimliği kullanılacak.');
    } finally { setPending(false); }
  }

  return <section className="card task-composer" aria-labelledby="task-create-heading">
    <div className="card-heading"><div><h2 id="task-create-heading">Görev oluştur</h2>
      <p>Alım ve teslim pozları çalışan filo profilinden alınır.</p></div></div>
    <form onSubmit={submit}>
      <fieldset disabled={pending || !connected || !catalog.enabled}>
        <label>Örnek rota<select defaultValue="" aria-label="Örnek rota" onChange={event => {
          const task = examples.find(task => task.id === event.target.value);
          if (task) { setPickup(task.pickup); setDropoff(task.dropoff); setPriority(task.priority); refreshRequest(); }
        }}><option value="">Rota seçin</option>{examples.map(task => <option key={task.id} value={task.id}>
          {task.pickup} → {task.dropoff}</option>)}</select></label>
        <label>Alım noktası<select required aria-label="Alım noktası" value={pickup} onChange={event => {
          setPickup(event.target.value); refreshRequest();
        }}><option value="">Nokta seçin</option>{points.filter(point => accepts(point, 'pickup')).map(point =>
          <option key={point.id} value={point.id}>{point.id}</option>)}</select></label>
        <label>Teslim noktası<select required aria-label="Teslim noktası" value={dropoff} onChange={event => {
          setDropoff(event.target.value); refreshRequest();
        }}><option value="">Nokta seçin</option>{points.filter(point => accepts(point, 'dropoff')).map(point =>
          <option key={point.id} value={point.id}>{point.id}</option>)}</select></label>
        <label>Öncelik<select aria-label="Öncelik" value={priority} onChange={event => {
          setPriority(event.target.value); refreshRequest();
        }}><option value="LOW">Düşük</option><option value="MEDIUM">Orta</option><option value="HIGH">Yüksek</option></select></label>
        <button type="submit" disabled={!pickup || !dropoff || pickup === dropoff}>Görevi gönder</button>
      </fieldset>
      {!catalog.enabled && <p>Görev komut bağlantısı açık değil. Fleet Manager görev girişini başlatın.</p>}
      {message && <p role="status">{message}</p>}
    </form>
  </section>;
}
