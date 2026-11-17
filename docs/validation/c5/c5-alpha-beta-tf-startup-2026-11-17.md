# C5 Alpha/Beta TF cold-start doğrulaması — 17 Kasım 2026

## Kapsam ve durum

`f68c991d8b397c4c72257f599402b98c587c481e` tabanından `demo/alpha-beta-stable` dalı `/private/tmp/ros2-fleet-manager-c5-alpha-beta-stable` yolunda açıldı. HEAD hedef commit'te kaldı; kod ve bu doğrulama kaydı dalda commit edilmemiş değişikliklerdir. Başlangıçta temiz olan worktree'nin bu görevdeki değişiklikleri `git status` ile listelenebilir. Kaynak `main` worktree'si ve önceki manuel demo container'ı değiştirilmedi.

**Doğrulandı:** Gerçek iki robotlu soğuk başlatmada AMCL, Nav2 ve `map → odom → base_link` TF zincirleri izlenip tümü hazır olduktan sonra Fleet Manager/API açıldı. Chrome GUI sayfa yenilemeden `2/2 TF LIVE` durumuna geçti. İki robot da test sonu `IDLE`, poz/batarya/telemetri `LIVE`; görev listesi boştu. Bu koşuda görev gönderilmedi.

**Kapsam dışı:** Uzun süreli çalışma, trafik/atama regresyonu, görev tamamlama ve performans/ölçek kabulü yapılmadı. Bu commit'te bulunmayan native watchdog, permit veya HMAC özellikleri varmış gibi doğrulanmamıştır.

## Başlangıç sorunu ve değişiklik

Launcher fiziksel reset ve BT Navigator durumundan sonra Executor'ları, köprüyü, manager'ı ve API'yi başlatıyordu. AMCL ilk konumu, diğer Nav2 lifecycle düğümleri ve güncel TF zinciri hazır olana kadar API/WebSocket tarafında gerçek robot pozu bulunmayabiliyordu. Ayrıca standalone kurulumda API `scene` DNS adına bağlanıyor, fakat API ve köprü aynı container'da olduğu için bu ad tanımlı değildi.

Yeni observer AMCL'in transient-local `amcl_pose` örneğini ve aktif lifecycle'ını; sekiz Nav2 lifecycle düğümünün tamamını; `NavigateToPose` action server'ını; Visualizer köprüsünün kullandığı `RobotReader` ile gerçek, güncel TF zincirini ve `/clock`'u denetler. Her robotun AMCL, TF ve Nav2 ilk hazır olma süreleri monotonic ms ve UTC olarak `startup-readiness.json` dosyasına yazılır. İki robotun tüm koşulları hazır olmadan manager/API açılmaz. Launcher en çok 90 saniye bekler; süreç hatası veya zaman aşımında fail-closed davranır. Sahte TF veya sabit başlangıç uykusu kullanılmaz.

Standalone launcher API'nin köprü adresini `127.0.0.1` olarak seçer. API CLI'nin varsayılan `scene` host'u Compose kullanımı için korunur.

## Cold-start sonucu

| Robot | AMCL hazır | TF hazır | Nav2 hazır |
|---|---:|---:|---:|
| Alpha (`robot_alpha`) | 3461 ms · 00:02:34.064824Z | 4469 ms · 00:02:35.072648Z | 5519 ms · 00:02:36.122714Z |
| Beta (`robot_beta`) | 3465 ms · 00:02:34.068380Z | 4473 ms · 00:02:35.076219Z | 6517 ms · 00:02:37.120807Z |

Tüm değerler observer başlangıcından itibaren ölçülmüştür (`2026-11-17T00:02:30.603568Z`). İki robotlu `READY` anı `2026-11-17T00:02:37.120903Z`, toplam 6517 ms'dir. Durum kanıtı `/tmp/c5-alpha-beta-stable-live-20261117/live/startup-readiness.json` içindedir.

- GUI: `http://127.0.0.1:21481/` — Chrome'da `2/2 TF LIVE` gözlendi.
- API: `http://127.0.0.1:21482/` — `/api/health` `source=LIVE` döndürdü.
- Son REST gözlemi: iki robot `IDLE`; başlangıç pozları Alpha `(-10.0, 5.25)`, Beta `(5.25, 7.75)` map frame'inde; ikisinde de aktif görev yok.
- `/api/tasks`: boş liste, `total=0`, `queued=0`, `active=0`.
- Container `c5-alpha-beta-stable-live-20261117` ve GUI dev server doğrulama sonunda çalışır durumdaydı.

## Kontroller

- `python3 docker/simulation-warehouse-grid/test_startup_readiness.py`: **3/3 geçti**.
- Değişen Python modüllerinin `py_compile` kontrolü: **geçti**.
- `git diff --check`: **geçti**.
- ROS 2 interface build (`fleet_interfaces`): **1/1 paket geçti**.
- Gerçek iki robotlu Gazebo cold-start, API health/robot/task gözlemi ve Chrome GUI: **2/2 TF LIVE; görev gönderilmedi ve robotlar IDLE kaldı**.

Komutların ve servis adlarının kaydı [komut ekindedir](c5-alpha-beta-tf-startup-commands-2026-11-17.md).
