# C5-B6B.1 — Birleşik trafik rezervasyon çekirdeği

15 Kasım 2026 · main, başlangıç HEAD `76f7badc0fa154b0d9ce007c0f84dbdb06b75569`.
**DOĞRULANDI: hedefli domain/SQLite protokol kapsamı. Fiziksel güvenlik HENÜZ TEST EDİLMEDİ.**

## Uygulama ve kapsam

[Traffic domain](../../../backend/fleet_manager/domain/traffic.py), [persistence adapter](../../../backend/fleet_manager/persistence/traffic.py), mevcut schema.sql, store.py ve event_loop.py değişti. [13 trafik testi](../../../tests/test_traffic_core.py) eklendi. Referanslar: [B6A.1](c5-b6a-1-warehouse-traffic-architecture-2026-11-15.md), [B6B.0](c5-b6b0-followpath-spike-2026-11-15.md), [tek consumer/Outbox](../../design/c3-2-sqlite-outbox.md).

TrafficAreaClaim dört türü aynı kernel'e taşır. PermitIdentity robot/task/epoch, üst ve child UUID, Executor/FM session, permit/generation/path hash, map/frame/geometri revision taşır. Claim generation ayrıca fenced edilir. observed_occupants/evidence owner'dan ayrıdır. Occupancy başka robotun owner kaydını değiştirmez.

Geometri ilk sürümde konservatif axis-aligned rectangle birleşimidir. sweep her segmenti açıkça verilen footprint çevrel çember yarıçapıyla genişletir; bütün yaw/dönüşleri kapsar, diyagonal rotaları gereğinden çok rezerve edebilir. Bu yarıçap ürün için kalibre güvenlik marjı değildir; ürüne varsayılan değer yazılmadı. Genel konkav poligon desteği veya path'e göre optimal yakın rezervasyon yoktur. Managed rectangle birleşiminin tam kapsaması sınır grid'iyle kontrol edilir; boşluklar UNMANAGED. Kesişme sınır temasını içerir. ETA/pencere yoktur.

TRAFFIC_CONFIGURE yalnız bir kez açık managed geometri/revision kurar; ürün config veya ROS otomatik bağlaması yoktur. TRAFFIC_BIND güvenilir iç consumer girdisiyle tam identity bağlar; aktif context değiştirilemez. Bu bir authentication servisi değildir. Yeni epoch/bacak otomatik rollover'ı bu dilimde kapalıdır: eski sahiplik serbest bırakılmadan context değiştirilmez. TRAFFIC_ACQUIRE bütün claim setini tek değerlendirmede alır veya hiç almaz. Aynı request kimliği aynı payload ile aynı tarihsel sonucu döndürür; bu sonuç güncel hareket izni değildir. Değişen payload reddedilir. Claim ID yeniden kullanılamaz. Aktif farklı robot geometrileri, hangi türde olursa olsun aynı çatışma kontrolüne girer.

TRAFFIC_BLOCK STALE/ERROR/session ve açık belirsizlik nedenleriyle owner'ı tutar. Mevcut consumer APPLIED/SESSION_BLOCKED olaylarında robotları değerlendirir ve mevcut traffic snapshot varsa STALE/ERROR/session bloklarını aynı transaction'a yazar. Normal task/station kararları değiştirilmez. TRAFFIC_OBSERVE gerçek fiziksel claim'i ayrı kaydeder; yetkisiz/başka owner/UNMANAGED durumunda ZONE_VIOLATION üretir. Bu sürümde gelen fiziksel evidence kalifiye olmadığı için her observation global yeni grant blokajı da kurar; son footprint silinmez veya otomatik ilerletilmez. Bu bilinçli kullanılabilirlik kısıtıdır. Olay fiziksel duruş sağlamaz.

## Transaction ve restart

