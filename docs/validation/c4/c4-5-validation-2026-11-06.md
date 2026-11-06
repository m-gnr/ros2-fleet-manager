# C4.5 — İki robotlu uçtan uca C4 kabulü

6 Kasım 2026. [Komut eki](c4-5-commands-2026-11-06.md) · [C4 kabul kontrol listesi](c4-acceptance-2026-11-06.md)

**C4 TAMAMLANDI.** İki robotlu Gazebo Fortress kabulü ve önceki aşamaların kritik regresyonları geçti.

Başlangıç commit'i `3424835c98161381ce7f871f9c4d20890c73d456`. C4.5 mevcut ürün yolunu gerçek Gazebo Fortress, Nav2, Humble/CycloneDDS, Executor, Battery Simulator, Fleet Manager ve SQLite ile sınar. Her kabul tekrarı iki ayrı temiz dünya ve ayrı veritabanı kullanır. Her iki profilde aynı C4.4 ürün kodu çalışır. Kabul katmanı test verisini ve ölçümleri düzenler.

## C4 aşamalarının kapsamı

| Aşama | Başlangıç ve bitiş | Uygulama ve kanıt |
|---|---|---|
| C4.1 | `2cfc2f2` → `5630544` | Gazebo saati ve odometriyle tüketim. [Doğrulama](c4-1-validation-2026-11-06.md) |
| C4.2 | `5630544` → `8eaba3b` | Bağımsız BatteryState, Executor güncelliği ve ölçülen Wh ile rota kararı. [Doğrulama](c4-2-validation-2026-11-06.md) |
| C4.3 | `8eaba3b` → `8282982` | Şarj yaklaşımı, park, güvenli bekleme ve HIGH duruş kapısı. [Doğrulama ve kök neden](c4-3-validation-2026-11-06.md) |
| C4.4 | `8282982` → `3424835` | Fiziksel temas, kısa süreli sahiplik, düşük SoC/FIFO şarj kuyruğu ve devir. [Doğrulama](c4-4-validation-2026-11-06.md) |
| C4.5 | `3424835` → bu raporu içeren commit | Enerji uygunluğu, kesinti, şarj devri ve şarj sonrası gerçek görevler. |

## Çalışan mimari ve ROS sözleşmesi

| Uç | Tür | Sorumluluk |
|---|---|---|
| `/clock` | `rosgraph_msgs/Clock` | Ortak Gazebo simülasyon zamanı. |
| `/<namespace>/odom` | `nav_msgs/Odometry` | Robot başına mesafe, hız ve duruş kanıtı. |
| `/<namespace>/physical_pose` | `geometry_msgs/PoseStamped` | Damgalı Gazebo dünya pozu. Şarj yarıçapı ve fiziksel dock ayrılması için kullanılır. |
| `/dock/<istasyon>/contacts` | `ros_gz_interfaces/Contacts` | DART çarpışma çifti ve temas zamanı. |
| `/<namespace>/dock_lease` | `fleet_interfaces/DockLease` | Fleet Manager'ın COMMIT sonrası kısa süreli dock sahipliği. |
| `/<namespace>/battery_state` | `fleet_interfaces/BatteryState` | Robotun tek enerji otoritesinden Wh, SoC, damga, oturum ve şarj istasyonu. |
| `/<namespace>/robot_status` | `fleet_interfaces/RobotStatus` | Executor fiziksel durumu, oturum, sıra, ölçülen enerji ve fiziksel ayrılma pozu. |
| `/<namespace>/execute_task` | `fleet_interfaces/ExecuteTask` | Epoch ve UUID ile tek taşıma sahipliği. |
| `/<namespace>/navigate_to_station` | `fleet_interfaces/NavigateToStation` | Dock, park veya güvenli bekleme hareketi. |
| `/<namespace>/compute_path_to_pose` | `nav2_msgs/ComputePathToPose` | Fleet Manager'ın robot bazlı rota ve enerji hesabı. |
| Yapılandırılmış `nav2_action_name` | `nav2_msgs/NavigateToPose` | Executor'ın robot bazlı fiziksel hareketi. |
| `/<namespace>/clear_robot_error` | `fleet_interfaces/ClearRobotError` | Yüksüz, güvenli durmuş ve doğru epoch'taki robot için operatör kurtarması. |

