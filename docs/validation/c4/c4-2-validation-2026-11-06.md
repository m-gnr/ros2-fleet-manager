# C4.2 — Battery Simulator, Executor ve Fleet Manager entegrasyonu

6 Kasım 2026. [Komut eki](c4-2-commands-2026-11-06.md) · [C4 geçiş onayı](../c3/c3-3-4-final-c4-gate-2026-11-05.md) · [C4.1 tüketim doğrulaması](c4-1-validation-2026-11-06.md)

Yerel `main`, upstream ve doğrudan GitHub sorgusu C4.1 commit'i `5630544f6e41f153364edd124761674c7fca68ee` üzerinde eşleşti. Kullanıcının `docs/README.md` içindeki rapor bağlantıları, izlenmeyen PDF ve `docs/reports/` içeriği korundu. Başlangıçtaki regresyon testi, ölçüm damgası taşımayan 100 Wh durumuyla SQLite görev kaydının `ASSIGNED` olduğunu gösterdi. C4.2'de aynı test `QUEUED` ve sıfır komut bekler.

## Veri akışı ve kaynak sürekliliği

| Akış | ROS sözleşmesi | Sorumluluk |
|---|---|---|
| Gazebo → Battery Simulator | `/clock` ve `/<namespace>/odom` | Robot başına C4.1 hareket ve taban güç tüketimi. |
| Battery Simulator → Executor | `/<namespace>/battery_state`, `fleet_interfaces/msg/BatteryState`, reliable/volatile, derinlik 10 | Wh, float32 SoC, kapasite, şarj durumu, simülasyon ölçüm damgası ve süreç UUID'si. |
| Executor → Fleet Manager | `/<namespace>/robot_status`, `fleet_interfaces/msg/RobotStatus`, reliable/volatile, derinlik 10 | RobotStatus sıra/oturum ve fiziksel alanlarıyla birlikte ölçülen Wh, SoC ve özgün `battery_stamp`. |
| Fleet Manager → SQLite/Scheduler | Tek consumer, robot snapshot'ı ve Outbox | Geçerli ölçüm, robot durumu ve rota ile uygunluk. Atama ve Outbox aynı transaction'da. |

Executor, ürün yolunda C1'le doğrulanmış kapasiteyi ve namespace'i kullanır. Robot kimliği, pozitif kapasite, sonlu Wh/SoC aralıkları ve %0,000005 puan SoC tutarlılık toleransı aranır. Sıfır, gelecekteki, 2 simülasyon saniyesinden eski, yinelenen ve geriye giden damgalar yeni ölçüm oluşturmaz. Enerjinin C4.2'de artması veya şarj bildirimi, süreklilik kanıtını geçersiz kılar.

Robot başına yalnız beklenen `battery_simulator` düğümünün tek DDS endpoint'i kabul edilir. Executor adı ve namespace'i çözümlenmiş ilk uygun endpoint'i GID ile sabitler. DDS writer keşfi ROS düğümü ilişkilendirmesinden önce gelirse telemetri, kimlik çözümlenene kadar bekler. İkinci endpoint, farklı tipte eski besleyici veya endpoint değişimi görülünce robotun batarya kabulü reset gerektirecek şekilde kilitlenir. Humble `rclpy` abonelik callback'inde mesaj başına yayıncı GID'si bulunmadığı için, DDS grafiğine ek olarak `BatteryState.publisher_session_id` eklendi. UUID her simülatör süreci açılışında üretilir. Aynı robot için değişen UUID, DDS grafiği güncellenmeden gelse bile ölçümü kilitler. `RobotStatus.battery_stamp` da eklendi. IDL değişikliğinden sonra bütün ROS katmanları birlikte yeniden derlenir. [Humble abonelik kaynak kodu](https://github.com/ros2/rclpy/blob/humble/rclpy/src/rclpy/subscription.cpp) · [Humble DDS grafik önbelleği](https://github.com/ros2/rmw_dds_common/blob/humble/rmw_dds_common/src/graph_cache.cpp) · [BatteryState](../../../interfaces/fleet_interfaces/msg/BatteryState.msg) · [RobotStatus](../../../interfaces/fleet_interfaces/msg/RobotStatus.msg)

