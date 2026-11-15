# C5-B6B.6 — Actuator komut yetkilendirmesi ve replay sınırı

15 Kasım 2026 · `main` worktree. **PARTIAL / test-only**: ürün hareket kabulü değildir.
Dayanak: [B6B.2](c5-b6b2-traffic-permit-protocol.md), [B6B.3](c5-b6b3-traffic-motion-gate.md),
[B6B.4](c5-b6b4-single-velocity-output.md), [B6B.5](../validation/c5/c5-b6b5-watchdog-2026-11-15.md).
[Doğrulama ve sınırlar](../validation/c5/c5-b6b6-authorization-2026-11-15.md).

## Güven sınırı ve seçenekler

Mevcut ürün yolu `TrafficMotionGate (henüz ürün bağlantısı yok) → ROS bridge →
Ignition → stock DiffDrive` önerisidir; C5-A mevcut cmd_vel yolunu kullanır.
Ham `geometry_msgs/Twist` yalnız linear/angular vektörlerini içerir. Humble
[bridge dönüşümü](https://github.com/gazebosim/ros_gz/blob/humble/ros_gz_bridge/src/convert/geometry_msgs.cpp)
bu vektörleri çevirir; source/session/sequence/permit taşımaz. Topic adı,
keşfedilen publisher sayısı ve beyan edilen source kimlik doğrulaması değildir.

Seçenekler: Twist metadata'sı varsaymak (reddedildi), ürün IDL/bridge/driver'ını
şimdi değiştirmek (kapsam dışı), ayrı imzalı test zarfı ve hareketsiz sink
(uygulandı). `docker/experiments/c5-b6b6` ürün tarafından import edilmez.
Testte JSON, `std_msgs/String → ignition.msgs.StringMsg → std_msgs/String`
üzerinden taşınır; son ROS readback callback'i test actuator güven sınırıdır.
Stock DiffDrive'a bağlanmaz. Readback sonrası doğrulama native DiffDrive'a
atomik entegre edilmiş değildir; bu fark **UNVERIFIED / BLOCKER**'dır.

## Komut ve yerel güncellik sözleşmesi

Zarf `{body, mac}` içerir; HMAC-SHA256 kanonik, sıralı, NaN kabul etmeyen JSON
body'nin tümünü bağlar. Fixture'da rastgele 256-bit anahtar yalnız güvenilen
üretici/verifier test koduna verilir; yanlış anahtar sahte source'u kabul
ettirmez. Bu, anahtar sahipliğini doğrular; DDS publisher/process kimliğini veya
üretim anahtar dağıtımını doğrulamaz. Fixture süreçleri aynı UID/container'dadır;
anahtar çalabilen, verifier kodunu değiştirebilen veya gerçek actuator'a ayrı
yazabilen süreçlere karşı koruma iddiası yoktur.

| Body alanı | Kontrol |
|---|---|
| `source_session`, `actuator_session` | Fixture'da güvenilir yerel kurulumla bağlanır; actuator oturumu rastgele yenilenir. Ağdan rollover/rearm yoktur. |
| `command_sequence` | Pozitif uint64; son kabulden kesin büyük. Duplicate/eski ret; son sırada farklı tüm payload ayrıca CHANGED_PAYLOAD. Bellek sabittir; restart yeni actuator session ile fence edilir. |
| `permit_id`, `permit_generation` | Yerel fixture permit'i ve tam integer generation eşleşir; permit yerel deadline'ı dolmuşsa ret. Gerçek FM live permit doğrulayıcısı değildir. |
| `issued_at` | `{clock: source_monotonic, value: sonlu sayı}` yalnız imzalı diagnostic; receiver veya ROS saatiyle çıkarılmaz. Kaynak stamp'inden fiziksel yaş iddiası yoktur. |
| `ticket` | Receiver'ın yerel monotonik saatinde 200 ms yaşayan rastgele tek kullanımlık nonce. En çok 32 bekleyen bilet; ağdan bilet/rearm servisi yoktur. Süresi geçmiş/eski tekrar watchdog'u yenilemez. |
| `velocity` | Altı sonlu sayının tamamı sıfır olmalıdır; imzalı nonzero bile BLOCKED_REARM üretir. |
| `command_context` | Yerel fixture task/epoch/child bağlamıyla kanonik tam eşleşme. Gerçek ürün context/health üretmez. |

Bilet, gecikmiş imzalı zarfın receiver'a en geç kabul edilebileceği zamanı
receiver saatinde sınırlar. Geçerli anahtar sahibi üreticinin eski bir hız
niyetini yeni imzayla üretmesini anlamsal olarak kanıtlayamaz. Bilet alma
zamanı yereldir; sim zamanıyla steady saniyeleri toplanmaz. Permit'in 10 saniye,
biletin 200 ms, lease'in 250 ms değerleri test fixture'ıdır; ürün duruş bütçesi
veya onaylı threshold değildir. Yerel receipt yalnız kabulde kaydedilir.

## Watchdog, yetki ve duruş ayrı iddialardır

B6B.5 `Lease.hh` değiştirilmeden C++ shared test ABI ile çağrılır.
NO_COMMAND → ACTIVE yalnız doğrulanmış sıfır receipt ile olur; timeout
TIMED_OUT, sonraki doğrulanmış receipt BLOCKED_REARM üretir. Yanlış MAC
receipt'i timeout'u veya deadline'ı değiştirmez. Kilit ağdan açılamaz;
yeni instance bile yalnız sıfır diagnostic kabul eder. Nonzero çıktı API'si,
actuator publisher'ı ve ownership/permit-release yolu yoktur.

Gate/bridge ayrı süreçtir; sink/native lease ayrı süreç yaşamında değildir:
test runner içinde readback callback ve timer ile çağrılır. Gate/bridge
SIGKILL'den sonra çalışan runner native steady timeout'u gözler. Bu sınırlı
bağımsızlık doğrulanır; actuator runner/update-loop ölümü veya donmasına karşı
bağımsız hardware fren/thread garantisi yoktur. Lease state, hedef sıfır ve
fiziksel duruş farklıdır. Dünya/robot/fizik başlatılmadığından fiziksel duruş
her test için **HENÜZ TEST EDİLMEDİ** kalır.

## Gerçek transport erişimi

[ROS DDS-Security](https://design.ros2.org/articles/ros2_dds_security.html)
PKI kimliği, imzalı governance/permissions ve destekleyen RMW ile publisher
izinlerini sınırlayabilir. Üründe/test overlay'inde bu policy kurulmadı.
`ROS_SECURITY_ENABLE=true`, `ROS_SECURITY_STRATEGY=Enforce` tek başına yeterli
değildir: doğru enclave/sertifika, default-deny topic izinleri, korunan anahtarlar,
bridge kimliği ve negatif yazma testleri gerekir. Yetkili ROS publisher da eski
komut gönderebilir; actuator session/sequence/ticket denetimi ayrıca gerekir.

Kurulu Ignition Transport 11.4.2'nin
[resmî güvenlik sözleşmesi](https://gazebosim.org/api/transport/11/security.html)
varsayılanı kimliksizdir. `IGN_TRANSPORT_USERNAME/PASSWORD` süreç düzeyinde
ortak kimlik bilgileriyle authentication sağlar; per-topic producer rolleri
ve actuator session/sequence semantiği sağlamaz. Bu testte etkinleştirilmedi.
`IGN_PARTITION`, DDS domain, localhost ve `--network none` test izolasyonudur;
aynı ortamda doğrudan transport erişimi olan süreç için ACL değildir.

Gerçek doğrudan IGN yazmayı sınırlandırmak için yalnız güvenilir adapter ve
actuator'ın erişebildiği ayrı OS kullanıcı/namespace/container/network sınırı,
korunmuş kimlik bilgileri ve default-deny girişler birlikte kalifiye edilmelidir.
Aynı UID/root/transport yetkisi olan yerel süreçlere karşı topic adı veya ortak
şifreyle ayrıcalık ayrımı iddia edilmez. Bu çözüm **ÖNERİ / UNVERIFIED**.
Mevcut stock DiffDrive'ın kimliksiz Twist girişi ve ürün bypass'ları kapanmadı.

## B6B.7 için en küçük adım

**ÖNERİ:** hareket kapalı kalırken doğrulayıcıyı native test actuator'ın tek
callback sınırına almak; ham Twist alternatif girişinin bulunmadığını test etmek;
korunan test kimlikleriyle DDS deny-all/allow-only policy ve ayrı IGN OS erişim
sınırını gerçek negatif yazma testleriyle kalifiye etmek. Önce mesaj kabulü ile
transport engellemesini ayrı kanıtlamak gerekir. Ürün FollowPath, gerçek nonzero,
fiziksel fren/health/duruş zarfı ve release kalifikasyonu bu adımın kabulü değildir.
