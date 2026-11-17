# Visualize V2 — park alanı yer değişikliği

**17 Kasım 2026 · `feature/visualize` · commit/push yapılmadı.** Bu kayıt [önceki V2 görsel düzenlemesinin](visualize-v2-validation-2026-11-17.md) ardından gelen ayrı park isteğini kapsar.

## Kaynak ve politika denetimi

- `feature/visualize` içindeki `config/fleet.warehouse-30x18.yaml` iki robot (`robot_alpha`, `robot_beta`) ve üç park istasyonu içeriyordu. `config/fleet.yaml` ise farklı, küçük C1 örnek profilidir; bu 30 × 18 m demonun kaynağı değildir.
- Çalışan `c5-20261117T081139Z-0ead015f09` container'ı `/private/tmp/ros2-fleet-manager-c5-alpha-beta-stable` dizinini salt okunur bağlayıp oradaki 30 × 18 m profiliyle çalışıyor. Bu bağlı profil üçüncü `robot_gamma` kaydını içeriyor. Canlı ürün snapshot'ında üç robot da `LIVE`; ekran görüntüsündeki `3/3 TF LIVE` bu oturuma aittir. `feature/visualize` profilinin iki robotlu kalması dal farkıdır. Kullanıcı talimatıyla burada robot kaydı veya başlangıç pozu eklenmedi/değiştirilmedi.
- Canlı snapshot'ta eski park sahipliği `park_1 → robot_beta`, `park_2 → robot_gamma`, `park_3 → robot_alpha` idi. Fleet Manager `station_dispatch._select` boş ve erişilebilir park istasyonlarını Nav2 rota/enerji koşuluyla değerlendirip en kısa rotayı seçer. Kalıcı `alpha → park_1`, `beta → park_2`, `gamma → park_3` eşleştirmesi **mevcut politikayla uyumlu değildir**. İstenen eşleştirme **uygulanmadı**; Scheduler/Fleet Manager, TrafficMotionGate, permit ve watchdog değiştirilmedi. Görsel yuva adı gerçek rezervasyon sahibinden okunur; boş yuvada istasyon ID'si görünür.

## Yerleşim

| İstasyon | Önceki map pozu (m, rad) | Yeni map pozu (m, rad) |
|---|---|---|
| `park_1` | (5,25; 5,25; π/2) | (13,5; 1,5; π) |
| `park_2` | (5,25; 6,5; π/2) | (13,5; 2,75; π) |
| `park_3` | (5,25; 7,75; π/2) | (13,5; 4,0; π) |

Yeni park bölgesi `x=[12,5;14,75]`, `y=[0,75;4,75]` m. Görsel yuva çizgileri istasyon merkezlerinden türetilen 1,50 × 1,00 m dikdörtgenlerdir; merkezler arası 1,25 m, sınırlar arası 0,25 m. Bunlar fiziksel bölme değildir. Nav2 robot yarıçapı 0,30 m; profilin yaklaşma açıklığı 0,45 m. Yuva önünde `cross_e` geçidi üzerinden batıya açık manevra alanı vardır; en yakın üst şarj hedefi `dock_6=(13,25;8,25)` m ve şarj yaklaşma şeridi park bölgesine girmez. Eski `x=[4,5;6,0]`, `y=[4,75;8,5]` m şeridi yalnız soluk dekoratif bekleme boyasıdır; istasyon/rezervasyon kaydı oluşturmaz.

`config/fleet.warehouse-30x18.yaml` yeni hedefler için tek düzenlenebilir kaynaktır. Aynı profil frontend statik 3D özeti, Gazebo SDF, doluluk haritası ve Nav2 parametrelerini üretir. Backend park istasyonlarını yüklenen YAML'den rezervasyonlara kaydeder; Executor hedefi buradan alır. Canlı çalışan container eski, ayrı dizini bağladığından bu çalışma ağacındaki değişiklik o oturuma uygulanmış sayılmaz.

## Doğrulama ve sınırlar

- **DOĞRULANDI (statik):** C1 profil doğrulaması, 0,45 m dairesel ayak izi için `check_approaches`, yeni YAML'den SDF/PGM/Nav2 üretimi, frontend profilinin `--check` eşleşmesi ve `git diff --check` geçti.
- **DOĞRULANDI (mock Chrome):** Üretim derlemesi ve hedefli Playwright testleri geçti. Üç yuva, kaynak pozları, mevcut sahiplerin adları, V1 işaretleri, TF fixture'ı ve kamera etkileşimi denetlendi. [Yeni üstten ekran](visualize-park-relocation-screenshots/top.png) ve [önceki üstten ekran](visualize-v2-screenshots/top.png).
- **HENÜZ TEST EDİLMEDİ:** Yeni hedeflerde canlı Nav2 `SUCCEEDED`, eşzamanlı üç robotla fiziksel giriş/çıkış, şarj geçişi ve trafik kapısı. Statik doluluk yol kontrolü dinamik çarpışmasızlık kanıtı değildir. Çalışan container'a hedef enjekte edilmedi.
- `tests/test_warehouse_grid.py` host ortamında `fastapi` bulunmadığı için test toplama aşamasında hata verdi; geçmedi veya skip edilmedi.

[Komut ve sonuç eki](visualize-park-relocation-commands-2026-11-17.md).
