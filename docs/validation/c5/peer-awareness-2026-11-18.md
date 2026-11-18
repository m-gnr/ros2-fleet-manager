# C5 — Çoklu robot rota farkındalığı ve çarpışma önleme

18 Kasım 2026. **PARTIAL: dar kapsamlı deneysel aday doğrulandı; tam kabul yok.**
Üç robotlu taşıma/park ve ayrı şarj yaklaşması koşuları temassız geçti. Güncel
rotaları gerçek trafik izinleriyle koordine eden ürün bağlantısı, dar koridor
önceliği ve hareketli iletişim kaybında güvenli bekleme/duruş henüz doğrulanmadı.
Bu nedenle aday varsayılan demo başlatmasında **kapalıdır**. Normal
`scripts/start_demo.sh` bu düzeltmeyi etkinleştirmez; eski park teması riski sürer.
Commit/push yapılmadı. [Tasarım](../../design/c5-peer-awareness.md) ·
[Komutlar](peer-awareness-commands-2026-11-18.md) · [Ham kanıt](peer-awareness-2026-11-18/).

## Mevcut mimarideki eksikler

- İstasyon sahipliği tekildir; koridor/rota rezervasyonu aynı şey değildir.
  [B6B.1](c5-b6b1-traffic-core-2026-11-15.md) geometrik rezervasyon çekirdeği ve
  B6B.2 protokolü vardır; gerçek hareket yetkisi ve kalifiye release kapalıdır.
  Bu çalışma bu kapıları açmaz, paralel trafik sistemi kurmaz.
- Ortak TF ve robot başına gerçek `/plan` yayınları zaten vardır. Mevcut
  `PlannerReader`/`PlanBuffer` panelde kaynak/TTL denetimi yapar. Gözlenen plan
  gerçek çalışan child UUID/path iznine bağlı değildir; FM mesafe sorgusunun
  planını da yürütülen rota gibi kullanmak doğru olmaz.
- Global costmap yalnız statik haritadır. Yerel costmap LiDAR'a dayanır;
  duran robotun geometrisi global planner'a ayrıca verilmez. Bu boşluk park
  yaklaşmasında yeniden üretildi. LiDAR'ın bağımsız algılama rolü korunur.
- Stock Nav2 `current=false` beklemesi bir süre sonra terminal abort üretebilir.
  Bu, trafik/iletişim beklemesi için tamamlanmış hold/resume sözleşmesi değildir.
  İletişim belirsizliğini FAILED/ERROR yapmama kuralını koruyacak gerçek yerel
  bağ kurulmadan varsayılan aktivasyon yapılmadı.

## Değişiklik ve sınır

Mevcut `fleet_perception` paketine `PeerRobotLayer` eklendi. Config'deki robot
namespace'lerinin TF konularını costmap'in özel callback grubunda dinler;
beklenen parent/child, ilerleyen kaynak damgası, yerel monotonik alım yaşı ve
tam zamanlı TF çözümünü denetler. Diğer robotların mevcut Nav2 çevrel
yarıçaplarını kullanır; üreticide gerçek SDF gövde/teker/sensör kasası kapsaması
kontrol edilir. Geometri hem global hem yerel costmap'e inflation öncesinde
lethal işlenir. Eski/yeni sınırlar birlikte güncellenir; kendi robotu dışlanır,
LiDAR veya statik katmanın maliyeti silinmez. TF eskirse son işgal tutulur ve
`current=false` olur; costmap clear gözlemi silemez.

Yeni robot, yarıçap veya süre sabiti eklenmedi. Mevcut profilin
`perception_safety` ve Nav2 alanları kullanılır; bunlar kalifiye belirsizlik veya
duruş marjı olarak sunulmaz. Şema/filo YAML/IDL/Compose değişmedi. Tek consumer,
Scheduler, Outbox, gerçek `completed_epoch`, session kapıları, 2 sn STALE ve
5 sn uyarı korunur. Consumer yield + WAL/FULL performans düzeltmeleri, frontend
TF düzeltmesi ve varsayılan ayrı Nav2 süreçleri korunur.

Aktivasyon yalnız izole harness `--peer-awareness-experiment` seçeneğidir.
Salt okunur probe mevcut TF/plan okuyucusunu yeniden kullanır; hiçbir görev,
hız, rezervasyon veya sahte poz üretmez. [Kaynak koruma kontrolü](peer-awareness-2026-11-18/preservation.json).

## Yeni canlı koşular

Koşular sırayla, tek aktif simülasyonla, bu workspace salt okunur bağlanarak,
ayrı Gazebo partition ve ROS domain'lerinde yürütüldü. Fiziksel reset,
AMCL/Nav2/TF readiness ve contact guard korunur. Baseline standart kullanıcı
komutuyla; adaylar aynı runner'ın yalnız deney seçeneğiyle başlatıldı.

