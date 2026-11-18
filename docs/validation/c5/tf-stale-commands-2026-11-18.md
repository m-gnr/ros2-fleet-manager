# C5 TF STALE — komut ve ham ölçüm eki

## Kapsam ve izolasyon

18 Kasım 2026 yerel saatindeki koşular `/Users/murat/develop/ros2-fleet-manager-demo` içinden, `9d67bd98ee6a9b7fce5e7335941634e728b80075` (`origin/main`) temelinde `codex/telemetry-stale-fix` dalında yapıldı. Başlangıçta çalışan Docker container yoktu. Her koşunun kendi `C5_SESSION_ID`, `ROS_DOMAIN_ID`, `IGN_PARTITION`, API ve UI portu vardı. Launcher kapanışta kendi container'ını ve Vite sürecini temizledi; sonunda `docker ps --format '{{.Names}}'` boştu. Commit ve push yapılmadı.

Üç robot profili `config/fleet.warehouse-30x18.yaml` idi. Bir ve iki robot profilleri yalnız bu YAML'nin `robots` listesinin ilk 1/2 öğesini taşıyan geçici test dosyalarıydı; koşulardan sonra silindi. `C5_DEMO_PROFILE` yalnız aynı workspace'in `config/` altındaki doğrulanmış YAML'yi kabul eder. Bu override ürünün varsayılan profilini değiştirmez.

## Canlı oturumlar

| Evre | Robot | Oturum | ROS domain | API / UI portu | Ham relay/API | Ham Chrome |
|---|---:|---|---:|---|---|---|
| Önce | 1 | `c5-demo-20261117T204922Z-93b9fc07cdc4` | 209 | 21520 / 21522 | [baseline-1.jsonl](tf-stale-2026-11-17/baseline-1.jsonl) | [chrome-1.jsonl](tf-stale-2026-11-17/chrome-1.jsonl) |
| Önce | 2 | `c5-demo-20261117T205111Z-14bbecbf86dc` | 231 | 21540 / 21542 | [baseline-2.jsonl](tf-stale-2026-11-17/baseline-2.jsonl) | [chrome-2.jsonl](tf-stale-2026-11-17/chrome-2.jsonl) |
| Önce | 3 | `c5-demo-20261117T205406Z-51896ef9efb7` | 205 | 21560 / 21562 | [baseline-3.jsonl](tf-stale-2026-11-17/baseline-3.jsonl) | [chrome-3.jsonl](tf-stale-2026-11-17/chrome-3.jsonl) |
| Sonra | 1 | `c5-demo-20261117T210113Z-6eceae2b93a4` | 208 | 21580 / 21582 | [after-1.jsonl](tf-stale-2026-11-17/after-1.jsonl) | [chrome-after-1.jsonl](tf-stale-2026-11-17/chrome-after-1.jsonl) |
| Sonra | 2 | `c5-demo-20261117T210259Z-3a36752f39aa` | 230 | 21640 / 21642 | [after-2.jsonl](tf-stale-2026-11-17/after-2.jsonl) | [chrome-after-2.jsonl](tf-stale-2026-11-17/chrome-after-2.jsonl) |
| Sonra | 3 | `c5-demo-20261117T211055Z-33bde2dec7ef` | 211 | 21680 / 21682 | [after-3.jsonl](tf-stale-2026-11-17/after-3.jsonl), [hareket penceresi](tf-stale-2026-11-17/after-3-moving.jsonl) | [chrome-after-3.jsonl](tf-stale-2026-11-17/chrome-after-3.jsonl), [hareket penceresi](tf-stale-2026-11-17/chrome-after-3-moving.jsonl) |

İlk üç robot sonrası tekrar 300 saniyede readiness kapısını geçemedi (`current_status=WAITING`); launcher kendi container'ını temizledi ve görev gönderilmedi. Yukarıdaki sonraki üç robot oturumu ikinci denemedir; yalnız iki robot eşzamanlı `EXECUTING` oldu.

## Kullanılan araçlar ve ölçüm sınırı

Her oturum `./scripts/start_demo.sh` ile başlatıldı. `scripts/c5_telemetry_probe.py SESSION_DIR OUTPUT --seconds 50` API'yi 250 ms aralıklarla yokladı, ayrı `/ws/fleet` istemcisinde scene ve ürün paketlerini zaman damgasıyla kaydetti. `node scripts/c5_chrome_probe.mjs http://127.0.0.1:UI_PORT OUTPUT 50` gerçek headless Chrome'da WebSocket, DOM STALE ve long task olaylarını kaydetti. Python probe için host `websockets` paketi, Chrome probe için `frontend/node_modules` ve yerel Chrome gereklidir. Görevler test oturumunun API katalog kimlikleriyle `pick_A1 → packing_1`, `pick_B2 → delivery-01`, `pick_D1 → shipping_2` olarak gönderildi. Oturum kayıtları `/tmp/<C5_SESSION_ID>/` içindeydi; ham JSONL bu depoda kalıcı kopyadır.

Python ve Chrome probeları bağımsız zamanlayıcıyla çalıştı. DOM aralıkları Chrome ana iş parçacığı durduğunda seyrekleşir; STALE örnek oranı gerçek zaman yüzdesi olarak yorumlanmaz. İlk `ws_open/ws_close` React StrictMode açılışını da içerir. API 503 sayısı 250 ms örnekleme sayısıdır; toplam sunucu yanıt sayısı değildir. Üç robot öncesi/sonrası pencereler eşdeğer eşzamanlı hareket içermez.

## Statik ve regresyon komutları

Depo kökünden:

```sh
python3 -m py_compile scripts/c5_demo_start.py scripts/start_demo.py scripts/c5_telemetry_probe.py
python3 -m unittest discover -s tests -p 'test_c5_session_cleanup.py'
npm --prefix frontend run build
C5_UI_PORT=21620 C5_API_PORT=21618 npm --prefix frontend test -- --grep 'product-only outage|keeps product and TF validity separate' --workers=1
C5_UI_PORT=21620 C5_API_PORT=21618 npm --prefix frontend test -- --workers=1
git diff --check
```

Sonuçlar: Python sözdizimi ve oturum temizliği 12/12 birim testi geçti; frontend TypeScript/Vite build geçti; hedefli 2/2 ve tam dashboard 27/27 Playwright testi geçti; `git diff --check` geçti. Playwright sahte WebSocket test sunucusu kullandığı için Vite proxy'nin canlı olmayan `/api/task-catalog` isteği `ECONNREFUSED` kaydı üretir; test sonucu etkilenmedi. Bir/iki robot YAML profilleri `python3 -m fleet_config` doğrulamasını geçti. Her launcher başlangıcında üç readiness birim testi de geçti. Üç robot sonraki ilk canlı readiness denemesi geçmediği için ayrıca raporlandı.

## Yeniden inceleme için kaynaklar

- `frontend/src/useFleet.ts`: ürün kesintisinde scene soketini kapatma çağrısı kaldırıldı.
- `frontend/tests/dashboard.spec.ts`: ürün kaybı sırasında canlı TF ve tek açık soket regresyonu.
- `backend/dashboard/api.py`, `backend/dashboard/publisher.py`, `backend/dashboard/scene_stream.py`: ürün dosyası, TTL ve ortak WebSocket.
- `fleet-visualizer/bridge/ros_reader.py`, `fleet-visualizer/bridge/server.py`, `fleet-visualizer/bridge/run.py`: TF kaynağı, alım yaşı ve relay.
- `docker/simulation-warehouse-grid/tf.py`, `backend/fleet_manager/event_loop.py`: upstream TF ve Fleet Manager yayın döngüsü.
