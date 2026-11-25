# C5-T3C-1B — Gerçek sağlık veto'su ve son yazıcı

24 Kasım 2026 · Taban `f69d1024b36a2cc5ac8ad93679f9f66c22f13397`.
**KISMİ UYGULAMA / TAM CANLI KABUL VERİLMEDİ.** Deneysel ve varsayılan kapalı.
Nonzero/rearm/rollover açılmadı; duruş veya hareketli fren kabulü yoktur.
Kabul engelleri nedeniyle commit/push yapılmadı; değişiklikler çalışma ağacındadır.

[1A](c5-t3c1a-native-worker-2026-11-19.md) ·
[T3B](c5-t3b-health-stop-2026-11-18.md) ·
[Mimari](c5-t3c0-stop-architecture-2026-11-19.md) ·
[Komutlar](c5-t3c1b-health-veto-commands-2026-11-24.md) ·
[Kanıtlar](c5-t3c1b-health-veto-2026-11-24/) ·
[Mermaid](../../diagrams/src/traffic-native-health-veto.mmd) ·
[SVG](../../diagrams/svg/traffic-native-health-veto.svg).

## Gerçekleştirilen bağlantı

T3B `HealthWindow` değerlendirmesi korunur. Yeni opt-in `SplitHealthWindow`
ve `SplitHealthProbe`, eski monolitik `native_health` yerine ayrı işçinin
imzaladığı **gerçek IPC readback**'ini ve gerçek costmap `ObservationHealth`
mesajlarını tüketir. Native status/ACK değiştirilmez. Ek readback HMAC alanı
tanısaldır; fiziksel APPLIED veya stop değildir. Sağlık çıktısı yalnız veto
eder; `movement_eligible=false`, `ownership_release=false`, stop **UNKNOWN**.

Mevcut FM/SQLite/Outbox bağından gerçek task, assignment epoch, Executor/FM
session, ExecuteTask ve gerçek FollowPath UUID, Path digest, permit/generation
kimlikleri alınır. Komut ve context hash'i, kaynak permit/child kararları ve
değişmez aktarım byte'larıyla karşılaştırılır. Sağlık paketi bu kimliğin
digest'ini, native session/context, writer boot ve özgün kaynak damgalarını
taşır. ROS mesajları için epoch/session doğruluğu kriptografik kaynak kanıtı
değildir; bağ **alım ilişkilendirmesidir**, yayıncı kimliği **UNKNOWN** kalır.

İşçi, ayrı HMAC alanıyla sağlık paketini doğrular; yanlış bağlam, session,
sıra, source rewind ve aynı ölçümün kalan ömrünü artırma reddedilir.
Mevcut fixed-size nonblocking seqpacket yanıtına yalnız sınırlı `HealthPart`
eklenir. Son DiffDrive yazıcısı JSON/HMAC/mutex veya işçi beklemez. PID/UID,
boot, native session/context ve komut lease denetimlerine ek olarak sağlığın
kendi çıkardığı biletini ve kalan süresini kontrol eder. Bilet geçmişi sabit
128 kayıttır; ring'den düşmüş bilet geçerli sayılamaz. Deadline, paketin alım
anına değil **gerçek biletin yazıcıdaki üretim anına + kalan ölçüm bütçesine**
bağlıdır. Bu muhafazakâr hesap aktarım gecikmesini tazelik kazancına dönüştürmez.

Eski paket/heartbeat aynı sağlık veya komut lease'ini yenilemez. İlk context
ve sağlık beklenirken uygunluk kapalıdır. Geçerli sağlık görüldükten sonra
eksik/bozuk/stale sağlık, işçi/IPC kaybı veya native kapanma kalıcı kapalı
kilit oluşturur. Geç ACK, eski sağlık ve işçi restart'ı kilidi açamaz. Native
doğrulayıcı kapalı yazıcıdan sonra da zarf doğrulayabilir; ACK bu nedenle
yazıcı seçimiyle veya fiziksel uygulamayla eşitlenmez.

**Tek joint yazıcısı korunur; geçerli sağlık ve permit dahil her hedef sıfırdır.**
Yeni trafik protokolü, robot durum makinesi veya fiziksel release yoktur.
Scheduler/Outbox/preemption, sahiplik ve STALE eşikleri değiştirilmedi.