C3.3.3 ve T02-AUTO-ROUTES tarihsel giriş noktaları açık test modunda `RobotStatus` tipli 100 Wh besleyicisini kullanır. C2.3 eski test varsayılanını kullanır. C4.2 canlı katmanı aynı Gazebo dünyasında bu besleyici yerine C1 listesinden iki Battery Simulator başlatır. Her Executor ürün aboneliğiyle çalışır. Temiz test dünyasının fiziksel reset kanıtı mevcut test giriş noktasıyla sağlanır.

## Güncellik, restart ve atama

- `RobotStatus.header.stamp` yayın zamanı, `pose.header.stamp` poz ölçüm zamanı, `battery_stamp` ise batarya ölçüm zamanıdır. Executor ROS saatiyle ölçüm yaşını, yerel monotonik saatle son kabulden beri geçen süreyi denetler. C4.2 uygulamasında iki bağımsız denetim için 2 saniye seçildi. Monotonik saatle ilerleyen RobotStatus zamanlayıcısı, Gazebo durakladığında batarya kaybını da bildirebilir. Batarya henüz yoksa Wh/SoC sıfırdır. Sonraki kayıpta son doğrulanmış değer korunur ve batarya damgası sıfırlanır.
- Fleet Manager topic kimliğini, mevcut Executor sıra/oturum denetimini, ölçüm yaşını, yapılandırılmış kapasiteyi ve Wh/SoC ilişkisini doğrular. İlk kabulde kalan geçerlilik süresi yerel monotonik son tarihe dönüşür. Aynı ölçümü tekrarlayan RobotStatus bunu uzatamaz. Scheduler karar anında son tarihi ve Gazebo ölçüm yaşını yeniden denetler. Normal RobotStatus stale süresi ve `SESSION_BLOCKED` bağımsızdır. Yanlış batarya alanları fiziksel durum güncellemesinden ayrılır.
- Uygunlukta `E_available = ölçülen Wh − C_usable × SoC_emergency / 100` kullanılır. Rota, kaçış ve güvenlik marjı mevcut kurallarla hesaplanır. Aynı denetim normal atamada, preemption adayı seçiminde, terminal PREEMPTED sonrasındaki yeni seçimde ve gecikmiş Nav2 rota sonucu sonrası zamanlamada çalışır. Geçersiz batarya yeni atamayı engeller ve devam eden işin durumunu değiştirmez. Uygun olmayan görev özgün FIFO zamanıyla kuyrukta kalır.
- Duraklamada simülasyon tüketimi ilerlemez. Monotonik telemetri süresi dolabilir. Aynı DDS endpoint'i ve UUID'den gelen daha yeni geçerli örnek, geçici kesintiden sonra robotu yeniden aday yapabilir.
- Gazebo saati geri sarıldığında C4.1 simülatörü Wh'yi koruyup odometri referansını sıfırlar. Executor ve Fleet Manager ayrı saat izleyicileriyle geri sarmayı veya ROS saat kaynağı değişimini algıladığında bataryaya dayalı yeni atamayı kilitler. Saatin yeniden ilerlemesi kilidi açmaz. Simülatör sürecinin restart'ında C1 başlangıç SoC'si %100'dür ve yeni UUID üretilir. Bu örnek mevcut senaryoda enerji sürekliliği olarak kabul edilmez.
- Executor restart'ı ayrı bir `RobotStatus.publisher_session_id` oluşturur. Fleet Manager mevcut sahipliği koruyarak `SESSION_BLOCKED` durumuna geçer. Yeni Executor, temiz DB veya batarya verisiyle görev kabul yetkisi kazanmaz. Operatörün fiziksel durum, yük, Nav2 hedefleri ve kaynakları uzlaştırması ya da doğrulanmış yeni senaryo başlatması gerekir. Ürün için otomatik reset/uzlaştırma protokolü gelecek kapsamdadır. [Executor güvenliği](../../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md) · [ROS adaptör kararları](../../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md)

## İki robotlu canlı kabul

