# C5 — Üçüncü robot Gamma entegrasyonu — 17 Kasım 2026

## Sonuç

**FAIL — gerçek Gamma görevi pickup öncesinde Nav2 abort ile başarısız oldu.** Cold-start ve üç robotlu hazırlık doğrulandı; API görevi Gamma'ya atadı ve gerçek Gazebo hareketi başladı. Pickup Nav2 goal'u `ABORTED`, görev `FAILED` oldu. Koşullu ön şart sağlanmadığı için üç görevli test başlatılmadı. Ayrıntılar aşağıdaki [gerçek görev takip kaydındadır](#gerçek-gamma-görevi-takip-koşusu).

Chrome'daki 3D sahne otomatik bağlandı. İlk yüklemede `WAITING FOR TF`, tüm pozlar geldiğinde `3/3 TF LIVE` görüldü. Üç model, depo içinde canlı poz ve `LIVE` durum etiketiyle görüntülendi.

## Robot başlangıç ve hazırlık durumu

| Robot | İlk poz (map, m) | AMCL hazır | Gerçek TF hazır | Nav2 hazır | Son Fleet Manager durumu |
|---|---:|---:|---:|---:|---|
| Alpha | `(-10.0, 5.25, 0)` | 8,996 ms | 10,879 ms | 12,786 ms | `IDLE`, telemetry/pose/battery `LIVE` |
| Beta | `(5.25, 7.75, π/2)` | 9,267 ms | 11,013 ms | 12,983 ms | `IDLE`, telemetry/pose/battery `LIVE` |
| Gamma | `(8.0, 5.5, π)` | 9,294 ms | 11,038 ms | 12,728 ms | `IDLE`, telemetry/pose/battery `LIVE` |

Faz süreleri container içindeki startup observer başlangıcından itibaren ölçülmüştür. Her robot için Nav2 readiness, AMCL/map server, controller, planner, behavior, BT navigator, waypoint follower ve velocity smoother lifecycle düğümlerinin `active` olmasını ve robot namespace'indeki `NavigateToPose` action server'ını gerektirir. Başlangıç kapısı üç robotun tüm koşulları aynı readiness turunda sağladığında `READY` oldu.

Gamma konumu 30 × 18 m profilinin `rack_B2` ayak izinden 1,25 m uzaktadır; C1 yaklaşım kontrolünün 0,45 m dairesel zarfından daha geniş açıklık bırakır. Grid çözünürlüğü 0,05 m/hücredir. Gamma-Beta merkez uzaklığı 3,55 m'dir. YAML semantik/occupancy doğrulaması pozun engel hücresiyle kesişmediğini onayladı. Gazebo'da başlangıçta gerçek model pozları `(8.0, 5.5)` oldu ve `unsafe-contact` kanıtı oluşmadı.

## Fleet Manager ve GUI kanıtı

- `GET /api/health`: `source=LIVE`.
- `GET /api/robots`: `robot_alpha`, `robot_beta`, `robot_gamma`; üçü `IDLE`, başlangıç durumu doğrulanmış, pose ve batarya `LIVE`; pozlar profil ile eşleşiyor.
- `GET /api/tasks`: `total=0`, `queued=0`, `active=0`.
- Chrome: `http://127.0.0.1:21486/`; `3/3 TF LIVE`, üç 3D işareti ve üç canlı robot kartı gözlendi.
- API: `http://127.0.0.1:21484/` (`/api/health`, `/api/robots`, `/api/tasks`).
- İzole doğrulama container'ı `c5-alpha-beta-gamma-live-retry1-20261117` çalışır bırakıldı. Önceki `c5-alpha-beta-stable-live-20261117` ve `c5-alpha-beta-manual-20261117` container'larına dokunulmadı.

Son incelemede observer kaydı `status=READY`, `current_status=WAITING` gösterdi. Önceki API örneğinde üç robot da `IDLE`/`LIVE`, Chrome'un gözlendiği anda gösterge `3/3 TF LIVE` idi. Bu bir startup başarısızlığı değildir; ancak observer'ın daha sonraki WAITING durumunun nedeni belirlenmediği için uzun süreli hazır olma doğrulanmış sayılmaz.

## Kod ve sınırlar

Robot sayısı veya ayrı bir Compose robot servisi eklenmedi. Tek değiştirilebilir 30 × 18 m filo profilindeki Gamma kaydı mevcut üretici tarafından ayrı SDF modeli, namespace içi Nav2 parametreleri, scan/odom/cmd_vel/contact köprüleri ve fiziksel pose için kullanılır. Fleet Manager, Executor ve Visualizer konfigürasyondan üç robotu aldı. Mevcut Alpha/Beta başlangıç pozları ve başlangıç prosedürü aynı kaldı.

Değişiklikler: `config/fleet.warehouse-30x18.yaml`, `docker/simulation-warehouse-grid/test_startup_readiness.py`, `frontend/src/ScenePanel.tsx`; bu rapor ve komut eki. Doğrulama komutları ve tam çalıştırma bilgisi [komut ekindedir](third-robot-gamma-commands-2026-11-17.md). Commit veya push yapılmadı.

## Kabul sınırı

İlk entegrasyon koşusunda Alpha/Beta/Gamma gerçek Gazebo'da oluştu; AMCL konumu, TF zinciri, Nav2 lifecycle/action server'ı ve canlı Fleet Manager/GUI görünürlüğü doğrulandı. Sonraki takip koşusunda tek gerçek Gamma görevi denendi ve Nav2 abort nedeniyle başarısız oldu. Üç robotlu eşzamanlı görev/temas değerlendirmesi başlatılmadı.

## Gerçek Gamma görevi takip koşusu

17 Kasım'da önceki manual ve Gamma demo container'larına dokunmadan yeni, izole bir cold-start açıldı: container `c5-three-robot-e2e-20261117`, ROS domain `198`, API `127.0.0.1:21494`, IGN partition `c5-three-robot-e2e-20261117`. Kanıt `/tmp/c5-three-robot-e2e-20261117/` altında tutuldu. Yeni koşunun başlangıç kapısı fiziksel reset'i doğruladı ve Alpha/Beta/Gamma için AMCL, 8/8 Nav2 lifecycle düğümü, `NavigateToPose` action server'ı ve gerçek TF zincirini kontrol etti. Görev öncesi Fleet API snapshot'ında üç robot `IDLE`/`LIVE`, görev sayısı sıfırdı.

| Alan | Kanıt |
|---|---|
| Görev | `web-e060891d-9f3a-4a73-acad-3383d3b0abb3` |
| API girişi | `POST /api/tasks` · HTTP `201` · `APPLIED` |
| Rota | katalogdan `pick_B2` → `quality_1`; koordinatlar config'ten alındı |
| Atama | `robot_gamma` · epoch `1` · `assigned_robot_id` API snapshot'ında Gamma |
| Pickup Nav2 | goal UUID `b166666d-970b-4c22-bee1-9f3a889c0ea2`; goal kabul edildi, sonra Nav2 status `6` (`ABORTED`) |
| Executor sonucu | `NAV2_ABORTED`; pickup öncesi hata, `is_loaded=false` |
| Fleet Manager terminali | SQLite ve son snapshot: `FAILED`; robot `STATE_ERROR` (`6`) |
| Dropoff | gönderilmedi; pickup tamamlanmadığı için test akışı burada sonlandı |
| Fiziksel hareket | Gamma başlangıç `(8.0, 5.5)` konumundan yaklaşık `(10.47, 4.74)` noktasına ilerledi; pickup `(6.0, 2.5)` konumuna ulaşmadı |
| Temas | observer `UNSAFE_CONTACT` kaydı yok; `unsafe-contact` sentinel dosyası oluşmadı |
| Üç robotlu koşu | başlatılmadı; Gamma görevi başarısız olduğu için koşullu ön şart sağlanmadı |

Gazebo logunda Gamma'nın `compute_path_to_pose`/`follow_path` action acknowledgement beklemeleri zaman aşımına uğradı; Nav2 daha sonra hedefi abort etti. Aynı olayda Fleet API beslemesi tekrarlayan `503`/`STALE` örnekleri verdi. Loglar action-server acknowledgement timeout'larını ve terminal abort'u kanıtlıyor; bu timeout'ların daha alt düzey nedeni bu koşuda izole edilmedi. Test bu nedenle **FAIL** olarak kaydedildi; tekrar veya kurtarma uygulanmadı.

Observer `status=READY` değerini korurken `current_status` kısa sürelerle `WAITING` oldu. `startup_readiness.py` bu alanı AMCL örneği/lifecycle, Nav2 lifecycle/action server'ı ve TF zincirinin anlık birleşiminden üretir; dosya yalnız birleşik durumu kaydeder, hangi alt koşulun düştüğünü yazmaz. Takip koşusundaki bağımsız read-only pre-task probu tüm robotlarda bu koşulları 1 saniye boyunca sağladı; aynı örnekte observer alanı yine `WAITING` idi. Bu kanıt, geçişin startup `READY` anını geri almadığını ve o anda Fleet/ROS dış snapshot'larının hazır olduğunu gösterir; observer'ın kendi örneklemesinde hangi fazın düştüğünü kesinleştirmez. **Geçişin faz düzeyindeki nedeni doğrulanmadı.**

Koşu, yalnız bu görev için açılmış container'ın SIGTERM ile normal kapanmasıyla bitirildi; `shutdown.json` tüm alt süreçler için `0` kaydetti. Diğer container'lar, worktree değişiklikleri ve commit/push durumu korunmuştur. Kanıt özeti, REST snapshot'ları, istek/yanıt, ROS olay akışı, Gazebo ve Executor logları ile SQLite yedeği aynı dizindedir.
