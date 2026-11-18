# C5-T2 gerçek ürün child metadata deneyi

**Deneysel, varsayılan kapalı.** [Rapor ve komutlar](../../../docs/validation/c5/c5-t2-product-child-2026-11-18.md)
çalıştırılan kapsamı ve başarısız denemeleri açıklar.

`world.py`, mevcut B6B.7 native sıfır dünyasını yeniden kullanır ve yalnız
bu fixture'ın üretilen Nav2 YAML'ına `fleet_nav2_observer` ekler.
`identity.py`, bağımsız fiziksel reset/AMCL/Nav2/TF ve contact gözlemcisini,
ürün Battery Simulator, Executor, FM/Scheduler, canlı Nav2 rota sorgusu,
SQLite ve gerçek Outbox göndericisini kullanır. Robotlar config'den gelir;
ilk robotun ürün görevi metadata için gözlenir. Provision anahtarları
arşive alınmaz. SQLite konteynerin yerel dosya sistemindedir; kapanışta
kanıt dizinine yedeklenir.

Gerçek Nav2 child kabulü ve stock replanning gözlenir; fiziksel hareket
native sürücüde daima sıfırdır. Fixture gerçek üst goal iptalinden önce
dispatch'i durdurur; C3'ün tekrar kuyruğa alma/atama kuralını değiştirmez.
Hiçbir APPLIED/RETIRED ACK veya fiziksel release üretilmez. Yeni epoch
Outbox'ı PENDING kalabilir; eski traffic claim BLOCKED kalır.

Bu kod normal launcher'a import edilmez. Observer, kabulden sonra metadata
toplar; actuator öncesi güvenli trafik izni değildir. Hareketli kabul, park/
şarj, hold/resume, güvenli rollover ve actuator bağı T3–T5 kapsamındadır.
