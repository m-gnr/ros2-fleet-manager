# C5 — Robotlar arası konum ve rota farkındalığı

18 Kasım 2026. **PARTIAL.** Kullanıcının bu görevdeki açık isteği üç
robotun rota/footprint farkındalığını, dar koridor incelemesini ve izole canlı
testleri kapsar. Bu kayıt fiziksel güvenlik kalifikasyonu veya trafik hareket
yetkisi vermez. [Yeni koşu ve kabul durumu](../validation/c5/peer-awareness-2026-11-18.md).

## Mevcut akış ve eksik bağlantılar

FM → ExecuteTask → Executor → NavigateToPose → Nav2 korunur. İstasyon
rezervasyonu, robotun istasyona giderken geçtiği koridoru rezerve etmez.
[B6B.1](../validation/c5/c5-b6b1-traffic-core-2026-11-15.md) geometrik çakışma
çekirdeği ve [B6B.2](c5-b6b2-traffic-permit-protocol.md) protokolü vardır.
Hareket yetkileri kapalıdır; kalifiye fiziksel release yoktur. Bu sınırlar
değiştirilmez. Ayrı trafik zamanlayıcısı veya cmd_vel üreticisi eklenmez.

`warehouse_tf`, odometriyi ve namespace içindeki AMCL dönüşümlerini ortak
`/tf` üzerinde paylaşır. Nav2 kendi namespace TF konularını kullanır.
`/{namespace}/plan` yayınlarını mevcut `PlannerReader`/`PlanBuffer` kaynak
topolojisi, damga, TTL ve terminal durum kontrolleriyle izler. Bu Path gözlemi
çalışan Nav2 child UUID'sine bağlanmış izin değildir. FM'in ComputePathToPose
mesafe sorgusu da Executor'ın yürüttüğü güncel planın yerine konamaz.

18 Kasım temel koşusunun global costmap’i statik harita ve inflation içerir; yerel costmap
bağımsız LiDAR kaynaklarını `ObservedObstacleLayer` ile işler. Parkta duran
robot için global planner'ın kullanacağı ayrı footprint gözlemi yoktur.
18 Kasım performans kaydında ve yeni baseline koşusunda Alpha'nın park
dönüşünde Beta ile teması vardır. Çift istasyon sahipliği saptanmaması
fiziksel koridorun güvenli olduğunu göstermez.

## Dar kapsamlı aday

`fleet_perception::PeerRobotLayer`, mevcut Nav2 eklenti mekanizmasında ek
gözlem katmanıdır. `scripts/start_demo.sh`, mevcut `stage1_run.py`
`--peer-awareness-experiment` seçeneğini kullanır. Seçenek katmanı global ve
yerel costmap’te inflation öncesine ekler. `generate()` doğrudan çağrıldığında
seçenek varsayılan olarak kapalıdır.

LiDAR gibi sunulan sentetik scan/cloud yerine ayrı geometri katmanı seçildi:
bağımsız algılama kaynağı/telemetrisi korunur; ray clearing bir robotu silemez.
Poligon yerine mevcut robot başına Nav2 yarıçapıyla çevrel daire kullanılır.
Üretilen SDF çarpışma geometrilerinin ve sensör kasalarının bu dairede kaldığı
kontrol edilir. Daire dönüşleri kapsar ama lokalizasyon belirsizliği, duruş
mesafesi veya güvenlik marjı kalifikasyonu değildir. Robotlar config'den gelir.

Katman config'deki açık `namespace/tf` konularından yalnız beklenen
`map → robot/odom → robot/base_link` zincirini kabul eder. Her abonelik kendi
robotunun frame'lerine bağlıdır. Nav2'nin `/tf → tf` remap'i böylece eklenti
aboneliğini yayıncısız costmap namespace'ine taşımaz. Abonelikler costmap'in
özel callback grubundadır. İlerleyen kaynak damgası ve yerel monotonik alım zamanı
birlikte değerlendirilir; duplicate/ters sıra deadline yenilemez. Yanlış
parent, geçersiz quaternion ve sonlu olmayan değer geçmez. Poz kendi gerçek
odometri damgasında çözülür; eksik TF geçmişinde latest fallback yoktur.
Yerel costmap için ortak harita üzerinden kendi odometri frame'ine dönüşür.
TF kaybında son footprint tutulur, katman `current=false` olur. Saat geri
sarılması TF geçmişini geçersiz yapar; eski işgal fiziksel boşluk sayılmaz.

