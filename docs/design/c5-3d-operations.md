# C5 / Aşama 1.5 — Salt okunur 3D operasyon görünümü

## Entegrasyon ön incelemesi

C5 Aşama 1 `76a80ab` commit'inde `frontend/src` altında operasyon kartları, Konva haritası ve bağımsız ürün snapshot istemcisi bulunur. Visualizer Aşama 4 `f3e3901` commit'inde `fleet-visualizer/frontend/src` altında sahne, kamera, TurtleBot3, TF akış indirgeyicileri ve plan/iz katmanları ayrı modüllerdir. Tam ekran Visualizer layout'u ile robot paneli C5'e taşınmaz. C5'in Konva matematiği operasyon kartlarından bağımsızdır. İki uygulama TypeScript 5.9.3 ve Vite 7.3.7 kullanır. C5 React 19.3.1, Visualizer React 19.2.0 kullanır. İçe aktarılan R3F 9.4.0 ve Three.js 0.181.2 sürümleri korunur. Sahne Three.js OrbitControls kullanır. Drei bağımlılığı bulunmaz. İki tabanda da aynı depo lisansı geçerlidir.

C5 ürün snapshot'ı Fleet Manager'dan tam kayıt, kaynak oturumu, sıra, ürün alım güncelliği ve simülasyon damgası taşır. Visualizer her robot için `map` TF, ayrı stream kimliği, simülasyon epoch'u, damga watermark'ı, Path TTL ve segmentlenmiş iz tutar. Yerel süreler kendi monotonik saatiyle değerlendirilir. Son iki TF ölçümü arasında interpolasyon yapılır. Robot seçimi C5'te ortak robot ID ile bağlanır. Ayrı kamera state'i sunuma aittir. İstasyon sahipliği ve taşıma durumu ürün snapshot'ından gelir.

## Dağıtım seçimi

**A seçildi.** Aynı doğrulanmış salt okunur Visualizer köprüsü bağımsız süreçte çalışır. FastAPI yalnız config ile belirlenen köprüye abone olur. B seçeneği C5'e ROS çalışma zamanı ve hata alanı getirirdi. C seçeneği tarayıcıya ikinci ağ girişi ve ayrı köprü Origin yapılandırması getirirdi. Fleet Manager, web süreci ve köprünün yeniden başlatma yaşam döngüleri ayrıdır. Köprü ROS okuma işlemlerini kendi yürütücüsünde çalıştırır.

Tarayıcı `/ws/fleet` üzerinde `fleet.scene.v1` alt protokolünü ister. Alt protokolsüz ürün istemcisi Aşama 1 sözleşmesini kullanır. Yeni akışta ürün snapshot'ı kendi şemasında kalır. `product_unavailable` ürün kaynağını, `scene_connected` ve `scene_disconnected` TF akış yaşam döngüsünü, `scene` Visualizer paketini, `heartbeat` yalnız taşıma bağlantısını bildirir. Ürün kaynağı oturum değişiminde veya geçersizleşince yeniden teyit edilir. TF oturumu köprü el sıkışmasıyla kurulur. Köprü paketlerini sırayla ileten, istemci başına sınırlandırılmış bir abonelik vardır. Yeniden bağlantıda paket replay'i yapılmaz. Yeni robotlar ve namespace eşlemesi doğrulanmış `fleet.yaml` üzerinden gelir.

## Sunum ve kaynak sınırları

**ONAYLANDI.** Ana görünüm, kullanıcı talimatıyla Konva 2D'den açık renkli Three.js ve React Three Fiber sahnesine geçer. Açık gri platform, beyaz raflar, kontrollü durum renkleri ve çapraz başlangıç kamerası Flowdeck’in görsel yaklaşımından esinlenir. [Callour Studio referansı](https://dribbble.com/shots/27098154-Flowdeck-AI-Warehouse-Management) Ürün panelleri mevcut C5 bileşenlerini kullanır. Temsili raf ve yollar Nav2 haritası olarak kullanılmaz.

