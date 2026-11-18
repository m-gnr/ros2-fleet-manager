# C5-B6B.2 — FM ↔ Executor trafik izin protokolü

## 18 Kasım C5-T2 eki — gerçek ürün child kanıtı

**IMPLEMENTED, yalnız deneysel metadata; varsayılan kapalı.** Aşağıdaki
15 Kasım hazırlama modu korunur. T2, hazırlanan UUID'yi gerçek child saymaz:
ayrı `_traffic_child_test_profile=None` kurucu seam'i ile Executor, gerçek
ExecuteTask handle/request/ExecutorSafety oturumundan bir `ChildBinding`
oluşturur. Her NavigateToPose gönderimi için ayrı client UUID'si ve yalnız
o goal'a ait XML dosyası ayrılır; response gerçek NavigateToPose
ClientGoalHandle tipi, endpoint ve UUID ile tekrar denetlenir. XML token'ı
üst UUID'nin child gibi kullanılmasının yerine geçmez; üç UUID farklıdır.

Yeni `fleet_nav2_observer` BT eklentisi stock Humble FollowPathAction'ını
genişletir. Gönderim öncesindeki Path kopyasını ve kabul edilmiş kendi gerçek
FollowPath handle UUID'sini typed `TrafficChildObservation` ile yayınlar.
On-wait, gerçek terminal ve halt ayrıdır; base `halt()` callback'inin
`on_cancelled()` çağırması gerçek terminal kanıtı sayılmaz. Yeni Path veya
controller/goal-checker güncellemesi eski bağı geçersizleştirir. Eklenti
stock replanning politikasını ve action istemcisini yeniden kullanır.

Executor, o NavigateToPose kabulü teyit edilene kadar en fazla 16 gözlemi
bekletir; sonrasında yerel aktif assignment, epoch, kendi session'ı,
context/nav UUID, observer session, artan kesintisiz sıra ve ROS kaynak
yaşını denetler. Kaynak yaş sınırı mevcut Executor
`odometry_freshness_sec` değeridir; toplam test receipt deadline'ı açık
monotonik `timeout` ile ayrıdır. Mevcut FM 2 s STALE / 5 s uyarı eşikleri
değişmedi. İlk observer session o benzersiz XML context'inde sabitlenir;
değişen session, duplicate, eski sıra ve kapalı context yeniden kullanılmaz.

`RequestTrafficPermit` sonuna opsiyonel context/nav/observer UUID, sıra,
gözlem türü, terminal ve neden alanları eklenmiştir. Tümü sıfır olan eski
B6B.2 hazırlama isteği aynı davranışı korur; kısmi kanıt eski moda düşemez.
Yeni adapter `TRAFFIC_PROTOCOL_CHILD` olayını mevcut consumer'a yollar.
`traffic_child.py`, mevcut `process_protocol` rezervasyonunu, child
kanıtını ve aynı `traffic_outbox` kayıtlarını tek transaction'da tutar.
Yeni tablo, ikinci trafik çekirdeği veya ikinci fiziksel durum makinesi yoktur.
İptal önce gelirse kapanma kaydı ilk kabulden önce kalıcılaşabilir; gecikmiş
kabul bu kaydı aşamaz. Replan/iptal/terminal mevcut claim'i BLOCKED tutar.

Bu sürüm bir context'te yalnız ilk gerçek child'ı bağlar. Replan sonrası
yeni child, kalifiye release/rollover bulunmadan eski rezervasyonu devralmaz.
Yeni epoch için ayrı gözlem eski context'i diriltmez. Executor restart'ında
context yüklenmez; FM mevcut nonempty DB'yi otomatik devam için kabul etmez.
Eski terminal veya ACK sahipliği serbest bırakamaz.

Gözlem bir izin önkoşulu olarak actuator'a uygulanmış değildir: test modunda
gerçek child kabulünden **sonra** metadata rezervasyonu alınır. T2 yalnız
native sıfır sürücülü veya actuator bulunmayan izole fixture içindir.
Varsayılan launcher eklentiyi yüklemez ve bu seam'i açmaz. APPLIED/RETIRED ACK
üretilmez; MovementGate `send` kapalı, fiziksel stop UNKNOWN ve release
reddidir. DDS/SROS yayıncı kimlik doğrulaması, native canlı permit uygulaması,
sağlık/stop zarfı ve hold/resume T3–T5 bağımlılıklarıdır. Context token/Path
hash'i kriptografik yayıncı kimliği veya fiziksel kanıt değildir.

[T2 test ve canlı kanıt kaydı](../validation/c5/c5-t2-product-child-2026-11-18.md)
· [Mermaid](../diagrams/src/traffic-product-child.mmd)
· [SVG](../diagrams/svg/traffic-product-child.svg).

## Korunan B6B.2 hazırlama modu kaydı

15 Kasım 2026. **IMPLEMENTED / DOĞRULANDI:** hareket kapalı, hedefli fake action/service ve consumer/SQLite kapsamı. **PLANNED / UNVERIFIED:** gerçek local boundary interlock, actuator fail-safe, kalifiye applied/retire kanıtı ve fiziksel release. Bu uygulama yeni ürün hareket yetkisi veya mimarinin tamamına onay değildir.

