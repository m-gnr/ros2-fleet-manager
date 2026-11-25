# C5-T3C-2A — Kontrollü hareket öncesi hazırlık

25 Kasım 2026 · İncelenen taban `a3dcf9ec9e906362cb11ed2e8847fa324b6fac8c`.

**Hazırlık kapsamı: PASS. T3C-2B hareketli deneye geçiş: BLOCKED.**
Yeni hareket veya Gazebo koşusu başlatılmadı. Nonzero/rearm/rollover,
hold/resume, fiziksel release ve varsayılan GUI entegrasyonu kapalı kaldı.
StopEnvelope **UNBOUNDED**; yeni ölçülmüş fren sınırı yoktur.

[Komutlar ve doğrulama](c5-t3c2a-preparation-commands-2026-11-25.md) ·
[Salt okunur araç](../../../docker/experiments/c5-t3c2a/README.md) ·
[Önceki 14/14 kabul](c5-t3c1b-last-two-2026-11-25.md) ·
[T3C-0 mimari sınırlar](c5-t3c0-stop-architecture-2026-11-19.md) ·
[Özgün frenleme planı](c5-t3c-braking-plan-2026-11-18.md).

## 1. Doğrulanan gerçek kontrol zinciri

Bu kayıt yeni mimari onayı vermez. Kaynak incelemesi, yeniden çalıştırılan
regresyonlar ve önceki değişmez canlı kanıtın yeniden denetimi ayrı tutulur.
**Nav2 hızının native actuator'a uygulandığı bir hareket zinciri bugün yoktur.**

| Aşama | Mevcut gerçek davranış ve kanıt sınırı |
|---|---|
| FM → SQLite/Outbox | Tek consumer, task/epoch/session/rezervasyon ve gerçek child/Path bağını transaction içinde işler. ExecuteTask Outbox ile gönderilir. Native transfer body/kararı da kalıcı kayda bağlanır. `prepared_at/issued_at` transaction içi hazırlık damgasıdır; COMMIT tamamlanma anı değildir. |
| ExecuteTask → NavigateToPose → FollowPath | Executor gerçek görev yaşam döngüsünü yürütür; T2 observer gerçek FollowPath client goal handle/UUID ve exact Path'i bağlar. ExecuteTask UUID'si child UUID diye kullanılmaz. |
| Nav2 controller/smoother | Hız üretir; bu hız akışı native sıfır gövdesine çevrilmez. Mevcut native deneyde stock ham Twist yolu kapalıdır. |
| FM permit → NativeZeroROSBridge → Executor NativeZeroLink | Consumer sonucu COMMIT sonrasında geleceğe döner; bridge imzalı exact body'yi iletir. Executor yerel context/session/sequence çitlerini kontrol edip aynı bytes'ı yayınlar; FM adına ACK üretmez ve anahtar tutmaz. |
| Native worker | Ayrı C++ process'te AuthorizedZero HMAC/exact-body, session, sequence, ticket, permit/generation/child/Path context ve lease denetimi yapar. Body velocity yalnız altı sıfırdır; nonzero kalıcı olarak engellenir. Native ACK doğrulama kaydıdır. |
| Worker → IPC | Nonblocking bounded SOCK_SEQPACKET; PID/UID SCM_CREDENTIALS, boot/session/challenge/report/command/context ve writer-local deadline kontrol edilir. Yeni NO_COMMAND düzeltmesi eski ACTIVE paketini kabul ettirmez. |
| IPC → DiffDrive writer | Mevcut tek DiffDrive'ın PreUpdate'ı son veto'yu değerlendirir; her iki joint hedefini koşulsuz sıfır tutar. Aynı bileşen sol/sağ `JointVelocityCmd` komponentlerini yazar. UpdateVelocity de sıfır sınırını korur. |
| Writer → Physics → recorder | Tek stock Physics/DART Update çağrısı tamamlanınca pozitif-dt sayaç artar. PostUpdate gerçek WorldPose/WorldLinearVelocity/WorldAngularVelocity ve ilk sol/sağ JointVelocity'yi okur; ayrı recorder gözlem alır. Fizik thread'i recorder/worker beklemez. |

