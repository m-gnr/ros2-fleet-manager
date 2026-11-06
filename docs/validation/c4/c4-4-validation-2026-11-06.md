# C4.4 — Fiziksel dock teması, şarj ve kuyruk

6 Kasım 2026. [Komut eki](c4-4-commands-2026-11-06.md) · [C4.3 kabulü](c4-3-validation-2026-11-06.md)

Başlangıç commit'i `82829821cb3184abb5aa7d107b875fc36cde6546`. Yerel ve uzak `main` bu commit'te eşleşti. C4.4, C4.3'ün istasyon action, tek consumer ve Outbox akışını kullanır.

## Fiziksel şarj sözleşmesi

- Fortress dünyasında yapılandırılmış dock merkezine 1 mm yükseltilmiş, pasif bir temas pedi eklenir. DART gerçek pad ve robot çarpışma çiftini üretir. Gazebo Contact sistemi çifti simülasyon damgasıyla yayınlar. GZ → ROS köprüsü `/dock/<istasyon>/contacts` üzerinde `ros_gz_interfaces/msg/Contacts` taşır. Robot ve istasyon kimliği, çarpışma varlık adlarından doğrulanır. Pad kare olduğu için çarpışma alanı tek başına dairesel şarj yarıçapı kanıtı sayılmaz.
- Robot başına Gazebo PosePublisher, damgalı dünya pozunu `/<namespace>/physical_pose` üzerinden sağlar. Battery Simulator yapılandırılmış yarıçapı bu pozla, 0,01 m/sn ve 0,01 rad/sn duruş sınırlarını ilgili robotun güncel odometrisiyle denetler. Poz, hız ve temas kanıtı 0,30 simülasyon saniyesi içinde olmalıdır. Fortress Contact sistemi yalnız pozitif teması yayınladığından, temasın tek başına kesilmesi son olumlu damganın geçerliliğini en çok 0,30 simülasyon saniyesinde sonlandırır. Hareket veya açık çelişkili temas daha erken kapatır.
- Fleet Manager, SQLite COMMIT sonrasındaki OCCUPIED istasyon sahibi için `/<namespace>/dock_lease` yayını yapar. `DockLease`, robot ve istasyon kimliği, Executor oturumu, epoch ve simülasyon damgası taşır. Battery Simulator aynı oturum ve epoch'u güncel, yüksüz ve görevsiz RobotStatus ile eşleştirir. Lease ve RobotStatus için pencere 0,50 simülasyon saniyesidir. Eski sıra, yanlış robot, oturum değişimi ve yanlış istasyon izin vermez. RELEASING, BLOCKED veya SESSION_BLOCKED bağlamında yeni geçerli lease üretilmez.
- Battery Simulator robot başına tek Wh otoritesidir. Tüketim devam eder. Geçerli fiziksel şarj adımında `P_charge × delta_t / 3600` Wh eklenir ve enerji kapasiteye kırpılır. İlk doğrulanan an önceki aralığa geriye dönük enerji eklemez. Sıfır veya geriye giden saat enerji artırmaz. Büyük saat sıçramasında aradaki şarj varsayılmaz. `BatteryState.charging_station_id` ve `RobotStatus.charging_station_id` şarjın istasyon kimliğini taşır.
- Şarj kuyruğu güncel düşük SoC ile sıralanır. Eşitlikte ilk kaydedilen talep öndedir. Uygun IDLE robot önce normal göreve bakılır. Dock sahibi dinamik Wh hesabı geçerse görev için erken ayrılabilir. Başka robota yer vermek için %80 altı çıkış başlatılmaz. %80 ve üzeri bir sahip, şarj bekleyen varsa uygun park veya güvenli bekleme hedefine yönlendirilebilir. Bekleyen yoksa %100'e kadar kalır.
- Ayrılma niyeti, hedef rezervasyonu ve Outbox komutu aynı transaction'da kaydedilir. Kaynak RELEASING kalır. Gerçek dock varışından sonra serbest bırakmak için daha yeni geçerli RobotStatus harita pozu ve damgalı Gazebo fiziksel pozu, istasyon merkezinden `tolerance_radius + departure_margin` ötesinde olmalıdır. Eski veya yok fiziksel örnek kaynağı devredemez.

## Başarısız koşular ve fiziksel mekanizma

