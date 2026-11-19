# C5-B6B.3 — Yerel hareket kapısı ve actuator sınırı

## 19 Kasım C5-T3C-1A eki — ayrı native işçi ve son sıfır veto

[Uygulama, testler ve sınırlar](../validation/c5/c5-t3c1a-native-worker-2026-11-19.md).
Mevcut B6B.7 doğrulayıcısı ayrı süreçte, aynı DiffDrive'ın açık deney build'inde
tek joint yazıcısı nonblocking yerel kayıtla bağlıdır. İşçi kaybında fizik
ilerlerken sıfır seçim ve kalıcı kapalı kilit doğrulandı. ACK native doğrulama
olarak kalır; APPLIED veya fiziksel duruş değildir. Sağlık veto'sunun tamamı,
kalifiye frenleme ve release açık; varsayılan launcher değişmedi.

## 18 Kasım C5-T3B eki — gerçek gözlem ve koşullu duruş hesabı

**IMPLEMENTED / yalnız deneysel altyapı.** Aşağıdaki tarihsel fake interlock
ürün hareket yetkisine dönüşmez. `RobotHealthProbe`, yalnız T3A'nın izole
koşucusunda açık hook ile kurulur. Varsayılan FM/Executor/GUI/launcher kurmaz.
Probe kalıcı ExecuteTask/permit/child kararlarını salt okunur okur;
Scheduler, Outbox, RobotStatus ve sahiplik otoritesini değiştirmez.

`domain/robot_health.py`, ölçüm damgasını ve yerel monotonik alım yaşını
ayrı denetler. Profilin mevcut odometry/observation/transport/watchdog/clock
bütçeleri ve 2 s STALE sabiti kullanılır; FM eşikleri değişmez.
`observations_current` yalnız tanısal zaman/biçim/bağlam tutarlılığıdır;
**movement_eligible=false** her sonuçta sabittir. Eksik, gelecek, eski,
geçersiz veya çelişkili veri tanıyı da düşürür. Bir kaynağın hatası diğer
kaynakların raporlanmasını engellemez.

| Kaynak | Gerçek gözlem / türetme | Açık sınır |
|---|---|---|
| Odometry | Header/frame/child, poz/quaternion, bildirilen twist/covariance; hız normu türetilir | Teker kinematiği bildirimi bağımsız kalibre gövde hız sınırı değildir |
| TF | Namespace buffer'ında tam odometry damgasında map→base lookup; edge/frame kaydı | Son TF veya initial-pose fallback kullanılmaz; map pozu lokalizasyon tahminidir |
| AMCL | Gerçek poz/covariance; simetri/PSD/sonlu değer ve yaş; sigma türetilir | Sigma kesin hata sınırı değildir; PSD başarısızlığı clamp edilmez |
| RobotStatus | Gerçek session UUID, artan status_seq, epoch/task/faz/state ve damgalar | Yeni sıra aynı yayın zamanını taşıyabilir; fiziksel ölçüm zamanı yenilenmiş sayılmaz |
| Lifecycle | Gerçek GetState RPC, ACTIVE=3, yerel request/response süresi | RPC receipt ölçüm damgası, endpoint adı süreç kimliği değildir |
| Native health | Gerçek UpdateVelocity/joint component readback'i, ayrı HMAC domain ve update sırası | İmzalı eski ACTIVE kaydı anlık sağlık veya fiziksel duruş değildir |
| FM bağlamı | Kalıcı ürün ataması, kaynak Outbox byte'ları, body/context hash'i, generation ve claim | Probe permit/ACK/claim yazmaz; restart otomatik replay değildir |

Kurulu Humble `_take_subscription`, callback'e mesaj bilgisinin yalnız mesaj
parçasını verir. Graph endpoint/GID kümesi **GRAPH_SNAPSHOT_ONLY** kanıtıdır;
mesajın gerçek yayıncı kimliği uydurulmaz. ROS ölçümlerinin task/epoch bağı
receipt association seviyesindedir; kriptografik kaynak oturumu değildir.
Kaynak kümesi/session, geri sarılan saat ve değişen context fence edilir.
Kapanmış permit olumlu claim görüntüsüyle canlanamaz. Duplicate ölçüm alım
yaşını yenilemez; status sırası ölçüm damgasından ayrıdır.

