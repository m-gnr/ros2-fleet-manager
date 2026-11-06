# Fleet Visualizer Aşama 4 doğrulama raporu

6 Kasım 2026. **DOĞRULANDI** — İki robotun TF hareket izi ve **Durum B, GÖZLEMLENEN NAV2 PLANI**. Canlı kabul Gazebo Fortress, Humble/CycloneDDS ve Chrome 156.0.8078.80 ile yapıldı. [Teknik tasarım ve WebSocket sözleşmesi](../../../design/fleet-visualizer-stage-4.md) · [Nav2 kaynak incelemesi](nav2-source.md) · [Komut eki](commands.md).

## Git ve değişiklik kapsamı

Başlangıçta `main`, yerel `origin/main` ile aynı C4.5 commit'indeydi (`32e23fce62026a1d50aa2f04e85c8c38a6ee5d76`). Ana worktree'de değiştirilmiş `docs/README.md` ile izlenmeyen literatür PDF'si ve `docs/reports/` vardı. Aşama 3 dalı ve kendi worktree'si, kabul raporunu ve kodu içeren `7cf6e7edf31bcf54c4554bf1c1fe2f72be044036` commit'indeydi. Aşama 4 için bu commit'ten `feat/fleet-visualizer-nav2-routes` dalı, `ros2-fleet-manager-nav2-routes` worktree'sine açıldı. Ana worktree ve önceki doğrulama kanıtları korundu. Push ve merge yapılmadı.

| Dosyalar | Değişiklik |
| --- | --- |
| `fleet-visualizer/bridge/{observed_plan,ros_reader,run,server,telemetry}.py` | Robot bazlı ROS kaynak kontrolü, Path doğrulaması, TTL, V1 plan ve temizleme paketleri |
| `fleet-visualizer/bridge/tests/plan*_checks.py` | Sıralama, sınır, DDS kaynak kaybı, durum geçişi, yeniden bağlantı ve yavaş istemci testleri |
| `fleet-visualizer/frontend/src/{routes.ts,routes.test.ts,RouteLayers.tsx,Scene.tsx,telemetry.ts,useTelemetry.ts,main.tsx,style.css}` | TF iz tamponu, ayrı plan durumu, 3D katmanlar, kontroller ve frontend testleri |
| `fleet-visualizer/frontend/validation/routes-live.mjs` ve `fleet-visualizer/validation/` | Chrome, bağımsız Path ve TF gözlemleri, karşılaştırmalar |
| `fleet-visualizer/README.md`, `docs/README.md`, `docs/design/fleet-visualizer-stage-4.md`, bu dizin | Kullanım, sözleşme, karar, komutlar ve canlı kanıt |

Ürün, C5, Compose, launch ve test konfigürasyonu değişikliği yoktur. Köprü grafiği yalnız `/clock` ile robot başına `tf`, `plan` ve `NavigateToPose` durum aboneliklerini gösterdi. Publisher, service client/server ve action client/server listeleri boştu. [Köprü grafiği](measurements/bridge-endpoints.txt).

## Canlı Path, TF ve Chrome

`/robot_1/plan` ve `/robot_2/plan`, ilgili robotun Planner Server düğümünden RELIABLE / VOLATILE / KEEP_LAST (1) ile geldi. `map` geometrisi iki bağımsız robot durumunda tutuldu. Path ile aktif hedef arasındaki bağ belirsiz olduğu için panel her iki robotta gözlem etiketi kullandı. Bağımsız ROS gözlemcisi `robot_1` için 83, `robot_2` için 74 Planner Server mesajı kaydetti. Chrome'a ulaşan 67 ve 65 paketin tamamı, robot, topic ve damga üzerinden eşleştirildiğinde tüm noktalarıyla ROS kaydına eşitti. Gözlemci aynı koşuda yeniden planlama, terminal başarı ve `robot_1` için C4.5 HIGH olayındaki Nav2 goal'unun CANCELING ve CANCELED durumlarını kaydetti. [Canlı Path örnekleri](measurements/nav2-source-samples.json) · [C4.5 güvenlik kaydı](measurements/c45.txt).

| Son Chrome koşusundaki karşılaştırma | `robot_1` | `robot_2` |
| --- | ---: | ---: |
| ROS → WS bire bir eşleşen Path | 67/67 | 65/65 |
| Bağımsız TF ile aynı damgada karşılaştırılan iz noktası | 336 | 411 |
| TF → WS iz noktası farkı < 1 µm | 335/336 | 411/411 |
| TF → WS iz noktası en büyük fark | 13,57 mm | 0 m |
| WS plan/iz → 3D katman en büyük yatay fark | 1,55 × 10⁻⁷ m | 1,57 × 10⁻⁷ m |
| Plan temizleme paketi | 13 | 6 |

