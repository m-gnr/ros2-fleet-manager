# C5-T3C-1A — Native işçi ayrımı ve bloke etmeyen sıfır veto

19 Kasım 2026 · Taban `cddeacb6f9622fd4f0dd5e891da2b4135c958b23`.
**DOĞRULANDI: bağımsız işçi/IPC ve son sıfır yazıcı kapsamı; deneysel,
varsayılan kapalı.** Hareketli frenleme, fiziksel duruş, hold/resume,
release ve donanım fail-safe kabulü verilmedi. Nonzero/rearm/rollover yoktur.

[Mimari inceleme](c5-t3c0-stop-architecture-2026-11-19.md) ·
[Komutlar](c5-t3c1a-native-worker-commands-2026-11-19.md) ·
[Ham kanıt ve manifest](c5-t3c1a-native-worker-2026-11-19/) ·
[Mermaid](../../diagrams/src/traffic-native-worker.mmd) ·
[SVG](../../diagrams/svg/traffic-native-worker.svg).
Kullanıcının T3C-1A talimatı süreç ayrımı/sıfır veto uygulamasını yetkilendirdi;
T3C-0'ın bütün sağlık ve hareketli kalibrasyon adımlarını yetkilendirmedi.

## Gerçekleştirilen ayrım

İncelemede mimariyi engelleyen bir çelişki bulunmadı. Mevcut B6B.7
doğrulaması ve B6B.5 Lease **değiştirilmeden** ayrı C++ işçisine alındı.
FM → gerçek ExecuteTask/FollowPath → NativeZeroLink → mevcut ROS/IGN String
bridge → native işçi zinciri korunur. FM hâlâ tek izin/rezervasyon otoritesi,
Executor RobotStatus otoritesi, Nav2 rota/hız üreticisidir.

| Parça | Son davranış |
|---|---|
| `worker.cc` | Gerçek `AuthorizedZero::Load/Receive/Tick/Snapshot`: HMAC, exact body, receiver session, sequence, permit/generation/context, bilet ve lease. JSON/kriptografi/transport callback'leri ve mutex ayrı süreçte. Ham Twist aboneliği yok. |
| Aynı `DiffDrive.cc`, `C5_SPLIT_ZERO_ONLY` kolu | Tek joint yazıcısı korunur. PreUpdate adımında en fazla bir sabit kayıt okunur; kilit/işçi bekleme veya JSON/HMAC yoktur. Geçerli kayıt dahil **her hedef sıfırdır**. UpdateVelocity de kesin sıfırdır. |
| `Ipc.hh` | 344-byte yanıt / 496-byte gözlem, nonblocking seqpacket. Supervisor boot token'ı, gerçek SCM_CREDENTIALS PID/UID, native session, context/body hash ve sıra denetlenir. Yanlış/tam olmayan/truncated kayıt kilitler. Alım/aktarım sayısı sınırlıdır. |
| Yerel süreler | Mevcut native fixture'ın `ticket_sec=0.2`, `lease_sec=0.25` değerleri kullanılır; onaylı ürün/STALE eşikleri değildir, değiştirilmedi. Deadline son yazıcının monotonik saatindedir. Heartbeat/report ilerlemesi komut lease'ini yenilemez; yeni command sequence gerekir. |
| Odometry | Mevcut DiffDrive hesabı aynı gerçek joint konumlarından üretilir. Bloklanabilen odometry/TF yayını işçiye taşınır. İşçi kaybı bu yayını da keser; fizik/kanıt kanalı bundan bağımsız çalışır. |
| `world.py` / `split-server` | Mevcut T3A dünya/TF/Nav2/bridge supervision'ı, config'den robotlar ve ayrı alt süreçler. Açık test Server API girişinde FD'ler korunur. Yeni Compose servisi veya trafik protokolü yoktur. |
| `physics.cc` | **Tek stock Physics** nesnesine Configure/Update yönlendirilir. Pozitif dt ve unpaused çağrı tamamlanınca sayaç artar. Engine algoritması veya joint komutu değiştirilmez; ikinci fizik sistemi değildir. |
| `split-recorder` | Ayrı salt okunur sink. Fizik öncesi seçilen hedef/context/komut hash'i, fizik sonrası gerçek joint/gövde hızı ve Physics sayacı farklı alanlardır. IPC trace gönderimi nonblocking; kayıp kanıt başarı sayılmaz. |

