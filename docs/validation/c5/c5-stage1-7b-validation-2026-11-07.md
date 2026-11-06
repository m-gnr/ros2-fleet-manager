# C5 Aşama 1.7B — Hazır 3D depo entegrasyonu

**7 Kasım 2026** · [Komutlar ve ölçüm yöntemi](c5-stage1-7b-commands-2026-11-07.md) · [C5 3D görünüm tasarımı](../../design/c5-3d-operations.md)

Yerel ve uzak `feat/c5-dashboard-ui-polish` uçları `b7fcb05c3cbcc24aaa6439ff494e459bc4d4549f` ile eşleşti. `feat/c5-warehouse-model-integration` bu commit’ten ayrı worktree’de açıldı.

## Model ve lisans

| Alan | Kayıt |
|---|---|
| Model | 3DAssets.dev Hardware Store and DIY Warehouse Starter Scene, yayıncı sayfasındaki adıyla DIY warehouse aisle |
| Yayıncı sürümü | Varlık 23990, v1 |
| Lisans | CC0 1.0 Universal. Yayıncının hem model sayfasında hem lisans sayfasında doğrulandı. |
| SHA-256 | `972056d2f10d432afeb1d52083186e3a02c1b045bf68dbc6d4d47de8c568bb98` |
| Dosya | [Yerel GLB](../../../frontend/src/scene/assets/warehouse-aisle.glb), 2.012.360 bayt. Vite üretim derlemesinde aynı kaynaktan sunulan hash’li dosya. |

