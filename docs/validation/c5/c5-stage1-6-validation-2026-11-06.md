# C5 / Aşama 1.6 depo öncelikli operasyon paneli

**6 Kasım 2026 · İki robotlu Gazebo Fortress ve Chrome kabulü DOĞRULANDI**

[Komutlar](c5-stage1-6-commands-2026-11-06.md) · [Aşama 1.5 kabulü](c5-stage1-5-validation-2026-11-06.md) · [3D veri akışı](../../design/c5-3d-operations.md)

## Yerleşim ve veri sunumu

- Üst menü tek başlıkta toplandı. Özet şeridi snapshot'tan toplam robot ve görev sayısını, aktif görevleri, canlı ürün telemetrisi olan robotları ve doğrulanmış şarj durumunu gösteriyor. Kaynak eksikse ilgili değer boş gösteriliyor. Canlı telemetri sayacı, ürün akışındaki LIVE durumunu sayıyor.
- 3D depo masaüstü çalışma alanının en geniş bölümü. Alt filo kartları kimlik, operasyon durumu, geçerli SoC, görev ve TF durumunu tek satırda gösteriyor. Yatay kart akışı ek robotlar için kayabiliyor. Model ve kart seçimi aynı robot kimliğini ve sağ paneli güncelliyor.
- Başlangıç, üstten görünüm ve sıfırlama, depo mesh'lerinin sınır köşelerini güncel viewport oranıyla perspektif frustum'a yerleştiriyor. 42° görüş açısı korunuyor. Sınırlayan eksende %90 kadraj ve 0,85–48 m orbit mesafesi kullanılıyor. Orbit elle ayarlandıktan sonra viewport değişimi kullanıcının konumunu koruyor. Takip ve filo kadrajı mevcut TF konumlarını kullanıyor.
- Robot modeli fiziksel ölçülerini koruyor. Renkli konum halkaları daha belirgin. Kimlik ve TF tazeliği etiketi aynı robotun ekran konumuna bağlı. Etiketler örtüştüğünde seçili robotun etiketi öncelikli. Kontrol çubuğu, görünür temsili depo etiketi ve Durum B lejandı ayrı yüzeylerde.
- Sağ panel kimlik, ürün güvenilirliği, batarya, görev, şarj, TF ve Nav2 durumlarını öne alıyor. Konum ve ölçüm ayrıntıları açılır bölümde. Canlı ürün telemetrisinde `status_age_sec` kaynak snapshot'ındaki monotonik alım yaşını gösteriyor. TF, batarya ve plan damgaları **ROS zamanı** ile etiketleniyor. Kesintide son kayıtlar ayırt ediliyor ve batarya yüzdesi kullanılamaz olarak gösteriliyor.
- C5 WebSocket, ürün güvenilirliği, TF tazeliği ve gözlemlenen Nav2 planı ayrı göstergeler. Plan üzerindeki **Durum B** etiketi korunuyor. [Salt okunur API sözleşmesi](../../design/c5-readonly-api.md)

## Chrome yerleşim karşılaştırması

Aynı hostta gerçek Chrome ve her iki aşamanın üretim build'i kullanıldı. 1440×900 başlangıç kaydı, diğer boyutlar taşıma senaryosu sonrası genel görünümden alındı.

| Ekran | Aşama 1.5 sahne alanı (px) | Aşama 1.6 sahne alanı (px) | Aşama 1.6 belge boyutu (px) |
|---|---:|---:|---:|
| 1280×850 | 688×434 | 938×493 | 1280×850 |
| 1440×900 | 848×459 | 1.063×539 | 1440×900 |
| 1920×1080 | 1.234×551 | 1.500×719 | 1920×1080 |
| 390×844 | 356×304 | 368×328 | 390×1216 |

1440×900'de sahne alanı %47,2 büyüdü. Özet yüksekliği 89 px'den 39 px'e, ilk kartın üst kenarı 927 px'den 832 px'e indi. Aşama 1.5 belgesi 1.128 px yüksekliğindeydi.

