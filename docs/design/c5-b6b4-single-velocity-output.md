# C5-B6B.4 — Tek son ROS hız çıkışı ve bypass izolasyonu

15 Kasım 2026 · `main` worktree. **IMPLEMENTED / DOĞRULANDI:** yalnız test-only gerçek ROS/DDS adapter, fake producer/actuator ve gerçek ROS→IGN transport köprüsü. **PARTIAL:** normal producer yollarının remap izolasyonu. **BLOCKER:** son ROS topic'ine veya downstream IGN topic'ine yetkisiz yazma teknik olarak açık. **UNVERIFIED:** fiziksel duruş ve gerçek sağlık kalifikasyonu. Bu kayıt ürün güvenlik kabulü değildir.

Dayanak: [B6A.1](../validation/c5/c5-b6a-1-warehouse-traffic-architecture-2026-11-15.md), [B6B.2](c5-b6b2-traffic-permit-protocol.md), [B6B.3](c5-b6b3-traffic-motion-gate.md), [B5G](../validation/c5/c5-b5g-headless-watchdog-2026-11-15.md), [B5H](c5-b5h-motion-envelope-review-2026-11-15.md). [Doğrulama](../validation/c5/c5-b6b4-topology-2026-11-15.md) · [Mermaid](../diagrams/src/traffic-single-output.mmd) · [SVG](../diagrams/svg/traffic-single-output.svg).

## Kaynaktan doğrulanan mevcut topoloji

Kurulu Humble Nav2 1.1.20 `navigation_launch.py` yeniden okundu; [paket sürümü, kaynak ve SHA-256](../validation/c5/c5-b6b4-topology-2026-11-15/installed-navigation.txt). Controller `cmd_vel → cmd_vel_nav`; smoother `cmd_vel → cmd_vel_nav`, `cmd_vel_smoothed → cmd_vel`; behavior server'ın controller'a özgü remap'i yoktur, doğrudan `cmd_vel` üretir. Composition kolu da aynı hız bağlantılarını içerir. Executor `cmd_vel_topic_name=cmd_vel` ile doğrudan publisher açar; incelenen publish noktaları sıfırdır. Sıfır yayıncısı diğer yayıncılara üstünlük sağlamaz.

`docker/simulation-warehouse-grid/serve.py` robot namespace'indeki `cmd_vel` için tek yönlü ROS→IGN mapping kurar; `docker/simulation-c3-3-3/check.py` tarafından üretilen stock DiffDrive aynı IGN topic'ini tüketir. Pickup/dropoff ve park/şarj NavigateToPose yolları Nav2/behavior hattına ulaşır. Ayrı ürün teleop publisher'ı bulunmaması harici yayıncıları engellemez. [Satır envanteri](../validation/c5/c5-b6b4-topology-2026-11-15/source-topology.txt). C5-A launcher, varsayılan topic bağlantıları ve mevcut Executor değiştirilmedi; [hash tabanı](../validation/c5/c5-b6b4-topology-2026-11-15/baseline.json) hedefli testte yeniden karşılaştırılır.

## Ayrı hareketsiz overlay

[`docker/experiments/c5-b6b4/`](../../docker/experiments/c5-b6b4/) yalnız `/b6b4_test/<run>` namespace'ini kabul eder. Ürün launch dosyası bu modülü import etmez. `topology.py` fake düğümlere uygulanan açık node-başı hız remap'lerini ve bridge argümanlarını üretir. Nav2/Executor binary'leri başlatılmaz; fake controller/smoother/behavior/Executor düğümleri gerçek Twist/DDS ile bu bağlantıları sınar. Bu, gerçek Nav2'nin çalışma testi değildir.

| Yol | Test-only bağlantı |
|---|---|
| Controller → smoother | `cmd_vel → upstream/controller`; fake smoother bu girişi tüketir. |
| Smoother → gate | `cmd_vel_smoothed → upstream/smoother`. |
| Behavior → gate | `cmd_vel → upstream/behavior`. |
| Executor doğrudan sıfır → gate | `cmd_vel → upstream/executor`. |
| Alternatif test publisher → gate | `upstream/alternative`; bağlamsız Twist reddi. |
| Gate → bridge | Yalnız `actuator_cmd_vel`; normal graph'ta tek publisher `traffic_motion_gate`. |
| Bridge → fake actuator | Gerçek `ros_gz_bridge` yalnız `actuator_cmd_vel` tüketir; ayrı test `ign_velocity` topic'ine taşır. İkinci salt-okuma IGN→ROS bridge'i `fake_actuator` gözlemini sağlar. |
| Eski hız topic'leri | Namespace `cmd_vel` ve kök `/cmd_vel` için bridge subscriber yoktur. |

