# Visualize V1 — görev noktası görsel doğrulaması

**17 Kasım 2026 · `feature/visualize` · commit/push yapılmadı.**

## Değişiklik ve kaynak

- `frontend/src/scene/operationPoints.ts`: canlı görev pozları ve katalog `roles` alanı ayrıldı. `pick_A1`–`pick_E2` çift rollüdür; aktif görevde bulunmuyorlarsa nötr işaretlenir. `inbound_1/2` yalnız alım, `quality_1`, `packing_1/2`, `delivery-01`, `shipping_2/3` yalnız bırakmadır. Bölge adından rol çıkarılmaz.
- `OperationMarkers.tsx`, `GridWarehouse.tsx`, `FloorSigns.tsx`: alım dolu turkuaz/beyaz yukarı ok; bırakma açık iç/amber çerçeve ve aşağı ok. Kutu simgesi kaldırıldı. Geri bildirim üzerine iki role aynı 1,24 × 1,24 m açık zeminli görsel taban eklendi; 0,92 × 0,92 m iç kareleri eşit kaldı. Bölge ve servis boyaları düşük doygunluklu yapıldı. İşaret pozları, istasyon kimlikleri, YAML ve robot renkleri değişmedi.
- `Scene.tsx`, `ScenePanel.tsx`, `styles.css`: bölge çağrıları soluklaştırıldı, nokta adlarının mevcut yakın/uzak eşiği 15/17 m histerezise dönüştürüldü. Robot ve rafla çakışan etiketler için mevcut yerleştirme denetimi kullanıldı.

## Doğrulama

| Kontrol | Sonuç |
|---|---|
| Üretim derlemesi | **DOĞRULANDI** — TypeScript ve Vite geçti. |
| Alım/bırakma işaret ölçüsü | **DOĞRULANDI (mock Chrome geometri)** — iki rolün iç karesi 0,92 × 0,92 m ve görsel tabanı 1,24 × 1,24 m. Fiziksel görev pozu değişmedi. |
| Katalog rolü ve aktif görev rolü | **DOĞRULANDI** — çift rol nötr; aynı noktadaki canlı görev alım işaretini tek kez çiziyor. |
| Üç robot TF, kamera ve etiket davranışı | **DOĞRULANDI (mock Chrome)** — 3/3 LIVE, üstten/genel/yakın/uzak; yakın adları açılıp uzakta gizlendi. Periyodik TF örnekleri koşu boyunca LIVE tuttu. |
| Renk olmadan ayrım | **GÖRSEL İNCELEME** — üstten gri tonlu görüntüde dolu kare/yukarı ok ile çerçeveli/aşağı ok ayrılıyor. Çok uzak ekranda simgeler küçülüyor. Rafın fiziksel olarak örttüğü yer işareti eğik kamerada yine kısmen gizlenebilir; rafı delerek gösterme uygulanmadı. |
| Eski `dashboard.spec.ts` paketi | 16 geçti, 9 kaldı. Sekiz test mevcut statik ızgara yerine eski GLB/şematik sahneyi bekliyor; bir test eski bireysel görev etiketi beklentisini kullanıyor. Bu tarihsel testler bu çalışmada değiştirilmedi. |
| Gerçek ROS/Gazebo, canlı üç robot, farklı fiziksel kamera/ekran ayarları | **HENÜZ TEST EDİLMEDİ**. Tarayıcı koşusu kontrollü WebSocket/TF fixture'ı kullandı. |

[Komut ve çıktı özeti](visualize-v1-commands-2026-11-17.md). Sonra görüntüleri: [genel](visualize-v1-screenshots/overview.png), [üstten](visualize-v1-screenshots/top.png), [gri ton](visualize-v1-screenshots/top-grayscale.png), [yakın](visualize-v1-screenshots/near.png), [uzak](visualize-v1-screenshots/far.png). Önce görüntüleri kullanıcı tarafından bu görevde eklenmiştir; depo dosyalarına kopyalanmadı.