[1440×900 yan yana karşılaştırma](stage1-6/screenshots/compare-1440.jpg)

| Viewport | Aşama 1.5 | Aşama 1.6 |
|---|---|---|
| 1280×850 | [Tam sayfa](stage1-6/screenshots/before-1280.png) | [Ekran](stage1-6/screenshots/after-1280.png) |
| 1440×900 | [Tam sayfa](stage1-6/screenshots/before-1440.png) | [Ekran](stage1-6/screenshots/after-1440.png) |
| 1920×1080 | [Tam sayfa](stage1-6/screenshots/before-1920.png) | [Ekran](stage1-6/screenshots/after-1920.png) |
| 390×844 | [Tam sayfa](stage1-6/screenshots/before-390.png) | [Tam sayfa](stage1-6/screenshots/after-390.png) |

1440×900'de model ve klavye ile seçim, açık kamera kontrolleri ve ilk ekrandaki filo kartları doğrulandı. Başlangıç kadrajı ön zemin köşesini kapsıyor. Mobilde menü ve kartlar kullanılabiliyor, panel sahnenin altında ve sayfa genişliği 390 px. Etiket önceliği yakın pozlu fixture ile doğrulandı. Üçüncü kartın mobil kaydırması ve klavye seçimi de fixture ile denetlendi.

[Seçili robot](stage1-6/screenshots/selected-robot.png) · [Takip](stage1-6/screenshots/camera-follow.png) · [Filo kadrajı](stage1-6/screenshots/camera-fit.png) · [Tek robotta TF STALE](stage1-6/screenshots/isolated-tf-stale.png) · [WebSocket kesintisi](stage1-6/screenshots/connection-loss.png) · [Plan ve TF izi](stage1-6/screenshots/active-task-plan.png)

## Canlı Gazebo ve Chrome

- ARM64 Gazebo Fortress, iki bağımsız Nav2 ve C4.5 şarj sürücüsü temiz SQLite ile çalıştı. İki robotun hareketi ve doğrulanmış şarjı görüldü. Üç taşıma görevi tamamlandı. C5 kabul okuyucusu SoC/Wh ve ürün pozunu ROS ölçümleriyle, görev ve istasyon sahipliğini SQLite ile karşılaştırdı.
- Chrome'da çizilen 1.481 poz ve çizgi uçları relay paketleriyle eşleşti. Bağımsız ROS okumalarında 4.571 aynı damgalı TF pozunun konum farkı 0 m, en büyük yaw farkı 8,88 × 10⁻¹⁶ rad. Gözlemlenen planlarda robot 1 için 67, robot 2 için 70 eşleşme konu, damga ve tüm noktalar üzerinden doğrulandı. [Bağımsız ROS karşılaştırması](stage1-6/measurements/ros-chrome-compare.json)
- TF test kapısı robot 2'yi STALE yaptı. Diğer robotun TF'i ve ürün akışı canlı kaldı. Köprü durup açıldığında kaynak oturumu korundu. API yeniden başladığında aynı ürün kaynağında yeni API oturumu kabul edildi. Chrome kapalıyken kaynak ilerlemeye devam etti.
- Kamera modları ve seçim doğrulandı. Tarayıcı yalnız `/ws/fleet` açtı. Kritik JavaScript/WebGL hatası görülmedi. Köprüde salt okunur ROS abonelikleri gözlendi. Üç konteyner temiz kapandı, SQLite bütünlük kontrolü `ok` döndürdü. [Chrome çıktısı](stage1-6/measurements/chrome.log) · [C4.5 şarj ve kaynak kontrolü](stage1-6/measurements/c4-5-c5.log) · [Kaynak snapshot’ı](stage1-6/measurements/verified-source.json) · [ROS grafiği](stage1-6/measurements/bridge-graph.txt) · [Kapanış](stage1-6/measurements/shutdown.txt) · [SQLite bütünlüğü](stage1-6/measurements/sqlite-check.txt)

## Performans

