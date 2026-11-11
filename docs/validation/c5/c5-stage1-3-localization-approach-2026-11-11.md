# C5 Aşama 1.3 — AMCL lokalizasyonu ve güvenli raf yaklaşması

11 Kasım 2026. **HEDEFLENEN FİZİKSEL PICKUP VE TEK/PARALEL GÖREV KABULÜ GEÇTİ.** Ürün ayarıyla pickup 5/5, tek görev ve iki paralel görev gerçek COMPLETED. Tuning sırasında üç bridge kapanış çökmesi ayrı açık bulgudur; koşulsuz bütün sistem kabulü verilmez. Bu kayıt C5 final kabulü değildir. [Komut eki](c5-stage1-3-commands-2026-11-11.md) · [Kanıtlar](stage1-3-2026-11-11/) · [Önceki Aşama 1.2](c5-stage1-2-physical-localization-2026-11-11.md)

## 1. Git/worktree başlangıcı

Başlangıç `feat/c5-warehouse-grid-layout / 19b6c4d`; mevcut `/Users/murat/develop/ros2-fleet-manager-c5-warehouse-grid` kullanıldı. Aşama 1.2 rapor commit’i `2cafb2b`, koruma denetimi `19b6c4d`; `072131a`, `36e0b50`, `5ca037b`, `971e586` doğrulandı. Ana çalışma ağacı `main / 32e23fc` salt okunur incelendi. Kullanıcıya ait 30×18 m, API, frontend, şema ve diğer değişiklikler korunur. HEAD tek başına test kaynağı değildir: [başlangıç manifesti](stage1-3-2026-11-11/baseline-hashes.json), [dirty diff](stage1-3-2026-11-11/baseline.diff), [kaynak manifesti](stage1-3-2026-11-11/source-manifest.json) ve [kaynak arşivi](stage1-3-2026-11-11/source-snapshot.tar.gz) birlikte okunur. Başlangıç manifesti 1826, deney kaynak arşivi 296 dosya içerir. İlk arşiv daha sonra eklenen araçların yerine geçmez; son [kaynak manifesti](stage1-3-2026-11-11/source-final-manifest.json) ve [kaynak arşivi](stage1-3-2026-11-11/source-final.tar.gz) nihai kaynakları tamamlar. Araç commit’i `1e80725`, model düzeltmesi `7293256`, canlı regresyon sürücüsü `d5caf34`; rapor/kanıt commit’i son yanıtta verilir. Başlangıçtaki kullanıcı kaynakları bu commit’lere katılmadı. Push/merge/rebase/stash/reset/clean yapılmadı.

## 2. İncelenen kaynaklar

Proje bağlamı, dokümantasyon haritası, AGENTS, Compose kılavuzu; Aşama 1 / 1.1 / 1.2 raporları ve komut ekleri; C3.3.1–C3.3.3, SQLite Outbox sözleşmesi ve C4.5 kabul kaydı incelendi. Aşama 1.1 `localization-analysis.json`, Aşama 1.2 `pickup-results.json`, `correction-gate.md`, beş footprint koşusunun `localization.json[l]`, `simulation.log`, `probe.log`, `raycast-alignment.json` ve üretilmiş parametre/harita/SDF incelendi. Beş eski probe.log boştur; ROS düğüm çıktıları simulation.log’dadır. Tarihsel 1/5 kabul değiştirilmedi.

## 3. Değişiklik öncesi hipotez matrisi

[İlk matris](stage1-3-2026-11-11/hypothesis-matrix.md) deney kodu ve parametre varyantlarından önce yazıldı. Kanıt, aleyhte kanıt, eksik ölçüm, ayrıştırıcı deney ve beklenen sonuç her hipotezde ayrı tutulur. Raf benzerliği başlangıçta hipotezdir; kesin neden değildir.