Kaynaklar: [consumer](../../../backend/fleet_manager/event_loop.py),
[native kalıcılık](../../../backend/fleet_manager/persistence/traffic_native.py),
[COMMIT sonrası bridge](../../../backend/fleet_manager/adapters/native_zero.py),
[Executor link](../../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/native_zero.py),
[AuthorizedZero](../../../docker/experiments/c5-b6b7/AuthorizedZero.hh),
[worker](../../../docker/experiments/c5-t3c1a/worker.cc),
[IPC](../../../docker/experiments/c5-t3c1a/Ipc.hh),
[DiffDrive](../../../docker/experiments/c5-b6b5/DiffDrive.cc),
[Physics wrapper](../../../docker/experiments/c5-t3c1a/physics.cc).

### Tek yazıcı ve arıza kapsamı

14 tarihsel SDF/mapping kanıtında model başına bir SplitZeroDiffDrive,
bir Physics wrapper ve ayrı worker vardır. Bu, **o opt-in dünya/build
konfigürasyonu** içindeki `JointVelocityCmd` yazıcısının tekliğidir; keyfi
başka plugin/process, world-pose komutu veya gerçek donanım üzerinde güvenlik
ACL'si/evrensel tek-yazıcı garantisi değildir. Physics motorunun temas/kuvvet
etkileri de bir komut yetkilendirme kanıtı değildir.

SIGSTOP/SIGKILL ve IPC kesintisinde eski kabulde Physics ilerlerken writer
sıfır seçmiştir; yeni offline audit aynı kaynakları tekrar doğruladı.
**Bu oturumda yeni fault veya canlı duruş testi yapılmadı.** Writer'ın veya
Physics'in kendi arızası worker arızasından farklıdır: writer çalışmazken
ilerleyen fiziğe fren uygulayabilen bağımsız donanım mekanizması yoktur.
Bütün Gazebo sürecini dondurmak frenleme kanıtı sayılmaz.

### Kaynak kimliği

FM exact-body HMAC'i, native receiver session'ı ve IPC process kimliği
belirli yerel bağlam kanıtlarıdır. Bunlar ROS mesajını hangi controller'ın
ürettiğinin kanıtı değildir. Humble graph GID/node adı, mesajın doğrulanmış
yayıncısı sayılamaz. Sağlık packet'inin `source_identity` alanları **UNKNOWN**
kalır. Nav2 hızının özgün üreticisi/üretim anı ve bu hızın gerçek child/Path'e
bağı bugün native'de doğrulanmıyor; geçerli sağlık tek başına izin değildir.

## 2. StopEnvelope ölçüm sözleşmesi

[StopEnvelope](../../../backend/fleet_manager/domain/stop_envelope.py)
StopInputs eksikse sıfır hızda bile UNBOUNDED döndürür. Bütün sayılar
verildiğinde dahi sonuç `CONDITIONAL_CANDIDATE`, `qualified=false` ve
`movement_authorized=false` olur; evidence hash'i kalibrasyonu kendiliğinden
kalifiye etmez. Hiçbir StopInputs alanı bu görevde sayı ile doldurulmadı.

