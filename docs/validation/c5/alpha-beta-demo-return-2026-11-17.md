# C5 — Alpha/Beta demo sürümüne dönüş — 17 Kasım 2026

## Karar

**PARTIAL.** Aktif 30 × 18 m profil iki robotla doğrulandı; Gazebo, iki robotun AMCL/Nav2/TF cold-start koşulları, Fleet Manager/API ve Chrome 3D GUI çalıştı. Chrome'da `2/2 TF LIVE`, Alpha/Beta canlı ve başlangıçta `IDLE` görüldü. Gerçek pickup/dropoff kabulü geçmedi: Alpha pickup Nav2 hedefini tamamladı, dropoff Nav2 hedefi abort oldu. Görev `FAILED`, Alpha `ERROR` ve `is_loaded=true` kaldı. Başarı ölçütü karşılanmadı.

## Değişiklik ve korunan Gamma çalışması

- `config/fleet.warehouse-30x18.yaml` ve readiness testi iki robotlu HEAD içeriğine döndürüldü; Gamma'ya özgü kirli farklar kaldırıldı.
- Ortak TF göstergesi iyileştirmesi `frontend/src/ScenePanel.tsx` içinde korundu: yalnız bütün robotlar TF canlı olduğunda gösterge yeşil olur ve `N/N TF LIVE` yazar.
- Gamma raporu ve komut eki tutuldu. Başlangıçtaki kirli Gamma diff'i ve iki yeni rapor için ayrıca `/private/tmp/c5-gamma-snapshot-demo-alpha-beta-stable-2026-11-17.tar.gz` (SHA-256 `b32b71606a9137a0748ad9168ef3c980eb821d559648c69b23515f0e58e0d4f8`) ve `/private/tmp/c5-gamma-snapshot-demo-alpha-beta-stable-2026-11-17.patch` (SHA-256 `e4eb5c3b668742b74b8838fc833301f55b0661a9853c51763da88750b858bada`) oluşturuldu. Snapshot `/private/tmp` altında ayrı tutulur.
- TF cold-start düzeltmeleri geri alınmadı. Canlı koşu önceden mevcut `c5-alpha-beta-stable-live-20261117` container'ını kullandı; diğer container/worktree'lere dokunulmadı.

## Gerçek görev

Chrome Görevler görünümünden katalog rotası `pick_A1 → packing_1` gönderildi. API `201 Created` döndürdü; görev ID `web-2de661a8-1627-4898-bc98-e11523021b88`, robot `robot_alpha`, epoch `1`, ExecuteTask UUID `9a039b1b-8408-4733-88f1-e7486f1157bb` oldu. Gerçek Nav2 pickup goal UUID `44488582-b86a-4cb3-98ac-df211a4aa234` terminal status `4` (`SUCCEEDED`) ile tamamlandı. Executor pickup yüklemesini `is_loaded=true` olarak kaydetti.

Dropoff için Nav2 goal UUID `5af98017-b698-41f1-97f9-847293e3d324` terminal status `6` (`ABORTED`) verdi. Gazebo/Nav2 loglarında `compute_path_to_pose` ve `follow_path` action-server acknowledgement timeout'ları ile planner/controller loop-rate uyarıları görüldü; Nav2 ardından goal'u abort etti. Bu gözlemler yakın nedeni gösterir; daha alt kök neden doğrulanmadı. Fleet Manager politikası doğrultusunda görev `FAILED`, Alpha `ERROR` oldu. Son status `is_loaded=true`, Beta `IDLE` ve `LIVE`; API `source=LIVE` kaldı. Yüklü hata durumu nedeniyle ikinci görev gönderilmedi; reset, ClearRobotError, retry veya reassignment yapılmadı.

## Servis ve arayüz

- Chrome GUI: `http://127.0.0.1:21481/` — gerçek 3D depo çizimi, `2/2 TF LIVE`, iki canlı robot ve başlangıçta iki `IDLE` robot gözlendi.
- Fleet API: `http://127.0.0.1:21482/` — `/api/health` `source=LIVE`; `/api/robots` iki robotu döndürdü. Görev sonrası Alpha `ERROR`, Beta `IDLE`.
- İki robot cold-start kaydı: `/tmp/c5-alpha-beta-stable-live-20261117/live/startup-readiness.json` (`status=READY`, `current_status=READY`). Gerçek ROS/Nav2 kaydı `ros.jsonl`; API, simülasyon ve Executor logları aynı `live/` dizinindedir.

## Kontroller ve sınırlar

- `python3 -m fleet_config config/fleet.warehouse-30x18.yaml`: **geçti**, şema/semantik/dosya referansları doğrulandı, 2 robot.
- `python3 docker/simulation-warehouse-grid/test_startup_readiness.py`: **3/3 geçti**.
- `git diff --check`: **geçti**.
- Canlı Gazebo, cold-start, API health ve Chrome GUI: **geçti** (iki robot).
- Gerçek pickup: **Nav2 SUCCEEDED**. Gerçek dropoff: **Nav2 ABORTED**; görev `COMPLETED` olmadı.
- İkinci görev ve iki COMPLETED kanıtı: **çalıştırılmadı**; Alpha yüklü `ERROR` durumunda kaldı.

Komut ve ham kanıt yolları [ek dosyadadır](alpha-beta-demo-return-commands-2026-11-17.md). Bu kayıt C5 demo kabulü vermez.