Fleet Manager görev, ürün durumu, C4 batarya ve istasyon sahipliği için yetkilidir. TF robot modeli, poz güncelliği ve iz için ayrı görüntüleme kaynağıdır. **GÖZLEMLENEN NAV2 PLANI (Durum B)** yalnız doğrulanmış robot namespace'indeki gözlemdir. Aktif goal UUID ilişkisi doğrulanmamıştır. Bağlantı veya veri kaybında güncel batarya gizlenir, geçmiş ürün kayıtları işaretlenir ve son geçerli TF pozunun durumu ayrı gösterilir. İlk geçerli TF ölçümü öncesinde robot modeli çizilmez.

Seçili sahne, koordinat ve reducer modülleri kaynak commit'ten bir kez içe alınır. Renk/kadraj ve C5 kabuğu, yerel entegrasyon farklarıdır. Köprü aynı kaynak dosyalarından derlenir. İçe aktarılan modüller bağımsız Visualizer layout'una bağlı olmadığı için sonraki ortak paket ayrımına uygundur. Konva'nın aşama geçmişi korunur.

## Akış sınırları

FastAPI köprüye özel DDS ağındaki `scene` adı ve yapılandırılmış port üzerinden ulaşır. Uç yalnız doğrulanmış filo robot ID kümesini, her robotun config namespace'ine ait `/plan` konusunu ve `map` / `tf` kimliğini geçirir. Visualizer mesajlarının stream, epoch, simülasyon damgası ve TTL doğrulaması istemcideki Aşama 4 indirgeyicilerinde sürer. Clock epoch değişiminde önceki poz, iz ve plan temizlenir. Köprü yeniden bağlandığında son poz STALE kalabilir. Yeni bir geçerli ölçüm gelince robot LIVE olur.

Upstream bağlantı başına 64 KiB WebSocket mesaj sınırı, 1 frame alım su seviyesi ve uygulamada bekleyen en fazla bir olay vardır. 250 ms'den uzun süre relay'de kalan poz atılır. Relay beklemesi plan TTL'sinden düşülür. İstemci gönderimi bir saniye içinde tamamlanamazsa bağlantı 1013 ile kapatılır. Ürün için yalnız son snapshot tutulur. Ürün sessizliği, tek başına açık TF akışını kapatmaz. Köprü sessizliği 2,5 sn sonra kendi yeniden bağlantısını tetikler. Köprü Aşama 4'ten gelen dört eşzamanlı istemci sınırına sahiptir. C5 ürün akışı kendi mevcut istemci sınırını kullanır.

Kamera serbest, takip, üstten, filo kadrajı ve sıfırlama modlarını sunar. WebGL sahnesi genel görünümde tembel yüklenir. Düşük kalite seçeneği piksel oranını 1'e indirir ve temas gölgelerini kapatır. Geometri instancing, rota arabelleği, renderer temizliği ve talep üzerine çizim Visualizer’dan alınmıştır.

## Aşama 1.7B hazır depo

Sunum sahnesi yerel CC0 GLB dekorunu asenkron yükler. Model hazır olunca şematik rafların yerini alır. İstasyonlar ile öncelikli görevin alım ve teslim noktaları doğrulanmış C5 snapshot’ından map koordinatlarında çizilir. Model seçimi, kaynak ve ölçüm kanıtı [Aşama 1.7B doğrulama raporunda](../validation/c5/c5-stage1-7b-validation-2026-11-07.md).

## Aşama 1.7C depo sunumu

Raf ve palet ayak izleri çevrede tutulur. Depo zemini, raf numaraları ve güvenlik çizgileri temsili geometri grubunda kalır. Operasyon katmanında şarj ünitesi ve park yönü istasyon snapshot’ındaki map pozu ve yönüyle hizalanır. Alım ve teslim alanları öncelikli görev çiftiyle birlikte görünür. Ayrıntı panelindeki Burger önizlemesi aynı gövdeden alınmış statik bir görseldir. Yerleşim gerekçesi, Chrome ölçümleri ve canlı kanıt [Aşama 1.7C raporunda](../validation/c5/c5-stage1-7c-validation-2026-11-07.md).