**DOĞRULANDI** — Gazebo Fortress, Humble/CycloneDDS, iki Battery Simulator, iki Executor ve SQLite kullanan Fleet Manager. ROS grafiğinde iki batarya topic'inin her birinde bir ürün yayıncısı, ilgili Executor aboneliği ve ortak tek `/clock` görüldü. Geçici besleyici kapalıydı. BatteryState, RobotStatus, FM bellek kaydı ve SQLite snapshot'ı aynı damgaya ait Wh ve SoC'de birebir eşleşti.

İlk kontrol, C1'in kabul ettiği **91,99 Wh** test marjını geçici bir YAML kopyasında kullandı. Gerçek BatteryState değerleri ve her robotun üç gerçek Nav2 rota mesafesiyle gereken enerji kullanılabilir enerjiyi aştı. Görev kuyrukta kaldı ve SQL'de sıfır Outbox komutu vardı. İkinci kontrol ürün YAML'ıyla çalıştı. Robotlar dururken iki Battery Simulator süreci kısa süre duraklatıldı. İki RobotStatus akışı tazeliğini korurken batarya ölçümleri güncelliğini yitirdi ve yine sıfır Outbox komutu oluştu. Aynı DDS yazarları ve UUID'ler devam ettikten sonra daha yeni ölçümler kabul edildi. Zamanlayıcı, canlı Nav2 rotalarıyla `robot_1` için tek Outbox komutu üretti. Robot gerçek ExecuteTask teslimatını tamamladı. Tüketim katsayıları ve Gazebo saati iki kontrolde de aynıydı.

`fleet-c42-accept-verified` ölçümleri

| Robot | Kullanılabilir / gerekli enerji (Wh), test marjı | Teslimat penceresi (sim sn) | Odometri yer değiştirmesi (m) | Hareket tüketimi (Wh) | Son Wh / SoC (%) |
|---|---:|---:|---:|---:|---:|
| `robot_1` | 91,998333 / 92,614320 | 7,000 | 0,768 | 0,153605 | 99,839489 / 99,839493 |
| `robot_2` | 91,998333 / 93,295586 | 7,000 | ≈0 | ≈0 | 99,993097 / 99,993095 |

Teslimat penceresinde her robotun taban güç tüketimi yaklaşık 0,003889 Wh idi. Bu koşuda kesinti sonrasındaki atamada altı rota sonucu işlendi. Ürün YAML'ındaki tüketim katsayıları kullanıldı; gözlenen azalma tek başına görev uygunluğunu tersine çevirecek kadar büyük değildi.

## Test sonuçları

| Test grubu | Geçti | Kaldı | Atlandı |
|---|---:|---:|---:|
| C4.1 tüketim çekirdeği | 22 | 0 | 0 |
| C4.1 Battery Simulator Humble | 2 | 0 | 0 |
| C4.2 batarya örneği doğrulaması | 23 | 0 | 0 |
| C4.2 Fleet Manager, preemption, rota ve SQLite COMMIT | 4 | 0 | 0 |
| C4.2 Humble Executor ve Fleet Manager telemetrisi | 9 | 0 | 0 |
| Tam host Python + Executor | 370 | 0 | 27 |
| Tam ROS 2 Humble / CycloneDDS | 415 | 0 | 0 |
| Humble C2.3 ve C3.3.3 test config | 6 | 0 | 0 |
| C4.1 iki robotlu canlı Fortress | 1 | 0 | 0 |
| C4.2 iki robotlu canlı kabul | 2 | 0 | 0 |
| C3.3.3 canlı T01–T10 | 10 | 0 | 0 |
| Canlı T02-AUTO-ROUTES ve T01 | 2 | 0 | 0 |
| C2.3 canlı T01–T07 | 7 | 0 | 0 |

Odaklı otomatik testler tam seçkilerin alt kümeleridir. Host atlamaları ROS 2 gerektiren testler ve modüllerdir. C1 CLI, host C3.3.3 config testi ve üç Mermaid/SVG eşleşme ve taşma kontrolü de geçti. Tablo son kabul koşularını gösterir. Önceki denemeler aşağıda ayrı kayıtlıdır.

