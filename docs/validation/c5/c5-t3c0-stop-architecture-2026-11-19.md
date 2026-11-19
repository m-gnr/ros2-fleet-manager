# C5-T3C-0 — Hareketli duruş için mimari inceleme

19 Kasım 2026 · Başlangıç: `7093931d6da453200a297909475b6d431d9aa730`.
**Statik bulgular DOĞRULANDI; aşağıdaki mimari ÖNERİ / uygulaması ve hareketli
duruş HENÜZ TEST EDİLMEDİ.** Mimari öneri kullanıcı onayı bekler; bu kayıt
nonzero, T3C-1 uygulaması veya ürün entegrasyonu yetkisi vermez.

Dayanak: [T3B sonuçları](c5-t3b-health-stop-2026-11-18.md),
[T3C ölçüm planı](c5-t3c-braking-plan-2026-11-18.md),
[B6B.3 mevcut tasarımı](../../design/c5-b6b3-traffic-motion-gate.md).
T1/T2/T3A/T3B kaynakları, kararları ve ham kanıtları korunmuştur.

## 1. Mevcut zincir ve kritik sınır

FM COMMIT/Outbox → ExecuteTask/gerçek FollowPath UUID–Path bağı → Executor
NativeZeroLink → bridge → B6B.7 `AuthorizedZero` → DiffDrive `PreUpdate`
→ `JointVelocityCmd` → Physics/DART akışı vardır. **Bugün tamamı yalnız
sıfır hedeflidir.** Native ACK, committed body ile eşleştirilen alıcı
doğrulama kaydıdır; fiziksel uygulama, anlık sağlık, duruş veya release
değildir. COMMIT, aktarım ve alıcı doğrulaması süreçler arasında atomik
değildir. Outbox PENDING ve ayrı ACK kaydı korunur. RobotStatus fiziksel
durum otoritesidir.