Fleet Manager mevcut rota ayaklarıyla taşıma ve güvenli şarja kaçış Wh'sini hesaplar. Kullanılabilir enerjiden acil rezerv düşülür ve marj bir kez uygulanır. Executor teslimat sonrasında yüksüzlüğü ve durumu yayımlar. Fleet Manager uygun istasyon ve hareket niyetini atomik kaydeder. Şarjda bağımsız Battery Simulator, doğrulanmış sahiplik, fiziksel temas, yarıçap ve duruşla ileri Gazebo zamanı üzerinden Wh artırır. Normal %80 devri veya dinamik göreve uygun çıkış sonrası dock, bağımsız fiziksel ayrılma kanıtı gelene kadar sahipli kalır. [Enerji sözleşmesi](../../configuration-c1.md) · [Şarj ve ayrılma](c4-4-validation-2026-11-06.md)

## Kabul profilleri

- **Enerji ve kesinti.** Geçici test YAML'ında marj 25 Wh, başlangıç SoC değerleri %26 ve %100. Her robotun üç gerçek Nav2 ayağı ayrı sorgulanır. İki robot da düşük SoC eşiğinin üstündeyken Wh yetersizliği yalnız birini eler. Battery Simulator süreçleri kısa süre duraklatıldığında fresh RobotStatus sürer ancak yeni komut oluşmaz. Aynı süreçler devam edince uygun robot MEDIUM taşımasını tamamlar. Wh kaybı, ölçüm damgasıyla BatteryState, RobotStatus ve SQLite arasında karşılaştırılır.
- **Şarj, kaynak devri ve görev.** %22 ve %24 başlangıç, test kopyasında 21.600 W şarj gücü. İlk robot gerçek dock temasından sonra %80 eşiğine ulaşır, park eder ve fiziksel ayrılmadan sonra istasyonu ikinci robot alır. İkinci robot %100'e ulaşır. Aynı Fleet Manager ve aynı SQLite veritabanında park sahibi önce LOW taşımasını alır, ardından dock'taki robot ayrı HIGH görevi için ayrılır. Yeni HIGH, ilk LOW'a güvenli iptal uygular. Eşleşen terminal, bağımsız odometri ve Outbox sırası denetlenir. İkinci HIGH görev kesilmeden tamamlanır.

Test başlangıçları, geçici marj ve hızlandırılmış şarj gücü ürün parametrelerine yazılmadı. Ürün simülasyon saati, odometri, şarj temas koşulları ve hareket güvenlik eşikleri profiller boyunca korundu.

## Başarısız koşular ve test altyapısı düzeltmeleri

`c45-energy-first` enerji ve telemetri kesintisi profilini geçti. `c45-charging-first` şarj devrini, iki taşımanın başlamasını, güvenli HIGH preemption'ı ve iki HIGH teslimatını tamamladı. Son telemetri denetimi zaman aşımına uğradı. SQLite, kesilen LOW'un normal Scheduler tarafından yeni epoch ile ASSIGNED durumuna getirildiğini gösterdi. Test sürücüsü bu yeni Outbox komutunu göndermeden yeni epoch'un telemetrisini bekliyordu. Executor henüz komutu almadığı için eski epoch yayınında kaldı ve FM onu yeni sahipliğe uygulamadı. Backend 1, simulation 0 ile temiz kapandı. Başarısız koşunun SQLite ve log kanıtları saklandı.

Test sürücüsü, yeniden kuyruklanan LOW ve bekleyen istasyon hareketlerini normal Outbox üzerinden yürütür. LOW'un özgün `created_at` değeri korunur, kesilme sayacı 1 olur ve eski goal UUID tekrar yürütülmez. Eski terminal yeni olay kimliğiyle geldiğinde STALE, aynı olay tekrarında DUPLICATE sonucu beklenir. Son ölçümler, bekleyen hareketler kapandıktan sonra aynı damgalarla karşılaştırılır. Ürün Scheduler, Executor, güvenlik eşikleri ve SQLite davranışı bu düzeltmede değişmedi.

