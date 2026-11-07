# C5 Aşama 1.7D — Depo duvarları ve operasyon bölgeleri

**7 Kasım 2026** · [Doğrulama komutları](c5-stage1-7d-commands-2026-11-07.md) · [3D görünüm tasarımı](../../design/c5-3d-operations.md)

`feat/c5-warehouse-zones-and-walls` dalı, doğrulanmış 1.7C commit’i `b21c642` üzerinden ayrı worktree’de açıldı. Önce ve sonra görüntüleri aynı Chrome üretim ölçüm akışını kullanıyor. Kod ve test değişiklikleri `1ab5b3a` commit’inde frontend ile sınırlı.

## Yerleşim

1.7C GLB’sinde arka rafın X aralığı −3,84…3,85 m, Z aralığı −5,36…−4,48 m ve yüksekliği 1,96 m idi. Sol raf X’te −5,39…−4,51 m, Z’de −2,02…2,31 m aralığındaydı. Eski koşuda bağımsız TF örnekleri X’te yaklaşık −3,52…2,57 m, Z’de −3,14…2,43 m aralığındaydı. Nav2 planları X’te yaklaşık −3,70…2,55 m, Z’de −3,30…2,50 m aralığındaydı. Çalışmanın başında kamera, GLB sınırları, `fleet.yaml` istasyonları ve görev işaretlerinin snapshot seçimi incelendi. [1.7C geometri kaydı](stage1-7c/geometry.json) · [Başlangıç 1440×900](stage1-7d/before/viewport-1440.png)

Arka cephede 2,41 m yüksekliğe çıkan açık gri kaplama, metal dikmeler ve sağ uçta **Yükleme 01** kepengi var. Sol duvar raf boyunca 1,76 m’ye çıkıyor ve öne doğru alçalıyor. Sağ bölme en yüksek arka ucunda 0,99 m, kameraya yakın uçta yaklaşık 0,32 m. Ön cephe açık. Sol ve arka GLB rafları mevcut yerlerinde, ön sağ palet sırası 0,16 m daha dışarıda. Sarı güvenlik çizgileri, kepenk önü şeridi, yaya işaretleri ve **A01/A02** ile **K01/K02** yazıları bölümleri ayırıyor. Koridorlar ve duvarlar sunum geometrisi. [Dünya uzayında dekor kutuları](stage1-7d/geometry.json)

İlk görsel turda yükleme yazısı zeminde küçük kalıyordu. Yazı kepenk üstündeki kontrastlı panoya taşındı. 1440×900 son görüntüsünde bütün ana ekran dikey kaydırma gerektirmeden yerleşiyor. Kapı ve raflar depo çevresini tanımlıyor. Dört alan ayrı renk ve simgelerle okunuyor, robotlar sahne ortasında seçilebilir kalıyor. [İlk düzenleme turu](stage1-7d/iteration-1440.png) · [Son 1440×900](stage1-7d/after/viewport-1440.png)

## Operasyon bölgeleri

| Bölge | Zemin | Simge ve kaynak |
|---|---|---|
| Şarj | Teal | Şimşek, istasyon kimliği ve snapshot durumu |
| Park | Gri-mavi | P, istasyon kimliği ve park yönü |
| Alım | Mavi | Paket ve yukarı ok, öncelikli görevin alım noktası |
| Teslim | Mor | Paket ve aşağı ok, aynı görevin teslim noktası |

Alanlar 0,92 m genişliğinde, kesik köşeli kare ve zeminle hizalı. Boya genişliği görsel bir ölçü. Aynı noktaya gelen alım ve teslim çifti kareyi ikiye bölüyor. Görev seçimi seçili robotun etkin görevini, diğer etkin görevi ve kuyruk sırasını izliyor. Görev yoksa alım ve teslim alanları kaldırılıyor.