İlk permit/context öncesi `NO_COMMAND` bir hareket lease'i değildir. Soğuk
render nedeniyle süresi geçen başlangıç **gözlem** biletleri atılır; eski
ACTIVE yanıtı kabul edilmez. İlk gerçek context bağlandıktan sonra timeout,
replay, yanlış session/context veya native kapanma **kalıcı kapalı kilit**
üretir. Sonraki gözlem yayını kilidi/kabul sayısını açmaz. Supervisor otomatik
restart yapmaz; kontrollü restart yalnız negatif fixture talebidir.

İşçi native ACK'si hâlâ doğrulanmış zarfın kaydıdır; açıkça
`NATIVE_VERIFIER_PROCESS` etiketi taşır. İşçi joint readback veya native_health
üretmez. Son yazıcının sıfır seçimi ayrı kanaldadır; ACK **APPLIED, güncel
sağlık veya fiziksel stop** yapılmadı. FM COMMIT, Outbox, aktarım, native
doğrulama ve son seçim süreçler arasında atomik sayılmadı. Ayrı ACK kaydı ve
traffic Outbox'ın **PENDING** sözleşmesi korundu. Son yazıcı kapalıyken
doğrulayıcının bir zarfı doğrulaması fiziksel uygulama anlamına gelmez.

## Son testler

| Seçki | Sonuç |
|---|---|
| Mevcut host domain/Outbox/Executor/traffic/health regresyonu | **442 PASS**, 0 fail/skip |
| Humble typed ROS / integration seçkisi | **154 PASS**, 0 fail/skip |
| Yeni native IPC/veto CTest | **1 PASS**; bounded receive, gerçek yanlış-PID credential, bozuk/nonzero/NaN, eski sıra/bilet, context/session, command expiry, EOF, rewind ve başlangıç NO_COMMAND |
| Eski B6B.7 temiz native build | **3/3 PASS** |
| Eski B6B.5 temiz native build | **2/2 PASS** |
| Son izole Gazebo matrisi, CLI/kapanış dahil | **8/8 PASS** |
| Kalıcı kayıt / verifier / writer / Physics çapraz denetimi | **8/8 PASS** |

Seçkiler örtüşür; benzersiz test toplamı olarak toplanmaz. Tam depo suite'i
ve GUI/varsayılan demo çalıştırılmadı. ROS teardown'ında mevcut iki invalid
feedback-publisher uyarısı korundu; duruş/terminal kanıtı sayılmadı.

### Gerçek Physics ilerlemesi

Her koşu yeni Linux-local SQLite DB, native/session/boot, fiziksel reset ve
güncel readiness ile başladı. Güncel RobotStatus sonrasında trafik geometrisi
kuruldu; atanan robot Scheduler'dan alındı. Üç robotun fizik/trace verisi var;
her koşuda tek görev üzerinden gerçek permit doğrulandı. Görevlerin COMPLETED
olduğu veya üç hareketli görevin koordine edildiği iddia edilmez.

| Son koşu / domain | Gerçek atama | Physics: fault öncesi → fault sürerken | Son veto nedeni |
|---|---|---|---|
| worker-stop-final3 / 204 | Gamma | **1423 → 1506** | TIMEOUT |
| worker-kill-final3 / 205 | Alpha | **1497 → 1573** | TIMEOUT; yeni işçi açamadı |
| ipc-loss-final3 / 206 | Gamma | **1535 → 1607** | TIMEOUT |
| duplicate-final3 / 207 | Alpha | **1395 → 1427** | REPLAY |
| wrong-context-final3 / 208 | Alpha | **1310 → 1342** | CONTEXT |
| wrong-session-final3 / 209 | Alpha | **1455 → 1487** | SESSION |
| corrupt-final3 / 210 | Alpha | **1470 → 1503** | MALFORMED |
| delayed-final3 / 211 | Alpha | **1533 → 1618** | TIMEOUT |

