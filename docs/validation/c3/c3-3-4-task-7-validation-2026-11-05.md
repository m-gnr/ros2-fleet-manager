# C3.3.4 Görev 7 — YAML enerji politikalarının doğrulanması

5 Kasım 2026. [Komut eki](c3-3-4-task-7-commands-2026-11-05.md)

## Başlangıç durumu

Yerel dal `main`, upstream `origin/main` ve doğrudan GitHub sorgusundaki `refs/heads/main` aynı `b336c27af50746ced9e7e38ad92ed75b7550dac1` commit'indeydi. `origin` fetch ve push hedefi `https://github.com/m-gnr/ros2-fleet-manager` idi.

| Görev | Başlangıç geçmişindeki commit |
|---|---|
| 1 — Terminal epoch | `fe2615b` |
| 2 — Oturum ve rezervasyon | `fe280d2` |
| 3 — Preemption sonrası yeniden uygunluk | `1eb60a7` |
| 4 — Fiziksel kanıtla istasyon kurtarma | `ed13291` |
| 5+6 — Robot bazlı canlı rota | `b336c27` |

Başlangıçta `docs/README.md` değiştirilmişti. `docs/gereksinim-literatur-ozgunluk-2026-10-27.pdf` ve `docs/reports/` izlenmiyordu. Bu içerikler korundu.

## Kök neden ve düzeltme

25 Ekim teknik raporunun 15. sayfasındaki bulgu başlangıç HEAD'inde yeniden üretildi. Builder robotun batarya modelini aktarıyor, ancak iki filo politikasını Scheduler'a vermiyordu. Scheduler da enerji fonksiyonunu %8 ve 10 Wh varsayılanlarıyla çağırıyordu. Ayrıca `ImportError` yakalandığında builder ham YAML okuyup eksik batarya alanlarına ve pozlara varsayılan değer atıyordu. Eski Nav2 test image'ında Pydantic yoktu ve `jsonschema` 3.2.0, C1 loader'ının kullandığı `Draft202012Validator` sınıfını içermiyordu. Düzeltilen builder eski image'da başlatıldığında eksik Pydantic hatası çağırana ulaştı.

- Builder yalnızca C1 `load_config()` sonucundan çalışır. Eksik veya geçersiz politika, eksik dosya ya da doğrulayıcı import hatası çağırana ulaşır. Açıkça verilen eksik dosyanın yerine başka bir filo dosyası aranmaz. C3.3.3 test harness'i kendi çözdüğü dosya yolunu builder'a geçirir.
- Builder, doğrulanmış `emergency_soc_percent` ve `safety_margin_wh` değerlerini `FleetManagerCore` üzerinden Scheduler'a verir. Temsili varsayılanlar doğrudan `FleetManagerCore` ve `Scheduler` kurulumunda ve doğrudan enerji fonksiyonu çağrılarında bulunur. C3.3.3 T03'ün bağımsız Wh denetimi bu çağrılardan biridir.
- Scheduler, normal atama ve HIGH preemption adaylığında aynı enerji değerlendirmesini çağırır. Terminal `PREEMPTED` sonucu HIGH görevi kuyruğa döndürür. Sonraki değerlendirme güncel SoC'yi kullanır. Otomatik rota tamamlandığında geçici Scheduler kopyası aynı politika değerleriyle zamanlar.
- Robotun kendi batarya modelindeki kapasite ile son kabul edilen SoC kalan enerjiyi belirler. Acil rezerv aynı kapasite üzerinden düşülür. Gerekli enerji, robotun Wh/m katsayısıyla pickup, teslimat ve şarja kaçış rotalarının toplamına marjın bir kez eklenmesiyle bulunur. Rezervin altındaki negatif net enerji korunur. Böylece sıfır mesafe ve sıfır marjla bile rezerv altındayken atama çıkmaz.
- Yetersiz enerji veya eksik/geçersiz rota adayın elenmesine yol açar. Görev aynı öncelik ve `created_at` ile kuyrukta kalır. Uygun atama görev, robot sahipliği ve bir mantıksal `EXECUTE_TASK` komutunu aynı SQLite transaction'ında yazar.
- C3.3.3 backend test image'ı, var olan Nav2 image'ından türetilip C1 bağımlılıklarıyla hazırlandı. C2.3 ve simülasyon servisi var olan Nav2 image'ını kullandı.

