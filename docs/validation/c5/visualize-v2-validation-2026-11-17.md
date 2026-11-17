# Visualize V2 — zemin adları ve nokta bilgi balonları

**17 Kasım 2026 · `feature/visualize` · commit/push yapılmadı.** Bu kayıt V1'in ardından gelen kullanıcı düzeltmesini kapsar; [V1 kaydı](visualize-v1-validation-2026-11-17.md) tarihsel durumu anlatır.

## Uygulama

- `Scene.tsx`, `ScenePanel.tsx`, `styles.css`: sürekli görev, katalog ve servis noktası adları kaldırıldı. Robot etiketleri korundu. İşaretin üzerine gelince ad/rol/durum bilgi balonu açılıyor; tıklama sabitliyor, boş zemine tıklama veya Escape kapatıyor. Etkin balon robot etiketiyle çakışmayan ekran konumuna yerleştiriliyor.
- `floorSignLayout.ts`, `GridWarehouse.tsx`, `FloorSigns.tsx`: profilin bölge ve ana koridor adları zemine soluk, düz yazı olarak yazılıyor. Raf, katalog görev pozu, şarj/park servis pozu ve diğer zemin yazıları yerleşim engelidir. Bulunamayan konuma yazı zorlanmıyor. Sağ üst servis alanı `ŞARJ` olarak adlandırılıyor.
- `operationPoints.ts`, `OperationMarkers.tsx`: canlı görev `pickup`/`dropoff` pozları ve katalog `transfer_points.roles` ayrımı sürüyor. Aktif görevi olmayan çift rollü noktada turkuaz dış/amber iç çerçeve, rolü belirlenemeyen noktada soluk gri çerçeve var. Turkuaz dolu yukarı ok ve amber boş aşağı ok, 0,92 m iç kare ve 1,24 m taban ölçüsü korunuyor. Şarj/park renkleri nötr kalıyor.

## Doğrulama

| Kontrol | Sonuç |
|---|---|
| Üretim derlemesi | **DOĞRULANDI** — TypeScript ve Vite geçti. |
| Hedefli Playwright | **DOĞRULANDI (mock Chrome)** — 5/5. Altı bölge adı ve dört ana koridor adı, katalog rolü, raf/nokta yerleşim engelleri, nokta yazılarının sürekli görünmemesi, hover/tıklama/boş zeminde kapatma, çift rol ve park durumu kontrol edildi. |
| Üç robot ve kamera | **DOĞRULANDI (mock Chrome)** — 3/3 TF LIVE, robot seçimi; üstten, genel, yakın ve uzak kadraj. Periyodik fixture TF/snapshot güncellemeleri kullanıldı. |
| Görsel inceleme | Üstten ve yakın görüntülerde zemin adları, işaretler ve robot etiketleri incelendi. Çok uzak veya eğik kamerada zemin yazıları perspektif nedeniyle küçülür; rafın fiziksel olarak örttüğü alan görünmez. Her olası canlı robot pozunda yazı okunurluğu garanti edilemez. |
| Eski `dashboard.spec.ts` | **14 geçti, 9 kaldı.** Dokuz hata eski `warehouse === "glb"` koşulunda kaldı; güncel doğrulanmış depo `grid`. Bu paket mevcut sahne için güncellenmedi. Geçti sayılmadı. |
| Gerçek ROS/Gazebo ve canlı üç robot | **HENÜZ TEST EDİLMEDİ.** Fixture sonucu fiziksel/entegrasyon kabulü değildir. |

[Komut eki](visualize-v2-commands-2026-11-17.md). Görseller: [üstten](visualize-v2-screenshots/top.png), [yakın](visualize-v2-screenshots/near.png), [alım bilgi balonu](visualize-v2-screenshots/pickup-hover.png), [çift rol bilgi balonu](visualize-v2-screenshots/dual-hover.png), [genel](visualize-v2-screenshots/overview.png), [uzak](visualize-v2-screenshots/far.png), [gri ton](visualize-v2-screenshots/top-grayscale.png).
