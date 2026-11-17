# Visualize V5 — minimal dış çevre ve mal akışı

**17 Kasım 2026 · `feature/visualize` · commit/push yapılmadı.** Yalnız Three.js sunumu, ilgili frontend testi ve dokümantasyon değiştirildi. Worktree'deki önceden mevcut YAML, bridge, observer ve V1–V4 değişiklikleri korunmuştur.

## Önkoşul ve duvar incelemesi

V5'e başlamadan güncel V4 üzerinde üretim build'i ve Chrome V1–V4 regresyonu **2/2 geçti**. Yeniden alınan [V4 eğik görüntüsü](visualize-v5-screenshots/v4-baseline-overview.png) ve üstten görüntü incelendi; boş canvas veya render sorunu görülmedi.

Sevkiyat yanındaki `wall_east_1`, yalnız dekoratif bir duvar değildir. `fleet_config/warehouse.py::walls()` fiziksel duvarları üretir; `obstacles()` bunları içerir ve `scene_payload()` aynı sınırları frontend'e verir. `fleet_config/occupancy.py::raster()` bu engelleri dolu hücreye çevirir; `warehouse_assets.py::static_box()` hem collision hem visual üretir. Mevcut profil yalnız batıdaki mal kabul kapısını açık tanımlar. Dolayısıyla doğudaki görsel duvar, gerçek harita engelinin yansımasıdır; inceleme kaynak kodu/konfigürasyon üzerinden yapılmıştır, yeni Gazebo koşusu değildir.

Yalnız frontend'deki duvar kopyası, sevkiyat bölgesinden türetilen merkezde (map y = −5,5 m) 2,4 m genişlikte bölündü. Alçak eşik ve üst kiriş kalır. Dışındaki **kapalı** yükleme kapısı ve yükseltilmiş platform lojistik cephesidir; yeni robot geçişi, koridor, istasyon veya hedef yoktur. Ortak layout nesnesi değiştirilmez. Batıdaki mal kabul açıklığı değiştirilmedi; dışına yalnız platform ve tek sabit kamyon eklendi. Gazebo/Nav2/TF/collision/YAML/harita bu görevde değiştirilmedi.

## Uygulama ve görünüm

- Gri-yeşil geniş dış zemin, birkaç nötr kesik yol çizgisi, dört küçük köşeli ağaç ve iki yükleme platformu eklendi. Kamyon yalnız mal kabul tarafında ve hareketsizdir. Harici asset/lisans bağımlılığı yoktur.
- Dış öğelerde ALMA turkuazı ve BIRAKMA amberi kullanılmaz; ek akış oku, animasyon, ışık veya post-processing yoktur. V4'ün shadow map kapalı ayarı korunur. Kutu detayları instanced, ağaç geometri/malzemeleri paylaşımlıdır.
- Dış kök depo kamera sınırlarının dışındadır. Varsayılan kamera ile sığdırma algoritması korunur; bu nedenle kenardaki dış nesneler kısmen kırpılabilir. [Elle uzaklaşılan çevre görünümü](visualize-v5-screenshots/exterior-wide.png), varsayılan kadrajın değişmesi değildir.
- **Çevreyi göster** alt araç satırındadır. Kapalıyken tüm dış kök gizlenir, eski arka plan döner; [sevkiyat açıklığı kalır](visualize-v5-screenshots/top-environment-off.png). Dış mesh'lerin raycast'i kapalıdır. Robot/nokta görüş çizgisini kesen dış nesneler gizlenir.

## Doğrulama

| Kontrol | Sonuç |
|---|---|
| TypeScript + Vite build | **DOĞRULANDI**. Mevcut Zod annotation uyarıları build'i engellemedi. |
| V1–V5 Chrome regresyonu | **2/2 geçti**. Üç TF fixture robotu, durum/yaw, seçim, görev hover/click, park etiketleri, V4 yüzeyleri korunuyor. |
| Profil regresyonu | **4/4 geçti**; hash, kesinti, doğrulanmış geometri, nokta rolleri ve zemin adları. |
| TF/Path kaynak ayrımı | **1/1 geçti**; epoch sınırında plan temizliği. |
| Çevre aç/kapa ve kamera | Serbest, üstten, takip ve filoyu sığdırma modlarında kamera/target sayısal tolerans içinde aynı; noktalar aynı. Açıklık kapalı çevrede de kalıyor. |
| Görsel inceleme | [Eğik](visualize-v5-screenshots/overview.png), [üstten](visualize-v5-screenshots/top.png), [geniş](visualize-v5-screenshots/exterior-wide.png) ve [panel/kontrol](visualize-v5-screenshots/panel-controls.png) Chrome ekran görüntüleri incelendi. Çevre açıkken kenarlarda beyaz boşluk yok; panel öğeleri çakışmıyor. |
| Kısa maliyet karşılaştırması | Aynı fixture/kamerada, 2,5 sn kapalı/açık pencereleri: 233 → 242 draw call, 18.748 → 19.282 üçgen (**+9 / +534**). Trace 54 → 56 frame; demand render ve tek kısa örnek nedeniyle sürekli FPS veya ölçek garantisi değildir. [Ham kayıt](visualize-v5-screenshots/exterior-render-cost.json). |
| Gerçek ROS/Gazebo/Nav2 canlı görev | **HENÜZ TEST EDİLMEDİ**; bu görev mock verili gerçek Chrome/WebGL görsel doğrulamasıdır. |

İlk iki genişletilmiş test koşusunda 5/6 geçti: birinde test kamera modu işlenmeden önce örnek aldı; diğerinde target'ın kayan nokta farkı yaklaşık 5×10⁻¹⁷ idi. Test artık önce beklenen modu/kararlı kamerayı bekler ve 10 ondalık hassasiyetle karşılaştırır. Son koşu 6/6; ayrı TF/Path testiyle toplam 7/7. Taslak build'deki tuple tür hatası giderildi; son build geçti. Fixture dışında kalan task-catalog/WS isteklerinde yerel API olmadığı için proxy ECONNREFUSED uyarıları görüldü; canlı backend kanıtı sayılmaz.

[Komut eki](visualize-v5-commands-2026-11-17.md) · [Teknik tasarım](../../design/c5-3d-operations.md#visualize-v5--minimal-dış-çevre-17-kasım-2026).
