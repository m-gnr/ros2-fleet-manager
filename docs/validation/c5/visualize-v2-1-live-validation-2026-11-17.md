# Visualize V2.1 — yeni park alanının canlı doğrulama denemesi

**17 Kasım 2026 · `feature/visualize` · commit/push yok.** Bu kayıt [V2 yerleşim değişikliğinin](visualize-park-relocation-2026-11-17.md) ardından yapılmış salt okunur canlı incelemedir. Ürün/config/launch kodu ve çalışan container değiştirilmedi; hareket hedefi gönderilmedi.

## Aktif kaynak ve engel

`c5-20261117T081139Z-0ead015f09` container'ının `/workspace` mount'u `/private/tmp/ros2-fleet-manager-c5-alpha-beta-stable` dizinidir. Çalıştırma komutu bu mount'taki `config/fleet.warehouse-30x18.yaml` dosyasını `stage1_run.py` için kullanıyor. Container içindeki aynı kodla hesaplanan profil özeti `58a5ca33e1995d1c765e93f25bf3e65c669fde8a0f2e56a798dc98071cddfb65`; `/api/warehouse-layout` aynı özeti verdi. Üç robot (`robot_alpha`, `robot_beta`, `robot_gamma`) bu YAML'de kayıtlı.

| İstasyon | `feature/visualize` hedefi (m) | Aktif API/rezervasyon pozu (m) | Sonuç |
|---|---|---|---|
| `park_1` | (13,5; 1,5) | (5,25; 5,25), `robot_beta` işgalinde | **FAIL** — yeni hedef aktif değil |
| `park_2` | (13,5; 2,75) | (5,25; 6,5), `robot_gamma` işgalinde | **FAIL** — yeni hedef aktif değil |
| `park_3` | (13,5; 4,0) | (5,25; 7,75), `robot_alpha` işgalinde | **FAIL** — yeni hedef aktif değil |

Feature dalının profili iki robotlu, bağlı canlı profil üç robotlu. İki dosyanın statik raf/duvar engelleri aynı; istasyon pozları ve robot kayıtları farklı. Bu nedenle çalışan üç robotlu Nav2 planlayıcısına yeni noktalar için **salt okunur** plan sorguları yapmak aynı fiziksel haritada rota uygunluğunu sınar, ancak yeni YAML'nin canlı olarak uygulanmasını veya park görevini doğrulamaz.

## Test matrisi