Kaynaklar [yayıncı model sayfası](https://3dassets.dev/assets/hardware-store-and-diy-warehouse-warehou-f3ddb545-starter-scene), [GLB v1](https://cdn.3dassets.dev/assets/23990/v1/model.glb), [yayıncı lisansı](https://3dassets.dev/license) ve [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

- Arka sırada `006–024` ve `026–028` gruplarındaki raf dikmeleri, kirişler, tabla, dolu/boş palet, kasa ve koruyucular kaldı. Kirişler dikmelere ulaşacak şekilde X ekseninde iki kat genişletildi ve üçüncü göz için bir üst raf tekrarlandı. Arka sıra yaklaşık 2,5 m yüksekliğe indirildi.
- Sol çevreye `026` boş palet, `031` platform arabası ve `035` transpalet alındı. `000–005` model zemin karoları, `025` ikinci kasa, `029–030` yüksek/askılı tabelalar ve `032–034` kereste, kolon ve ayna çıkarıldı. Açık gri platform, çizgiler ve arka sıra gölgesi R3F sahnesinde çiziliyor. Standart ve düşük kalite kontrolleri korundu.
- `GLTFLoader` yerel GLB’yi asenkron açıyor. Kullanılan geometri dönüşümleri malzeme gruplarına bir kez uygulanıyor. Malzeme başına bir mesh çiziliyor. İlk kare ve model yükleme hatası için şematik raflar ile platform çalışmaya devam ediyor.

## Koordinatlar ve kamera

- Dekor kendi grubunda. Robotlar, Nav2 yolu, TF izi ve operasyon işaretleri map çerçevesinde `(x, y) → (x, 0, −y)` dönüşümünü kullanıyor. Robot yönü ve Burger ölçüleri korundu. **Temsili 3D depo** ve **Salt okunur** etiketleri görünür. Raflar yalnız görsel geometri.
- Şarj işareti şimşek, park işareti P, alım üçgen ve teslim elmas çerçeve. İstasyon konumu, kimliği, türü, durumu ve varsa sahibi doğrulanmış snapshot’tan geliyor. Ürün akışı kesilince son eşitleme belirtiliyor ve canlı sahiplik bilgisi kaldırılıyor. Konumu eksik veya map dışı kayıt çizilmiyor.
- Seçili robotun etkin görevi öncelikli. Ardından ilk atanmış/yürüyen görev, bunlar yoksa ilk kuyruktaki görev gösteriliyor. Tek görev çifti etiketleniyor. Görevsiz görünümde görev işareti bulunmuyor. Robot etiketleri öncelikli ve yakın robotlarda 26 px işaretler TF köklerinde kalıyor.
- Şematik ve GLB düzenleri için kadraj, gerçek çizim geometrisinin yatay ve dikey sınırlarına göre hesaplanıyor. GLB tamamlandığında dokunulmamış Serbest veya Üstten kadraj güncelleniyor. Elle düzenlenen kamera yükleme ve resize boyunca korunuyor. Takip geçişi hareketli robotun güncel hedefine göre tamamlanıyor. Filo kadrajı robotlara odaklanıyor.

## Chrome ve ekran görüntüleri

**DOĞRULANDI.** Üretim derlemesi ve gerçek Chrome Playwright paketi geçti. 19 test arasında map konumu ve görev önceliği, yerel GLB ile elle düzenlenen kameranın korunması, GLB isteği başarısızken şematik depo ve canlı TF ile devam bulunuyor. İlk test koşusunda iki geometri testi model hazır olmadan kamera örneği aldığı için başarısız oldu. Bu testler GLB çizimini bekledikten sonra 19/19 geçti. [Üretim derlemesi](stage1-7b/build.log) · [Chrome test çıktısı](stage1-7b/playwright.log)

| Viewport | Aşama 1.6 | Aşama 1.7B |
|---|---|---|
| 1280×850 | [Önce](stage1-7b/before/viewport-1280.png) | [Sonra](stage1-7b/after/viewport-1280.png) |
| 1440×900 | [Önce](stage1-7b/before/viewport-1440.png) | [Sonra](stage1-7b/after/viewport-1440.png) |
| 1920×1080 | [Önce](stage1-7b/before/viewport-1920.png) | [Sonra](stage1-7b/after/viewport-1920.png) |
| 390×844 | [Önce](stage1-7b/before/viewport-390.png) | [Sonra](stage1-7b/after/viewport-390.png) · [Tam sayfa](stage1-7b/after/mobile-full.png) |

1440×900 fixture görselleri [şarj](stage1-7b/after/charging.png), [seçili robot](stage1-7b/after/selected.png), [etkin alım/teslim, Nav2 ve TF izi](stage1-7b/after/task-plan-trail.png), [takip](stage1-7b/after/follow.png), [üstten](stage1-7b/after/top.png), [STALE](stage1-7b/after/stale.png) ve [bağlantı kesintisi](stage1-7b/after/disconnected.png).

Çizim geometrisinin ekran doluluğu iki eksende ölçüldü. Dört viewport’ta iki sürümün de varsayılan kadrajı geometriyi kırpmadı. 1440×900’de arka sıranın yüksekliği dikey sınırı belirliyor. Mobilde yatay sınır belirleyici. [Aşama 1.6 projeksiyonu](stage1-7b/before/framing.json) · [Aşama 1.7B ölçümleri](stage1-7b/after/metrics.json)

| Viewport | Yatay doluluk önce → sonra | Dikey doluluk önce → sonra |
|---|---:|---:|
| 1280×850 | %90,0 → %83,4 | %91,7 → %94,0 |
| 1440×900 | %88,4 → %80,5 | %94,0 → %94,0 |
| 1920×1080 | %82,2 → %74,8 | %94,0 → %94,0 |
| 390×844 | %90,0 → %90,0 | %53,6 → %60,4 |

## Performans

Üretim Vite build’leri, yerel gerçek Google Chrome 156.0.8078.80, Apple M3, ANGLE Metal WebGL2, DPR 1 ve standart sahne kalitesi. Her çözünürlükte ayrı tarayıcı bağlamı. Aynı C5 snapshot fixture’ı 2 Hz, iki TF akışı 10 Hz, bir sabit ve bir hareketli robot. Ölçüm penceresi 5 sn. Plan ve iz katmanları açık, Nav2 planı etkileşim kaydında ayrıca gönderildi. Tarayıcı RAF ve talep üzerine gerçekleşen 3D çizimler ayrı ölçüldü.


| Viewport | Sahne FPS | Sahne p95 aralığı, ms | Çağrı p95 | Geometri/doku | Chrome RSS, MiB | JS heap, MiB | İlk 3D kare, sn | GLB istek → çizim, ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1280×850 | 35,9 → 36,8 | 66,7 → 66,7 | 52 → 63 | 52/3 → 63/3 | 1059,5 → 1105,0 | 12,0 → 15,1 | 7,3 → 5,7 | 32,0 |
| 1440×900 | 37,4 → 37,8 | 66,7 → 65,5 | 52 → 63 | 52/3 → 63/3 | 1070,2 → 1113,0 | 11,8 → 10,8 | 6,3 → 3,8 | 34,1 |
| 1920×1080 | 37,1 → 37,3 | 66,2 → 66,8 | 52 → 63 | 52/3 → 63/3 | 1080,3 → 1075,6 | 11,8 → 14,8 | 6,3 → 4,9 | 37,5 |
| 390×844 | 36,7 → 36,8 | 66,8 → 66,7 | 52 → 63 | 52/3 → 63/3 | 1085,5 → 1072,3 | 12,5 → 17,7 | 6,3 → 6,5 | 33,6 |

- Soldan sağa değerler Aşama 1.6 ve 1.7B sırasındadır. İlk 3D kare, sayfa başlangıcına göre ilk çizim çağrısının zamanıdır. GLB sütunu ilk varlık isteğinden modelin ilk çizimine kadar indirme, ayrıştırma ve gruplamayı kapsar. Yerel indirme 5–8 ms sürdü. İlk GLB çizimi 1440×900’de 3,83 sn’de gerçekleşti. Başlangıç süresi tek örnekli ve değişken.
- Tüm viewport’larda tarayıcı RAF yaklaşık 60 FPS, RAF p95 16,7–16,8 ms. 1440×900’de çizilen üçgen p95 değeri 4.464 → 73.026. Bütünleşik sahne 63 çağrıda kaldı. Araştırmadaki ham modelin 101 çağrısı ayrı, tek model ölçümüdür. Canlı C4.5 akışında 1440×900’de iki rota katmanı açıkken 55,8 sahne FPS’i, 19,1 ms p95 ve 68 çizim çağrısı ölçüldü. [Önce ham ölçüm](stage1-7b/before/metrics.json) · [Sonra ham ölçüm](stage1-7b/after/metrics.json) · [Canlı ölçüm](stage1-7b/live/browser-metrics.json)
- 1440×900’de seçim komutundan çizilmiş seçime 99 → 96 ms. Kamera tıklamasından geçiş sonuna takip 633 → 632 ms, üstten 640 → 642 ms, filo kadrajı 633 → 646 ms ve sıfırlama 616 → 617 ms. Bu eşli ölçümde takip geçişi için TF konumu kısa süre sabitlendi. Yeni derleme sürekli hareketli fixture’da ve canlı koşuda ayrıca takip edildi.

## Canlı C4.5 Fortress

**DOĞRULANDI.** İki robot hareket etti ve fiziksel şarjı ayrı ayrı aldı. `c45-low`, `c45-parallel` ve `c45-urgent` tamamlandı. Şarj devri ve C4.5 güvenli kesme senaryosu mevcut akışla yürütüldü. Canlı kaynak, aynı damgalı C4 `BatteryState` SoC/Wh alanları ile, görev durumu ve istasyon sahipliği de SQLite ile eşleşti. Chrome şarj sahibini ve batarya değerini gösterdi. [Chrome sonucu](stage1-7b/live/chrome.log) · [C4.5 ve C5 olayları](stage1-7b/live/c4-c5-events.log) · [Doğrulanmış kaynak](stage1-7b/live/verified-source.json)

- Bağımsız ROS okuyucuları 4.728 aynı damgalı TF pozu ve 127 Nav2 planı eşleştirdi. En büyük konum farkı `4,44 × 10⁻¹⁶ m`, en büyük yön farkı `8,88 × 10⁻¹⁶ rad`. Chrome’da 356 çizilmiş robot pozu ve yönü relay’e karşı doğrulandı. Nav2 planı ve TF izi köşe noktaları aynı akıştan gelen örneklerle karşılaştırıldı. [Bağımsız TF/Path karşılaştırması](stage1-7b/live/ros-chrome-compare.json)
- Chrome’da 11.166 istasyon veya görev işareti örneği C5 snapshot’ıyla eşleşti. `dock_1` dünya konumu `(0,5; 0; 2)`, `park_1` `(−2; 0; −1)`. Bu iki konum hem `fleet.yaml` hem SQLite rezervasyon kaydıyla, çizilen iki görev çiftinin konumları ve yönleri SQLite görev kayıtlarıyla bağımsız eşleşti. `c45-urgent` tamamlanmış görev listesinde doğrulandı ve kaydedilen öncelikli işaret çiftleri arasında yer almadı. [Chrome noktaları](stage1-7b/live/chrome-operation-points.json) · [Bağımsız nokta karşılaştırması](stage1-7b/live/independent-operation-points.json)
- İzole TF kesintisinde ilgili robot STALE oldu. API durduğunda canlı batarya gizlendi, istasyon etiketleri son eşitlemeye geçti ve API yaklaşık 1,11 sn içinde yeni backend oturumuyla eşitledi. Chrome sayfası kapatılıp tekrar açıldığında Fleet Manager kaynak oturumu aynı kaldı ve kaynak dizisi ilerledi. SQLite bütünlük kontrolü `ok` döndürdü ve üç konteyner kod 0 ile kapandı. [Canlı tarayıcı ölçümleri](stage1-7b/live/browser-metrics.json) · [SQLite](stage1-7b/live/sqlite-check.txt) · [Kapanış](stage1-7b/live/shutdown.txt)

Canlı görseller [genel depo](stage1-7b/live/isometric-two-robots.png), [fiziksel şarj](stage1-7b/live/charging-scene.png), [Nav2 ve TF izi](stage1-7b/live/active-task-plan.png), [seçili robot](stage1-7b/live/selected-robot.png), [takip](stage1-7b/live/camera-follow.png), [üstten etkin alım ve teslim](stage1-7b/live/camera-top.png), [izole TF STALE](stage1-7b/live/isolated-tf-stale.png) ve [bağlantı kesintisi](stage1-7b/live/connection-loss.png).

## Sınırlamalar

- Yalnız sunum geometrisi ve iki robotlu kabul koşusu doğrulandı. Canlı kaynak kesintileri, 3D işaretlerin veri güvenilirliğini gösterir. Aktif Nav2 goal ilişkisi mevcut Durum B kapsamındadır.
- Mobilde pano dikey kayar. Dar viewport’ta veya robotlar ve operasyon noktaları üst üste geldiğinde çakışan etiketler gizlenebilir. İstasyon detayları mevcut İstasyonlar / Şarj görünümünden okunabilir. Yakın çekim takip ve filo kadrajı robot alanına odaklanır.
- GLB yerelden soğuk yüklenirken şematik depo kısa süreli görünebilir. Ölçüm tek Chrome/macOS sistemini ve kısa pencereleri kapsar. Uzun süreli dayanıklılık, 3+ robot veya başka tarayıcılar **HENÜZ TEST EDİLMEDİ**.
