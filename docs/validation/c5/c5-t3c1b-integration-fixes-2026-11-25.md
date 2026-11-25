# C5-T3C-1B — Üç entegrasyon hatasının hedefli doğrulaması

25 Kasım 2026 · Taban `f69d1024b36a2cc5ac8ad93679f9f66c22f13397`.
**DOĞRULANDI: üç hedefli senaryo ayrı ayrı temiz tamamlandı.**
**Tam T3C-1B kabulü verilmedi.** Son kullanıcı talimatı gereği 14'lü matris,
commit/push ve T3C-2 hareketli deneyleri yapılmadı. Önceki çalışma ağacı ve
başarısızlık kanıtları korundu; varsayılan GUI/launcher değiştirilmedi.

[Önceki kısmi kayıt](c5-t3c1b-health-veto-2026-11-24.md) ·
[Komutlar](c5-t3c1b-integration-fixes-commands-2026-11-25.md) ·
[Ham kanıtlar](c5-t3c1b-integration-fixes-2026-11-25/).

## Kök nedenler ve kanıt sınırı

### Bridge: node'u hayatta tutan iki sahiplik döngüsü

Kurulu `ros_gz_bridge 0.244.26` içinde node → handle → node güçlü referans
döngüsü vardır. ROS→GZ subscription callback'i de node'u güçlü referansla
tutar. Node'un dış sahibi bırakıldıktan sonra middleware uçları kapanmaz.
Yeni yaşam süresi testi bunu fizik/robot kullanmadan doğrudan gösterir:

| Bağımlılık | ROS→GZ: dış sahip bırakılmadan önce ref / sonra expired | GZ→ROS | Test |
|---|---|---|---|
| Kurulu 0.244.26 | 3 / false | 2 / false | **FAIL** |
| Upstream 0.244.27 | 2 / false | 1 / true | **FAIL** |
| 0.244.27 + callback weak-owner düzeltmesi | 1 / true | 1 / true | **PASS** |