Chrome headless, 1440×900, canlı iki robot ve sahne ölçüm izi açık. Plan ve TF izi açık ve kapalıyken yaklaşık beş saniyelik ardışık örnekler alındı. İlk WebGL çizimi navigasyon başlangıcından, klavye seçimi Enter ve ayrıntı panelinin görünmesinden ölçüldü. CPU bir çekirdeğin yüzdesi, RSS Chrome süreçlerinin toplamıdır.

| Ölçüm | 1.5 açık | 1.6 açık | 1.5 kapalı | 1.6 kapalı |
|---|---:|---:|---:|---:|
| Sahne FPS | 58,1 | 58,5 | 58,7 | 58,6 |
| Frame aralığı p95 (ms) | 18,7 | 18,4 | 18,7 | 18,8 |
| Draw call p95 | 59 | 59 | 53 | 53 |
| Geometri / texture | 59 / 3 | 59 / 3 | 59 / 3 | 59 / 3 |
| JS heap (MiB) | 15,6 | 17,7 | 24,9 | 28,7 |
| Chrome CPU (%) | 35,3 | 28,6 | 37,9 | 30,0 |
| Chrome RSS (MiB) | 938,4 | 925,0 | 940,1 | 929,7 |

İlk WebGL çizimi 5,34 sn ve 5,38 sn. Klavye seçiminin tek örneği 30,2 ms ve 52,3 ms. Sahne FPS ve çizim yükü yakın kaldı. Bu ölçümde Chrome CPU düşerken JS heap ve seçim süresi yükseldi. Seçim gecikmesi için dağılım ölçülmedi.

[1.5 ham ölçümler](stage1-6/measurements/before-browser-metrics.json) · [1.6 ham ölçümler](stage1-6/measurements/after-browser-metrics.json)

## Regresyonlar

| Seçki | Yeni koşu |
|---|---|
| Üretim frontend build | Geçti |
| Chrome / Playwright üretim build'i | 12 geçti |
| C5 salt okunur backend | 7 geçti |
| Tam host Python / Executor | 416 geçti, ROS çalışma zamanı gerektiren 28 test atlandı |
| Humble / CycloneDDS | 464 geçti |
| C2.3 ve C3.3.3 config seçkileri | 3 + 3 geçti |
| Visualizer Aşama 4 frontend ve ROS köprüsü | 21 frontend testi ve 25 köprü testi geçti |
| C4.5 seçilmiş canlı şarj profili | İki robot, doğrulanmış şarj ve üç tamamlanan görev |

İlk arayüz koşusunda açılır ölçüm bölümü eklenince mevcut testin seçicisi iki özeti eşleştirdi. Test doğrudan robot paneli başlığını hedefleyecek şekilde düzeltildi. İlk canlı yerleşim koşusunda 1440×900 belgeye sığdı ancak sahne yüksekliği ve geometri kadrajı görsel hedefin altında kaldı. Üst boşluklar azaltıldı ve köşe tabanlı kadraj yeniden doğrulandı.

Kısa ölçüm pencereleri iki robot ve yerel kabul ortamını kapsıyor. Uzun süreli yük, fiziksel robot, 3+ robotla canlı çalışma ve nihai üç servisli ürün dağıtımı **HENÜZ TEST EDİLMEDİ**. Durum B için aktif goal ilişkisi **HENÜZ TEST EDİLMEDİ**.

## Git kapsamı

`feat/c5-dashboard-ui-polish`, `ros2-fleet-manager-c5-ui-polish` worktree'sinde oluşturuldu. Taban `72e500eb84e0409f220779adab5035a2bcf28f0f`. GitHub'daki `feat/c5-3d-operations-dashboard` ucu ve yerel dal aynı SHA'yı döndürdü. Yerel Aşama 1.6 commit başlığı `feat(c5): polish 3D operations dashboard`. Tam SHA için dalda `git log -1 --oneline` kullanılabilir. Değişiklik kapsamı C5 frontend sunumu, ilgili Chrome testleri ve bu doğrulama kaydıdır.