İlk C4.2 canlı koşusu 92 Wh test marjı C1'deki rezerv sonrası kullanılabilir enerjinin tamamını tükettiği için doğrulama aşamasında durdu. Backend çıkışı 1, simulation çıkışı 0 idi. C1 doğrulayıcısı korunarak test marjı 91,99 Wh yapıldı. İlk T02-AUTO-ROUTES koşusunda iki senaryo geçti ve backend 0 çıktı. Geçici besleyicide SIGINT sırasında Humble mesaj dönüşümü hatası simulation çıkışını 1 yaptı. Test besleyicisi sinyali bir durdurma bayrağına çevirip ROS callback'i döndükten sonra kapanacak şekilde değiştirildi.

C4.2 tekrarlarından birinde atama sırasında ikinci robotun henüz rota sonucu yoktu. İlk robotun üç geçerli rotası görev için yeterliydi. Test, ürün kararını değiştirmeden atanan robotun üç rotasını zorunlu tutacak şekilde düzeltildi. Başka bir tekrarda gerçek teslimat tamamlandıktan sonra Executor'ın SIGINT işleyicisiyle ana iş parçacığı aynı ROS context'ini kapatmaya çalıştı ve simulation 1 çıktı. Executor sinyali durdurma bayrağına çevirip ROS işçilerini bekledikten sonra context'i bir kez kapatacak şekilde güncellendi.

Bir sonraki deneme, DDS endpoint keşfedildiğinde ROS düğüm ilişkisinin henüz gelmemesi nedeniyle grafik kontrolünde durdu. Erken kapanışta Nav2 yaşam döngüsü servislerinden biri zaman aşımına uğradı. Executor, geçici kimlik belirsizliğinde telemetriyi reddedip grafiğin tamamlanmasını bekler. Bu sırada birden çok endpoint veya sabitlenmiş GID değişimi görülürse kilit davranışı sürer. Canlı test artık kimlik bilgisi gelene kadar bekler. Ayrı bir Humble koşusunda Python 3.10 SQLite yetki denetleyicisini kaldırma adımı testin SQL karşılaştırmasını engelledi. Mevcut regresyon desenindeki açık `SQLITE_OK` dönüşüne geçildi.

Son kabul ve regresyon seçkisindeki altı canlı Compose projesinin tamamında backend/simulation çıkışları **0/0**, `OOMKilled=false` ve `SIMULATION_SHUTDOWN clean=true` görüldü. Nav2 `Failed to make progress`, Docker SIGKILL ve supervisor zorla kapatma kaydı görülmedi. Docker simülasyon kapanışını SIGTERM ile başlattı. Yukarıdaki ara koşularda görülen 1 çıkış kodları ayrı tutuldu. T09 ve C2.3 hata kurtarma senaryolarındaki kasıtlı Nav2 abort, ilerleme hatası olarak sayılmadı.

## Sınırlar ve C4.3 önkoşulları

C4.2'nin Wh sürekliliği C4.1 odometri kalitesine bağlıdır. Simülatör hareket sırasında odometri kaçırırsa o aralığın hareket tüketimini geriye dönük tahmin etmez. Canlı kesinti deneyi iki robot dururken yapıldı. DDS keşif anı ağ gecikmesine bağlıdır ve UUID/GID kontrolleri kimlik doğrulaması yerine kaynak sürekliliğini denetler. Canlı Gazebo geri sarma ve canlı süreç restart'ı **HENÜZ TEST EDİLMEDİ**. Bu güvenlik dalları Humble'da kontrollü saat geri sarma, süreç UUID'si ve DDS endpoint değişimiyle doğrulandı. Koşu, normal YAML ile kısa teslimat sırasında tüketimi ve ayrı test marjıyla enerji yetersizliğini gösterir. Doğal boşalmanın aynı görev için uygunluk sınırını aştığı bir uzun koşu yapılmadı.

C4.3 için taze batarya ölçümüyle düşük enerji kararının kontrollü canlı doğrulaması, uygun şarj hedefi için gerçek Nav2 rota ve rezervasyon akışı, fiziksel varış/ayrılma kanıtları gerekir. C4.2 kabulü bu lojistik akışları veya şarjı kapsamaz.