| Gereksinim | Bugünkü veri | 2B öncesi/2B'de gereken ölçüm ve sınır |
|---|---|---|
| Komut üretimi → son yazıcı | FM source_monotonic issued_at/prepared_at, native verified_steady_ns, writer PostUpdate damgası; farklı süreçlerde | Gerçek Nav2 hız üretim anı, immutable command/hash/context; COMMIT bitişi, gönderim/aktarım/alım ayrı. Source clock → receiver/writer clock offset ve hata sınırı doğrulanmadan çıkartma yok. |
| Algılama / hesap / iletişim / uygulama | Health özgün stamp/ilk receipt/değerlendirme/publish; worker alım ve IPC check zamanları | Kaynak kesilmesinin gerçekleştiği olay, stale/veto kararı, son hedef yazımı ve gerçek fizik tepkisi ayrı. Dört StopInputs gecikme aralığı çakışmayacak tanımlanmalı; aynı süre iki kez sayılmamalı. |
| Kontrol döngüsü / fizik fazı | pre_iteration + post Physics sayacı, `writer_steady_ns` **POST_UPDATE** | Ayrı PreUpdate giriş/seçim, gerçek her-joint yazım ve PostUpdate damgaları; sim_ns/dt/iteration anlamının Physics adımıyla eşlemesi. ACK veya PostUpdate damgası pre-write anı sayılamaz. |
| Odometry/TF/AMCL yaşı | Header sim zamanı ve ilk monotonik receipt; exact odometry stamp'inde TF, AMCL covariance/PSD | Aynı frame ve zamanda world truth ile karşılaştırma, map→world hizalama ve hata bütçesi. Covariance/sigma bir deterministik konum üst sınırı değildir. |
| Gerçek teker/gövde hızı | İlk sol/sağ joint rad/s ve WorldLinear/AngularVelocity | Tüm konfigüre joint adları/entity ID, yarıçap/track ve gerçek quaternion/frame; world planar hızının gövde eksenine dönüşümü. Encoder/odometry ile fizik truth aynı otorite sayılamaz. |
| Fren eğrisi | Yalnız durağan, sıfır hedefli örnekler | Hareket başlangıç hızı/ivmesi, gerçek fault başlangıcı, hedefin sıfıra geçişi ve v(t)/omega(t). Reaksiyon ivmesi üst, etkin fren yavaşlaması alt sınırları; yük/zemin/slip/doygunluk kapsamı ve ölçüm hatası. |
| Mesafe / süre / dönüş | Post world position ve sim zamanı var; aralıklı örnekler | Fault → ölçülmüş ardışık duruş penceresi boyunca yol uzunluğu, son displacement, açı ve süre ayrı. Sadece iki uç nokta veya sıfır komut yeterli değil; örnek boşluklarındaki hareket bilinmiyorsa üst sınır yok. |
| En kötü durum | Gözlenmiş maksimum örnek aralıkları, limit config'i | Kapsamı sabit model/build/config/yük/sürtünme, hız/yön/dönüş koşulları ve tekrar/yük matrisi; clock/ölçüm hatası ve eksik frame etkisi. Gözlenen maksimum, ortalama veya Nav2 decel limiti garanti değildir. |

StopInputs eşlemesi: `detection_sec`, `computation_sec`, `communication_sec`,
`actuator_sec`; reaksiyon `linear/angular_acceleration`; frenleme için pozitif
`linear/angular_deceleration`; konum/hız/açısal hız hata bounds'u, gerekçeli
`margin_m` ve değişmez kanıt hash'i. Geri/yön değiştirme, dönme ve birleşik
hareket mevcut izotropik modelin varsayımlarıyla ayrıca uyumlanmalıdır.
Ölçülmeyen veya kalibrasyon kapsamı dışındaki alan **None / UNBOUNDED** kalır.

## 3. Tamamlanan salt okunur hazırlık

Yeni [measurements.py](../../../docker/experiments/c5-t3c2a/measurements.py):

- Yeni trafik, hareket veya robot durum makinesi kurmaz; ROS publisher,
  socket, simulator veya actuator başlatmaz. Mevcut 1B tam audit'ini yeniden
  kullanır. Çıktı girdi ağacına yazılamaz ve var olan çıktı ezilemez.
- Manifestteki kapalı backup DB'leri `mode=ro&immutable=1` ile okur;
  boş olmayan canlı WAL reddedilir. Ürün SQLite/Outbox koduna dokunmaz.
- Gerçek görev/epoch/session/child/Path/permit kimliğini ve komut hash'ini,
  özgün health stamp/measurement ID/receipt yaşlarını korur. FM/native/writer
  ham zamanlarını ayrı tutar; clock eşlemesi yoksa uçtan uca gecikme **None**.
