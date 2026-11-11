# C5 — 30 × 18 m uçtan uca doğrulama, Aşama 1

11 Kasım 2026 · [Komut eki](e2e-stage1-commands-2026-11-11.md) · [Ham kanıtlar](e2e-stage1-2026-11-11/)

**AŞAMA 1 TESTLERİ TAMAMLANDI; KOŞULSUZ KABUL VERİLMEDİ.** Tek görev ve iki robotlu paralel görev gerçek `COMPLETED` oldu. Bununla birlikte feedback sözleşmesi hatası ve bir fiziksel yaklaşma sapması bulundu. **Final kabul değildir. Aşama 2, Aşama 3 ve 27 noktalı fiziksel tarama başlatılmadı.**

## Kaynak, kapsam ve ortam

Ana worktree `main`, `32e23fc`; istenen 30 × 18 m profil burada yoktu. Güncel profil ve görev API'si, `feat/c5-warehouse-grid-layout` dalındaki `/Users/murat/develop/ros2-fleet-manager-c5-warehouse-grid` worktree'sinde, commit edilmemiş kullanıcı değişiklikleri içindeydi. Bu worktree korundu. Yeni branch, commit, push, merge, reset, clean veya rebase yapılmadı. Ürün kodu, filo/şema, IDL, TF ve Nav2 parametreleri değiştirilmedi. Eklenen kod yalnız doğrulama araçlarıdır; iki dokümantasyon dizinine bu raporun bağlantısı eklendi.

| Kimlik | Değer |
|---|---|
| Kullanılan commit, iki son koşuda aynı | `30373ff6ec6661130e0b2e78b382fdc768eda58c` |
| Kaynak profil | `config/fleet.warehouse-30x18.yaml` |
| Profil dosyası SHA-256 | `207e4f6d36e6dd03f5a68f854a81a061d80e16a161da3c312955b4a159161c36` |
| Çözülmüş profil özeti | `8e8396b60c306e795ea84275ac56aa41a47fc8cf090fe14ad9627988bc91fda2` |
| Şema SHA-256 | `92f8024ffcd7f9fc3e5d8871d0123240ceadf479a9f4830f180091c34beb7cb0` |
| Nav2 şablonu SHA-256 | `7f2a273cbdff28e9e3399ec7bd1ad693ca5dd725906dfab8309b5265de67fd98` |
| Image | `ros2-fleet-c5-validation:humble-fortress` |
| Image SHA-256 | `7fb7e7fc4aebe0d2b4097752e9b470e30d8ea7a8126bb1dee87d03f30330609d` |
| Container | ARM64 Ubuntu 22.04.5, Python 3.10.12, ROS 2 Humble, CycloneDDS, Fortress/DART |
| Nav2 / DART | `1.1.20-1jammy.20260916.171610` / `6.12.1+dfsg4-11build2` |
| Docker Desktop kaynakları | 8 CPU, 8.32 GB bellek; macOS ARM64 host |
| Son senaryolar | `scenario-a4`, domain 163; `scenario-b`, domain 164 |
| Tarayıcı | Gerçek Google Chrome, Playwright `channel: chrome`, headless; 1440 × 1000 |
| Test portları | UI 20081, API 20082, özel TF/Path köprüsü 20083; ürün sabiti değildir |