| Son sınıflandırma | Kanıt ve sınır |
|---|---|
| **KANITLANDI** — map/AMCL ile gerçek fiziksel poz ayrışıyor | Aynı damgalı TF zinciri ve bağımsız Gazebo pozu; gerçek ray hizası ayrı doğrulanır |
| **GÜÇLÜ BİÇİMDE DESTEKLENDİ** — yanlış map pozu statik costmap üzerinde sahte daralma üretiyor | A/pickup-2 aynı grid damgasında tahmini merkez 99, gerçek merkezin aynı frame’de izdüşümü 73; BaseObstacle ve abort |
| **KONTROLLÜ DENEYLE DESTEKLENDİ** — gözlem modeli bu koşullarda önemli etken | Yalnız model alanı değişince aynı heading 1/3→3/3, diğer iki heading ayrı ayrı 1/3→3/3; ürün ayarıyla yeni 5/5 |
| **KESİNLEŞMEDİ** — tekrarlayan raflar tek/başlıca neden | Gerçek lidar ayrımı sağlayan B varyantında fiziksel kabul yine 1/3; üç tekrar istatistiksel eleme değildir |
| **BU HEDEF İÇİN DESTEKLENMEDİ** — güvenli hedef geometrik olarak erişilemez | Statik 0,44 m artık açıklık; aynı gerçek hedefte 14 seçilmiş-model fiziksel başarı |
| **AÇIK** — model alt mekanizmalarının ayrı payı ve kapanış çökmesi | Beam alanı menzil hesabı yanında mevcut z_short/z_max katkılarını da etkinleştirir; bunların payı ayrı ölçülmedi. Bridge -11 için kök neden kanıtı yok |


## 4. Tekrarlayan raf deneyleri

A ürün profili ve controller değişmeden en az üç temiz dünya; B yalnız izole üretici sürecinde rack_A2’nin kuzeydoğu kısmında 1,0×0,5 m kör girinti; C aynı XY/hedefle başlangıç heading 0 ve π. B’de rack_A2’nin güney servis yüzü, alt 0,5 m kesintisiz şerit, orijinal dış zarf ve bütün koridor açıklıkları korunur. Rafın içinden geçiş yoktur. `WarehouseLayout.obstacles` aynı test sürecinde hem raster haritayı hem SDF collision/visual üretimini besler; yalnız texture değildir. Başlangıçta değişen ışınların 28 gözleminde girintiyle medyan ray hatası 0,00263 m, eski hacimle 0,75217 m; lidar farkı gerçek kayıtta doğrulandı ([kanıt](stage1-3-2026-11-11/landmark-lidar-visibility.json)). Ürün YAML ve raf sözleşmesi değişmez. Geometri listesi her koşunun generated/solids.json dosyasındadır. Deney varyantı ürün profili olarak sunulmaz.

| Aynı hedefte koşul | Eski likelihood_field fiziksel kabul | Beam fiziksel kabul |
|---|---:|---:|
| A — mevcut depo, heading=π/2 | 1/3 (bir abort) | 3/3 |
| B — izole kör girinti, heading=π/2 | 1/3 (üç Nav2 başarı) | Ayrı beam+B kombinasyonu denenmedi |
| C — heading=0 | 1/3 | 3/3 |
| C — heading=π | 1/3 | 3/3 |

B hataları 0,382 / 0,324 / 0,505 m; eski C/0 0,288 / 0,369 / 0,426 m; eski C/π 0,377 / 0,319 / 0,368 m. Beam C/0 0,216 / 0,246 / 0,216 m, C/π 0,244 / 0,179 / 0,235 m. B’nin görsel texture değişikliği olmadığı kanıtlandı; yine de bu sonuç raf simetrisini kesin kök neden ilan etmeye yetmez.

## 5. AMCL parametre duyarlılığı

Başlangıç etkin parametreler [canlı dump](stage1-3-2026-11-11/a-baseline/runtime-amcl.yaml) ile doğrulandı. Her koşunun generated/nav2-robot_beta.yaml dosyası ayrıca saklanır. Her varyant tek alan değiştirir ve üç bağımsız dünyada çalışır. Aynı fiziksel robot, track, hedef, radius ve controller kullanılır. Yalnız covariance azalması kabul değildir.

