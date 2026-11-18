# C5-T3B — Sağlık gözlemi ve koşullu duruş hesabı

**Deneysel, varsayılan kapalı, yalnız sıfır actuator.** Mevcut T3A koşucusu,
FM/SQLite/Outbox, gerçek ExecuteTask/FollowPath ve B6B.7 native sürücüsü
kullanılır. Yeni trafik veya izin servisi yoktur. Sağlık probe'u salt okunur;
FM durumu, permit, ACK, kaynak sahipliği veya fiziksel release yazmaz.

`world.py`, mevcut bridge'in gerçek odometri çıkışını özel raw topic'e
yönlendirir. `odometry_link.py` ölçümü byte içeriğini/damgasını değiştirmeden
normal topic'e iletir; böylece odometry bağlantısı, TF helper ve AMCL process
gecikmeleri ayrı enjekte edilir. İkinci C++ odometry bridge'i kullanılmaz.
`transports.py`, bu test bağlantısı ve TF helper'ı mevcut supervisor sırasıyla
Nav2'den sonra, ana bridge/Gazebo'dan önce kontrollü kapatır.
Native sağlık yayını açık `health_period_sec` provision alanıyla, mevcut
profilin `timer_period_sec` periyodunda etkinleştirilir. Eski T3A provision'ı
sağlık yayını açmaz. Normal native status ve değişmez sıfır komut kanalı
korunur; readback aboneleri yalnız en son örneği tutar. Bu kuyruk seçimi
lease/bilet/ACK/STALE eşiklerini uzatmaz.

`live.py`, gerçek kaynakları `RobotHealthProbe` ile toplar. Humble graph GID
kümesi mesaj yayıncı kimliği değildir; bu boşluk açıkça UNKNOWN tutulur.
ROS stamp ve yerel monotonik alım yaşı ayrılır. Native health ve nested
native status MAC'leri doğrulanır; ACK fiziksel duruşa dönüştürülmez.
`measured`, gerçek ROS/API/readback bildirimlerini; `derived`, hız normu,
yaw ve covariance sigma hesaplarını tutar. TF lookup pozu bir dönüşüm/
lokalizasyon tahminidir; bağımsız ground truth veya kalibre hız/hata sınırı
olarak sunulmaz. Raw TF edge'leri ve tüm kullanılan kaynaklar ayrıca kaydedilir.

Standart `negative`, `replan`, `executor-loss`, `bridge-loss`, `fm-loss`
koşularına ek olarak `sensor-loss`, `controller-inactive`, `update-freeze`
vardır. Her koşu yeni dizin/DB/session/gerçek fiziksel reset kullanır.
İlk Executor kabulü güncel READY'yi sınırlı süre bekler; historical READY
veya restart sonrası otomatik açılma yoktur. Eski BLOCKED kayıt açılmaz.

Ölçülmüş fren/ivme/gecikme/hata/marj bounds'u bulunmadığından gerçek koşular
`UNBOUNDED`, `tube=None`, `qualified=false` üretir. Native joint hedefleri
sıfır kalır. SIGSTOP ile native süreç/fiziğin donması bağımsız fren kanıtı
değildir. Koşullu sentetik matematik testleri fiziksel ölçüm yerine geçmez.

[Sonuçlar ve ham kanıt](../../../docs/validation/c5/c5-t3b-health-stop-2026-11-18.md)
· [Çalıştırılmış komutlar](../../../docs/validation/c5/c5-t3b-health-stop-commands-2026-11-18.md)
· [T3C önkoşul/test planı](../../../docs/validation/c5/c5-t3c-braking-plan-2026-11-18.md).
