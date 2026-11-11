# C5 Aşama 1.2 — Fiziksel model, odometri, AMCL ve footprint doğrulaması

11 Kasım 2026 · [Komut ve kanıt eki](c5-stage1-2-commands-2026-11-11.md) · [Ham kanıtlar ve özetler](stage1-2-2026-11-11/) · [Önceki Aşama 1.1](stage1-1-validation-2026-11-11.md)

**AŞAMA 1.2 KABUL EDİLMEDİ. F2 AÇIK.** Dönüş odometrisinin ölçülen sistematik hatası büyük ölçüde azaltıldı; collision zarfını kapsayan Nav2 yarıçapı uygulandı. Buna rağmen son beş bağımsız pickup denemesinde yalnız **1/5** fiziksel kabul sağlandı: iki Nav2 abort, iki başarılı Nav2 terminalinde 0,350 m üstü fiziksel hata vardır. Gerçek paralel görevde beta FAILED oldu. Geometrik güvenlik düzeltmesi operasyonel erişim kabulü değildir. Bataryanın kanıtlanan SIGTERM kapanış eksikliği düzeltildi; eski `_take_subscription` hatasının kök nedeni kesinleşmedi.

## 1. Başlangıç Git ve kaynak durumu

Ana worktree `main / 32e23fc` yalnız okundu. Çalışma mevcut `/Users/murat/develop/ros2-fleet-manager-c5-warehouse-grid`, `feat/c5-warehouse-grid-layout` dalında yürütüldü. Başlangıç HEAD `c79f2de0ca11fd37e73d4eac23d31de71df9ba5b`: Aşama 1.1 rapor commit’i doğrulandı. `7b2bc82`, `0b9dee8`, `f5cff89` geçmişte yerindedir. 30 × 18 m profil, görev API’si, frontend ve önceki kanıtların önemli bölümü kaydedilmemiş kullanıcı değişiklikleriydi; başka checkout açılmadı. [Başlangıç Git kaydı](stage1-2-2026-11-11/baseline.json) ve [dosya hash’leri](stage1-2-2026-11-11/baseline-hashes.json) korunur. Reset, clean, stash, rebase, merge ve push yapılmadı.

[Proje bağlamı](../../project-context.md), [harita](../../README.md), C3.3.1–C3.3.3 kararları, Outbox sözleşmesi, C4 kabul listesi ve Compose kılavuzu okundu. Önceki Aşama 1/Aşama 1.1 raporları; localization-analysis, physical-measurements, feedback-contract; üç bağımsız deneyin ham kayıtları ve scenario-a/b/a2/b2 karşılaştırmaları incelendi. Tarihsel sonuçlar bu koşunun sonuçlarına eklenmedi.

Bu çalışmanın kod/test commit’leri: `072131a` ölçüm araçları; `36e0b50` etkin track; `5ca037b` güvenli dairesel zarf; `971e586` kontrollü batarya kapanışı ve ROS test readiness. Rapor/kanıt commit SHA’sı son yanıtta verilir.

## 2. Gazebo modeli, yayıncılar ve Burger karşılaştırması