SIGSTOP'ta Gamma işçi PID **30**, Gazebo PID **33** idi. `/proc/30/status`
fault sürerken **T (stopped)** kaydedildi; Physics sayacı ve sim zamanı
ilerledi. Gazebo PID'si durdurulmadı. SIGCONT sonrası kilit açılmadı.
SIGKILL koşusunda yeni işçi farklı PID ve native session aldı; son yazıcının
eski session/kilidi ve kabul sayısı değişmedi. Yeni PID'nin unlatched
alıcıya reddi native SCM_CREDENTIALS testinde de sınanır.

Sayaç dış `/clock` yayını veya işçi heartbeat'i değildir: tamamlanan
**stock Physics::Update (unpaused, dt>0)** çağrısı sayılır. Gerçek yüklenen
driver, observer, stock `libignition-gazebo6-physics-system.so.6.18.0` ve
DART `libignition-physics5-dartsim-plugin.so.5.4.0` mapping'leri her son
koşuda saklandı. Bu engine-internal alt adım/solver iteration sayacı değildir.
Gerçek Physics joint ve world velocity component'leri ayrıca okunur.

Her son koşuda `writer-committed-binding.json`, seçilen command hash/sıra,
native session ve context hash'ini gerçek FM transferi ve canlı doğrulanmış
native durumuyla eşler. Kaynak permit/child kararları Outbox byte'larıyla,
gerçek ExecuteTask atamasıyla ve ayrı native ACK ile denetlendi. Canlı probe
MAC doğruladı; anahtarsız offline denetim MAC'i yeniden doğruladığını iddia
etmez. [Çapraz denetim](c5-t3c1a-native-worker-2026-11-19/live-audit.json).

Son matrisin bütün kayıtlı pre-joint hedefleri sıfırdır. En büyük yatay
konum farkı **1.616 × 10⁻⁷ m** altında; robot-robot/robot-raf unsafe-contact
kaydı yoktur. Zemin desteği ve başlangıçtaki yerçekimi yerleşmesi bu temas
iddiasına dahil değildir. Fizik sonrası hızlar komut sıfırından türetilmedi.
**Bunlar duran robot testleridir; fren kapasitesi veya güvenli hareket
kabulü değildir.** Fiziksel release sekiz koşuda
`RELEASE_THRESHOLDS_UNVERIFIED` ile reddedildi.

Native build **a5**: Fortress 6.18.0 / Physics 5.4.0 / DART 6.12.1.
Gerçek kullanılan driver SHA-256:
`1b72963487f7b919c36974869ea2608501a7cec769fe7814762607bbee1624c4`.
Dokuz C++/header/CMake girdisi build kaydıyla tam eşleşir. Son fixture
hash'leri, paketler ve diğer binary hash'leri kanıttadır. Bilet/lease değerleri
ve kısa durağan ölçümler kalifiye frenleme/gecikme üst sınırı değildir.

## Korunan başarısız ve ara denemeler

- İlk native build: kurulu Fortress component header adları nedeniyle
  compile hatası. Düzeltilmiş temiz build/testler kaydedildi. Bir SHA toplama
  denemesi de `__pycache__` dizinini dosya saydığı için build başlamadan kaldı;
  dosya glob'ları düzeltildi, hiçbir dosya silinmedi.
- `worker-stop-a1`: ilk soğuk render gecikmesi IPC gözlem biletini aştı,
  NO_COMMAND iken kilit/odometry kaybı readiness'i engelledi. Koşu kontrollü
  kesildi; TF helper kapanışında force-kill kaydı var. Başarı sayılmadı.
  İlk gözlem ile bound komut lease'i ayrıldı; eski ACTIVE canlanması ayrıca
  test edildi. Hiçbir süre/STALE değeri uzatılmadı.
- `worker-stop-a2`: host paylaşımlı mount üzerinde canlı SQLite başlangıcı
  `no such table: main.tasks` ile kaldı. Kökeni bu kapsamda kalifiye edilmedi.
  Ürün store'u değişmedi; mevcut T3A fixture sözleşmesindeki Linux-local
  canlı DB ve sonradan SQLite backup kullanımına dönüldü.