## Aşama 1.7D duvarlar ve operasyon bölgeleri

Arka duvar, yükleme kepengi, yan kesitler ve koridor boyası sunum geometrisidir. Yerleşim haritanın operasyon alanını çevreler. Serbest kameradan bir dekor grubunun kutusu robot gövdesine görüşü kapatırsa grup geçici olarak kesilir. İlk ve üstten kadraj, dekorun tam sınırlarına göre hesaplanır.

Şarj, park, alım ve teslim zeminde 0,92 m kare, simge ve metinle ayrılır. Alım ve teslim aynı map noktasındaysa kareyi paylaşır. Zemin boyası görsel ölçüdür. İstasyon sahipliği, C4 şarj durumu ve görev çiftinin seçimi mevcut snapshot kurallarını kullanır. [Yerleşim ve doğrulama](../validation/c5/c5-stage1-7d-validation-2026-11-07.md)

## Aşama 1.7E işlevsel iç yerleşim

Ana koridor, kepenk önü, raf geçidi ve operasyon cepleri temsili dekor grubunda kalır. Alçak bölmeler bağımsız kesilebilir; GLB iç rafı ayrı bir statik mesh’tir. İstasyon çerçeveleri ve görev işaretleri canlı snapshot katmanındadır. Kesişen alım/teslim kareleri ayırıcı doğruyla bölünür, map pozları değişmez. Sahne etiketleri kısa durum gösterir; sahiplik kaydı robot ayrıntılarında açılır. [Yerleşim ve ölçüm kapsamı](../validation/c5/c5-stage1-7e-validation-2026-11-08.md)

## 11 Kasım 2026 dağıtılmış depo ve katalogdan görev girişi

Kullanıcı 30 × 18 m, raflara dağılmış alım ve birden fazla teslim bölgesi istedi. Mevcut 12 blok ile 8–10 pick sınırının çelişkisi açıklanınca 10 daha uzun blok ve 10 pick seçeneğini onayladı. Boyut, geometri, yaklaşma pozları, uç rolleri ve örnek görevler [tek profil dosyasındadır](../../config/fleet.warehouse-30x18.yaml). Bu seçim ürünün final kabulü değildir.

17 Kasım park yerleşimi: üç `park_*` hedefi profilin doğu kenarına taşındı. 3D yuva çizgileri canlı istasyon pozlarından türetilir; yuva metni bağlıysa gerçek rezervasyon sahibini, boşsa istasyon ID'sini gösterir. Eski şerit görsel bekleme boyasıdır. Fleet Manager park istasyonunu rota ve enerji uygunluğuyla seçmeye devam eder; robot başına sabit yuva politikası uygulanmadı. [Kaynak ve doğrulama sınırları](../validation/c5/visualize-park-relocation-2026-11-17.md).

Görev oluşturma için API içinde ikinci bir Fleet Manager kurmak, SQLite’a doğrudan HTTP callback’inden yazmak ve mevcut tek consumer’a olay göndermek seçenekleri değerlendirildi. Üçüncü yol uygulandı. `runtime.py`, mevcut builder, `FleetEventLoop`, `FleetROS2Adapter` ve `OutboxDispatcher` sınıflarını çalıştırır. `publish_fleet(..., fleet_config=config)` aynı consumer’ın yanında izinleri 0600 olan yerel görev soketini açar. API ayrı süreçte kalır. Soket yolu snapshot’ın `.tasks.sock` uzantılı karşılığıdır ve container’ın yerel dosya sisteminde bulunur.

`GET /api/task-catalog` çalışan kaynak oturumunu, çözülmüş profilin SHA-256 özetini, nokta rollerini ve örnek görevleri verir. `--task-socket` ile açılan API `POST /api/tasks` yolunu etkinleştirir. Tam Origin, JSON içerik türü, sınırlı istek boyutu, UUID, kaynak oturumu, profil özeti ve uç rollerinin hepsi doğrulanır. İstemci koordinat gönderemez. Noktalar consumer tarafında yeniden katalogdan çözülür ve `SUBMIT_TASK` olayına dönüşür. Kalıcılık ve sonraki atama mevcut domain/transaction/Outbox yolundan ilerler.