| Parametre | Başlangıç değeri | Kaynakta etkisi |
|---|---|---|
| alpha1 / alpha2 | 0,2 / 0,2 | Dönüş örneklemesinde dönme / öteleme katkılı varyans |
| alpha3 / alpha4 | 0,2 / 0,2 | Öteleme örneklemesinde öteleme / dönme katkılı varyans |
| alpha5 | 0,2 | DifferentialMotionModel içinde saklanır, bu modelin odometryUpdate hesabında kullanılmaz |
| min/max_particles | 200 / 1000 | Adaptif parçacık örneklemesinin alt/üst sınırı |
| update_min_d / update_min_a | 0,1 m / 0,1 rad | Hareket güncelleme eşikleri; tek başına periyodik durağan yeniden lokalizasyon değildir |
| laser_model_type | likelihood_field | Işın uçlarının en yakın dolu hücreye uzaklığı üzerinden ağırlık |
| laser_likelihood_max_dist | 2,0 m | Engele uzaklık alanı üst sınırı |
| z_hit / z_rand | 0,5 / 0,5 | Gaussian isabet ve rastgele ölçüm katkıları |
| sigma_hit | 0,2 m | Gaussian genişliği; daha küçük değer yanlış poz örneklerini keskin cezalandırır, yanlış kümeye kilitlenme riski var |
| resample_interval | 1 | Her uygun filtre güncellemesinde yeniden örnekleme |
| do_beamskip | false | Mevcut likelihood_field yerine prob modeliyle ilişkili mekanizma; bu deneyde açılmadı |
| transform_tolerance | 1,0 s | map→odom TF’nin ileri tarihli geçerliliği; fiziksel ölçüm damgası veya extrapolasyon izni değildir |

Filtre güncelleme ve TF damgalama ayrıntıları [amcl_node](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_amcl/src/amcl_node.cpp); beam skipping koşulları [prob model](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_amcl/src/sensors/laser/likelihood_field_model_prob.cpp) üzerinden incelendi. Son durumda yalnız model alanı beam’dir; diğer sayılar aynı kaldı. Beam’de likelihood alanına özgü `laser_likelihood_max_dist` ve prob modelin beam-skipping alanları etkin değildir. Mevcut `z_short=0,05`, `lambda_short=0,1`, `z_max=0,05` beam modelde kısa/maksimum menzil katkılarını etkinleştirir. Kaynak incelemesi: [Humble differential model](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_amcl/src/motion_model/differential_motion_model.cpp), [likelihood field](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_amcl/src/sensors/laser/likelihood_field_model.cpp). Kurulu paket sürümü versions.txt; uzak branch ile binary derleme hash eşleşmesi iddia edilmez.

Gözlem modelinin ek ayrıştırması: `likelihood_field` dolu hücreye uç mesafesini toplamsal kübik ağırlıkla birleştirir. [Sürekli kutu surrogate](stage1-3-2026-11-11/endpoint-likelihood-surrogate.json), terminalde yanlış map pozunun gerçek pozun skorunun %88–92’sini koruyabildiğini gösterir; bu tam raster AMCL skoru veya kesin posterior nedeni değildir. Dolu hacme uç uzaklığı ile gerçek ray menzil hatası ayrı metriklerdir. [Beam modeli](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_amcl/src/sensors/laser/beam_model.cpp) her örnekte beklenen map ray menzilini hesaplar; tek alan model karşılaştırması bu farklılığı sınar. Beam’in ilk üç bağımsız koşusu 0,223 / 0,244 / 0,154 m ile geçti; ardından iki farklı heading ve ilgili canlı regresyonlar da geçti. [Son etkin AMCL dump’ı](stage1-3-2026-11-11/acceptance-pickup/runtime-amcl.yaml) ürün şablonundaki beam seçimini doğrular.

## 6. Nav2 local planner analizi

DWB ve controller sabit tutulur. BaseObstacle, trajectory merkezindeki lethal/inscribed/unknown costmap değerini reddeder; ret tek başına fiziksel temas demek değildir. [Humble BaseObstacle kaynağı](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_dwb_controller/dwb_critics/src/base_obstacle.cpp). `diagnostics.jsonl` global/local plan, local/global occupancy costmap, published footprint, örneklenmiş candidate skorları/ret nedenleri ve Nav2 feedback içerir. [OccupancyGrid dönüştürücüsünde](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_costmap_2d/src/costmap_2d_publisher.cpp) 99 inscribed, 100 lethal’dır; native 253/254 ile aynı sayı değildir.

Yeni A/pickup-2 abortunda aynı grid damgasında map tahmini merkez maliyeti 99, gerçek fiziksel merkez map→odom dönüşümüyle aynı grid frame’ine taşındığında 73’tür. Son fiziksel merkez x≈4,649, map x≈4,524; raf sınırı 4,25 m. [Aynı damgalı iz ve güvenli zarf grafiği](stage1-3-2026-11-11/baseline-abort.png). Bu fiziksel koridor darlığından ayrı, lokalizasyonun statik map engeliyle çatışmasına doğrudan destek sağlar. Candidate BaseObstacle retleri ayrıca vardır. Global planın alınması yürütme garantisi değildir; başlangıç planı engelden ~0,491 m uzak geçerken ilerleyen bazı yeniden planlar zaten hatalı tahminle raftan yalnız ~0,25 m uzaktaki başlangıçtan çıkar. Bunlar güvenli sürekli swept-path kanıtı sayılmaz. Seçilen beam modelinde controller değiştirilmeden aynı köşe geçildi; [aynı damgalı başarılı yaklaşma](stage1-3-2026-11-11/beam-approach.png) fiziksel ve map izlerini gösterir. Yeni beşli koşuda recovery sayısı 0; aday retleri yalnız hata terminali olarak yorumlanmadı. Aday skorları 0,5 s aralıklı örneklenir, short-circuit nedeniyle bütün critic’ler her adayda hesaplanmaz; sürekli/eksiksiz skor taraması iddiası yoktur.

