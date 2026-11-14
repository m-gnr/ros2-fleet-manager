# C5-B2 — Side-mount obstacle sensörleri

14 Kasım 2026 · `main` (`f68c991`, çalışma başlangıcı). İlgili hedefli kanıt [canlı koşu dizininde](c5-b2-live-2026-11-14/).

## Değişiklik

C5-A `warehouse-30x18` profiline iki deneyde doğrulanmış sonlu sensör eklendi: `(0.15, 0.23, 0.0125)` / 90° ve `(-0.15, -0.23, 0.0125)` / 270°. Topic'ler `/robot_{alpha,beta}/obstacle_{front_left,rear_right}`, frame'ler `robot_{alpha,beta}/obstacle_{front_left,rear_right}/lidar`. Her iki montajda gerçek collision/visual/inertia, 97 ışın, 5 Hz, 191° FOV ve 0.1–10 m menzil kullanılır.

Üst LiDAR, AMCL parametreleri, mevcut body/wheel/caster collision/inertia ve 0.30 m Nav2 yarıçapı değiştirilmedi. AMCL yalnız namespace'li `/scan` kaynağını korur. İki side-mount kaynak local costmap ObstacleLayer'a `marking` ve `clearing` ile bağlandı. TF ve bridge aynı profile sözleşmesinden üretilir; temas gözlemcisi sensör link'lerini de izler. Sensörlü katman gerçek Nav2 `ObservationBuffer` girdilerini gözlem raporuna çıkarır.

## Doğrulama

Hedefli Python testi: `tests/test_obstacle_sensors.py` **9/9 PASS**. Filo doğrulayıcısı iki robotu kabul etti. Humble/Fortress container'ında `fleet_interfaces` ve `fleet_perception` **2/2 paket derlendi**. İlk derleme gereksiz `scan_source` hedefinin bulunmayan IDL'sinde durdu; yalnızca gerçek ürün akışında kullanılmayan hedef kaldırıldı, ardından temiz derleme geçti.

Tek Gazebo koşusunda iki robot 6 m aralıkla, hareketsiz ve geçici probe pozlarında çalıştı; unsafe contact yok, kontrollü kapanışta bütün alt süreçler exit 0. İki local costmap de 3×3 m rolling grid yayımladı. `perception_observations` raporlarında `/scan`, `/obstacle_front_left`, `/obstacle_rear_right` için `used=true` görüldü. Ancak robot merkezleri arası 6 m olduğundan karşı robot local costmap penceresinin dışındaydı; koşu yeni sensörlerin gerçek karşı robot gövdesini local grid'de işaretlediğini **kanıtlamaz**. Fiziksel karşı-gövde → lethal hücre kanıtı ve Nav2 yavaşlama/durma ölçümü **FAIL / tamamlanmadı**. Bu rapor çarpışmasız trafik kabulü değildir.

Önceki deney sonuçları ve sınırlamaları [sensör optimizasyon raporunda](c5-obstacle-sensor-optimization-2026-11-14.md) korunur. Komut/çalışma ayrıntıları `commands.md` içindedir.