[Ayrıntılı karşılaştırma](stage1-2-2026-11-11/model-comparison.md): bu dünya gerçek Burger collision/tekerlek modeli değildir. Gövde 0,50×0,30×0,10 m, ana kütle 2 kg, tekerlek r=0,10 m, genişlik 0,04 m, merkezler ±0,20 m; destekler r=0,05 m küredir. ROBOTIS Humble Burger URDF’sinde gövde collision 0,140×0,140×0,143 m ve ofsetlidir; tekerlek r=0,033 m, genişlik 0,018 m, merkez açıklığı 0,160 m. Chrome’daki nominal görsel fiziksel kabul kaynağı değildir. [ROBOTIS URDF](https://raw.githubusercontent.com/ROBOTIS-GIT/turtlebot3/humble/turtlebot3_description/urdf/turtlebot3_burger.urdf) · [özellikler](https://emanual.robotis.com/docs/en/platform/turtlebot3/features/)

Odometri: Gazebo joint position → Fortress DiffDrive odometri integrasyonu → Gazebo odom → bridge → ROS odom → TF helper’ın odom→base_link yayını. AMCL map→odom üretir. Ground truth ayrı PosePublisher→physical_pose yolundadır. Ground truth odometri veya TF yerine geçirilmedi. [Fortress kaynak incelemesi](https://raw.githubusercontent.com/gazebosim/gz-sim/ign-gazebo6/src/systems/diff_drive/DiffDrive.cc) encoder/joint konumu integrasyonunu destekler; kurulu binary’nin kaynak derleme hash eşleşmesi doğrulanmadı.

Üretilmiş dünya DART, 5 ms timestep ve hedef real_time_factor=1 kullanır. Tekerlek eksenleri model Y ile tutarlıdır; ileri/geri işaretleri fiziksel deneyle sınandı. Özel tekerlek sürtünmesi yoktur; desteklerde mu/mu2=0 vardır. Bu değerler kalibre lastik modeli değildir. Test süreleri `/clock`; timeout, ağ ve kapanış süreleri monotonic ile ölçüldü.

## 3. Kök neden matrisi

| Konu | Sınıf | Kanıt / sınır |
|---|---|---|
| Nominal tekerlek yarıçapı/merkez açıklığının SDF ile plugin arasında yazım farkı | ELENDİ | İlk kaynakta r=0,10 ve merkez açıklığı=0,40 m iki yerde tutarlı; düz 0,80 m deneyleri ölçek hatasını desteklemez |
| Fiziksel dönüş ile joint odometrisi arasında yaklaşık %11 fark | KANITLANDI | Bağımsız 90°/180° ve dönüş+düz deneyleri |
| DART temasında etkin dönme açıklığının yaklaşık 0,36 m olması | GÜÇLÜ BİÇİMDE DESTEKLENİYOR | İki bağımsız dönüşten 0,3602/0,3601 m; 0,36 m varyantında yeni dönüşler yaklaşık 0,001 rad farkla eşleşti |
| Temas çözücüsünün iç tekerlek kenarına kilitlenmesi | GÜÇLÜ BİÇİMDE DESTEKLENİYOR | Temaslar ±0,18/±0,22 m kenarlarda; etkin açıklık iç kenarlarla eşleşir. Kuvvet/constraint çözümü ölçülmedi; kesin engine alt nedeni sayılmaz |
| Timestep’in 5 ms olması tek başına dönüş farkını yaratıyor | ELENDİ (sınanan düşük hızlı dönüş için) | Yalnız 1 ms varyantında 1,744028 rad fiziksel / 1,570400 rad odom; fark sürer |
| Genel frame/zaman karışıklığı bu yeni odom farkını açıklıyor | ELENDİ (eşleşen kayıtlar için) | Başlangıç frame’i döndürülür; fiziksel/odom örnekleri aynı damgada, interpolasyon aralığı ayrıca kaydedilir |
| AMCL/map pozunun fiziksel pozdan ayrışması | KANITLANDI | Aynı damgalı map→odom→base_link ve bağımsız fiziksel yayın; raw scan ray/box karşılaştırması |
| Tekrarlı raf geometrisi, AMCL hareket gürültüsü ve örneklemenin kalan sapmadaki ayrı payları | OLASI / BELİRSİZ | Parçacık bulutu ve covariance geniştir; kontrollü tek-parametre AMCL nedensellik deneyi yapılmadı |
| Fiziksel collision zarfını r=0,25 m’nin kapsayamaması | KANITLANDI | Gövde köşe yarıçapı 0,291548 m; padding’li 0,26 m de yetersiz |
| Büyük footprint ile her mevcut rota aynı biçimde yürür | ELENDİ | Son beş pickup’ın ikisi ve gerçek paralel beta görevi Nav2 abort oldu |
| Battery SIGTERM handler eksikliği | KANITLANDI / DÜZELTİLDİ | Önce 7/7 SIGTERM -15; sonra 7/7 SIGTERM 0 ve context kapalı |
| Eski rclpy `_take_subscription` RuntimeError alt nedeni | BELİRSİZ | Önceki traceback incelendi; yeni 60 canlı başlat/kapat denemesinde yeniden üretilmedi |

## 4. Kontrollü odometri deneyleri

Her satır ayrı Gazebo dünyasıdır. Açık alan deneylerinde beta `(12;0;0)` başlar; koridor deneyinde `(-7;5,25;0)`, 2,25 m raf aralığında düşük hızlı düz sürüş yapılır. Bu koridor ölçümü 1,05 m yaklaşma açıklığı veya karşılıklı trafik kabulü değildir. Konumlar yalnız yeni deney profilinin spawn girdisidir; çalışan robot ışınlanmadı. Nav2 aktif olsa da bu ilk altı deneyde goal gönderilmedi; doğrudan test cmd_vel kullanıldı. FM/Executor ve dock güvenliği değiştirilmedi.

| Deney / varyant | Fiziksel yol / odom (m) | Fiziksel dönüş / odom (rad) | Uç konum farkı (m) | Yaw farkı (rad) |
|---|---|---|---|---|
| forward / baseline-motion | 0.801520 / 0.800000 | -0.000000 / -0.000000 | 0.000320 | 0.000000 |
| reverse / baseline-motion | 0.800082 / 0.800000 | 0.000000 / 0.000000 | 0.000082 | -0.000000 |
| turn90 / baseline-motion-rest | 0.000002 / 0.000000 | 1.743429 / 1.570000 | 0.000001 | -0.173430 |
| turn180 / baseline-motion-rest | 0.000004 / 0.000000 | 3.489960 / 3.142000 | 0.000001 | -0.347960 |
| turn_forward / baseline-motion-rest | 0.801318 / 0.800000 | 1.744896 / 1.571000 | 0.138975 | -0.173896 |
| corridor / baseline-motion-rest | 0.601996 / 0.600000 | 0.000000 / 0.000000 | 0.000181 | 0.000000 |
| turn90 / effective-track | 0.000002 / 0.000000 | 1.570145 / 1.571000 | 0.000001 | 0.000855 |
| turn180 / effective-track | 0.000004 / 0.000000 | 3.141011 / 3.142000 | 0.000002 | 0.000989 |
| turn_forward / effective-track | 0.801440 / 0.800000 | 1.570145 / 1.571000 | 0.000754 | 0.000855 |
| reverse / footprint | 0.799582 / 0.799500 | 0.000000 / 0.000000 | 0.000082 | 0.000000 |
| corridor / footprint | 0.602010 / 0.600000 | 0.000000 / 0.000000 | 0.000181 | 0.000000 |

Başlangıç/bitiş fiziksel, odom ve map pozları; simülasyon süresi, iki ayrı hız ölçümü, max interpolasyon aralığı ve temas kayıtları her deneyin `metrics.json`, `localization.json` ve `localization.jsonl` dosyasındadır. Komut hızları düz ±0,10 m/s, dönüş 0,20 rad/s, koridor 0,05 m/s’dir. Fiziksel hız ground truth farkından; odom hızı mesaj twist’inden ayrı hesaplandı. Saf dönüşte fiziksel kayma mesafesi mikrometre ölçeğindedir; hareketli Nav2 rotasında kalan 0,02–0,10 m odom uç farkı vardır. Bütün hız/temas koşullarında kayma giderildiği iddia edilmez.

İlk 180° koşusu son fiziksel örnek için TF henüz alınmadan lookup yapıldığı için gözlemci assertion’ıyla kaldı. Dünya temiz kapandı. Kayıt silinmedi; gözlemci belirlenen sabit damgadaki TF’yi bekleyecek şekilde düzeltildi ve yeni dünyada tekrarlandı.

## 5. Odometri, AMCL ve lidar ayrıştırması

A: başlangıç fiziksel heading’iyle hizalanmış odom uç farkı ilk üç gerçek Nav2 deneyinde 0,620 / 0,667 / 0,650 m; etkin açıklık varyantında 0,090 / 0,051 / 0,072 m oldu. Saf dönüşteki iyileşmenin Nav2 rotasına da yansıdığı ölçüldü; kalan kavis/hız/temas etkisi sıfır değildir.

B: map→odom düzeltmesinin tüm damgalı x/y/yaw dizisi deney `metrics.json` içindeki `map_odom_corrections` alanındadır. C: map ve Gazebo pozları aynı fiziksel stamp’te TF lookup ile karşılaştırılır. Odom yaşı, AMCL stamp’i/yaşı ve interpolasyon aralığı ayrı alanlardır. Kovaryans terminal zamanına taşınmış gibi sunulmaz.

D: ham LaserScan ışınları bu çalışmada kaydedildi. Bağımsız [ray/box analizi](../../../docker/simulation-warehouse-grid/stage12_scan_analysis.py) fiziksel quaternion ile 0,15 m sensör ofsetini ve ışın yönünü döndürür; map tarafında aynı stamp’te SE(2) TF zincirini kurar. Yalnız tam fiziksel quaternion damgası olan scan’ler kullanılır; extrapolasyon yoktur. Fiziksel pozu varsayarak elde edilen son scan medyan ray hataları milimetre düzeyindedir; map pozu ile aynı ışınlarda daha büyük sapma görülür. Sayısal sonuçlar `raycast-alignment.json` ve `raycast-*.log` dosyalarındadır. Occlusion kenarları, statik kutu temsili ve GPU lidar örneklemesi p90’ı etkiler; bu metrik AMCL’nin likelihood skoru değildir. Önceki dolu hacme uzaklık metriğiyle karıştırılmaz.

ParticleCloud ham poz/ağırlıkları, AMCL covariance ve TF birlikte kaydedildi. İlk pose doğru ve reset hata sınırları içindeydi; ilk parçacıklar tek pose etrafında başlar. Hareket sırasında x/y dağılımı genişler. Parçacık sayısının düşmesi veya covariance’ın küçük olması fiziksel doğruluk kanıtı sayılmadı. Aynı başlangıç/hedef için ilk 3, açıklık varyantında 3 ve son varyantta 5 bağımsız koşu yapıldı. Pickup için farklı başlangıç heading’leri ayrıca denenmedi. AMCL parametreleri değiştirilmedi; kalan hatanın raf belirsizliği / alpha katsayıları / örnekleme payları bağımsız nedensellik ölçümü gerektirir.

## 6. Footprint hesabı ve erişim

Gövde köşesi `sqrt(0,25²+0,15²)=0,291548 m`; tekerlek izdüşümünün en uzak köşesi `sqrt(0,10²+0,22²)=0,241661 m`; destekler en çok 0,25 m uzanır. Gerçek birleşim dönüş zarfı gövdede maksimumdur. 0,50×0,44 m AABB’nin boş köşelerini de kapsayan 0,333 m çember gerekli değildir. **Seçilen daire r=0,30 m**, eski 0,01 m padding korunur. Inflation 0,45 m ayrı maliyet alanıdır. Local/global iki costmap aynı geometrik düzeltmeyi aldı.

Mevcut Navfn + DWB BaseObstacle merkez/inscribed maliyet yaklaşımıyla dairesel zarf seçildi; sadece poligon ekleyip köşeler için tam kontrol garantisi ileri sürülmedi. Collision gövdesi, tekerlekler, görsel, C4 dock yarıçapı/temas/lease/duruş koşulları ve hedef koordinatları değişmedi. [Düzeltme öncesi kapı kaydı](stage1-2-2026-11-11/correction-gate.md) seçenek ve gerekçeleri korur.

Her iki varyantta seçili 8 ComputePathToPose sorgusu SUCCEEDED: iki robot için pickup, dropoff, park ve dock. Global plan alınması fiziksel yürütme garantisi değildir. Son yarıçapta yol segmenti merkez–engel mesafesi eksi ihtiyatlı 0,31 m zarfın minimumları ve tüm Path noktaları [rota kaydındadır](stage1-2-2026-11-11/footprint/pickup-5/routes.json). Son ek fiziksel erişimde beta quality_1, park_1, dock_1 hedeflerine sırasıyla 0,207 / 0,094 / 0,133 m merkez hatasıyla ulaştı; zararlı temas gözlenmedi. Park ve dock yalnız bu başlangıç zincirinde geometrik erişimdir; şarj otomasyonu kabulü değildir.

Buna karşılık pick_A2 yaklaşmasında iki bağımsız koşu raf köşesi civarında `BaseObstacle/Trajectory Hits Obstacle`, ardından controller patience ve Nav2 ABORTED ile kaldı. Fiziksel robot engelle temas etmedi. Örneğin ikinci koşuda fiziksel merkez x=4,652, map x=4,481 m idi; map pozu daha büyük footprint ile raf köşesine yakın algılandı. Daha küçük güvensiz yarıçapa dönerek test geçirilmedi. Bu başarısızlık hedefin statik olarak daima erişilemez olduğunu ispatlamaz; lokalizasyon ve yaklaşma rotası birlikte incelenmelidir. Yeni geometri veya hedef taşıma kararı alınmadı. **F3 geometrik eksik kapsaması giderildi; F3 operasyonel regresyon kabulü açık.**

## 7. Değişen parametreler ve geri dönüş

| Değişiklik | Önce → sonra | Gerekçe / beklenen etki | Risk / geri dönüş |
|---|---|---|---|
| DiffDrive etkin track | 0,40 → 0,36 m | Bağımsız dönüş ölçümleri; fiziksel/odom yaw tutarlılığı | Geometri/temas/hız profiline özgü; merkez geometrisi 0,40 m kalır. Yalnız ilgili plugin değerini geri almak |
| Local/global robot_radius | 0,25 → 0,30 m | Gerçek collision birleşimi ve dönüş zarfını kapsamak | Yaklaşma/plan maliyeti değişir; gerçek pickup abortları var. Varyantı kapatmak veya yalnız iki radius değişikliğini geri almak; eski zarfın güvensizliği korunur |
| Battery kapanış yaşam döngüsü | Asenkron KeyboardInterrupt / kontrolsüz SIGTERM → durma bayrağı ve sahip olunan executor | Callback bittikten sonra executor→node→context kapanışı | Callback kilitlenirse yeni kill politikası yok. Yalnız node.py kapanış diff’ini geri almak |
| Timestep deney varyantı | 0,005 → 0,001 s, sonra varsayılan 0,005 korundu | Hipotez testi; fayda göstermedi | Kalıcı uygulanmadı |

AMCL alpha/particle/lidar ayarları, Nav2 xy/yaw toleransları, hız/ivme limitleri, inflation, fiziksel collision ve C4 şarj kapıları korunur. Değişiklikler birden topluca denenmedi: önce baseline → timestep → yalnız track → track üstüne ayrı footprint varyantı. [Batarya değişiklik kaydı](stage1-2-2026-11-11/battery-change.md)

## 8. Beş bağımsız fiziksel pickup yeniden kabulü

Her deneme yeni dünyada, aynı beta başlangıcı `(5,25;7,75;π/2)` ve pick_A2 `(2,25;5,75;π/2)` ile başladı. Kabul değişmedi: gerçek Nav2 SUCCEEDED **ve** duruş sonrası fiziksel merkez hatası ≤0,350 m.

| Deneme | Nav2 | Terminal / duruş fiziksel hata (m) | Duruş yaw hatası (rad) | Map–Gazebo (m) | AMCL covariance xx / yy / yaw | Sonuç |
|---|---|---|---|---|---|---|
| pickup-1 | SUCCEEDED | 0.248280 / 0.248280 | 0.315657 | 0.055011 | 0.056846 / 0.014493 / 0.025281 | GEÇTİ |
| pickup-2 | ABORTED | 2.804932 / 2.804932 | 2.626776 | 0.183957 | 0.029616 / 0.018631 / 0.018896 | KALDI |
| pickup-3 | ABORTED | 2.833775 / 2.833775 | 2.974622 | 0.129855 | 0.034637 / 0.023412 / 0.031361 | KALDI |
| pickup-4 | SUCCEEDED | 0.419834 / 0.419834 | 0.297677 | 0.166313 | 0.095686 / 0.021027 / 0.030531 | KALDI |
| pickup-5 | SUCCEEDED | 0.395827 / 0.395827 | 0.298664 | 0.199819 | 0.093447 / 0.018017 / 0.031075 | KALDI |

Terminal sonrası gözlemci monotonic saatte yaklaşık 2 s bekleyip sabit fiziksel stamp’te TF okur; gerçek simülasyon stamp farkı ham kayıttadır, tam 2 s `/clock` garantisi değildir. Kabul anındaki odom hızları ayrıca kaydedilir. Her satırın covariance stamp’i ve yaşı [pickup sonuç özetinde](stage1-2-2026-11-11/pickup-results.json) ayrıdır. Abort koşularında son covariance yaklaşık 17,5 saniyeye kadar eski olabilir; terminal covariance’ı olarak yorumlanmaz. Zararlı contact kaydı beş koşuda da yoktur; bu sürekli çarpışmasızlık garantisi değildir.

## 9. Fiziksel hata dağılımı

| Varyant | Tekrar | Fiziksel min / ortalama / medyan / max (m) | Fiziksel kabul |
|---|---|---|---|
| baseline-motion-rest | 3 | 0.334898 / 0.391866 / 0.356917 / 0.483783 | 1/3 |
| effective-track | 3 | 0.349878 / 0.370064 / 0.352196 / 0.408118 | 1/3 |
| footprint | 5 | 0.248280 / 1.340530 / 0.419834 / 2.833775 | 1/5 |

Son varyantın yalnız SUCCEEDED terminalleri: 3 örnek, ortalama 0.354647 m, örnek std 0.092895 m. Bütün beş hata için std 1.351611 m’dir; 2,8 m’lik abort uzaklıkları hassasiyet dağılımıyla başarıymış gibi birleştirilmez. **F2 açık.**

## 10. Battery Simulator lifecycle araştırması

Önceki rclpy traceback’i incelendi: native `_take_subscription` / `take_message` sırasında RuntimeError. Mevcut düğüm tek thread’li spin kullanıyordu; eşzamanlı node destroy edildiğine dair kanıt yok. Python SIGINT’in native çağrı sırasında exception enjeksiyonu olası açıklamadır; tekrar üretilmediği için kanıtlanmış kök neden değildir.

İlk lifecycle seçkisi timestep izolasyon dünyasında 1 ms, son seçki normal 5 ms dünyasında yapıldı; image/ROS/Python aynı, callback yükü birebir eşit değildir. SIGTERM’in handler olmadan sonlanması sinyal sözleşmesiyle ayrıca açıktır; bu iki seçki aynı yükte RuntimeError stres karşılaştırması diye sunulmaz.

Önceki kodla gerçek Gazebo mesajları altında 30 deneme: **23 SIGINT → 0**, **7 SIGTERM → -15**. Son kodla aynı image ve canlı trafik altında 30 deneme: **23 SIGINT + 7 SIGTERM → tamamı 0**. Son çocuk loglarında ROS context kapalı, Python thread listesi MainThread; ebeveyn context döngü boyunca açık, sonunda kapalıdır. /proc child kaydı exit sonrası yoktur. Sonraki gerçek A/B supervisor’larında da batarya dahil bütün çocuklar 0 ile kapandı.

Çocuk/ebeveyn çıkış, context, thread sayısı, traceback ve monotonik kapanış süresi [önce](stage1-2-2026-11-11/timestep/turn90/lifecycle/) ve [sonra](stage1-2-2026-11-11/footprint/pickup-5/lifecycle/) saklanır. Python 3.10.12, rclpy 3.3.22 ve Nav2 AMCL 1.1.20 paketleri kullanıldı; ayrı python3-pybind11 paketi bulunmadı, gömülü pybind11 derleme sürümü doğrulanmadı. Son 30 canlı kapanışın en uzunu yaklaşık 0,55 s. Düzeltme exception’ı yutmaz; sinyal yalnız bayrak koyar, spin_once 0,2 s sınırlıdır. Eski RuntimeError **yeniden üretilemedi / çözüldü iddiası yok**; somut SIGTERM eksikliği düzeltildi.

## 11. Gerçek tek/paralel görev ve Chrome/ROS regresyonu

Gerçek Chrome formu, gerçek API, FM, SQLite, Outbox, ExecuteTask, Nav2 ve bağımsız C4 Battery Simulator kullanıldı. Mock HTTP/WS veya simüle GUI hareketi yoktur. Her senaryo ayrı temiz dünya, fiziksel reset kapısı ve yeni volume DB dosyası kullanır. Frontend canlı TF/Path çizer.

| Senaryo / robot | Görev sonucu | Fiziksel pickup / dropoff (m) | Görev penceresi tüketimi |
|---|---|---|---|
| scenario-a / robot_alpha | COMPLETED | 0.084269 / 0.272660 | 4.298513 Wh |
| scenario-b / robot_alpha | COMPLETED | 0.093260 / 0.295598 | 4.260092 Wh |
| scenario-b / robot_beta | FAILED | 2.792582 | 0.228857 Wh |

A tek görev ve B alpha `QUEUED → ASSIGNED → EXECUTING → COMPLETED` oldu. B beta `QUEUED → ASSIGNED → EXECUTING → FAILED`, Nav2 ABORTED ve robot ERROR oldu. Otomatik retry/reassignment veya ClearRobotError uygulanmadı. İlk B tarayıcı kabul aracı FAILED görünce başarısız çıktı; alpha taşıması durdurulmadı ve terminale kadar izlendi. İkinci **salt okunur** Chrome gözlemcisi aynı gerçek tabloda alpha Tamamlandı / beta Başarısız hücrelerini doğruladı. Bu gözlem ilk başarısız kabulü geçersiz kılmaz.

Her task için tek ExecuteTask Outbox komutu / tek gönderim, immutable payload, tekil rezervasyon, SQLite integrity ve request replay idempotency korundu. Beta’nın gerçek başarısız sonucu da doğru goal UUID ve completed_epoch=1 taşıdı; [ayrı başarısız görev güvenlik denetimi](stage1-2-2026-11-11/scenario-b/failed-task-safety.json). Eski başarı odaklı özetleyicideki `actual_result_epoch=false`, SUCCEEDED şartını da içerdiğinden beta’da epoch uyuşmazlığı anlamına gelmez. [A karşılaştırması](stage1-2-2026-11-11/scenario-a/comparison.json) · [B karşılaştırması](stage1-2-2026-11-11/scenario-b/comparison.json)

B’de bağımsız iki robot gerçekten eşzamanlı çalıştı; iki başarılı paralel taşıma kabulü **sağlanmadı**. Chrome/BatteryState ve TF/render karşılaştırmaları geçti. B alpha’nın tamamlanması ilk başarısız browser’ın final snapshot’ından sonra olduğundan ek salt okunur gözlem ayrı kanıttır. A/B kapanışları bütün çocuklarda 0, Docker OOMKilled=false.

## 12. Test sonuçları

| Kontrol | Sonuç |
|---|---|
| İlk host Python / Executor | 442 geçti, 28 atlandı |
| Son host Python / Executor | 449 geçti, 29 atlandı; ROS runtime/IDL eksikliği, skip başarı sayılmaz |
| Yeni ölçüm/frame/raycast/footprint seçkisi | 7 geçti; önceki r=0,25 testinde 1 kaldı / 4 geçti |
| İlk Humble tam seçki | 497 geçti, 2 yeni test gözlemcisi kaldı; DDS uyarısı readiness satırı sanıldı |
| İkinci Humble tam seçki | 498 geçti, 1 C4.2 DDS graph readiness testi kaldı |
| Son Humble tam seçki | **499 geçti**, 1 Starlette/httpx deprecation uyarısı |
| Chrome mock regresyonu | **23 geçti**; task-catalog proxy ECONNREFUSED uyarıları logda, canlı A/B’den ayrıdır |
| Son fiziksel pickup | **1 geçti / 4 kaldı** |
| Seçili 8 + 8 Nav2 rota sorgusu | İki varyantta da 8/8 SUCCEEDED |
| Seçili fiziksel dropoff/park/dock devamı | 3/3 Nav2 SUCCEEDED; yalnız bu rota |
| Battery canlı lifecycle | Önce 23 temiz / 7 SIGTERM hatası; sonra 30/30 temiz |
| Gerçek tek taşıma A | Geçti |
| Gerçek paralel taşıma B | Beta FAILED; iki tamamlanmış taşıma kabulü başarısız |
| HIGH canlı uçtan uca | T04-HIGH-E2E geçti; epoch 2 ve gerçek terminal iptal+duruş |
| C3.3.3 T01–T10 | **10/10 geçti**, STALE/session dahil; backend/simulation 0/0 |

Yeni shutdown testleri artık birleşik stdout içindeki DDS uyarılarını atlayıp gerçek readiness işaretini bekler. C4.2 testi subscription eşleşmesi ile alıcı graph görünürlüğünü aynı an sanıyordu; aynı 3 s bounded DDS bekleme yordamıyla endpoint’in görünmesini bekler. Ürün tazelik/oturum kapıları değiştirilmedi. İlk iki başarısız ROS logu korundu. Son test düzeltmelerinden sonra tüm Humble seçkisi yeniden koşuldu.

## 13. Performans ve sistem yükü

Karşılaştırma aynı macOS ARM64 / Docker Desktop, 8 CPU, aynı image ve 30×18 m profil altında yalnız primary pickup gözlem pencerelerini kullanır. Ek erişim, lifecycle, ROS ve tarayıcı regresyonlarının sonradanki yükü bu pencerelere katılmaz. 0,5 s /proc örnekleri tepe yük veya ölçek garantisi değildir.

| Varyant | Ortalama RTF | İki AMCL CPU toplamı (bir core=100%) | İki AMCL ortalama RSS (MiB) |
|---|---|---|---|
| baseline-motion-rest | 0.9966 | %5.79 | 61.89 |
| effective-track | 0.9962 | %5.92 | 61.73 |
| footprint | 0.9983 | %5.97 | 62.26 |

Odom/physical_pose yaklaşık 28,57 Hz, lidar 5 Hz; AMCL hareket eşiğine bağlı yaklaşık 1–2,5 Hz’dir. Hedef gözlem süresi, başarı/abort durumu, fiziksel hata, frekans ve seçilmiş süreç RSS örnekleri [performans özetinde](stage1-2-2026-11-11/performance-summary.json). Bütün container belleğinin karşılaştırılabilir primary-window zaman serisi alınmadı; AMCL ve seçili süreç RSS’i toplam bellek diye sunulmaz.

Seçili rota sorgularının gerçek Nav2 `planning_time` alanı ve monotonic istemci süresi kaydedildi. Planning_time `/clock` tabanlı ve 5 ms kuantalıdır; sıfır değer hesaplama maliyetinin sıfır olduğunu göstermez. Goal tamamlanma süresi için başlangıç fiziksel ölçümü–terminal alımı penceresi kullanılır; gönderim callback zamanıyla birebir aynı değildir. Başarılı ve abort süreleri ayrı etiketlenir. Uzun süre / tepe yük / 3+ robot garantisi verilmez.

effective-track: Nav2 planning_time ortalaması 1.250 ms; monotonic istemci tur süresi ortalaması 37.236 ms (8 sorgu); footprint: Nav2 planning_time ortalaması 1.875 ms; monotonic istemci tur süresi ortalaması 51.635 ms (8 sorgu).

Başlangıç ölçümünden terminale simülasyon süreleri:

baseline-motion-rest: pickup-1=23.365 s (SUCCEEDED), pickup-2=24.270 s (SUCCEEDED), pickup-3=24.335 s (SUCCEEDED)

effective-track: pickup-1=25.085 s (SUCCEEDED), pickup-2=26.545 s (SUCCEEDED), pickup-3=24.450 s (SUCCEEDED)

footprint: pickup-1=24.935 s (SUCCEEDED), pickup-2=35.885 s (ABORTED), pickup-3=32.195 s (ABORTED), pickup-4=24.065 s (SUCCEEDED), pickup-5=24.465 s (SUCCEEDED).

## 14. Başarısızlıklar ve ortam olayları

F2’nin hem 0,350 m üstü terminal hataları hem Nav2 abortları korunur. Büyük güvenli zarfla gerçek paralel beta taşımasının FAILED olması yeni operasyonel regresyondur. Ayrı parametre etkileri saklanır; farkı gizlemek için hedef, fiziksel pose, TF veya kabul sınırı kaydırılmadı.

İlk 180° gözlemci damga hazır olma hatası, ilk iki ROS seçkisi ve browser B kabul başarısızlığı ham loglarıyla korunur. C3.3.3 ilk başlatması Docker adres havuzunun tükenmesi nedeniyle dünya açılmadan kaldı; yalnız bu görevde yaratılan ve bitmiş HIGH Compose projesinin kanıtı/DB’si alınıp kendi ağı kapatıldı, sonra C3.3.3 tekrar başlatıldı. Kullanıcının diğer ağ/container/volume’leri silinmedi. Bu ilk hata ROS ürün testi sayılmaz.

## 15. Doğrulanamayan maddeler ve kabul sınırı

- **HENÜZ DOĞRULANMADI:** pick_A2 için 5/5 fiziksel kabul ve iki başarılı paralel taşıma; bu koşular başarısızdır.
- **BELİRSİZ:** DART constraint/kuvvet seviyesindeki kesin temas alt nedeni; bütün hızlarda etkin track; kalan AMCL hatasının ayrı neden payları; eski rclpy RuntimeError kök nedeni.
- **HENÜZ TEST EDİLMEDİ:** farklı pickup başlangıç yönleri, 1,05 m kritik açıklığın fiziksel geçişi, bütün 27 istasyon, farklı hedeflerde tekrarlanabilirlik, uzun süre/ölçek ve nihai üç servis dağıtımı.
- **Bu aşama değildir:** tam otomatik şarj kabulü, Aşama 3 trafik ve 27 noktalı ziyaret taraması. Seçili dock geometrisi testi bunların yerine geçmez.
- **DOĞRULANDI:** belirtilen düşük hızlı odometri deneyleri, güvenli collision zarfı hesabı, seçili rota/erişim örnekleri, batarya SIGTERM düzeltmesi, tek görev ve belirtilen regresyonlar; kapsam dışına genellenmez.

## 16. Sonraki aşama riskleri ve durma

Öncelikli engel, doğru güvenli footprint korunurken map/Gazebo ayrışmasının pickup köşesinde hem hassasiyet hem yerel plan geçerliliğini bozmasıdır. Sonraki çalışma mevcut ham scan/particle/TF kayıtlarıyla AMCL hareket gürültüsü ve raf belirsizliğini tek değişkenli deneylerle ayırmalıdır. Güvenli yarıçapı küçültmek veya collision’ı daraltmak çözüm sayılmaz. Geometri/hedef değişikliği gerekiyorsa ayrı karar olarak sunulmalıdır.

Son Chrome görseli de incelendi: aynı tabloda alpha Tamamlandı / beta Başarısız görülür. [Gerçek son tablo](stage1-2-2026-11-11/chrome-b-terminal/terminal-tasks.png)

**Aşama 1.2 açık bırakıldı. Aşama 2/3 ve 27 istasyon taramasına geçilmedi.** Mantıksal kod/test/rapor commit’leri son yanıtta SHA’larıyla bildirilir; kullanıcıya ait önceki değişiklikler eklenmez. Push ve merge yapılmadı. Sonraki aşama için kullanıcı onayı beklenir.
