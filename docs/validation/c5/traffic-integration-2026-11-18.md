# C5 — Gerçek trafik entegrasyonu: güvenli bağımlılık aşamaları

18 Kasım 2026. Taban **da6f27a**. **PARTIAL; varsayılan demoya hazır değil.**
Native actuator girişinde sıfır komut doğrulaması ve gerçek Nav2 child/Path
gözlem bağı geliştirildi. Gerçek ExecuteTask → permit → actuator hareket
yetkisi → hold/resume → fiziksel release zinciri henüz tamamlanmadı. Hareket
yetkisi açılmadı; istenen hareketli kabul senaryoları geçirilmiş sayılmaz.
Commit/push yapılmadı. [Komut eki](traffic-integration-commands-2026-11-18.md) ·
[Ham kanıt](traffic-integration-2026-11-18/) ·
[Deney sözleşmesi](../../../docker/experiments/c5-b6b7/README.md) ·
[Mermaid](../../diagrams/src/traffic-native-zero.mmd) · [SVG](../../diagrams/svg/traffic-native-zero.svg).

## İncelenen mimari ve kalan bağlantılar

| Bileşen | Bulgu / durum |
|---|---|
| PeerRobotLayer | Mevcut deneysel geometri/güncellik kapıları korunur; diğer robotlar global/local costmap'te engeldir. Bu fiziksel duruş veya izin kanıtı değildir. |
| Executor → NavigateToPose | Gerçek child UUID `ClientGoalHandle.goal_id` içinde vardır; bazı loglar üst ExecuteTask UUID'sini gösterir. BT'nin FollowPath child'ı ve güncel Path bu üst handle'dan türetilemez. |
| B6B.1 / B6B.2 | Tek consumer/SQLite COMMIT ve geometrik conflict çekirdeği vardır. Movement yetkisi kapalı; aktif context rollover ve kalifiye release yoktur. |
| Yerel motion gate | Fake/sentetik sağlık ve stop tube ile daima sıfırdır. APPLIED metadata'sı gerçek actuator uygulaması değildir. |
| Hold/resume | Executor `_hold_uncertain` sahipliği tutar ve safety block kurar; bu normal trafik bekleme/devam protokolü değildir. Preemption/PREEMPTED yerine kullanılamaz. |
| Actuator | B6B.6 verifier test readback'indeydi. Bu çalışmada aynı doğrulama kavramları gerçek native callback'e taşındı; yalnız sıfır kabul edilir. |
| Fiziksel release | Gerçek terminal bile `RELEASE_THRESHOLDS_UNVERIFIED` ile reddedilir. Native watchdog flag'i, sıfır hedef veya costmap current bayrağı FREE üretmez. |

Mevcut Scheduler/öncelik/FIFO, Outbox, epoch/session, preemption ve STALE
eşikleri değişmedi. Paralel ürün trafik servisi kurulmadı. [Kaynak koruma kaydı](traffic-integration-2026-11-18/preservation.json)
önceki deneysel değişiklikleri ve mevcut performans düzeltmelerini ayırır.
Normal `scripts/start_demo.sh` mevcut C5-A/stock hız yolunu kullanmaya devam
eder; bu deneyin native alıcısı veya peer aktivasyonu ona eklenmedi. Önceki
normal demo park teması riski bu görevle kapatılmış sayılmaz.

## Aşama 1 — Gerçek native alıcı, hareket kapalı

**IMPLEMENTED / DOĞRULANDI, yalnız sıfır kapsamı.** Yeni B6B.7 build'i
B6B.5'in aynı DiffDrive/joint yazıcısını ve değişmeyen `Lease.hh` dosyasını
kullanır. Ayrı C++ sembolleri ve alias vardır; stock alias'ları bu build'de
dışa aktarılmaz. Varsayılan B6B.5 dalı iki eski CTest'i yeniden geçmiştir.

Native callback artık HMAC ile tam body byte'larını; receiver/source session,
artan sequence, değişmez context/permit generation ve receiver'ın monotonik
tek kullanımlık biletini denetler. Yanlış imza, eski sıra veya yanlış context
receipt'i yenilemez. İmzalı nonzero, timeout ve enable değişimi kilitler;
ağdan rearm yolu yoktur. Her iki native build'de actuator hedefi ve teker
hedefleri daima sıfırdır. Burada gerçek nonzero kapısı bulunmaz.