- `worker-stop-a3` ve ilk sekiz final1 koşusu işlevsel/CLI olarak geçti;
  ancak stock Physics mapping filtresi sürümlü gerçek adı kaçırıyordu.
  İlk offline audit bu eksikte kaldı. Salt kayıt filtresi düzeltildi;
  bunlar son mapping kabulünün yerine konmadı.
- İkinci matrisin `duplicate-final2` koşusu işlevsel özet üretse de komut
  bridge'i kapanışta `free(): corrupted unsorted chunks` / exit **-6** verdi;
  **kabul dışı**. Fixture, manager/Executor/batarya üreticilerinden sonra
  native işçi abonelerini bridge'den önce kontrollü kapatacak şekilde
  düzeltildi. Physics/recorder bu sırada çalışır. Son sekiz koşu CLI ve
  bütün normal alt süreçler için exit 0; yalnız kasıtlı worker SIGKILL -9'dur.
  ros_gz/IGN heap sorununun genel kök nedeni giderilmiş sayılmaz; yalnız
  bu kapanış sırası doğrulandı. Önceki hatalar ve tam ham çıktılar korunur.

## İzolasyon, sınırlar ve T3C-1B

464 mevcut dokümantasyon dışı dosya ve önceki C5 doğrulama dizininin
**4332 dosyası** tabanla byte eşittir. Tek mevcut kaynak değişikliği
DiffDrive'ın açık compile koludur. B6B.5/B6B.7'nin etkin koşullu kaynak
metni tabanla eşittir; temiz native build'leri geçti.
[İzolasyon kaydı](c5-t3c1a-native-worker-2026-11-19/isolation.json).
Varsayılan GUI/launcher/config/IDL, Scheduler, Outbox, preemption, STALE,
T1/T2/T3A/T3B kaynak/kanıtları ve PeerRobotLayer aktivasyonu değişmedi.

Bağımsızlık yalnız **native işçi ↔ fizik yazıcısı** sınırındadır. Son
yazıcı/Physics/Gazebo/host takılması veya güvenilen yazıcının yanlış ama
sürekli komut üretmesi için bağımsız donanım freni yoktur. Nonblocking IPC
tek başına hard-real-time/WCET garantisi değildir. Supervisor negatif restart
için endpoint kopyası tutar; bu nedenle kayıp EOF yerine deadline ile
görülebilir. Gerçek EOF ve yanlış sender PID ayrıca native testtedir.
Ortak UID/root ve test anahtar alanına karşı erişim izolasyonu kalifiye değil.

**1B için sıfır-komutlu başlangıç noktası hazır; varsayılan entegrasyon veya
hareketli deney için hazır değildir.** Kalan işler:

1. T3B sağlık çıktılarının mevcut gate/son veto kapatma zincirine bağlanması;
   TF/odometry/AMCL/ObservationHealth/lifecycle yaş ve gerçek kaynak kimliği.
2. Son yazıcı seçimi/readback'inin yetkilendirilmiş bağla gözlenmesi; native
   doğrulama ACK'siyle fiziksel uygulamayı karıştırmadan mevcut FM zincirine
   taşıma. Bu açık tanısal trace fiziksel APPLIED kanıtı değildir.
3. IPC/OS/anahtar rollerinin erişim ayrımı, final writer güven sınırı ve
   saat/gecikme bütçelerinin kalifikasyonu. Engine/bridge farklı build veya
   farklı kapanış sırası bu kabulden türetilmez.
4. [T3C planındaki](c5-t3c-braking-plan-2026-11-18.md) fren/ivme, gecikme,
   hız/konum hata ve marj ölçümleri. StopEnvelope fiziksel bounds eksikliğinde
   **UNBOUNDED** kalır. Hareketli ölçüm ayrı açık kapsam/yetki ister.

Hold/resume, fiziksel release, nonzero rearm/rollover ve çoklu hareketli
robot/park/şarj kabulü bu çalışmanın sonucu değildir.