## 7. pick_A2 geometrik yaklaşma

[Geometri ölçümü](stage1-3-2026-11-11/geometry.json): profil hedefi `(2,25;5,75;π/2)`; rack_A2 `[0,25;4,25]×[6,5;7,5]`. Hedef–servis yüzü 0,75 m; gerçek gövde yaw=π/2 için ön yüz boşluğu 0,50 m; r=0,30+0,01 m tam dönüş dairesi artık boşluğu 0,44 m. Güney yaklaşma koridoru 2,25 m geniştir, iki yandaki 0,31 m zarf sonrası 1,63 m kalır. Bu hesap hedefin statik olarak erişilemezliğini desteklemez; hareket boyunca lokalizasyon belirsizliğinin aynı açıklığa sığacağını garanti etmez.

## 8. Uygulanan ve reddedilen varyantlar

[Düzeltme kapısı](stage1-3-2026-11-11/correction-gate.md) dosya, kanıt, seçenekler, güvenlik etkisi, geri dönüş ve regresyonları **kalıcı satır değişikliğinden önce** kaydetti. `config/simulation-c2-3-params.template.yaml` içinde yalnız `laser_model_type: likelihood_field → beam` uygulandı. Geri dönüş yalnız bu alanı eski değere almaktır; kullanıcı diff’leri geri alınmaz.

| Tek değişkenli varyant | Üçlü fiziksel kabul / gerçek Nav2 | Kalıcı seçim |
|---|---|---|
| sigma_hit 0,20→0,05 | 0/3; üç ABORTED | Reddedildi |
| alpha1 0,20→0,02 | 0/3; bir ABORTED | Reddedildi |
| alpha4 0,20→0,002 | Yeni temiz seçki 3/3; 0,230 / 0,340 / 0,341 m | Seçilmedi; sınır yakınında, farklı koşul kanıtı yok |
| alpha3 0,20→0,02 | Yeni seçki 1/3; iki ABORTED | Reddedildi |
| sigma_hit 0,20→0,10 | Üç geçerli ölçümde 0/3; üç ABORTED | Reddedildi |
| max_beams 60→180 | 2/3; bir ABORTED | Reddedildi |
| laser_model_type→likelihood_field_prob | 2/3; üç SUCCEEDED, bir fiziksel hata 0,363 m | Reddedildi |
| laser_model_type→beam | İlk 3/3, farklı heading’lerde 6/6 | **Uygulandı** |

İlk alpha4 ve ilk alpha3 dünyaları fiziksel kriteri sağlasa da bridge -11 ile kapandı; ayrı tekrarlar bunları silmez. Yeni alpha3 seçkisinin ikinci dünyası da -11 ile kapandı. Sigma-010 üçüncü dünyasında başlangıç TF örneği boş kaldı: ABORTED ve son fiziksel hata kaydedildi, fakat senkronizasyon kabulü geçersiz sayıldı; tek yeni replacement dünya ile üçüncü geçerli ölçüm alındı. İlk baz çizgiden ayrı bir dünya yalnız seçili planlama sorguları için kaydedildi; baz çizgi üçlüsüne sessizce eklenmedi.

Toplam **51 izole dünya**, bütün iyi/kötü/geçersiz kayıtlarıyla [tam sonuç tablosunda](stage1-3-2026-11-11/comparison-tables.md). Farklı varyantlar tek bir başarı yüzdesinde birleştirilmedi. Fiziksel collision, 0,36 m etkin track, local/global r=0,30 m ve padding, inflation, xy/yaw toleransları, controller/velocity/recovery sınırları, TF ve gerçek istasyonlar korunur. TF offset, kabul eşiği büyütme, yapay başarı veya otomatik görev temizleme yoktur.