Provision dosyası owner-only ve aynı UID'ye ait olmalıdır; symlink kabul
edilmez. Gerçek test anahtarları `/run` altında 0600 dosyalardadır ve arşive
alınmadı. Bu, aynı UID/root'a karşı anahtar izolasyonu veya transport ACL
kalifikasyonu değildir. Doğrudan IGN yazısı **ulaştı ve native MAC kontrolünde
reddedildi**; transport erişimi engellenmiş gibi sunulmaz.

Son temiz dünyada üç gerçek robotun tek joint writer'ı bu native sıfır
sürücüydü. `/proc/.../maps` gerçek yüklenen binary'yi doğruladı. Negatif matris:

| Deneme | Gerçek gözlem |
|---|---|
| ROS ve IGN ham Twist / eski cmd_vel | Native sürücü aboneliği yok; authenticated receipt oluşmadı. |
| Yetkili sıfır üreticileri | Üç alıcı ACTIVE; her biri en az 8 kabul. ACTIVE hareket yetkisi değildir. |
| Doğrudan native IGN topic'ine yanlış MAC | Paket ulaştı, reddedildi; receipt değişmedi. |
| Üretici SIGKILL + yanlış MAC akışı | Native steady timeout; yanlış mesajlar lease'i yenilemedi. |
| İmzalı nonzero | Native `NONZERO_DISABLED`, BLOCKED_REARM; teker hedefi sıfır. |
| Komut bridge'i SIGKILL / restart | Fizik ve native durum okuyucusu çalışırken timeout; restart'tan gelen geçerli sıfır bile kilidi açmadı. |

Son matris **1.714 native örnekte** sıfır dışı joint hedefi görmedi.
Matris penceresindeki yatay fiziksel yer değiştirme 0 m; koşunun tamamında
örneklenen maksimum başlangıç yerleşmesi yaklaşık **1,59 × 10⁻⁷ m**.
Robotlar baştan duruyordu: bu ölçüm **hareketten frenleme, stop mesafesi veya
update-loop donmasına karşı bağımsız fail-safe kanıtı değildir**.
[Native matris](traffic-integration-2026-11-18/final/live/native-matrix/summary.json).

## Aşama 2 — Gerçek child UUID / Path kaydı, yetki kapalı

**IMPLEMENTED / DOĞRULANDI, component metadata kapsamı.** Mevcut `MovementGate`
kabul edilen child UUID'sini ve tüm serialized ROS Path byte'larının SHA-256
değerini aynı rezervasyon kimliğiyle kaydedebilir. Gerçek ClientGoalHandle,
FollowPath tipi ve beklenen action endpoint'i adaptörde denetlenir. Yanlış
UUID/Path eski isteği kapatır; yanlış terminal UUID'si yok sayılır, çelişen
terminal kaydı kapanır. Yeni prepare eski gözlemi taşımaz.

Bu gözlem APPLIED ACK değildir. `send` hâlâ False, physical_stop UNKNOWN ve
ownership_release false kalır. Varsayılan Executor bu yeni API'yi çağırmaz.

Native sıfır sürücüler altında gerçek Nav2 sunucularına yalnız **sıfır
uzunluklu** üç FollowPath gönderildi. Her iki pose güncel, tam damgalı TF'den
aynı poz/yönelimle alındı. Gerçek child sonuçları:

| Robot | Gerçek accepted child UUID | Gerçek terminal |
|---|---|---|
| Alpha | `849a12f4-271c-4e12-a2c6-765bd9631a9b` | SUCCEEDED (4) |
| Beta | `5ee7d449-e515-402e-9a6d-60ccb153c5ea` | SUCCEEDED (4) |
| Gamma | `756e31b2-ced7-4e9e-8af8-a3130fa6a46c` | SUCCEEDED (4) |

Üst atama ve COMMIT, ROS adapter/Outbox dispatcher kurulmayan ayrı SQLite
domain fixture'ıdır. **Gerçek ürün ExecuteTask üst eylemi gönderilmedi**;
bu üç sonuç taşıma görevlerinin COMPLETED olduğu veya ürün FM ile native
actuator arasında atomik permit uygulaması bulunduğu anlamına gelmez.
Fixture, mevcut aynı consumer/traffic kodunu kullanır; ikinci bir canlı ürün
Fleet Manager veya alternatif trafik sistemi değildir.

Her üç testte gerçek terminal sonrası release reddedildi; frame'i değişmiş
Path aynı child için kabul edilmedi ve eski byte'lar isteği tekrar açamadı.
[Child kanıtı](traffic-integration-2026-11-18/final/live/child-binding/summary.json).

## Aşama 3 — Peer TF sorgusu düzeltmesi

