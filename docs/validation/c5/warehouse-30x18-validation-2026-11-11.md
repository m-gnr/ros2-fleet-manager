# C5 — 30 × 18 m dağıtılmış depo ve katalog görev girişi

11 Kasım 2026 · Dal `feat/c5-warehouse-grid-layout` · Taban `30373ff` · [Komut eki](warehouse-30x18-commands-2026-11-11.md)

## Yerleşim ve kullanıcı seçimi

Kullanıcı mevcut 12 raf bloğu ile 8–10 pick sınırı arasındaki çelişki açıklandıktan sonra **10 daha uzun blok ve 10 pick** seçeneğini **ONAYLADI**. [30 × 18 m profili](../../../config/fleet.warehouse-30x18.yaml) bu seçimi uygular. Boyutlar `warehouse.width` ve `warehouse.depth` alanlarında bir kez tanımlıdır. Izgara 0,25 m kalır. [20 × 12 m](../../../config/fleet.warehouse-grid.yaml) ve [12 × 8 m](../../../config/fleet.warehouse-grid-12x8.yaml) dosyaları değiştirilmemiştir.

| Bölüm | Yerleşim |
|---|---|
| Raflar | Beş sırada iki blok, 10 ayrı servis yüzü. Yatay modül sayısı 36’dan 58’e çıkar. Her modül üç görsel kat taşır |
| Koridorlar | Dört ana koridor 2,25 m. Batı, orta ve doğuda üç enine geçit 1,75 / 2,00 / 1,75 m. Kapı için ayrı erişim bağlantısı |
| Raf alımı | `pick_A1`–`pick_E2`, blok başına bir nokta. Yaklaşma merkezi raf yüzünden 0,75 m uzakta ve rafa dönük. 0,45 m zarfla koridorun karşı tarafında 1,05 m şerit kalır |
| Mal kabul | Batı kapısı yanında `inbound_1`, `inbound_2` |
| Paketleme | Güneyde iki nokta, `packing_1`, `packing_2` |
| Sevkiyat | Karşı doğu duvarında `delivery-01`, `shipping_2`, `shipping_3` |
| Kalite kontrol | Orta bölgedeki özel cepte `quality_1`. `rack_C2` başlangıcı bu cebi açık bırakır |
| Şarj ve park | Kuzeydoğu servis köşesinde `dock_1`–`dock_6` ve üç park yeri. Dock’ların önünde en az 2 m açık yaklaşma şeridi |

