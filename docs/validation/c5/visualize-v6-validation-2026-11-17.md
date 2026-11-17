# Visualize V6 — yaşayan dış çevre

**17 Kasım 2026 · `feature/visualize` · commit/push yapılmadı.** V5 dış kökü genişletildi; yalnız Three.js görsel sunumu, frontend testleri ve dokümantasyon değişti. Önceden mevcut YAML, bridge, observer ve V1–V5 değişiklikleri korunmuştur. Gazebo, Nav2, TF, collision, fiziksel harita, YAML koordinatları, istasyonlar ve görev hedefleri bu görevde değiştirilmedi.

## Sonuç

- Beton tonunda gri-yeşil avlu, soluk çim, iki şeritli yol ve kaldırım; sade çit/açık giriş, güvenlik kulübesi, teknik bina, dört aydınlatma direği eklendi. Direkler yalnız geometri, yeni ışık üretmiyor.
- İki rampa yanında paletler ve konteynerler, küçük otoparkta beş gri/krem/kum tonlu araç var. Mal kabul kamyonu sabit; sevkiyat kamyonu dış avluda yavaş yanaşma/uzaklaşma manevrası yapıyor. Yolda aralıklı geçen tek dekoratif araç var.
- Dört küçük üçlü ağaç kümesinde konik/yuvarlak tipler ve alçak çalılar kullanıldı. Sabit saha üç instanced çizimde; araç parçaları instanced kutularda çiziliyor. Harici model veya yeni asset lisansı bağımlılığı yok.
- Dış malzemeler soluk ve mat; görev turkuazı/amberi kullanılmıyor. Shadow map, dinamik ışık ve post-processing eklenmedi. Geniş çim düzlemiyle aynı renk arka planı, kenarlardaki boşluğu ve keskin ufuk geçişini önlüyor.
- Dış öğeler kamera sığdırma kökünün dışında, raycast'leri kapalı. Görüş çizgisini kesen dekoratif prop'lar instance bazında/grup olarak gizleniyor. Varsayılan kamera değişmedi; tüm sahayı gösteren görseller elle uzaklaştırılmış görünüm.
- **Çevreyi göster** kapalıyken bütün dış kök ve animasyon timer'ı kapanıyor; V4 iç sahnesi ile V5 sevkiyat açıklığı kalıyor. Mevcut batı/mal kabul açıklığı korunuyor.

## Hareket sınırı

Hareket yalnız yerel dekoratif saate bağlıdır; robot verisi, görev veya gerçek sevkiyat bilgisi kullanılmaz. Sevkiyat kamyonu 80 saniyelik döngüde bekler, 2,8 m dışarı manevra yapar, bekler ve geri yanaşır. Yol aracı 56 saniyelik döngünün 16 saniyesinde geçer; aynı anda en fazla bir yol aracı vardır. Kaynak kodundaki bu süreler ürün veya navigasyon ayarı değildir.

Timer en fazla yaklaşık 20 Hz güncelleme ister. Çevre kapalı veya `document.hidden` iken iptal edilir; faz, tick sayısı ve konum donar. Yeniden açılışta geçen süreyi telafi etmez. Sekme görünürlüğü Chrome testinde kontrollü `document.hidden` ve `visibilitychange` üzerinden sınandı; gerçek işletim sistemi sekme değiştirme/uyku testi yapılmadı. Kamyon döngüsünün gidiş/dönüş örnekleri saf fonksiyon testinde doğrulandı; 80 saniyelik tam gerçek zaman koşusu yapılmadı.

## Doğrulama

| Kontrol | Sonuç |
|---|---|
| TypeScript + Vite üretim derlemesi | **DOĞRULANDI**. Mevcut Zod annotation uyarıları build'i engellemedi. |
| V1–V6 görsel/etkileşim regresyonu ve hareket modeli | **3/3 geçti**. Üç TF fixture robotu, rol/durum/yaw, robot seçimi, hover/click, park etiketleri, V4 yüzeyleri; kapalı/gizli sekmede hareket saatinin donması ve sıçramadan devamı. Dekoratif sabit geometri depo ayak izinin dışında kalıyor. |
| Depo profil regresyonu | **4/4 geçti**. Hash, kesinti, doğrulanmış geometri, nokta rolleri ve zemin adları. |
| TF/Path kaynak ayrımı | **1/1 geçti**. Epoch sınırında plan temizliği. Son toplam **8/8**, 27,3 sn. |
| Kamera/çevre | Serbest, üstten, takip ve filoyu sığdırma modlarında çevre aç/kapa kamera/target değerlerini 10 ondalık hassasiyette koruyor; noktalar değişmiyor. |
| Chrome görsel inceleme | [Varsayılan eğik](visualize-v6-screenshots/overview.png), [üstten](visualize-v6-screenshots/top.png), [çevre kapalı](visualize-v6-screenshots/top-environment-off.png), [geniş eğik](visualize-v6-screenshots/exterior-wide.png), [geniş üstten](visualize-v6-screenshots/exterior-wide-top.png), [panel/kontrol](visualize-v6-screenshots/panel-controls.png) incelendi. Depo ve görev noktaları öncelikte; kontrol çakışması ve beyaz kenar boşluğu görülmedi. |
| Gerçek ROS/Gazebo/Nav2 koşusu | **HENÜZ TEST EDİLMEDİ**. Chrome gerçek WebGL kullanıyor; TF/WS verileri fixture. |

## Kısa FPS karşılaştırması

Aynı fixture, kamera ve kaliteyle, `trace=1` modunda benchmark event'i her browser RAF'ında eşit render talebi üretti. Yaklaşık 2,5 saniyelik kapalı/açık örnekleri:

| | Çevre kapalı | Çevre açık |
|---|---:|---:|
| Render FPS | 60,00 | 59,90 |
| Trace frame | 150 | 150 |
| Örnek süresi | 2.483,3 ms | 2.487,4 ms |
| Draw call | 233 | 246 |
| Üçgen | 18.748 | 26.918 |

Fark yaklaşık **−0,10 FPS**, **+13 draw call**, **+8.170 üçgen**. Bu, kısa yerel geliştirme sunucusu ölçümüdür; uzun süreli/başka donanımda FPS veya CPU/ölçek garantisi değildir. Çevre kapalıyken normal demand-render robot/TF/kamera güncellemeleriyle devam edebilir; bu dekoratif timer'ın çalıştığı anlamına gelmez. [Ham JSON](visualize-v6-screenshots/exterior-render-cost.json).

[Komut eki](visualize-v6-commands-2026-11-17.md) · [Teknik tasarım](../../design/c5-3d-operations.md#visualize-v6--yaşayan-dış-çevre-17-kasım-2026).