0.244.27'nin [Humble backport'u](https://github.com/gazebosim/ros_gz/pull/956)
handle'ın geri referansını zayıflatır. Yerel test, callback'teki ikinci döngünün
kaldığını ortaya çıkardı. `ros-gz-callback-owner.patch`, yalnız callback'in
sahibini weak pointer yapar; çağrı sırasında geçerli sahibi kilitler. Mesaj
dönüşümü, GID döngü filtresi, topic/IDL ve izin protokolü değişmez.

Yeni `replan-repro2` koşusunda bridge'in process exit aşamasındaki
`free(): corrupted unsorted chunks` / **SIGABRT -6** hatası core ile kaydedildi.
Bu, tarihsel **-11** ile aynı sinyal diye sunulmaz. GDB stack'i allocator/exit
aşamasını gösterir; heap'i ilk bozan yazımın adresi yakalanmadı. İki Valgrind
denemesi 0 error verdi; bu sonuç çökme kanıtını geçersiz kılmaz. Doğrulanan ve
kapatılan yazılım kusuru yukarıdaki deterministik sahiplik döngüleridir.
Tarihsel -11'in tek olası nedeni olduğu iddia edilmez.

### Nav2: callback çalışırken costmap belleğinin serbest bırakılması

Kurulu Humble `Costmap2DROS::on_cleanup`, executor thread'ini en son
sonlandırıyor. Böylece costmap/layer/publisher silinirken callback hâlâ bu
belleğe erişebiliyor. [Navigation2 #4323](https://github.com/ros-navigation/navigation2/issues/4323)
aynı yaşam süresi kusurunu ve executor'ın önce sonlandırılmasını açıklar.

`replan-readonly-cleanup1` yalnız **GetCostmap okuma** istekleri kullanarak
kusuru yeniden üretti; costmap temizlenmedi/değiştirilmedi. Beta/Gamma planner
**-11**, lifecycle timeout ve sonra launch tarafından **-9** kaydedildi.
Core'un crashing thread'i `Costmap2DPublisher::costmap_service_callback`
içinde, başka thread `Costmap2DROS::on_cleanup` / TF listener destructor'ında
beklerken çalışıyordu. Bu, süreç kapanış sırası varsayımından farklı, gerçek
eşzamanlı erişim kanıtıdır.

Düzeltme, kurulu sürümün yalnız `on_cleanup` sembolüne uygulanan deneysel
backport'tur: önce executor cancel/join, sonra publisher/service ve costmap
kaynaklarının bırakılması. `costmap_cleanup.cc` mevcut kurulu başlıklarla
derlenir; stock constructor/planner/controller döngüsü değiştirilmez.
`C5_1B_CLEANUP_FIX_LIBRARY` yalnız controller/planner süreçlerine bu sembolü
yükler. **Varsayılan launcher'a eklenmedi.** Süreç kapatma sırası değiştirilmedi.

| Salt okunur cleanup deneyi | Gönderim / tamamlanan future | Sonuç |
|---|---|---|
| Önce | 19.836 / 19.772 | İki planner -11, lifecycle timeout, zorunlu kapanış |
| Sonra, kurulu Nav2 + cleanup backport | 18.294 / 18.230 | **CLI 0**, alt süreçler temiz; altı callback-join kaydı |

64 bekleyen RPC, servislerin teardown sırasında kaybolmasıyla test sonunda
bırakılır; hepsinin başarıyla yanıtlandığı iddia edilmez. Bu yük testi robot
duruş veya frenleme kanıtı değildir. Kaynak/body/binary bağları ham kayıttadır.

### Health-session: gerçek başlangıç önkoşulu

Tarihsel koşuda Scheduler gerçekten Gamma'yı atamış, gerçek FollowPath
başlamış fakat FM'de child/permit/native-transfer kaydı oluşmamıştı. Native
alıcıların **NO_COMMAND** kalması doğru kapalı davranıştı. Bu ilk metadata
kaybının tam mekanizması eski kayıtlardan kesin olarak yeniden kurulamadı;
DDS discovery veya mesaj/clock sıralaması hipotezleri doğrulanmış sayılmaz.

Yeni `health-session-repro2` koşusunda başka somut başlangıç hatası yakalandı:
Nav2 BT, gerçek `ComputePathToPose` goal ACK'sini beklerken mevcut süresini
doldurdu; FollowPath'e ulaşmadan goal ABORT oldu. Ayrıca fixture, ilk READY
dosyasından **sonra** AMCL'yi yeniden initialize ediyor, ardından aynı tarihsel
READY kanıtıyla devam ediyordu. O dosya yeni ölçümlerin hazırlık kanıtı değildi.

`fixture_readiness.py` ve `prepare` düzeltmesi, gerçek initialization
damgasından sonraki AMCL ölçümünü, güncel odometry/ölçüm zamanında TF,
clock, gerçek ObservationHealth ve aktif lifecycle kanıtlarını bekler.
Başlangıçta henüz olmayan permit/native bağını **yetki olarak kullanmaz**;
FM hâlâ güncel RobotStatus/session kanıtını ayrıca ister. Sonraki gerçek
Scheduler ataması ve FM/native ACK zinciri değişmeden kullanılır. BT ACK
timeout'u, STALE ve diğer güvenlik eşikleri büyütülmedi; task retry, sahte
child/ACK veya BLOCKED kaydını açma eklenmedi. Aşırı gecikme hâlâ güvenli
başarısızlık üretebilir.

## Son üç temiz senaryo

Kaynak kopyası 499 runtime/test dosyasıdır; Git worktree değildir ve container'a
salt okunur bağlanır. Üç koşu boyunca kaynak/binary/adaptör aynı kaldı:

`14eb4e63a2eb0c69c986aaf0f0dca71894c23b5901da72d044bfd9012b543da8`

Her koşu yeni DB, robot/native session ve boot ile başladı. Gerçek Scheduler
ataması üçünde de Alpha oldu; harness robotu ACK kimliğinden okur. Her koşuda
üç robotun stack'i gözlendi; tek gerçek görev/permit vardır.

| Senaryo / domain | CLI / kapanış | Gerçek Physics: hata öncesi → sürerken | İlk veto | Claim |
|---|---|---|---|---|
| controller-inactive / 201 | **0 / temiz** | **1828 → 2214** | HEALTH_REJECTED | BLOCKED |
| replan / 202 | **0 / temiz** | **1591 → 1802** | HEALTH_REJECTED | BLOCKED |
| health-session / 203 | **0 / temiz** | **2004 → 2051** | HEALTH_REJECTED | BLOCKED |

Üçünde de altı gerçek controller/planner cleanup kaydı var. `/proc/maps`
kurulu stock Nav2 kütüphanesi ile yalnız cleanup backport'unun yüklendiğini
gösterir; reddedilen tam costmap overlay'i kullanılmadı. İç ROS launch child
çökmesi ve `FORCED_KILL` ayrıca aranır; parent CLI 0 tek başına yeterli değildir.

Hedefli audit, gerçek FM COMMIT/Outbox, native doğrulama ACK'si, sağlık hash'i,
alınan gerçek IPC context'i, fizik öncesi sıfır seçimi ve ayrı fizik sonrası
readback'i eşler. Çıktı `PASS_TARGETED_STATIONARY_HEALTH_VETO_AUDIT`,
`scope_complete=true`, **`acceptance_complete=false`**; bu 14'lü kabul değildir.
Claims BLOCKED kalır, traffic Outbox PENDING sözleşmesi korunur ve fiziksel
release `RELEASE_THRESHOLDS_UNVERIFIED` ile reddedilir.

Son üç koşudaki **1838** yazıcı kaydının bütün joint hedefleri sıfırdır.
En büyük kayıtlı yatay yer değiştirme **1.618 × 10⁻⁷ m**; unsafe-contact kaydı
yoktur. Duran robot/zemin yerleşmesi ölçümleri hareketli fren kabulü değildir.
Native ACK, callback-join marker'ı ve fiziksel APPLIED/stop farklı kavramlardır.
Stop **UNKNOWN**, `StopEnvelope` **UNBOUNDED**, nonzero/rearm/rollover ve
fiziksel release kapalı kalır. ROS yayıncı kimliği hâlâ UNKNOWN'dır.

## Regresyon ve korunan başarısızlıklar

| Son seçki | Sonuç |
|---|---|
| Host domain/Outbox/Executor/traffic/health/readiness | **487 PASS**, 0 fail/skip |
| Typed Humble ROS / integration | **200 PASS**, 0 fail/skip |
| Aynı native a4 binary ile sağlık/IPC CTest | **2/2 PASS** |
| Düzeltilmiş bridge yaşam süresi CTest | **1/1 PASS** |
| Üç hedefli canlı koşu ve çapraz denetim | **3/3 temiz**, kaynak/binary sabit |

Seçkiler örtüşür; benzersiz toplam olarak toplanmaz. ROS regresyonundaki
mevcut invalid feedback-publisher / unresolved-ownership negatif test log'ları
korunur; fiziksel stop kanıtı sayılmaz. Tam depo suite'i/GUI çalıştırılmadı.

Önceki tüm kanıtlar değişmedi. Yeni bridge SIGABRT core'u, salt-okunur Nav2
SIGSEGV core'ları, negatif yaşam süresi testleri ve başarısız başlangıçlar
korundu. İki RelWithDebInfo derlemesinde compiler bellekten öldürüldü; bunlar
başarı sayılmadı. Son bağımlılık derlemesi tek compiler ve `-O1` ile bitti.
Tam Nav2 costmap paketini yeniden derleyen ara overlay yeni başlangıç hataları
üretti ve reddedildi; son yöntem sadece kurulu cleanup sembolüne daraltıldı.
Bu ara başlangıç hatasının kök nedeni çözülmüş diye sunulmaz.

İlk host tekrarında snapshot'a eklenmemiş tarihsel topology fixture nedeniyle
**486 PASS / 1 FAIL** oluştu. Mevcut baseline dosyası birebir kopyalandı;
assertion değiştirilmedi ve son 487 test geçti. İlk post-run mapping denetimi
cleanup interposer'ını costmap tüketicilerinde de beklediği için kaldı;
doğru sahipler olan controller/planner'a daraltılan analiz ayrıca kaydedildi.
Hiçbir koşu veya test atlanarak PASS üretilmedi.

## Kaynak/binary ve teslim sınırı

| Binary | SHA-256 |
|---|---|
| ROS bridge kütüphanesi | `5c10fe7b89dab80db34810bd345c426646a5fa2083ec6e7a18353b963ff33501` |
| parameter_bridge | `693a291b78a786ae53b3d0121b65a4ed95a453320390b8c1e52ee1c37e2a61f5` |
| Cleanup backport | `6203bb8d6678277eaa77f9f3d4e0438a378d17d8cf411155c9a9db7df9610105` |
| Önceki aynı native joint writer a4 | `7d06ca9144f298693fe4abf158429f8d11403cbe6853dca9a69c42a08869c212` |

Tam kaynak/binary manifestleri kanıttadır. Sekiz mevcut health/native kaynak
dosyası önceki çalışma checkpoint'iyle birebir aynı; Scheduler, Outbox,
preemption, session doğrulaması ve eşikler değiştirilmedi. Child gözlem
dosyalarına yalnız opt-in tanı logları eklendi. Varsayılan config, GUI ve
launcher değişmedi; başka worktree'ye dokunulmadı.

Cleanup interposition'ı kurulu Humble sürümüne/ABI'sine bağlı deneysel bir
düzeltmedir; farklı Nav2 sürümü için bu sonuç devralınamaz. Üç kısa temiz
koşu tarihsel bütün crash yollarının veya tüm yük/iletişim koşullarının
kapatıldığını kanıtlamaz. Özellikle ilk metadata kaybı mekanizması ve tam
14'lü son revizyon kabulü açıktır. Donanım freni veya hareketli duruş güvencesi yoktur.

Kullanıcının son kapsamı burada biter: **14'lü matris yok, commit/push yok,
T3C-2 yok.** Çalışma ağacı değişiklikleri ve ham kanıtlar korunarak duruldu.