`dock_1` ROS map pozu **(0,50; −2,00) m**, Three.js konumu **(0,50; 0; 2,00) m**, yaw **0 rad**. `park_1` map pozu **(−2,00; 1,00) m**, Three.js konumu **(−2,00; 0; −1,00) m**, yaw **1,57 rad**. İstasyonlar canlı snapshot üzerinden çizildi, konum ve yönler `fleet.yaml` ile SQLite rezervasyon kayıtlarına karşı doğrulandı. Şarj ünitesi istasyonun yerel ileri ekseninde merkezden 0,57 m uzakta. Sahiplik ve fiziksel şarj vurgusu mevcut C4 ve telemetri güncellik kontrollerine bağlı. Kesintide istasyon etiketi **Son eşitleme** gösteriyor. [Bağımsız istasyon ve görev karşılaştırması](stage1-7d/live/independent-operation-points.json) · [Canlı şarj ve görevsiz sahne](stage1-7d/live/charging-scene.png)

## Chrome ve kamera

**DOĞRULANDI.** Chrome 156.0.8078.80 üretim önizlemesinde 21/21 Playwright testi geçti. Kapsam alan ölçüsü, snapshot dönüşümü, aynı pozdaki görev işaretleri, görevsiz görünüm, GLB ve şematik yedek, beş kamera işlemi, elle düzenlenen kamera, 26 px robot işareti, STALE ve bağlantı kaybını içeriyor. [Derleme çıktısı](stage1-7d/build.log) · [Chrome test çıktısı](stage1-7d/playwright.log)

- Burger ölçeği, TF kökü ve yön işareti korunuyor. Kamera arkaya çevrilip dekor gövdeye görüşü kapattığında ilgili duvar ve stok grubu kesiliyor. Sıfırlamada tüm dekor yeniden kadraja giriyor. Kesit kararı ihtiyatlı grup kutularına dayanıyor.
- Serbest, takip, üstten, filo kadrajı ve sıfırlama çalıştı. Otomatik genel ve üstten kadraj, dekorun tam sınırlarını kullanıyor. Elle ayarlanan açı, pan ve zoom yeniden boyutlandırma ve GLB geçişinde korundu. [Takip](stage1-7d/after/follow.png) · [Üstten](stage1-7d/after/top.png)

| Boyut | Son Chrome görüntüsü |
|---|---|
| 1280×850 | [Genel görünüm](stage1-7d/after/viewport-1280.png) |
| 1440×900 | [Genel görünüm](stage1-7d/after/viewport-1440.png) |
| 1920×1080 | [Genel görünüm](stage1-7d/after/viewport-1920.png) |
| 390×844 | [Viewport](stage1-7d/after/viewport-390.png) · [Tam sayfa](stage1-7d/after/mobile-full.png) |

## Performans

Apple M3, ANGLE Metal WebGL2, DPR 1 ve standart kalite. Her boyutta aynı kontrollü akış 5 sn örneklendi. Sahne talep üzerine çizildiği için çizilen sahne kareleri ve tarayıcı RAF ayrı ölçüldü. [Başlangıç ölçümü](stage1-7d/before/metrics.json) · [Son ölçüm](stage1-7d/after/metrics.json)

| Viewport | Son yatay × dikey kadraj doluluğu | Sahne FPS, önce → sonra | Kare aralığı p95, ms | Çizim çağrısı p95 |
|---|---:|---:|---:|---:|
| 1280×850 | %70,2 × %94,0 | 37,5 → 36,2 | 66,5 → 66,7 | 68 → 83 |
| 1440×900 | %67,7 × %94,0 | 37,3 → 36,8 | 66,7 → 66,5 | 68 → 83 |
| 1920×1080 | %62,6 × %94,0 | 37,4 → 36,6 | 66,8 → 67,0 | 68 → 83 |
| 390×844 | %90,0 × %76,4 | 37,3 → 35,6 | 66,6 → 66,8 | 68 → 83 |

Dört boyutta dekor kırpılmadı ve yatay taşma görülmedi. Tarayıcı RAF yaklaşık 60 FPS kaldı. Duvarlar instance edildi. Raflar, kesit sırasında ayrı gizlenebilmeleri için dekor bölümü ve malzemeye göre gruplandı.