## Regresyonlar

| Seçki | Geçti | Kaldı | Atlandı |
|---|---:|---:|---:|
| Düzeltme öncesi builder seçkisi | 7 | 5 | 0 |
| Konfigürasyon, builder, Scheduler, enerji, Outbox ve rota odak seçkisi | 234 | 0 | 0 |
| Tam host Python ve Executor | 321 | 0 | 25 |
| C3.3.3 ayrı config modülü | 3 | 0 | 0 |
| ROS 2 Humble / CycloneDDS ilk koşu | 349 | 1 | 0 |
| Humble image'ında düzeltme sonrası odak COMMIT testi | 1 | 0 | 0 |
| ROS 2 Humble / CycloneDDS tam tekrar | 350 | 0 | 0 |
| C2.3 ayrı config modülü, Humble | 3 | 0 | 0 |

Yeni testler aynı rota ve SoC'de iki YAML alanını ayrı ayrı değiştirir. Üç 4 m rota ve 22 Wh marj için 25 Wh tam eşikte atama çıkar. Eşik altında görev kuyrukta kalır. Başarılı eşik koşusu marjın tek eklenmesini, başarısız koşular ise kaçış rotasının hesaba katılmasını sınar. İkinci batarya modeli testi otomatik rota çözümünde, daha yakın 100 Wh robotu eleyip daha uzak 200 Wh robotu seçer.

Preemption testi yetersiz SoC'de iptal üretmediğini, terminal sonuç sonrası güncel SoC'nin tekrar değerlendirildiğini ve eski SoC güncellemesinin reddedildiğini doğrular. HIGH görev sırası korunur. SQLite COMMIT reddedilince görev, robot, rezervasyon, işlenmiş olay ve Outbox kayıtları ile yayımlanan domain durumu korunur. Başarılı tekrarda yalnız bir yeni atama oluşur.

İlk Humble koşusunda yeni COMMIT testi, Python 3.10'da `set_authorizer(None)` sonrasında SQLite durumunu okurken `not authorized` hatası verdi. Test kancası, mevcut Outbox testlerindeki `SQLITE_OK` callback'i ile geri alındı. Hedefli Humble testi ve tam tekrar geçti. COMMIT hatası enjeksiyonu ve durum karşılaştırmaları aynı kaldı.

## Canlı kabul ve regresyon

### YAML-ENERGY-POLICY

**DOĞRULANDI.** Aynı Gazebo oturumunda iki robotun başlangıç koşulları, harita, görev ve %100 SoC sabit tutuldu. İki robot için gerçek `ComputePathToPose` sonuçları bir kez alındı ve iki doğrulanmış YAML varyantında aynı mesafeler kullanıldı. Filo dosyasının geçici kopyasında yalnızca marj değiştirildi. Acil rezerv %8, iki robot için kullanılabilir net enerji 92 Wh idi.

| Robot | Pickup / taşıma / şarja kaçış | 10 Wh marjla gereken | 91,99 Wh marjla gereken |
|---|---|---:|---:|
| `robot_1` | 0,500 / 0,500 / 2,122 m | 10,624 Wh | 92,614 Wh |
| `robot_2` | 3,906 / 0,500 / 2,122 m | 11,306 Wh | 93,296 Wh |

91,99 Wh ile SQLite görevi `QUEUED` ve Outbox boş kaldı. 10 Wh ile görev `ASSIGNED` oldu ve `robot_1` için bir `PENDING EXECUTE_TASK` kaydı oluştu. Kabul koşusu komut gönderiminden önce sonlandırıldı. Hareket ve görev tamamlama ayrı regresyonlarla sınanır.

### Diğer canlı regresyonlar

**C2.3 DOĞRULANDI.** Yedi senaryonun tamamı geçti. Güvenli duruşta doğrulanan lineer ve açısal hız sıfırdı. Koşuda Nav2 `Failed to make progress` olayı yoktu.

