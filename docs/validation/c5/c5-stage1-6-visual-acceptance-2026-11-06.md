# C5 Aşama 1.6 görsel kabul düzeltmesi

**6–7 Kasım 2026** · [Komutlar ve ölçüm betiği](c5-stage1-6-visual-commands-2026-11-06.md) · [Önceki Aşama 1.6 kaydı](c5-stage1-6-validation-2026-11-06.md)

Arayüz ve ilgili testler `6ea81ee` commit’inde. Ölçüm tabanı `feat/c5-dashboard-ui-polish` dalındaki `51ad28d1859fd5c363f41a6359da21981ebe81fa` commit’i. Dalın kendi worktree’si başlangıçta temizdi. Başlangıç üretim build’i kaynak değişikliğinden önce alındı ve dört iç viewport’ta ölçüldü. Aynı build karşılaştırma kanıtında yeniden kullanıldı.

## Ölçüm düzeni

- Gerçek Google Chrome 156.0.8078.80, headless, Apple M3 üzerinde ANGLE Metal GPU WebGL2. Tarayıcı ve canvas DPR 1. Görsel kalite standart, ilk kamera Serbest, plan ve TF izi katmanları açık.
- Üretim build’leri aynı Vite/Three.js lockfile ile sunuldu. WebSocket fixture’ında `robot_alpha` TF konumu `(-2, 1)`, `robot_beta` TF konumu `(2, -1)`, iki yaw değeri de π/2. TF 10 Hz, ürün snapshot’ı 2 Hz. Normal kareler iki doğrulanmış TF pozu çizildikten ve arayüzde `2 / 2 TF LIVE` göründükten sonra alındı.
- Zemin kutusunun dünya sınırları `x,z ∈ [-7, 7] m` ve `y ∈ [-0,175, -0,025] m`. Raf çerçeveleri `x ∈ [-5,1325, 5,1325] m`, `z ∈ [-5,3625, 5,3625] m` ve `y ∈ [0, 1,58] m`. Kasalar dahil en yüksek kutu 1,652 m. Üretim sahnesinin zemin, çevre ve raf bileşenlerinden alınan 252 kutunun 2.016 köşesi, çizilmiş kamera konumu, hedefi, 42° FOV ve canvas en-boy oranından kurulan Three.js projeksiyonuyla CSS pikseline çevrildi. Yatay ve dikey sınır açıklıkları kendi canvas eksenlerine bölündü. Dört başlangıç kadrajında ve dört düzeltme kadrajında geometri viewport içinde kaldı. Kesikli mor dikdörtgenler zemin ve raf siluetlerinin uçlarıyla örtüşüyor.
- DOM yerleşimi `getBoundingClientRect()` ve `getComputedStyle()` ile ölçüldü. Eski halka için 0,238 m dış yarıçapın projekte edilmiş yatay ve dikey açıklığı, yeni halka için CSS kutusu kullanıldı. İşaret merkezi ve yönü, aynı kamera altında TF kökü ve ileri yön vektöründen bağımsız hesaplandı.

## Görsel sonuçlar