## 9. Beş bağımsız fiziksel pickup kabulü

Düzeltmeden sonra **beş yeni ve bağımsız Gazebo dünyası**, gerçek ürün şablonu, aynı beta başlangıcı `(5,25;7,75;π/2)` ve aynı gerçek hedef `(2,25;5,75;π/2)` kullanıldı. Deney AMCL override’ı verilmedi; `generated/experiment.json` boştur. Her reset fiziksel poz/yaw ve duruşla doğrulandı. [Beşli kapı](stage1-3-2026-11-11/acceptance-gate.json) uçtan uca testlerden önce geçti.

| Koşu | Nav2 | Fiziksel hata (m) | Gerçek yaw hata (rad) | Map–fiziksel (m) | Recovery | Temas / duruş |
|---|---|---:|---:|---:|---:|---|
| [pickup-1](stage1-3-2026-11-11/acceptance-pickup/pickup-1/analysis.json) | SUCCEEDED | 0.253855 | 0.236706 | 0.096016 | 0 | Yok / geçti |
| [pickup-2](stage1-3-2026-11-11/acceptance-pickup/pickup-2/analysis.json) | SUCCEEDED | 0.214297 | 0.236574 | 0.056107 | 0 | Yok / geçti |
| [pickup-3](stage1-3-2026-11-11/acceptance-pickup/pickup-3/analysis.json) | SUCCEEDED | 0.282275 | 0.251357 | 0.067182 | 0 | Yok / geçti |
| [pickup-4](stage1-3-2026-11-11/acceptance-pickup/pickup-4/analysis.json) | SUCCEEDED | 0.199725 | 0.222296 | 0.043334 | 0 | Yok / geçti |
| [pickup-5](stage1-3-2026-11-11/acceptance-pickup/pickup-5/analysis.json) | SUCCEEDED | 0.172636 | 0.232119 | 0.066259 | 0 | Yok / geçti |

**5/5 geçti.** Ortalama fiziksel hata 0.224558 m, en kötü 0.282275 m; sınır **0,350 m**. Bu sonlu tekrar güvenilirliğe yönelik sınırlı kanıttır, bütün koşullarda garanti değildir. Yaw ölçümleri ayrıca raporlandı; fiziksel yaw için yeni bir kabul eşiği uydurulmadı.

Terminal ve duruş ölçümleri farklı gerçek `/clock` damgalarıyla saklandı; fiziksel merkez ve map TF her örnekte aynı damgada karşılaştırıldı. Son bir saniyelik fiziksel merkez yayılımı beşinde de 0, odom doğrusal/açısal hızları ≤0,01; beş dünya 0 ile kapandı. Terminal sonrası bekleme monotonic yaklaşık 2 s, gerçek sim zaman aralığı analysis.json’da ayrıdır.

Son covariance xx 0,0478–0,1206 m²; covariance yaşı 2,005–2,420 s. Kovaryans terminal zamanına taşınmış gibi sunulmadı. Son tam damgalı ray örneklerinde fiziksel medyan hata 0,00204–0,00231 m, map medyanı 0,0262–0,0311 m; occlusion/kenar p90’ı ayrıdır. ParticleCloud ham poz/ağırlıkları saklandı; son bulut 201–228 parçacık, gerçek merkezin 0,35 m çevresindeki ağırlık payı %60,5–85,1. Bunlar kalibre güven olasılığı değildir. Bazı başarılı koşularda bulut hâlâ geniştir; global yakınsama veya sıfır lokalizasyon hatası iddia edilmez.

## 10. Tek/paralel görev sonuçları

[Ürün karşılaştırmaları](stage1-3-2026-11-11/e2e-acceptance.json) gerçek Chrome formu → HTTP API → FM/SQLite Outbox → ExecuteTask → Nav2 zincirini, bağımsız C4 Battery Simulator ve canlı TF/Path render’ını içerir. Mock HTTP/WS, kayıt oynatma veya ayrı GUI hareket modeli yoktur. Her son koşu yeni dünya ve yeni volume DB dosyasıdır; mevcut DB’nin boş olması tek başına reset kanıtı sayılmadı.

| Son koşu | Robot / rota | Sonuç | Fiziksel pickup / dropoff (m) | Görev penceresi tüketimi |
|---|---|---|---:|---:|
| scenario-a2 | alpha: pick_A1→packing_1 | COMPLETED | 0,123560 / 0,270257 | 4,267534 Wh |
| scenario-b | alpha: pick_A1→packing_1 | COMPLETED | 0,132588 / 0,193822 | 4,259306 Wh |
| scenario-b | beta: pick_A2→quality_1 | COMPLETED | 0,167846 / 0,229692 | 2,400403 Wh |