Dayanak: [B6A.1](../validation/c5/c5-b6a-1-warehouse-traffic-architecture-2026-11-15.md), [B6B.0](../validation/c5/c5-b6b0-followpath-spike-2026-11-15.md), [B6B.1](../validation/c5/c5-b6b1-traffic-core-2026-11-15.md), [Outbox](c3-2-sqlite-outbox.md). [Doğrulama](../validation/c5/c5-b6b2-traffic-protocol-2026-11-15.md), [Mermaid kaynak](../diagrams/src/traffic-permit-protocol.mmd), [türetilmiş SVG](../diagrams/svg/traffic-permit-protocol.svg).

## Seçim ve konfigürasyon sınırı

İki seçenek değerlendirildi: mevcut demo davranışını değiştiren ürün parametresi veya açık in-process test seam'i. Kullanıcının C5-A'yı koruma ve nonzero açmama sınırı nedeniyle ikinci yol uygulandı. Varsayılan `RobotExecutorNode` trafik istemcisi kurmaz ve mevcut NavigateToPose akışını kullanır. Pickup/dropoff ve ayrı park/şarj yordamları aynı `prepare_and_authorize_movement` metoduna girer.

Test harness'i consumer başlamadan `enable_traffic_protocol_test(enclosing_radius=...)`, FM adaptöründe `traffic_protocol_test=True`, Executor kurucusunda `_traffic_protocol_test_profile={map_revision, geometry_revision, frame, radius, timeout}` verir. Bunlar ürün YAML/Apply/CLI/ROS parametresi değildir; profil hareket açma alanı kabul etmez. Test yarıçapı fiziksel kalibrasyon değildir; ürün `motion_envelope: null` korunur. Managed alanlar B6B.1'in açık `TRAFFIC_CONFIGURE` girdisiyle hazırlanır; ürün haritasından kalifiye trafik geometrisi türetildiği iddia edilmez.

Test modu planner sorgusu yapabilir; NavigateToPose veya FollowPath hareket goal'u göndermez. Executor, adaptör yanlışlıkla True döndürse bile belirsizlik hold'una girer. Bekleme, timeout veya ret için FAILED/ERROR, sahte action terminali ya da PREEMPTED üretilmez. Sahiplik senaryo resetine kadar tutulabilir. Bu yerel admission kapısı bağımsız teleop/cmd_vel producer'larını veya çalışan actuator'u denetleyen fiziksel interlock değildir; canlı hareket için kullanılmaz.

## ROS sözleşmesi ve gerçek kimlikler

| Uç / tip | İçerik ve sınır |
|---|---|
| `/{namespace}/request_traffic_permit` / `RequestTrafficPermit.srv` | Request UUID, gerçek task_id veya move_id, assignment_epoch, gerçek üst action UUID, önceden ayrılan child UUID, Executor session, hareket türü/istasyon, tam `nav_msgs/Path`, path/geometry digest, map/geometri revision. |
| `TrafficPermitIdentity.msg` | B6B.1 PermitIdentity'nin aynı alanları; UUID alanları ROS UUID, epoch/generation uint64. Station için `execute_uuid` alanı NavigateToStation UUID'sini taşır. |
| `/{namespace}/traffic_decision` / `TrafficPermitDecision.msg` ve servis yanıtı | Request, tam kimlik, geometry digest, tür/istasyon, RESERVED/DENIED/REVOKED, reason, committed, daima `movement_authorized=false`. |
| `/{namespace}/traffic_ack` / `TrafficPermitAck.msg` | Tam permit kimliği ve request/digest/tür/istasyon; APPLIED veya RETIRED, sıfır olmayan local_binding_id. Hiçbiri fiziksel uygulanma kanıtı veya hareket yetkisi değildir. |

Robot kimliği FM'de mevcut config namespace eşlemesinden seçilir. İstek robot alanı bu uçla eşleşmek zorundadır. Consumer güncel `_active_tasks_by_robot` veya `station_dispatch.active` kaydındaki gerçek task/move ID, epoch ve goal UUID'yi; kabul edilmiş RobotStatus'tan gelen `session_id`, tazelik, initial verification ve session_blocked durumunu doğrular. İstek bu kaynakları oluşturamaz veya değiştiremez. Executor üst UUID'yi `ServerGoalHandle.goal_id`, görev/hareket ID ve epoch'u kabul edilen action request'inden, oturumu `ExecutorSafety.session_id` üzerinden alır; yerel aktif UUID/epoch/safety tekrar kontrol edilir.

FM session consumer test aktivasyonunda üretilir. Permit UUID, FM session + request UUID üzerinden UUIDv5; generation aynı consumer transaction'ında kalıcı protokol kararlarından artan şekilde üretilir. Duplicate aynı kimlik/generation'ı korur. Bu sürümde child UUID sadece hazırlanır, hareket action'ı başlatılmadığından gerçek çalışan Nav2 child'ı olduğu iddia edilmez. B6B.1'in aktif bağlam rollover yasağı korunur; ikinci bacak/yeni atama otomatik olarak eski rezervasyonu aşamaz.