| Metrik | 1280×850 önce → sonra | 1440×900 önce → sonra | 1920×1080 önce → sonra | 390×844 önce → sonra |
|---|---:|---:|---:|---:|
| Depo yatay doluluğu | %68,4 → %90,0 | %66,0 → %88,4 | %62,4 → %82,2 | %90,0 → %90,0 |
| Depo dikey doluluğu | %90,0 → %91,7 | %90,0 → %94,0 | %90,0 → %94,0 | %67,3 → %53,6 |
| Robot işareti minimum çapı (yatay × dikey, px) | 14,4 × 7,6 → 26 × 26 | 15,8 × 8,3 → 26 × 26 | 21,0 × 11,0 → 26 × 26 | 7,5 × 4,2 → 26 × 26 |
| Etiket yüksekliği (px) | 19 → 18 | 19 → 18 | 19 → 18 | 19 → 18 |
| Sağ panel ve sahne dış yükseklik farkı (px) | 217,0 → 0,0 | 263,0 → 0,0 | 442,6 → 0,0 | Ayrı satırlar |
| Üst bölüm (px) | 170,0 → 112,9 | 174,0 → 112,9 | 174,4 → 112,9 | 259,2 → 186,1 |
| 3D canvas yüksekliği (px) | 493,0 → 535,1 | 539,0 → 585,1 | 718,6 → 765,1 | 327,6 → 327,6 |
| Canvas yüksekliği değişimi (px ve yüzde) | 42,1 px · %8,5 | 46,1 px · %8,6 | 46,5 px · %6,5 | 0,0 px · %0,0 |
| Sahne dış kutu yüksekliği (px) | 577,0 → 628,1 | 623,0 → 678,1 | 802,6 → 858,1 | 428,0 → 475,0 |
| Son filo kartı alt boşluğu (px) | 15,0 → 15,0 | 15,0 → 15,0 | 15,0 → 15,0 | -0,2 → 18,0 |
| scrollHeight / innerHeight (px) | 850 / 850 → 850 / 850 | 900 / 900 → 900 / 900 | 1080 / 1080 → 1080 / 1080 | 1229 / 844 → 1231 / 844 |
| scrollWidth / innerWidth (px) | 1280 / 1280 → 1280 / 1280 | 1440 / 1440 → 1440 / 1440 | 1920 / 1920 → 1920 / 1920 | 390 / 390 → 390 / 390 |
| Minimum kritik font-size (px) | 8 → 12 | 8 → 12 | 8 → 12 | 8 → 12 |

Üst bölüm ölçüsü sayfanın başlangıcından sahne kartının üst sınırına kadar olan mesafedir. Panel farkı aynı satırdaki dış kutular arasındadır. Mobilde panel ayrı satıra geçer ve belge dikey kayar. Alt boşluk son filo kartı ile iç viewport’un alt sınırı arasındaki farktır.

Varsayılan kamera daha yatay bir çapraz açıyla yerleşir. Her köşe için derinlik `z`, eksen koordinatı `p`, hedef kaydırması `s`, yarı görüş açısının güvenli tanjantı `t` ve kamera mesafesi `d` kullanılır. Görünürlük koşulu `|p − s| ≤ (d − z)t`. Karşılıklı düzlemlerden `d_axis = (max(p + zt) − min(p − zt)) / (2t)` elde edilir. Hedef her eksende sınırların orta noktasına, mesafe iki eksenin daha kısıtlayıcı değerine alınır. Serbest kadraj sınırı yatayda %90 ve dikeyde %94. 1920×1080’de dikey sınır belirleyici. Yatay doluluk %82,2’de kalırken üstte ve altta yaklaşık 23 px geometrik pay kaldı. 390×844’te yatay sınır belirleyici. Yeni açı, o genişlikte daha sığ bir depo silueti veriyor. Kamera araçları, ön zemin köşesinin üstünü kapatmaması için sahne alt çubuğuna alındı.

Orbit, pan ve zoom sonrası resize testleri kullanıcı kamera konumu ve hedefini ayrı ölçtü. Sıfırlama, yeni canvas oranına göre hesaplanan başlangıç pozunu geri yükledi. Serbest, takip, üstten ve filo modları üretim build’inde çalıştırıldı.

Yakın fixture `(0, 0)` ve `(0,01, 0)` TF pozlarını kullandı. Her iki uzaklıkta işaret çapı **26 px**, etiket yüksekliği **18 px** ve etiket/işaret oranı **%69,2**. Seçili etiket öncelikli. Sığmayan veya çakışan etiket gizlenir. Seçili etiket üstte yer bulamazsa işaretin altında denenir. Halka ve yön oku, TF kökünün aynı ekran projeksiyonuna sabitlenir. Dünya koordinatında ofset 0 m. CSS kutu merkezi ile yeniden projekte edilen TF kökü ölçüm hassasiyetinde çakıştı. Fiziksel Burger gövde geometrisi, boyutu, TF kök dönüşümü ve ölçülen yaw korundu.

