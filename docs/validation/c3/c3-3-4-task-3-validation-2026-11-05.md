# C3.3.4 Görev 3 — Preemption sonrası güvenli yeniden atama

5 Kasım 2026 · Başlangıç dalı `main` · HEAD `fe280d292ec8ad427cc94c06a641f8993d3d53d7`

[C3.3.1 güvenli iptal kararı](../../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md#c331-dec-05-terminal-nav2-iptali-ve-fiziksel-duruş-teyidi) · [SQLite Outbox sözleşmesi](../../design/c3-2-sqlite-outbox.md) · [Komut eki](c3-3-4-task-3-commands-2026-11-05.md)

## Başlangıç ve kök neden

Görev 1 (`fe2615b264efa2fda4e99806d07787f18e209c31`) ve Görev 2 (`fe280d292ec8ad427cc94c06a641f8993d3d53d7`) başlangıç geçmişinde doğrulandı. Başlangıçta `docs/README.md` değiştirilmişti. `docs/gereksinim-literatur-ozgunluk-2026-10-27.pdf` ve `docs/reports/` izlenmiyordu. Bu kullanıcı değişikliklerine dokunulmadı.

25 Ekim raporundaki açık HEAD üzerinde tekrar görüldü. `FleetEventLoop` bekleyen iptal kaydından `CANCEL_TASK` üretip gerçek terminal epoch, task ID ve goal UUID'yi doğruluyordu. `FleetManagerCore`, eşleşen `PREEMPTED` ile kurbanı kuyruğa alıyor, `SESSION_BLOCKED` dışında bekleyen HIGH görevi doğrudan `_dispatch_assignment` ile atıyordu. Bu dal güncel RobotStatus, fiziksel görev alabilirlik, rota önbelleği ve Wh kontrollerini atlıyordu. Tek tüketici de yeni aktif hedefi normal atama gibi Outbox'a yazıyordu.

## Yeniden uygunluk akışı

1. Normal zamanlama turu önce uygun boş robotu arar. Gerekirse HIGH için pickup öncesi, yüksüz ve iki kez kesilmemiş LOW/MEDIUM kurbanı seçer. HIGH geçici beklemeye alınır, `CANCEL_TASK` Outbox'a yazılır. İptal kabulü sahipliği kapatmaz.
2. Eşleşen `PREEMPTED`, kurbanın aktif sahipliğini kapatır ve sayacını bir artırır. Kurban ve bekleyen HIGH orijinal `created_at` değerleriyle kuyruğa döner. Bekleyen iptal kaydı kapanır ve henüz gönderilmemiş eski komutlar aynı transaction içinde geçersiz kılınır. Bu işlem robotun fiziksel durumunu IDLE yapmaz ve istasyon sahipliğini değiştirmez.
3. Sonraki normal `TICK`, HIGH görevi olağan öncelik ve FIFO kurallarıyla değerlendirir. Robotun başlangıç doğrulaması, oturum engeli, 2 saniyelik monotonik telemetri güncelliği, görev alabilir RobotStatus durumu, yükü ve aktif sahipliği denetlenir. Terminalden önce IDLE gelirse aktif sahiplik atamayı engeller. Terminal önce gelirse uygun RobotStatus görülene kadar robot aday olmaz.
4. Scheduler güncel pozdan pickup'a, pickup'tan dropoff'a ve dropoff'tan güvenli şarja mevcut sağlayıcı üzerinden mesafe alır. Eksik, süresi dolmuş veya geçersiz rota atamayı engeller. Her ayak sonlu ve negatif olmayan bir mesafe, SoC de 0–100 aralığında olmalıdır. Mevcut dinamik Wh hesabı kullanılabilir enerjiyi gereksinimle karşılaştırır.
5. Uygun aday yoksa HIGH kuyrukta kalır. Uygun aday seçilirse yeni epoch ve UUID ile tek mantıksal `EXECUTE_TASK` kaydı oluşur. Atama, rezervasyon geçişi ve Outbox aynı transaction içinde kaydedilir. Doğal başarı/hata ve iptal reddi kendi sonuçlarını korur. Yinelenen terminal, sayacı veya Outbox kaydını ikinci kez değiştiremez.

Normal zamanlama yoluna dönme tercihi, önceki robotun HIGH göreve tahsisini uzatmaz. Daha eski uygun HIGH görevi veya başka uygun robot, normal öncelik ve seçim kurallarına göre değerlendirilebilir.

## Değişen dosyalar

- [fleet_manager_core.py](../../../backend/fleet_manager/domain/fleet_manager_core.py), [models.py](../../../backend/fleet_manager/domain/models.py) ve [scheduler.py](../../../backend/fleet_manager/domain/scheduler.py)
- [Outbox regresyonları](../../../tests/test_fleet_manager_outbox.py) ve [canlı T04 denetimi](../../../docker/simulation-c3-3-3/check.py)
- [Outbox tasarımı](../../design/c3-2-sqlite-outbox.md), [diyagram kataloğu](../../diagrams/README.md), [Mermaid kaynağı](../../diagrams/src/safe-preemption.mmd) ve [SVG çıktısı](../../diagrams/svg/safe-preemption.svg)
- [Doğrulama dizini](../README.md), bu rapor ve [komut eki](c3-3-4-task-3-commands-2026-11-05.md)

## Eklenen ve genişletilen testler

- IDLE ve terminal olaylarının iki geliş sırası, iptal kabulü, yeniden atamanın epoch/UUID'si, tek Outbox kaydı, duplicate ve eski terminal.
- `SESSION_BLOCKED`, stale telemetri, düşük enerji, geçersiz SoC, üç eksik rota ayağı ayrı ayrı, TTL, harita revizyonu, negatif ve sonlu olmayan mesafe, yük ve ERROR.
- Telemetride başka görev bildirilmesi ve normal FIFO ile başka bir göreve verilmiş aktif sahipliğin korunması. HIGH ve kurbanın `created_at` değerleri, kurbanın FIFO sırası ve kesilme sayacı.
- Terminal ve yeniden atama işlemlerinde SQLite `COMMIT` hatası. Hatalı işlemden sonra bellek, veritabanı ve Outbox karşılaştırıldı, aynı olay başarıyla yeniden işlendi. Doğal `SUCCEEDED` ve `FAILED` yarışında kurbanın gerçek terminal durumu ve sıfır kesilme sayacı korundu.
- Canlı T04, terminalde HIGH'ın kuyrukta ve Outbox kaydının henüz oluşmamış olduğunu kontrol eder. Güvenli duruştan sonraki gerçek IDLE telemetrisi ve kontrollü rota mesafeleriyle yeni atama Outbox'a kadar doğrulanır. T04 yeni HIGH komutunu sonraki senaryolar için göndermeden bırakır.

## Doğrulama

| Koşu | Geçti | Başarısız | Atlandı | Çalıştırılmadı |
|---|---:|---:|---:|---:|
| Ürün düzeltmesi öncesi hedef seçki | 7 | 16 | 0 | 36 seçim dışı |
| Scheduler/domain, Outbox ve rota sağlayıcısı | 93 | 0 | 0 | 0 |
| Tam host Python regresyonu | 245 | 0 | 16 | 0 |
| Host Executor paket testleri | 10 | 0 | 5 | 0 |
| C3.3.3 config | 3 | 0 | 0 | 0 |
| ROS 2 Humble/CycloneDDS, ilk koşu | 204 | 2 | 0 | C1 saf Python seçkisi hostta |
| ROS 2 Humble/CycloneDDS, test düzeneği düzeltildikten sonra | 206 | 0 | 0 | C1 saf Python seçkisi hostta |
| Canlı C3.3.3, ilk koşu | 10 | 0 | 0 | 0 |
| Canlı C3.3.3, tekrar | 10 | 0 | 0 | 0 |
| Canlı C2.3 | 7 | 0 | 0 | 0 |

Host atlamaları ROS çalışma zamanı gerektirir. ROS imajında üç paket derlendi. İlk ROS koşusunda Python 3.10, rollback testlerinin `set_authorizer(None)` ile denetleyiciyi kaldırma adımını desteklemedi ve sonraki tablo okumasını reddetti. Test düzeneği izin veren denetleyiciyle geri yüklenince iki test de geçti. Ürün kodu değişmedi. Son ROS koşusu imajın eski `jsonschema` paketinden 23 metaschema uyarısı üretti. C1 saf Python testleri host regresyonuna dahildir.

C3.3.3 ilk koşusunda T02, son 10,2 saniye ilerleme satırından sonra geçti. Tekrar koşusunda T02, son 10,0 saniye ilerleme satırından sonra geçti. Her iki koşuda da T02 için `Failed to make progress` görülmedi ve T04 yeniden atamayı doğruladı. Görev 2'nin iki başarısız T02 koşusu tarihsel kayıtta ayrı durur. [Görev 2 raporu](c3-3-4-task-2-validation-2026-11-05.md)

C2.3'te `robot_1` ikinci senaryonun dropoff bölümünde dört kez `Failed to make progress` bildirdi. Nav2 toparlandı, taşıma ve kalan senaryolar geçti. Senaryo eşikleri aynen kullanıldı. Nav2 ilerleme kararsızlığı açık altyapı bulgusu olarak kalır.

## Simulation kapanışı

| Canlı koşu | Backend çıkışı | Simulation çıkışı | Simulation OOMKilled | SIGTERM → SIGKILL |
|---|---:|---:|---|---:|
| C3.3.3 ilk | 0 | 137 | false | 3,01 sn |
| C3.3.3 tekrar | 0 | 137 | false | 3,02 sn |
| C2.3 | 0 | 137 | false | 3,01 sn |

Docker olayları 15 ve ardından 9 numaralı sinyalleri gösterdi. Loglarda ilk sinyalden sonra ROS alt süreçlerinin kapanmaya başladığı görüldü. Senaryo doğrulaması tamamlandı. Temiz simulation kapanışı **doğrulanmadı**. Görev 2'nin 20 saniye sınırıyla yaptığı ayrı kapanış deneyi kendi kaydında bulunur. [Görev 2 raporu](c3-3-4-task-2-validation-2026-11-05.md)

## Kapsam sınırları

Rota sağlayıcısının mevcut önbellek geçerlilik sözleşmesi kullanılır. Robot bazlı rota izolasyonu, otomatik Nav2 sorguları ve ek önbellek geçersiz kılma tetikleyicileri Görev 5+6 kapsamındadır. Enerji kontrolü son kabul edilen RobotStatus içindeki SoC ve mevcut Wh politikasıyla yapılır. RobotStatus ayrı bir batarya örnek zamanı taşımadığı için batarya kaynağının bağımsız güncelliği bu aşamada doğrulanamaz. YAML enerji politikalarının runtime'a tam bağlantısı Görev 7 kapsamındadır.

## Git kaydı

Görev 3 dosyaları için commit mesajı `fix(fleet-manager): revalidate eligibility after preemption`. Commit kimliği `git log -1 --format='%H %s' -- docs/validation/c3/c3-3-4-task-3-validation-2026-11-05.md` ile okunur. Uzak depoya gönderim yapılmadı.
