# C5-T3A — Gerçek permit, yalnız sıfır native context

**Deneysel / varsayılan kapalı.** Bu dizin gerçek FM, Scheduler, ExecuteTask,
Nav2 child observer, SQLite/Outbox ve B6B.7 native alıcıyı ayrı süreçlerle
birleştiren izole test fixture'ıdır. `start_demo.sh` tarafından kullanılmaz.
Her koşu yeni DB, native session ve fiziksel reset gerektirir. Eski BLOCKED
kaydı veya receiver context'i yeniden açılmaz. Nonzero hiçbir modda kabul
edilmez; stock ham Twist bridge mapping'i bu dünyadan çıkarılır.

`manager.py`, gerçek güncel RobotStatus'ların tamamından sonra trafik
geometrisi kurar. `live.py`, gerçek Scheduler atamasındaki robotun ACK'sini
izler. `single_plan.xml` kayıp testlerini replan'dan ayırır; `replan` koşusu
stock yeniden planlama ağacını kullanır. JSON fixture el sıkışmaları atomik
dosya görünürlüğüyle yapılır; bunlar ürün trafik protokolü değildir.

`negative`, `replan`, `executor-loss`, `bridge-loss`, `fm-loss`,
`startup-missing`, `startup-delayed` ayrı temiz dünyalarda çalıştırılır.
Negatif enjeksiyon test otoritesinin anahtarını kullanır; olumlu permit veya
ACK üretmez. Geçerli ACK yalnız gerçek native signed readback'ten kaydedilir.
Native nonzero ret tanısı, reddedilen paketin hash'ini taşır; son kabul edilen
komutun hash'i ve ACK'siyle karıştırılmaz.

[Çalıştırılmış komutlar ve ortam](../../../docs/validation/c5/c5-t3a-native-permit-commands-2026-11-18.md)
· [Sonuçlar ve sınırlar](../../../docs/validation/c5/c5-t3a-native-permit-2026-11-18.md)
· [Mevcut B6B.2 tasarımına T3A eki](../../../docs/design/c5-b6b2-traffic-permit-protocol.md).

ACK, `APPLIED`, güncel fiziksel duruş, release veya hareket güvenliği kabulü
değildir. Native hedefler sıfır, `physical_stop=UNKNOWN`, hareket/release
yetkisi false kalır. Aynı fixture UID'si/anahtar güven alanı üretim rol
izolasyonu sağlamaz. Hold/resume, hareketli duruş ve fiziksel release açık
bağımlılıklardır; varsayılan demo için hazır değildir.