Üç task’ın yetkili COMMIT kayıtlarında **QUEUED → ASSIGNED → EXECUTING → COMPLETED** tam dizisi doğrulandı. Chrome, paralel görevlerin çok kısa ASSIGNED aralığını her iki task için örnekleyemedi; EXECUTING ve iki COMPLETED canlı görüldü. ASSIGNED kaynak kanıtı `committed-events.jsonl` dosyasındadır; gözlenmeyen UI karesi üretilmedi. İki gerçek yürütme penceresi **66,999584 s** örtüştü.

Üç assignment_epoch=1 olması normaldir; robot/task bağlamları ayrıdır. ExecuteTask UUID’leri A2 `00b67773-bfae-4881-8641-7fcbbafef70d`, B alpha `a349e375-106b-43fe-8d8d-11a0b7e9cf65`, B beta `cf5f93e1-294a-4c51-b0af-8273185128e8`. Gerçek action yanıtındaki completed_epoch=1 ve UUID eşleşti. Her task için tek EXECUTE_TASK Outbox komutu, tek gönderim, değişmez payload; HTTP exact replay 200/DUPLICATE, yeni fiziksel görev yok. İki DB integrity=ok, foreign key hatası ve review hold yok, kaynak tek sahipliği korundu. FAILED görev temizlenmedi.

A2’de robot başına 399, B’de 391 Chrome/BatteryState eşleşmesi; Wh uyuşmazlığı 0. TF–RobotStatus aynı damga farkları ≤8,3e-15 m; Chrome render karşılaştırmaları A2 alpha/beta 407/440, B alpha/beta 270/294 örnekte tam eşleşti. Her robotta tek yayın oturumu ve artan status_seq korundu. [Tek görev görseli](stage1-3-2026-11-11/chrome-a2/completed-overview.png) ve [iki tamamlanan görev](stage1-3-2026-11-11/chrome-b/completed.png) doğrudan incelendi.

İlk scenario-a **tam kabulü geçmedi**: taşıma COMPLETED ve fiziksel kriterler geçse de test Docker zarfında `--add-host scene:127.0.0.1` unutuldu; API’nin `ws://scene:20313` bağlantısı kurulamadı, Chrome TF paketi 0 idi. Bu test hazırlama hatasıdır, AMCL düzeltmesi sayılmaz. İlk kayıt/DB ve başarısız karşılaştırma korundu. Alias eklendikten sonra yeni scenario-a2 ve scenario-b koşuları bütün karşılaştırmaları geçti. A1/A2/B runtime çocuklarının tamamı 0 ile kapandı. Bunlar nihai üç servis dağıtımı kabulü değildir.

## 11. Collision ve footprint

[Canlı parametre denetimi](stage1-3-2026-11-11/runtime-costmap-audit.json): beta local/global radius=0,30 m, padding≈0,01 m, inflation=0,45 m, resolution=0,05 m. Local frame robot_beta/odom, global frame map. Üretici iki robotta iki radius’u assert eder; [kaynak/zarf denetimi](stage1-3-2026-11-11/preservation-and-contract-audit.json) tüm izole SDF’lerde gövde 0,50×0,30×0,10 m ve track=0,36 m olduğunu, controller/planner/behavior parametrelerinin değişmediğini doğrular.

Gerçek birleşim zarfı hesabı önceki Aşama 1.2’de korunur: gövde köşe yarıçapı 0,291548 m. Model/collision küçültülmedi. Robot base/tekerlek/caster contact topic’leri izlendi; zararlı temas gözlemcide hata ve cancellation üretir. Beşli kabul ve son görevlerde zararlı temas kaydı yok. Ayrık gözlemler, örneklenmiş yol/trajectory veya global plan sürekli çarpışmasızlık garantisi değildir. C4 dock teması ise beklenen ve ayrı kabul koşuludur.

## 12. Regresyonlar