- `post_actual_body_velocity` alanının uygulamadaki kaynağını **WORLD-frame**
  diye etiketler. Gövde-ekseni işaretli hız ve pre-joint-write zamanı **None**.
  Bilinmeyen readback'i sıfıra çevirmeyi, robot/boot karıştırmayı, bozuk veya
  ilerlemeyen fizik kaydını başarı saymaz.
- Her writer boot'unun tamamındaki gözlemleri görev-özel örnek diye sunmaz;
  gözlenen aralıkları worst-case bound veya fren kalibrasyonu yapmaz.

Yeniden okunan tarihsel kanıt: **14 koşu, 42 robot/writer grubu, 14.715 kayıt**.
Tüm pre-selected hedefler sıfırdır. Gözlenen en büyük kayıt boşluğu aynı
writer monotonik saatinde **1.087833 s**, sim zamanında **0.060 s / 12 Physics
adımıdır**; bunlar farklı örnek çiftlerinin maksimumları olabilir. Bu kayıt
sıklığı/trace kaybı, sürekli fren eğrisi üst sınırını kanıtlamaz. Trace gönderim
kayıp sayacı ve her-fizik-adımı kayıt zinciri henüz yoktur.
Gözlenen world XY hızının maksimumu yaklaşık **2.821e-7 m/s**; bu durağan
simülasyon sayısı ölçülmüş hareketli frenleme kapasitesi değildir.

İlk denemede eski audit'in `mode=ro` kullanımı 28 yeni WAL/SHM yan dosyası
oluşturdu; DB'ler değişmedi. Bu ilk salt okunurluk varsayımı **başarısızdı**;
ilk PASS çıktısı final hazırlık kanıtı sayılmaz. Yeni yan dosyalar korundu.
Ayırma glob'u 36 sıkıştırılmış eski artefaktı da geçici olarak seçti; tümü
korunan bytes'tan özgün yerine geri alındı, 1.825 eski arşiv hash'i doğrulandı.
Düzeltmeli immutable okuma yeni yan dosya oluşturmadı. Bu hata ve düzeltme
[ham kayıt/koruma kanıtında](c5-t3c2a-preparation-2026-11-25/manifest.json) açıktır.

## 4. Geçiş kapıları

| Kapı | Durum | Anlamı |
|---|---|---|
| 2A kaynak/mimari ve ölçüm envanteri | **PASS** | Kaynak incelemesi + tarihsel tam audit yeniden çalıştı. |
| 2A salt okunur araç ve koruma | **PASS** | 13 test; immutable çıktı, eski DB/arşiv hash'leri aynı. |
| 2A mevcut davranış / varsayılan izolasyonu | **PASS** | Kontrol/health/lease/Outbox/STALE/GUI/launcher kaynak ve kabul binary'leri değişmedi. |
| Hareketli deney için ayrı yetki ve tek-robot fixture | **BLOCKED** | Bu görev hareket yetkilendirmesi vermez; tek-robot canlı fixture oluşturulmadı/başlatılmadı. |
| Kaynağı doğrulanmış gerçek Nav2 hız girişi | **BLOCKED** | UNKNOWN; mevcut sıfır native body bir Nav2 hız örneği değildir. |
| Clock eşlemesi ve uçtan uca gecikme sınırı | **BLOCKED** | Ham damgalar var; doğrulanmış domain/offset/hata modeli ve pre-write damgası yok. |
| Her adımda fizik öncesi/sonrası veri ve kayıp hesabı | **BLOCKED** | Aralıklı trace, ilk iki joint, quaternion/gerçek yazım kanıtı eksik. |
| Hareketli fren/konum-hız hata bounds'u | **BLOCKED** | Hiç ölçülmedi; StopEnvelope UNBOUNDED. |
| Physics/son writer arıza kapsamı kararı | **BLOCKED** | Bağımsız donanım freni yok; worker kaybı dışındaki ortak hata sınırı ayrı onaylanmalı. |

