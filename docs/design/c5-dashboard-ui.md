# C5 / Aşama 1 — Operasyon arayüzü ve koordinatlar

Üç Flowdeck görseli yerleşim, yüzeyler ve bilgi hiyerarşisi için referans alındı. Açık gri çalışma alanı, beyaz kartlar, sakin yeşil vurgu, kompakt durum etiketleri ve özgün üstten görünüm kullanıldı. Görünüm salt okunur ürün sözleşmesini izler. Aktif görev oluşturma alanı yerine sonraki aşama etiketi görünür.

Sol navigasyon genel görünüm, robotlar, görevler ve istasyonlar/şarj görünümlerini açar. Operasyon genel görünümünde merkezde depo, sağda seçili robot ve altta filo kartları bulunur. Robotlar Konva işaretçisinden veya HTML kartından seçilebilir. Kartlar Tab ve Enter ile kullanılabilir. Durumlar metin ve görsel işaretle ayrılır. Dar ekranlarda navigasyon üst sıraya taşınır, sağ ayrıntı paneli haritanın altında açılıp kapanır. Görev ve istasyon tabloları kendi alanlarında yatay kayar.

## Harita

C4 Executor, odometriyi robotun TF ağacından `map` çerçevesine dönüştürür. Doğrulama ortamında iki AMCL, aynı harita varlığını kullanır ve Nav2 küresel çerçevesi `map` olur. Fleet Manager istasyonlarını `fleet.yaml` içindeki aynı çerçeve varsayımıyla oluşturur. Backend ve Konva, gelen pozu `frame_id == "map"` ve sonlu koordinatlar koşuluyla işler. Kullanılabilir bir ölçüm gelene kadar başlangıç pozu çizilmez.

Kamera orijini `(tx, ty)`, ölçek `s` piksel/metre olmak üzere Konva konumu `(tx + s*x, ty - s*y)` olur. ROS yaw, +X'ten +Y'ye saat yönünün tersine ölçülür. +X yönünde çizilmiş işaretçiye Konva'da `-yaw * 180 / π` derece uygulanır. Zoom iki ekseni eşit ölçekler ve işaretçi boyutunu ekran pikseli cinsinden korur. Tekerlek, düğmeler, sürükleme ve filo kadrajı kamera durumunu değiştirir.

Yüzey **TEMSİLİ 2D DEPO** olarak etiketlenir. Raf ve çizgiler görsel referanstır. İstasyon işaretleri doğrulanmış config koordinatını, robot işaretleri kabul edilmiş ölçüm koordinatını kullanır. Gerçek occupancy map ve Nav2 rota aktarımı sonraki kapsamdır. Kopmada işaretçi son ölçüm konumunda kalır ve kesik sınırla gösterilir. Batarya miktarı gizlenir, görev ve rezervasyon kayıtları son eşitlemeden olarak işaretlenir.