- İlk yerel temas sondasında topic, Fortress'ın beklediği iç `contact/topic` alanı yerine sensör seviyesinde yazıldığı için varsayılan adla açıldı. Düzeltilen sondada `dock_1::pad::surface` ile `robot_1::left_wheel::wheel`, sağ teker ve caster çiftleri yerel Ignition ile ROS mesajında görüldü. Örnekler `/tmp/fleet-c44/native-contact.json` ve `/tmp/fleet-c44/ros-contact.log` altında saklandı. [Fortress Contact sistemi](https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/src/systems/contact/Contact.cc#L97) · [Humble Contacts dönüşümü](https://github.com/gazebosim/ros_gz/blob/humble/ros_gz_bridge/src/convert/ros_gz_interfaces.cpp#L279)
- `c44-first` koşusunda Nav2 varışı, dock lease'i ve temas vardı. Fortress sahne yayınının ROS TF dönüşümünde poz damgası sıfırdı. Şarj kapısı enerji artırmadı ve backend süre sonunda 1 çıktı.
- `c44-pose` koşusunda robot bazlı PosePublisher topic'i açıldı, ancak Fortress top-level model için `publish_model_pose` ve `publish_nested_model_pose` birlikte bekliyordu. Model pozu gelmediği için şarj başlamadı. İkinci başarısız koşu da backend 1, simulation 0 ile kapandı. Pozun güvenlik eşiği gevşetilmedi. [Fortress PosePublisher](https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/src/systems/pose_publisher/PosePublisher.cc#L358)
- `c44-pose2` koşusu damgalı robot pozu ve temasla iki robotun gerçek şarjını ve istasyon devrini doğruladı. `robot_1` 21,44 Wh ile şarja başladı, 81,95 Wh civarında fiziksel olarak dock'tan ayrıldı. Gazebo ayrılma mesafesi 0,402 m idi. `robot_2` 23,09 Wh ile başladı ve kapasiteye ulaştı. Bu koşuyu takiben, bağımsız fiziksel ayrılma örneği kaynak serbest bırakmanın da ürün önkoşulu yapıldı.

## Son doğrulama

**DOĞRULANDI.** `c44-final` ve `c44-final-repeat` ayrı temiz dünyalar ve ayrı SQLite dosyaları kullandı. Test bataryaları %22 ve %24 SoC ile başladı. Kopya YAML'da şarj gücü 21.600 W yapıldı. Ürün YAML'ındaki 20 W ve %100 başlangıcı korundu. Bu değişiklik yalnız canlı test süresini kısalttı. Konum, temas, hız, rezerv ve şarj politikası eşikleri korunarak çalıştırıldı.

| Koşu | İlk robotun temas Wh | İlk robotun devir anındaki Wh / fiziksel mesafe | İkinci robotun temas Wh / son Wh |
|---|---:|---:|---:|
| `c44-final` | 21,450 | 81,967 / 0,370 m | 23,095 / 100,000 |
| `c44-final-repeat` | 21,455 | 81,961 / 0,422 m | 23,078 / 100,000 |

İlk robot %80 altındayken park komutu oluşmadı. Her iki koşuda ikinci robot ancak ilk robot 0,35 m sınırını geçtikten sonra dock rezervasyonunu aldı. Bir park ve iki dock hareketinin her biri Outbox'ta bir kez gönderildi. İki veritabanında SQLite bütünlük sonucu `ok`, yabancı anahtar hatası sıfırdı.

| Test seçkisi | Geçti | Kaldı | Atlandı |
|---|---:|---:|---:|
| Odaklı C4.4 | 23 | 0 | 0 |
| Tam host Python ve Executor | 409 | 0 | 28 |
| Tam Humble ve CycloneDDS | 457 | 0 | 0 |
| Humble config | 6 | 0 | 0 |
| C4.4 canlı şarj ve devir | 2 | 0 | 0 |
| C4.3 canlı istasyon | 1 | 0 | 0 |
| C4.2 ve C4.1 canlı | 3 | 0 | 0 |
| C3.3.3 canlı T01–T10 | 10 | 0 | 0 |
| Canlı T01 ve HIGH preemption | 2 | 0 | 0 |

Son canlı projeler backend/simulation 0/0 ve `OOMKilled=false` ile kapandı. Zorla sonlandırma ve Nav2 ilerleme hatası görülmedi. İlk iki başarısız fiziksel poz denemesi başarı tablosuna dahil edilmedi. İlk tam seçkiden sonra eklenen eski epoch ve damga engeli son odaklı, tam host, tam Humble ve `c44-final-repeat` canlı koşusunda doğrulandı.

Şarj altyapısı, simülasyondaki pasif temas pedini ve robot pozunu kullanır. Bu, gerçek batarya ve şarj elektroniği kalibrasyonu kapsamına girmez. Erken görev çıkışı, eşit SoC/FIFO, duraklama ve lease kaybı kontrollü testlerle doğrulandı. İki temiz canlı kabul normal %80 devir ve bekleyen yokken %100 senaryosunu kapsar.