T3A komut/ACK wire'ı değişmez. `AuthorizedZero::AttachHealth`, yalnız live
native fixture'da, actual joint component'ler okunduktan sonra mevcut
`native_actuator` mesajına `native_health={body,mac}` ekler.
`C5_NATIVE_ZERO_HEALTH_V1` domain'i hedefleri, joint command'ları, sim
damgasını, update sırasını ve imzalı native_status'u bağlar. Yanlış MAC/domain,
replay ve unsigned dış readback ile çelişki reddedilir. Bu izin protokolü
değildir. ACK tarihsel doğrulama, Outbox PENDING, fiziksel stop UNKNOWN ve
release false kalır. Nonzero ve ağdan rearm yoktur.

Sağlık readback'i yalnız T3B'nin açık `health_period_sec` provision alanıyla
yayımlanır; değer mevcut profilin `timer_period_sec` değeridir. Eski T3A
provision'ı sağlık yayını açmaz. Normal native status/komut akışı aynı kalır;
sağlık paketleri arasındaki legacy status, sağlık yaşını yenilemez. Lifecycle
RPC polling'i mevcut watchdog/transport bütçelerinin küçüğüyle sınırlıdır.
Bu gözlem yükü sınırlamasıdır; lease, bilet, ACK veya STALE süresi uzatılmaz.

Native readback aboneleri history=1 kullanır. Eski biletlerin kuyruğunu
tüketmek güncel alıcı verisi sağlamaz; daha yeni report sırası kayıplı
örneklenebilir, ancak imza/session/sıra ve receiver bilet süresi kontrolü
atlanmaz. İzin/komut retry kanalı aynı kalır. İzole hata enjeksiyonunda tek
mevcut C++ bridge'in gerçek odometri çıkışı pasif ROS bağlantısıyla iletilir;
ölçüm yeniden damgalanmaz, gerçek robot durumu üretilmez.

`domain/stop_envelope.py` aynı B6B `sweep` / `covered` geometrisini kullanır.
Ölçülmüş alt frenleme, üst reaksiyon ivmesi, dört gecikme bileşeni, hız/konum
hata sınırları ve marj eksikse **UNBOUNDED / tube=None** döner. Sıfır gözlenen
hız eksikleri kapatmaz. Nav2 decel ayarları fiziksel kapasite yerine geçmez.
Tüm girdiler açık verilse bile **CONDITIONAL_CANDIDATE / qualified=false**
kalır; hash kendi başına ölçümü kalifiye etmez.

Koşullu model: `T=t_detect+t_compute+t_comm+t_actuator`,
`v=|v_obs|+e_v`, `v1=v+a_max*T`,
`d=v*T+a_max*T²/2+v1²/(2*b_min)`. Açısal hesap aynı yapıdadır.
Konum hata payı + açık marj + fiziksel çevreleyen footprint yarıçapı + `d`,
bütün yönlerde daire/AABB oluşturur. Daire her yaw'ı içerir; dönüş mesafesi
iki kez eklenmez. Bounds tüm duruş boyunca geçerli değilse fiziksel garanti
vermez. Eksik, negatif, sıfır frenleme veya taşan aritmetik sonlu tüp üretmez.

Rezervasyon değerlendirmesi mevcut dikdörtgen birleşim kapsamasını kullanır;
boşluklar atlanmaz. Göreli değerlendirme iki robotun bağımsız duruş alanını
toplar; peer'in yol vereceği varsayılmaz. Sınırsız peer ile sonuç UNKNOWN'dır.
Hesap acquire/release yapmaz; UNBOUNDED, rezervasyon yeterliliği kanıtı değildir.

Mevcut `ObservedObstacleLayer` / `ObservationHealth`, LiDAR buffer'larının
gerçek costmap update kullanımını ayrıca anlatır; bu probe onun yerine yeni
otorite kurmaz. Bütün sensör/producer zincirinin hareket kalifikasyonu açık
kalır. Costmap current=false duruş değildir. PeerRobotLayer/LiDAR değişmedi.

