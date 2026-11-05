# C4.3 — Şarj istasyonuna, parka ve güvenli beklemeye yönlendirme

6 Kasım 2026. [Komut eki](c4-3-commands-2026-11-06.md) · [C4.2 kabulü](c4-2-validation-2026-11-06.md)

**DOĞRULANDI.** İstasyon yönlendirmesi, düzeltilen canlı HIGH duruş kontrolü ve son regresyonlar geçti. İlk durdurma ve başarısız yeniden üretimler aşağıda korunur.

Başlangıç commit'i `8eaba3b7c37dbc8867815ff483713ea2f6d64ebb`. Yerel `main`, upstream ve doğrudan GitHub sorgusu eşleşti. C4.2'nin iki önceki temiz koşusunun ham kayıtları incelendi. Aynı HEAD'de canlı C4.2 yeniden çalıştırıldı. Gerçek BatteryState → RobotStatus → Fleet Manager → SQLite akışı, tek batarya yayıncısı, kesintide yeni atamanın engellenmesi, aynı oturumda toparlanma ve Nav2 teslimatı geçti. Kullanıcının yerel dokümantasyon değişiklikleri ve izlenmeyen dosyaları korundu.

## Uygulama ve güvenlik

- C1 `fleet.yaml` altındaki şarj, park ve güvenli bekleme alanları kullanılır. Yüksüz, görevsiz robotun batarya ve RobotStatus verisi taze olmalıdır. Düşük SoC şarj önceliği alır. Teslimat sonrası yeterli enerjide boş park hedeflenir. Uygun birincil hedef yoksa tanımlı güvenli bekleme alanı denenir. Uygun hedef de yoksa robot bekler ve `STATION_DISPATCH_WAIT` nedeni kaydedilir. Varsayılan YAML'da güvenli bekleme listesi boştur.
- Adaylar robotun kendi `compute_path_to_pose` sonuçlarıyla sıralanır. Şarj yaklaşımı hareket tüketimi, mevcut Wh rezervi ve marjı kullanır. Park ve güvenli bekleme için hedef sonrasındaki güvenli şarj rotası da hesaba katılır. Planner sonucu yoksa ilgili aday elenir. Rota sorgusu COMMIT sonrasında çalışır.
- Fleet Manager `/<namespace>/navigate_to_station` üzerinden `fleet_interfaces/action/NavigateToStation` gönderir. Goal, hareket kimliği, robot ve istasyon kimliği, beklenen Executor oturumu, ortak atama epoch'u, YAML hedef pozu ve yarıçapını taşır. ROS goal UUID'si Outbox'taki kimliktir. Executor aynı Nav2 istemcisini ve tek kabul kilidini `ExecuteTask` ile paylaşır.
- `station_moves`, rezervasyon ve değişmez Outbox niyeti aynı SQLite transaction'ında yazılır. Belirsiz DDS yanıtında adaptör mevcut future'ı bekler. Açık action reddinde komut incelemeye alınır ve kaynak tutulur. Terminal Nav2 hatasında istasyon bloke edilir, robot hata bildirir ve tamamlanmış taşıma sonucu korunur.
- PARK ve güvenli bekleme dönüşleri her görev önceliğinde güvenli iptale adaydır. Eşleşen Nav2 iptal terminali ile daha yeni, hareketsiz odometri gelmeden yeni hareket açılmaz. Doğal varış ve hata kendi sonuçlarını korur. Lojistik iptal taşıma kesilme sayacını artırmaz.
- Executor, ürün yolunda odometri damgasında robotun `map ← <namespace>/odom` TF dönüşümünü kullanır. Poz doğrulanamazsa o örnek istasyon varış veya ayrılma kanıtı olmaz. Başarılı istasyon varışı Nav2 terminali, daha yeni hareketsiz odometri ve yapılandırılmış yarıçap gerektirir. Ayrılma için bu ölçümden daha yeni geçerli poz ile `tolerance_radius + departure_margin` sınırı aşılmalıdır. `BLOCKED` veya oturumu değişmiş kaynak otomatik serbest bırakılmaz.

## Canlı Fortress kabulü

`c43-tf` ve `c43-confirmed` ayrı Compose projesi, temiz dünya ve SQLite dosyasıyla çalıştı. `robot_1` ürün başlangıç enerjisiyle taşıma görevini tamamlayıp `park_1` hedefine gitti. `robot_2` için kabul düzeneği gerçek Battery Simulator'ın yalnız başlangıç SoC'sini %24 yaptı. Tüketim katsayıları, simülasyon saati, Wh rezervi, rota ve varış eşikleri ürün değerleriydi. `robot_2` taşıma almadı ve gerçek Nav2 ile `dock_1` alanında durdu. Geçici batarya besleyicisi kapalıydı.

