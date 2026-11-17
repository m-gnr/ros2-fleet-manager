# Visualize V2.3 — üç robotun parkta başlangıcı

**17 Kasım 2026 · `feature/visualize` · commit/push yok.** İzole koşu `visualize-v23-verified-20261117`, kaynak bağı `/Users/murat/develop/ros2-fleet-manager-visualize:/workspace:ro`, `ROS_DOMAIN_ID=212`, `IGN_PARTITION=visualize-v23-verified-20261117`, API/UI `21582/21584`. Önceki `21482` oturumuna ve başka worktree'ye dokunulmadı. Profil özeti `e9dfb0d9cb428e822faa50606fdae99cb7d7dbf8262a15d263ee339ec191f56c`.

## Canlı poz kanıtı

| Robot → park | Gazebo fiziksel reset pozu x, y, z, yaw | WebSocket `map` TF x, y, yaw | Sonuç |
|---|---|---|---|
| `robot_alpha → park_1` | 13,5; 1,5; 0,199997; 3,141593 | 13,500000; 1,500000; 3,141593 | **PASS** |
| `robot_beta → park_2` | 13,5; 2,75; 0,199997; 3,141593 | 13,500000; 2,750000; 3,141593 | **PASS** |
| `robot_gamma → park_3` | 13,5; 4,0; 0,199997; 3,141593 | 13,500000; 4,000000; 3,141593 | **PASS** |

Mevcut üretici map x/y/yaw değerlerini SDF model pozuna doğrudan geçirir; SDF'deki üç başlangıç pozu sırasıyla `13.5 1.5 0.21 0 0 π`, `13.5 2.75 0.21 0 0 π`, `13.5 4.0 0.21 0 0 π`. Harita rasterinin origin'i `(-16.5, -10.5)`, çözünürlüğü `0.05 m`; bu raster dönüşümü Gazebo dünya pozuna ofset eklemez. Yaw `π`, robotların duvardan batıya bakmasını sağlar. Fiziksel reset denetiminde üç robotun konum/yaw hatası ve hızı sıfır çıktı. [Ham fiziksel kayıt](visualize-v2-3-2026-11-17/reset-verified.json) ve [beş saniyelik WebSocket örneği](visualize-v2-3-2026-11-17/websocket-sample.json) saklandı.

`/clock` örneği 112,095 s; `/tf` örneği 112,525 s damgalı `robot_alpha/odom → robot_alpha/base_link` dönüşümü verdi. WebSocket örneğinde 201 gerçek `robot_pose` paketi, üç robot için `data_status: LIVE` ve ürün snapshot'ında üç `telemetry: LIVE` kaydı vardı. Chrome'un canlı üstten ve izometrik görünümünde üç robot kendi yuvasında, üç ad ayrı ve `3/3 TF LIVE` olarak gözlendi. Bu gözlem mock fixture'a dayanmaz.

## Sonuçlar

| Kontrol | Durum | Kanıt / sınır |
|---|---|---|
| İzole üç robotlu başlangıç, fiziksel reset | **PASS** | Yeni container yalnız bu worktree'yi bağladı; üç Gazebo pozu reset kaydında. |
| `/clock`, `/tf`, WebSocket ve ürün LIVE | **PASS** | Gerçek ROS örnekleri ve `fleet.scene.v1` kaydı. |
| Chrome yuvalar, üç etiket ve TF LIVE | **PASS** | Gerçek API/TF bağlı Chrome üstten ve izometrik gözlemi; etiketler çakışmadı. |
| Profil üretim `--check`, frontend build | **PASS** | Son değişikliklerden sonra tekrar çalıştırıldı. |
| Frontend hedefli regresyon | **PASS** | Chrome Playwright `5 passed`; bunlar mock testtir, canlı kanıtın yerine kullanılmadı. |
| Host park/dispatch/dashboard/motion-gate regresyonu | **PASS** | `63 passed`. |
| ROS görselleştirici okuyucu regresyonu | **PASS** | Humble ortamında `4 passed`, skip yok. |
| Fiziksel Nav2 park çıkışı ve dönüşü | **NOT TESTED** | `motion_envelope: null`; permit, motion gate ve watchdog zinciri için hareket yetkisi yok. Hiçbir hareket komutu gönderilmedi. |

İlk başlatma image'da `fleet_perception` bulunmadığı için preflight'ta, sonraki deneme `scene` host adı çözülmediği için canlı köprüde, bir deneme de SQLite şema oluşturma yarışı nedeniyle observer'da kaldı. Ayrı overlay build, container içi `scene` host eşlemesi ve observer'ın dört tabloyu beklemesiyle son izole koşu geçti. Geçmiş denemeler PASS sayılmadı.

**Kalan sınır:** Fiziksel spawn, Fleet Manager'da park rezervasyonu oluşturmaz; üç istasyon snapshot'ta `FREE` kaldı. Dinamik park seçimi değiştirilmedi. Hareket ve fiziksel çıkış/dönüş kabulü açık. [Komut ve sonuç eki](visualize-v2-3-commands-2026-11-17.md).