| Bu çalışmada yeniden koşulan seçki | Sonuç | Kanıt |
|---|---|---|
| Yeni + önceki ölçüm/frame seçkisi | 16 geçti | measurement-tests-final.log |
| Tam host Python/Executor | 455 geçti, 29 atlandı, 1 uyarı | host-tests-final.log |
| Tam Humble/CycloneDDS | 505 geçti, 0 atlandı, 1 uyarı | ros-tests.log |
| C3.3.3 canlı T01–T10 | GEÇTİ; iki container 0/0 | [regression-c333](stage1-3-2026-11-11/regression-c333/result.json) |
| Gerçek HIGH / T04-HIGH-E2E | GEÇTİ; iki container 0/0 | [regression-high](stage1-3-2026-11-11/regression-high/result.json) |
| C4.1 tüketim | GEÇTİ; iki container 0/0 | [regression-c41](stage1-3-2026-11-11/regression-c41/result.json) |
| C4.2 batarya güncelliği/teslim | GEÇTİ; iki container 0/0 | [regression-c42](stage1-3-2026-11-11/regression-c42/result.json) |
| Eski C4 profilinde C4.4 dock temas/ayrılma | GEÇTİ; iki container 0/0 | [regression-c44](stage1-3-2026-11-11/regression-c44/result.json) |

505 Humble testi ROS/IDL gereken host atlamalarını kapsar; host skip başarı sayılmaz. Uyarı FastAPI/Starlette TestClient httpx deprecation’ıdır. C3 T07 STALE, T08 SESSION_BLOCKED, rezervasyon/BLOCKED ve eski epoch/UUID korumaları; ayrıca gerçek HIGH terminal PREEMPTED+duruş kapısı geçti. Saklanan C3/HIGH ve C4.4 DB’lerde integrity=ok, foreign key ihlali yok; beş canlı projenin hepsinde clean=true, çıkışlar 0/0, OOM yok. Image yeniden build edilmedi; çözülmüş Compose ve gerçek image kimlikleri saklandı. Yalnız bu görevin projeleri, kanıt/DB alınmasından sonra down edildi; başka ağ/container/volume silinmedi.

Tuning sırasında üç bridge kapanışı -11 ile kaldı; bunlar başarılı regresyonlara eklenip silinmedi. Son seçilen modelin 14 izole dünyası, C5 A1/A2/B kapanışları ve son canlı regresyonları temizdir; bu, eski bridge alt nedeninin giderildiği kanıtı değildir. Battery SIGTERM düzeltmesi korunur; C5’de altı gerçek batarya çocuğu 0 kapandı. Eski 30/30 lifecycle seçkisi bu çalışmada yeniden koşulmuş sayılmaz; önceki _take_subscription kesin kök nedeni çözüldü denmez. Yeni gözlemci başlangıç TF’sini aynı sabit stamp’te bounded bekler; geçmiş geçersiz koşu korunur.

## 13. Performans

Aynı Docker VM (ARM64, 8 CPU, 8,32 GB), aynı image ve sıralı dünyalar kullanıldı. Önceki tarihlerdeki sonuçlar eş performans baz çizgisi sayılmadı. [Ham/özet performans](stage1-3-2026-11-11/performance-comparison.json) ve [bütün varyantlar](stage1-3-2026-11-11/comparison-tables.md) gerçek damgaları içerir. CPU %100 bir çekirdektir, 0,5 s /proc örnekleri tepe/ölçek garantisi değildir.

| Aynı 30×18 m profilinde birincil pencere | Eski A (3) | Beam ilk (3) | Ürün kabulü (5) |
|---|---:|---:|---:|
| Terminal penceresi medyan (sim s) | 24.500 | 25.015 | 25.355 |
| Gözlenen RTF medyan | 0.995 | 0.987 | 0.999 |
| Beta AMCL CPU ortalaması (%) | 2.716 | 3.597 | 3.140 |
| Son map–fiziksel medyan (m) | 0.183 | 0.032 | 0.066 |

Terminal penceresi başarısız koşuda abort’a kadar olan süredir; başarılı tamamlanma süreleriyle aynı başarı sınıfı gibi yorumlanmaz. Model değişimi küçük bir AMCL CPU artışı gösterdi; kesin performans üstünlüğü iddiası yoktur. Covariance ve fiziksel hata birlikte değerlendirilir.

Seçili 8 ComputePathToPose sorgusunun her biri baz planlama dünyası, beam ilk ve ürün kabulü son dünyasında SUCCEEDED. Planlama medyanı alanı sırasıyla 0.0 / 5.0 / 0.0 ms, action toplam monotonic duvar medyanı 36.552 / 36.155 / 36.074 ms. Bunlar birincil sürüşten **sonra**, sabit başlangıç/hedef ayaklarıyla alınan sorgulardır; görev içindeki her otomatik replan’ın süresi değildir. [Planner kaynağı](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_planner/src/planner_server.cpp) planning_time’ı node now() ile ölçer; use_sim_time ve 5 ms Gazebo adımı nedeniyle 0/5 ms kuantalanma görülür. 0 ms sıfır CPU maliyeti anlamına gelmez.

