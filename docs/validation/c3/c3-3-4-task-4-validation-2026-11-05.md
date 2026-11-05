# C3.3.4 Görev 4 — Fiziksel kanıtlı istasyon güvenliği

5 Kasım 2026 · Başlangıç dalı `main` · HEAD ve uzak `origin/main` başlangıçta `1eb60a75f47f9ba5da840957d1c2412871731acb`

[İstasyon kurtarma sözleşmesi](../../design/c3-2-sqlite-outbox.md#istasyon-bırakma-ve-blocked-kurtarma) · [Komut eki](c3-3-4-task-4-commands-2026-11-05.md)

## Başlangıç ve kök neden

Görev 1 (`fe2615b264efa2fda4e99806d07787f18e209c31`), Görev 2 (`fe280d292ec8ad427cc94c06a641f8993d3d53d7`) ve Görev 3 (başlangıç HEAD'i) Git geçmişinde doğrulandı. Başlangıçta `docs/README.md` kullanıcı tarafından değiştirilmişti. `docs/gereksinim-literatur-ozgunluk-2026-10-27.pdf` ve `docs/reports/` izlenmiyordu.

`ReservationManager.unblock(station_id)`, `BLOCKED` kontrolünden sonra iki sahiplik alanını temizleyip kaynağı `FREE` yapıyordu. Bu metodu kullanan ürün çağrısı bulunmadı. `RELEASE` ve otomatik fiziksel bırakma zaten `BLOCKED` durumunu reddediyordu. Başlangıç HEAD'inde eklenen regresyon testi, robot ayrılmadan tek parametreli çağrının başarılı olduğunu gösterdi. Executor ayrıca önbellekteki odometri pozuna her durum yayınının zamanını yazdığı için yayın güncelliği ölçüm güncelliğini kanıtlamıyordu.

SQLite, istasyon başına tek kayıt, robot yabancı anahtarı, sahiplik alanlarının uyumu ve `FREE` durumunda boş sahiplik gerektiriyor. Fiziksel ayrılma denetimi domain ve tek tüketiciye ait. Şema değişmedi.

## Uygulama ve test kapsamı

- `UNBLOCK` iç olayı istekteki robotu mevcut sahiplikle eşler. Hata yayınıyla kurulan oturum ve zaman sınırının ardından aynı oturumun hata dışı RobotStatus ölçümü gerekir. Geçerli poz `tolerance_radius + departure_margin` eşiğini aşmalıdır. İstasyon ancak açık istek ve başarılı COMMIT sonrasında serbest kalır.
- Normal `RELEASE` akışı ve tek sahiplik korunur. Geçerli fiziksel ayrılma `OCCUPIED` veya `RELEASING` kaynağı serbest bırakabilir. `BLOCKED` kaynağın rezerve eden ve işgal eden alanları mevcut anlamlarıyla korunur. [Domain ve tüketici](../../../backend/fleet_manager/domain/reservations.py) · [Olay işlemesi](../../../backend/fleet_manager/event_loop.py)
- ROS adaptörü robot kimliğini topic ile eşler, ölçüm zamanını yayın zamanından ayrı doğrular ve kalan güncellik penceresini consumer'a taşır. Executor, RobotStatus'ta gerçek ölçüm damgasını ve bilinen koordinat çerçevesini yayımlar. [ROS adaptörü](../../../backend/fleet_manager/adapters/status_subscriber.py) · [Executor](../../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py)
- Yeni testler içeride, sınırda ve dışarıdaki pozu, eksik ve geçersiz koordinatı, boş ve yanlış çerçeveyi, stale durumu, tekrar ve geç teslimi, başka robotu ve bilinmeyen/değişen oturumu kapsar. COMMIT reddinden sonra bellek ve SQLite kayıtları karşılaştırılır, aynı olay başarıyla yeniden denenir. Terminal FAILED sonucu ile ERROR telemetrisi ayrı ayrı sınanır. [Domain testi](../../../tests/test_fleet_manager_domain.py) · [Outbox testleri](../../../tests/test_fleet_manager_outbox.py)
- Adaptör testleri güncel yayındaki eski, eksik ve gelecek damgalı pozları ayırır. Humble/CycloneDDS testi gerçek RobotStatus topic'i üzerinden önce ERROR ile blokajı, sonra yeni ölçümle operatör kurtarmasını denetler. Executor testi yinelenen yayında ölçüm zamanının korunduğunu ve yabancı odometri çerçevesinin map'e çevrilmediğini doğrular. [Adaptör testleri](../../../tests/test_ros2_status_subscriber.py) · [DDS testi](../../../tests/test_ros2_adapter_integration.py) · [Executor testi](../../../ros2_ws/src/fleet_robot_executor/test/test_node.py)

### Değişen dosyalar

- Domain ve persistence sınırı: `fleet_manager_core.py`, `fleet_tracker.py`, `models.py`, `reservations.py` ve `event_loop.py`.
- ROS uçları: `ros2_adapter_node.py`, `status_subscriber.py`, `RobotStatus.msg` ve Executor `node.py`. Mesajın alanları korunur, poz damgasının anlamı açıklanır.
- Regresyonlar: `test_fleet_manager_domain.py`, `test_fleet_manager_outbox.py`, `test_ros2_status_subscriber.py`, `test_ros2_adapter_integration.py` ve Executor `test_node.py`.
- Dokümantasyon: Outbox tasarımı, iki Mermaid kaynağı ve SVG çıktıları, diyagram kataloğu, doğrulama dizini, bu rapor ve komut eki.

## Doğrulama

| Koşu | Geçti | Başarısız | Atlandı | Açıklama |
|---|---:|---:|---:|---|
| Düzeltme öncesi tek parametreli unblock | 0 | 1 | 0 | 25 test seçim dışı |
| İlk odak koşusu | 115 | 3 | 0 | Geçersiz pozlar JSON snapshot yazımında reddedildi |
| Son odak koşusu | 120 | 0 | 0 | Domain, Outbox, telemetri adaptörü ve ClearRobotError istemcisi |
| Tam host Python ve Executor paket testleri | 283 | 0 | 24 | Atlamalar ROS çalışma zamanı gerektirir |
| C3.3.3 Compose config testi | 3 | 0 | 0 | Host |
| C2.3 Compose config testi, host denemesi | 0 | 3 | 0 | Test container'daki `/config` yolunu gerektirir |
| C2.3 Compose config testi, container | 3 | 0 | 0 | `/config` salt okunur bağlı |
| ROS 2 Humble/CycloneDDS | 237 | 0 | 0 | C1 saf Python config seçkisi hostta. 26 metaschema uyarısı. |
| Canlı C3.3.3 ilk koşu | 10 | 0 | 0 | Son çerçeve sıkılaştırmasından önce |
| Canlı C3.3.3 tekrar | 10 | 0 | 0 | Son ürün koduyla |
| Canlı C2.3 regresyonu | 7 | 0 | 0 | Son ürün koduyla |
| Canlı C2.3 kapanış tanısı | 7 | 0 | 0 | Simulation için geçici 30 sn kapanış süresi |

## Canlı koşular ve açık bulgular

| Koşu | Nav2 `Failed to make progress` | Backend / simulation çıkışı | Simulation sinyalleri |
|---|---|---|---|
| C3.3.3 ilk | T02 sırasında `robot_2` dört kez. Nav2 toparlandı ve iki taşıma tamamlandı. | 0 / 137 | SIGTERM → 3,015 sn → SIGKILL |
| C3.3.3 tekrar | T02 sırasında `robot_1` dört kez. Nav2 toparlandı ve iki taşıma tamamlandı. | 0 / 137 | SIGTERM → 3,027 sn → SIGKILL |
| C2.3 regresyonu | Görülmedi. | 0 / 137 | SIGTERM → 3,017 sn → SIGKILL |
| C2.3 kapanış tanısı | Görülmedi. | 0 / 0 | SIGTERM → 3,499 sn → çıkış, Docker SIGKILL olayı yok |

Dört canlı koşuda da iki container için `OOMKilled=false`. Runner ve tanı Compose komutu 0 döndü. Tanı koşusunda container içindeki kapanış kodu bir `ros2` alt sürecini SIGKILL ile durdurdu ve bir `python3` alt süreci 1 ile çıktı. Uzatılan süre Docker'ın container'ı zorla sonlandırmasını önledi. Standart Compose kapanış süresi ve alt süreç temizliği açık bulgu olarak kaldı.

T06 normal rezervasyon ve fiziksel bırakmayı domain seviyesinde sınar. Canlı T09 operatör hata temizliğini sınar. Yeni `UNBLOCK` akışı consumer ve gerçek DDS testlerinde kapsanır. Gazebo'da hata sonrası istasyondan ayrılan bir robot için tam operatör senaryosu ayrı uçtan uca kanıt gerektirir. Eski Executor sürümleriyle karışık çalıştırmada poz damgası sözleşmesi geçersiz olacağı için iki uç birlikte güncellenmelidir.