| Koşu | Oturum / domain | Sonuç |
|---|---|---|
| Baseline | `c5-demo-20261118T063426Z-13936ad0dbed` / 226 | Üç taşıma COMPLETED; Alpha park_3 dönüşünde Beta ile temas. **FAIL** |
| A1 | `c5-demo-20261118T064710Z-25037b4febf4` / 200 | TF remap hatası; altı katman uncurrent, üç görev QUEUED. **FAIL**, hareket başarısı değil |
| A2 | `c5-demo-20261118T065849Z-3046dc67af6a` / 226 | Üç taşıma COMPLETED, üç park ARRIVED/IDLE, zararlı temas kaydı 0. **Sınırlı PASS** |
| A3 | `c5-demo-20261118T070545Z-8e1f5186661d` / 212 | Ayrı üçlü şarj yaklaşması ARRIVED, BatteryState `is_charging=true`; zararlı temas 0. Duran robotta TF kesinti testi geçti. **Sınırlı PASS** |

### Baseline: park teması yeniden üretildi

Üç MEDIUM katalog işi `pick_A1 → packing_1`, `pick_B2 → delivery-01`,
`pick_D1 → shipping_2` API üzerinden gönderildi. Üçünün aynı anda EXECUTING
olduğu snapshot'lar ve gerçek action sonuçları vardır. Beta/Gamma/Alpha
completion damgaları sırasıyla 393,830 / 469,390 / 496,790 sim-s;
`completed_epoch=1`, gerçek üst UUID'ler korunmuştur.

İlk temas **614,405 sim-s**, **09:45:55 İstanbul**:
Alpha `base_link/body` ↔ Beta `left_wheel/wheel`. Beta park_1'de, Gamma park_2'de;
Alpha'nın ayrı park_3 rezervasyonu vardır. Contact guard koşuyu kapattı.
511 contact **mesajı** tek koşudaki devam eden temas kayıtlarıdır; 511 ayrı
kaza sayılmaz. [Özet](peer-awareness-2026-11-18/baseline/summary.json),
[DB](peer-awareness-2026-11-18/baseline/database-summary.json).

### A1: bulunan ve düzeltilen entegrasyon hatası

Nav2'nin `/tf → tf` remap'i eklenti aboneliğini
`/robot_alpha/global_costmap/tf` gibi yayıncısız konulara taşıdı. Pose damgaları
sıfır kaldı; aday hareket açmadı, FM mesafe sorguları timeout/cancel oldu ve
görevler kuyrukta kaldı. Bu koşu güvenlik/işlev kabulü değildir. Namespace TF
uçları açıkça config'den üretildi ve abonelikler costmap callback grubuna
bağlandı. Native test bu remap ve ayrı callback grubu altında tekrarlandı.
A1 kapanışında simulation=1; temiz kapanış sayılmadı.

### A2: üç taşıma ve park

Aynı üç katalog işi kullanıldı. Beta/Gamma/Alpha gerçek ExecuteTask sonuçları:

| Robot | Gerçek üst action UUID | completed_epoch | Completion sim-s |
|---|---|---:|---:|
| Beta | `8b5dc1b8-819c-469a-b989-ed3bf63ca5d1` | 1 | 140,075 |
| Gamma | `0c4cc8b1-b87a-4e1d-b1cd-bce9f10cdeaf` | 1 | 217,950 |
| Alpha | `c5dad7a0-0263-4da9-941e-28d967321df4` | 1 | 239,935 |

Üç görev aynı anda EXECUTING oldu; ardından Beta park_1, Gamma park_2,
Alpha park_3 için ARRIVED oldu. Son API snapshot'ında üçü de IDLE.
Alpha'nın Beta seviyesinden geçişinde gerçek fiziksel X=14,284–14,370 m
ölçüldü; sampled Alpha–Beta merkez minimumu 0,788 m'dir. Bu örnekler sürekli
ayrıklık sınırı veya genel çarpışmasızlık garantisi değildir.

331,38 duvar-s probe penceresinde altı katmanın tüm gözlemleri current=true.
Robot başına farklı gerçek plan damgası Alpha 238, Beta 137, Gamma 271.
Grid ve katman raporu damgaları en fazla 50 ms farkla eşleştirildi: altı
yönlü global peer merkezinde 1.004/1.004, yerel pencereye giren peer merkezinde
468/468 örnek lethal bulundu. Gözlem kaydı tüm footprint sınırlarının veya
tüm zamanların canlı kanıtı değildir; bunların raster kontrolleri native testtedir.
[Özet](peer-awareness-2026-11-18/candidate-a2-transport-park/summary.json),
[park sonu](peer-awareness-2026-11-18/candidate-a2-transport-park/park-complete.json).

### A3: şarj yaklaşması ve dururken TF kaybı