Kritik metinler 12–19 px. Alt filo kartları, panel kimliği ve durum rozeti, görev ve şarj alanları, TF, Nav2 durumu ve istatistik şeridinde minimum 12 px ölçüldü. Kritik yazıların tamamı bu aralıkta. Canlı telemetri ve şarj sayaçlarının `title` açıklamaları doğrulanmış kaynak ve C4 ölçümünü belirtir. Açılmış ayrıntı içeriği için kaydırma testi, başlığı ve robot kimliğini sabit tutarken iç bölümü kaydırdı.

## Nav2 gözlemi

`Güncel`, taban commit’inde `frontend/src/Operations.tsx:40` satırında yalnız `plan?.points` dolu olduğunda üretiliyordu. Aşama 1.5 aynı koşulda yalnız `Durum B` gösteriyor, plan yoksa `—` basıyordu. Ekran görüntülerinde farklı plan örnekleri varsa `—` ile `Güncel` birlikte açıklanır. Aynı plan örneğiyle fark yalnız sunum metnidir. Aynı fixture ile taze doğrulanmış plan, görev durumundan bağımsız olarak iki build’de de görünür. Güncel üretim noktası `frontend/src/Operations.tsx:40`.

| Robot | Plan yok | Doğrulanmış ve taze plan | Süresi dolmuş plan |
|---|---|---|---|
| Boşta | Plan yok | Gözlemlenen Nav2 planı · Güncel · Durum B | Bayat / Gizli |
| Görevde | Plan yok | Gözlemlenen Nav2 planı · Güncel · Durum B | Bayat / Gizli |

Altı kombinasyon Chrome’da doğrulandı. TTL dolarken TF LIVE tutuldu. Ayrı STALE ve bağlantı senaryoları da çalıştırıldı. Durum B açıklaması, aktif Nav2 hedefiyle ilişkinin doğrulanmadığını belirtir.

## Chrome performans gözlemi

| Viewport ve build | RAF FPS / p95 ms / örnek | Sahne FPS / p95 ms / örnek | Chrome CPU % | Chrome RSS MiB | JS heap MiB | Çizim çağrısı p95 | Geometri / doku |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1280×850 önce | 60,0 / 16,7 / 301 | 36,4 / 66,7 / 182 | 17,5 | 909,3 | 12,6 | 53 | 53 / 3 |
| 1280×850 sonra | 60,0 / 16,8 / 301 | 37,7 / 65,7 / 189 | 19,2 | 931,9 | 12,9 | 51 | 51 / 3 |
| 1440×900 önce | 60,0 / 16,8 / 301 | 37,2 / 66,5 / 185 | 15,8 | 864,2 | 12,7 | 53 | 53 / 3 |
| 1440×900 sonra | 60,0 / 16,7 / 301 | 36,1 / 66,6 / 181 | 17,6 | 959,9 | 12,7 | 51 | 51 / 3 |
| 1920×1080 önce | 60,0 / 16,7 / 301 | 37,1 / 66,5 / 186 | 17,3 | 894,7 | 12,7 | 53 | 53 / 3 |
| 1920×1080 sonra | 60,0 / 16,7 / 301 | 37,0 / 66,4 / 184 | 17,4 | 984,3 | 12,7 | 51 | 51 / 3 |
| 390×844 önce | 60,0 / 16,8 / 301 | 35,8 / 66,6 / 179 | 18,2 | 967,5 | 12,3 | 53 | 53 / 3 |
| 390×844 sonra | 60,0 / 16,8 / 302 | 37,9 / 66,0 / 190 | 18,0 | 982,9 | 12,5 | 51 | 51 / 3 |