Aynı UUID ve aynı değişmez içerikle tekrar gönderim mevcut görevi döndürür. Aynı UUID’nin başka uç veya öncelikle kullanılması reddedilir. Ağ yanıtı kaybolduğunda arayüz kabulü belirsiz gösterir ve aynı UUID’yi korur. Görev kabulü robotun hareket ettiğinin veya görevin tamamlandığının kanıtı değildir. Oturum/profil değişimi eski isteği engeller. Var olan dolu DB ile runtime yeniden başlatması otomatik replay oluşturmaz.

Katalog bulunan yeni profilde uzak görünüm bölge etiketlerini, yakın görünüm tek tek nokta ID’lerini kullanır. Rafların izdüşümü ve robot işaretleri etiket yerleştirmesinden çıkarılır. Şarj telemetrisi güncel değilse bölge sayacı `—/6` biçiminde maskelenir. Yer bulunamazsa etiket gizlenir. 30 × 18 m profilinde rota yakınlığı fiziksel rafı gizlemez. Görsel kamera kesiti ayrıca korunur. Raf yapıları mevcut `Boxes` instancing yolundan çizilir. Kamera sınırı daha büyük deponun mobil kadrajına izin verecek şekilde genişletildi.

`GET /api/warehouse-costmap`, varsayılan olarak ortak YAML’den üretilen statik doluluk rasterini verir. `--costmap` ile açıldığında aynı profil özetini taşıyan Nav2 global costmap kaydını sunar ve arayüz bunu kayıt olarak işaretler. Sürekli canlı costmap akışı bu uçla uygulanmış sayılmaz. [Host, Chrome ve Fortress kanıtları](../validation/c5/warehouse-30x18-validation-2026-11-11.md)

## C5-A çevrimdışı ilk sahne ve profil geçişi

İlk render, `config/fleet.warehouse-30x18.yaml` dosyasını C1 doğrulayıcısıyla okuyan `frontend/scripts/generate_warehouse_profile.py` tarafından üretilen, sürüm kontrolündeki statik haritayı kullanır. `--check` üretim çıktısının YAML ile güncel olduğunu denetler. Backend yanıtındaki `profile_digest` doğrulanmadan harita değiştirilmez. Aynı hash’te oturum boyunca son doğrulanmış geometri korunur; farklı hash ve geçerli geometri yeni profile geçirir. Farklı hash geometri vermiyorsa önceki profile bağlı kalmak yerine harita doğrulama durumu gösterilir. Bağlantı kesilince telemetri stale/no-data olur; statik depo, robot pozu veya görev üretmez.

## Visualize V1 — görev noktalarının sunumu (17 Kasım 2026)

Bu değişiklik yalnız 3D sahnenin işaret ve etiket katmanındadır. Aktif/seçili görevin `pickup` ve `dropoff` pozları rolün canlı kaynağıdır. Statik katalogdaki `transfer_points.roles` izinleri tek rollü noktaları işaretler; iki rollü raf noktası aktif görevde kullanılmıyorsa nötr kalır. `kind` yalnız `roles` bulunmadığında katalog varsayılanıdır. Bölge türü görev rolünü belirlemez. Çakışan katalog işareti, canlı görev işaretinin altında ikinci kez çizilmez.

Alım dolu `#168DA4` kare ve beyaz yukarı ok; bırakma açık zeminli `#D18A28` çerçeve ve aşağı oktur. İkisinin iç işareti 0,92 × 0,92 m, görsel tabanı 1,24 × 1,24 m karedir. Birbirine çok yakın iki canlı görev pozu için mevcut kesilmiş işaret kuralı sürer. Şarj ve park düşük doygunluklu servis renklerinde kalır. Bölge boyası gri tonludur. Nokta adları mevcut kamera uzaklığına bağlı yerleştirilir; 15 m'de açılıp 17 m'de kapanan histerezis eşik geçişindeki titreşimi azaltır. Mevcut robot/raf çakışma denetimi korunur. [Doğrulama ve sınırlar](../validation/c5/visualize-v1-validation-2026-11-17.md).

