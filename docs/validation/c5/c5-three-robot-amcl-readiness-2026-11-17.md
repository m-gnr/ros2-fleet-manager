# C5 — Üç robot AMCL readiness incelemesi — 17 Kasım 2026

## Karar

**PARTIAL.** Hareketsiz üç robotta `/amcl_pose` tekrarının olmaması, AMCL'in çalışmadığı veya TF'nin güncel olmadığı anlamına gelmiyor. Canlı parametreler ürün şablonuyla uyumlu; AMCL, Nav2 ve TF üç robot için başlangıçta hazır kaydedilmiş. Kısa salt-okunur kontrolde üç robot da `IDLE`, API `LIVE`, AMCL lifecycle aktif, Nav2 lifecycle/action server'ları hazır ve `map → odom → base_link` örnekleri günceldi. Görev veya hareket başlatılmadı.

`startup-readiness.json` içinde `status=READY`, `current_status=WAITING` ve her robotun `amcl`, `nav2`, `tf` ilk-ready kayıtları bulunuyor. Ancak dosya mevcut readiness düşüşünün hangi alt koşuldan geldiğini yazmıyor. Uygulama kodunda `current_status` şu birleşik koşuldan türetilir: tüm robotlarda AMCL lifecycle + geçerli son AMCL pozu, tüm Nav2 lifecycle düğümleri + `NavigateToPose` action server'ı ve güncel TF snapshot'ı aynı örneklemede hazır olmalıdır. Bu nedenle geçmişteki READY → WAITING geçişinin kesin alt koşulu eldeki canlı kayıttan geri çıkarılamadı; bu geçişin AMCL poz tekrarsızlığından kaynaklandığı iddiası desteklenmiyor. Geçiş anında koşul bazında telemetri tutulmadığından koşulsuz PASS verilmedi.

## Canlı gözlem

Oturum: `c5-20261117T065353Z-77741f4968`, ROS domain `206`, üç robotlu `warehouse-30x18` profili. Veri yalnızca okundu.

| Robot | AMCL | Nav2 | TF zinciri | Operasyon durumu |
|---|---|---|---|---|
| `robot_alpha` | Aktif; probe sırasında 1 transient `/amcl_pose` örneği | Lifecycle düğümleri aktif; `NavigateToPose` hazır | Güncel `odom → base_link`, map zinciri çözüldü; `LIVE` | `IDLE`, telemetry/pose/battery `LIVE`, görev yok |
| `robot_beta` | Aktif; probe sırasında 1 transient `/amcl_pose` örneği | Lifecycle düğümleri aktif; `NavigateToPose` hazır | Güncel `odom → base_link`, map zinciri çözüldü; `LIVE` | `IDLE`, telemetry/pose/battery `LIVE`, görev yok |
| `robot_gamma` | Aktif; probe sırasında 1 transient `/amcl_pose` örneği | Lifecycle düğümleri aktif; `NavigateToPose` hazır | Güncel `odom → base_link`, map zinciri çözüldü; `LIVE` | `IDLE`, telemetry/pose/battery `LIVE`, görev yok |

Yaklaşık 8 saniyelik gözlemde her robotun AMCL pozu yalnız bir kez geldi ve damgası `map` çerçevesinde `0.2 s` idi. Aynı pencerede robot başına 154–156 odom, 27 scan ve 181–182 TF mesajı; `/clock` üzerinde 1047 örnek alındı. Odom ve TF damgaları Gazebo saatiyle ilerlemeye devam etti. AMCL pozunun tekrarlanmaması, hareket eşiğini geçmeyen hareketsiz robotta beklenen yayın davranışıyla uyumludur; TF güncelliğini AMCL poz mesaj sayısıyla ölçmek doğru değildir.

## Etkin AMCL parametreleri

Üç `/robot_{alpha,beta,gamma}/amcl` düğümünden ROS parameter service ile okundu:

| Parametre | Alpha | Beta | Gamma |
|---|---:|---:|---:|
| `update_min_d` | 0.1 m | 0.1 m | 0.1 m |
| `update_min_a` | 0.1 rad | 0.1 rad | 0.1 rad |
| `transform_tolerance` | 1.0 s | 1.0 s | 1.0 s |
| `tf_broadcast` | true | true | true |
| `save_pose_rate` | 0.5 Hz | 0.5 Hz | 0.5 Hz |

`save_pose_rate`, AMCL pose topic yayın frekansı değildir. Hareket eşikleri ve TF toleransı için kanıtsız değişiklik yapılmadı.

## Observer koşulu ve düzeltme kararı

`stage1_observer.py` AMCL hazır koşulunda her döngüde yeni `/amcl_pose` mesajı istemiyor. En son örneğin `map` çerçevesinde, sıfır olmayan ve simülasyon saatinden en fazla 250 ms ileride olmasını ve AMCL lifecycle'ın `active` olmasını kontrol ediyor. Sonra TF tazeliğini ayrı `RobotReader` snapshot'ı ile kapıdan geçiriyor. Bu nedenle “hareketsizken yeni AMCL pozu gelmedi” durumunu doğrudan TF kaybı sayan bir AMCL kabul koşulu bulunmadı; AMCL güncelleme eşikleri/toleransı değiştirilmedi ve kabul davranışına düzeltme uygulanmadı.

Gözlenen kaydın kesin alt başarısız koşulu belirlenemedi: observer birleşik `current_status` saklıyor, AMCL/Nav2/TF için anlık ayrı boole değerleri veya başarısızlık nedeni saklamıyor. Bu geçmiş geçiş için bir alt koşul uydurmak güvenli olmaz. Kod değişikliği ve test yapılmadı. Bu rapor, hazır olma koşullarının mevcut canlı oturumdaki kısa yeniden gözlemini kanıtlar; kaydedilmemiş geçmiş geçişi kanıtlamaz.

## Kapsam sınırı

Üç robotun güncel hareketsiz readiness durumu kısa pencerede **3/3 hazır** olarak gözlendi. `/api/health` `source=LIVE`; `/api/robots` üç robotu `IDLE` ve pose/telemetry `LIVE` gösterdi; `/api/tasks` `total=0`. Hareket, görev, Nav2 goal, parametre değişimi, restart veya performans testi yapılmadı. Navigasyon hareketi bu koşuda sınanmadı.

Çalıştırılan salt-okunur komut ve probe özeti [komut ekindedir](c5-three-robot-amcl-readiness-commands-2026-11-17.md). Ham oturum kanıtı `/tmp/c5-20261117T065353Z-77741f4968/live/` altındadır; readiness dosyası koşul bazlı geçiş nedeni içermemektedir.