Her viewport ve build için 5 sn pencere kullanıldı. RAF tarayıcı yenileme hızını, sahne FPS’i yalnız talep üzerine çizilen kareleri gösterir. Frame p95 ardışık zaman aralıklarından, CPU tarayıcı süreçlerinin toplam süresinden ve RSS aynı süreçlerin toplamından hesaplandı. Bellek sütunları MiB cinsindedir. Bu ölçümler yalnız 5 sn süreli sabit fixture yükünü kapsar.

## Test ve canlı kanıt

| Kontrol | Sonuç |
|---|---|
| Üretim build’i, Git kapsamı ve `git diff --check` | **DOĞRULANDI**. İlk commit’in kapsamı frontend sunumu ve testleri. |
| Chrome Playwright, üretim build’i | **DOĞRULANDI**. 16 geçti. [Test çıktısı](stage1-6-visual/playwright-verified.log) |
| Host Python ve Executor paketi | **DOĞRULANDI**. 416 geçti. Hostta ROS kurulumu gerektiren 28 vaka atlandı. [Test çıktısı](stage1-6-visual/host.log) |
| Humble/CycloneDDS seçili ROS regresyonu | **DOĞRULANDI**. 44 geçti. C5 salt okunur API, C4 batarya düğümü, batarya ve istasyon ROS zincirleri ile şarj senaryosu testleri. Starlette bir bağımlılık uyarısı üretti. [Test çıktısı](stage1-6-visual/ros-regression.log) |
| İki robotlu Fortress, C4.5 şarj ve C5 Chrome | **DOĞRULANDI**. Üç görev tamamlandı. İki robot hareket etti ve fiziksel şarj sahibi oldu. [Chrome çıktısı](stage1-6-visual/live/chrome.log) · [C4/C5 olayları](stage1-6-visual/live/c4-c5-events.log) |

- Canlı Chrome’da 1.885 çizilmiş poz ve yön, ROS relay örneklerine karşı doğrulandı. Bağımsız ROS okuyucularında 5.002 aynı damgalı TF pozu eşleşti. Konum farkı 0 m, en büyük yaw farkı `8,88 × 10⁻¹⁶ rad`. Robot 1 için 69, robot 2 için 73 Nav2 planı konu, damga ve tüm noktalar üzerinden eşleşti. [Bağımsız TF/Path karşılaştırması](stage1-6-visual/live/ros-chrome-compare.json)
- Seçim, takip, kamera sıfırlama, Durum B etiketi, izole TF STALE, köprü kesintisi ve API kesintisi sınandı. API tekrar açıldığında 1,11 sn içinde yeni backend oturumuyla eşitleme geldi ve Fleet Manager kaynak oturumu korundu. Tarayıcı sayfası kapalıyken kaynak dizisi ilerledi. [Canlı ölçümler](stage1-6-visual/live/browser-metrics.json) · [TF STALE](stage1-6-visual/live/isolated-tf-stale.png) · [Bağlantı kesintisi](stage1-6-visual/live/connection-loss.png) · [Takip](stage1-6-visual/live/camera-follow.png) · [Sıfırlama](stage1-6-visual/live/camera-reset.png) · [Nav2 planı](stage1-6-visual/live/active-task-plan.png)
- C4 batarya SoC ve Wh alanları aynı damgalı `BatteryState` ile, görev ve istasyon alanları SQLite kayıtlarıyla karşılaştırıldı. Güvenli preemption ve geç gelen terminal kontrolü C4.5 senaryosunda geçti. Üç konteyner çıkış kodu 0 ile durdu ve SQLite bütünlük kontrolü `ok` döndürdü. [Canlı depo](stage1-6-visual/live/isometric-two-robots.png) · [Şarj](stage1-6-visual/live/charging-scene.png) · [Görevler](stage1-6-visual/live/tasks.png) · [Kaynak snapshot’ı](stage1-6-visual/live/verified-source.json) · [Köprü grafiği](stage1-6-visual/live/bridge-graph.txt) · [Kapanış](stage1-6-visual/live/shutdown.txt) · [SQLite](stage1-6-visual/live/sqlite-check.txt)

