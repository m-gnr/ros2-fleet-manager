# C5-T3B — Gerçek sağlık gözlemi ve duruş zarfı altyapısı

18 Kasım 2026. Taban **e4b04ad6a4fc79a485b58f747cb0b557fd58aaa9**.
**Bağımsız T3B altyapı kapsamı DOĞRULANDI; deneysel ve varsayılan kapalı.**
Gerçek Gazebo/ROS kaynaklarının kısıtlayıcı değerlendirmesi, imzalı native
readback ve koşullu duruş hesabı test edildi. **Kalifiye fiziksel frenleme,
hareket güvenliği, hold/resume veya release kabulü verilmedi.**

[Komutlar](c5-t3b-health-stop-commands-2026-11-18.md) ·
[Ham kanıt/manifest](c5-t3b-health-stop-2026-11-18/) ·
[Mevcut B6B.3 tasarımına ek](../../design/c5-b6b3-traffic-motion-gate.md#18-kasım-c5-t3b-eki--gerçek-gözlem-ve-koşullu-duruş-hesabı) ·
[T3C önkoşul/test planı](c5-t3c-braking-plan-2026-11-18.md) ·
[Mermaid](../../diagrams/src/traffic-health-stop.mmd) · [SVG](../../diagrams/svg/traffic-health-stop.svg).

## Mimari inceleme ve gerçek kaynaklar

T1'in PeerRobotLayer'ı, T2'nin gerçek ExecuteTask→NavigateToPose→FollowPath
UUID/Path bağı ve T3A'nın COMMIT/Outbox→native doğrulama→ayrı ACK zinciri
korundu. Yeni trafik servisi, izin protokolü veya fiziksel robot durum
makinesi kurulmadı. RobotStatus/Executor otoritesi ve tek consumer/SQLite
sahipliği değişmedi. Sağlık probe'u yalnız açık izole fixture'da kurulur;
kalıcı kaynakları salt okunur okur ve hiçbir permit/ACK/claim yazmaz.

İnceleme şu boşlukları doğruladı:

- RobotStatus session/epoch/faz/poz taşır; hız ve lokalizasyon covariance'si
  ayrı kaynaklardadır. Odometry'nin bildirilen hızı teker kinematiği
  tahminidir; bağımsız kalibre gövde hız sınırı değildir.
- TF çözümü poz/yönelim tahminidir. Gerçek odometry damgasındaki lookup,
  frame, kaynak damgası ve alım yaşı gerekir; son TF veya başlangıç pozu
  ölçüm yerine konamaz. AMCL covariance istatistiktir; kesin hata sınırı
  veya fiziksel doğruluk kanıtı değildir.
- Nav2 lifecycle ACTIVE, controller/sensör zincirinin bütün sağlık kanıtı
  değildir. Mevcut ObservationHealth gerçek costmap buffer kullanımını
  ayrıca anlatır; onun ve LiDAR'ın yerine yeni otorite kurulmadı.
- T3A ACK'si son doğrulanmış komuta ilişkindir; anlık sağlık veya duruş
  değildir. Mevcut native status dışındaki joint alanları ayrı bağlanmadan
  imzalı sağlık sayılmamalıdır.
- DWB'nin config'deki `0,25 m/s`, `0,8 rad/s`, `-2,5 m/s²`, `-3,2 rad/s²`
  ve smoother limitleri komut ayarlarıdır; ölçülmüş minimum fren kapasitesi
  değildir. Profilde `motion_envelope: null` kalır.
- Aynı native update döngüsündeki watchdog, o döngü tamamen durunca
  çalışamaz. Dış gözlemci arızayı görse bile bu bağımsız fiziksel fren değildir.

## Uygulanan dar kapsam

| Bileşen | Son davranış |
|---|---|
| `domain/robot_health.py` | Kaynak stamp/alım yaşı, frame/quaternion, covariance PSD, lifecycle, native imza/sıra, session/epoch/context ve committed komut eşleşmesi. Invalid kaynak diğer kaynakları gizlemez. Replayed ölçüm yaş yenilemez; kapanmış context/permit canlanmaz. |
| `adapters/robot_health.py` | Gerçek typed ROS aboneleri, ölçüm anında TF lookup ve gerçek GetState RPC; salt okunur FM/T2/T3A bağlam sağlayıcısı. Kaynaklar ve değerlendirmeler ayrı ham loglarda. |
| Native B6B.7 | Gerçek UpdateVelocity/joint component readback'inden `native_health`; ayrı `C5_NATIVE_ZERO_HEALTH_V1` MAC domain'i. İçinde T3A native_status ve update sayacı bulunur. Command/ACK wire'ı, HMAC/session/sequence/generation ve zero-only sınırı korunur. |
| B6B.7 gözlem yükü | Yalnız açık `health_period_sec` alanıyla, mevcut `timer_period_sec` periyodunda sağlık yayını. Eski T3A provision'ında kapalı. Normal native status/komut akışı devam eder; legacy status sağlık yaşını yenilemez. Lifecycle sorgu sıklığı mevcut gözlem bütçeleriyle sınırlıdır. |
| Latest readback | NativeZeroLink/probe/fixture readback history=1; eski bilet kuyruğunu tüketmek yerine en güncel örnek. Permit/envelope retry kanalı değişmez. Lease/bilet/ACK/STALE süresi uzatılmaz. |
| `domain/stop_envelope.py` | Mevcut B6B sweep/union geometry ile koşullu model, rezervasyon kapsaması ve iki peer'in göreli alanı. Kalibrasyon eksikse sonlu tüp üretmez. |
| İzole fixture | T3A koşucusunda varsayılan None hook'ları; gerçek ölçümü damgalamadan ileten ROS odometry bağlantısı, TF helper/AMCL/Native process fault'ları. İlk admission güncel READY'yi sınırlı süre bekler; restart kapısını açmaz. Üreticiler transport'tan önce kapanır. |

`measured` gerçek ROS/API/readback bildirimlerini, `derived` hız normu,
yaw ve covariance sigma hesaplarını gösterir. TF lookup çıktısı birleştirilmiş
lokalizasyon tahminidir; fiziksel ground truth olarak sunulmaz. Raw TF edge'leri,
odom/AMCL bildirimleri ve orijinal stamp'ler ayrıca saklanır. Gezegen/saatler
arası monotonik değerler güvenlik gecikmesi olarak çıkarılmadı.

Kurulu Humble `_take_subscription` callback'e yalnız mesajı geçirir.
Bu nedenle graph endpoint/GID kümesi **GRAPH_SNAPSHOT_ONLY**; mesajın
gerçek yayıncı kimliği **UNKNOWN** tutulur. Task/epoch ile ROS kaynağı
receipt association seviyesinde ilişkilidir. Native MAC, ortak FM/native
fixture güven alanında doğrulanır; anahtar sahibi süreç/UID ayrımı veya
SROS/OS izolasyonu kalifiye değildir. Sahte kaynak kimliği üretilmedi.

## Duruş hesabı ve eksik fiziksel bounds

Mevcut Nav2 yarıçapı **0,30 m**; generated SDF'deki bütün collision/sensör
parçalarının bu çevreleyen küre içinde kaldığı mevcut analitik yardımcıyla
denetlendi. Gerçek link kütleleri, driver ayarları, yüzey/friction öğeleri,
DWB ve smoother değerleri `physical-config-inventory.json` dosyalarındadır.
Bunlar fren kalibrasyonu olarak kullanılmadı.

Koşullu hesap reaksiyon sırasında ivmelenmeyi ve sonra minimum frenlemeyi
ayrı kapsar: `T=t_detect+t_compute+t_comm+t_actuator`,
`v1=(|v_obs|+e_v)+a_max*T`,
`d=(|v_obs|+e_v)*T+a_max*T²/2+v1²/(2*b_min)`.
Açısal karşılığı ve duruş süresi ayrıca hesaplanır. Footprint dairesi tüm
yaw'ları kapsar; konum hata payı ve marj genişletir. Dönüş iki kez sayılmaz.
İki robotun alanları bağımsız genişletilir; karşı tarafın durduğu veya yol
verdiği varsayılmaz. B6B birleşim kapsaması aradaki boşlukları atlamaz.

Fiziksel fren/ivme, algılama/hesaplama/iletişim/actuator gecikme üst sınırları,
konum/hız hata bounds'u ve marj ölçülmemiştir. Gerçek koşular bu nedenle
**UNBOUNDED / tube=None / qualified=false**, rezervasyon için
**UNKNOWN_STOP_TUBE**, peer'ler için **UNKNOWN_RELATIVE_OCCUPANCY** döndürür.
Gözlenen hız sıfır olsa da bu eksikler kapanmaz. Unit fixture'ındaki açık
sayısal girdilerle üretilen sonlu alan bile **CONDITIONAL_CANDIDATE** kalır;
evidence hash'i kendi başına kalifikasyon değildir.

Hiçbir sağlık sonucu `movement_eligible=true` üretmez. Fiziksel stop UNKNOWN,
ownership_release false kalır. Mevcut TrafficCore release reddi ve kaynak
sahipliği korunur; ACK/APPLIED/fiziksel duruş birbirine çevrilmez.

## Son doğrulama

| Seçki | Sonuç |
|---|---|
| Geniş host regresyonu | **442 PASS, 0 FAIL, 0 SKIP** |
| Humble typed ROS / integration seçkisi | **154 PASS, 0 FAIL, 0 SKIP** |
| Temiz son B6B.7 native build / CTest | **3 PASS**; authorization, actual callback/target, live-context/health cadence |
| B6B.5 sıfır native regresyonu | **2 PASS**; değişmeyen Lease, zero-target davranışı |
| Son seçilmiş izole Gazebo matrisi | **8/8 PASS**, CLI ve kontrollü teardown dahil |
| Ham/kalıcı kayıt denetimi | Sekiz koşuda integrity/Outbox/gerçek atama/Path/native health byte/ACK eşleşmesi, sıfır hedef ve release reddi geçti |

Seçkiler örtüşür; tek benzersiz toplam olarak toplanmaz. Tam depo suite'i
çalıştırılmadı. ROS test teardown'ındaki mevcut invalid feedback publisher /
unresolved ownership uyarıları loglarda tutuldu; duruş/terminal başarısı
sayılmadı. Typed/component fixture'lar sentetiktir; fiziksel kaynak kanıtı
olarak yalnız aşağıdaki gerçek Gazebo/ROS koşuları kullanılır.

### Gerçek süreçler ve son matrix

Tek Gazebo, ayrı domain/partition, yeni DB/receiver/session, gerçek reset ve
AMCL/Nav2/TF readiness kullanıldı. Gerçek Scheduler ataması izlenir; görev
etiketi `t3a-robot_alpha` olsa bile robot sabit değildir. Üç robotun sağlık
kaynakları toplandı; görevli olarak Alpha ve Beta gözlendi. Gamma'nın bu
matrix'te hareketli/permitli görevi kabul edilmiş sayılmaz.

| Koşu / domain | Gerçek atama | Sonuç / native örnekleri A-B-G |
|---|---|---|
| replan-a5 / 220 | Alpha | Gerçek Path/controller değişimi, eski context BLOCKED, gerçek native revoke ACK; **390-381-358** |
| fm-loss-a5 / 221 | Beta | Gerçek FM SIGKILL, native TIMED_OUT, sağlık uygunsuz; aynı DB restart reddi; **230-222-197** |
| bridge-loss-a3 / 222 | Alpha | Command bridge SIGKILL, timeout, restart + eski paket BLOCKED_REARM; **630-605-594** |
| negative-a1 / 223 | Beta | Yanlış imza/session/epoch/generation/child/Path, duplicate ve nonzero reddi; **377-362-347** |
| update-freeze-a3 / 224 | Beta | Mapping'i doğrulanmış native Gazebo PID SIGSTOP; readback yaşlanması; resume sonrası BLOCKED_REARM; **421-404-390** |
| sensor-loss-a3 / 228 | Beta | Gerçek odometry bağlantısı, TF helper ve AMCL gecikmeleri ayrı ayrı algılandı; **1024-984-951** |
| controller-inactive-a2 / 229 | Beta | Gerçek controller lifecycle deactivation, ACTIVE dışı durum algılandı; **226-204-198** |
| executor-loss-a2 / 230 | Alpha | Gerçek Executor SIGKILL, native TIMED_OUT; yeni Executor bloklu, FM session fence; **613-589-573** |

V5 ve V6 arasında sağlık/native/hesap algoritmaları birebir aynıdır;
V6 yalnız fixture PID seçimi ve producer-before-bridge kapanışını düzeltir.
[Hash karşılaştırması](c5-t3b-health-stop-2026-11-18/matrix-version-compatibility.json).
Son native kitaplık SHA-256:
`4237efaf5f454bfde0e236969fcd02b2ce0cdec0aa12d763499d3699e84ec6bb`.
Her dünyada gerçek `/proc/.../maps` kaydı alınır; dosya adı/SDF beyanı tek
kanıt sayılmaz. Stock ham Twist girişi açılmadı.

Sensör koşusunda her kesim öncesi ilgili kaynak günceldi. Kesimde son kabul
edilen kaynağın yerel alım yaşı odometry için **1,222 s**, TF için **1,232 s**,
AMCL için **1,060 s** oldu; mevcut bütçeler aşıldı ve veri uygunsuz kaldı.
Bunlar tek koşu gözlemleridir; arıza→frenleme veya maksimum gecikme bounds'u
değildir. Native freeze yaklaşık **0,603 s** sürdü; son sağlık örneği
**0,705 s** yaşındaydı. Cached health o anda NO_COMMAND taşıyordu; gerçek FM
ACK ve sağlık snapshot'ının anlık aynı durum olduğu varsayılmadı. Önceki
ara freeze-a2'de cached ACTIVE de gözlendi. İkisi de stale/bağlam uygunsuz
olduğunda hareket veya fiziksel duruş kanıtı değildir.

Her son koşuda committed komuta bağlı imzalı sağlık readback'i gözlendi.
Offline audit sırasıyla FM/bridge/replan/negative/freeze/sensor/controller/
Executor için **13/60/27/26/38/86/19/63** farklı readback'i bilinen gerçek
transfer/hash/session/generation ile eşledi. Native MAC'ler canlı verifier'da
özel fixture anahtarıyla kontrol edildi; anahtarsız offline audit yalnız
packet byte/bağ tutarlılığını yeniden denetler.
[Denetim](c5-t3b-health-stop-2026-11-18/live-audit.json).

### Fiziksel gözlem ve watchdog sınırı

Sekiz koşunun kaydedilmiş native linear/angular/joint hedefleri sıfırdı.
Gözlenen en büyük yatay poz farkı **4,248 × 10⁻¹¹ m** altında; 1 mm durağan
fixture sınırının altında kaldı. Mevcut guard'da **UNSAFE_CONTACT / robot-robot veya
robot-raf teması yok**; zemin destek teması hariçtir. Bu, başlangıçtan duran
dünyanın örneklenmiş gözlemidir. Hareketli fren, park/şarj dönüşü, dar koridor
ve üç COMPLETED görevin güvenliği olarak sunulmaz.

Native update/process freeze fiziği de dondurur. Aynı süreçteki watchdog
o aralıkta çalışamaz; dış observer stale görse de gerçek bağımsız fren yoktur.
Loop-only stall, process ölümü sırasında hâlâ ilerleyen fizik ve donanım
deadman davranışı bu aşamada kalifiye edilmedi. Native body'nin sıfır hedefi,
anlık joint/gövde hızı ve fiziksel stop ayrı iddialardır.

Normal son alt süreçler 0 ile kapandı; yalnız planlı SIGKILL -9 ve aynı DB
manager restart'ı 1 beklenir. V6 transport wrapper'ı hem pasif bağlantı hem
TF helper için ayrı exit 0 kaydı tutar. Failed/forced shutdown kabul edilmez.
Son durumda deney container'ı kalmadı; başka kullanıcı/worktree sürecine
dokunulmadı.

## Korunan başarısız denemeler ve aşama sonuçları

Hiçbir başarısız kayıt silinmedi; PASS özeti bulunan fakat CLI/teardown
başarısız koşular son matrix'e katılmadı. Ham kayıtlar ve orijinal byte
hash'leri [arşivde](c5-t3b-health-stop-2026-11-18/original-byte-sha256.json).

- İlk unit fixture'ında native_health dict/string biçim hatası **5 FAIL /
  52 PASS** verdi; yalnız sentetik fixture düzeltildi.
- İlk ROS domain 241 port hatası; sonraki iki ROS denemesinde Humble'ın
  MessageInfo'yu callback'e vermemesi yakalandı. Kaynak GID'si uydurmak
  yerine graph kanıtı ayrı ve unqualified tutuldu. Daha sonraki negative
  AMCL fixture'ının QoS uyumsuzluğu da fail olarak korundu, publisher gerçek
  transient-local sözleşmeye uyarlandı.
- İlk canlı freeze-a1, NumPy covariance tipleri ve tek geniş try bloğunun
  native/Executor alanlarını gizlemesi nedeniyle doğrulamada kaldı. Sayısal
  değer değiştirilmeden float aktarımı ve kaynak başına hata izolasyonu
  eklendi. Aynı zaman damgalı yeni status_seq, metadata olarak ayrı ele alındı.
- FM-loss-a1/a2 gerçek arıza enjeksiyonuna ulaşmadan readiness düşüşüyle
  kabulü reddetti. İlkinde ek bridge shutdown abort'u da vardı. Initial
  fixture güncel READY'yi bounded bekler; historical READY, eski DB veya
  restart blokajı bypass edilmedi. Eşzamanlı ROS yükü ilk denemede vardı;
  tek başına neden olduğu iddia edilmez.
- Replan-a1/a2 ve gözlemcisiz baseline-a1 beklenen revoke ACK'sine ulaşamadı;
  fail-closed timeout oldu. Sağlık payload'ı tek neden sayılamadı. Native
  gözlem cadence'i profile bağlandı; eski readback/bilet kuyruğu yerine
  history=1 kullanıldı. Sonra baseline-a2 ve replan-a3/a4/a5 işlevsel olarak
  geçti. Süreler veya imza/context kontrolleri gevşetilmedi.
- Bridge-loss-a2 ve replan-a4 özetleri işlevsel PASS idi fakat ek C++
  odometry bridge'i shutdown'da abort/segfault verdi; **kabul edilmedi**.
  Sıra düzeltmesi tek başına yetmedi. İkinci C++ bridge kaldırılıp aynı gerçek
  odometriyi değişmeden ileten ROS fault bağlantısı kullanıldı. Upstream
  heap hatasının tam kök nedeni/uzun süre kalifikasyonu yapılmış sayılmaz.
- Sensor-loss-a2, wrapper argv'sinin de TF PID aramasına eşleşmesiyle
  durdu; yanlış PID'ye sinyal gitmedi. Ayrıca command bridge shutdown abort'u
  oldu. Manifest'in gerçek alt PID'si seçildi; bütün sıfır üreticileri
  transport'tan önce durduruldu. Son sensor/controller/Executor koşuları
  ve bağımsız owned-process cleanup testi geçti.

Gerçek AMCL örneklerinin bir kısmı sıkı PSD kontrolünden geçmedi. Örneğin
replan-a5 Alpha'da xx **−4,885×10⁻¹³ m²**, yaw varyansı
**−1,332×10⁻¹⁵ rad²** raporlandı. Bunlar sıfıra clamp edilmedi, güvenilir
hata bounds'u sayılmadı. Sayısal yuvarlama olasılığı kesin kök neden diye
sunulmaz. T3C'de ölçüm/numerik model ve fiziksel hata kalifikasyonu gerekir.

## Varsayılan koruma ve T3C'ye devir

**166 mevcut varsayılan dosya** tabanla byte eşit: frontend/visualizer,
launcher/config/IDL, ürün Executor node/safety constants, Scheduler/core,
Outbox/persistence, PeerRobotLayer/BT observer ve Lease dahil.
[Koruma](c5-t3b-health-stop-2026-11-18/default-isolation.json).
NativeZeroLink yalnız açık fixture'da kurulur; QoS düzeltmesi onu ürün
launcher'ına taşımaz. Ortak DiffDrive health çağrısı yalnız deneysel
`C5_AUTH_ZERO_ONLY` kolundadır; normal B6B.5 regresyonu ayrıca geçti.
Varsayılan GUI/demo çalışması yeniden başlatılmadı; source/API koruması
canlı GUI testi gibi sunulmaz. T1/T2/T3A'nın dört manifest'i birebir korundu.

**T3C planı hazır; gerçek hareket veya varsayılan entegrasyon hazır değil.**
Başlıca kapılar: kalibre fren/ivme/gecikme/hata/marj bounds'u; kaynak kimliği
ve health→yerel veto/actuator bağının kalifikasyonu; aynı loop/process dışında
gerçek bağımsız fail-safe; load/clock/queued veri ve değişen context altında
ölçümler; ayrı hold/resume ve fiziksel release kabulü. Kaynakları zorla FREE
yapmak veya nonzero/rearm açmak bu teslimin parçası değildir.

Kabul yalnız bu sınırlı altyapı ve durağan fault kapsamındadır. Commit/normal
FF push, kullanıcının T3B talimatındaki yetkiyle bu kontroller geçtikten sonra
yapılır; commit/uzak SHA ve temiz ağaç sonucu ayrıca bildirilir.
