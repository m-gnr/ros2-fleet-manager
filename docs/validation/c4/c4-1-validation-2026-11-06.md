# C4.1 — Battery Simulator tüketim doğrulaması

6 Kasım 2026. [Komut eki](c4-1-commands-2026-11-06.md) · [C4 geçiş onayı](../c3/c3-3-4-final-c4-gate-2026-11-05.md)

## Başlangıç

Yerel `main`, izlenen `origin/main` ve doğrudan GitHub sorgusu, C3.3.4-FINAL commit'i `2cfc2f2c2903af9cf33bd8d02a607b7abd55b941` üzerinde eşleşti. Çalışma ağacındaki `docs/README.md`, `docs/gereksinim-literatur-ozgunluk-2026-10-27.pdf` ve `docs/reports/` kullanıcı değişiklikleri korundu.

## Mimari ve model

Nihai mimari kararların 8. bölümü uyarınca her robotun namespace'inde bir `fleet_battery_simulator` düğümü çalışır. Tek çok robotlu düğüm, her callback'te robot kimliğiyle durum ayırmayı gerektirirdi. Robot başına tek örnek, göreli topic'leri ve tek enerji durumunu doğrudan eşler. Canlı senaryo, düğüm örneklerini C1'le doğrulanan `fleet.yaml` robot listesinden üretir. [Nihai kararlar](../../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.pdf)

Simülatör mevcut C1 doğrulayıcıdan `usable_capacity_wh`, `consumption_wh_per_meter` ve `idle_power_w` alır. Eksik alan, geçersiz değer, hatalı model referansı ve bilinmeyen robot kimliği açılışı durdurur. C1'de başlangıç SoC alanı bulunmadığından yeni senaryonun başlangıcı yapılandırılmış kapasitenin %100'üdür. Her süreç başlangıcı bu başlangıç politikasını uygular. Tüketilmiş durum depodan yüklenmez. Süreç canlıyken saat geri sarılırsa kalan Wh korunur. [C1 sözleşmesi](../../configuration-c1.md)

- `E_motion = consumption_wh_per_meter × delta_s_m`
- `E_idle = idle_power_w × delta_t_sec / 3600`
- `E_remaining = max(0, E_previous − E_motion − E_idle)`
- `SoC_percent = 100 × (E_remaining / usable_capacity_wh)`

Taban güç hareket, duruş, yükleme ve boşaltma boyunca aynı anda işler. Scheduler, kendi rota tabanlı tahminini ve kabul edilmiş `RobotStatus` verisini görev uygunluğu için kullanmaya devam eder. C4.1 fiziksel tüketimi yalnız Battery Simulator'da işler. [Çekirdek](../../../ros2_ws/src/fleet_battery_simulator/fleet_battery_simulator/consumption.py)

## Saat ve odometri