Her daireyle kesişen grid karesi lethal işaretlenir. Eski/yeni sınırlar
birlikte güncellenir; hareket sonrası eski iz temizlenir, başka katmanın
maliyeti silinmez. Kendi footprint'i peer engeli değildir. Costmap clear
servisi peer gözlemini silemez. `peer_observations` tanısı işlenen damgayı,
frame'i, yarıçapı ve geçerliliği gösterir; actuator duruş kanıtı değildir.

Yeni eşik yoktur: pose yaşı `odometry_freshness_sec`, alım aralığı
`transport_sec`, lokalizasyon kaynak yaşı `observation_age_sec`, AMCL ileri
damga toleransı mevcut `transform_tolerance` değerinden üretilir. Bunların
TF/çoklu robot hareketi için kalifiye olduğu iddia edilmez. RobotStatus'ın
2 sn STALE ve 5 sn uyarısı değişmez. IDL/şema/filo YAML alanı eklenmez.

## Rota ve trafik izinleriyle birleştirmenin sınırı

Salt okunur probe mevcut `RosReader`, `PlannerReader`, `PlanBuffer` ve gerçek
Gazebo physical_pose uçlarını yeniden kullanır; FM veritabanına yazmaz.
Rotaların erişilebilir olması ve geometrik kesişim, zaman bakımından çarpışma
kanıtı veya hareket izni değildir. Probe hiçbir hedef/hız göndermez.

Canlı koordinasyonun sonraki bağlantısı mevcut B6B.1/B6B.2 üzerinden olmalıdır:
gerçek child/path kimliği → atomik claim edinimi → kalifiye yerel
uygulama/duruş → fiziksel ayrılma kanıtıyla release. Yeni plan eski izni
kullanamaz; STALE/session/iletişim belirsizliğinde owner korunur. Timeout ile
sahiplik bırakma, otomatik geri sürüş ve ayrı öncelik politikası eklenmemiştir.

**Açık engel:** stok Nav2'nin güncel olmayan costmap beklemesi timeout sonrasında
terminal abort üretebilir. Mevcut Executor bunu gerçek Nav2 hatası olarak
işler. Trafik/iletişim beklemesini yeni FAILED/ERROR kaynağına dönüştürmeden
yerel hold/resume sözleşmesine bağlamak gerekir. Normal demoda katman etkin
olduğunda Nav2’nin bu bekleme davranışı sürer. B6B.2'nin hareket kapalı durumu ve
`motion_envelope: null` korunur. Dar koridor ilerleme/öncelik ve kilitlenmeden
kurtulma kabulü bu aday tarafından sağlanmış sayılmaz.

Katman bir kaynak/session kimlik doğrulayıcısı değildir. `current` yalnız
costmap güncellemesinde yeniden hesaplanır; update-loop donması için bağımsız
actuator watchdog'u yoktur. Duran robotta TF kaybı testi bu boşlukları kapatmaz.

18 Kasım sonraki entegrasyon aşamasında, ROS Buffer'ın dedicated-thread
bekleme kontrolü yerine `tf2::BufferCore` üzerinden doğrudan beklemesiz lookup
kullanıldı. Tam ölçüm damgası, kaynak/alım yaşı ve yanlış frame denetimleri
değişmedi; dedicated thread varmış gibi bayrak ayarlanmadı. On native peer
testi yeniden geçti; yeni hareketsiz üç robotlu koşuda önceki TF thread
uyarısı görülmedi. [Yeni kapsam](../validation/c5/traffic-integration-2026-11-18.md)
önceki taşıma/park sonuçlarının yeniden koşulduğu anlamına gelmez.

Native testler aynı C++ katmanını ve gerçek ROS callback'ini dünya/actuator
başlatmadan sınar. Canlı testte bağımsız contact/physical_pose kayıtları
esastır. Eklenti API dayanağı [Humble Layer](https://api.nav2.org/nav2-humble/html/classnav2__costmap__2d_1_1Layer.html)
ve [Nav2 kılavuzudur](https://docs.nav2.org/rolling/tutorials/plugin_tutorials/writing_new_costmap2d_plugin/writing_new_costmap2d_plugin/).
Kullanılan binary Humble'dır; Rolling kılavuzu sürüm kanıtı değildir.

[Mermaid kaynak](../diagrams/src/peer-awareness.mmd) · [SVG](../diagrams/svg/peer-awareness.svg).
