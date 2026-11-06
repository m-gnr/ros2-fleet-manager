# Doğrulama Compose dosyaları

Bu dosyalar uygulamanın nihai üç servisli dağıtımı değildir. Komutlar depo kökünden çalıştırılır; her dosya için `-f docker/compose/<dosya>` kullanılır. İlk dosya daima DDS tabanıdır. Farklı bir `--project-directory` ile göreli yolların anlamı değiştirilmemelidir.

| Test | Dosyaların sırası |
|---|---|
| DDS | `docker-compose.dds.yml` |
| Action | DDS → `docker-compose.dds-action.yml` |
| A | DDS → `docker-compose.simulation-check.yml` |
| B1 | DDS → A → `docker-compose.simulation-lidar-check.yml` |
| B2 | DDS → A → `docker-compose.simulation-nav2-check.yml` |
| AMCL | DDS → A → `docker-compose.simulation-amcl-test.yml` |
| B3 | DDS → A → `docker-compose.simulation-b3.yml` |
| B3 Retry | DDS → A → `docker-compose.simulation-b3-retry.yml` |
| C2.3 | DDS → A → `docker-compose.simulation-c2-3.yml` |
| C3.3.3 | DDS → A → `docker-compose.simulation-c3-3-3.yml` |
| C4.1 | DDS → A → C3.3.3 → `docker-compose.simulation-c4-1.yml` |
| C4.2 | DDS → A → C3.3.3 → C4.1 → `docker-compose.simulation-c4-2.yml` |
| C4.3 | DDS → A → C3.3.3 → C4.1 → C4.2 → `docker-compose.simulation-c4-3.yml` |
| C4.4 | DDS → A → C3.3.3 → C4.1 → C4.2 → C4.3 → `docker-compose.simulation-c4-4.yml` |
| C4.5 | DDS → A → C3.3.3 → C4.1 → C4.2 → C4.3 → C4.4 → `docker-compose.simulation-c4-5.yml` |

DDS için `DDS_TEST_PAYLOAD` zorunludur. Env dosyaları ve bind mount kaynakları depo kökündeki `config/` ve `docker/` dizinlerine gider. Container içindeki yollar, proje/servis/ağ adları ve image adları korunmuştur. Dosyaların yerinin değişmesiyle `.env` arama bağlamı da etkilenebilir; depoda `.env` yoktur. Başka çalışma dizini veya sonradan eklenen yerel env dosyası için ayrıca doğrulama gerekir.

C3.3.3 çalıştırıcısının `--auto-routes` seçeneği aynı Compose katmanlarıyla ayrı **T02-AUTO-ROUTES** koşusunu başlatır. Backend, bu koşuda T01 başlangıç denetiminden sonra boş önbellekten canlı planner sorguları yürütür. Tarihsel T01–T10 seçkisi için seçenek verilmez. [Komutlar ve ölçütler](../../docs/validation/c3/c3-3-4-task-5-6-commands-2026-11-05.md)

`--energy-policy` seçeneği ayrı **YAML-ENERGY-POLICY** koşusunu başlatır. Aynı canlı Nav2 mesafeleri ve iki Executor'dan alınan SoC ile iki YAML marjını karşılaştırır. Kabul ölçütü SQLite görevi ve Outbox kaydıdır. [Görev 7 komutları](../../docs/validation/c3/c3-3-4-task-7-commands-2026-11-05.md)

`--high-preemption` seçeneği ayrı **T04-HIGH-E2E** koşusunu başlatır. İki Executor gerçek taşıma başlatır. Fleet Manager, boş rota önbelleğiyle Nav2'ye sorgu gönderir ve güvenli terminal iptalden sonra HIGH görevi tamamlatır. Bu koşuda tarihsel T04'teki kontrollü mesafeler kullanılmaz. [C4 geçiş kanıtı](../../docs/validation/c3/c3-3-4-final-c4-gate-2026-11-05.md)

C2.3 ve C3.3.3 çalıştırıcıları `--domain` değerini DDS env dosyası üzerinden iki servise geçirir. Docker init, test supervisor'ına durdurma sinyali iletir. Supervisor Executor'ları ve geçici besleyiciyi durdurur, navigasyon ve lokalizasyon lifecycle yöneticilerini sırayla kapatır, ardından ayrı Nav2 süreçlerini launch üzerinden bekler. TF ve bridge'den sonra Gazebo kapanır. Compose'un 40 sn süresi bu sıralı kapanışın üst sınırıdır. Runner hem backend sonucu hem simulation kapanış işaretini ve launch alt süreç hatalarını denetler.