Consumer'ın BEGIN IMMEDIATE transaction'ında traffic_state snapshot, traffic_decisions ve traffic_outbox birlikte yazılır. Ayrı trafik outbox mevcut hareket göndericisi tarafından tüketilmez; yalnız reservation karar kaydıdır, durum PENDING kalır. Mevcut outbox_events'e yeni hareket komutu eklenmez. Ağ/ROS gönderimi eklenmedi. Her sonuç movement_authorized=false taşır. Mutasyona uğrayan traffic state kalıcı snapshot'tan transaction içinde yüklenir; rollback sonrası sızan canlı domain kopyası yoktur. Bir event aynı payload ile idempotenttir; aynı event ID farklı payload ile reddedilir (ilk kayıt korunur). Geçerli yeni request retleri kalıcı karar ve outbox'a kaydedilir; parse/validation exception transaction'ı rollback eder, başarılı karar gibi kaydedilmez.

require_empty üç trafik tablosunu da kapsar. Mevcut DB yeniden açıldığında trafik kayıtları silinmez; FleetEventLoop başlangıcı ScenarioResetRequired ile otomatik devamı engeller. SQL snapshot okumak operasyonel replay yetkisi değildir. Yeni DB/ilk telemetri fiziksel reset kanıtı sayılmaz. Timeout release yoktur.

## Release sınırı ve açık eksikler

ReleaseEvidence identity, claim seti, child terminal, local retire ACK, pose örnekleri, velocity/TF damgaları ve footprint dışarıda alanlarını tanımlar. Eşikler/kanıt üreticisi kalifiye olmadığı için **bütün release istekleri reddedilir**; hiç FREE geçişi yoktur. Identity uyuşmazlığında ayrıca RELEASE_IDENTITY_FENCE döner. Pose/velocity/TF tazeliğini veya sahte ACK'yi gerçek güvenlik kanıtı olarak kabul eden bir doğrulayıcı yoktur. BLOCKED otomatik kaldırılmaz. Observation geçmişi ve request kayıtları bu sınırlı dilimde temizlenmez; bounded memory/storage ve operasyonel recovery sonraki tasarım işidir.

Ürün hareketi açmak için eksik olanlar: gerçek map/footprint/uncertainty kalifikasyonu, yerel permit/ACK/retire producer, stop tüpü ve actuator fail-safe, gerçek child UUID/path eşlemesi, kimlik kaynağı ve context rollover, fiziksel release validator ve kontrollü reset. Domain UUID alanlarını doğrular fakat ROS sender ile kriptografik/transport kimlik bağı kurmaz. Domain claim geometrisi/hash'i arasındaki bağ güvenilir adapter sorumluluğudur; kernel keyfi path hash'inden geometri türetmez. Bunlar fiziksel çarpışmasızlık kanıtı değildir.

## Komut ve sonuç

Depo kökünden:

```sh
python3 -m pytest -q tests/test_traffic_core.py tests/test_fleet_manager_outbox.py
```

Son koşu **114 geçti, 0 kaldı, 0 skip; 1,84 s**. 13 yeni trafik testi; 101 mevcut hedefli consumer/SQLite/Outbox testi. Kesişen/kesişmeyen rotalar, static–static/static–dynamic temas, fiziksel occupancy/STOP_HOLD, UNMANAGED, bozuk geometri, eşzamanlı iki SQLite writer acquire, çoklu claim ret/transaction rollback, duplicate/epoch/UUID/session/generation/revision fence, STALE/ERROR blokajı, release reddi, violation, restart ve mevcut command outbox izolasyonu kapsandı. Gerçek consumer async yolu da kullanıldı. Daha önceki 10 testlik ilk koşu ve geliştirme koşuları son kapsamın yerine geçmez. Geniş regresyon, Gazebo, ROS hareket ve GUI testi çalıştırılmadı.

C5-A NavigateToPose, Executor, station reservation algoritması, şarj/preemption politikası, watchdog, GUI ve motion_envelope değiştirilmedi. Kullanıcı değişiklikleri korunur; commit/push yoktur.

## B6B.2 için en küçük adım — ÖNERİ

Önce hareket kapalı gerçek handshake/IDL: trusted robot/session/current assignment context → immutable path+geometri+child UUID → reservation decision → matching local applied ACK. Pickup/dropoff ve station send yollarında ortak gate gerekir. Herhangi bir ROS reconnect/timeout/revoke belirsizliğinde gate kapalı ve owner tutulur. Gerçek ACK ve release evidence producer/validator kalifiye edilmeden sahte cevapla nonzero açılmaz. FollowPath yeniden bağlaması ve actuator interlock ayrı kabul kapısıdır.
