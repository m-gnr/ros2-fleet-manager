# C3.3.4 Görev 1 — Terminal epoch güvenliği

5 Kasım 2026 · **DOĞRULANDI** · İnceleme tabanı `63b8075`

[C3.3.1-DEC-04](../../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md#c331-dec-04-gerçek-completed_epoch-ve-sahipliğin-korunması) · [C3.3.2-DEC-05](../../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md#c332-dec-05-gerçek-completed_epoch-doğrulaması) · [Komut eki](c3-3-4-task-1-commands-2026-11-05.md)

## Bulgular ve düzeltme

Executor, durum makinesinin tamamladığı epoch'u `ExecuteTask.Result.completed_epoch` alanında yayınlar. ROS action istemcisi bu alanı alır ve ilgili goal bağlamındaki `task_id`, `assignment_epoch` ve goal UUID ile birlikte `ACTION_RESULT` olayına taşır. `FleetEventLoop`, atama kimliği eşleştikten sonra eksik veya `None` olan `completed_epoch` değerini `assignment_epoch` ile dolduruyordu. Düzeltme öncesi testte üç terminal sonuç türü de bu yoldan `APPLIED` döndü.

Tüketici artık gerçek bir tam sayı olan ve aktif atamayla eşleşen epoch'u zorunlu tutar. Alan geçersizse uyarı loglar ve SQLite `processed_events` tablosuna `STALE` yazar. Domain ayrıca robotun görev, epoch ve goal kimliğini doğrular. Domain reddederse tüketici bekleyen HIGH görevi ilerletmeden `STALE` döner. Başarılı geçişler görev, sahiplik ve Outbox değişikliklerini mevcut transaction içinde kaydeder. [SQLite Outbox sözleşmesi](../../design/c3-2-sqlite-outbox.md)

## Doğrulama

| Koşu | Geçti | Başarısız | Atlandı |
|---|---:|---:|---:|
| Düzeltme öncesi eksik epoch regresyonu | 0 | 3 | 0 |
| Host Python paketi | 219 | 0 | 16 |
| C3.3.3 config testleri | 3 | 0 | 0 |
| ROS 2 Humble ve CycloneDDS | 163 | 0 | 0 |
| Canlı C3.3.3, T01–T10 | 10 | 0 | 0 |
| Canlı C2.3 regresyonu | 7 | 0 | 0 |

Host atlamaları ROS 2 çalışma zamanı ve üretilmiş IDL gerektirir. Bu testler ROS kapsayıcısında çalıştı. Outbox regresyonu üç terminal türünde eksik, boş, yanlış tipli ve uyuşmayan epoch'ları, gecikmiş sonucu, farklı UUID'yi, tekrarlı sonucu ve ret sonrasında SQLite ile aktif sahipliğin korunmasını kapsar. Gerçek ROS action testinde eşleşen epoch tamamlandı, varsayılan sıfır ve farklı epoch `STALE` olarak kaydedildi.

İlk host komutunda aynı adlı iki `test_config.py` dosyası toplama hatası verdi. Dosyalar ayrı koşularda çalıştırıldı. ROS kapsayıcısında otomatik yüklenen launch eklentileri Python logger sınıfını değiştirerek uyarıların `caplog` yerine stderr'e gitmesine neden oldu. Dört log doğrulaması bu nedenle ilk koşuda başarısız oldu. Son koşuda iki launch eklentisi kapatıldı ve aynı 163 test geçti. Eski `jsonschema` sürümü 19 metaschema uyarısı üretti.

Canlı iki koşuda backend tüm senaryoları tamamlayıp 0 ile çıktı. Compose, backend çıkışından sonra simulation kapsayıcısını durdururken 137 kaydetti. Docker `OOMKilled=false` bildirdi. Simulation'ın temiz kapanışı doğrulanmadı.