İlk canlı koşuda Colcon hazırlığı tarayıcı bekleme süresini aştı. İkinci koşuda köprü kapanırken ürün kaynağı bataryayı kullanılamaz bildirdi. Son koşuda backend, iki Nav2 yaşam döngüsü yöneticisi ACTIVE olduktan sonra başlatıldı. Ürün kaynakları, Compose ve veri sözleşmesinin Git farkı boş. Tam C3 T01–T10 canlı matrisi, geniş Executor yaşam döngüsü ve C3 DDS action regresyonları bu koşunun seçkisi dışındaydı.

## Ekran görüntüleri ve ham ölçümler

| Viewport | Önce | Sonra | Projeksiyon |
|---|---|---|---|
| 1280×850 | [Önce](stage1-6-visual/before/viewport-1280.png) | [Sonra](stage1-6-visual/after/viewport-1280.png) | [Önce](stage1-6-visual/before/viewport-1280-projected.png) · [Sonra](stage1-6-visual/after/viewport-1280-projected.png) |
| 1440×900 | [Önce](stage1-6-visual/before/viewport-1440.png) | [Sonra](stage1-6-visual/after/viewport-1440.png) | [Önce](stage1-6-visual/before/viewport-1440-projected.png) · [Sonra](stage1-6-visual/after/viewport-1440-projected.png) |
| 1920×1080 | [Önce](stage1-6-visual/before/viewport-1920.png) | [Sonra](stage1-6-visual/after/viewport-1920.png) | [Önce](stage1-6-visual/before/viewport-1920-projected.png) · [Sonra](stage1-6-visual/after/viewport-1920-projected.png) |
| 390×844 | [Önce](stage1-6-visual/before/viewport-390.png) | [Sonra](stage1-6-visual/after/viewport-390.png) | [Önce](stage1-6-visual/before/viewport-390-projected.png) · [Sonra](stage1-6-visual/after/viewport-390-projected.png) |

| Senaryo | Önce | Sonra |
|---|---|---|
| Yakın iki robot | [Önce](stage1-6-visual/before/close-robots.png) | [Sonra](stage1-6-visual/after/close-robots.png) |
| Seçili robot | [Önce](stage1-6-visual/before/selected-robot.png) | [Sonra](stage1-6-visual/after/selected-robot.png) |
| Yakın robotlar, uzak kamera | [Önce](stage1-6-visual/before/close-robots-far.png) | [Sonra](stage1-6-visual/after/close-robots-far.png) |
| Elle zoom sonrası resize | [Önce](stage1-6-visual/before/manual-resize.png) | [Sonra](stage1-6-visual/after/manual-resize.png) |
| Kamera sıfırlandı | [Önce](stage1-6-visual/before/camera-reset.png) | [Sonra](stage1-6-visual/after/camera-reset.png) |
| TF STALE | [Önce](stage1-6-visual/before/tf-stale.png) | [Sonra](stage1-6-visual/after/tf-stale.png) |
| Bağlantı kesildi | [Önce](stage1-6-visual/before/connection-loss.png) | [Sonra](stage1-6-visual/after/connection-loss.png) |
| Plan yok | [Önce](stage1-6-visual/before/plan-none.png) | [Sonra](stage1-6-visual/after/plan-none.png) |
| Taze plan | [Önce](stage1-6-visual/before/plan-fresh.png) | [Sonra](stage1-6-visual/after/plan-fresh.png) |
| Bayat plan | [Önce](stage1-6-visual/before/plan-stale.png) | [Sonra](stage1-6-visual/after/plan-stale.png) |

[Önce ham ölçümler](stage1-6-visual/before/metrics.json) · [Sonra ham ölçümler](stage1-6-visual/after/metrics.json)
