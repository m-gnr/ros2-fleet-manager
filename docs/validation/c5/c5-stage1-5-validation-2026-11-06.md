# C5 / Aşama 1.5 — Açık temalı 3D operasyon paneli doğrulaması

**6 Kasım 2026 · İki robotlu Gazebo Fortress ve Chrome kabulü DOĞRULANDI**

[Komut eki](c5-stage1-5-commands-2026-11-06.md) · [Teknik tasarım](../../design/c5-3d-operations.md) · [Onaylı görünüm kararı](../../decisions/c5-stage1-5-3d-decision-2026-11-06.md)

## Git ve kapsam

| Kayıt | Doğrulanan değer |
|---|---|
| Başlangıç `main` ve `origin/main` | `32e23fce62026a1d50aa2f04e85c8c38a6ee5d76`, C4.5 kabulü |
| C5 Aşama 1 | `76a80abb5d35ca5a4e7005b145d0c83ce3104b0e`, `feat/c5-readonly-dashboard`, `ros2-fleet-manager-c5-dashboard` |
| Visualizer Aşama 4 | `f3e39017514b5ee2ef2da199c2f8615b9b5d25b6`, `feat/fleet-visualizer-nav2-routes`, `ros2-fleet-manager-nav2-routes` |
| Entegrasyon | `feat/c5-3d-operations-dashboard`, `ros2-fleet-manager-c5-3d-dashboard`, C5 Aşama 1 tabanlı |

Ana worktree'deki değiştirilmiş doküman haritası ile izlenmeyen PDF ve rapor dizini korundu. C5 Aşama 1 ve Visualizer worktree'leri başlangıçta ve doğrulama sonrası temizdi. Entegrasyon ayrı yerel commit olarak kayıtlıdır. Uzakta entegrasyon dalı bulunmadı. Push ve merge yapılmadı.