Docker `--network none`, salt okunur depo mount'u, ayrı ROS domain'i ve IGN partition kullanılır. Gazebo server, dünya, robot, DiffDrive, fiziksel actuator veya iki robot çalıştırılmaz. Fake upstream ve bypass enjeksiyonlarındaki nonzero sayılar yalnız yönlendirme işaretidir; fiziksel komut/hız eşiği değildir. Bridge'in test IGN çıkışı hiçbir ürün hız topic'iyle bağlı değildir.

## Gerçek ROS adapter ve kapalı hareket

`gate_adapter.py` B6B.3 `TrafficMotionGate` modelini gerçek `rclpy` subscriber/publisher'a bağlar. Başlangıç, 50 ms test heartbeat'i, normal callback, ret, timeout, revoke ve yakalanan adapter hatasında **yalnız yeni `Twist()`** yayınlanır. Model yanlışlıkla nonzero döndürse dahi serializer bu değeri kullanmaz. Hareket açma parametresi/CLI/ROS servisi yoktur. Heartbeat steady-clock ile yürür; 50 ms ürün safety threshold'u veya fiziksel fren garantisi değildir. Süreç öldürülürse heartbeat de yoktur.

Bütün ham Twist'ler `UNBOUND_TWIST` olarak reddedilir: kaynak damgası, sıra, session, epoch, generation ve context yoktur; aynı hız değerlerinin tekrarı semantic duplicate kanıtı değildir. Topic veya node adı güvenilir producer kimliği sayılmaz. Mevcut Twist sözleşmesine kimlik uydurulmaz.

Ayrı test `upstream/envelope` String/JSON girişi `{gate_session, source, sequence, context, velocity}` taşır. Gate session restart'ta değişir; eski session ve aynı source için artmayan sıra reddedilir. Bu alanlar yalnız test fencing'idir, authentication veya ürün komut IDL'i değildir. Tam context modelin kimliğiyle karşılaştırılır; epoch/Executor session/FM session/generation uyuşmazlığı binding'i kapatır. Adapter ROS üzerinden permit, geometri, caller-asserted health veya APPLIED ACK kabul etmez; canlı permit kurulamaz. Testte bir B6B.3 fake binding'i yalnız aynı süreçte enjekte edilerek ROS context/revoke/timeout kontrolleri ayrıca sınanır. Eksik gerçek health daima UNKNOWN/ret kalır.

QoS: RELIABLE, VOLATILE, KEEP_LAST depth=1. Bu ayarlar kuyruk/erişim güvenliği kanıtı değildir. Restart öncesi yayınlanan raw Twist ve eski envelope, ayrıca restart sonrası yeniden teslim edilen eski session test edilir; bağlamsız Twist hiçbir durumda nonzero açamaz. Yeni geçerli session/sequence bile permit ve sağlık üretmez. Ürün için kimliksiz Twist'i görev context'ine güvenilir bağlayan yerel producer adapter'ı hâlâ **BLOCKER**'dır.

## Bypass ve kayıp envanteri

| Denetim | Sonuç ve sınır |
|---|---|
| Controller/smoother, behavior, Executor sıfır, alternatif upstream | **DOĞRULANDI:** gerçek ROS graph'ta upstream; gate çıkışı ve fake downstream sıfır. Kalıcı erişim yetkisi kısıtlaması değildir. |
| Eski namespace `cmd_vel` ve kök `/cmd_vel` | **DOĞRULANDI:** bu overlay'de bridge tüketmiyor; downstream etkisi yok. Varsayılan C5-A'daki eski bağlantı korunur. |
| Doğrudan `actuator_cmd_vel` | **BLOCKER:** ikinci yetkisiz ROS publisher fake actuator'a nonzero ulaştırdı; güvenlik etkin DDS/SROS izinleri veya eşdeğer yazma izolasyonu yok. Tek publisher yalnız normal çalışma anı graph iddiasıdır. |
| Doğrudan downstream IGN | **BLOCKER:** gate öldürülmüşken native `ign topic` yayını fake actuator'a ulaştı. ROS remap, DDS izinleri ve publisher sayısı bu ayrı transport yolunu kapatmaz. |
| Gate kaybı | **BLOCKER:** süreç SIGKILL sonrası yeni sıfır yok. DDS graph hayalet publisher kaydını discovery lease boyunca gösterebilir. Sayım canlılık/yetki kanıtı değildir; fiziksel stop UNKNOWN. |
| Bridge kaybı | **BLOCKER:** gate sıfır üretmeye devam etti, fake actuator'a ulaşmadı; ayrı fake IGN enjeksiyonuyla son alımı 0.4 yapılan latch bu hedefi tuttu. Fiziksel duruş ölçülmedi; bağımsız timeout/fren şart. |
| Eski/kuyrukta komut ve restart | **DOĞRULANDI:** test adapter yeniden deny-all; eski session/duplicate ret, raw replay unbound. Downstream stock DiffDrive'ın eski receipt/yeniden alım semantiği **UNVERIFIED / BLOCKER**. |