Braking bounds'un eksik olması **kalifiye hareket/duruş kabulünü** engeller.
İlk kalibrasyon deneyi bu bounds'u üretmeyi amaçlar; bu deney için tüm
bounds'un önceden var olduğu varsayılmaz. Önce ayrı deney yetkisi, kaynak/
telemetri, izolasyon ve açık fault-scope kapıları çözülmelidir. Donanım freni
bir simülasyon eklentisiyle varmış sayılmaz; simülasyon ve donanım kabulü ayrıdır.

## 5. T3C-2B için minimum, sıralı değişiklik önerisi

Bunlar **ÖNERİ / HENÜZ UYGULANMADI**, otomatik geçiş veya hareket izni değildir:

1. Tek robotu mevcut filo config'inden seçen, şemayla doğrulanan bağımsız
   opt-in deney profili; yeni DB/session/domain/partition, model/zemin/yük/
   footprint ve build hash'leri. Varsayılan config/GUI/launcher değişmez.
   Mevcut world/supervisor/Physics ve tek DiffDrive yeniden kullanılır.
2. Mevcut recorder/IPC'ye yalnız gözlem alanları: kaynak clock/domain/boot
   kimlikleri, gerçek command üretim/forward/verify damgaları, ayrı pre-write
   ve post-step sim/steady/dt/iteration; tüm joint kimlikleri, quaternion,
   frame ve readback-valid alanları. Bounded nonblocking trace sequence/drop
   hesabı; recorder yavaşlığı fiziği bloke etmez, eksik veri kabul edilmez.
3. Gerçek Nav2 hız üreticisi ile mevcut task/session/epoch/child/Path/permit
   bağının kalifiye edilmesi; publisher listesi yerine gerçek kaynak güveni
   ve yanlış yayıncı/eski context negatif erişim testleri. Mevcut FM rezervasyon
   ve sahipliği korunur; FM yeni bir per-wheel hız kontrolcüsü olmaz.
4. Bu kanıtlar ve hata kapsamı ayrı incelendikten sonra hareket deneyi için
   açık karar. **AuthorizedZero/split-zero hedeflerinin sınırı kaldırılmaz**;
   gelecekteki opt-in deney yolunun komut/lease/veto sözleşmesi ayrıca onaylanır.
   Ham Twist açmak, sıfır makrosunu kapatmak veya rearm eklemek geçiş yöntemi değildir.
5. Ancak bu kapılardan sonra ayrı 2B görevinde gerçek tek-robot hareket/fault
   ölçümleri; fizik ilerlemesi, kaynak kesimi, her adım gerçek hız ve duruş
   alanı/süresi karşılaştırılır. Kapsam ve tekrar matrisi belirlenir; veri
   kalifiye olana kadar StopInputs boş, envelope UNBOUNDED kalır. Hold/resume,
   release, rollover ve çoklu hareket bu önerinin otomatik uzantısı değildir.

## Regresyon, açık riskler ve teslim

**500 host PASS** (13 yeni test dahil), **200 ROS PASS**, mevcut sabit native
binary'lerle **2/2 CTest**, bridge **1/1 CTest**. Host/ROS sayıları örtüşür.
Yeni canlı Gazebo/motion testi **0**; 14/14 sonucu tarihsel kanıtın yeni offline
kontrolüdür. ROS negatif testlerinin invalid feedback-publisher uyarıları
ham loglarda korunur; fiziksel duruş kanıtı sayılmaz.

Tarihsel ACK/child metadata kaybının kesin nedeni hâlâ açık; 14/14 bunu
bütün koşullarda çözülmüş yapmaz. Kullanılmayan Nav2 full-overlay patch'inin
bozuk hunk sayımı korunur; aktif cleanup backport'u ayrı ve değişmemiştir.
ROS kaynak kimliği, clock alignment, trace boşlukları ve Physics/writer ortak
fault domain'i açık risklerdir. BOUNDED, APPLIED, fiziksel stop veya release
üretilmedi. 2A hazırlığı kendi kapsamında geçti; **T3C-2B başlatılmadı**.

Commit/push yalnız bu hazırlık dosyaları, testleri ve raporlarına aittir;
normal fast-forward ve uzak SHA doğrulaması teslimde yapılır.