`c45-regression-high` bağımsız HIGH regresyonunda duruş ve teslimat geçti. Executor ile gözlemci 5,075 sn damgalı, 0,01 m/sn ve 0,01 rad/sn sınırları içindeki aynı odometriyi gördü. Ardından ROS kapanırken test TF yardımcısının varsayılan SIGINT istisnası DDS mesajını Python'a aktaran işlemi böldü. `tf_helper` 1 ile çıktı ve supervisor `SIMULATION_SHUTDOWN clean=false` bildirdi. Backend 0 ile kapandı, OOM görülmedi. Kapanış başarısızlığı ve SQLite kopyası `/tmp/fleet-c43-recovery/` altında saklandı.

Test TF yardımcısı artık SIGINT ve SIGTERM ile bir durdurma bayrağı ayarlıyor. Mesaj işlemesi döndükten sonra ROS düğümü ve bağlamı sırayla kapanıyor. TF verisi ve test eşikleri aynı kaldı.

`c45-regression-high-repeat` koşusunda Nav2 iptal terminali 4,355 sn, ardışık duruş aralığı 4,585–4,795 sn ve terminal kararı 4,805 sn idi. Bağımsız gözlemci 4,795 sn damgalı `robot_1/odom` örneğini aynı hızlarla aldı ve terminalden sonra altı duruş örneği kaydetti. HIGH, epoch 2 ile tamamlandı. TF yardımcısı ve iki konteyner 0 ile döndü. SQLite bütünlük kontrolü `ok` sonucunu verdi ve yabancı anahtar ihlali çıkmadı.

## Ölçülen enerji ve atama

Enerji profilinde ölçülen toplam rotanın taşıma ve kaçış ayakları ayrı tutuldu. Örneğin `c45-energy-final-3` koşusunda robot 1 için üç ayak 3,906 m, 0,600 m ve 3,454 m idi. Acil rezerv sonrası 17,998 Wh kullanılabilir enerji, gereken 26,592 Wh'nin altında kaldı. Robot 2 için ayaklar 0,500 m, 0,600 m ve 3,454 m, kullanılabilir enerji 91,998 Wh ve gereksinim 25,911 Wh idi. Gerçek batarya yayını kesildiğinde Outbox boş kaldı. Yayın toparlandığında yalnız robot 2 için bir taşıma komutu oluştu ve MEDIUM teslimatı tamamlandı. Robot 2 ölçümü 99,998 Wh'den 99,802 Wh'ye, bekleyen robot 1 ölçümü 25,998 Wh'den 25,992 Wh'ye düştü. İki robotun Wh ve SoC değerleri bağımsız BatteryState ölçümü, RobotStatus ve SQLite'ta aynı damgalarla eşleşti.

Şarj sonrası HIGH denetiminde aynı epoch ve goal UUID için önce geçerli `PREEMPTED`, sonra yeni `EXECUTE_TASK` görüldü. İkinci robotun çalışan HIGH görevi iptal komutu almadan tamamlandı. Eski terminal tekrarları yeni komut oluşturmadı. Kesilen LOW, aynı sıra zamanı ve kesilme sayacı 1 ile daha yüksek epoch'ta tamamlandı. Yüklü faz koruması, oturum değişiminde kilit ve iletişim kesintisinde aktif görevi otomatik FAILED yapmama kuralları son host/Humble seçkilerinde ve ilgili C3.3.3 senaryolarında yeniden sınandı.

## Son iki kabul tekrarı

`final-3` ve `final-4` tekrarları aynı ürün kodu, test sürücüsü ve eşiklerle çalıştı. Her tekrar ayrı enerji ve şarj projeleri, temiz Gazebo dünyaları ve ayrı SQLite dosyaları kullandı. Robot 2 her enerji profilinde tek MEDIUM komutu ile teslimatı tamamladı. Şarj profillerinde ilk robotun tekeri, ikinci robotun caster'ı dock pediyle temas etti. İlk robot %80'i geçince park etti ve 0,35 m fiziksel ayrılma sınırından sonra kaynak devredildi. İkinci robot %100'e ulaştı.

