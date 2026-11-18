# C5-T3A — Gerçek FM permit → native sıfır context doğrulaması

18 Kasım 2026. Taban **f94ed776c616334c17a3ce6b79e4bf5192d75508**.
**T3A bağımsız sıfır-komut kapsamı DOĞRULANDI; deneysel ve varsayılan kapalı.**
Gerçek ürün görevinin FM izni native alıcıya ulaştı; hatalı/eski bağlamlar
reddedildi. **Nonzero, APPLIED, fiziksel stop/release, hareketli trafik veya
üç görevin COMPLETED kabulü verilmedi. Varsayılan demoya açılmaya hazır değil.**

[Komut eki](c5-t3a-native-permit-commands-2026-11-18.md) ·
[Ham kanıt ve manifest](c5-t3a-native-permit-2026-11-18/) ·
[Mevcut B6B.2 tasarımına ek](../../design/c5-b6b2-traffic-permit-protocol.md#18-kasım-c5-t3a-eki--canlı-permit-ve-native-sıfır-doğrulaması) ·
[Mermaid](../../diagrams/src/traffic-live-permit-zero.mmd) ·
[SVG](../../diagrams/svg/traffic-live-permit-zero.svg).

## Korunan başlangıç ve dar kapsamlı düzeltmeler

[Önceki durdurma notu](c5-t3a-continuation-2026-11-18.md) tarihsel olarak
korundu; bu rapor devam oturumunu anlatır. İlk 19 kaynak/test dosyasının
durdurma snapshot'ıyla birebir aynı olduğu yeniden doğrulandı. T1 manifest'i
22, T2 manifest'i 172 ve önceki T3A manifest'i 98 dosyada aynı kaldı.
[Başlangıç](c5-t3a-native-permit-2026-11-18/resume-start.json) ·
[Koruma denetimi](c5-t3a-native-permit-2026-11-18/preservation.json).
Reset, clean, stash, checkout, force push, dosya silme veya başka worktree
değişikliği yapılmadı. Eski DB/BLOCKED kaydı açılmadı.

Önceki canlı hata, fiziksel reset/readiness sonrasında bile FM ilk güncel
RobotStatus'ları almadan trafik geometrisi kurulduğunu gösteriyordu.
Fixture artık bütün robotlarda initial verification, mevcut STALE eşiği,
session fence ve ERROR kontrolünü bekliyor. Deadline'da senaryo reddediliyor;
STALE/session/sahiplik kuralları gevşetilmedi. Görev etiketi
`t3a-robot_alpha` olsa bile gerçek Scheduler ataması Alpha olmak zorunda
değil; ACK gerçek atanan robot üzerinden izleniyor. Son replan ve Executor
kaybı koşularında **Gamma** seçildi. Scheduler kodu değiştirilmedi.

Bu oturum ayrıca iki fixture görünürlük sorununu dar kapsamda düzeltti:
nonzero ret nedeni sonraki paketle örtülünce native'ın kalıcı ret tanısı ve
reddedilen body hash'i eklendi; süreçler arası test JSON tetik/yanıt/session
dosyaları atomik görünür kılındı. Bunlar yeni hareket izni değildir.
Yeni testler kapanma nedenlerini ayrı REPLAN/CANCEL/PREEMPTION fixture'larıyla,
her hatalı ACK alanını ayrı temiz consumer'la ve ACK transaction rollback'iyle
doğruladı. Önceki kaynakların sürümleri durdurma arşivinde korunur.

## Gerçekleştirilen bağlantı ve ayrı kanıt aşamaları

| Aşama | Gerçek kaynak / kanıt | Yetki sınırı |
|---|---|---|
| Ürün ataması | Mevcut Scheduler, ExecuteTask `outbox_events`, gerçek task/epoch/üst UUID ve Executor session | Sabit robot fixture ataması yok |
| Child ve rezervasyon | T2 BT observer'ın gerçek accepted FollowPath UUID'si ve serialized Path SHA-256'sı; B6B.1/B6B.2 `permit:*` + `child:*` kararı | Üst UUID child yerine kullanılmaz |
| Kalıcı sıfır aktarımı | Aynı consumer/SQLite transaction'ında `native-transfer:*` kararı ve trafik Outbox; tam kaynak karar metinleri ve hash'leri | Altı hız alanı sıfır; rollback'te cursor/transfer/Outbox birlikte geri alınır |
| Aktarım | Başarılı COMMIT dönüşünden sonra FM HMAC imzası; anahtarsız Executor gerçek MovementGate bağını kontrol edip değişmez zarfı iletir | Ağ gönderimi transaction dışında; dağıtık atomiklik yok |
| Native doğrulama | Gerçek Gazebo native callback: HMAC, alıcı/kaynak session, sequence, bilet, generation, tam context; native lease | Yanlış paket receipt yenilemez; geçerli nonzero bile kilitlenir |
| Native readback | Ayrı MAC domain'inde gerçek alıcı session/sıra/context hash'i ve son doğrulanan body hash'i | Kaynak saatinden fiziksel yaş hesaplanmaz |
| Kalıcı ACK | FM readback'i önceki transferle eşleyip ayrı değişmez `native-ack:<transfer>` kararı/Outbox kaydı tutar | Mevcut Outbox CHECK'i ve kayıtları **PENDING**; APPLIED üretilmez |

Yeni `traffic_native_receivers` tablosu yalnız replay/session cursor'ıdır;
ikinci trafik servisi, rezervasyon çekirdeği veya fiziksel durum makinesi
kurulmadı. Tek consumer, SQLite sahipliği ve ürün hareket Outbox'ı korunur.
FM/native aynı test güven alanındaki anahtarı paylaşır; native'ın SQLite
COMMIT'i bağımsız sorguladığı veya kriptografik olarak tasdik ettiği iddia
edilmez. Anahtar Executor'a verilmez, SQLite/rapor/SDF'ye yazılmaz.

ACK'de `native_verified=true`, yalnız o body'nin geçmiş doğrulamasını ifade
eder. `fm_context_valid_at_ack` ayrıca hesaplanır; gecikmiş veya kapanmış
bağda false olur. `receiver_live_now=UNKNOWN`, `physical_stop=UNKNOWN`,
`movement_authorized=false`, `ownership_release=false` daima korunur.
Kapanma veya geç ACK'de yalnız `REVOKE_ZERO` gönderilebilir. Native revoke
receipt'i yenilemez ve BLOCKED_REARM'dan ağ üzerinden çıkış yoktur.

## Güncel test sonuçları

| Seçki | Sonuç / kapsam |
|---|---|
| Geniş host regresyonu | **375 PASS, 0 FAIL, 0 SKIP**; native bağ, B6B core/protocol/gate, T2 child, Scheduler, Outbox, Executor safety/state machine, park/şarj, rota ve peer config |
| Humble ROS tipli seçki | **84 PASS, 0 FAIL, 0 SKIP**; gerçek tipler ve adapter sınırı; bazı endpoint'ler açık fake fixture'dır |
| Temiz son native build / CTest | **3 PASS**: eski authorization/callback-target ve yeni live-context testi; assert'ler açık (`-UNDEBUG`) |
| Ara seçkiler | 163 hedefli host, 76/80 ROS, 371 host ve ilk 3 native test geçti; final seçkilerle örtüşür, toplanmaz |
| Son izole Gazebo matrisi | **7/7 senaryo geçti**, aşağıdaki sınırlar içinde; ayrıca önceki binary ile temiz replan-a1 geçti |
| Kalıcı kayıt/ham örnek denetimi | Yedi son koşuda SQLite integrity, kaynak karar/Outbox byte eşitliği, ExecuteTask sahipliği, Path byte hash'i, ayrı ACK/body eşleşmesi ve sıfır hedefler geçti |

Tam depo suite'i çalıştırılmadı. ROS lifecycle teardown'ında mevcut
`unresolved ownership` / geçersiz feedback publisher uyarıları loglarda
korundu; test exit'i 0'dır. Bunlar güvenli terminal, duruş veya release
kanıtı olarak değerlendirilmedi. Cancel/preemption ve receiver restart
negatifleri unit/component/T2 sınırındadır; canlı hareketten iptal veya
Gazebo update-loop restart kalifikasyonu değildir.

### Temiz ve izole Gazebo koşuları

Her koşuda yeni DB, native/Executor session, fiziksel reset, AMCL/Nav2/TF
readiness; üç robotlu dünya, gerçek Battery Simulator ve ayrı FM/Executor/
command bridge süreçleri kullanıldı. Tek simülasyon çalıştırıldı; varsayılan
demo/API/frontend açılmadı. Non-replan kayıp koşularında açık tek-plan BT,
replan'da stock yeniden planlama kullanıldı. Olumlu permit ve ACK sentetik
üretilmedi; negatif paket enjeksiyonları ayrı test otoritesiyle etiketlendi.

| Koşu / DDS domain | Sonuç | Son native örnekleri A / B / G |
|---|---|---|
| `negative-a2` / 203 | Gerçek FM ACK; yanlış imza, generation, FM/Executor session, epoch, child UUID, Path, duplicate ve nonzero reddi | 968 / 966 / 964 |
| `executor-loss-a1` / 204 | Gerçek atanan Gamma SIGKILL; native TIMED_OUT; yeni Executor bloklu, FM session fence; aynı DB FM restart reddi | 1602 / 1599 / 1596 |
| `bridge-loss-a2` / 206 | Yalnız komut bridge'i SIGKILL; fizik/readback devam, TIMED_OUT; bridge restart + eski paket BLOCKED_REARM | 1297 / 1294 / 1293 |
| `fm-loss-a1` / 207 | Gerçek FM SIGKILL; native TIMED_OUT; aynı DB restart ScenarioResetRequired | 946 / 943 / 941 |
| `startup-missing-a1` / 208 | Gamma RobotStatus yok; 15 s fixture deadline'ında güvenli ret; geometri/transfer/ACK/görev Outbox'ı yok | 3392 / 3391 / 3389 |
| `startup-delayed-a1` / 209 | Gamma Executor 2,5 s gecikti; önce geometri yok, güncel üç durum sonrasında gerçek permit/ACK | 1470 / 1469 / 1468 |
| `replan-a2` / 210 | Gerçek görev Gamma'ya atandı; gerçek replan context'i kapattı; native revoke ACK, eski paket yeniden açmadı | 1158 / 1156 / 1156 |

Son native kitaplık SHA-256:
`8979ce39d5b9f3f452a51c6a36f5233e35c7e89d8571354532175cba55f57b9c`.
Son replan'da Gazebo PID 27'nin gerçek `/proc/.../maps` kaydı alındı;
yalnız dosya adı/SDF beyanına dayanılmadı. İlk replan-a1 eski ara binary
`13b7f36b...` ile ayrı kapsam olarak saklandı. Native kabul sınırı değişmedi;
son binary yalnız kalıcı nonzero ret tanısını ekler.

Son replan'dan somut zincir:

- Görev `t3a-robot_alpha`, **robot_gamma**, epoch **1**.
- Gerçek ExecuteTask UUID `56b6c207-75e5-4ed5-bd64-2e22b312272f`;
  gerçek FollowPath UUID `1b155cc4-42d6-ce80-0036-07807f5f25a5`.
- Path SHA-256 `08b623d589392ea941975588ceca9106f8f256122449c0dcaa0536e45ef9ed94`.
- Permit `df727a77-492b-5b3b-bc7d-8a420117c8cd`, generation **1**;
  transfer `native-transfer:7ca5bf9ba85b21f3:b99d5be9-b398-59ce-ad11-bf8129181b84`.
- Native doğrulama ACK'sindeki komut SHA-256
  `83838a34bba5d1e25ac83e288b998174a886bb4f75b01195c719544a58323d74`,
  tam kalıcı transfer body'siyle eşleşti. Native MAC canlı runner'da özel
  test anahtarıyla doğrulandı; anahtarsız offline audit yalnız byte ve bağ
  tutarlılığını yeniden doğrular.
- Replan sonrası ayrı gerçek `NATIVE_ZERO_REVOKED` ACK kaydı bulundu.
  Generation rollover otomatik kabul edilmedi; yeni bağ eski kaynağı devralmaz.

[Son audit](c5-t3a-native-permit-2026-11-18/live-audit.json) ·
[Replan özeti](c5-t3a-native-permit-2026-11-18/live/replan-a2/summary.json) ·
[Gerçek library mapping](c5-t3a-native-permit-2026-11-18/live/replan-a2/native-loaded-mappings.json) ·
[Başlangıç kanıtı](c5-t3a-native-permit-2026-11-18/live/replan-a2/traffic-start-proof.json).

### Fiziksel gözlem ve kapanış sınırı

Üç robotun kayıtlı native linear/angular ve mevcut joint command hedefleri
bütün son koşul örneklerinde sıfırdı. Poz ölçülen altı görevli koşuda en büyük
yatay fark **1,282 × 10⁻¹⁰ m**; 1 mm fixture sınırının altında. Mevcut contact
guard'da **UNSAFE_CONTACT / robot-robot veya robot-raf teması kaydı yok**.
Zemin destek teması bu iddiaya dahil değildir. Bunlar **başlangıçtan durağan
dünyanın** gözlemleridir; hareketli fren, park dönüşü veya şarj yaklaşması
temassızlık kabulü değildir. Üç görev COMPLETED olarak sunulmaz.

Normal alt süreçler exit 0 ile kapandı. Bilerek öldürülen FM/bridge/Executor
exit -9; beklenen manager restart exit 1, eksik başlangıçta manager exit 1
olarak `shutdown.json` dosyalarında ayrıdır. Senaryo sonunda aktif deney
container'ı/simülasyon kalmadı. Başka kullanıcı/çalışma ağacı süreci durdurulmadı.

## Korunan başarısızlıklar ve düzeltme kanıtı

- Önceki oturumun ilk **2 FAIL / 154 PASS** Outbox denemesi ve STALE/Scheduler
  kaynaklı başarısız replan koşusu durdurma arşivinde aynen korunur.
- Bu devamın `negative-a1` / domain 202 koşusu **BAŞARISIZ**: native alıcı
  kilitlendi fakat nonzero ret nedeni sonraki paketle örtüldü; fixture
  `NONZERO_DISABLED` görmeyi beklerken kaldı. Kilitlenme tek başına ilgili
  paket reddi kanıtı sayılmadı. Kalıcı ret tanısı/body hash'i, component testi
  ve temiz `negative-a2` tekrarıyla kapatıldı.
- `bridge-loss-a1` / domain 205 **BAŞARISIZ**: release-response dosyası
  açılmış fakat JSON henüz yazılmamışken okunarak JSONDecodeError oluştu.
  Kayıp enjeksiyonuna ulaşılmadı; trafik güvenliği başarısı sayılmadı.
  Atomik fixture dosya görünürlüğü sonrası temiz `bridge-loss-a2` geçti.
- Offline audit'in ilk taslağı native_status'u dict yerine string varsaydı;
  TypeError verdi. Şema okuması düzeltildi; ürün veya kanıt değiştirilmeden
  ikinci audit yedi koşuda geçti. Bu analiz aracı hatası ayrıca kaydedildi.

İlk koşuların log/native/ROS/SQLite dosyaları silinmedi veya değiştirilmedi;
yeni arşivde ve orijinal `/tmp/c5-t3a-resume-*` yollarında durur. Gzip
arşivler açıldığında orijinal byte SHA-256'larıyla karşılaştırılabilir.

## Varsayılan izolasyon ve açık T3B bağımlılıkları

`start_demo.sh`, ürün Executor node'u, Scheduler, STALE/safety constants,
standart warehouse launcher, B6B.5 Lease/DiffDrive, PeerRobotLayer ve T2 BT
observer kaynakları tabanla **byte eşit**.
[İzolasyon hash'leri](c5-t3a-native-permit-2026-11-18/default-isolation.json).
Varsayılan consumer native profili None; varsayılan Executor yeni linki
kurmaz. Peer ve native deney aktivasyonu mevcut açık fixture'larında kalır.
Outbox PENDING kısıtı gevşetilmedi; yeni ACK ayrı kayıttır. Performans
düzeltmeleri ve mevcut T1/T2 kaynakları/kanıtları korunur.

**T3B için sıfır-komut başlangıç noktası hazır; nonzero veya varsayılan
demo entegrasyonu hazır değil.** Açık sınırlar:

1. Gerçek sağlık/duruş zarfı, hareketten kontrollü duruş ve bağımsız
   actuator/update-loop/hardware fail-safe kalifikasyonu yok.
2. FM/native aynı fixture UID/anahtar güven alanında; SROS/DDS/IGN ACL ve OS
   rol/anahtar izolasyonu kalifiye değil. HMAC key sahipliği süreç kimliği
   veya gerçek fiziksel durum kanıtı değildir.
3. Geçerli yeni generation/context'e canlı rollover/rearm yok; güvenli ret
   var. Kaynaklar fiziksel kanıt olmadan tutulur. Otomatik restart replay yok.
4. Hold/resume, fiziksel release, hareketli çoklu robot koordinasyonu, dar
   koridor, park/şarj dönüşü ve üç eşzamanlı COMPLETED bu aşamada test edilmedi.
5. ACK tarihsel doğrulamadır; anlık receiver liveness veya fiziksel frenleme
   değildir. İletişim kesilince hedeflerin sıfır gözlenmesi hareketli stop
   kabulünün yerine geçmez.

Commit/push yalnız bu bağımsız deneysel kapsamın testleri ve izolasyonu
geçtikten sonra kullanıcının devam talimatındaki yetkiyle yapılır. Rapor
kendisini içeren commit'in SHA'sını kendisine gömmez; Git teslim sonucu
ayrıca bildirilir. T1/T2 tarihsel kayıtları yeni test gibi sunulmaz.
