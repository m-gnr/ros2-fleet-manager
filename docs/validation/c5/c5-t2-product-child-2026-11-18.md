# C5-T2 — Gerçek ürün görevi ve Nav2 child/Path bağı

18 Kasım 2026. Taban `33ad236392f81dce6fe1b354c835e6f852de461d`.
**T2 bağımsız metadata kapsamı DOĞRULANDI; deneysel ve varsayılan kapalı.**
Gerçek ürün Outbox → ExecuteTask → NavigateToPose → FollowPath kimlik bağı
kuruldu. **Nonzero hareket yetkisi, APPLIED ACK, fiziksel stop/release veya
hareketli trafik koordinasyonu kabulü verilmedi.** T1 kaynakları ve kanıtları
korundu. [Komut eki](c5-t2-product-child-commands-2026-11-18.md) ·
[Ham kanıt ve manifest](c5-t2-product-child-2026-11-18/) ·
[Mevcut B6B.2 tasarımına T2 eki](../../design/c5-b6b2-traffic-permit-protocol.md#18-kasım-c5-t2-eki--gerçek-ürün-child-kanıtı) ·
[Mermaid](../../diagrams/src/traffic-product-child.mmd) · [SVG](../../diagrams/svg/traffic-product-child.svg).

## Mimari bulgu ve gerçekleştirilen bağlantı

Stock NavigateToPose response'u kendi UUID'sini verir; BT'nin FollowPath
UUID'sini veya gönderilen Path byte'larını vermez. Status topic'ini dinlemek
ya da benzer pozları eşlemek, child ile ExecuteTask arasında güvenilir bir
ilişki kurmaz. T1 testi gerçek FollowPath kullanıyordu, fakat üst ataması
domain fixture'ıydı ve ExecuteTask göndermiyordu.

T2, mevcut Executor'da yalnız açık in-process `_traffic_child_test_profile`
seam'ini ekler. Gerçek ServerGoalHandle/request ve ExecutorSafety session'ı
task/epoch/üst UUID bağlamını oluşturur. Her gerçek NavigateToPose gönderimi
ayrı client UUID'si ve üzerine yazılmayan, goal'a özel BT XML dosyası alır;
gerçek NavigateToPose accepted ClientGoalHandle ile tekrar eşleştirilir.
`fleet_nav2_observer`, stock Humble FollowPathAction'ını genişleterek kendi
gerçek accepted child handle'ını ve gönderimden önceki tam Path kopyasını
yayınlar. Üst UUID child UUID yerine kullanılmaz.

Executor'daki `ChildBinding` bu gözlemi yerel aktif assignment, epoch,
Executor session, NavigateToPose UUID, XML context UUID, observer session,
kesintisiz artan sıra ve zaman sınırıyla eşleştirir. Tam ROS Path byte'ları
SHA-256 ile sabitlenir. Gözlem süresi ROS clock üzerinden mevcut Executor
odometry freshness değeriyle; toplam fixture deadline'ı monotonik saatle
ölçülür. FM'in **2 s STALE / 5 s uyarı** eşikleri korunur.

Mevcut RequestTrafficPermit sözleşmesine opsiyonel provenance alanları
eklendi. Eski B6B.2 hazırlama modu korunur; kısmi yeni kanıt eski moda
düşemez. ROS callback yalnız mevcut consumer'a değer olayı sunar.
Consumer'ın yeni küçük `traffic_child.py` işlemcisi mevcut B6B.1/B6B.2
bind/acquire ve **aynı SQLite transaction / traffic_outbox** altyapısını
kullanır. Yeni trafik çekirdeği, tablo, Scheduler veya fiziksel robot durum
makinesi eklenmedi. Hareket Outbox'ı değişmedi.

Replan, farklı child/Path, iptal, terminal, yerel assignment kaybı ve timeout
eski bağı kapatır. Consumer, kabulden önce ulaşan iptal kaydını da tutar;
gecikmiş kabul bu kapanmayı aşamaz. Duplicate/stale/session/epoch uyuşmazlığı
reddedilir. Claim fiziksel kanıt olmadan serbest kalmaz; kapanmada BLOCKED
kalır. Yeni child veya epoch eski rezervasyonu devralmaz. Restart'ta yerel
context yüklenmez; mevcut nonempty DB otomatik devam için kabul edilmez.

## Yeni bağımsız testler ve regresyon

| Seçki | Son doğrulama |
|---|---|
| Host: yeni provenance, B6B core/protocol/gate, Outbox, Scheduler, Executor safety/state machine, peer config, park/şarj, rota, topology | **350 PASS / 0 FAIL / 0 SKIP** |
| Humble: yeni typed IDL/service/BT XML seam, gerçek tip guard'ları ve mevcut Executor/ROS lifecycle/safety | **66 PASS / 0 FAIL / 0 SKIP** |
| fleet_interfaces + yeni BT observer + fleet_perception build | **3 paket başarılı** |
| Native PeerRobotLayer regresyonu | **10 gtest PASS**; colcon wrapper dahil 11, 0 skip |
| Değişmeyen B6B.7 native binary: authorization ve gerçek callback/target programları | **2 program PASS**; nonzero/replay/timeout kapalı |
| Varsayılan kaynak/launcher ve doğrudan NavigateToPose gönderimi | **PASS**; observer varsayılan None, UUID/BT eklenmez |

Seçkiler örtüşür; bu sayılar tek bir benzersiz test toplamı değildir. Tam
depo suite'i ve T3–T5 hareketli senaryolar çalıştırılmadı. Bazı mevcut ROS
lifecycle testleri belirsiz görevleri teardown'da durdururken ERROR ve
goal-state/feedback uyarısı basar; bunlar loglarda korunur, fiziksel başarı
veya yeni trafik terminali olarak kullanılmaz.

Yeni testler yanlış UUID/Path/session/epoch, duplicate/sıra boşluğu, kaynak
yaşı ve receipt timeout, observer restart, replan/terminal/cancel, geç kabul,
SQLite rollback ve Outbox atomikliğini kapsar. Release her durumda mevcut
`RELEASE_THRESHOLDS_UNVERIFIED` sınırını korur. APPLIED/RETIRED gönderilmez.

Genişletilen seçkide B6B.4 tarihsel hash testi önce kaldı: T1 tabanındaki altı
dosya zaten 15 Kasım hash'lerinden farklıydı. Tarihsel baseline değiştirilmedi.
Yeni test fixture'ı bu altı hash'i **T1 commit'inden** alır; Executor'ın T2
hook'u için byte eşitliği yerine varsayılan gönderimin aynı nesne ve argümanla,
UUID/BT mutasyonu olmadan çalıştığı davranış testi eklendi. Bu güncelleme
hareket kapısı veya safety testinin atlanması değildir; başarısız ilk log
ayrıca korunur.

## İzole canlı Nav2 kanıtı — a6

Tek simülasyon, ayrı domain **218** ve IGN partition kullanıldı. Üç robot
config'den üretildi. Mevcut bağımsız fiziksel reset, AMCL/Nav2/TF readiness
ve contact gözlemcisi korunarak gerçek Battery Simulator ve ürün Executor'lar
başlatıldı. Varsayılan demo/API/frontend başlatılmadı. SDF'deki her robotun
tek joint writer'ı mevcut B6B.7 native sıfır sürücüdür; gerçek Gazebo maps
kaydındaki binary hash'i `00d6fb6687b32dfd3b475688a8c0fe7ee0455c76f67afaf6b8e8e9798b5a275f`.

FM normal canlı Nav2 rota sorguları ve mevcut Scheduler ile Alpha'yı seçti;
gerçek ExecuteTask Outbox kaydı **SENT** oldu. Nav2'ye kısa bir rota gönderildi,
robot native sürücüyle sabit tutuldu. Bu fiziksel taşıma başarısı değildir.

| Kimlik / içerik | Gerçek kayıt |
|---|---|
| task / assignment_epoch | `t2-real-task` / `1` |
| ExecuteTask UUID | `7ca8468e-7044-4752-8a61-1744767c5f0d` |
| NavigateToPose UUID | `e793a445-7b76-431c-afc1-382e26a1aea0` |
| İlk gerçek FollowPath child UUID | `cb933732-407c-1d8f-507e-07bea49e7cf0` |
| Tam Path SHA-256 | `39b30569aab1c00835613a2802a92930eb6bdb9453bab7327a8a18e8b12d9947` |
| XML context UUID | `b6293331-6568-4f41-9063-bc8a6c511128` |

İlk gözlem aynı kimlikle RESERVED kararına ve trafik Outbox COMMIT'ine
ulaştı. Ham BT mesajlarında sıra 1 gerçek kabul, sıra 2
`PATH_OR_CONTROLLER_REPLACED`, sıra 3 yeni gerçek child kabulü ve sıra 4
`BT_HALTED` görüldü. **Sıra 3 kapatılan bağı açmadı**; yeni child eski claim'i
devralmadı. İlk claim BLOCKED kaldı. Gerçek parent goal iptali
STATUS_CANCELED + gerçek completed_epoch=1 / PREEMPTED döndü; bu test
başlangıçta duran robotta mevcut C3 iptal protokolünü gözler, hareketten
frenleme veya HIGH Scheduler preemption kabulü değildir.

Fixture, iptal öncesi Outbox dispatch döngüsünü durdurur. Mevcut C3 domain
kuralı iptal edilen işi epoch 2 ile tekrar atayabilir; bu yeni Outbox kaydı
PENDING kalır ve gönderilmez. Epoch 1 context'i veya rezervasyonu otomatik
geçerli sayılmaz. Bu davranış Scheduler değiştirilerek gizlenmedi.

Üç native alıcıdan **2.449 örnekte** hedef linear/angular ve gerçek joint
komutları sıfırdı. Örneklenen maksimum yatay yer değiştirme yaklaşık
**4,25 × 10⁻¹¹ m**; robot/raf/duvar UNSAFE_CONTACT kaydı **0**. Robotlar
baştan duruyordu; hareketli stop mesafesi, tüm temas türleri veya çarpışmasız
koordinasyon garantisi verilmez. Fiziksel release isteği **DENIED** kaldı.
Bütün child process'ler **0** ile kapandı; test container'ı kaldırıldı.
[Son koşu](c5-t2-product-child-2026-11-18/live/a6/identity-summary.json) ·
[Ham BT gözlemleri](c5-t2-product-child-2026-11-18/live/a6/child-observations.json) ·
[Kapanış](c5-t2-product-child-2026-11-18/live/a6/shutdown.json).

## Önceki denemeler ve koruma

- **a1 / domain 213:** loopback-only DDS participant sınırı; reset/readiness
  oluşmadı, görev gönderilmedi. Kesilerek kapatıldı; simulation exit 1 korunur.
- **a2 / domain 214:** reset/readiness geçti. Fixture aynı pickup/dropoff
  noktasını verdiği için planner'ın tek pose'lu mesafe sonucu None kaldı;
  mevcut no-fallback kuralı gereği atama/Outbox olmadı. Bind mount WAL'ını
  okuyan bağımsız gözlemci readonly hatasıyla çıktı.
- **a3 / domain 215:** SQLite konteyner yerel dosya sistemine taşındı;
  rota sorgu kaydı tek pose'lu mesafenin None olduğunu gösterdi. Kuyrukta
  kaldı; bütün süreçler temiz kapandı. Planner sonucu uydurulmadı.
- **a4 / domain 216:** farklı pickup/dropoff ile gerçek ürün child bağı,
  replan, cancel ve sıfır native hedef geçti. Fixture iptalden sonra dispatch'i
  sürdürdüğü için meşru epoch 2 yeniden gönderildi; kapanışta unresolved goal
  hatası çıktı. **Son temiz kabul koşusu sayılmaz.**
- **a5 / domain 217:** metadata ve temiz kapanış geçti. Özet sayaç 2.519,
  ham native dosya 2.502 örnekti: callback yazımı sürerken snapshot sınırı
  farklıydı. İki kayıt değiştirilmeden korundu; nihai sayım kanıtı değildir.
- **a6 / domain 218:** kontrol, ham dosya ve rapor tek kilit altında alınan
  değişmez snapshot kullanır. Aynı gerçek ürün zinciri ve temiz kapanış
  tekrar geçti; **2.449** native örnek ham dosya ve raporda birebir eşleşir.

İlk Python geçmiş filtresi/C++ derleme hataları ve test düzeltmelerinin
logları da arşivdedir. T1 kanıtları yeniden yazılmadı. Native provision
anahtarları `/run` içinde kaldı; arşiv yalnız public fixture bilgilerini
içerir. Build ürünleri, venv ve cache'ler commit dışındadır.

## İzolasyon, açık eksikler ve C5-T3

Varsayılan launcher, dashboard runtime, ortak generator, native B6B.7,
motion gate, Scheduler ve safety eşikleri T1 ile byte düzeyinde korunur.
Executor'ın yeni kurucu seam'i None'dır; launcher/ROS parametresiyle
açılmaz. Yeni BT paketi varsayılan overlay paket listesinde değildir.
PeerRobotLayer ve native B6B.7 hâlâ varsayılan demoda kapalıdır.

**C5-T3 için metadata başlangıcı hazırdır; gerçek hareket yetkisi hazır
değildir.** Gözlem gerçek child kabulünden sonra rezervasyon alır; actuator
öncesi atomik izin kapısı değildir. Nav2 ham hızının gerçek child/permit'e
bağlanması, gerçek sağlık snapshot'ı, native canlı permit/context uygulaması,
kalifiye duruş zarfı, hold/resume, fiziksel release ve güvenli rollover
T3–T5'te tamamlanmalıdır. NavigateToStation/park/şarj ürün child gözlemi bu
T2 canlı koşusunda doğrulanmadı. Beta/Gamma ürün child zinciri ayrı canlı
test edilmedi; üç robotlu ortam yalnız native sıfır ve başlangıç kanıtıdır.
DDS/SROS yayıncı authentication yoktur; token/hash güvenlik imzası değildir.
Manager veya Executor restart'ı otomatik uzlaştırma/continue değildir.

Kullanıcının T2 kapsamına verdiği açık izinle bağımsız testler ve izolasyon
geçtikten sonra tek deneysel commit hazırlanır; uzak dal fast-forward ise
normal push yapılır. Kendi commit/uzak SHA'sı döngüsel olarak bu dosyaya
yazılmaz; teslim yanıtında verilir. Başka worktree, force push veya reset yoktur.
