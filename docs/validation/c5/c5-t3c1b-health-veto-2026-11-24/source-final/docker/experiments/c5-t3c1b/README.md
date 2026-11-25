# C5-T3C-1B — Deneysel sağlık veto'su

**Varsayılan kapalı, yalnız sıfır-komut. Bağımsız canlı kabul tamamlanmadı.**
Ürün launcher'ı bu dizini veya yeni `SplitHealthProbe` adaptörünü yüklemez.
[Doğrulama ve açık engeller](../../../docs/validation/c5/c5-t3c1b-health-veto-2026-11-24.md).

`CMakeLists.txt`, 1A'nın aynı native işçi, tek DiffDrive joint yazıcısı,
Physics gözlemcisi ve recorder hedeflerini `C5_SPLIT_HEALTH_VETO` ile derler.
`Health.hh` yalnız tanısal HMAC/readback ve veto alıcısıdır; permit servisi,
hareket komutu veya ikinci joint yazıcısı değildir.

`world.py` mevcut 1A/T3B supervision ve odometry/TF fault kanallarını kullanır.
Bu izole fixture'da local costmap değerlendirmesi mevcut sağlık timer
periyodundadır; ürün config'i değiştirilmez. `live.py` görev öncesinde gerçek
AMCL servisine Nav2'nin başlangıç kovaryans öncülünü verir; çıktı gerçek
LiDAR/AMCL'den gelir. Öncül, ölçülmüş lokalizasyon hatası üst sınırı değildir.
Nomotion RPC gerçek AMCL ölçüm üretimini talep eder; pose/TF/odometri veya
ObservationHealth taklidi yayınlanmaz. İmzası bozulmuş/yanlış bağlamlı sağlık
paketleri yalnız açık negatif fixture olarak üretilir.

Güncel kaynak kontrolü, kullanılan overlay/native binary ve yeni DB/session
ile izole çağrı için [çalıştırılmış komut eki](../../../docs/validation/c5/c5-t3c1b-health-veto-commands-2026-11-24.md)
izlenir. `audit.py` gerçek COMMIT/Outbox/ACK, imzalı sağlık/readback, alınan IPC,
fizik öncesi sıfır seçimi ve ayrı fizik sonrası gözlemi karşılaştırır.
Offline denetim HMAC'i tekrar doğruladığını veya fiziksel APPLIED/stop
kanıtladığını iddia etmez. Eksik/başarısız koşu tam kabul üretmez.

Nonzero, rearm, rollover, hold/resume ve fiziksel release yoktur.
`StopEnvelope` **UNBOUNDED**, ROS mesaj yayıncısının kimliği **UNKNOWN** kalır.
Gazebo Physics veya son yazıcı arızasında bağımsız donanım freni yoktur.
