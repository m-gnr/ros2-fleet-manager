# C5 Docker preflight ve çoklu simülasyon kontrolü — 17 Kasım 2026

## Uygulama

**DOĞRULANDI (hedefli host testi).** `scripts/run_c5_dashboard.sh` `up`, `create`, `start`, `restart` veya `run` komutundan önce Docker preflight çalıştırır. `api` ve `stop-api` alt komutları çalışan simülasyonun parçası olduğu için yeni simülasyon başlangıcı sayılmaz.

Preflight çalışan container listesini, durumunu, CPU/bellek kullanımını ve Compose project/service etiketlerini raporlar. Her container'ın çalışan süreçleri `docker top` ile taranır; Gazebo/Nav2/ROS 2/Fleet Manager kanıtı bulunan simülasyon container'ları süreçlere göre belirlenir. Compose projesi yalnız eşlikçi servisleri birleştirmeye yardım eder; aynı Compose proje adındaki birden çok aktif demo container'ı ayrı simülasyon olarak listelenir.

Başka aktif simülasyon saptanırsa normal başlangıç engellenir ve container adlarıyla kaynak tüketimi gösterilir. Hiçbir container durdurulmaz veya silinmez. Kullanıcı bilinçli şekilde birlikte çalıştırmak isterse `--allow-concurrent-simulation` açıkça verilir ve override stdout'a yazılır. Docker listesi, süreç incelemesi, istatistik veya VM kapasitesi ölçülemezse sistem temiz kabul edilmez ve başlangıç kapalı kalır.

## Canlı Docker gözlemi

Yalnızca okuma yapan preflight 17 Kasım koşusunda üç aktif demo container'ı saptadı:

| Container | Süreç kanıtı | CPU | Bellek |
|---|---|---:|---:|
| `c5-alpha-beta-gamma-live-retry1-20261117` | Gazebo, ROS 2, Nav2, Fleet Manager | %392.1 | 1589.2 MiB |
| `c5-alpha-beta-stable-live-20261117` | Gazebo, ROS 2, Nav2, Fleet Manager | %212.4 | 1089.5 MiB |
| `c5-alpha-beta-manual-20261117` | Gazebo, ROS 2, Nav2, Fleet Manager | %299.3 | 967.1 MiB |

Aynı Docker gözleminde `c5-v031-stall-20261117` (0.0%, 4.2 MiB) ve `c5-actuator-timeout-20261114` (0.0%, 36.9 MiB) da çalışan container olarak raporlandı; bu örnekte süreç taraması bu ikisinde simülasyon sinyali bulmadı.

Docker VM kapasitesi 8 CPU ve 7934.4 MiB RAM olarak bildirildi. Container ölçümleri toplamı anlık örnekte 903.8% CPU ve 3687.0 MiB RAM idi; CPU toplamı 8 CPU kapasitesini aştığı için uyarı verildi. Bu değerler anlık Docker container ölçümleridir; VM içindeki container dışı süreçleri kapsamaz ve eşik bir güvenlik garantisi değildir.

Aktif demo oturumlarına dokunulmadı. İsimler ve tüketimler anlık örnektir; sonraki çalıştırmada değişebilir.

## Hedefli doğrulama

- Boş container envanteri ve ölçülebilir VM: launcher preflight'tan sonra fake Compose `up` çağrısına ulaştı.
- Başka simülasyon: başlangıç engellendi, simülasyon ve eşlikçi container adları gösterildi, `docker stop` çalıştırılmadı.
- Açık override: `--allow-concurrent-simulation` raporlandı ve fake Compose `up` çağrısına geçildi.
- Docker VM ölçüm hatası: başlangıç kapalı kaldı.
- Test kapsamı `scripts/run_c5_dashboard.sh` başlatma yolu ve mocked Docker CLI'dır; yeni gerçek Gazebo/Nav2 koşusu başlatılmadı.

Komutlar ve koşu çıktısı [komut ekindedir](docker-simulation-preflight-commands-2026-11-17.md).
