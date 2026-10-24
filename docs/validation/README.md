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

B3 Retry başarısı dinamik çarpışma önleme, dar koridor çözümü, 3+ robot performansı veya nihai üç servisli dağıtım kanıtı değildir. C1 konfigürasyon doğrulaması canlı simülasyon veya Compose çalışma kanıtı değildir. Testler kendi image, ayar, ölçüt ve tarihleriyle değerlendirilir.