İlk canlı koşuda birleşik TF gözlemcisine karşı `robot_1` için 194 iz eşleşmesinden birinde 8,99 mm fark, 459 kök eşleşmesinden ikisinde 9,24 mm'ye varan fark bulundu. Son Chrome koşusu, birleşik TF aktarımı yerine her robotun namespaced TF akışına doğrudan abone olan bağımsız gözlemciler kullandı. `robot_1` için 222 kök eşleşmesinden ikisi 1 µm eşiğini aştı. `robot_2` için 148 kök eşleşmesinin tamamında fark 0 m oldu. Farkın kaynağını inceleyen ayrı C4.5 şarj koşusu, köprünün kullandığı AMCL damgalarını izledi ve bağımsız kaydedilen ham `map → odom → base_link` kenarlarından her robot için 2.415 pozu yeniden hesapladı. En büyük yatay fark sırasıyla 2,71 × 10⁻¹⁵ ve 3,04 × 10⁻¹⁵ m oldu. Santimetre ölçeğindeki fark bu koşuda tekrarlanmadığı için önceki örneklerin nedeni kesinleştirilemedi. [İlk karşılaştırma](measurements/compare-first.json) · [Son karşılaştırma](measurements/compare.json) · [Ham TF kenarlarından yeniden hesaplama](measurements/tf-reconstruction.json).

Chrome, iki modeli aynı kadraja aldı. Rota çizimleri kesikli ve uç işaretli, hareket izleri ince ve parçalıydı. Test, kaynak ve damga eşleşmesini GPU buffer'larına yazılan geometri üzerinden denetledi. Seçim, yalnız seçili robot, vurgu ve iki katmanın görünürlük kontrolleri çalıştı. `robot_1` planı `STALE` durumuna geçip gizlendi ve sonraki yeni planlar kendi damgalarıyla gösterildi. Kritik WebGL veya JavaScript hatası görülmedi. [Chrome sonuçları](measurements/routes-result.json).

## Kesinti ve C4 bağımsızlığı

Kabul sarmalayıcısı yalnız Visualizer'ın `robot_1` TF girişini kesti. WebSocket bağlı kaldı, `robot_1` STALE oldu ve son iz damgası 79,765 sn'de sabit kaldı. `robot_2` LIVE kaldı ve izine nokta ekledi. Giriş geri açıldığında `robot_1` 81,025 sn'de yeni bir segment başlattı. Eski ve yeni ölçümler arasına çizgi eklenmedi. [Kesinti ölçümü](measurements/isolated-cut.json).

Köprü kapandığında tarayıcı DISCONNECTED ve iki robot STALE gösterdi. Aynı sırada ROS grafiğinde Fleet Manager, iki Nav2 ve iki Battery Simulator vardı. Köprü yeniden başladığında iki robot yeni pozla LIVE oldu. Aynı C4.5 şarj koşusu 13 bağımsız duruş örneğiyle sıfır doğrusal ve açısal hızı, eski terminal epoch 3'ün engellenmesini ve LOW görevinin epoch 5 ile devamını doğruladı. Backend, simülasyon ve köprü 0 ile kapandı. Enerji ve şarj SQLite dosyalarında bütünlük `ok`, foreign-key çıktısı boştu. [Köprü kapalı grafik](measurements/bridge-off.json) · [Yeniden başlama](measurements/bridge-on.json) · [C4.5 kanıtı](measurements/c45.txt).

## Performans

Chrome 1280 × 850, Standart kalite, DPR 1 ve `?trace`. Aşama 4 açık ve kapalı ölçümler, aynı C4.5 şarj koşusunda iki robot kadrajdayken art arda 4,50 sn'lik pencerelerden alındı. Katmanları kapatınca ROS/WS ve iz biriktirme devam etti. Aşama 3 sütunu ayrı tarihsel filo kadrajı koşusudur. [Aşama 3 ölçümü](../stage-3/measurements/performance-fit.json) · [Açık](measurements/layers-on.json) · [Kapalı](measurements/layers-off.json).

| Ölçüm | Aşama 3 tarihsel | Aşama 4 açık | Aşama 4 kapalı |
| --- | ---: | ---: | ---: |
| Ortalama FPS | 59,32 | 59,97 | 59,98 |
| p95 kare aralığı | 17,60 ms | 18,10 ms | 18,50 ms |
| En çok draw call / üçgen | 53 / 4.656 | 59 / 6.558 | 55 / 4.656 |
| En çok geometri / texture | 53 / 3 | 59 / 3 | 59 / 3 |
| Pencere sonu JS heap | 14,38 MiB | 12,87 MiB | 14,13 MiB |
| Chrome CPU / RSS | %40,54 / 884,88 MiB | %38,96 / 1.131,42 MiB | %40,36 / 1.130,58 MiB |
| Poz/sn, robot 1 / 2 | 19,48 / 19,68 | 20,09 / 20,09 | 20,07 / 20,07 |
| Path/sn, robot 1 / 2 | — | 1,08 / 0,86 | 0,87 / 1,09 |
| Pencere sonu iz noktası, robot 1 / 2 | — | 150 / 41 | 191 / 80 |