Native watchdog FM/Executor/bridge'den ayrı süreçte gözlenir; kendi update
döngüsü durunca bağımsız fren garantisi veremez. T3B SIGSTOP'u bütün native
Gazebo sürecini/fiziği dondurur; dış stale tespiti ve resume timeout'u hareketli
fren kabulü değildir. Sağlık çıktısını nonzero izin zincirine bağlayan kalifiye
producer, OS/anahtar izolasyonu ve bağımsız fail-safe hâlâ açık bağımlılıktır.

[T3B doğrulama](../validation/c5/c5-t3b-health-stop-2026-11-18.md) ·
[T3C önkoşul/test planı](../validation/c5/c5-t3c-braking-plan-2026-11-18.md) ·
[Mermaid](../diagrams/src/traffic-health-stop.mmd) · [SVG](../diagrams/svg/traffic-health-stop.svg).

## Korunan B6B.3 tarihsel kapsam

15 Kasım 2026 · `main`. **IMPLEMENTED / DOĞRULANDI:** yalnız saf Python, fake üretici/actuator, immutable yerel uygulama ve hedefli protokol/SQLite testleri. **PARTIAL:** gerçek topoloji kaynaklardan çıkarıldı; canlı topic graph ölçülmedi. **PLANNED / UNVERIFIED:** ROS hız interlock'u, kalifiye sensör/duruş tüpü, bağımsız actuator fail-safe ve fiziksel duruş. Bu kayıt ürün hareket kabulü değildir.

Dayanak: [B6A.1](../validation/c5/c5-b6a-1-warehouse-traffic-architecture-2026-11-15.md), [B6B.0](../validation/c5/c5-b6b0-followpath-spike-2026-11-15.md), [B6B.1](../validation/c5/c5-b6b1-traffic-core-2026-11-15.md), [B6B.2](c5-b6b2-traffic-permit-protocol.md), [B5G](../validation/c5/c5-b5g-headless-watchdog-2026-11-15.md), [B5H](c5-b5h-motion-envelope-review-2026-11-15.md). [Test kaydı](../validation/c5/c5-b6b3-motion-gate-2026-11-15.md) · [Mermaid](../diagrams/src/traffic-motion-gate.mmd) · [SVG](../diagrams/svg/traffic-motion-gate.svg).

## Gerçek hareket topolojisi ve bypass

Kurulu `ros2-fleet-c5-validation:humble-fortress` image'ındaki Humble Nav2 1.1.20 `navigation_launch.py` bu görevde ağ kapalı container'dan okundu. [Tam kaynak, paket sürümü ve SHA-256](../validation/c5/c5-b6b3-motion-gate-2026-11-15/installed-navigation.txt); [depo satır envanteri](../validation/c5/c5-b6b3-motion-gate-2026-11-15/source-topology.txt). Bu, başlatılmış sistemin canlı publisher envanteri değildir.

| Kaynak | Actuator'a mevcut yol | Güvenlik sınırı |
|---|---|---|
| Nav2 controller / DWB | `cmd_vel_nav → velocity_smoother → cmd_vel` | Controller önündeki gate, smoother'ın önceki komutunu kesmez. |
| Velocity smoother | `cmd_vel_smoothed` çıkışı `cmd_vel` olarak remap edilir | Template: 10 Hz, OPEN_LOOP, timeout 1 s; bağımsız actuator watchdog değildir. |
| Behavior server | `cmd_vel → bridge` (controller'a özel `cmd_vel_nav` remap'i burada yok) | Spin, BackUp, DriveOnHeading, AssistedTeleop nonzero üretebilir; smoother/controller kapısını atlayabilir. Wait hareket üretmez. |
| Executor doğrudan publisher | `node.py` içindeki `_cmd_vel_pub → cmd_vel` | İncelenen bütün publish noktaları sıfır Twist; mevcut nonzero üretici olarak raporlanmaz. Çok yayıncılı son topic sıfıra öncelik sağlamaz. |
| Pickup/dropoff, park/şarj | İki Executor NavigateToPose yolu → Nav2 controller ve BT recovery → yukarıdaki yollar | Ayrı docking hız sürücüsü bulunmadı; park/şarjın ayrı action yordamı aynı hız hattına ulaşır. |
| Teleop / başka üretici | `cmd_vel_nav`, doğrudan ROS `cmd_vel` veya Ignition `cmd_vel` | Ürün launcher'ında ayrı teleop düğümü bulunmadı; AssistedTeleop mevcut. C4.1 battery_check, stage12_probe gibi test araçları doğrudan nonzero yayınlayabilir; ürün bileşeni değildir. Harici yayıncı yokluğu kanıtlanmadı. |
| Son bridge / sürücü | `/{namespace}/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist → aynı Ignition topic → stock DiffDrive → teker joint'leri` | Warehouse generator, C3.3.3 `prepare_world` kullanır. Bridge ROS→Gazebo tek yönlüdür. DiffDrive doğrudan Ignition yayınıyla da sürülebilir. |