Path digest, ROS serialized Path'in bütün byte'ları üzerinde SHA-256'dır; frame, damga, koordinat ve yönelimleri kapsar. Revision alanları ayrıca fenced edilir. FM ROS adaptörü path'i ve digest'i doğrular; noktaları aynı Path'ten çıkarır. Consumer açık test yarıçapıyla B6B.1 sweep geometrisini yeniden hesaplar; gelen AABB'ler ve SHA-256 geometry digest ile eşleştirir. Geometry digest, anahtarları sıralı, `allow_nan=False` standart Python JSON listesi üzerinde hesaplanır. Değişmez kopya planner sonucundan ayrıdır. Bu hash'ler authentication/imza veya fiziksel güvenlik kanıtı değildir. DDS/SROS kimlik doğrulaması geliştirilmedi.

## COMMIT, Outbox, ACK ve yarışlar

ROS callback'i yalnız consumer kuyruğuna event sunar. Consumer, güvenilir mevcut sahiplik denetimi, B6B.1 bind/acquire, snapshot, karar ve `traffic_outbox` kaydını aynı SQLite transaction'ında yazar. `submit` ancak başarılı COMMIT'ten sonra döner; servis ve topic o sonucu yayınlar. Rollback'te karar, claim ve Outbox birlikte geri alınır. Hareket komutlarının `outbox_events` tablosu bu protokolce tüketilmez/değiştirilmez.

Karar yayını consumer üzerinden Outbox'a bağlı kayıtları tekrar okur; tazeliği/oturumu ve claim'in hâlâ RESERVED olduğunu kontrol eder. Blokajda REVOKED yayınlanır. `traffic_outbox` PENDING olarak kalır: teslim/alındı/applied birbirine eşitlenmez; yayınlar tekrar edebilir. Bir ROS servis yanıtı veya `committed=true` hareket yetkisi değildir. Poll başarısızlığı Executor'ın yerel monotonik deadline'ını uzatmaz. Caller timeout'u kabul edilmiş consumer event'ini geri çekmez; geç COMMIT edilen rezervasyon tutulur.

Yerel gate WAITING → RESERVED → APPLIED_UNQUALIFIED metadatasını tutar. İlk eşleşen COMMIT edilmiş rezervasyon stage edilir; ACK sadece kaydedilebilir. Gerçek applied producer/validator olmadığı için **APPLIED_UNQUALIFIED → SENDING geçişi yoktur**. `send` ve `revoke` aynı lock altında sıralanır; iki sıra da goal=0 verir. Gelecekte send-wins fiziksel iptal/duruş gerektirecektir; bu sürüm o geçişi açmaz. Revoke/retire/timeout request'i tombstone yapar; aynı request veya eski child cevabı tekrar açamaz. Yeni hazırlanmış child'a eski request cevabı uygulanmaz. Aynı request'e farklı permit/session/generation/digest gelirse gate kapanır; deadline hiçbir duplicate ile yenilenmez.

APPLIED ACK kimliği consumer'da doğrulanır, `UNQUALIFIED_LOCAL_ACK` olarak kalıcı kaydedilir ve hareket açmaz. RETIRED ACK yerel kanıtın kalifiye olmadığını koruyarak rezervasyonu BLOCKED yapar; FREE üretmez. Yanlış ACK reddedilir. Executor sahte local ACK üretip yayınlamaz. B6B.1'in bütün fiziksel release isteklerini reddeden davranışı değiştirilmedi; release validator eklenmedi. Timeout/session değişimi görev veya istasyon sahipliğini kapatmaz. Yeni DB/ilk mesaj fiziksel reset kanıtı değildir.

## B6B.3 için en küçük sonraki adım

18 Kasım ek uygulama: mevcut `MovementGate` artık kabul edilen gerçek
FollowPath child UUID'sini ve gönderilen Path'in tüm serialized byte hash'ini
rezervasyon kimliğiyle eşleyen **yetkisiz gözlem kaydı** tutabilir. Gerçek ROS
ClientGoalHandle/tip/endpoint adaptörü ve terminal kimlik fence'i vardır.
Bu kayıt APPLIED ACK, fiziksel duruş veya release değildir; `send` hâlâ daima
False döner. Varsayılan Executor akışı bu gözlem API'sini çağırmaz.
[Yeni doğrulama ve sınırlar](../validation/c5/traffic-integration-2026-11-18.md).

**ÖNERİ:** hareket kapalı kalarak, permit kimliği/path/child bağını gerçekten yerel sınır uygulayıcısına atomik kuran ve revoke/retire durumunu okuyan producer sözleşmesini doğrulamak. Fake ACK yerine bu producer'ın uygulanmış kimlik kanıtını göstermek gerekir. Fiziksel hareket açmak ayrıca actuator fail-safe, gerçek path yürütmesi ve kalifiye release için bağımsız kabul gerektirir.
