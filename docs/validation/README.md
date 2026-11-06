# Doğrulama kayıtları

Rapor ve komut ekleri aynı aşama dizinindedir. Kod blokları geçmişte çalıştırılan komutları ve alınan çıktıları aynen korur; eski Compose yolları için [güncel yol kılavuzunu](../../docker/compose/README.md) kullanın. Tarihsel komutların bu düzenlemede yeniden çalıştırıldığı iddia edilmez.

| Aşama | Kayıtlar | Tarihsel sonuç |
|---|---|---|
| DDS topic/action | [Action raporu](dds/dds-action-validation-2026-10-23.md) · [Topic raporu](dds/dds-validation-2026-10-22.md) | İlgili kapsamda geçti |
| A | [Rapor](simulation/a/simulation-validation-2026-10-23.md) | Temel fizik geçti |
| B1 | [Rapor](simulation/b1/simulation-stage-b-2026-10-23.md) · [Komut eki](simulation/b1/simulation-stage-b-commands-2026-10-23.md) | İki temiz başarılı koşu; ilk hatalar korundu |
| B2 | [Rapor](simulation/b2/simulation-stage-b2-2026-10-23.md) · [Komut eki](simulation/b2/simulation-stage-b2-commands-2026-10-23.md) · [Devam rapor](simulation/b2/simulation-stage-b2-continuation-2026-10-23.md) · [Devam komut eki](simulation/b2/simulation-stage-b2-continuation-commands-2026-10-23.md) | İlk durma kaydı ve devamında iki temiz başarı |
| AMCL | [Rapor](simulation/amcl/simulation-stage-amcl-test-2026-10-23.md) · [Komut eki](simulation/amcl/simulation-stage-amcl-test-commands-2026-10-23.md) | 1 geçti / 1 kaldı |
| B3 | [Rapor](simulation/b3/simulation-stage-b3-2026-10-23.md) · [Komut eki](simulation/b3/simulation-stage-b3-commands-2026-10-23.md) | 1 temiz başarı, 1 başarısız, 1 durduruldu |
| B3 Retry | [Rapor](simulation/b3-retry/simulation-stage-b3-retry-2026-10-23.md) · [Komut eki](simulation/b3-retry/simulation-stage-b3-retry-commands-2026-10-23.md) | 2/2 temiz başarı |
| C1 | [Rapor](c1/c1-validation-2026-10-24.md) | 74/74 birim/sözleşme testi geçti; 1, 2, 3 robot doğrulandı |
| C2.1 | [Rapor](c2/c2-1-validation-2026-10-24.md) | 49/49 durum makinesi ve IDL testi geçti; saf Python doğrulandı |
| C2.2 | [Rapor](c2/c2-2-validation-2026-10-24.md) | 55/55 ROS 2 Humble düğüm ve yaşam döngüsü testi geçti; entegrasyon doğrulandı |
| C2.3 | [Rapor](c2/c2-3-validation-2026-10-24.md) | 2/2 temiz canlı simülasyon koşusu geçti; 7/7 senaryo (lojistik döngü, preemption, hata kurtarma, Option A) doğrulandı |
| C3.1 | [Rapor](c3/c3-1-validation-2026-10-24.md) | 25/25 saf Python çekirdek, FIFO/öncelik, Wh enerji, Karar 08 T01-T09 ve rezervasyon testi geçti |
| C3.2 | [Rapor](c3/c3-2-validation-2026-10-24.md) · [Komut eki](c3/c3-2-commands-2026-10-24.md) | 29 SQLite/consumer testi geçti; tam regresyonda 174 geçti, ROS ortamı gerektiren 10 test atlandı |
| C3.3.1 | [Rapor](c3/c3-3-1-validation-2026-10-24.md) | Sıra/oturum sözleşmesi, duplicate koruması, Nav2 güvenli iptali ve canlı simülasyon doğrulandı (189 host, 81 ROS 2/DDS testi, 7/7 canlı senaryo geçti) |
| C3.3.2 | [Rapor](c3/c3-3-2-validation-2026-10-24.md) | ROS 2 adaptör entegrasyonu doğrulandı: status subscriber, session order/SESSION_BLOCKED, eylem istemcisi, Outbox göndericisi, task_review_holds, 0.20m/30s rota önbelleği (212 host, 102 ROS 2/DDS testi, 7/7 canlı senaryo geçti) |
| C3.3.3 | [Rapor](c3/c3-3-3-validation-2026-10-24.md) | İki robotlu uçtan uca canlı simülasyon ve DDS entegrasyonu doğrulandı: Gazebo Fortress headless + iki Nav2 + iki Executor + Fleet Manager (214 host testi, T01–T10 senaryolarının tamamı 10/10 temiz geçti) |
| C3.3.4 Görev 2 | [Rapor](c3/c3-3-4-task-2-validation-2026-11-05.md) · [Komut eki](c3/c3-3-4-task-2-commands-2026-11-05.md) | Oturum engeli ve istasyon sahipliği için host, ROS ve canlı regresyon kayıtları |
| C3.3.4 Görev 3 | [Rapor](c3/c3-3-4-task-3-validation-2026-11-05.md) · [Komut eki](c3/c3-3-4-task-3-commands-2026-11-05.md) | Preemption sonrası normal zamanlamada yeniden uygunluk denetimi ve Outbox güvenliği |
| C3.3.4 Görev 4 | [Rapor](c3/c3-3-4-task-4-validation-2026-11-05.md) · [Komut eki](c3/c3-3-4-task-4-commands-2026-11-05.md) | Normal bırakma, fiziksel kanıtla BLOCKED istasyon kurtarma ve canlı koşu bulguları |
| C3.3.4 Görev 5+6 | [Rapor](c3/c3-3-4-task-5-6-validation-2026-11-05.md) · [Komut eki](c3/c3-3-4-task-5-6-commands-2026-11-05.md) | Robot bazlı canlı rota, SQL COMMIT güvenliği, C3.3.3/C2.3 regresyonları ve ayrı T02-AUTO-ROUTES koşuları |
| C3.3.4 Görev 7 | [Rapor](c3/c3-3-4-task-7-validation-2026-11-05.md) · [Komut eki](c3/c3-3-4-task-7-commands-2026-11-05.md) | YAML enerji politikalarının Scheduler'a aktarımı ve ayrı YAML-ENERGY-POLICY kabul koşusu |
| C3.3.4-FINAL | [C4 geçiş kontrolü](c3/c3-3-4-final-c4-gate-2026-11-05.md) · [Komut eki](c3/c3-3-4-final-commands-2026-11-05.md) | İki ardışık temiz C3.3.3 koşusu 10/10, gerçek HIGH teslimatı ve temiz kapanış doğrulandı; C4'e geçiş onaylandı |
| C4.1 | [Rapor](c4/c4-1-validation-2026-11-06.md) · [Komut eki](c4/c4-1-commands-2026-11-06.md) | İki robotlu Fortress tüketim hesabı ve DDS izolasyonu doğrulandı. C2.3 ve C3.3.3 regresyonları geçti |
| C4.2 | [Rapor](c4/c4-2-validation-2026-11-06.md) · [Komut eki](c4/c4-2-commands-2026-11-06.md) | İki robotlu Fortress ortamında telemetri, enerji yetersizliği, geçici kesinti ve gerçek Nav2 teslimatı doğrulandı |
| C4.3 | [Rapor](c4/c4-3-validation-2026-11-06.md) · [Komut eki](c4/c4-3-commands-2026-11-06.md) | Park ve dock yaklaşımı, canlı HIGH duruşu ve SQLite/Outbox bütünlüğü doğrulandı |
| C4.4 | [Rapor](c4/c4-4-validation-2026-11-06.md) · [Komut eki](c4/c4-4-commands-2026-11-06.md) | Fiziksel dock teması, iki robotlu şarj ve ayrılma kanıtıyla devir |
| C4.5 | [Sonuç raporu](c4/c4-5-validation-2026-11-06.md) · [Komut eki](c4/c4-5-commands-2026-11-06.md) · [C4 kabul listesi](c4/c4-acceptance-2026-11-06.md) | İki robotlu enerji, fiziksel şarj devri, görev ve güvenli preemption |

B3 Retry başarısı dinamik çarpışma önleme, dar koridor çözümü, 3+ robot performansı veya nihai üç servisli dağıtım kanıtı değildir. C1 konfigürasyon doğrulaması canlı simülasyon veya Compose çalışma kanıtı değildir. Testler kendi image, ayar, ölçüt ve tarihleriyle değerlendirilir.

## Depo ve dokümantasyon denetimleri

- [26 Ekim 2026 düzenleme ve diyagram doğrulaması](organization/organization-validation-2026-10-26.md) · [komut eki](organization/organization-commands-2026-10-26.md)