Önceki A2 kaydında da bulunan 19.917 dedicated-thread TF uyarısı incelendi.
Peer katmanının thread'i olmayan ROS Buffer wrapper'ı bekleme kontrolüne
giriyordu. Katman doğrudan **beklemesiz `tf2::BufferCore` lookup** kullanacak
şekilde düzeltildi. Thread varmış gibi bayrak ayarlanmadı; ölçüm zamanı,
frame/parent, source/receipt yaşı, duplicate ve stale hold değişmedi.

On native peer testi yeniden geçti. Son temiz dünyada TF thread uyarısı **0**;
10 s durağan probe'da altı costmap'in toplam 182 raporunun tümü current=true.
Bu bir hareketli TF kaybı veya yeni performans kabulü değildir.
[Peer özeti](traffic-integration-2026-11-18/final/peer-final-summary.json).

## Koşular, hatalar ve test sonucu

Tek aktif simülasyonla, ayrı domain/partition ve yalnız bu workspace kullanıldı.
Başlangıç reset/AMCL/Nav2/TF ve contact guard kapıları korunur.

| Koşu | Sonuç |
|---|---|
| `074546Z-9681b633ed35`, domain 205 | Bridge mapping'leri --ros-args sonuna eklenmişti; startup FAIL. Düzeltilip temiz reset yapıldı. |
| `074815Z-c76b8b0c621e`, domain 225 | Native ilk adımlar geçti; restart'taki ghost DDS subscriber kaydına güvenen test mesajı kayboldu. Matris FAIL; mesaj alıcıdan teyit edilene kadar tekrar edilerek test düzeltildi. |
| `075448Z-aaed8d4fc452`, domain 222 | Native matris ve üç gerçek child metadata testi geçti; eski Peer TF uyarısı vardı. |
| `080634Z-e136c7eaa9ae`, domain 210 | Son native matris, child testi ve peer probe geçti; TF thread uyarısı ve unsafe-contact kaydı yok. |

İlk C++ fixture JSON yazım hatası ve başarısız koşular arşivde korunur. İlk
startup haricindeki üç koşunun bütün alt süreçleri 0 ile kapandı. Sonuçlar:

- B6B.7 **2 CTest PASS**, içinde 13 schema/kimlik/nonzero vakası ve ek replay,
  timeout, duplicate-key, dosya izni/symlink, callback/target kontrolleri.
- B6B.5 regresyon **2 CTest PASS**; Peer katmanı **10 gtest PASS** (colcon 11
  sayısı CTest wrapper'ını da içerir).
- Son host seçki **252 PASS**, ROS tipi içeren native Python seçki **188 PASS**;
  skip yok. Tam repo suite ve önceki hareketli senaryolar yeniden koşulmadı.
- İki temiz native build aynı binary SHA-256 üretti:
  `00d6fb6687b32dfd3b475688a8c0fe7ee0455c76f67afaf6b8e8e9798b5a275f`.

## Hareketli kabul kapısı

İstenen altı senaryo için yeni trafik zinciriyle **HENÜZ TEST EDİLMEDİ**:
üç eşzamanlı taşıma; kesişme/karşılıklı dar koridor; hareketli park/şarj;
hareketli TF/iletişim kaybı; permit revoke → kontrollü stop → resume; üç görev
COMPLETED ve park. Önceki peer taşıma/park/şarj kayıtları tarihsel olarak
korunur; yeni native zincirin kabulü gibi sunulmaz. Bu çalışmadaki temas
kaydının yokluğu, hareketli çarpışma önleme kanıtı değildir.

Önce tamamlanması gerekenler: gerçek ExecuteTask üst bağlamından FollowPath'e
tek yaşam döngüsü; kimliği doğrulanmış gerçek sağlık/poz/TF/ObservationHealth
snapshot'ı; raw Nav2 hızının doğru child/context'e bağlanması; gerçek permit'in
native actuator'a atomik uygulanması; hız/yük/lokalizasyon belirsizliği ve
stop tube kalifikasyonu; actuator/bridge/gate kaybında hareketli stop; revoke,
retire ve fiziksel ayrılma kanıtıyla release; güvenli hold/resume ve context
rollover. Native test fixture'ının dosya context'i canlı FM permit'i değildir.

**ÖNERİ:** bu bağımlılıklar mevcut B6B bileşenleri üzerinde tamamlanmalı;
claim sahibi fiziksel release olmadan değişmemeli. Geçiş önceliği/koridor
beklemesi, timeout ile FREE veya ayrı Scheduler/preemption politikasıyla
taklit edilmemeli. Bu kapılar tamamlanmadan native sıfır inhibisyonu ve
varsayılan launcher izolasyonu kaldırılmamalıdır. **Demoya alınmaya hazır değil.**