| Koşu | Robot ve kaynak | Epoch | Executor / Gazebo merkez hatası (m) | Son Wh |
|---|---|---:|---:|---:|
| `c43-tf` | `robot_1` · `park_1` | 2 | 0,214 / 0,219 | 99,500 |
| `c43-tf` | `robot_2` · `dock_1` | 1 | 0,196 / 0,218 | 23,099 |
| `c43-confirmed` | `robot_1` · `park_1` | 2 | 0,208 / 0,262 | 99,510 |
| `c43-confirmed` | `robot_2` · `dock_1` | 1 | 0,227 / 0,229 | 23,102 |

İki koşuda her istasyon `OCCUPIED` ve doğru robotun sahipliğindeydi. Tek taşıma ve iki ayrı istasyon action'ı için üç benzersiz UUID, üç `SENT` Outbox kaydı ve her kayıtta bir gönderim denemesi görüldü. İki SQLite dosyasında `PRAGMA integrity_check` sonucu `ok` ve yabancı anahtar ihlali sıfırdı. Nav2 ilerleme hatası, zorla sonlandırma veya OOM görülmedi. Backend ve simulation çıkışları 0/0 idi. İki canlı senaryoda da park iptali tetiklenmedi.

## İlk durdurma sırasındaki test durumu

| Test grubu | Geçti | Kaldı | Atlandı | Kapsam |
|---|---:|---:|---:|---|
| Odaklı Python | 18 | 0 | 0 | 14 istasyon ve 4 C4.2 domain testi |
| Tam host Python ve Executor | 384 | 0 | 28 | ROS 2 gerektiren seçki hostta atlandı |
| Tam Humble ve CycloneDDS, ara koşu | 425 | 0 | 0 | TF düzeltmesinden ve ek park senaryolarından önce |
| Odaklı Humble ve CycloneDDS | 3 | 0 | 0 | Ortak kabul, güvenli park iptali, dock iptal reddi ve aynı goal future'ıyla retry. TF düzeltmesinden önce |
| Host C3.3.3 config | 3 | 0 | 0 | C1 CLI doğrulaması ayrıca geçti |
| C4.3 canlı kabul denemeleri | 2 | 3 | 0 | İlk üç başarısız koşunun ayrıntıları aşağıda |
| C4.1 ve C4.2 canlı regresyon | 3 | 0 | 0 | C4.1 bir, C4.2 iki senaryo |
| C3.3.3 canlı T01–T10 | 10 | 0 | 0 | Ana regresyon |
| Canlı T01 ve T04-HIGH-E2E | 1 | 1 | 0 | T01 geçti. HIGH duruş kontrolü kaldı |

Kritik duruştan önce eklenen, düşük SoC'li robotun dolu dock beklerken mevcut güvenli alanında kalmasına ilişkin son değişiklik ve testi **HENÜZ DOĞRULANMADI**. Son adayda tam Humble seçkisi ve ayrı T02-AUTO-ROUTES koşusu **HENÜZ DOĞRULANMADI**.

## Başarısız koşular ve düzeltmeler

- İlk odaklı test, C4.3 öncesinde beklenen istasyon komutunu üretmedi. İlk yeşil denemeden önceki ikinci test seçkisi 12 geçti ve 2 kaldı. OCCUPIED fixture'ında sahibi yanlışlıkla dock dışında gösteriliyordu. C4.2 eşik testi ise C4.3 yönlendirmesiyle aynı düşük SoC aralığındaydı. Test marjı, hassas Wh eşiğini düşük SoC sınırının üstünde ve aynı 0,000001 Wh farkla sınayacak şekilde yükseltildi.
- `c43-first` koşusunda planner etkinleşti, ancak `bt_navigator` henüz etkinleşmeden verilen hareket reddedildi. Kaynak `BLOCKED` kaldı. Sonraki canlı koşularda iki `bt_navigator` için etkin lifecycle durumu beklenir. Ürün action reddinden sonra hareketi otomatik tekrar etmez.
- `c43-second` ve `c43-diag` koşularında Nav2 parkı bitirdi. Başlangıç pozundan türetilen Executor odometrisi yaklaşık 0,39–0,40 m hata gösterdi. Tanıda aynı park varışında Gazebo yaklaşık 0,23 m ve AMCL 0,22 m gösterdi. Executor varışı reddetti ve kaynak bloke kaldı. Canlı konum denetimi odometri damgasındaki robot bazlı harita TF'sine geçirildi. İstasyon yarıçapı ve Nav2 eşikleri korundu. Bu iki tanı koşusu diğer hareket devam ederken kesildi ve onun belirsiz sahiplik kapanış hataları loglandı. Üç başarısız canlı koşu da backend 1, simulation 0 ve `OOMKilled=false` ile sonuçlandı.