- Tek fiziksel saat Gazebo bridge'inin `/clock` akışıdır. Düğüm `use_sim_time: true` ile başlar. İlk geçerli saat yalnız referansı kurar. Eşit saat tüketim ve yayın üretmez. Geri sarma odometri kuyruğunu, son kabul edilen damgayı ve mesafe referansını temizler. İleri saat, odometri eksikken de taban gücü ilerletir.
- Gazebo DiffDrive, odometriyi 30 Hz üretir. `header.stamp` simülasyon damgasıdır. `header.frame_id` odometri koordinatlarını, `child_frame_id` hızın referansını tanımlar. Hareket, `odom` referansında ardışık XY konumları arasındaki mesafedir. Başlangıç harita pozu bu mesafeye girmez. [Humble Odometry tanımı](https://raw.githubusercontent.com/ros2/common_interfaces/humble/nav_msgs/msg/Odometry.msg)
- Odometri ve saat ayrı DDS akışlarıdır. Düğüm, saatin ±0,5 sn penceresindeki ve kendi akışında monoton artan odometri damgalarını en fazla 64 örnek bekleterek işler. Mesafe, ileri saat damgası örneğe yetiştiğinde hesaba girer. Yinelenen, eski veya sırası bozuk damgalar referansı değiştirmez. Kuyruk taşması, 0,5 sn üzerindeki örnek aralığı ve çerçeve değişimi mevcut mesafe zincirini keser.
- Sonlu konum ve hız değerleri aranır. Geçersiz örnek mesafe zincirini keser. Doğrusal hız ve örnek çiftindeki yer değiştirme 1 m/sn'lik süreye bağlı koruma sınırıyla değerlendirilir. Bu değer mevcut Nav2 0,25 m/sn üst sınırına pay bırakan veri bütünlüğü korumasıdır. Büyük sıçrama tüketilmeden yeni referans kurulur. İlk sonraki geçerli aralık yeniden tüketilebilir.

## ROS sözleşmesi

| Topic | Tip ve QoS | Sözleşme |
|---|---|---|
| `/clock` | `rosgraph_msgs/msg/Clock`, best effort, derinlik 1 | Ortak Gazebo simülasyon saati. |
| `/<namespace>/odom` | `nav_msgs/msg/Odometry`, sensor data QoS | Yalnız ilgili robotun ölçümü. |
| `/<namespace>/battery_state` | `fleet_interfaces/msg/BatteryState`, reliable, volatile, derinlik 10 | `robot_id`, kalan `battery_energy_wh`, `battery_soc_percent` (%0–100), `battery_capacity_wh`, `is_charging` ve simülasyon `battery_stamp`. |

Yayın ilk geçerli saatte ve geri sarma sonrasında hemen, ilerlerken 0,2 simülasyon saniyesi aralıkla yapılır. `is_charging` C4.1'de `false` değerindedir. Standart `sensor_msgs/BatteryState` Wh modeline karşılık gelen kapasite alanı sunmaz ve elektriksel ölçümleri Ah/V üzerinden ifade eder. `RobotStatus` ise Executor fiziksel durumuna ait alanlar taşır. Bu yüzden onaylı Wh alanları mevcut ürün IDL paketine tek küçük mesaj olarak eklendi. [Humble BatteryState tanımı](https://raw.githubusercontent.com/ros2/common_interfaces/humble/sensor_msgs/msg/BatteryState.msg) · [C4.1 IDL](../../../interfaces/fleet_interfaces/msg/BatteryState.msg)

C3.3.3 ve T02-AUTO-ROUTES koşuları kendi geçici `RobotStatus` besleyicisini kullanır. C4.1 katmanı farklı bir DDS domain'iyle başlatılır ve yalnız C4.1 batarya düğümlerini açar. Canlı ROS grafiğinde iki `battery_state` topic'inde de doğru tipte tek yayıncı ve tek `/clock` kaynağı görüldü. Executor ve Fleet Manager'a geçişte geçici besleyici önce devreden çıkarılmalı, Executor aboneliği Wh mesaj tipine geçirilmeli, robot kimliği, zaman damgası ve güncellik doğrulanmalı ve kabul edilen telemetri `RobotStatus` üzerinden FM'e iletilmelidir. Canlı batarya süreci restart'ı ve yeniden başlayan saat sonrası telemetri kabulü için senaryo sınırı ayrıca doğrulanmalıdır.

## Doğrulama sonuçları

**DOĞRULANDI** — C4.1 tüketim çekirdeği, ROS telemetrisi ve iki robotlu canlı Fortress seçkisi.

| Grup | Geçti | Başarısız | Atlandı |
|---|---:|---:|---:|
| C4.1 saf Python çekirdeği | 22 | 0 | 0 |
| C4.1 Humble topic/mesaj ve geçersiz config | 2 | 0 | 0 |
| Tam host Python + Executor | 343 | 0 | 26 |
| Tam ROS 2 Humble / CycloneDDS | 379 | 0 | 0 |
| C1 CLI ve C3.3.3 host test config | 4 | 0 | 0 |
| C2.3 ve C3.3.3 Humble test config | 6 | 0 | 0 |
| C4.1 iki robotlu canlı Fortress koşusu | 1 | 0 | 0 |
| C3.3.3 canlı T01–T10 | 10 | 0 | 0 |
| Canlı T02-AUTO-ROUTES ve T01 başlangıç kontrolü | 2 | 0 | 0 |
| C2.3 canlı T01–T07 | 7 | 0 | 0 |
| Dört canlı projede temiz kapanış | 4 | 0 | 0 |

Odaklı çekirdek ve ROS satırları tam seçkilerin alt kümeleridir. Host atlamaları macOS üzerinde `rclpy` ve Humble çalışma zamanı gerektiren modüller/testlerdir. İlk Humble derlemesi başarılıydı ancak test toplaması Humble'da bulunmayan hazır saat QoS sabitini içe aktarırken durdu. Açık best-effort/derinlik 1 profiline geçildikten sonra tam Humble seçkisi atlamasız geçti.

### İki robotlu canlı ölçüm

Ürün YAML değerleri kullanıldı. İki robotta 100 Wh kapasite, 0,20 Wh/m hareket katsayısı ve 2 W taban güç uygulandı. Hareket aşaması 6 simülasyon saniyesi boyunca 0,18 m/sn test komutu ve duruş payını içerdi. Gerçek `/clock` ve iki DiffDrive odometrisi bağımsız ölçümde kullanıldı.

| Pencere | Robot | Simülasyon süresi (sn) | Odometri mesafesi (m) | Ölçülen tüketim (Wh) | Son kalan (Wh) | Son SoC (%) |
|---|---|---:|---:|---:|---:|---:|
| Duruş | robot_1 | 3,2 | ≈0 | 0,001778 | 99,998222 | 99,998222 |
| Duruş | robot_2 | 3,2 | ≈0 | 0,001778 | 99,998222 | 99,998222 |
| Hareket | robot_1 | 7,2 | 1,080 | 0,220000 | 99,778222 | 99,778221 |
| Hareket | robot_2 | 7,2 | ≈0 | 0,004000 | 99,994222 | 99,994225 |
| Hatalı odometri | robot_1 | 3,2 | 0 | 0,001778 | 99,776444 | 99,776443 |
| Hatalı odometri | robot_2 | 3,2 | ≈0 | 0,001778 | 99,992444 | 99,992447 |

Robot 1 hareket penceresinde 0,216 Wh hareket ve 0,004 Wh taban güç harcadı. Robot 2 yalnız taban güç harcadı. Hatalı veri penceresinde robot 1'e 30 grup tekrar, 1000 m sıçrama ve NaN konum gönderildi. İki robot da beklenen taban gücü harcadı. Testte paketlerin ayrı topic'lerden geliş sırası nedeniyle hareket penceresi için 0,002 Wh, duruş için 0,0001 Wh tolerans kullanıldı. Duraklama ve saat geri sarma davranışı sentetik çekirdek ve Humble mesaj testleriyle denetlendi.

C3.3.3 T01–T10, T02-AUTO-ROUTES ve C2.3 regresyon loglarında `Failed to make progress` görülmedi. Dört canlı projede simulation/backend çıkışı 0/0, `OOMKilled=false` ve supervisor kapanışı temizdi. Docker olaylarında simülasyona SIGTERM gönderildi. Docker veya launch SIGKILL kaydı ve beklenmeyen alt süreç çıkışı görülmedi.

## Kalan sınırlar

Odometrinin kaybolduğu aralıkta hareket enerjisi tahmin edilmez. Aynı çerçevede, hız sınırı altında kalan küçük poz sıçraması ham odometriyle gerçek hareketten ayırt edilemez. Tekrar kullanılan simülasyon zamanında yeterince gecikmiş eski odometri, yeniden aynı pencereye düştüğünde ayrı bir oturum kimliği taşımadığından ayırt edilemeyebilir. Canlı kabul iki robotun kısa Fortress koşusudur. Katsayı kalibrasyonu, uzun süreli çalışma, Gazebo reset hizmetinin canlı kullanımı, şarj ve Executor'a ürün bağlantısı sonraki doğrulama konularıdır.
