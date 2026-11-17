# C5 Alpha/Beta demo dönüşü — komut ve kanıt eki — 17 Kasım 2026

Worktree: `/private/tmp/ros2-fleet-manager-c5-alpha-beta-stable`
Branch: `demo/alpha-beta-stable`

## Yapılandırma ve kod kontrolleri

```sh
python3 -m fleet_config config/fleet.warehouse-30x18.yaml
python3 docker/simulation-warehouse-grid/test_startup_readiness.py
git diff --check
```

Sonuç: profil şema/semantik/dosya kontrollerinden iki robotla geçti; readiness birim testleri 3/3 geçti; diff kontrolü geçti.

## Canlı servis gözlemleri

Kullanılan mevcut cold-start oturumu/container: `c5-alpha-beta-stable-live-20261117`. Yeni container başlatılmadı ve diğer çalışan demo container'larına sinyal gönderilmedi.

```sh
cat /tmp/c5-alpha-beta-stable-live-20261117/live/startup-readiness.json
curl -fsS http://127.0.0.1:21482/api/health
curl -fsS http://127.0.0.1:21482/api/robots
curl -fsS http://127.0.0.1:21482/api/tasks
```

Readiness `READY` verdi. Chrome'da `http://127.0.0.1:21481/` açıldı; gerçek 3D depo çizimi, `2/2 TF LIVE`, Alpha ve Beta kartlarında `Canlı` ve `Boşta` gözlendi. API başlangıçta `source=LIVE`, iki robot `IDLE` döndürdü.

## Görev izleme

Chrome'da Görevler → `pick_A1 → packing_1` rotası seçildi ve bir kez gönderildi. Görev ID `web-2de661a8-1627-4898-bc98-e11523021b88`; Alpha epoch `1`; ExecuteTask UUID `9a039b1b-8408-4733-88f1-e7486f1157bb`.

Ham olaylar:

- `/tmp/c5-alpha-beta-stable-live-20261117/live/ros.jsonl`
- `/tmp/c5-alpha-beta-stable-live-20261117/live/simulation.log`
- `/tmp/c5-alpha-beta-stable-live-20261117/live/executor_robot_alpha.log`
- `/tmp/c5-alpha-beta-stable-live-20261117/live/api.log`

Nav2 pickup UUID `44488582-b86a-4cb3-98ac-df211a4aa234` status `4` (`SUCCEEDED`); dropoff UUID `5af98017-b698-41f1-97f9-847293e3d324` status `6` (`ABORTED`). Final API task `FAILED`; Alpha status `ERROR`, `is_loaded=true`; Beta `IDLE`. Dropoff sırasında Nav2 action acknowledgement timeout'ları ve planner/controller loop-rate uyarıları kaydedildi. İkinci görev, fiziksel yük/hata belirsizliği nedeniyle başlatılmadı.

## Gamma snapshot

```text
/private/tmp/c5-gamma-snapshot-demo-alpha-beta-stable-2026-11-17.tar.gz
SHA-256 b32b71606a9137a0748ad9168ef3c980eb821d559648c69b23515f0e58e0d4f8

/private/tmp/c5-gamma-snapshot-demo-alpha-beta-stable-2026-11-17.patch
SHA-256 e4eb5c3b668742b74b8838fc833301f55b0661a9853c51763da88750b858bada
```