| Şarj profili | Robot 1 temas / ayrılma | Fiziksel ayrılma | Robot 2 temas / en yüksek | HIGH duruşu | Görevlerden sonra robot 1 / 2 |
|---|---:|---:|---:|---|---:|
| `c45-charging-final-3` | 21,452 / 81,959 Wh | 0,442 m | 23,089 / 100,000 Wh | 13 bağımsız örnek, karar 67,525 sn | 80,476 / 98,351 Wh |
| `c45-charging-final-4` | 21,436 / 81,945 Wh | 0,388 m | 23,073 / 100,000 Wh | 13 bağımsız örnek, karar 68,945 sn | 80,423 / 98,364 Wh |

Dört kabul projesi ve son bağımsız HIGH koşusunda backend/simulation 0/0, `OOMKilled=false` ve `SIMULATION_SHUTDOWN clean=true` kaydedildi. Nav2 ilerleme hatası, SIGKILL veya supervisor zorla sonlandırması görülmedi. Dört profil veritabanı ve HIGH kopyası `PRAGMA integrity_check` için `ok` döndürdü. Yabancı anahtar ihlali çıkmadı. Şarj profillerinde iki HIGH, LOW'un ilk çalışması ve yeniden atanması için dört ayrı `EXECUTE_TASK` kaydı oluştu. Her mantıksal goal UUID kendi komutunda tekil kaldı.

## Son test sonuçları

| Seçki | Geçti | Kaldı | Atlandı |
|---|---:|---:|---:|
| Tam host Python ve Executor | 409 | 0 | 28 |
| Tam ROS 2 Humble ve CycloneDDS | 457 | 0 | 0 |
| Humble C2.3 ve C3.3.3 config | 6 | 0 | 0 |
| C4.1 ve C4.2 canlı regresyon projeleri | 2 | 0 | 0 |
| C3.3.3 canlı T01–T10 | 10 | 0 | 0 |
| Bağımsız canlı T01 ve T04-HIGH-E2E | 2 | 0 | 0 |
| C4.5 son enerji ve kesinti profilleri | 2 | 0 | 0 |
| C4.5 son şarj, kaynak devri ve görev profilleri | 2 | 0 | 0 |

Host atlamaları ROS 2 Humble ve kurulu IDL gerektiren seçkilerdir. Humble seçkisi atlama olmadan geçti. C4.1, C4.2 ve son C3.3.3 canlı projelerinde iki konteyner 0/0 ve `OOMKilled=false` ile kapandı. C3.3.3 T09'da kasıtlı harita dışı hedef reddi ve operatör kurtarması beklenen sonuçtu. İlk birleşik şarj koşusu ve ilk HIGH kapanış başarısızlığı, yukarıdaki son test sayılarından ayrı raporlandı. Ara `final-1` ve `final-2` profillerinin kayıtları da saklandı.

## Bilinen sınırlar ve C5 önkoşulları

- Kabul, iki TurtleBot3 benzeri simülasyon robotu ve mevcut haritada geçerlidir. Fiziksel batarya elektroniği, kalibrasyon, 3+ robot, küresel trafik, dar koridor ve uzun süreli tepe yük kapsam dışıdır.
- Ürün tasarımında tek aktif Fleet Manager ve kontrollü senaryo reseti korunur. Kaynak oturumu değişirse yeni atama ve fiziksel kaynak bırakma kilitlenir. Kalıcı Outbox ağda exactly-once teslim garantisi vermez.
- C5'in başlangıç girdileri C4'ün ROS ve Wh sözleşmesi, görev ve kaynak durumlarının SQLite kaydı ile [kabul kontrol listesidir](c4-acceptance-2026-11-06.md). C5, FastAPI ve WebSocket uçları, DDS ağının dışında React/Konva ve hedef üç servisli Compose doğrulamasını kapsar. Config Apply için etkin görev ve yük yokluğu ile kontrollü restart şartları geçerlidir.
