# C5-A — Çalışan filo demosu / ilk entegrasyon

14 Kasım 2026. **DOĞRULANDI: tek gerçek Chrome görevi, iki Gazebo robotu ve canlı batarya görünürlüğü.** Bu kayıt C5 sensör qualification, HOLD/RESUME veya ürün kabulü değildir. [Gerçek komutlar](c5-a-first-integration-commands-2026-11-14.md).

## Kaynak ve seçilen yol

Feature worktree: `/Users/murat/develop/ros2-fleet-manager-c5-auto-charging-integration`; HEAD `ddf65e31b30d6ea49ce8c10eccf6e98879713600`. Başlangıçtaki kullanıcı değişiklikleri korundu; main, eski kanıtlar ve Docker kaynakları silinmedi. Commit/push yapılmadı.

[C3 final](../c3/c3-3-4-final-c4-gate-2026-11-05.md), [C4 kabulü](../c4/c4-acceptance-2026-11-06.md), [C5 gerçek Chrome komutları](e2e-stage1-commands-2026-11-11.md), [Aşama 1.3 canlı kayıt](c5-stage1-3-localization-approach-2026-11-11.md) ve mevcut launcher kaynakları incelendi. Mevcut `stage1_run.py`, C4 Battery Simulator ve Executor ile ortak 30×18 m profili çalıştırdı. Profilde robotlara deneysel ek engel sensörü bağlanmamıştır; bu koşu için sensör kaldırılmadı, kapı açılmadı veya qualification değeri değiştirilmedi. Mevcut lidar/Nav2, reset, oturum, epoch ve batarya kontrolleri korundu. İlk deneme fiziksel resetten sonra eski IDL nedeniyle kapandı; bu başarısızlık saklandı.

## Bağlantı hatası ve çözüm

Chrome `http://127.0.0.1:20181`; frontend `ws://127.0.0.1:20181/ws/fleet` ve `/api/*` kullanır. Vite bunları `http://127.0.0.1:20182` backend adresine proxy eder. Backend scene kaynağı container içindeki `ws://scene:20183/telemetry/fleet` adresidir; `scene` aynı container loopback aliasıdır. Frontend DDS ağına bağlanmaz.

İlk launcher `/tmp/c5-stage21-audit/install` içindeki eski IDL’yi kaynakladı. Executor import sırasında `ResumePerception` bulunamadığından çıktı; supervisor backend’i kapattı. Chrome’daki bağlantı kesintisi bunun sonucuydu. Güncel `interfaces/fleet_interfaces` ayrı `/evidence/idl-install` alanında başarıyla derlendi (1 paket, 29,4 sn); yeni dünya ve boş DB ile tekrar başlatıldı. Ürün kodu değiştirilmedi. Chrome’da **Bağlı**, iki robot, **2/2 TF LIVE**, canlı SoC ve Wh gözlendi.

## Harita ve 3B sahne

Bağlantı yokken eski `WarehouseEnvironment` statik temsili fallback’i kullanılır. Bağlantı geldikten sonra `/api/warehouse-layout`, `profile_mismatch=false` ve map çerçevesinde 30×18 m yerleşim döndürdü. Chrome ekranında **ORTAK DEPO HARİTASI**, raflar, duvarlar ve gerçek robot işaretleri görüldü.

Sahne Gazebo video aktarımı veya Gazebo mesh stream’i değildir. `GridWarehouse` görsel rafları ortak YAML geometrisinden üretir; aynı profil `fleet_config/warehouse_assets.py` ile Gazebo SDF ve Nav2 occupancy haritasını üretir. Raf görsel ayrıntıları dekoratiftir; yerleşim/boyutlar ortak kaynaktır. Robot hareketi ROS TF’den, görev/batarya Fleet Manager snapshot’ından gelir. `x → x`, `y → -z` dönüşümü uygulanır. Kaynak ve arayüz eşleştiği için yeni geometri değişikliği gerekmedi.

## Gerçek görev kanıtı

Chrome formundan LOW `pick_A1 → pick_B1` gönderildi; task ID `web-12dd7189-f174-49ce-bb87-29163728342f`. Scheduler `robot_alpha` seçti. İkinci robot `(5,25; 7,75)` m doğu park konumunda kaldı; taşıma batıda yapıldı. Gerçek Nav2 pickup ve dropoff sonuçlarının ikisi de `SUCCEEDED` (4); Executor yükleme/boşaltma işlemlerini tamamladı.

- ExecuteTask UUID: `27f40f93-2de4-482b-8329-ef00a7ae2cf1`.
- SQLite `COMPLETED`, `assignment_epoch=1`; gerçek action result `completed_epoch=1`, status=1 ve ROS terminal status=4.
- Aynı task/epoch/UUID ile tek `EXECUTE_TASK` Outbox satırı, `SENT`, `attempts=1`; review hold yok.
- Chrome’da aynı task ID için **Tamamlandı** görüldü. Fixture/interception veya terminal taklidi kullanılmadı.
- İki bağımsız gerçek Battery Simulator yayını ve Chrome’da değişen SoC/Wh gözlendi; şarj döngüsü bu koşunun kapsamı değildir.

## Kanıt, sınır ve açık çalışma

Ham kök `/Users/murat/develop/c5-a-demo-evidence-20261114`: ilk başarısız `live/`, başarılı `live-current-idl/`, `observed-summary.json`, `verification.json`, API doğrulama JSON’ları ve frontend logu. `ros.jsonl` fiziksel poz, odometri, RobotStatus, BatteryState, Nav2/ExecuteTask terminal sonuçları ve SQLite değişimlerini içerir. Tek görev zinciri ve layout eşleşmesi assertion ile doğrulandı; tam regresyon yapılmadı. Tarihsel testler yeni test gibi sayılmadı.

Demo container’ı `fleet-c5-a-demo-live-20261114` ve Vite açık bırakıldı. Taşıma sonrası otomatik park dönüşü normal FM akışıdır. Sürekli çalışma/uzun süre dayanıklılık, bütün katalog noktaları, iki eşzamanlı taşıma veya sensörlü ürün kabulü çıkarılamaz. Bu koşu çalışan ilk entegrasyon sunumunu destekler.

Son read-only kontrolde taşıma sonrası park dönüşü de bitti; iki robot IDLE/LIVE, iki batarya LIVE idi. Fiziksel poz örneklerinde en küçük merkez ayrımı 2.539 m, unsafe-contact olay sayısı 0. Bu örnekleme küresel çarpışmasız trafik kanıtı değildir. Son ölçüm `final-readonly-check.json` içinde korunur.