**Tek mevcut son ortak hız topic'i `/{namespace}/cmd_vel`'dir; bu topic'te tek yetkili yayıncı veya trafik gate'i yoktur.** Behavior ve doğrudan nonzero ROS/IGN yayınları, yalnız action/controller kapısına göre açık bypass'tır. Mevcut C5-A değiştirilmediği için bu riskler kapanmadı.

Gelecekteki topoloji **ÖNERİ / PLANNED:** bütün producer'lar ayrı upstream girişlere; smoother sonrası son yerel gate; yalnız gate'in yazabildiği ayrı actuator topic'i; yalnız onu taşıyan bridge ve bağımsız watchdog'lu tek DiffDrive. Sıfır talebi son gate'te üstün olmalı. Producer adı kontrolü veya graph taraması yetkilendirme değildir; aşağıdan doğrudan yazma erişimi, kuyrukta eski komut ve SROS/transport izolasyonu ayrıca ele alınmalıdır. Bu görev remap/launch/bridge değişikliği yapmaz.

## Yerel bileşen

[`motion_gate.py`](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/motion_gate.py) içindeki `TrafficMotionGate`, B6B.2 `MovementGate` protokolünü aynı RLock altında genişletir. Node tarafından import edilmez, ROS publisher/parametre/CLI veya hareket açma anahtarı içermez. Çıktı altı eksenli **daima sıfırdır**; bütün fixture koşulları sağlansa bile `PHYSICAL_FAIL_SAFE_UNQUALIFIED` ve `NONZERO_DISABLED` kalır. C5-A varsayılanı ve `motion_envelope: null` korunur.

`prepare/receive`: yerel monotonik deadline, COMMIT edilmiş RESERVED metadata, tam robot/task-or-move/epoch/üst UUID/child UUID/Executor–FM session/path digest/map/frame/geometri revision/permit generation bağı korunur. `movement_authorized=false` rezervasyon metadata'sıdır; yetki sayılmaz. `apply_local`: geometriyi digest ile yeniden eşler, geometri ve hareket bağlamını atomik kopyalar, bu gate oturumuna bağlı yerel APPLIED ACK oluşturur. Duplicate aynı bağlamı korur; dışarıdan ACK yerel uygulamanın yerine geçmez. Bu ACK yalnız offline veri uygulamasıdır; FM'ye yayınlanmaz ve B6B.2'nin fiziksel kalifiye olmayan ACK durumunu yükseltmez.

`filter_velocity`: üretici, hareket türü, tam context, live permit, yerel binding/ACK ve sentetik pose/TF/ObservationHealth/velocity/clock yaşlarını denetler. Kaynak ve alım yaşı birlikte, TF ölçüm anında ve gerekli bütün ölçümlerin kullanılmış olması ayrıca gerekir. Eksik, gelecek damgalı veya STALE veri ret üretir. Fixture zamanları tek yerel monotonik alana aittir; gerçek ROS kaynak stamp'lerini farklı makine monotonic saatinden çıkarma yöntemi değildir. Gerçek `ObservationHealth` session/sequence, sensör listesi ve measurement stamp doğrulayıcısı henüz yoktur; çağıranın bool assertion'ı fiziksel kanıt değildir.

Revoke, timeout, context/path/generation değişimi veya bypass eski request'i tombstone yapar. Session değişimi yeniden prepare'ı da kilitler; yeni instance kapalı başlar. Geç ACK/yanıt eski binding'i geri getiremez. Gate yalnız sıfır/duruş talebi ve nedenler üretir; Nav2 terminali, robot state/FAILED, fiziksel duruş veya SQLite release üretmez. SQLite/occupancy yazma yetkisi ve store referansı yoktur. ROS kopması duruş veya release değildir.

## Süpürme alanı ve rota sınırı