Remap veya publisher sayımı tek başına yetkilendirme değildir. Normal yolların yönlendirilmesi ile bütün ROS/IGN yazarlarının zorunlu olarak kapıdan geçmesi aynı iddia değildir; ikincisi bu overlay tarafından sağlanmamıştır. Sahiplik bırakma, fiziksel IDLE, FAILED veya hareket kabulü üretilmez.

## Gerçek kaynak damgası adapter sözleşmesi — PLANNED / UNVERIFIED

Bu bölüm yeni safety threshold'u koymaz; B6B.3'ün bool/sentetik kanıtını gerçek kaynaklara bağlayacak somut tasarımdır. Adapter her kaydı immutable `{topic, producer_identity, publisher_session, sequence_if_available, source_stamp_ros_ns, receipt_mono, clock_generation, frame, revision, payload_digest, validation_result}` olarak saklamalıdır. Kimliği doğrulanamayan producer veya eksik alan UNKNOWN kalır; IDL'de olmayan session/sequence alınmış gibi varsayılmaz. Tek yerel lock/snapshot context, permit generation ve ölçüm setini aynı anda fence etmelidir.

| Kaynak | Gerçek alan ve gerekli doğrulama |
|---|---|
| RobotStatus | Config robot/topic eşleşmesi; `publisher_session_id` sıfır olmayan UUID, `status_seq` oturumda artan; `header.stamp` kaynak zamanı. `current_epoch/current_task_id` mevcut kabul edilmiş action bağlamıyla eşleşmeli; gerçek parent/child UUID'ler yürütücü/action kaydından gelmeli, status'ta varmış gibi türetilmemeli. Session değişimi kapıyı kilitler; yeni mesaj otomatik reset değildir. RobotStatus fiziksel state otoritesi olarak kalır. |
| Pose | `RobotStatus.pose.header.stamp` ve bağımsız `physical_pose.header.stamp` ayrıdır; status yayın zamanı eski pose'u tazelemez. Nonzero/sonlu ölçüm, frame/revision, normalize yönelim ve kaynak/alım yaşları ayrı doğrulanır. Mevcut PoseStamped belirsizlik/covariance vermez; qualification için ölçülmüş hata sınırı ayrıca gerekir. Eksik fiziksel pose'a odomdan fiziksel kanıt uydurulmaz. |
| TF | Config'deki map→odom→base/sensör frame zinciri ölçümün kendi stamp'inde `tf2` ile çözülebilmeli; latest transform, gelecek transform veya extrapolation kabul edilmez. Statik TF için yayın yaşı yerine doğrulanmış sabit geometri/revision; dinamik TF için ölçüm anı kapsaması gerekir. TF session ID taşımadığından yeniden başlatma/lifecycle kimliği ayrı izlenmeli, belirsizlikte binding invalid olmalı. |
| Velocity | Stamped odometry/actuator feedback'in `header.stamp`, frame/child_frame ve sonlu lineer/açısal değerleri kontrol edilmeli; komut Twist'i ölçülmüş hız sayılmaz. Kaynak receipt ile ölçüm zamanı ayrıdır. Gerçek fiziksel duruş için bağımsız gövde poz farkı ve açısal gözlem gerekir; yalnız odom/zero komutu yeterli değildir. |
| ObservationHealth | `layer_session`, artan `sequence`, `processed_at`; `topics/measurement_stamps/used` eşit uzunlukta, config sensör kümesi tam ve yinelenmesiz olmalı. Layer session değişimi binding'i kapatmalı. Her gerekli `used=true` stamp, gerçekten alınan sensör örneği ve o stamp'teki TF ile eşleşmeli; yalnız `processed_at` veya bool health tazeliği yetmez. Gerçek plugin `observed_obstacle_layer.cpp`, buffer'ları update boyunca kilitler; birden çok observation/persistence örneğini desteklenen tek ölçüm kimliği olarak raporlamaz. Eksik/çoklu/used=false UNKNOWN. |
| Scan | Config'den çözümlenen tam topic/frame; `LaserScan.header.stamp`, `time_increment/scan_time`, açılar ve ranges/range sınırları semantik olarak doğrulanmalı. Sonsuz menzil sensör semantiğine göre ayrılmalı, otomatik bozuk sayılmamalı. Tam taramanın ölçüm aralığı ve gerekli ışınların TF kapsaması hesaba katılmalı; ObservationHealth stamp'i gerçek scan kaydıyla join edilmeli. LaserScan session/sequence içermez: restart/source kimliği ayrı güvenilir lifecycle/transport sözleşmesi ister. |
| `/clock` | Aynı ROS sim saat alanı ve ilerleyen clock generation izlenmeli; zero/geri sıçrama/reset, donma veya clock kaybında gate deny-all olmalı. Ağ/receipt deadline'ları yerel monotonic, fiziksel ölçüm yaşları ROS `/clock` alanındadır; uzak makinenin monotonic stamp'i çıkarılmaz. Pause halinde ROS yaşı sabit kalsa da yerel liveness sona erebilmelidir. |