## Visualize V2 — zemin adları ve isteğe bağlı nokta bilgisi (17 Kasım 2026)

V1'deki sürekli nokta etiketleri kaldırıldı. Bölge adları ve dört ana koridor adı, mevcut depo profilinin `zones` ve `aisles` alanlarından zemine düz, soluk yazı olarak yerleştirilir. Yerleşim raf sınırlarını, katalog görev pozlarını, şarj/park servis pozlarını ve diğer yazıları dışlar. Sağ üstteki büyük servis alanı `ŞARJ` adını taşır. Dar uzun bölgelerde yazı zeminde 90 derece döner. Yer bulunamazsa yazı rafın veya noktanın üzerine taşınmaz.

Bir görev veya servis noktasının üzerine gelince küçük bilgi balonu açılır; tıklama balonu sabitler, boş zemine tıklama veya Escape kapatır. Balonda katalog nokta adı, mevcut işlevsel rol, varsa durum ve robot sahibi gösterilir. Katalog `roles` alanı iki rolü içeriyorsa aktif görevin rolü balonda ayrıca çift rollü nokta olarak belirtilir. Aktif görevi olmayan çift rollü noktada turkuaz dış ve amber iç çerçeve; rolü belirlenemeyen noktada soluk gri çerçeve kullanılır. Alım/bırakma işaretleri ve robot etiketleri korunur. [Doğrulama ve sınırlar](../validation/c5/visualize-v2-validation-2026-11-17.md).

## Visualize V2.3 — üç robotun parkta başlangıcı (17 Kasım 2026)

30 × 18 m demo profilindeki üç robotun `initial_pose` değerleri sırasıyla `park_1`, `park_2`, `park_3` merkezidir; yaw `π` ile batıya bakarlar. Mevcut SDF üreticisi bu map x/y/yaw değerlerini Gazebo model pozuna doğrudan geçirir; Nav2 başlangıç pozu da aynı YAML'den üretilir. Bu eşleştirme yalnız senaryo başlangıcıdır. Fleet Manager'ın dinamik park seçimi ve rezervasyon sahipliği değiştirilmedi.

Gazebo yardımcısı ortak `/tf` yayımladığından görselleştirici robot namespace'lerindeki TF aboneliklerine ek olarak ortak `/tf`'yi bir kez okur. Her robot okuyucusu yalnız kendi `map → robot/odom → robot/base_link` zincirini kabul eder. İzole demo `docker run` ağında API'nin `scene` köprü adını aynı container'a çözmesi gerekir. Başlangıç gözlemcisi SQLite'daki dört tablo oluşana kadar DB örneklemesini bekler. [Canlı doğrulama ve kalan sınırlar](../validation/c5/visualize-v2-3-validation-2026-11-17.md).

## Visualize V3 — robot öncelikli sunum (17 Kasım 2026)

Robot modeli yalnız sunum grubunda 1,30 kat büyütülür; URDF/SDF, collision, footprint, TF ve Nav2 ölçüleri değişmez. Modelin kendi malzemeleri korunur. Her robotun doğrulanmış TF pozu sabit 34 px, içi boş ince zemin halkasına projekte edilir; TF yaw yönü halkanın dışına çıkan küçük üçgenle gösterilir. Mevcut etiket yerleştiricisi işaret, robot gövdesi ve diğer robot etiketlerini çakışma alanı sayar. Görsel zarf raf kesiti hesabına da aynı 1,30 katsayısıyla girer. Seçim yalnız halka çizgisini hafifçe belirginleştirir.