| Mevcut bileşen | Güçlü yön / açık sınır |
|---|---|
| [AuthorizedZero](../../../docker/experiments/c5-b6b7/AuthorizedZero.hh), [Lease](../../../docker/experiments/c5-b6b5/Lease.hh) | HMAC, tam body, receiver session, sequence, tek kullanımlık yerel bilet, permit/context ve yerel süre kontrolü; timeout/revoke/rewind kilitlidir. Fakat kontrol ancak callback/Tick çalışırsa yürür. |
| [DiffDrive](../../../docker/experiments/c5-b6b5/DiffDrive.cc) | Tek deneysel joint yazıcısı, ham Twist aboneliği yok, PreUpdate ve UpdateVelocity sıfır sınırı. Transport callback'i, PreUpdate ve PostUpdate aynı mutex'i kullanır; kilitlenme fizik ilerlemesini de engelleyebilir. Ayrı actuator OS süreci değildir. |
| [HealthWindow](../../../backend/fleet_manager/domain/robot_health.py), ROS adapter | Gerçek kaynak stamp/alım yaşı, frame, covariance, lifecycle, imzalı native readback ve committed context kontrolü var. Salt okunur; actuator veto bağlantısı yok. ROS graph kimliği mesaj kimliği değildir; `movement_eligible=false` kalır. |
| [StopEnvelope](../../../backend/fleet_manager/domain/stop_envelope.py) | Gecikme, reaksiyon ivmesi, fren, hata/footprint ve iki robotun alanını mevcut B6B geometriyle kapsar. Ölçülmeyen bounds nedeniyle gerçek çıktı UNBOUNDED; rezervasyonu değiştirmez. |
| Nav2 / Executor | Controller/smoother komut üretir; Executor iptalde sıfır yayımlar ve terminal+odometry teyidi arar. Bu süreçler/transport yoksa bu duruş yolu da yoktur. Smoother timeout'u çalışan timer/publisher'a bağımlıdır; actuator fail-safe değildir. [Humble kaynak](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_velocity_smoother/src/velocity_smoother.cpp#L228). |
| TF / odometry / AMCL / PeerRobotLayer | Konum/tahmin ve bağımsız LiDAR algısı korunur. Peer katmanı eski işgali tutup `current=false` olabilir; bu fiziksel fren değildir. AMCL covariance kesin hata sınırı değildir. |

Fortress 6.18.0'da PreUpdate/Update çağrıları sıralı; PostUpdate işçileri
bariyerle beklenir. Dolayısıyla native callback takılması sonraki fizik
adımını engelleyebilir. Bütün Gazebo PID'sini durdurmak/öldürmek aynı
süreçteki fiziği de durdurur; “fizik ilerlerken actuator süreci öldü” deneyi
bugünkü yerleşimde mümkün değildir. Bu, kaynak kodundan çıkarımdır;
yeni canlı fault testi yapılmadı. [SimulationRunner: 470–523](https://github.com/gazebosim/gz-sim/blob/b90cd2c41a193102d6951857c2d83e13f59bb64b/src/SimulationRunner.cc#L470).

Önemli mevcut koruma: Physics önce komutları tüketir, fizik adımını yürütür,
sonra `JointVelocityCmd` elemanlarını sıfırlar. Bileşen korunur ve alternatif
kuvvet/reset yoksa yazıcının sessizce komut üretmemesi sonraki tüketimde
sıfır hedefe gider; bunu yeniden yazan ikinci plugin gerekmez. Kuvvet komutu
hız komutundan önceliklidir. **Sıfır hedef, gövdenin durması değildir.**
[Physics: 763–788, 1814–1868, 2883–2888](https://github.com/gazebosim/gz-sim/blob/b90cd2c41a193102d6951857c2d83e13f59bb64b/src/systems/physics/Physics.cc#L763).

T3B native health, joint command bileşenlerini **PostUpdate'te, Physics'in
sıfırlamasından sonra** okur. Sıfır-only kod/test sonucu geçerlidir; ileride
bu örnekten nonzero'nun fizik öncesi tüketildiği veya fren uygulandığı
çıkarılamaz. Tüketim öncesi komut ve fizik sonrası gerçek hız ayrı izlenmelidir.

## 2. Alternatifler

| Yaklaşım | İzolasyon / test edilebilirlik | Karmaşıklık ve tercih |
|---|---|---|
| ROS sıfır publisher'ı, Nav2 cancel/smoother, aynı native loop'a ek timer | FM kaybında yardımcı; bridge/mutex/loop kaybında son joint'e ulaşamaz. | En az değişiklik; bağımsız çözüm olarak yetersiz. Mevcut ikincil yollar korunur. |
| Aynı Gazebo'da ikinci watchdog/joint writer | Aynı süreç/scheduler; iki writer sırası ve kuvvet/hız önceliği yarışır. | Küçük görünür; bağımsızlık sağlamaz, önerilmiyor. |
| **Native işçisi ayrı süreç + mevcut tek fizik yazıcısında bloke etmeyen son veto** | İşçi kill/freeze olurken fizik ve son veto çalışabilir. Yerel mailbox kaybı doğrudan sınanabilir. | **Önerilen en küçük yeterli süreç ayrımı.** DiffDrive/Physics ve B6B protokolü yeniden kullanılır; stock Physics fork'u gerektirmez. |
| Physics tüketim noktasına özel engine/Physics yaması | Writer'ın hatalı biçimde sürekli yazmasını ayrıca sınırlayabilir; Physics/Gazebo çökmesine bağımsız değildir. | Engine sürümü/build bakımı ve güvenilen kod alanı büyür. İlk tercih değil; daha güçlü hata modeli istenirse ayrı karar gerekir. |
| Gazebo dışı supervisor ile pause/kill; gerçek donanım fren kontrolcüsü | İlki yalnız deney containment'ı; ikincisi fiziksel motor enerjisini gerçekten bağımsız kesebilir. | Pause/kill fren kabulü değildir. Donanım yolu bu simülasyonun uygulama kapsamı dışındadır. |

## 3. Önerilen sınır: aynı actuator'ın ayrılması

Bu öneri yeni trafik servisi/rota kontrolcüsü değildir. FM tek rezervasyon
otoritesi, Nav2 tek rota/hız üreticisi kalır. Üç servisli hedef değişmez;
işçi mevcut simulation servisi içinde supervisor'ın config'den ürettiği
alt süreçtir, robot başına Compose servisi değildir.

1. Mevcut native doğrulama/context işini ayrı **işçi sürecine** taşı;
   `AuthorizedZero`/Lease mantığını ve T2/T3A değişmez komut bağını yeniden
   kullan. ROS/IGN, JSON/HMAC, sağlık birleştirme ve bloklanabilir yayın/log
   işi fizik callback'inde tutulmasın. Mevcut B6B.7 sıfır sürücüsü referans
   olarak korunsun; yeni yerleşim yalnız açık deney fixture'ında kurulsun.
2. Gazebo'da mevcut DiffDrive'ın **tek joint yazıcısı** kalsın. PreUpdate,
   işçinin mutex'ini/yanıtını beklemeden tam snapshot alabilsin; sınırlı
   okuma başarısızsa sıfır seçsin. PostUpdate de dış işçiyi beklemesin.
   Latest-value mailbox kuyruğu geçmiş heartbeat'leri boşaltarak lease
   yenileyemesin; yarım/bozuk snapshot kapalı kabul edilsin.
3. Son yazıcı boot/receiver session'ının, işçi oturumunun ve tam
   task/epoch/child/Path/permit-generation/body-hash bağının **birlikte**
   sabitlenmesi gerekir. Yerel aktarım kimliği doğrulanmalı, tek üretici
   erişimi olmalı; aynı UID/root tehdidine karşı korunma yokmuş gibi
   gösterilmemeli. Bu actuator içi aktarım yeni FM permit'i/ACK'i üretmez.
   Somut aday, supervisor'ın önceden açıp yalnız iki uca devrettiği
   nonblocking Unix `SOCK_SEQPACKET` socketpair'dir: sınırlı mesaj/okuma,
   tanımlayıcı sahipliği ve tam kayıt sınırı. Peer credentials tek başına
   aynı UID içindeki süreç kimliğini kanıtlamaz. Boot/session bağlama,
   IPC erişimi ve rol ayrımı T3C-1'in ilk tasarım kontrolüdür.
4. Son yazıcı kendi monotonik saatinde bilet/deadline ve son yeni snapshot
   ilerlemesini sınasın. Var olan receiver-local bilet yaklaşımı yeniden
   kullanılsın; işçi saatini çıkararak veya eski kayda yeni alım stamp'i
   basarak tazelik üretilmesin. Session/child/path/revoke/timeout, restart
   ve clock rewind kapalı kilitlensin; geç paket/yeniden başlayan işçi
   otomatik rearm/rollover yapamasın. Yeni sayısal süre seçilmedi.
5. T3B sağlık değerlendirmesi yalnız **veto** girdisi olsun: bilinmeyen/
   geçersiz/eski kaynak, kayıp lifecycle veya eşleşmeyen permit aktarımı
   sıfır gerektirsin; probe/işçi kaybı da deadline ile aynı sonuca gitsin.
   Health snapshot özgün ölçüm kimliği/yaşı/context'iyle bağlansın; sıradan
   timer yayını sağlık ölçümünü yenilemesin. Bugünkü kaynak kimliği ve
   kalibrasyon eksikleri nedeniyle veto'nun hareket açma karşılığı yoktur.
6. Kontrol edilen fiziksel etki **iki tahrik tekerinin sıfır hız hedefidir**;
   torque=0, pose teleport veya hız reset'i değildir. Normal smoother/
   limiter geçmişi acil sıfırı geciktirmemeli; bu ayrım ayrıca ölçülmelidir.
   DART kaynakta hız hedefini SERVO komutuna dönüştürür; gerçek fren torku,
   slip ve duruş mesafesi modelde ölçülmeden garanti edilemez.
   [DART JointFeatures: 133–168](https://github.com/gazebosim/gz-physics/blob/b84ef0b293b224bc1e1077f2252221a8359c7b98/dartsim/src/JointFeatures.cc#L133).

Physics'in mevcut adım sonu sıfırlaması yazıcı **omission** arızasına ek
korumadır; sürekli yanlış komut yazan/arızalı güvenilen son yazıcıya karşı
bağımsız fren değildir. Alternatif JointForceCmd/velocity-reset/link-wrench
yolları bulunursa test topolojisi reddedilmeli; ikinci writer ile üstünü
örtme yolu seçilmemelidir. Aynı host, kernel, Physics/DART ve son yazıcı
güvenilen ortak hata alanıdır. **Bu sınırın tamamına karşı gerçekten bağımsız
bir fiziksel duruş mekanizması mevcut Gazebo yerleşiminde yoktur.**

## 4. Arıza kapsamı

| Arıza | Öneride beklenen davranış / sınır |
|---|---|
| FM / Executor kaybı | Yeni geçerli aktarım/sağlık ilerlemez; son yazıcı yerel deadline'da sıfır ve kilit. Süre, çalışan fiziğe bağlıdır; ölçülmedi. |
| ROS/IGN bridge veya komut/IPC akışı kaybı | Aynı sıfır/kilit; eski snapshot/ACK lease yenileyemez. IPC/işçi restart hareketi açmaz. |
| Native işçi update-loop'u takılır veya süreç ölür | Gazebo beklemez; fizik ilerlerken son yazıcı timeout'u sınanabilir. Ayrım yapılmadan bugünkü plugin için bu iddia yoktur. |
| Son yazıcı callback'i atlanır, Physics çalışır | Mevcut Physics sıfırlamasının koşulları ve sonraki gerçek tüketim doğrulanır; gövde duruşu ayrıca ölçülür. |
| Son yazıcı mutex/deadlock, Gazebo/Physics süreci stop/crash | Aynı dünya ilerlemez; bağımsız fren başarısı sayılmaz. Dış observer koşuyu geçersiz/containment olarak işaretler. |
| TF/odometry/AMCL/ObservationHealth veya permit geçerliliği kaybı | Bağlı sağlık veto'su ve yerel expiry sıfır ister. Bu bağlantı bugün yok; salt T3B raporu/Peer `current=false` yeterli değildir. |
| Host/engine arızası, yanlış ama sürekli yenilenen güvenilen veri | Kapsanan fail-silent hata modelinin dışı; kalifiye kaynak/bağımsız fiziksel fren olmadan garanti yoktur. |

## 5. T3C-1 için sıralı plan ve kabul kapıları

**T3C-1 önerisi yalnız sıfır-komutlu süreç ayrımı ve veto doğrulamasıdır.**
Bu mimarinin onayı, hareketli kalibrasyon izni yerine geçmez.

1. Önerilen hata kapsamı, IPC güven sınırı, receiver/session sahipliği ve
   tek writer sözleşmesi onaylansın. Ayrışan karar/eksik yetkide uygulama
   dursun. Taban/hash, aktif model, native/Physics/DART/Nav2 paketleri,
   gerçek yüklü kitaplıklar ve generated config sabitlensin.
2. Açık deney fixture'ında işçi/tek-yazıcı ayrımı ve bloke etmeyen snapshot
   aktarımı kurulsun. Kaynak/binary/IPC envanteri, negatif doğrudan ROS/IGN/
   joint yazma testleri ve bozuk/duplicate/eski snapshot testleri yapılabilsin.
   Native zero-only inhibisyonu, mevcut eşikler ve default launcher korunsun.
3. T3B ölçümleri mevcut gate'in kapatma tarafına bağlansın. Kaynak doğrulaması
   eksikse kapalı kalsın. COMMIT→Outbox→işçi doğrulaması→son yazıcı seçimi→
   fizik öncesi tüketim→fizik sonrası hız ayrı kayıtlar olsun; ayrı ACK kaydı
   değiştirilmesin. Tüketim noktası izlenemiyorsa APPLIED/duruş iddia edilmesin.
4. Önce unit/integration; ardından yeni DB/session/reset ve güncel
   RobotStatus/readiness sonrası geometriyle **durağan** Gazebo: işçi freeze/
   kill, bridge/FM/Executor kaybı, TF/odom/AMCL/health kesintisi, replan,
   stale/replay/session/permit kaybı. Atanan robot Scheduler'dan izlensin.
   Physics adım sayacı ve sim zamanı fault aralığında ilerlemeli; yalnız
   yayımlanan `/clock`/health timer'ı veya joint hedefi yeterli sayılmasın.
   Durağan koşuda snapshot ilerlemesi→timeout/veto nedeni ve yerel seçim
   gecikmesi ölçülsün; zaten sıfır olan hızdan fren kapasitesi çıkarılmasın.
5. **T3C-1 çıkış kriteri:** fault sırasında physics ilerlerken işçiden
   bağımsız son veto çalışıyor; bütün gerçek hedefler sıfır; eski bağ/restart
   açmıyor; kaynaklar serbest bırakılmıyor; bypass/default regresyonu yok.
   Fizik durmuşsa test duruş kabulü açısından geçersizdir. Başarısızlıklar ve
   ham kanıtlar korunur. Bunlar hareketten fren kabulü değildir.
6. Sonraki **ayrı yetkilendirilmiş hareketli ölçüm** öncesinde T3C planındaki
   kaynak kimliği/erişim ayrımı, fiziksel model ve bağımsız veto kalifikasyonu
   kapanmalı; izole containment ve bağımsız ground-truth kayıt hazırlanmalıdır.
   İlk tek robot/ileri–geri/dönüş/birleşik hareket/yük–zemin ölçümleri;
   algılama+hesaplama+iletişim+actuator gecikme üst sınırları, reaksiyon ivmesi,
   minimum frenleme, hız/konum hatası, footprint ve marj kanıtı üretmelidir.
   Örnekleme boşlukları, RTF/duvar saati–sim zamanı ayrımı ve tekrar/yük kapsamı
   kaydedilsin. Eksik bounds'ta UNBOUNDED sürsün; sonra B6B rezervasyon
   kapsaması ve iki peer'in göreli alanı doğrulansın. Çoklu robot/park/şarj,
   hold/resume ve release ayrı sonraki kabullerdir.

## 6. Bu oturumun doğrulaması ve Git kapsamı

Yeni canlı koşu, build, hareket veya yeni test kodu yoktur. Mevcut iki saf
test dosyası yeniden çalıştırıldı: **66 PASS**, exit 0. Komut ve ilk ortam
hatası [kanıt dizinindedir](c5-t3c0-stop-architecture-2026-11-19/).
İlk `.venv/bin/python -m pytest` denemesi `No module named pytest` ile exit 1
verdi; bağımlılık/ortam değiştirilmeden T3B'nin mevcut test venv'i kullanıldı:

```bash
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor \
  /tmp/c5-perf-test-venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_robot_health.py tests/test_stop_envelope.py
```

T3B'nin 442/154/3+2/8 sonuçları tarihsel kanıttır; burada yeniden koşulmadı.
Fortress kaynak sürümü archived paket `6.18.0-1~jammy` ile eşlendi;
SimulationRunner/Physics release commit'i, DART ve Nav2 dal snapshot'larının
URL/SHA-256'ları [kaynak manifestinde](c5-t3c0-stop-architecture-2026-11-19/primary-sources.json).
DART/Nav2 branch snapshot'ı kurulu binary'nin birebir kaynağı olarak
sunulmaz; paket/source eşlemesi T3C-1 preflight kapısıdır. Python urllib ilk
indirme denemesinde yerel CA hatası verdi; TLS denetimini kapatmadan sistem
curl ile sabit commit'ler okundu. Yerel sınırlı statik kontrol ve doküman
bağlantı kontrolü hareket güvenliği testi değildir.

Statik kontrolde **465 dokümantasyon dışı izlenen dosya**, başlangıç commit'i
ile byte eşit bulundu; sonuç [statik kayıttadır](c5-t3c0-stop-architecture-2026-11-19/static-checks.json).
Yalnız bu rapor/kanıtları ve dokümantasyon haritaları değişir. Kod, config,
IDL, Compose, GUI, Scheduler, Outbox, STALE, PeerRobotLayer ve varsayılan
launcher değişmez. T3C-1'e başlanmadı; mimari öneri burada teslim edilir.