## İlk kritik yayın engeli

`fleet-c43-high` koşusunda T01 geçti ve gerçek LOW Nav2 hedefi iptal edildi. Eşleşen `PREEMPTED` işlenirken bağımsız gözlemcinin son odometri örneği 0,005 sn yaşında, doğrusal hız 0,043421 m/sn ve açısal hız yaklaşık sıfırdı. Test eşiği 0,01 m/sn'dir. Executor'ın terminal kararı için kullandığı odometri örneği ham kayıtta ayrı bir zaman damgasıyla yer almadığından gözlemci ile Executor örneğinin aynı olup olmadığı belirlenemedi. Yeni HIGH hedefinin Executor tarafından kabul edildiğine ilişkin kayıt yoktur.

Backend 1, simulation 0 ile kapandı. `OOMKilled=false`, Docker sonlandırma sinyali SIGTERM ve `SIMULATION_SHUTDOWN clean=true` görüldü. Test durduğunda ikinci robotun hareketi sürüyordu ve Executor kapanışta belirsiz sahipliği logladı. Başarısız koşunun ham logu ve Docker çıkış kaydı korundu. Geçici HIGH SQLite dosyası konteyner kaldırılmadan hosta kopyalanmadı.

İlk durdurmada C4.3 yerel çalışma ağacında kaldı. Yerel ve uzak `main` C4.2 commit'inde eşleşiyordu. Kök neden ve yayın kapısının yeniden doğrulanması aşağıda yer alır.

## HIGH preemption kök neden ve düzeltme

İnceleme, özgün `fleet-c43-high` logundaki iki olay arasındaki yaklaşık 70 ms'yi ayırdı. `NavigateToPose` iptal terminali önce geldi. `FollowPath` denetleyicisi daha sonra durma kaydı verdi. Humble davranış ağacı alt action sonucunu sınırlı süre bekler ve süre dolduğunda `halt` tamamlanabilir. Controller, `cmd_vel_nav` yayınını keserken velocity smoother son komutu `cmd_vel` üzerinde kademeli düşürebilir. Executor da fren için aynı `cmd_vel` girişine sıfır yayınlıyordu. [Nav2 Humble davranış ağacı](https://github.com/ros-navigation/navigation2/blob/humble/nav2_behavior_tree/include/nav2_behavior_tree/bt_action_node.hpp#L282) · [Controller](https://github.com/ros-navigation/navigation2/blob/humble/nav2_controller/src/controller_server.cpp#L361) · [Hız topic bağlantıları](https://github.com/ros-navigation/navigation2/blob/humble/nav2_bringup/launch/navigation_launch.py#L95)

Eski kod, ilgili Nav2 terminalinden önce alınmış olsa bile son taze sıfır hız örneğini kullanabiliyordu. Odometri callback'i ölçüm sırasını da korumuyordu. İlk odaklı regresyon 6 geçti ve 3 kaldı. Önceden alınmış duruş ve terminalden sonraki tek örnek eski kodda `PREEMPTED` üretti.

| Tanı koşusu | Simülasyon ölçümü | Sonuç |
|---|---|---|
| `c43-high-instrumented` | Executor ve gözlemci 4,795 sn'deki yaklaşık sıfır hızı gördü. Karar 4,815 sn'de verildi. `cmd_vel` üzerinde 4,850 sn'de 0,086842 m/sn görüldü. | Eski tek örnekli gözlem geçti. Sonraki hareket penceresini denetlemiyordu. |
| `c43-high-rebound` | İptal terminali 4,370 sn, eşleşen `robot_1/odom` örneği 4,410 sn ve karar 4,420 sn. Gözlemci FM terminal işlemesinde aynı örneği gördü. 4,425 sn'de `cmd_vel` 0,086842 m/sn oldu. Odometri 4,445 sn'de 0,0261, 4,480 ve 4,515 sn'de 0,086842 m/sn gösterdi. | HIGH komutu gönderilmeden önce gerçek yeniden hareket doğrulandı. Backend 1 ile döndü. |
| `c43-high-fixed` | İptal terminali 4,350 sn. 4,410 sn'deki ilk sıfır hızdan sonra odometri yeniden 0,0347 m/sn'ye çıktı. Geçerli pencere 4,515–4,725 sn. Karar 4,750 sn ve FM alımı 4,755 sn. | Yedi sıralı duruş örneği, son örneğin birebir eşleşmesi ve HIGH gönderilmeden sonraki altı duruş örneği doğrulandı. Ardından HIGH epoch 2 ile tamamlandı. |