Durum rengi yalnız ince zemin halkası ve yön üçgeninde, güncel Fleet Manager `RobotStatus.state` değerinden türetilir: `IDLE` `#64748B`, `EXECUTING_TASK` ile iki dönüş durumu `#6554B5`, `CHARGING` `#44846B`, `ERROR` `#C45151`. Bağlantı veya ürün telemetrisi güncel değilse bu dört anlamlı renkten biri atanmaz. Etiket, dönüş durumunun gerçek adını göstermeye devam eder; renk ailesi yeni bir durum tahmini değildir. V1 alım/bırakma renkleri değişmez.

TF izi görev/aktif hareket durumunda son 2,8 m, 9 saniye ve 48 örnekle sınırlıdır; son gerçek hareket ölçümünden sonra 4,5 saniyede solar. Gözlemlenmiş Nav2 planı mevcut TTL ve kaynak denetimleriyle çizilir; rota yoksa çizgi üretilmez. İz ve plan nötr gri-mavidir, robot durum renklerini kullanmaz. Raf geometri ve konumları korunur; yalnız malzeme tonları açılır ve yatay kenar kalınlıkları azaltılır. [Doğrulama ve sınırlar](../validation/c5/visualize-v3-validation-2026-11-17.md).

## Visualize V4 — zemin ve aydınlatma (17 Kasım 2026)

Zeminde 1 m aralıklı, düşük opaklıklı gri-mavi kılavuz çizgileri tek `LineSegments` geometrisinde çizilir. Katman zemin üstünden ayrıdır ve koridor boyası, bölge yazıları, operasyon işaretleri ile park yuvalarının altında kalır. Raf ayak izleri ve fiziksel geometri değişmez; sert taban kutuları yerine tüm raflar tek instanced shader çiziminde kenara doğru saydamlaşan temas gölgeleri kullanır. Düşük kalite seçimi temas gölgelerini kapatır.

Sahne açık gri-mavi zemin/duvar/raf paletini, yumuşak hemisphere ışığını ve tek yönlü düşük şiddetli ana ışığı kullanır. Raf malzemeleri mat kalır; yüz normallerinin ürettiği üst/yan/ön ton farkı korunur. WebGL shadow map, post-processing ve parlama açılmaz. [Doğrulama ve sınırlar](../validation/c5/visualize-v4-validation-2026-11-17.md).

## Visualize V5 — minimal dış çevre (17 Kasım 2026)

`warehouse-exterior`, kamera sınırlarının alındığı `warehouse-environment` grubunun kardeşidir. Soluk gri-yeşil geniş zemin ve aynı renk arka planı, ince yol çizgileri, mal kabul dışında bir platform ve tek sabit kamyon, sevkiyat dışında kapalı yükleme kapısı/platformu ve dört küçük ağaç içerir. Geometri Three.js ilkellerinden oluşur; kutular instanced, ağaç geometrileri ve malzemeleri paylaşılır. Yeni ışık, shadow map, animasyon, post-processing veya harici model yoktur. Dış öğeler turkuaz/amber görev renklerini kullanmaz; mal akışı yalnız nesne yerleşimiyle anlatılır.

Sevkiyatın doğu duvarı ortak profilde gerçek engeldir. `exteriorLayout.ts`, bu duvarın yalnız görsel kopyasını sevkiyat bölgesinin merkezinde iki parçaya ayırır; üst kiriş ve alçak eşik kalır. Kapalı yükleme kapısı ve yükseltilmiş platform robot geçişi algısını sınırlar. Ortak layout, YAML, Gazebo collision, occupancy ve Nav2 değişmez. Mal kabulün mevcut batı açıklığı korunur; yeni görev noktası veya navigasyon hedefi üretilmez.

Alt araç satırındaki **Çevreyi göster**, dış kökü ve zeminle eşleşen arka planı açıp kapatır; kamera komutu veya sığdırma hesabı üretmez. Sevkiyatın görsel açıklığı depo grubunda kalır. Dış mesh'ler raycast'e katılmaz; robot/nokta görüş çizgisini kesen dış nesne geçici olarak gizlenir. Varsayılan kadraj değişmediği için bazı dış nesneler kenarda kırpılabilir; çevrenin bütününü incelemek için kullanıcı elle uzaklaşabilir. [Doğrulama ve sınırlar](../validation/c5/visualize-v5-validation-2026-11-17.md).