Yetkili mevcut Battery Simulator test API'si, kendi session/revision/geri
okuma ve C4 süreklilik kanıtıyla üç robotu %24'e aldı. FM durumuna/DB'ye
doğrudan yazılmadı; sahte BatteryState/dock contact yayınlanmadı. Normal
katsayılar ve fiziksel şarj koşulları korundu. FM Gamma→dock_6,
Beta→dock_5, Alpha→dock_4 atadı; üç hareket ARRIVED. Gerçek BatteryState
`is_charging=true` örnekleri ve artan Wh vardır. %80'e ulaşma/şarjdan ayrılma
bu kısa testte doğrulanmadı.

Üç robot şarjda ve dururken yalnız bu oturumun TF odometri helper'ı 4,09
duvar-s SIGSTOP/SIGCONT ile durduruldu. Altı katman current=false oldu:
yerel ilk gözlem 0,741–0,759 s; global 1,154–1,173 s. Kaynak devamından
sonraki ilk current=true 0,052–0,086 s. Eşikler büyütülmedi, eski damga güncel
sayılmadı. Bu, **hareketli robotta fiziksel stop, tam ağ kesintisi veya gerçek
trafik izni geri açma testi değildir**. TF kesinti aralığındaki eşli fiziksel
örneklerde yer değiştirme 0 m bulundu.
[Kontrol kanıtı](peer-awareness-2026-11-18/candidate-a3-charge-tf/battery-control.json),
[şarj örnekleri](peer-awareness-2026-11-18/candidate-a3-charge-tf/charging-samples.json),
[TF kesintisi](peer-awareness-2026-11-18/candidate-a3-charge-tf/tf-fault-summary.json).

## Testler ve kalan kabul engelleri

Son native seçki **10 gtest PASS / 0 FAIL / 0 SKIP**; colcon'un 11 sayısı
CTest wrapper'ını da içerir. Son host seçki **138 PASS**, ek regresyon
**224 PASS**, skip yok. İlk uninitialized parameter, fixture context ve eksik
host pytest kurulum hataları ham loglarda korunur; başarıya katılmaz.
Baseline, A2 ve A3 bütün alt süreçler 0 ile kapandı; baseline üst harness'i
contact guard nedeniyle exit 1, A2/A3 container'ları exit 0 verdi. Dört DB backup'ı
integrity/foreign-key kontrolünü geçti; trafik tabloları boş kaldı. Dolayısıyla
bu canlı sonuçlar trafik izin protokolünün kullanıldığı iddiasını desteklemez.

| Kabul / hata yolu | Gerçek kapsam ve durum |
|---|---|
| Üç konum ve footprint'in diğer costmap'lere ulaşması | A2/A3 ve native dönüşüm/raster testleriyle **DOĞRULANDI**, deneysel |
| Güncel Nav2 planlarına erişim | Mevcut okuyucuyla üç robot için **DOĞRULANDI**; hareket yetkisi bağı yok |
| Üç eşzamanlı görevin COMPLETED olması | A2 **DOĞRULANDI** |
| Park ve şarj yaklaşmasında temassızlık | A2 park, A3 şarj pencerelerinde **DOĞRULANDI**; genel garanti değil |
| Kesişen/karşılıklı rotalarda izinle öncelik ve bekleme | Mevcut core/protokol unit kapsamı korunur; gerçek hareket entegrasyonu **HENÜZ TEST EDİLMEDİ** |
| Karşılıklı dar koridor ve bekleme kilitlenmesi | Canlı kabul **HENÜZ TEST EDİLMEDİ**; otomatik geri sürüş/release yok |
| Rota değişimi | Gerçek yeniden planlar gözlendi; yeni path/child için izin rollover'ı **HENÜZ TEST EDİLMEDİ** |
| Gecikmiş TF, duplicate, rewind | Native testler; dururken kaynak kaybı A3. Hareketli kesinti/duruş **HENÜZ TEST EDİLMEDİ** |

**ÖNERİ:** sonraki iş mevcut B6B.1/B6B.2'nin gerçek child/path bağını, kalifiye
yerel hold/resume ve fiziksel release üreticisini tamamlamaktır. Dar koridor
önceliği ancak bu bağ üzerinden uygulanmalı; yeni bir trafik sistemi veya
timeout ile otomatik kaynak bırakma eklenmemelidir. Lokalizasyon belirsizliği,
duruş zarfı, çoklu yazar/actuator erişim sınırı, hareketli transport kaybı ve
uzun dayanıklılık açık kalır. Bu sonuçla güvenli üç robot ürün demosu veya tam
C5 kabulü ilan edilmez.

Katmanın TF kimliği kriptografik yayıncı/Executor session kanıtı değildir;
RobotStatus session kapıları tek başına bu katmandan aktif Nav2'ye fiziksel
stop bağı kurmaz. `current` costmap güncellemesinde hesaplanır; update loop
donarsa bağımsız monotonik actuator watchdog'u gibi davranmaz. Bu iki boşluk
nedeniyle durağan kaynak kaybı testini hareketli fail-safe kabulüne genişletmek
doğru olmaz.