## Gerçek kaynaklar ve fixture düzeltmeleri

- Odometri ile TF ayrı DDS mesajlarıdır. Sınırlı tampon, özgün odometri
  damgasında gerçek dönüşümü seçer; latest-TF fallback veya yeniden damgalama
  yoktur. TF beklenirken duplicate odometri ilk alım süresini yenileyemez.
- ObservationHealth değerlendirme sırası ve `processed_at`, sensör ölçümü
  değildir. Her buffer'ın özgün ölçüm damgası ve ilk alımı korunur; bir
  sensörün yenilenmesi diğerinin süresini yenilemez. Aynı sim zamanındaki
  yeni layer değerlendirmesi yanlış bir ölçüm rewind'i sayılmaz.
- Durağan AMCL için gerçek `request_nomotion_update` RPC kullanılır. İlk canlı
  koşuda gerçek AMCL negatif kovaryans üretti ve PSD denetimi doğru biçimde
  veto etti. Nav2 1.1.20'nin `set_initial_pose=true` yolu sıfır kovaryanslı
  mesaj oluşturur; `initOdometry` varsayılan öncülleri ise `0.5², 0.5²,
  (π/12)²` değerleridir. Yeni izole senaryoda, görevden önce bu öncülle gerçek
  `set_initial_pose` servisi çağrılır. Sağlık çıktısı düzeltilmez/clamp edilmez;
  [Nav2 birincil kaynak](https://github.com/ros-navigation/navigation2/blob/1.1.20/nav2_amcl/src/amcl_node.cpp).
  Bu başlangıç öncülü fiziksel hata sınırı veya kalibrasyon değildir.
- Sadece 1B fixture'ında local costmap güncellemesi mevcut sağlık timer
  periyoduna alınır; stok 5 Hz costmap + 5 Hz scan hattı 0.5 s ölçüm bütçesini
  aktarımdan önce tüketebiliyordu. Hiçbir yaş/lease/STALE eşiği büyütülmedi.
- ROS gözlemcisi mevcut executor'da sınırlı callback batch'i tüketir; fizik
  döngüsüyle birleşmez. Release denetimi hata kanıtından sonra ayrıca yapılır.
  Controller fault'u mevcut lifecycle manager üzerinden PAUSE ister; dışarıdan
  doğrudan transition ile bond-recovery yarışına girilmez. Native rearm yoktur.

## Doğrulama durumu

| Son kontrol | Sonuç |
|---|---|
| Host domain/Executor/Outbox/traffic/health seçkisi | **472 PASS**, 0 fail/skip |
| Humble typed ROS / integration seçkisi | **185 PASS**, 0 fail/skip; mevcut invalid feedback-publisher teardown uyarısı korunur |
| 1B native temiz a4 build / CTest | **2/2 PASS**, health receiver/son veto + eski IPC |
| Sağlık makrosu kapalı 1A temiz build | **1/1 PASS** |
| Eski B6B.7 / B6B.5 temiz native build | **3/3 + 2/2 PASS** |
| İkinci izole durağan matris | **11/14 temiz CLI**, 3 başarısız; tam kabul **FAIL** |
| Tam COMMIT/ACK/sağlık/IPC/Physics audit | Başarısız CLI nedeniyle doğru biçimde **FAIL** |
| Yalnız temiz biten 11 koşunun çapraz denetimi | 11/11 kanıt tutarlı; çıktı açıkça `INCOMPLETE_1B_ACCEPTANCE_COMPLETED_CASES_AUDITED` |

Seçkiler örtüşür; benzersiz test toplamı olarak toplanmaz. Tam depo suite'i,
GUI ve varsayılan demo çalıştırılmadı. Ham ledger, CLI/kapanış, kaynak/binary
hash'leri ve denetim çıktısı [kanıt dizinindedir](c5-t3c1b-health-veto-2026-11-24/).
Native a4'ün derlenen C++/header/CMake girdileri son kaynakla aynıdır. Canlı
Python fixture/adaptörleri koşu başına hash'lenir. Son matris **tek dondurulmuş
kaynak revizyonu değildir**: geçersiz pending veri tamponunu temizleyen son
düzeltme sırasında iki adaptör varyantı vardır. Son kaynak host/ROS
regresyonlarından geçti; aynı son kaynakla tam canlı matris henüz doğrulanmadı.

### Son canlı matris: gerçek tamamlanan Physics Update sayacı

Her satır ayrı Linux-local DB, native session/boot ve fiziksel reset ile başladı;
güncel RobotStatus sonrasında mevcut trafik geometrisi kuruldu. Atama gerçek
Scheduler'dan okunur. Her koşuda üç robot gözlenir, tek gerçek görev/permit
kullanılır; üç eşzamanlı görev veya COMPLETED kabulü değildir.

| Koşu / domain | Gerçek robot | Physics: hata öncesi → sürerken | İlk kilit / tam CLI |
|---|---|---|---|
| health-flow-loss / 210 | Alpha | 1629 → 1725 | HEALTH_EXPIRED / 0 |
| tf-loss / 211 | Alpha | 1607 → 1855 | HEALTH_EXPIRED / 0 |
| odometry-loss / 212 | Alpha | 1636 → 1884 | HEALTH_EXPIRED / 0 |
| amcl-loss / 213 | Alpha | 1594 → 1798 | HEALTH_EXPIRED / 0 |
| controller-inactive / 214 | Alpha | 1789 → 2245 | HEALTH_REJECTED / **1** |
| observation-loss / 215 | Alpha | 1728 → 1821 | HEALTH_EXPIRED / 0 |
| health-context / 216 | Alpha | 1575 → 1606 | HEALTH_REJECTED / 0 |
| health-session / 217 | Atanmış native bağ yok | Hata testi başlamadı | ACK önkoşulu timeout / **1** |
| health-old / 218 | Gamma | 1639 → 1687 | HEALTH_REJECTED / 0 |
| worker-stop / 219 | Alpha | **1703 → 1777** | TIMEOUT / 0 |
| worker-kill / 220 | Alpha | **1662 → 1726** | HEALTH_EXPIRED / 0 |
| ipc-loss / 221 | Alpha | 1623 → 1695 | TIMEOUT / 0 |
| replan / 222 | Gamma | 1621 → 1809 | HEALTH_REJECTED / **1** |
| cancel / 223 | Alpha | 1541 → 1603 | NATIVE_CLOSED / 0 |

Worker SIGSTOP'ta PID **37**, Gazebo PID **42** idi. İşçi `/proc` durumu
**T** iken Physics ilerledi; Gazebo süreci durdurulmadı. SIGCONT ve eski paket
kilidi açmadı. SIGKILL sonrası farklı PID/native session ile gerçek işçi restart
edildi ve son yazıcı kapalı kaldı. Sayaç, stock Physics::Update'ın unpaused,
pozitif dt ile tamamlanmasıdır; dış clock/worker heartbeat veya engine solver
alt-adımı değildir. Yüklenen stock Physics/DART ve tek driver mapping'leri
koşularda saklandı. Durağan Physics ilerlemesi frenleme kanıtı değildir.

Temiz 11 koşuda gerçek `health-before.json`, sağlık gövdesi hash'ini son
yazıcıdaki kabul edilen health digest/sıra ile; gerçek IPC session/context/
komut hash'ini kalıcı transfer ve gerçek native ACK ile eşler. Ayrı imzalı
readback aynı gerçek yazıcı gözlemini içerir. Bütün kaynak mesaj yayıncıları
**UNKNOWN** olarak kalır. HMAC canlı probe'da doğrulandı; anahtarsız offline
audit HMAC'i tekrar doğruladığını iddia etmez. SQLite integrity ve Outbox byte
eşitliği kontrol edilir; traffic Outbox **PENDING** sözleşmesi korunur.

Korunan 31 ham koşuda **45.760 yazıcı kaydındaki bütün joint hedefleri**
sayısal sıfırdır; en büyük kayıtlı yatay yer değiştirme **1.620 × 10⁻⁷ m**.
Robot-robot/robot-raf unsafe-contact kaydı yoktur. Zemin desteği ve ilk yerçekimi
yerleşmesi bu kapsamın dışındadır. Bunlar eksiksiz süreklilik/kalifiye fren
kanıtı değildir. Temiz kabul adımlarına ulaşan koşularda fiziksel release
`RELEASE_THRESHOLDS_UNVERIFIED` ile reddedildi.

İlk native derlemelerin C++ callback tip hataları, ilk ROS duplicate-alım
testi başarısızlığı, sağlık bekleme/expiry ve ObservationHealth sıralama
denemeleri ayrı dizin/loglarda korunur. Eski kanıt yeniden yazılmadı.
CLI kapanışı başarısız olan koşunun `summary.json` dosyasında PASS bulunması
**tam koşu kabulü değildir**; ledger/exit ve shutdown birlikte değerlendirilir.

İkinci matrisin controller inactive koşusunda sağlık veto'su ve fizik ilerlemesi
gözlendi, fakat ROS/IGN bridge kapanışı **-11** ile bitti. Replan koşusunda
Beta'nın Nav2 controller'ı kapanışta **-11**, navigation lifecycle shutdown ise
timeout üretti; launch daha sonra lifecycle child'ını **-9** ile sonlandırdı.
Bu hataların kök nedeni çözülmüş sayılmaz. Yanlış-health-session koşusu gerçek
FM/native ACK önkoşuluna süre içinde ulaşamadı ve native alıcılar NO_COMMAND'da
kaldı; negatif paket testi yapılmış sayılmaz. Önceki matrisin bu senaryodaki
başarılı koşusu son başarısızlığı gizlemez. Bu nedenle tam T3C-1B kabulü ve
GitHub teslimi kapalıdır.

İzolasyon kontrolü tabandaki **6410** izlenen dosyanın değişmediğini, önceki
C5 belge/kanıtlarından **5771** dosyanın birebir korunduğunu doğrular. İzinli
13 izlenen dosya değişimi dışında ürün config/IDL/GUI/launcher/Scheduler/Outbox
değişmedi. Yeni dosyalar yalnız opt-in kod/test ve bu kayıt/kanıt/diyagramdır.
Başlangıç çalışma ağacı temizdi; önceki çalışma silinmedi/sıfırlanmadı, başka
worktree'ye dokunulmadı. Test container'ları ve kendi alt süreçleri kapatıldı;
varsayılan demo başlatılmadı. `origin/main` taban SHA'sında kaldı; commit/push yok.

## Kalan güvenlik sınırları ve sonraki adım

`StopEnvelope` ölçülmemiş fren/gecikme, konum/hız hata ve marj bounds nedeniyle
**UNBOUNDED**; tube yoktur. Duran robotun hedef/hız kayıtları fren kapasitesi,
hareketli stop veya üç eşzamanlı görevin COMPLETED olması kanıtı değildir.
Fizik öncesi hedef, tamamlanan stock Physics adımı ve fizik sonrası gerçek
joint/gövde hızı ayrı kayıtlardır. Hiçbir native ACK fiziksel APPLIED/stop veya
kaynak bırakma kanıtına yükseltilmedi. Gerçek release reddedilmeye devam eder.

Gazebo Physics, son yazıcı veya ortak OS arızasında bağımsız donanım freni
yoktur. Aynı UID/anahtar alanı, ROS yayıncı kimliği, zaman/gecikme bütçeleri
ve çoklu süreç güven sınırı kalifiye değildir. Kısa durağan gözlemler bu
sınırları kaldırmaz. Varsayılan launcher/GUI ve önceki çalışan demo değişmedi.

Sonraki adım **hareketli ölçüm değildir**: aynı sıfır-komut sınırında, güncel
RobotStatus/readiness ve gerçek Scheduler atamasıyla, permit önkoşulunun
sağlanamadığı başlangıcı ve bridge kapanış hatasını ayıran temiz senaryo;
ardından bütün 1B matrisini tek sabit kaynak revizyonunda tekrar doğrulama.
Ancak tam 1B kabulünden sonra ayrı açık yetkiyle erişim/süre kalifikasyonu ve
kontrollü hareketli fren/ivme/konum-hız hata ölçümleri planlanabilir.