## Visualize V6 — yaşayan dış çevre (17 Kasım 2026)

V6, V5 dış kökünü koruyarak depo ayak izinden türetilen gri-yeşil beton avlu, soluk çim, iki şeritli yol ve kaldırım ekler. Saha çiti ve açık giriş kapısı, güvenlik kulübesi, teknik/ofis binası, dört ışıksız aydınlatma direği, iki rampanın yanındaki palet/konteynerler ve beş park edilmiş araç yalnız sunumdur. Dört küçük üçlü ağaç kümesinde konik ve yuvarlak tipler ile çalılar kullanılır. Sabit saha ayrıntıları kutu, koni ve düşük poligonlu yuvarlak geometri için üç instanced çizimde toplanır; araç ayrıntıları da instanced kutulardır. Harici model yoktur. Açık depo, turkuaz ALMA ve amber BIRAKMA önceliği korunur; dış palette bu vurgu renkleri yoktur.

Kullanıcının V6 talebi, V5'in hareketsiz dış çevresine yalnız **dekoratif** hareket ekler: yol üzerinde aynı anda en fazla bir araç (56 saniyelik döngüde 16 saniye geçiş), sevkiyatta 80 saniyelik döngüyle bekleyen, yavaşça uzaklaşıp geri yanaşan kamyon vardır. Mal kabul kamyonu sabit kalır. Sevkiyat kamyonunun manevrası dış avluda 2,8 m ile sınırlıdır; depo içine girmez. Saat yerel `performance.now()` kaynağındandır; ROS, TF, görev, gerçek sevkiyat ve `/clock` ile ilişkisi yoktur. Bu süreler ürün/navigasyon parametresi değildir.

Dekoratif timer 50 ms aralıkla en fazla yaklaşık 20 Hz görsel güncelleme ister; React state'i her karede değiştirmez. Çevre kapalı veya `document.hidden` iken timer iptal edilir; faz donar, dönüşte geçen süre yakalanmaz. Unmount temizliği timer ve visibility listener'ını kaldırır. Sabit saha için görüş kesiti kamera/robot/nokta pozu değişince yeniden hesaplanır; her dekoratif nesnenin instance'ları birlikte gizlenir. Dış mesh'ler pointer raycast'ine katılmaz. Dış kök kamera sığdırmasına girmez; yeni istasyon/hedef, fiziksel harita, ışık, shadow map veya post-processing yoktur.

Çevre kapalıyken V5'in sevkiyat açıklığı ve V4 iç sahnesi korunur. Devam eden render'lar robot/TF veya kamera nedeniyle olabilir; dış hareket saati kapalıdır. `trace=1` tanılama modundaki benchmark event'i yalnız eşit yükte FPS karşılaştırması için frame ister; ürün akışında kullanılmaz. [V6 doğrulaması ve ölçüm sınırları](../validation/c5/visualize-v6-validation-2026-11-17.md).

### V6 dış zemin paleti — 17 Kasım 2026

V6 saha düzeni ve hareketi korunur. Kullanıcının sonraki isteğiyle düz zemin bölgeleri ayrıştırıldı: soluk adaçayı çim `#9aa98f`, sıcak krem-gri avlu `#b8b2a8`, aynı ailede biraz daha koyu kaldırım `#b0aba2`, koyu nötr asfalt `#626762`, soluk beyaz mevcut yol çizgileri `#d5d7d1`. Palet `exteriorSite.ts::exteriorPalette` içinde tek yerde tutulur. Kaldırım yalnız kendi malzemesinde ışıktan bağımsız düz renk kullanır; diğer `Boxes` çağrılarının varsayılan malzemesi değişmez. Depo zemini ve çevre kapalı arka planı değiştirilmez. Açıktan koyuya depo → avlu → kaldırım → çim → yol sırası hedeflenir. Yeni doku/desen veya geometri eklenmez. [Güncel kontrol](../validation/c5/visualize-v6-palette-2026-11-17.md).
