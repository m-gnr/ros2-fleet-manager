# C5-B6B.3 — Yerel hareket kapısı doğrulaması

15 Kasım 2026 · `main` worktree: `/Users/murat/develop/ros2-fleet-manager-c5-a-demo-integration`. Başlangıç dizini `main-legacy` olduğundan mevcut main worktree kullanıldı; branch checkout yapılmadı. Önceki bütün kullanıcı değişiklikleri korundu. Yeni bileşen, test, tasarım, diyagram ve bu kayıt/komut eki eklendi; dizinlere yalnız bağlantı eklendi.

**DOĞRULANDI:** fake üretici ve fake actuator ile hareket kapalı yerel model. Son hedefli koşu **69 passed, 0 skip**, exit 0: 38 yeni hareket kapısı testi ve 31 mevcut trafik protokolü/domain/SQLite testi. [Ham çıktı](c5-b6b3-motion-gate-2026-11-15/offline-tests.txt) · [Komut eki](c5-b6b3-motion-gate-commands-2026-11-15.md) · [Tasarım ve topoloji](../../design/c5-b6b3-traffic-motion-gate.md).

| İstenen senaryo | Sonuç / kanıt sınırı |
|---|---|
| 1. Permit yok | Sıfır çıkış, NO_LIVE_PERMIT. |
| 2. Applied ACK yok | Sıfır çıkış; dış ACK de yerel binding'i ikame edemiyor. |
| 3. Yanlış epoch/UUID/generation | Epoch, parent/child UUID, digest, task ve iki session için parametreli ret; request tombstone. |
| 4. Session değişimi | Eski ACK/decision reddi; reprepare kilitli. |
| 5. STALE pose/sensör | Pose/TF/ObservationHealth/velocity/clock ret; gelecek/missing veri ve kullanılan ölçüm doğrulaması ayrıca test edildi. |
| 6. Revoke | Yeni nonzero yok, geç ACK/decision ret; gate release üretmez. Mevcut protokol/SQLite testleri revoke/retire/disconnect'te claim/owner tutulmasını da doğruladı. |
| 7. Restart | Yeni local_session, kapalı başlangıç, eski ACK reddi. |
| 8. Alternatif kaynak | Fake teleop gate girişinde BYPASS_DETECTED; actuator'a doğrudan yazmanın kapıyı atladığı ayrıca gösterildi. Bu tespit ROS yayıncı kimlik doğrulaması değildir. |
| 9. Predicted breach | Ret + PREDICTED_BOUNDARY_BREACH; gerçek sentetik footprint ihlali ayrı ZONE_VIOLATION. Geometri birleşimindeki boşluk da ret. STALE footprint gerçek ihlal diye raporlanmıyor. |
| 10. Son komutu tutma | Fake actuator'a önceden nonzero verildi; gate sıfırı teslim edilmeyince eski hedef kaldı. Fiziksel stop UNKNOWN, release false. |

Ek testler: tüm koşullar sentetik olarak sağlansa da nonzero kapalı; pickup/dropoff/park/charge; yerel uygulamanın kopyalanması/idempotence; değiştirilmiş geometri digest'i; deadline/duplicate ve NaN/Inf/unknown hız. Yeni testlerde hareket açan yol yoktur. İlk geliştirme koşusu 26, ardından 36 kapı testiyle 67 toplam geçti; son iki ek testten sonra yukarıdaki 69 testlik koşu esas alındı. Bu sayılar geniş regresyon değildir.

**HENÜZ TEST EDİLMEDİ:** canlı ROS graph, gerçek hız gate adapter'ı, gerçek ObservationHealth/TF producer doğrulaması, fiziksel rota/tüp, bağımsız actuator durdurması, gate/bridge kaybında gerçek duruş. Son ortak topic/bypass envanteri mevcut kod ve kurulu launch kaynağından çıkarıldı; runtime publisher yokluğu iddiası yok. Topoloji ve fiziksel fail-safe bloklayıcıları tasarımda ayrıntılıdır.

Gazebo/robot/Nav2 runtime, GUI, gerçek FollowPath ve yeni nonzero ürün hareketi çalıştırılmadı. Ürün config/launch/IDL/Compose veya mevcut Executor düğümü değiştirilmedi; motion_envelope null. Deneysel watchdog ürünleştirilmedi. Commit/push ve geniş regresyon yok.