Commit SHA tek başına çalışma ağacını tanımlamaz. [Başlangıç Git/worktree/diff kaydı](e2e-stage1-2026-11-11/baseline.json), [başlangıç patch'i](e2e-stage1-2026-11-11/baseline.diff), [dosya manifesti](e2e-stage1-2026-11-11/source-manifest.json) ve [ortam kaydı](e2e-stage1-2026-11-11/environment.txt) birlikte değerlendirilmelidir.

[Proje bağlamı](../../project-context.md), [C4.5 kabul listesi](../c4/c4-acceptance-2026-11-06.md), [C4.5 raporu](../c4/c4-5-validation-2026-11-06.md), [Outbox sözleşmesi](../../design/c3-2-sqlite-outbox.md), C3.3.1–C3.3.3 kararları ve [önceki 30 × 18 m raporu](warehouse-30x18-validation-2026-11-11.md) incelendi. Tarihsel C4 kabulü bu tarihte yeniden çalıştırılmış kabul sayılmadı.

Her son senaryo ayrı Gazebo dünyası ve ayrı SQLite ile başladı. Bağımsız gözlemci, Executor kabulü açılmadan önce iki robotun başlangıç poz/yaw hatasının ≤0,05 m/rad, güncel odometri hızlarının ≤0,01 m/s ve rad/s olduğunu bir saniye boyunca kontrol etti; Nav2 lifecycle `active` idi. Mevcut kontrollü reset test giriş noktası ancak bu kanıttan sonra kullanıldı. [A reset](e2e-stage1-2026-11-11/scenario-a4/reset-verified.json) · [B reset](e2e-stage1-2026-11-11/scenario-b/reset-verified.json)

Gerçek ürün runtime'ı, Executor ve robot başına tek C4 Battery Simulator çalıştı. Başlangıç SoC'si ürün varsayılanı %100; tüketim 0,2 Wh/m, bekleme 2 W ve şarj 20 W olarak profilden alındı. Düşük SoC %25, acil rezerv %8, hedef %80 ve marj 10 Wh değişmedi. Rota sorguları canlı Nav2'den; Euclidean fallback veya kontrollü mesafe enjeksiyonu yoktu. Tarayıcı HTTP/WS mock'u veya kayıt oynatma kullanılmadı. Bu tek-container test yerleşimi nihai üç servisli dağıtım kabulü değildir.

## Görevler ve zaman çizelgeleri

Tablodaki zamanlar **Türkiye saati, UTC+3**; ham kayıtlarda UTC, monotonik zaman ve `/clock` nanosecond değerleri birlikte saklanır.

| Etiket | Rota | Robot | Epoch | ExecuteTask goal UUID |
|---|---|---|---|---|
| A1 | `pick_A1 → packing_1` | `robot_alpha` | 1 | `a6de5ecb-53c8-4e33-9266-23f1dd2a6b7e` |
| B1 | `pick_A1 → packing_1` | `robot_alpha` | 1 | `ea866399-da3a-4a6b-a673-faf047ea914c` |
| B2 | `pick_A2 → quality_1` | `robot_beta` | 1 | `7c504524-fa70-4258-9b5d-100eb8be86dd` |

- A1 task: `web-9b9c96bf-0556-4e61-b4c6-eede1d131484`.
- B1 task: `web-14ff1644-1119-46dd-a09e-df3fa02e504f`.
- B2 task: `web-ccb5b174-5c31-422b-bb8c-021fddfae197`.

| Gözlem / kaynak | A1 | B1 | B2 |
|---|---|---|---|
| Chrome HTTP `201` | 18:11:14.066 | 18:14:14.218 | 18:14:14.299 |
| Chrome `QUEUED` | 18:11:14.237 | 18:14:14.500 | 18:14:14.500 |
| Chrome `ASSIGNED` | 18:11:14.643 | 18:14:15.245 | 18:14:15.245 |
| RobotStatus `MOVING_TO_PICKUP`, yüksüz | 18:11:14.513 | 18:14:15.111 | 18:14:15.323 |
| Pickup Nav2 terminal `SUCCEEDED` | 18:11:29.728 | 18:14:32.742 | 18:14:40.955 |
| RobotStatus `LOADING`, yüksüz | 18:11:29.929 | 18:14:32.953 | 18:14:41.123 |
| RobotStatus `MOVING_TO_DROPOFF`, yüklü | 18:11:31.907 | 18:14:34.908 | 18:14:43.123 |
| Dropoff Nav2 terminal `SUCCEEDED` | 18:12:49.729 | 18:15:57.537 | 18:15:22.067 |
| RobotStatus `UNLOADING`, yüklü | 18:12:49.914 | 18:15:57.708 | 18:15:22.113 |
| Chrome `COMPLETED` | 18:12:51.874 | 18:15:59.696 | 18:15:24.363 |

RobotStatus örnekleme anı HTTP/Chrome görünme anıyla aynı değildir. Görevlerin gerçek ExecuteTask sonucu `STATUS_SUCCEEDED`, ROS action sonucu `SUCCEEDED`, gerçek `completed_epoch=1` olarak bağımsız get-result servisiyle okundu. Sonraki RobotStatus'ta aynı epoch, boş task ID, `PHASE_NONE` ve `is_loaded=False` görüldü. Nav2 alt goal UUID'leri ve sonuçları karşılaştırma dosyalarında ayrı tutulur. Aynı sayısal epoch'un iki robotta bulunması normaldir; sahiplik robot/task/epoch/UUID birleşimiyle doğrulanmıştır.

**Önemli:** Gerçek FM görev durum dizisi `QUEUED → ASSIGNED → COMPLETED` oldu. `EXECUTING` gözlenmedi; eksik durum aşağıda başarısız kontrol olarak açıklanır. Executor fazları FM'de ikinci fiziksel durum makinesi kurularak tamamlanmadı.

B'nin iki HTTP kabulü arasında **81 ms** vardı. RobotStatus yürütme pencereleri **68,800 saniye** örtüştü. Scheduler görevleri aynı robota vermedi; robot seçimi zorlanmadı. Üç son görev için üç ayrı task, üç ayrı ExecuteTask Outbox komutu ve üç farklı goal UUID vardır. Her komut bir gönderim denemesinde `SENT` oldu. İki son veritabanında `integrity_check=ok`, foreign key ihlali ve review hold yoktu. Her exact request replay `200 / DUPLICATE` döndürdü; yeni görev üretmedi.

[A kaynak karşılaştırması](e2e-stage1-2026-11-11/scenario-a4/comparison.json) · [A SQLite export](e2e-stage1-2026-11-11/scenario-a4/sqlite-export.json) · [A Chrome](e2e-stage1-2026-11-11/chrome-a4/chrome-evidence.json) · [B karşılaştırması](e2e-stage1-2026-11-11/scenario-b/comparison.json) · [B SQLite export](e2e-stage1-2026-11-11/scenario-b/sqlite-export.json) · [B Chrome](e2e-stage1-2026-11-11/chrome-b/chrome-evidence.json)

## Fiziksel hedef ve batarya ölçümleri

| Görev | Pickup merkez / yaw hatası | Dropoff merkez / yaw hatası | Görev penceresi Wh başlangıç → bitiş | Tüketim |
|---|---|---|---|---|
| A1 | 0,176 m / 0,173 rad | 0,304 m / 0,162 rad | 99,990 → 95,733 Wh | 4,257 Wh |
| B1 | 0,126 m / 0,180 rad | 0,252 m / 0,150 rad | 99,999 → 95,711 Wh | 4,288 Wh |
| B2 | **0,378 m** / 0,194 rad | 0,173 m / 0,141 rad | 99,999 → 97,644 Wh | 2,355 Wh |

Wh uçları en yakın gerçek BatteryState örnekleridir; bütün koşu tüketimiyle karıştırılmaz. Görev sonrası otomatik park hareketinin ayrıca tüketimi vardır. Fiziksel hedef ölçümleri en yakın Gazebo model pozundan hesaplandı. Her iki robotun gövde, tekerlek ve destek contact topic'leri izlendi; raf/duvar/diğer robot için zararlı temas kaydı yoktu. Bu, sürekli geometrik çarpışma garantisi değildir.

Chrome bataryası, ölçüm damgası aynı olan bağımsız BatteryState ile A'da robot başına 392, B'de alpha için 414 ve beta için 413 snapshot'ta eşleşti; Wh uyuşmazlığı sıfırdı. RobotStatus ile Chrome TF'sinin aynı damgalı örnekleri robot başına yüzlerce eşleşme verdi; en büyük fark <`1e-12` m. Chrome'un gerçek render olayları da gelen TF'ye karşı denetlendi: A 582, B 1435 eşleşme, sıfır koordinat farkı (`scene.z = -map.y`). Her robotun tek yayın oturumu ve artan `status_seq` dizisi korundu. İşlenen RobotStatus'lar, canlı ürün snapshot'ları, Gazebo pozları ve odometri [ROS JSONL kayıtlarında](e2e-stage1-2026-11-11/scenario-b/ros.jsonl), Chrome'a gelenler [ayrı WS kaydında](e2e-stage1-2026-11-11/chrome-b/chrome-ws.jsonl) bulunur.

## Başarısız kontroller ve kök nedenler

**F1 — Feedback → FM `EXECUTING` geçişi başarısız.** [Action adaptörü](../../../backend/fleet_manager/adapters/action_client.py) `distance_to_goal` ve `battery_soc` alanlarını feedback olayına ekler. [Consumer](../../../backend/fleet_manager/event_loop.py) bu payload'ı `status_seq` çıkarıldıktan sonra doğrudan `handle_action_feedback(**p)` metoduna geçirir. [Domain metodu](../../../backend/fleet_manager/domain/fleet_manager_core.py) bu iki parametreyi kabul etmez. Gerçek adaptör callback'i ve gerçek consumer ile ayrı geçici DB'de yapılan [sözleşme denemesi](e2e-stage1-2026-11-11/feedback-contract.json), `unexpected keyword argument 'distance_to_goal'` TypeError'ını üretti; durum `ASSIGNED` kaldı, işlenmiş feedback sayısı 0 oldu. Deneme çıkış kodu **1**; başarılı test diye sayılmaz. Canlı iki son DB'de de feedback stream kaydı 0'dır. Canlı callback başına istisna sayısı ayrıca kaydedilmedi. Coroutine sonucunu izlemeyen adaptör yolu hatayı manager logunda görünür kılmıyor.

**F2 — B2 pickup fiziksel merkez hatası 0,35 m kontrolünü aşar.** 0,378 m hata, önceki 30 × 18 m fiziksel doğrulamasının 0,35 m ek sınırından 0,028 m büyüktür. Bu sınır ürün pickup sözleşmesinde uygulanmış bir kapı değildir; doğrulama ölçütüdür. Nav2 terminali ve gerçek ürün yükleme geçişi başarılıdır; fiziksel hassasiyet kontrolü başarılı değildir. Terminal yakınında RobotStatus map pozu `(2,3578; 5,8285)`, Gazebo pozu `(2,6224; 5,8159)` idi. Hedef `(2,25; 5,75)` için map hedef hatası 0,133 m, map–fiziksel poz farkı 0,265 m ölçüldü. Fiziksel hata yükleme boyunca aynı kaldı; tek örnek zamanlama sapması açıklaması desteklenmiyor. Mevcut `xy_goal_tolerance=0,25 m` ve `yaw_goal_tolerance=0,25 rad` map çözümünde başarılı terminali açıklar. Lokalizasyon farkının alt nedeni bu koşuyla kesinleşmedi; raf tekrarları/AMCL belirsizliği araştırma hipotezidir, onaylı kök neden değildir. TF'ye düzeltme ofseti eklenmedi.

**Düzeltme önerileri — ÖNERİ, uygulanmadı:** F1 için consumer→domain çağrısında kimlik/faz alanlarını açık eşlemek ve gerçek adapter payload'ını consumer'a veren regresyon eklemek; callback future hatalarını görünür kaydetmek. Bu çalışma sahiplik veya güvenlik algoritmasını değiştirmeden ayrı, dar bir düzeltme olarak ele alınabilir. F2 için aynı hedefte AMCL kovaryansı, scan/map hizası ve fiziksel hata bütçesini ayrı tekrarlarla ölçmek gerekir. Parametre düşürmek, TF'yi kaydırmak veya fiziksel toleransı büyüterek testi geçirmek önerilmez. Yeni trafik algoritması tasarlanmadı veya uygulanmadı.

## Ortam denemeleri ve kapanış

- `scenario-a`: test başlatıcısı Battery Simulator modülünü executable giriş noktası gibi çağırdı; modül 0 ile çıktı. Görev gönderilmedi. Başlatıcı gerçek `main()` girişine düzeltildi.
- İlk Chrome denemesinde video encoder eksikti; Playwright FFmpeg kuruldu. Ürün bağımlılığı veya lockfile değiştirilmedi.
- `scenario-a2`: gözlemci SQLite şeması oluşturulmadan okumayı denedi; `no such table: tasks`. Şema readiness kontrolü eklendi. Görev gönderilmedi.
- `scenario-a3`: bind mount üzerindeki salt okunur SQLite okuyucusu `attempt to write a readonly database` verdi. Bu kez tek görev atanmış ve pickup'a gidiyordu; observer kaybında koşu durduruldu. Eski görev başarı/FAILED olarak yeniden etiketlenmedi; eski DB tekrar kullanılmadı. Bu koşu kabul kanıtı değildir.
- Son A4 ve B'de ürün SQLite'ı kalıcı `fleet-c5-stage1-20261111` Docker volume'ünde tutuldu. Gözlemci aynı volume dosyasını salt okunur, kısa transaction'larla okudu. Kapanıştan sonra SQLite backup API ile rapor dizinine tutarlı kopya alındı.
- Son A4/B'de API, FM, scene, iki Executor, iki Battery Simulator, gözlemci ve simulation supervisor 0 koduyla kapandı. Nav2 lifecycle kapandı, `SIMULATION_SHUTDOWN clean=true`; iki container'da `OOMKilled=false`. [A kapanış](e2e-stage1-2026-11-11/scenario-a4/shutdown.json) · [B kapanış](e2e-stage1-2026-11-11/scenario-b/shutdown.json). Görev sonrası park dönüşleri tamamlanmış park kabulü sayılmadı; senaryo kontrollü kapatıldı.

Host seçkisi **87 geçti**, Chrome regresyonu **23 geçti**. Feedback sözleşme denemesi **başarısız**. Host seçkisinde bir Starlette/httpx deprecation uyarısı, mock tabanlı Chrome regresyonunda `/api/task-catalog` proxy bağlantı mesajları vardı; testler geçse de bu çıktılar saklandı. Bunlar canlı API'nin çalışmadığı iddiasıyla veya feedback hatasının giderildiği iddiasıyla karıştırılmaz. Tarihsel bütün C4.5/HIGH/preemption/şarj regresyonları bu aşamada yeniden çalıştırılmadı.

## 1,05 m geçiş ve sonraki aşamaların riskleri

27 noktalı katalog yeniden okundu: **18 transfer + 6 dock + 3 park**. [Statik envanter](e2e-stage1-2026-11-11/clearance-precheck.json) koordinat/yaw değerlerini içerir. Bu aşama yalnız dört benzersiz transfer noktasında ürün işlemi yürüttü; tüm noktalara ziyaret matrisi değildir.

Yalnız sonraki aşama için statik ön denetim yapıldı. [ROBOTIS resmi kaynağı](https://emanual.robotis.com/docs/en/platform/turtlebot3/features/) nominal Burger genişliğini 0,178 m verir. Frontend aynı nominal modeli çizer; çalışan Fortress doğrulama robotu ise farklı geometridedir: gövde 0,50 × 0,30 m, tekerlek dıştan dışa **0,44 m**. Arka ve ön destekler bu uzunluk/genişlik sınırının içindedir. SDF'den türetilen [YAML ölçüm kaydı](e2e-stage1-2026-11-11/physical-measurements.yaml), ayrı düzenlenebilir ürün config'i değildir; validator bu türetilmiş YAML'yi okuyarak hesabı tekrarlar.

`C = 2,25 − 0,75 − 0,45 = 1,05 m`. Düz fiziksel geçişte geometrik tolerans `1,05 − 0,44 = 0,61 m`; mevcut yaklaşma yarıçapının 0,90 m çapı kullanıldığında `1,05 − 0,90 = 0,15 m`. Bütün gövdeyi kapsayan ihtiyatlı dikdörtgenin dönüş çapı üst sınırı `sqrt(0,50² + 0,44²) = 0,666 m`. Bunlar lokalizasyon, dinamik salınım veya iki robotlu geçiş için onaylı güvenlik payı değildir. Gerçek nominal model, simülasyon collision modeli ve görsel model eşdeğer sayılmaz.

Yerel/global costmap `robot_radius=0,25 m`, inflation yarıçapı 0,45 m. Gövde köşe yarıçapı `sqrt(0,25² + 0,15²) = 0,292 m`; dolayısıyla belirtilen daire fiziksel gövde köşelerini bütünüyle kapsamaz. Inflation maliyet alanıdır; fiziksel collision zarfını veya güvenlik payını değiştirmez. Parametreler değiştirilmedi. Bu fark, ölçülen 0,265 m lokalizasyon farkıyla birlikte dar koridor öncesi değerlendirilmelidir. **Statik genişlik hesabı geçti diye trafik kabulü verilmedi.**

Aşama 2 için düşük enerji yönlendirmesi, dock lease/temas, %80 çıkış, altı dock ve en az üç fiziksel şarj ziyareti henüz bu profilde doğrulanmadı. Hedef hassasiyeti dock temas kanıtını etkileyebilir; Nav2 başarısı tek başına fiziksel dock kanıtı sayılmayacaktır. Aşama 3 için karşı yönlü aynı dar koridor, minimum açıklık, recovery/deadlock ve güvenli durdurma ölçümleri henüz yapılmadı. 27 istasyonun tam Nav2 ziyaret/operasyon matrisi ayrıca onay bekler.

## Aşama sonu

**Başarılı:** üç gerçek taşıma terminali, iki ayrı robota eşzamanlı atama, doğru task/epoch/UUID ve gerçek completed_epoch, yükleme/boşaltma, idempotency, kalıcı tekil Outbox, SQLite bütünlüğü, bağımsız batarya/TF/Chrome render eşleşmesi ve son iki temiz kapanış.

**Başarısız:** F1 feedback/`EXECUTING` akışı; F2 beta `pick_A2` fiziksel 0,35 m kontrolü. İlk ortam denemeleri ayrıca başarısızdır ve korunmuştur.

**Doğrulanmayan:** F2'nin kesin lokalizasyon alt nedeni, bütün hedeflerde tekrarlanabilir fiziksel hassasiyet, bu profilde otomatik şarj/dock çıkışı, 27 noktanın tam ziyaret matrisi, dar koridor trafiği ve nihai üç servisli dağıtım.

**Duruldu. Sonraki aşama kullanıcı onayı olmadan başlatılmayacak.** Mevcut iki bulgu nedeniyle bu kayıt koşulsuz Aşama 1 veya final kabulü vermez.

![İki görevin tamamlandığı Chrome tablosu](e2e-stage1-2026-11-11/chrome-b/completed.png)

[Canlı depo ve iki robot](e2e-stage1-2026-11-11/chrome-b/completed-overview.png) · [A Chrome hareket kaydı](e2e-stage1-2026-11-11/chrome-a4/video/) · [B Chrome hareket kaydı](e2e-stage1-2026-11-11/chrome-b/video/)