Kaynak yaşı, alımda aynı ROS saatinden hesaplanıp clock generation ile bağlanır; sonraki alım/liveness süresi yerel monotonic ölçülür. Sim ROS süresi ile steady saniyeleri fiziksel süre gibi toplanmaz; real-time factor/pause ayrı izlenir. Mevcut FM 2 s status stale kuralı bu gate'in kalibre edilmiş güvenli duruş bütçesi değildir. Tüm gate freshness/TF toleransı, sensör kapsaması, hız/hata/duruş payları **TBD / qualification bekliyor**; ürün `motion_envelope: null` korunur. Sağlık snapshot'ı, kalifiye süpürme ve duruş tüpü olmadan hareket yetkisi vermez.

## B5G watchdog'u ürün bağlantısına almadan kabul kapısı

Aşağıdakiler bu görevde uygulanmadı; **BLOCKER / UNVERIFIED** olarak kalır:

1. Kaynak/sürüm/hash'leri, bağımlılıkları ve ABI'si sabitlenmiş yeniden üretilebilir native build; temiz build ve yüklenen binary eşleşmesi.
2. Timeout'un bağımsız steady-clock, receipt/generation, pause/resume, eski queued komut ve yeniden komut alma semantiği; `timed_out` reset ve açık yeniden yetkilendirme sözleşmesi. B5G receipt bayrağı kusuru ürün kabulüne taşınamaz.
3. Tek gerçek actuator velocity girişinin bütün ROS **ve** IGN yazarları için kontrolü; yetkisiz direkt yayın ve eski bridge/driver girişlerinin teknik olarak kapanması.
4. Gate, bridge ve ilgili process ölümü/donması altında bağımsız actuator timeout/fren; üretici sıfırı gönderemediğinde de çalışması.
5. Komut/receipt/state'ten bağımsız fiziksel gövde duruşu ve gözlemcinin kendi kayıp davranışı; sıfır hedef, timeout bayrağı veya ACK tek başına yeterli değil.
6. Gerçek ürün lineer/açısal hızları, geri/dönüş, yük/zemin, jitter ve ölçüm belirsizliğini kapsayan duruş zaman/yol/açı zarfı; B5G'nin tek +0.015 m/s ölçümünü ölçekleyerek doldurma yok.

**B6B.5 için tek önerilen sonraki adım:** B5G deneysel native watchdog kaynağını ürün bağlantısı yapmadan yeniden üretilebilir test-only build ve açık timeout/yeniden-receipt arayüz paketi haline getirmek; ilk kabulü fake girişli/sıfır-hızlı tutmak. Nonzero, hareketli Gazebo ve FollowPath ürün geçişi ayrı kabul gerektirir.