## Image bağımlılıkları

C4.1 doğrulaması iki robotlu Gazebo dünyasını ve ortak kapanış supervisor'ını kullanır. Yalnız Gazebo, bridge, robot başına Battery Simulator ve DDS gözlemcisi çalışır. Katman iki servis için C1 bağımlılıklarını içeren C3.3.3 backend image'ını kullanır. Ayrı DDS domain'i ve `--no-build` ile [C4.1 komut ekini](../../docs/validation/c4/c4-1-commands-2026-11-06.md) izleyin.

C4.2, DDS → A → C3.3.3 → C4.1 → [C4.2](docker-compose.simulation-c4-2.yml) katmanlarıyla çalışır. Son katman gerçek Battery Simulator ve Executor'ları başlatır. PID paylaşımı, yalnız canlı kabulde batarya süreçlerini kısa süre duraklatmak içindir. [C4.2 çalıştırma ve kapanış komutları](../../docs/validation/c4/c4-2-commands-2026-11-06.md)

C4.3 aynı image'larla ve `--no-build` ile çalışır. `C43_EVIDENCE_DIR` boş bir host dizinine işaret eder. Bu dizine koşunun SQLite veritabanı yazılır. Yalnız kabul koşusunda ikinci robotun gerçek Battery Simulator düğümü %24 SoC ile başlatılır. [C4.3 çalıştırma ve kapanış komutları](../../docs/validation/c4/c4-3-commands-2026-11-06.md)

C4.4 katmanı Gazebo dünyasına yapılandırılmış fiziksel dock pedlerini ve robot başına damgalı poz yayını ekler. Aynı host bind dizininde `c44.sqlite3` oluşturur. Test kopyasındaki başlangıç enerjisi ve şarj gücü [C4.4 raporunda](../../docs/validation/c4/c4-4-validation-2026-11-06.md) ayrı kaydedilir.

C4.5, `C45_PROFILE=energy` ve `C45_PROFILE=charging` profillerini ayrı temiz projelerde çalıştırır. Her profil ayrı SQLite ve log kanıtı üretir. [C4.5 komut eki](../../docs/validation/c4/c4-5-commands-2026-11-06.md)

DDS image'ı temel alınır; A, B1 ve Nav2 image'ları aşamalı hazırlanır. Action image'ı da DDS tabanına bağlıdır. B2/AMCL/B3/Retry katmanları Nav2 image adını kullanırken A katmanının build tarifini miras alır. Bu mevcut davranış organizasyon sırasında değiştirilmedi. Bu birleşimlerde `build` veya `up --build` doğru Nav2 bağımlılık image'ını üretme garantisi vermez; [B2 hazırlık kanıtı](../../docs/validation/simulation/b2/simulation-stage-b2-2026-10-23.md) esas alınmalıdır.

C3.3.3 backend image'ı mevcut Nav2 image'ından türetilir ve `requirements-c1.txt` bağımlılıklarını kurar. Üç C3.3.3 katmanıyla yalnızca `build backend` çalıştırın. Simülasyon servisi mevcut Nav2 image'ını kullanır. [Image hazırlama komutu](../../docs/validation/c3/c3-3-4-task-7-commands-2026-11-05.md)

## Tarihsel komutlar

[Doğrulama kayıtlarındaki](../../docs/validation/README.md) komut ve çıktılar geçmiş koşuların kanıtıdır; içlerindeki eski kök Compose yolları korunur. Yeniden kullanımda her `-f docker-compose.*.yml` yolu `-f docker/compose/docker-compose.*.yml` olarak uyarlanır. Test kodu ve config yolları değişmedi. B3 Retry host betiğinin aktif Compose referansları güncellendi.

24 Ekim 2026 organizasyon kontrolünde sekiz birleşimin çözümlenen yapılandırması taşıma öncesiyle eşdeğerdir. Bu kontrol image derlemesi veya canlı ROS/Gazebo testi değildir.