B6B.1/B6B.2 ile aynı kanonik AABB geometri digest'i kullanılır. İzin alanı segment sweep AABB'lerinin birleşimidir; bütün genişletilmiş footprint ve reachable-stop tube birleşimin içinde olmalıdır. Birleşim kapsaması sınır ızgarasıyla hesaplanır: yalnız köşeleri veya waypoint'leri kontrol etmek aradaki boşluğu kaçırmaz. AABB'ler konservatif geometri modelidir, kalifiye fiziksel envelope değildir.

Taze sentetik footprint dışarıdaysa `ZONE_VIOLATION`; footprint içeride fakat tahmini duruş tüpü dışarıdaysa `PREDICTED_BOUNDARY_BREACH` döner. İkisi farklı nedenlerdir; gerekirse ikisi birlikte bulunabilir. STALE fiziksel veri gerçek ihlal diye sunulmaz: `BOUNDARY_OBSERVATION_UNKNOWN` ve ret üretilir. İhlal/prediction yerel permit'i kapatır; alarm şu dilimde çıktı reason'ıdır, FM/Outbox alarm entegrasyonu yoktur. Sahiplik korunur.

Duruş tüpünü komut, gecikme, açısal sweep, footprint/yük ve poz belirsizliğinden üreten doğrulanmış model yoktur; test açıkça fake tüp sağlar. Path/generation uyuşmazlığında mevcut bağ kapanır; kesintisiz replan veya gerçek FollowPath yoktur. **Sınırdan önce fiziksel duruş garantisi verilmez.**

## Actuator fail-safe ve bloklayan kabul koşulları

Gate canlıyken sıfır hedef üretmesi, sıfırın actuator'a teslimi, actuator hedefinin sıfır olması ve fiziksel gövdenin durması ayrı aşamalardır. `GateOutput.physical_stop=UNKNOWN`, `ownership_release=false` bu ayrımı korur. Gate ölürse sıfır üretilemez; bridge ölürse üretilebilen sıfır ulaşamaz. Stock DiffDrive son hız hedefini tutabilir; smoother timeout'u veya action cancel bunu bağımsız olarak güvenceye almaz. Fake actuator'a önceden nonzero verilip gate çıktısı teslim edilmediğinde hedefin kaldığı test edildi; gate hiçbir nonzero üretmedi.

B5G'nin deneysel 250 ms steady-clock watchdog'u yalnız +0,015 m/s, boş tek robot dünyasında yayın kesmesini sınadı. Kesme→fiziksel duruş 380–455 ms sim örnekleme aralığı ve 4,338–4,413 mm örneklenmiş yol, ürün hızları/geri/dönüş için sınır değildir. `timed_out` bayrağının yeni receipt'te temizlenmemesi ve bridge/Guard hareketli fault enjeksiyonları B5H'deki açık eksiklerdir. Watchdog ürüne taşınmadı. Observer pause da ürün bağımsız fren mekanizması değildir.

Ürün nonzero kabulü için **BLOKLAYICI / UNVERIFIED**: gate/bridge/FM kaybında çalışan bağımsız actuator timeout/freni; tüm ROS/IGN bypass'larının kapanması; eski queued Twist/yeniden receipt semantiği; kaynak damgalı gerçek sağlık/context binding'i; lineer/açısal hızlarda kalifiye duruş tüpü ve fiziksel stop gözlemi. Bunlar tamamlanmadan ürün gate'i açılmaz. Yerel modelin testleri bu kabulü karşılamaz.

## B6B.4 için en küçük adım

**ÖNERİ:** Gerçek nonzero yine kapalı kalırken ayrı test-only overlay'de tek final actuator topic'ini ve gate'in tek publisher oluşunu fake ROS producer/actuator ile kanıtlamak; behavior/teleop/Executor/doğrudan downstream girişlerini ve gate/bridge kaybını sınamak. Kimliksiz Twist'in context'e güvenilir bağını ve gerçek kaynak-stamp doğrulayıcı sözleşmesini somutlaştırmak gerekir. Bağımsız actuator watchdog'unun yeniden üretilebilir build/arayüz kalifikasyonu ayrı açık engeldir; B5 binary'sini otomatik ürünleştirmek veya hareketli Gazebo'ya geçmek bu adım değildir.
