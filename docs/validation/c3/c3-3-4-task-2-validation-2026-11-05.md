# C3.3.4 Görev 2 — Oturum ve istasyon sahipliği

5 Kasım 2026 · İnceleme tabanı `fe2615b264efa2fda4e99806d07787f18e209c31` (`main`)

[C3.3.2-DEC-04](../../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md#c332-dec-04-fleet-manager-başlangıcyeniden-başlama-ve-oturum-güvenliği) · [SQLite Outbox sözleşmesi](../../design/c3-2-sqlite-outbox.md) · [Komut eki](c3-3-4-task-2-commands-2026-11-05.md)

## Bulgular ve düzeltme

ROS adaptörü `publisher_session_id` ve `status_seq` alanlarını tek tüketiciye iletiyordu. Farklı bir oturum kimliği atamayı kilitliyordu, ancak tüketicide `RESERVE`, `OCCUPIED` ve `RELEASE` bu kilidi denetlemiyordu. Kimliksiz durum olayı tüketicideki kontrolün dışına çıkabiliyordu. Doğrudan domain çağrısı ise oturum değişimini, pozu ve diğer telemetriyi uyguladıktan sonra denetliyor ve fiziksel ayrılma hesabına devam ediyordu. Ayrıca eşleşen `PREEMPTED` sonucu, oturum arada değiştiğinde bekleyen HIGH görevi için yeni atama üzerinden istasyonu `RELEASING` yapabiliyordu.

- Üç kaynak olayı, istasyon geçişinden önce aynı oturum engelini denetler. Engellenen istek yalnızca `processed_events` tablosuna `REJECTED` olarak kaydedilir. Aynı olay kimliği `DUPLICATE` döndürür. Robot, görev, istasyon ve Outbox kayıtları korunur.
- Tüketici ve domain ortak oturum kontrolünü durum güncellemesinden önce çalıştırır. Yeni, önceki veya kimliksiz telemetri engeli açamaz ve fiziksel ayrılma kanıtı olarak işlenmez. Aynı güvenilir oturumda eski ve eşit sıra `STALE` kalır. Kabul edilen konum, mevcut yarıçap ve marj eşiğini geçtiğinde istasyon normal akışta `FREE` olur.
- Eşleşen terminal `PREEMPTED` sonucu işlenir. Oturum engelliyse bekleyen HIGH görev orijinal sırasıyla kuyruğa döner ve istasyon sahipliği korunur.

## Değişen dosyalar

- [event_loop.py](../../../backend/fleet_manager/event_loop.py) ve [fleet_manager_core.py](../../../backend/fleet_manager/domain/fleet_manager_core.py)
- [test_fleet_manager_outbox.py](../../../tests/test_fleet_manager_outbox.py)
- [Outbox tasarımı](../../design/c3-2-sqlite-outbox.md), [diyagram kataloğu](../../diagrams/README.md) ve `status-session-order`, `parking-reservations`, `safe-preemption` Mermaid/SVG çiftleri
- [Doğrulama dizini](../README.md), bu rapor ve [komut eki](c3-3-4-task-2-commands-2026-11-05.md)

## Doğrulama

| Koşu | Geçti | Başarısız | Atlandı | Çalıştırılmadı |
|---|---:|---:|---:|---:|
| Düzeltme öncesi yeni testler | 1 | 7 | 0 | 34 seçim dışı |
| Domain, Outbox ve durum adaptörü | 73 | 0 | 0 | 0 |
| Tam host Python regresyonu | 227 | 0 | 16 | 0 |
| C3.3.3 config | 3 | 0 | 0 | 0 |
| ROS 2 Humble/CycloneDDS seçkisi | 171 | 0 | 0 | 0 |
| Canlı C3.3.3, ilk koşu | 1 | 1 | 0 | 8 |
| Canlı C3.3.3, tekrar | 1 | 1 | 0 | 8 |
| Canlı C3.3.3, başlangıç commit'iyle karşılaştırma | 10 | 0 | 0 | 0 |
| Canlı C3.3.3, güncel kodla son koşu | 10 | 0 | 0 | 0 |
| Canlı C2.3 | 7 | 0 | 0 | 0 |

İki C3.3.3 koşusunda da T01 geçti. T02'de Nav2 `robot_1` için art arda `Failed to make progress` bildirdi. `robot_1` taşıması 120 saniyelik eşiğe kadar tamamlanmadığı için senaryo başarısız oldu. Backend kapsayıcıları assertion sonrasında 139 ile çıktı. T03–T10 başlamadı. Her iki T02 veritabanında da `robot_1` görevi `ASSIGNED`, `robot_2` görevi `COMPLETED` ve iki istasyon `FREE` kaldı. Oturum blokajı veya kaynak olayı reddi kaydedilmedi. C2.3 backend kapsayıcısı yedi senaryodan sonra 0 ile çıktı.

Başlangıç commit'iyle yapılan karşılaştırmada Nav2 bu kez `robot_2` için aynı ilerleme hatasını bildirdi. T02, 115,6 saniyelik son ilerleme satırından sonra 120 saniyelik eşiğe ulaşmadan tamamlandı. Ardından T03–T10 geçti ve backend 0 ile çıktı.

Güncel kodla son koşuda T02, `robot_1` için ilerleme hatalarına rağmen 115,4 saniyelik son ilerleme satırından sonra aynı eşik içinde tamamlandı. T01–T10 geçti ve backend 0 ile çıktı. İlk iki başarısızlık, T02'nin tekrarlanabilirliği açısından açık kalır.

Tam ROS paketini toplama denemesinde, imajdaki `jsonschema` sürümü nedeniyle `tests/test_config.py` için bir toplama hatası alındı ve test yürütmesi başlamadı. ROS seçkisi tüm ROS bağımlı host atlamalarını kapsadı. C3.3.3'ün mevcut T06 ve T08 kontrolleri, canlı koşu içinde sentetik domain/olay girdileri kullanır. Yeni rezervasyon retleri ve SQLite etkileri odak regresyonda doğrulandı.

## Simulation kapanışı

Görev 1'in iki koşusunda, bu görevin tüm C3.3.3 koşularında ve C2.3 koşusunda Docker, backend çıkışından sonra simulation'a SIGTERM ve yaklaşık 3 saniye sonra SIGKILL gönderdi. Simulation kapsayıcıları 137 ile çıktı ve `OOMKilled=false` kaydedildi. ROS launch logları SIGTERM sonrasında alt süreçlerin kapanmaya başladığını gösteriyor.

Ayrı kapanış deneyinde iki Nav2 yığını etkinleşince yalnız simulation kapsayıcısına 20 saniye süre verilerek durdurma istendi. Kapsayıcı yaklaşık 5,47 saniyede 0 ile çıktı. Test betiği iki Nav2 launch alt sürecini kendi bekleme sınırında SIGKILL ile kapattı. Bu deney kapsayıcıya verilen yaklaşık 3 saniyenin kapanış dizisine yetmediğini gösterdi. Alt süreçlerin temiz kapanışı doğrulanmadı.

## Kalan sınırlar

SQLite, tek tüketicinin işlem sınırında ret kararını ve sahiplik kaydını korur. Senaryo içeren DB ile otomatik devam kapalıdır. Kaynak olayları `station_id` ve `robot_id` taşır. Güvenlik kararı işleme anındaki kayıtlı robot oturumuna dayanır. Fiziksel ayrılma kabul edilen robot pozuyla değerlendirilir. `BLOCKED` istasyon için fiziksel kanıtlı operatör kurtarması Görev 4 kapsamındadır.

## Git kaydı

Commit mesajı `fix(fleet-manager): enforce session safety for reservation events`. Commit kimliği ve mesajı depo kökünden `git log -1 --format='%H %s' -- docs/validation/c3/c3-3-4-task-2-validation-2026-11-05.md` ile okunur. Commit, geçen oturum güvenliği testleri ve son canlı senaryo koşularına dayanır. Simulation kapanışı ayrı altyapı bulgusu olarak açık kalır.

Görev sonunda `main`, yerel `origin/main` referansının iki commit önündedir. Çalışma ağacında başlangıçtan gelen `docs/README.md` değişikliği, izlenmeyen `docs/gereksinim-literatur-ozgunluk-2026-10-27.pdf` ve `docs/reports/` bulunur.