| Kontrol | Sonuç | Gözlem ve sınır |
|---|---|---|
| Aktif YAML'nin bulunması | **PASS** | Docker mount, çalıştırma komutu, container içi profil özeti ve API özeti eşleşti. |
| Yeni park hedeflerinin aktif runtime'da kullanılması | **FAIL** | Üç canlı istasyonun API ve rezervasyon pozları eski koordinatlar. |
| Üç yeni hedefe Nav2 planı | **PASS — yalnız plan** | Üç robotun mevcut pozundan karşılık gelen yeni noktaya `ComputePathToPose` sonucu `SUCCEEDED`: 415/361/338 poz; 10,401/9,068/8,486 m. Goal olarak `NavigateToPose` gönderilmedi. |
| Parktan şarja ve ana geçide Nav2 planı | **PASS — yalnız plan** | Her yeni noktadan `dock_6=(13,25;8,25)` ve `cross_e=(11,5;2,5)` için altı plan daha `SUCCEEDED`. Fiziksel geçiş yok. |
| Yeni hedef merkezlerinde statik açıklık | **PASS — geometri** | Her merkezden en yakın sabit engel doğu duvarı, 1,45 m. Nav2 local/global `robot_radius=0,30 m`, `inflation_radius=0,45 m` canlı parametreleri okundu. |
| Plan boyunca minimum statik açıklık | **PASS — sınırlı ölçüm** | Dokuz planın en küçüğü `park_1` girişinde `rack_B2`'ye 0,471 m; inflation sınırının yalnız 0,021 m üzerinde. `park_2` girişi 0,476 m, `park_3` girişi 0,704 m. Bu dinamik costmap veya gerçek takip güvenliği garantisi değildir. |
| Üç park hedefine fiziksel Nav2 varışı | **NOT TESTED** | Yeni pozlar aktif rezervasyonlarda yok; hareket başlatılmadı. |
| Raf/duvar/istasyonla fiziksel çakışmasız giriş ve çıkış | **NOT TESTED** | Planlar statik engelden ayrılıyor; hareket, duruş ve diğer robotlarla çakışma gözlenmedi. |
| Üç robotun eşzamanlı park çıkışı ve trafik güvenliği | **NOT TESTED** | Aktif ROS grafında trafik permit servisi/topic'i yok. Bu daldaki `TrafficMotionGate` test yolu nonzero ürün hareketine açık değil; mevcut güvenliği bypass ederek hareket gönderilmedi. |
| Canlı ürün snapshot/WebSocket | **PASS** | `fleet.scene.v1` WebSocket ürün sırası arttı; üç robot kaydı ve eski istasyon sahipliği taşındı. |
| Canlı sahne TF/WebSocket pozları | **FAIL** | Altı saniyede `robot_pose` paketi yok; üç robot için `data_status=STALE`. `/clock` ve `/tf` için beş saniyelik ROS gözleminde örnek gelmedi. Ürün snapshot'ındaki `LIVE`, sahne TF LIVE kanıtı değildir. |
| Üç yuva/isimler, etiket çakışması, V1 işaretleri, kamera | **PASS — mock Chrome** | Hedefli Playwright 5/5; üstten görüntüde yuvalar ve sahip adları ayrı okunuyor. Canlı yeni profilde görsel koşu **NOT TESTED**. |
| Robot modelinin yeni yuvalara fiziksel parkı | **NOT TESTED** | Görsel Burger zarfı 0,138 × 0,178 m ve yuva 1,50 × 1,00 m; statik çizim sığar. Gerçek robotun park/yaw sonucu gözlenmedi. |
| Boş yuva park ID'si | **NOT TESTED — render** | Kod `owner ?? id` kullanıyor; boş canlı yeni yuva görüntüsü test edilmedi. |
| Eski alanın nötr bekleme görünümü | **PASS — mock / FAIL — aktif runtime** | Feature sahnesinde dekoratif boyama var; aktif runtime eski bölgeyi hâlâ işgal edilmiş park kaynağı olarak tutuyor. |
| Park seçimi, rezervasyon ve sahiplik host regresyonu | **PASS — host** | Tanımlı C5 image'ında seçili dört test dosyası 63/63 geçti; canlı yeni pozlarda görev seçimi **NOT TESTED**. |
| Önceki `fastapi` eksikliğiyle kalan host testi | **PASS** | `tests/test_warehouse_grid.py` aynı image'da 3/3 geçti. Global Python değiştirilmedi. |

Canlı oturumdaki `/tf` yayıncısı ROS grafında listeleniyor fakat ölçüm aralığında mesaj üretmedi. Gazebo süreci görünürken `/clock` da örnek vermedi. Simülasyon logunun sonunda `malloc(): unsorted double linked list corrupted` satırı var; bunun duraksamanın tek nedeni olduğu doğrulanmadı. Plan action'larının yanıt vermesi simülasyon saatinin ve TF'nin sağlıklı olduğu anlamına gelmez.

## Çıkış değerlendirmesi

Yeni konumun **statik planlanabilirliği PASS**, canlı park kabulü **NOT TESTED**, aktif YAML tutarlılığı **FAIL**. Bir sonraki canlı kabul koşusu, mevcut üç robotlu profilin robot kayıtlarını koruyarak V2 park hedefleriyle aynı kaynakta birleştirilmesini ve kontrollü, taze senaryo başlangıcını gerektirir. Ardından kalifiye trafik/actuator güvenlik zinciriyle fiziksel park, çıkış, şarj ve eşzamanlı hareket ölçülmelidir. Bu kayıt böyle bir profil veya güvenlik değişikliği yapmaz.

[Komut eki](visualize-v2-1-live-commands-2026-11-17.md) · [Mock üstten görüntü](visualize-park-relocation-screenshots/top.png).