Değişiklikler [C5 API ve köprü relay'i](../../../backend/dashboard), [C5 operasyon kabuğu ve Visualizer kökenli sahne](../../../frontend/src), [salt okunur ROS köprüsü](../../../fleet-visualizer/bridge), [Compose kabul katmanı](../../../docker/compose/docker-compose.simulation-c5-3d.yml), [Chrome kabulü](../../../frontend/tests/live-acceptance.mjs), [API testleri](../../../tests/test_c5_dashboard.py), karar, diyagram ve kanıt dosyalarındadır. Fleet Manager, Scheduler, Executor, C4, Nav2, AMCL, Gazebo, SQLite ve Outbox ürün kaynakları değişmedi.

## Canlı kabul

- Apple Silicon üzerinde ARM64 Humble, CycloneDDS, Gazebo Fortress ve Google Chrome `156.0.8078.80`. `fleet-c5-scene-final` projesi temiz SQLite ve DDS domain 117 ile başlatıldı. Chrome yalnız C5 `/ws/fleet` bağlantısını açtı. [Chrome kabul çıktısı](stage1-5/measurements/chrome.log)
- İki TurtleBot3 aynı açık ve izometrik başlangıç sahnesinde görüntülendi. Seçim kartlar, 3D model ve sağ panelde aynı robot kimliğini kullandı. Takip, üstten, filo kadrajı ve sıfırlama canlı koşuda, orbit, pan, zoom ve klavyeyle seçim Chrome fixture testinde doğrulandı. Mobil görünüm 390 px'de yatay sayfa taşması olmadan açıldı.
- Chrome'da 1.864 çizilmiş robot pozu relay TF konumu ve yönüyle eşleşti. İz çizgilerinin her ucu doğrulanmış TF örneğine karşılaştırıldı. Bağımsız ROS okuyucusunda aynı simülasyon damgasına sahip 4.443 pozun konum farkı 0 m, en büyük yön farkı `6,67 × 10⁻¹⁶ rad`. Robot 1 için 64, robot 2 için 65 gözlemlenen Nav2 planı konu, damga ve tüm noktalar üzerinden birebir eşleşti. Çizilen plan ve iz noktaları Three.js düzlemine aynı dönüşümle aktarıldı. [ROS/Chrome karşılaştırması](stage1-5/measurements/ros-chrome-compare.json)
- Gözlemlenen planlar kesik, TF izleri düz çizgiyle sunuldu. Plan Durum B etiketi taşıdı. İz, kesinti ve epoch sınırlarında bölündü. Ana depo rafları ve koridorlar temsili geometri olarak etiketlendi.
- Robot 2 TF testi sırasında son kabul edilen pozunda STALE kaldı. Robot 1 TF LIVE ve ürün ölçümleri güncel kaldı. Köprü durdurulup başlatıldığında ürün oturumu korundu ve snapshot sırası ilerledi. FastAPI yeniden başlatılınca batarya gizlendi ve görev/rezervasyon kayıtları son eşitleme olarak işaretlendi. Kaynak oturumu korunarak yeni API oturumu yaklaşık 1,11 sn'de alındı. Ürün kaynağı kesikken açık TF'nin güncel kalması ayrıca entegrasyon ve Chrome fixture testleriyle doğrulandı.
- İki robotun doğrulanmış şarjı ve üç taşıma görevinin tamamlanması görüldü. C5 kabul okuyucusu ürün SoC/Wh ve pozunu aynı damgalı ROS ölçümleriyle, görev ve rezervasyon durumlarını SQLite ile karşılaştırdı. C4.5 fiziksel şarj ve güvenli terminal duruş seçkisi geçti. Chrome kapatılıp açıldığında ürün akışı aynı kaynak oturumunda ilerledi.
- Köprü grafiğinde `/clock` ile robot başına TF, plan ve Nav2 durum abonelikleri görüldü. Publisher, servis ve action uçları boştu. C5 salt okunur testleri kontrol isteklerini reddetti. Chrome kabulünde kritik WebGL veya JavaScript hatası görülmedi. Üç konteyner çıkış kodu 0 ve OOM false olarak kapandı. SQLite bütünlük sonucu `ok`, yabancı anahtar ihlali sıfırdı. [Köprü ROS grafiği](stage1-5/measurements/bridge-graph.txt) · [Kapanış](stage1-5/measurements/shutdown.txt)

## Performans

Chrome headless, 1440×900, canlı iki robot ve sahne ölçüm izi açık. Katman karşılaştırması ardışık yaklaşık beş saniyelik pencerelerden gelir. CPU değerleri bir çekirdeğin yüzdesi, Chrome RSS değerleri Chrome süreçlerinin toplamıdır.

| Ölçüm | Plan ve iz açık | Plan ve iz kapalı |
|---|---:|---:|
| Sahne FPS | 58,0 | 58,2 |
| Sahne frame aralığı p95 | 18,0 ms | 17,8 ms |
| Draw call p95 | 59 | 53 |
| Geometri / texture | 59 / 3 | 59 / 3 |
| JS heap | 14,2 MiB | 15,2 MiB |
| Chrome CPU / RSS | %34,1 / 888,4 MiB | %35,0 / 887,7 MiB |
| FastAPI CPU / RSS | %2,1 / 48,8 MiB | %1,9 / 48,8 MiB |
| ROS köprüsü CPU / RSS | %11,2 / 71,0 MiB | %10,5 / 71,0 MiB |
| WebSocket toplam / ürün / sahne | 51,9 / 4,17 / 46,81 Hz | 50,7 / 4,02 / 45,75 Hz |

İlk DOM etkileşimi 3,86 sn, sahne modülü indirmesinin bitişi 3,91 sn, ilk WebGL çizimi 4,08 sn ve klavyeyle seçimin Chrome kontrolü 28 ms ölçüldü. Rota/iz katmanları bu pencerede p95'te altı ek draw call üretti. Farklı anlarda alınan CPU ve heap örnekleri birlikte raporlanmıştır. [Ham tarayıcı ölçümleri](stage1-5/measurements/browser-metrics.json)

## Regresyonlar

| Seçki | Yeni koşu sonucu |
|---|---|
| Host Python ve Executor | 416 geçti, ROS gerektiren 28 test atlandı |
| Humble/CycloneDDS ve Executor | 464 geçti. C2.3 ve C3.3.3 config testleri 3 + 3 geçti |
| C5 Chrome | Aşama 1 tabanında 5 geçti, Aşama 1.5 entegrasyonunda 6 geçti |
| Visualizer Aşama 1–4 | Bağımsız frontend'de 21 geçti ve derlendi. Humble köprüsünde 25 geçti |
| C3.3.3 ve HIGH | T01–T10 (10/10) ve ayrı T04-HIGH-E2E geçti. İki simülasyon temiz kapandı. |
| C4.5 | Canlı şarj geçti. Ayrı enerji profili geçti. Konteynerler çıkış 0 ile kapandı, SQLite sonucu ok. |
| Üretim frontend build ve npm audit | Derleme geçti. Denetimde 0 zafiyet |

İlk birleşik Humble koşusunda bir C4.2 DDS keşif testi, yayımcı listesi boş döndüğü için kaldı. Son bağımsız tam koşu aynı ürün koduyla 464/464 geçti. İlk canlı Chrome denemesi gerçek veriyi çizdi ve C4.5 şarjı tamamladı. Performans betiğinin sabit PID varsayımı düzeltildikten sonra temiz canlı koşu bütün Chrome denetimlerini tamamladı.

## Kapsam sınırları ve ekran görüntüleri

Bu kanıt iki robot ve yerel kabul topolojisi içindir. 3+ robot, uzun süreli kaynak kullanımı ve nihai ürün Compose'u **HENÜZ TEST EDİLMEDİ**. Köprü dört eşzamanlı TF istemcisiyle sınırlıdır. Gözlemlenen planın aktif goal UUID ilişkisi doğrulanmamıştır.

- [İzometrik açık depo ve iki canlı robot](stage1-5/screenshots/isometric-two-robots.png)
- [Seçili robot ayrıntıları](stage1-5/screenshots/selected-robot.png)
- [Canlı taşıma, Nav2 planı ve TF izi](stage1-5/screenshots/active-task-plan.png)
- [Doğrulanmış şarj](stage1-5/screenshots/charging-scene.png)
- [Tek robotta TF STALE](stage1-5/screenshots/isolated-tf-stale.png)
- [FastAPI bağlantı kesintisi](stage1-5/screenshots/connection-loss.png)
- [390 px mobil görünüm](stage1-5/screenshots/overview-390.png)

Ham Compose ve bağımsız ROS kayıtları `/tmp/fleet-c5-scene-final`, regresyon çıktıları `/tmp/fleet-c5-scene-regressions` altında saklandı.