Raf noktaları hem alım hem teslim rolünü destekler. `inbound_1 → pick_B1` ile rafa mal götürmek mümkündür. Şarj/park sahipliği mevcut rezervasyon modelinde kalır. Transfer noktaları görev ucu kataloğudur. [Alan sözleşmesi](../../configuration-c1.md#dağıtılmış-operasyon-profili)

## Ortak kaynak ve costmap denetimi

**DOĞRULANDI.** Doğrulayıcı ve üretici aynı doluluk rasterini kullanır. Robot başlangıçları, 18 transfer noktası ve 9 kaynak yaklaşmasının ihtiyatlı zarfı dolu hücreye değerse üretim hata verir. SDF raf/duvar kutuları, PGM, Nav2 parametreleri, backend katalog pozları ve ön yüz geometri payload’ı aynı çözülmüş profilden gelir.

Canlı iki robotun her haritası, PGM’nin 277.200 hücresinin tamamıyla eşleşti. On raf merkezi her iki global costmap’te engeldi. Bütün **27 istasyon yaklaşma merkezi**, iki Nav2 global costmap’inde de **0 maliyetli** çıktı. Üç rotanın altı gözlemlenen planında 99–100 engel maliyetli hücre bulunmadı. Bazı dönüşler şişirme katmanında 55–58 maliyetli hücrelerden geçer.

Aynı profil host üzerinde yeniden üretildiğinde `warehouse.sdf`, `map.pgm` ve `scene.json` canlı koşudaki dosyalarla bayt düzeyinde eşleşti. [Hash ve rota ölçümleri](warehouse-30x18/geometry-audit.json) · [Nav2 global costmap kaydı](warehouse-30x18/nav2-costmap.json)

## Fortress / Nav2 fiziksel sonuçları

**DOĞRULANDI.** ROS 2 Humble, Fortress headless ve iki bağımsız Nav2/AMCL yığını kullanıldı. Hazır image `ros2-fleet-c5-validation:humble-fortress`, SHA-256 `7fb7e7fc4aebe0d2b4097752e9b470e30d8ea7a8126bb1dee87d03f30330609d`. Kaynak profili özeti `8e8396b60c306e795ea84275ac56aa41a47fc8cf090fe14ad9627988bc91fda2`.

Üç örnek çiftte `robot_alpha` önce alım hedefine, sonra teslim hedefine gerçek `NavigateToPose` goal’larıyla sürüldü. `robot_beta` park köşesinde kaldı. Her fiziksel robotun gövde, iki teker, arka destek ve ön destek çarpışmaları ayrı contact sensörleriyle izlenir. Alım ve teslim için kabul eşiği fiziksel merkez hatası en fazla 0,35 m ve terminal `SUCCEEDED` olarak korundu.

| Senaryo | Sonuç | Alım / teslim son hatası | Alım → teslim gözlemlenen planı |
|---|---|---|---|
| `pick_A1 → packing_1` | **Geçti** | 0,211 / 0,344 m | 18,223 m, 729 nokta |
| `pick_C2 → delivery-01` | **Geçti** | 0,110 / 0,290 m | 10,710 m, 427 nokta |
| `inbound_1 → pick_B1` | **Geçti** | 0,224 / 0,198 m | 8,226 m, 326 nokta |
| Aynı koridorda iki karşı yönlü robot | **Geçti** | İki goal `SUCCEEDED` | C koridorunda X sırası tersine döndü. Eşleşen örneklerde en küçük merkez mesafesi 1,302 m |

Son koşularda robot–robot veya robot–raf/duvar temas kaydı oluşmadı. Karşılıklı geçişte Y = −1,75 ve −0,50 m olan önceden ayrılmış iki şerit kullanıldı. Üç çiftin her ayağında en çok noktalı gözlemlenen Nav2 planı, Gazebo fiziksel poz örnekleri ve goal sonuçları saklandı. İki simülasyon da Nav2 lifecycle ve süreç kapanışlarını temiz tamamladı. [Üç çift ham kaydı](warehouse-30x18/live-routes.json) · [Karşılıklı geçiş ham kaydı](warehouse-30x18/live-passing.json) · [Kapanışlar](warehouse-30x18/shutdown.json)

## Tarayıcı, görev oluşturma ve kalıcılık

**DOĞRULANDI.** Önce/sonra 1440 × 1000 ve mobil 390 × 844 kadrajları ölçüldü. Hiçbir depo köşesi varsayılan veya sıfırlanmış kadrajın dışına çıkmadı. Uzakta bölge etiketleri, yakında nokta ID’leri göründü. Üstten ölçümde görünür bölge etiketleri birbirleriyle ve raf izdüşümleriyle kesişmedi. Yerleşim algoritması robot işaretlerinin kapladığı ekran alanını da dışarıda tutar. Rafa teslimde aktif teslim işareti aynı konumdaki katalog alım boyasını çoğaltmaz. Güncel olmayan şarj sayacı maskelenir. Raflar mevcut instanced mesh yolunda çizilir. Rotanın yakınlığı 30 × 18 m profilinde fiziksel rafı gizlemez.

Costmap görüntüsü çalışan Nav2’den alınmış **kayıttır**. Sürekli canlı costmap akışı değildir. Son depo görüntülerinde Nav2/TF poz ve plan kaydı yeniden oynatılır. Ürün snapshot’ı robot telemetrisi uydurmayan başlangıç Fleet Manager görünümüdür. Önce görüntüsü tarihsel 20 × 12 m kontrollü ürün fikstürünü kullanır.

Üç örnek görev ayrıca Chrome’dan gerçek HTTP API’ye gönderildi. Yerel soket üzerinden aynı tek consumer’a ulaştılar. SQLite’ta üç ayrı `QUEUED` kaydı, doğru alım/teslim koordinatları ve öncelikler görüldü. `integrity_check=ok`, foreign key hatası yok. Ekrandaki bu görev tablosu gerçek API/SQLite akışından gelir. Bu host koşusunda ROS robotları bağlanmadığı için görevler kuyrukta kaldı. [Tarayıcı kanıtı](warehouse-30x18/chrome-evidence.json) · [Üç görev ve SQLite kanıtı](warehouse-30x18/task-evidence.json)

Host seçkisinde **87 test**, Chrome regresyonunda **23 test** geçti. Aynı UUID ile retry tek görev bıraktı. Değişen uç/öncelikle UUID kullanımı, yanlış Origin, eski kaynak oturumu, farklı profil özeti ve geçersiz uç rolü reddedildi. Salt okunur API kurulumu `POST /api/tasks` için 405 davranışını korudu. Yeni ROS Fleet Manager runtime’ı IDL derlemesinden sonra başlatıldı, snapshot/soket oluşturdu ve SIGINT ile 0 koduyla kapandı. [Python](warehouse-30x18/python.log) · [Playwright](warehouse-30x18/playwright.log) · [Derleme](warehouse-30x18/build.log) · [Runtime smoke](warehouse-30x18/runtime-smoke.log)

## Görseller

| Önce · 20 × 12 m | Sonra · 30 × 18 m |
|---|---|
| ![Önce](warehouse-30x18/before.png) | ![Sonra](warehouse-30x18/after.png) |

[Önce üstten](warehouse-30x18/before-top.png) · [Sonra üstten](warehouse-30x18/after-top.png) · [Nav2 costmap bindirmesi](warehouse-30x18/after-costmap.png) · [Yakın nokta ID’leri](warehouse-30x18/after-close.png) · [Mobil](warehouse-30x18/after-mobile.png) · [Gerçek API ile görev oluşturma](warehouse-30x18/tasks.png)

## Düzeltilen denemeler ve doğrulanmayan kapsam

- İlk host denemelerinde şema varsayılanları, genişleyen GET yüzeyinin test beklentisi ve uzun macOS Unix socket yolu düzeltildi. Mevcut API’nin salt okunur POST davranışı korundu.
- İlk runtime smoke denemesinde host bind mount üzerindeki Unix socket `chmod` işlemi hata verdi. Soket ve snapshot container’ın yerel dosya sistemine taşındı. Kalıcı SQLite ayrı volume/bind mount üzerinde kaldı. Son smoke 0 koduyla tamamlandı.
- Bir tekrar koşusu `goals.json` hazır olmadan probe başladığı için başarısız oldu. Üreticiye ait readiness dosyasıyla başlangıç sırası düzeltildi ve üç çift temiz ortamda yeniden tamamlandı.
- Ön destek collision’ı için ayrı sensör eklendi. Son fiziksel koşular bu düzeltmeyle çalıştı. İlk kısa plan kayıtlarının yerine her ayaktaki tam uzun plan saklandı. Tarayıcı fikstürü de fiziksel son pozu ham iz kaydından okuyacak şekilde düzeltildi.
- **HENÜZ TEST EDİLMEDİ.** Yeni profilde tarayıcı → FM → Outbox → Executor → yükleme/boşaltma → Battery zincirinin birleşik canlı kabulü. API/consumer/SQLite, ROS runtime başlangıcı ve fiziksel Nav2 koşuları bu turda ayrı doğrulandı.
- **HENÜZ TEST EDİLMEDİ.** 27 istasyonun tamamına fiziksel ziyaret, altı dock’a yanaşma/geri çıkış ve batarya şarjı. Yaklaşma geometrisi ve bütün hedef merkezlerinin çalışan costmap değeri doğrulandı.
- **HENÜZ TEST EDİLMEDİ.** Aynı merkez hattında otomatik trafik çözümü, dar koridor deadlock, üçten fazla robot ve uzun süreli performans. Karşılıklı geçiş iki ayrılmış şeritle sınandı. Test dünyası önceki doğrulama robotunun fiziksel modelini kullanır.

Bu kayıt C5 veya depo tasarımı için final kabul değildir. Yeni uygulama değişiklikleri çalışma ağacındadır. Bu geliştirme adımında commit/push yapılmamıştır.