**T02-AUTO-ROUTES DOĞRULANDI.** T01 başlangıç kontrolü geçti. Boş önbellekten başlayan koşuda dokuz `ROUTE_APPLIED` kaydı oluştu. İki görev sırasıyla `robot_1` ve `robot_2` ile tamamlandı. Ayrı SQLite kopyasında her iki görev `COMPLETED`, epoch değerleri 1 ve iki `EXECUTE_TASK` kaydı `SENT` idi. `robot_1` dropoff sırasında dört ilerleme hatasından sonra 120 sn sınırı içinde tamamladı.

**C3.3.3 ilk T01–T10 koşusu BAŞARISIZ.** T01 geçti. T02'de her iki görev doğru robota atandı ve iki Outbox komutu `SENT` oldu. `robot_1` dropoff sürüşünde 120 sn sınırını aştı. SQLite kopyasında `task_t02_r1` durumu `ASSIGNED`, `task_t02_r2` durumu `COMPLETED` idi. T03–T10 bu koşuda başlamadı.

**C3.3.3 bağımsız tekrar DOĞRULANDI.** Temiz Compose projesinde aynı eşiklerle T01–T10 **10/10** geçti. T02'de `robot_2` dört ilerleme hatasından sonra süresi içinde tamamladı. İki görev SQLite'ta `COMPLETED`, iki Outbox komutu `SENT` ve iki atama epoch'u 1 idi. T04 güvenli duruş, eşleşen terminal `PREEMPTED` ve yeniden atama denetimlerini geçti. T04'te duruş sonrası rota kontrollü olarak sağlandı.

### Nav2 olayları ve Docker kapanışı

| Koşu | Nav2 `Failed to make progress` | Compose çıkışı | Backend / simulation çıkışı | Simulation durdurma |
|---|---|---:|---|---|
| C2.3 | 0 | 0 | 0 / 137 | SIGTERM → 3,030 sn → SIGKILL |
| YAML-ENERGY-POLICY | 0 | 0 | 0 / 137 | SIGTERM → 3,014 sn → SIGKILL |
| T02-AUTO-ROUTES | `robot_1` 4 | 0 | 0 / 137 | SIGTERM → 3,016 sn → SIGKILL |
| C3.3.3 ilk | `robot_1` 4, T02 zaman aşımı | 1 | 1 / 137 | SIGTERM → 3,023 sn → SIGKILL |
| C3.3.3 tekrar | `robot_2` 4 | 0 | 0 / 137 | SIGTERM → 3,022 sn → SIGKILL |

Docker her iki servis için `OOMKilled=false` bildirdi. Simulation container'ları backend test sonucu çıktıktan sonra durduruldu. YAML kabul koşusunda, SIGTERM sonrasında robot_2 lifecycle yöneticisi `bt_navigator` heartbeat kaybı kaydetti. Simulation servisinin normal kapanışı ayrı bir açık doğrulama olarak kaldı.

## Kalan kapsam

Şarja kaçış hedefi ilk yapılandırılmış şarj istasyonudur. Çoklu istasyon seçimi ayrı kapsamdadır. Canlı kabulde geçici C3.3.3 besleyicisinin sabit SoC değeri kullanılır. Zamana ve harekete bağlı tüketim, şarj gücü ve batarya telemetrisinin fiziksel üretimi C4 Battery Simulator kapsamındadır.

T02 dropoff ilerleme kararsızlığı ve simulation servisinin SIGKILL ile kapanması açık kalıyor. T01–T10 tekrarında kabul ölçütleri karşılandı. Süreç kapanışı ve tekrar edilebilirlik bulguları yukarıda ayrı kayıtlıdır.

## Yayın kaydı

Görev commit mesajı `fix(fleet-manager): wire YAML energy policies into scheduler`. Bu raporu ekleyen commit'in kimliği ve uzak HEAD eşleşmesi [Git doğrulama komutlarıyla](c3-3-4-task-7-commands-2026-11-05.md#diyagram-ve-git) okunabilir. Yayın hedefi `origin/main` ve yöntem normal fast-forward push'tur.