Bu yeniden üretimde ölçüm farkı DDS gecikmesiyle açıklanmadı. Eski kodun seçtiği örnek gözlemciyle birebir eşleşti ve sonraki damgalar hareketi gösterdi. Özgün 0,0434 m/sn koşusunun Executor örneği hâlâ bilinmiyor. Düzeltilen koşuda aynı 4,725 sn örneği bağımsız aboneliğe Executor'dan yaklaşık 0,15 ms sonra ulaştı. Executor kararı ile FM terminal işleme başlangıcı arasındaki monotonik fark yaklaşık 3,4 ms idi.

Düzeltme, ilgili goal handle'ının `STATUS_CANCELED` terminalinden daha yeni odometriyi kabul eder. Odometri callback'i ayrı, seri bir callback grubunda çalışır ve eski veya yinelenen damgalar en yeni örneği değiştiremez. İzin verilen robot odometri çerçevesi, mevcut tazelik ve 0,01 m/sn ile 0,01 rad/sn sınırları korunur. Hareket, geçersiz örnek veya 0,10 simülasyon saniyesini aşan örnek aralığı pencereyi keser. En az 0,20 simülasyon saniyesi boyunca sıralı duruş gerekir. Bu süre, kullanılan 10 Hz Nav2 denetleyicisi ve smoother'ın iki çevrimini kapsamak üzere seçildi. Fiziksel kanıt yoksa taşıma sahipliği korunur. Park iptali aynı pencereyi kullanır.

Executor `PREEMPTION_STOP_PROOF` kaydında taşıma ve Nav2 goal UUID'lerini, epoch'u, simülasyon terminal, örnek ve karar zamanlarını, callback alım zamanını, odometri çerçevesini ve hızları yayınlar. Test aynı kaynak damgasını bağımsız ROS aboneliğinde eşleştirir. FM'nin terminal işlemesinden önce HIGH Outbox kaydı oluşmadığını ve HIGH gönderilmeden önceki ek 0,20 sn boyunca hareket oluşmadığını denetler. Eylem IDL'si ve Fleet Manager'ın terminal sahiplik sözleşmesi korunur.

Özgün log `/tmp/fleet-c43/c43-high.log` altında kalır. Yeni tanı, başarısız yeniden üretim ve düzeltme kayıtları ile bunların SQLite kopyaları `/tmp/fleet-c43-recovery/` altında saklandı.

## Son kabul ve regresyonlar

| Seçki | Geçti | Kaldı | Atlandı |
|---|---:|---:|---:|
| Tam host Python ve Executor | 386 | 0 | 28 |
| Tam Humble ve CycloneDDS | 434 | 0 | 0 |
| Humble C2.3 ve C3.3.3 config | 6 | 0 | 0 |
| C3.3.3 T01–T10 | 10 | 0 | 0 |
| C3.3.3 T01 ve AUTO-ROUTES | 2 | 0 | 0 |
| T01 ve gerçek HIGH teslimatı | 2 | 0 | 0 |
| C2.3 canlı | 7 | 0 | 0 |
| C4.1 ve C4.2 canlı | 3 | 0 | 0 |
| C4.3 istasyon kabulü | 2 | 0 | 0 |

Son host ve Humble seçkileri güvenli bekleme, eski ve sırası bozuk odometri, harekete devam, gecikme ve odometri yokluğu testlerini içerir. İlk tam host ve Humble denemelerinde ROS paketindeki bir test tek duruş örneğiyle terminal bekledi. Bu koşular sırasıyla 385/1 ve 433/1 idi. Test, sıralı duruşu doğrulayacak şekilde güncellendi.

`c43-recovery-station` senaryoları geçti. Test batarya süreci SIGINT sırasında DDS mesaj dönüşümünde hata verdi ve simulation 1 ile kapandı. Test girişinde sinyal bir durdurma bayrağına çevrildi ve callback'in dönmesi beklendi. `c43-station-final` ve `c43-station-final-repeat` ayrı temiz dünyalarda aynı eşiklerle tekrar çalıştı. Gazebo merkez hataları ilk koşuda park için 0,230 m ve dock için 0,241 m, ikinci koşuda 0,220 m ve 0,279 m idi. Her koşuda üç benzersiz ve birer kez gönderilmiş Outbox kaydı vardı.

Son sekiz canlı projenin tümünde backend/simulation 0/0, `OOMKilled=false` ve `SIMULATION_SHUTDOWN clean=true` görüldü. Docker ve supervisor zorla sonlandırma kaydı ile Nav2 ilerleme hatası görülmedi. Son iki istasyon veritabanı ve HIGH koşusunun kopyasında `PRAGMA integrity_check` sonucu `ok` ve yabancı anahtar ihlali sıfırdı. Şarj enerjisi, fiziksel dock teması ve şarj kuyruğu C4.4 kabul kapsamındadır.