Tüm son canlı koşuda en büyük WS Path mesajı robot 1 için 10.807 bayt / 258 nokta, robot 2 için 8.573 bayt / 203 noktaydı. Köprü kesintisinden önceki 20 Docker örneğinde CPU medyanı %9,77 (aralık %9,00–14,42), RAM medyanı 51,02 MiB (50,45–51,36) oldu. Chrome CPU bir çekirdek üzerinden hesaplandı. RSS tarayıcı süreç toplamıdır. Pencerelerin hareket ve plan yoğunluğu farklıdır. Kısa örnekler, uzun süreli kaynak veya ölçek garantisi vermez. [Docker ölçümü](measurements/bridge-stats.json).

| Gecikme p50 / p95 | `robot_1` | `robot_2` |
| --- | ---: | ---: |
| TF alımı → köprü WS gönderim sonu | 19,76 / 36,90 ms | 16,52 / 32,69 ms |
| Path alımı → köprü WS gönderim sonu | 28,82 / 47,95 ms | 27,99 / 46,77 ms |
| Tarayıcı poz alımı → tam kök pozunun çizildiği kare | 45,70 / 60,50 ms | 56,00 / 60,90 ms |
| Tarayıcı Path alımı → geometrinin hazırlandığı kare | 7,70 / 14,00 ms | 8,50 / 15,80 ms |

Köprü ve tarayıcı ayrı monotonik saatler kullanır. Tek yön ağ gecikmesi ayrı ölçülmedi. [Gecikme ölçümleri](measurements/compare.json).

## Yeni regresyon sonuçları

| Kapsam | Sonuç |
| --- | --- |
| Visualizer Python host | 19 geçti, ROS gerektiren iki modül atlandı |
| Visualizer Python Humble/CycloneDDS | 25 geçti |
| Visualizer frontend | 21 geçti, üretim derlemesi geçti |
| Chrome fixture | Mevcut kamera, kalite, dar ekran, epoch, yeniden bağlantı kontrolleri geçti. Fixture yalnız regresyon kanıtıdır. [Sonuç](measurements/chrome-fixture.json) |
| Host ürün Python ve Executor | 409 geçti, 28 ROS bağımlı test atlandı |
| Tam Humble/CycloneDDS ürün ve Executor | İzole tekrar 457 geçti |
| C3.3.3 canlı | T01–T10, 10/10 geçti. İki konteyner 0 ile kapandı. [Sonuç](measurements/c333.txt) |
| C4.5 enerji ve şarj | Temiz profiller geçti. Şarjda iki robot hareketi, preemption ve SQLite yeniden doğrulandı. [Sonuç](measurements/c45.txt) |

İlk Humble ürün koşusunda `test_discovery_waits_for_ros_node_identity` başarısız oldu ve 456 test geçti. İlgili test tek başına, ardından tam paket izole konteynerde geçti. İlk Path gözlemcisi Humble callback'inde yayıncı metadatasını ikinci argüman sanıyordu. Nav2 mesajı alınırken TypeError oluştu. Gözlemci tek argüman ve ayrı ROS grafik kaydına geçirildi. Bir sonraki temiz Compose projesi Docker adres havuzu dolu olduğu için başlamadı. Bu göreve ait tamamlanmış projelerin ağları kaldırıldıktan sonra yeni proje başarıyla başladı.

Saat geri sarımı, hatalı frame, sıra, tekrar, kaynak kaybı ve restart/reconnect korumaları birim/Humble testlerindedir. Canlı Gazebo saat geri sarımı, üç ve üzeri robot ve farklı ROS/DDS topolojileri **HENÜZ TEST EDİLMEDİ**. Goal UUID ile plan eşleştirme ve paket başına DDS yazıcı GID'si doğrulaması bu kurulumda yapılamadı.

## Canlı ekran görüntüleri

- [Robot 1 gözlemlenen Nav2 planı](screenshots/robot-1-observed-plan.png)
- [İki hareket izi ve bağımsız Nav2 planları](screenshots/two-live-trails-observed-plan.png)
- [Robot 1 STALE, robot 2 canlı iz](screenshots/robot-1-stale-robot-2-trail.png)
