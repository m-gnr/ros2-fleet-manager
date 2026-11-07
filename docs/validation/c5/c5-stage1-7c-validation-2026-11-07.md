# C5 Aşama 1.7C — Depo sunumu ve operasyon alanları

**7 Kasım 2026** · [Çalıştırma ve ölçüm komutları](c5-stage1-7c-commands-2026-11-07.md) · [C5 3D görünüm tasarımı](../../design/c5-3d-operations.md)

Çalışma `feat/c5-warehouse-presentation-polish` dalında, Aşama 1.7B kabul commit’i `b682888` üzerinden ayrı worktree’de yapıldı. Kaynak değişiklikleri ve testler `6fdfd8d` commit’indedir.

## Başlangıç incelemesi ve yeni düzen

1.7B’de platform 14 × 14 m idi. GLB’nin `006–024` ve `026–028` gruplarından oluşan arka raf ve stok kutusu X’te −6,52 ile 5,61 m, Z’de −5,75 ile −4,03 m arasında, 2,44 m yüksekliğindeydi. Sol kenardaki palet, platform arabası ve transpalet 0,53 m’ye kadar yükseliyordu. 1440×900’de kamera yatayda %80,5, dikeyde %94,0 doluydu. Öndeki geniş zemin ve arka sıraya yığılan stok, platformu operasyon alanından daha baskın gösteriyordu. [Başlangıç ekranı](stage1-7c/before/viewport-1440.png)

Haritanın 30.625 serbest hücre merkezi Three.js uzayında yaklaşık X = [−4,33; 4,38] m, Z = [−4,38; 4,33] m aralığındadır. Konfigürasyonda robot başlangıçları ROS map uzayında (−2; −0,5) ve (1; 2,5) m. 1.7B bağımsız TF kaydında iki robotun hareketi yaklaşık X = [−3,52; 2,57] m, Z = [−3,14; 2,43] m aralığındaydı. Nav2 örnekleri X = [−3,70; 2,55] m, Z = [−3,30; 2,50] m aralığındaydı. Önceki canlı görev işaretleri sol arka ve sağ orta bölgelerdeydi. Bu inceleme, yüksek rafları kameranın arka ve sol tarafında tutma ve öne yalnız alçak palet koyma kararını belirledi. [1.7B bağımsız görev noktaları](stage1-7b/live/independent-operation-points.json)

11,35 × 10,95 m platformun ortası operasyonlara açık bırakıldı. Arka üç göz ve sol iki göz GLB’nin mevcut kiriş, dikme, raf ve stok parçalarını kullanıyor. Rafların önünde bölüm işaretleri, sarı sınırlar ve kenar geçişleri var. Ön sağda düşük palet alanı, arka ve sol uçta alçak kesit duvarı bulunuyor. Ortadaki işaretlerin kaynağı canlı snapshot. Şematik yükleme ve hata görünümü de aynı kenar düzenini kullanıyor.

| GLB stok grubu | X aralığı, m | Z aralığı, m | Yükseklik, m |
|---|---:|---:|---:|
| Arka sıra A01 | −3,84 … 3,85 | −5,36 … −4,48 | 1,96 |
| Sol sıra A02 | −5,39 … −4,51 | −2,02 … 2,31 | 1,36 |
| Ön sağ palet alanı | 2,03 … 4,64 | 4,55 … 5,29 | 0,45 |