## Canlı iki robotlu Fortress

**DOĞRULANDI.** `robot_1` ve `robot_2` hareket etti ve sırayla fiziksel şarj aldı. `c45-low`, `c45-parallel` ve `c45-urgent` tamamlandı. Chrome 11.338 istasyon veya görev noktası çizimini kaynak snapshot’la eşleştirdi. Görüntülenen iki görev çiftinin koordinatları SQLite’a karşı bağımsız doğrulandı. Nav2 planı ve TF izi kaynak koordinatlarıyla eşleşti. [Kaynak snapshot karşılaştırması](stage1-7d/live/verified-source.json) · [Canlı Chrome sonucu](stage1-7d/live/chrome.log) · [Görev, Nav2 ve TF izi](stage1-7d/live/active-task-plan.png)

- Bağımsız ROS okuyucularıyla 4.659 aynı damgalı TF pozu ve 138 birebir Nav2 planı eşleşti. En büyük konum farkı 4,44 × 10⁻¹⁶ m, yön farkı 8,88 × 10⁻¹⁶ rad. 597 çizilmiş robot kökü ve yönü relay’e karşı doğrulandı. [ROS karşılaştırması](stage1-7d/live/ros-chrome-compare.json)
- İzole TF kesintisi ilgili robotu STALE yaptı. API kesilince güncel batarya ve canlı şarj vurgusu kalktı. API yeniden başlatıldıktan yaklaşık 1,12 sn sonra aynı kaynak oturumunda eşitleme gerçekleşti. SQLite bütünlük sonucu `ok`, üç doğrulama konteynerinin çıkış kodu 0. [İzole TF kaybı](stage1-7d/live/isolated-tf-stale.png) · [Bağlantı kaybı](stage1-7d/live/connection-loss.png) · [Canlı ölçümler](stage1-7d/live/browser-metrics.json) · [SQLite](stage1-7d/live/sqlite-check.txt) · [Kapanış](stage1-7d/live/shutdown.txt)
- Katmanlar açıkken kısa canlı ölçümde 58,0 sahne FPS, 18,1 ms p95 kare aralığı ve 88 p95 çizim çağrısı kaydedildi. Tarayıcı RAF yaklaşık 60 FPS. [Canlı ölçümler](stage1-7d/live/browser-metrics.json)

Kayıtlı parçalarda dekorla ayak izi kesişmesi veya varsayılan kameradan örtüşme bulunmadı. Bağımsız okuyucuların tüm geçerli map planları ölçüme girdi. TF örneklerine duruş anları da dahil. [Ham geometri ölçümü](stage1-7d/geometry.json)

| Kaynak | Parça sayısı | Görüş örneği | Örtülen | Duvarlara en kısa açıklık | Tüm dekora en kısa açıklık |
|---|---:|---:|---:|---:|---:|
| İki TF izi | 12.444 | 12.446 | 0 | 1,92 m | 1,34 m |
| 164 Nav2 planı | 11.534 | 11.885 | 0 | 1,74 m | 1,18 m |

## Bilinen sınırlar

- Görüş ölçümü 1440×900 varsayılan kamera, bu harita ve kaydedilen iki robotlu koşu ile sınırlı. 390×844 kontrollü örneğinde şarj ve park etiketleri yerleşti. Alım ve teslim etiketleri dar kadrajda robot etiketlerine yer açmak için gizlendi. Zemin işaretleri ve Görevler görünümündeki kayıtlar kullanılabilir. Yakın görev bölgelerinin zemin boyası kısmen üst üste gelebiliyor.
- Tüm olası Nav2 rotaları, 3+ robot, uzun süreli yük ve diğer tarayıcılar **HENÜZ TEST EDİLMEDİ**. Gözlemlenen planın aktif goal ile ilişkisi Durum B kapsamındadır.