Gözlenen damga frekansları scan≈5,00 Hz, odom≈26–28,2 Hz, odom TF≈28,57 Hz; bunlar gözlemcinin aldığı mesajlardır. Yeni beşlide alım anındaki /clock–TF stamp farkı medyanı 0–0,015 s, tepe 0,27–0,745 s. Callback/log kuyruğu etkisi olan bu fark gerçek uçtan uca ağ gecikmesi değildir; map→odom’un +1 s tolerans damgası da ölçüm zamanı sayılmaz. Gerçek yayıncı-alıcı tek yönlü duvar gecikmesi ayrıca doğrulanmadı. Hiçbir matematiksel poz karşılaştırması extrapolasyonla tamamlanmadı.

Son Chrome koşularında render/TF ve batarya eşleşmeleri geçti; başlangıç/restart sırasında geçici disconnected/product_unavailable olayları kayıtta kaldı. İlk yanlış DNS zarfının uzun scene kesintisi başarısız kabul olarak ayrıdır. Bu kısa koşular uzun süreli ROS/Chrome bağlantı garantisi değildir.

## 14. Başarısız ve doğrulanamayan maddeler

- **BAŞARILI / DOĞRULANDI:** Bu profil ve koşullarda güvenli zarfla 5/5 fiziksel pickup, farklı heading’lerde seçilmiş modelin 6/6 tekrarı, gerçek tek ve iki paralel taşıma, listelenen host/Humble/C3/C4 regresyonları. Eski Aşama 1.2’nin 1/5 sonucu geriye dönük değiştirilmedi.
- **BAŞARISIZ / KORUNDU:** Reddedilen varyantların abort/hassasiyet hataları; üç tuning dünyasının bridge -11 kapanışı; ilk C5 A koşusunun eksik test DNS aliası nedeniyle TF/görsel kabulü; sigma-010’un ilk TF örneği boş olan gözlemci koşusu. Son ikisi hazırlama/ölçüm hatası olarak giderildi ve yeni koşular ayrı saklandı.
- **DOĞRULANAMADI / AÇIK:** Bridge çökmesinin kesin alt nedeni, raf simetrisinin ayrı nedensel payı, bütün hızlarda odom/model kalibrasyonu, global lokalizasyon güvenilirliği, gerçek tek yönlü TF ağ gecikmesi, uzun süre/tepe yük/3+ robot ve bütün istasyonlar. Covariance veya parçacık ağırlıkları fiziksel doğruluk garantisi değildir.
- **KARAR GEREKTİRİYOR:** Bu çalışma için yeni istasyon/raf koordinatı kararı gerekmiyor; mevcut hedefin erişilemezliği kanıtlanmadı ve aynı gerçek hedef kabulü geçti. Ürün yerleşimi kendiliğinden değiştirilmedi. Gelecekte böyle değişiklik gerekirse ayrı kullanıcı kararı gerekir.

## 15. Sonraki adımlar

Bu aşamada duruldu. **Aşama 2 otomatik şarj, Aşama 3 trafik ve 27 istasyon fiziksel taraması başlatılmadı.** Eski C4 dock regresyonu bunların yerine geçmez. Bridge kapanış çökmesi için gelecekte ayrı yeniden üretim/backtrace çalışması ve model güvenilirliği için daha geniş ama kontrollü koşullar önerilir; bu görev yeni kapsam veya onay üretmez.

[Ham arşiv manifesti](stage1-3-2026-11-11/raw-evidence-manifest.json), dosya SHA’ları ve kaynak snapshot’ları iyi/kötü bütün koşuları korur. Ham JSONL/log/SDF/harita dosyaları yerelde kalır; Git’te per-varyant arşiv ve küçük özetler tutulur. Arşivler yeni boş bir dizine açılarak doğrulanabilir; mevcut kullanıcı dosyalarının üzerine açılması önerilmez. Video dosyaları yerelde korunur, ayrı medya hash manifestindedir. Kullanıcı dirty kaynakları korunur; sadece bu görevin araç/config/rapor ve kanıt değişiklikleri commit edilir. Push veya merge yapılmadı.