Yerel GLB’nin SHA-256 değeri `972056d2f10d432afeb1d52083186e3a02c1b045bf68dbc6d4d47de8c568bb98`. Raflar malzeme başına birleştirildi. Statik zemin kutuları instance edildi ve dört zemin yazısı tek küçük atlas kullanıyor. Model CC0 1.0 lisanslıdır. [Yayıncı model sayfası](https://3dassets.dev/assets/hardware-store-and-diy-warehouse-warehou-f3ddb545-starter-scene)

## Operasyon alanları ve robotlar

- Şarj alanı teal kontur, robotun yanına alınmış şimşek ve yönlendirilmiş alçak bir 3D üniteden oluşuyor. İstasyon pozu ve rezervasyon durumu snapshot’tan geliyor. Canlı sahip etiketi güncel robot kaydı gerektiriyor. Şarj vurgusu için C4’ün istasyon ve robot alanları ile güncel batarya bilgisi eşleşmeli. Kesinti durumunda istasyon etiketi **Son eşitleme** gösteriyor.
- Park alanında P ve snapshot yaw yönünde ok var. Şarj ünitesi ve şarj vurgusu yalnız şarj istasyonunda kullanılıyor. Alım mavi paket ve yukarı ok, teslim mor elmas ve aşağı ok ile ayrılıyor. Seçili robotun etkin görevi, diğer etkin işler ve kuyruk sırası önceki önceliği koruyor. Görevsiz durumda bu iki işaret kalkıyor.
- Burger gövdesi 0,138 × 0,178 × 0,192 m ve TF kökü 26 px ekran işaretiyle örtüşüyor. Seçim zemin halkasıyla vurgulanıyor. Yakın takipte robot etiketi gövdenin üst sınırını hesaba katıyor. Sağ panelde aynı modelden alınmış 7,18 kB statik WebP bulunuyor. Görselin şarj satırı C4 verisini izliyor.
- **Temsili 3D depo** ve **Salt okunur** ibareleri görünür. Robot, istasyon, görev ve rota verileri mevcut ROS map dönüşümünden geçiyor. Kaynak diff’i frontend ve test dosyalarıyla sınırlı.

## Görsel kabul ve kamera

İlk Chrome turunda iki zemin yazısı stok silüetine karışıyordu. Yazıların yeri ve çizimi düzeltildi, arka raflara karton kutular eklendi ve önizleme şeffaf kesitle yenilendi. Son takip kontrolünde etiket, yakın planda lidarın önüne geldiği için gövde yüksekliğine göre yukarı alındı. Mobilde operasyon etiketlerine ek yerleşim seçenekleri eklendi. [İlk tur görüntüsü](stage1-7c/iteration-1440.png) · [Son 1440×900 görüntüsü](stage1-7c/after/viewport-1440.png)

| Boyut | Chrome üretim görüntüsü |
|---|---|
| 1280×850 | [Genel depo](stage1-7c/after/viewport-1280.png) |
| 1440×900 | [Genel depo](stage1-7c/after/viewport-1440.png) |
| 1920×1080 | [Genel depo](stage1-7c/after/viewport-1920.png) |
| 390×844 | [Viewport](stage1-7c/after/viewport-390.png) · [Tam sayfa](stage1-7c/after/mobile-full.png) |

Bu tablo ve aşağıdaki etkileşim görselleri kontrollü test verisi kullanır. [Şarj](stage1-7c/after/charging.png) · [Seçim](stage1-7c/after/selected.png) · [Alım/teslim, plan ve iz](stage1-7c/after/task-plan-trail.png) · [Takip](stage1-7c/after/follow.png) · [Üstten](stage1-7c/after/top.png) · [STALE](stage1-7c/after/stale.png) · [Bağlantı kesintisi](stage1-7c/after/disconnected.png)

**DOĞRULANDI.** Masaüstünde sahne ve sağ panel aynı yüksekliği kullanıyor. 1440×900’de pano dikey kaydırma istemiyor ve iki filo kartı bütünüyle görünüyor. 390×844’te yatay taşma yok. Geometri kutuları üzerinden kadraj alan dört görünüm kırpılmadı. Serbest, takip, üstten, filo kadrajı ve sıfırlama çalıştı. Elle değiştirilmiş açı, zoom ve pan, yeniden boyutlandırmada ve GLB değişiminde korundu.

## Chrome testleri ve performans

**DOĞRULANDI.** Google Chrome üretim önizlemesinde **20/20** test geçti. Kapsam yeni stok ayak izini, yerel GLB ve şematik fallback’i, snapshot map pozlarını, temsili şarj ünitesinin göreli yerini, sahiplik maskesini, görev seçimini ve boş listeyi, TF kökünü, katmanları, kamera geçişlerini, resize, responsive düzen ve veri kaybını içeriyor. [Derleme](stage1-7c/build.log) · [Playwright](stage1-7c/playwright.log)

Apple M3, gerçek Chrome 156.0.8078.80, ANGLE Metal WebGL2, DPR 1, standart kalite. Her viewport ayrı Chrome bağlamında 5 sn boyunca aynı 2 Hz ürün snapshot’ı ve iki 10 Hz TF akışıyla ölçüldü. Nav2 planı etkileşim görseli için ayrıca gönderildi. Talep üzerine çizilen sahne kareleri ve tarayıcı RAF ayrı kaydedildi. [1.7B ham ölçüm](stage1-7c/before/metrics.json) · [1.7C ham ölçüm](stage1-7c/after/metrics.json)

| Viewport | Yatay doluluk, % | Dikey doluluk, % | Sahne FPS | Kare aralığı p95, ms | Çizim çağrısı p95 |
|---|---:|---:|---:|---:|---:|
| 1280×850 | 83,4 → 74,5 | 94,0 → 94,0 | 36,9 → 36,3 | 66,7 → 66,8 | 63 → 68 |
| 1440×900 | 80,5 → 71,9 | 94,0 → 94,0 | 37,1 → 36,1 | 66,5 → 66,8 | 63 → 68 |
| 1920×1080 | 74,8 → 66,8 | 94,0 → 94,0 | 37,0 → 36,8 | 66,8 → 66,8 | 63 → 68 |
| 390×844 | 90,0 → 90,0 | 60,4 → 70,9 | 37,0 → 36,2 | 66,6 → 66,7 | 63 → 68 |

Soldaki değerler yeniden ölçülen 1.7B’ye, sağdakiler 1.7C’ye aittir. 1440×900’de sahne çizimi %2,7 yavaşladı ve p95 aralığı 0,3 ms arttı. Tarayıcı RAF her boyutta yaklaşık 60 FPS kaldı. Yan raf, palet ve operasyon alanlarıyla üçgen p95 73.026’dan 96.840’a, geometri/doku 63/3’ten 68/4’e çıktı. Ek doku zemin yazısı atlasıdır. Yerel GLB ve mevcut malzeme grupları yeniden kullanıldı.
1440×900’de başlangıç ve son fixture TF örneklerinde Burger gövde zarfı sırasıyla 11,5×13,5 ve 12,8×15,7 px (dock’taki robot), 11,2×12,4 ve 12,4×14,2 px (hareketli robot) ölçüldü. Fark kadrajdan geliyor. AABB görüş testi, 30.625 serbest hücreden 1.7B’de 1.225, 1.7C’de 147 hücre merkezinde olası stok örtüşmesi buldu. Başlangıçtaki arka kenar bandı açıldı. Son düzende olası örtüşme ön sağdaki yaklaşık 2,4 × 0,1 m’lik kenar bandında kaldı. [Geometri ölçümü](stage1-7c/geometry.json)

## Canlı C4.5 Fortress

**DOĞRULANDI.** İki robot hareket etti ve sırayla fiziksel şarj aldı. Chrome, C4 şarj sahibini 3D ünitede, TF kök işaretinde ve önizlemede eşleştirdi. `c45-low`, `c45-parallel` ve `c45-urgent` tamamlandı. Aynı damgalı C4 batarya SoC/Wh alanları ile SQLite görev ve rezervasyon kayıtları bağımsız karşılaştırmadan geçti. [Chrome sonucu](stage1-7c/live/chrome.log) · [C4.5 ve C5 olayları](stage1-7c/live/c4-c5-events.log) · [Doğrulanmış snapshot](stage1-7c/live/verified-source.json)

- Bağımsız ROS okuyucuları 4.510 aynı damgalı TF pozu ve 130 birebir Nav2 planı eşleştirdi. En büyük konum farkı 0 m ve en büyük yön farkı 8,88 × 10⁻¹⁶ rad. Chrome’da 1.857 çizilmiş robot kökü ve yönü relay’e karşı doğrulandı. Tarayıcıdaki Nav2 ve TF iz köşeleri kaynak koordinatlarla eşleşti. [Bağımsız ROS karşılaştırması](stage1-7c/live/ros-chrome-compare.json)
- Chrome’da 11.314 istasyon veya görev noktası snapshot’la eşleşti. `dock_1` dünya konumu (0,5; 0; 2) m, `park_1` (−2; 0; −1) m. İstasyonların yön ve konumları `fleet.yaml` ile SQLite’a, çizilen üç görev çiftinin yön ve konumları SQLite görev kayıtlarına karşı bağımsız doğrulandı. [Chrome noktaları](stage1-7c/live/chrome-operation-points.json) · [Bağımsız nokta karşılaştırması](stage1-7c/live/independent-operation-points.json)
- Başlangıç açısından 8.448 TF örneği ve 11.510 rota köşesi stok kutularınca örtülmedi. En yakın ayak izi açıklığı TF için 1,34 m, Nav2 için 1,18 m. Görüntülenen rotanın geometrisi canlı ROS planıyla eşleşti. [Geometri ölçümü](stage1-7c/geometry.json)
- İzole TF kesintisi ilgili robotu STALE yaptı. API kesintisinde canlı batarya ve şarj vurgusu kalktı. API yeniden başladığında kaynak oturumu korunarak yaklaşık 1,11 sn’de eşitleme sağlandı. Chrome sayfası kapatılıp açıldığında Fleet Manager aynı kaynak oturumunda kaldı ve snapshot dizisi ilerledi. Katmanlar açıkken 58,3 sahne FPS, 18,3 ms p95 ve 73 çizim çağrısı ölçüldü. SQLite bütünlük kontrolü `ok`, üç konteynerin çıkış kodu 0. [Canlı ölçümler](stage1-7c/live/browser-metrics.json) · [SQLite](stage1-7c/live/sqlite-check.txt) · [Kapanış](stage1-7c/live/shutdown.txt)

Canlı ekranlar [iki robot](stage1-7c/live/isometric-two-robots.png), [fiziksel şarj](stage1-7c/live/charging-scene.png), [alım/teslim, Nav2 ve TF izi](stage1-7c/live/active-task-plan.png), [seçim](stage1-7c/live/selected-robot.png), [takip](stage1-7c/live/camera-follow.png), [üstten](stage1-7c/live/camera-top.png), [izole TF STALE](stage1-7c/live/isolated-tf-stale.png) ve [API kesintisi](stage1-7c/live/connection-loss.png).

## Bilinen sınırlar

- Ölçülen ayak izi açıklığı bu harita ve kayıtlı iki robotlu rotalar içindir. Tüm olası Nav2 rotaları ve diğer kamera açıları **HENÜZ TEST EDİLMEDİ**. Kenarlardaki görsel örtüşmeler için üstten görünüm de kullanılabilir.
- Yakın görev noktalarında ve dar viewport’ta robot etiketleri önceliklidir. Çakışan operasyon etiketleri yer kalmadığında gizlenebilir. Şarj ve park ayrıntıları **İstasyonlar / Şarj** görünümünde yer alır.
- Nav2 planının aktif goal ile ilişkisi Durum B kapsamındadır. Tarayıcı performansı kısa Apple M3 ölçümüne aittir. Diğer tarayıcılar, 3+ robot ve uzun süreli dayanıklılık **HENÜZ TEST EDİLMEDİ**.
