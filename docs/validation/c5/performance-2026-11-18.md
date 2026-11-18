# C5 kanıta dayalı performans — 18 Kasım 2026

**PARTIAL.** Değişikliksiz baseline tamamlandı; consumer yield ve WAL + FULL tutuldu, composition geri alındı. Gerçek üçlü hareket ve üç taşıma terminali doğrulandı. Görev sonrası park dönüşünde contact guard tetiklendiği için tam C5/hafif profil kabulü yoktur. Önceki TF STALE düzeltmesi korunur; commit/push yapılmadı. Bu kayıt yeni güvenlik veya scheduler politikası onayı değildir.

## Faz 0: değişikliksiz baseline

`codex/telemetry-stale-fix` dalındaki mevcut kaynaklar, üç robotlu `config/fleet.warehouse-30x18.yaml` ve mevcut image kullanıldı. Faz 0 bitiş işareti `2026-11-17T22:09:14.324354Z` (18 Kasım 01:09:14 İstanbul). Öncesinde 2.035 takipli dosyanın SHA-256 değeri değişmedi. Kaynak farkı, başlangıçtaki kullanıcı değişikliklerini içerir; bu çalışmanın optimizasyon diff'i değildir. [İşaret ve kapsam](performance-2026-11-18/phase0/phase0-complete.json), [kaynak manifesti](performance-2026-11-18/phase0/source-sha256.json).

Ana oturum `c5-perf-20261117T220400Z-6ece89b2`, ROS domain 211, API/UI portları 21721/21722. Gerçek standart reset/AMCL/Nav2/TF kapıları geçildi. Ayrı Metal renderer kullanan Chrome açıldı; mevcut kullanıcı Chrome oturumu değiştirilmedi. Nav2 gerçekten robot başına ayrı süreçlerde çalışıyordu; composition kapalıydı. Başka worktree veya oturum durdurulmadı.

Bu mevcut C5 launcher harness'i simülasyon/manager/API/observer süreçlerini tek test container'ında, Vite'ı hostta çalıştırır; nihai üç servis dağıtımının performans kabulü değildir.

Aynı katalog görevleri MEDIUM olarak `pick_A1 → packing_1`, `pick_B2 → delivery-01`, `pick_D1 → shipping_2` gönderildi. İlk 15 saniye Chrome ısınmasıdır; görevler bundan sonra gönderildi. 180 saniyelik ana pencerede **en çok iki görev EXECUTING** oldu: beta ve gamma hareket etti, alpha'nın görevi kuyrukta kaldı. Üç robotlu kurulum üç eşzamanlı hareket kanıtı değildir. Bir/iki robotlu yeni config koşusu yapılmadı; bu baseline mevcut üç robotlu konfigürasyonu değiştirmedi.

| Ana pencere metriği | Değişikliksiz sonuç |
|---|---:|
| Gazebo bildirilen RTF ortalama / p50 / p95 / minimum | 0,544 / 0,549 / 0,918 / 0,050 |
| `/clock` uçtan uca sim-s / duvar-s | 0,418 |
| `/clock` alım aralığı p95 / maksimum | 54,9 / 821,1 ms |
| En kötü saat boşluğunda simülasyon ilerlemesi | 0,005 sim-s / 0,821 duvar-s |
| FM asyncio lag p95 / tamamlanmış ölçüm maksimumu | 1,398 / 39,200 s |
| FM olay kuyruğu p95 / maksimum | 1.382 / 1.612 olay |
| SQLite COMMIT p50 / p95 / maksimum | 10,8 / 86,5 / 751,9 ms |
| Snapshot dosya yaşı p50 / p95 / maksimum | 13,77 / 83,70 / 92,16 s |
| Yayınlar arası tamamlanmış aralık p95 / maksimum | 9,63 / 23,57 s |
| API 503 / tüm yoklamalar | 567 / 679 = %83,5 |
| WS ürün aralığı p95 / maksimum | 9,56 / 23,57 s |
| WS heartbeat aralığı p95 / maksimum | 1,32 / 1,75 s |
| Chrome WS aç/kapat | 2 / 1; açılıştaki StrictMode çevrimi, devam eden bağlantı kopması yok |
| Chrome timer lag p95 / maksimum | 12,6 / 46,9 ms |
| Chrome uzun görev | 1 adet, 77 ms |
| Chrome TF STALE olay / toplam gözlenen süre | alpha 2 / 0,555 s; beta 1 / 0,255 s; gamma 0 |
| Gözlenen zararlı temas | 0 |

Alıcı duvar saatine göre 5 s kovalarının en yavaş üç gözlemi aşağıdadır. Süre ilk/son stats mesajı arasındadır; alıcı ilerleme oranı transport/örnekleyici gecikmesini de içerir, yalnız fizik motoru süresi değildir. RTF p95 hızlı ucu gösterdiğinden yavaş kovalar ayrıca tutulur.

| Başlangıç (İstanbul) | Gözlenen süre | Gazebo RTF ortalaması | Alıcı sim-s/duvar-s |
|---|---:|---:|---:|
| 01:07:21 | 4.849 s | 0.378 | 0.256 |
| 01:08:01 | 4.910 s | 0.474 | 0.259 |
| 01:07:46 | 4.884 s | 0.367 | 0.306 |

Son yayın gelmeyen pencere sonu sağdan sansürlüdür: 23,57 s tamamlanmış yayın aralığı, 92,16 s süren son kesintiyi kapsamaz. Event loop ölçer de yalnız yeniden çalıştırıldığında lag yazabilir; 39,2 s üst sınır garantisi değildir. RTF dağılımı Gazebo'nun kendi istatistik mesajlarıdır; `/clock` uçtan uca oranı bridge/DDS/alım etkisini de içerir. Ortalamaları aynı metrik saymayın.

Nav2 sorguları 15 geçerli / 1 rotasız sonuç; toplam çağrı süresi p50 0,397 s, p95/maksimum 2,583 s. Bu süre callback ve event loop beklemesini de içerir; yalnız planner CPU süresi değildir. 2 s timeout değiştirilmedi. AMCL XY hatası aynı kaynak damgasında fiziksel pozla ≤150 ms interpolasyon braketi üzerinden beta p95/maksimum 0,081/0,102 m, gamma 0,099/0,123 m. Hareketsiz alpha için eşli yeni AMCL örneği yoktur; sıfır hata varsayılmadı. Ana pencere sonunda taşıma terminali yoktur.

Odometri, TF ve scan için robot bazlı yayın damgası/alım aralıkları; observer göreli callback gecikmeleri; CPU/RSS/context switch/cgroup bellek ve bütün dağılımlar [makine özetinde](performance-2026-11-18/phase0/summary.json) ve [iç zamanlama özetinde](performance-2026-11-18/phase0/details.json) bulunur. Observer gecikmesi, aynı kaynak damgasını alan bağımsız ROS probe ile mevcut observer'ın log zamanı farkıdır: odometride robot başına p95 0,84–0,88 s, maksimum 1,28–1,32 s. Bu değer callback gövdesinin çalışma süresi veya mutlak DDS yayın→callback gecikmesi değildir.

## Ölçüm yöntemi ve etkisi

Ürün kaynakları değiştirilmeden `/tmp` altındaki ayrı araçlar kullanıldı. Bir süreç Gazebo stats, `/proc`/cgroup ve snapshot dosyasını okudu. ROS probe Clock/Odometry/TF/physical_pose/AMCL/scan alımını kaydetti; komut göndermedi. API 250 ms'de bir yoklandı; bağımsız WS ve Chrome tüketicileri açıldı. Chrome Metal renderer kullandı; SwiftShader zorlanmadı. Ana hareket koşusunda FM yöntemlerinin etrafına süre ölçen bir test wrapper'ı eklendi; aynı SQLite transaction'ı, tek consumer ve gerçek Nav2 çağrıları yürütüldü. Wrapper kodu ürün kodu değildir.

Önceki araç denemesinde iki ölçüm penceresinin kısa bölümü çakıştığından 0,95→0,76 RTF farkı ölçüm maliyeti olarak kullanılmaz. Son ana oturumda pencereler sırayla çalıştırıldı: 25 s yalnız dış örnekleme RTF 0,799; ardından 25 s ROS/API/WS probe ile 0,764, yaklaşık %4,3 fark. Ortalama süreç CPU toplamı 551→573 yüzde-puan; ek ROS probe yaklaşık bir çekirdeğin dörtte birine yaklaşabilir. Bu tek sıra, ısınma/host yükünü ayrıştırmaz. FM wrapper maliyeti de tamamen sıfır varsayılmaz. Daha önce wrapper olmadan alınan 150 s koşuda da snapshot 27,9 s'ye, publisher aralığı 28,2 s'ye çıktı; ardından ek ROS/Chrome probe olmayan 45 s hareket koşusunda yayın aralığı 17,4 s oldu. Dolayısıyla ürün kesintisi yalnız ölçüm aracının eseri değildir; koşular eşdeğer görev ilerlemesi içermez.

Ayrıntılı observer instrumentation denemesi readiness sağlayamadı; bu deneme kabul baseline'ı değildir. Son ana koşuda observer kaynakları değiştirilmedi. Başarısız başlangıçlar, kapanış kusurları ve eksik ölçümler komut ekinde ayrı tutulacaktır. Kısa örnekleme tepe yük/ölçek/dayanıklılık garantisi vermez. Docker VM 8 CPU / 7,75 GiB; ana koşu cgroup belleği en fazla 1,73 GiB. `/proc` ve Docker CPU yüzdeleri kısa VM zaman pencerelerinde tutarsız tepe değerleri gösterebilir; çekirdek kapasitesi garantisi çıkarılmaz.

## Faz 1: öncelik ve beklenen etki

1. **FM event loop adaleti:** Tek consumer'ın dolu `Queue.get()` döngüsü askıya alınmıyor. 39 s lag ve 92 s snapshot kesintisi, tek transaction süresinden çok büyük. Her tam transaction + bellek yayını sonrası asyncio'ya sıra vermek publisher ve ağ geleceklerini çalıştırabilir. Sıra/transaction/Outbox politikası değişmeden sınırlı müdahaledir; işleme kapasitesi veya kuyruk gecikmesini tek başına çözmesi beklenmez.
2. **SQLite throughput:** 20 Hz nonblocking profiler örneklemesinde FM ana iş parçacığının 484 örneğinin 317'si COMMIT'teydi. Doğrudan zamanlama da beklemeyi doğruladı. İlk müdahale sonrası backlog sürerse ayrı değerlendirilir; `synchronous=FULL`, her olayın atomik commit'i ve tek yazarlık korunur.
3. **ROS/simülasyon yükü:** Hareket altında RTF ve kaynak alımı yavaşlıyor. Nav2 composition ayrı deney için anlamlıdır; CPU/RAM/context switch kazanımı tek başına kabul değildir. Gazebo'nun hangi iç sensör/fizik safhasının maliyetli olduğu ayrıştırılmadı.
4. **Chrome/taşıma:** Metal koşusunda heartbeat ve TF yolu ürün snapshot'ından bağımsız sürüyor. Frontend V1–V6 veya STALE eşikleri için yeni değişiklik gerekçesi yok.

Üst LiDAR mevcutta 180 samples / 5 Hz / 10 m / tam yatay FOV, köşe sensörleri 97 / 5 Hz / 10 m; controller zaten 10 Hz, local costmap 3×3 m. Bunları 360 samples / 10 Hz'e çevirmek yükü artırır. Sensör çözünürlüğü/hızı, AMCL parçacığı, costmap, collision ve fizik ayarları maliyet/algılama kanıtı olmadan değiştirilmez.

## Faz 2: ayrı müdahaleler ve ölçülen etki

### 1. Consumer'a işlem sonrası çalışma sırası — tutuldu

`FleetEventLoop._run`, her atomik işlem ve commit sonrası bellek yayınını tamamladıktan sonra `await asyncio.sleep(0)` çağırır. Dolu `Queue.get()` beklemeden döndüğünde diğer asyncio görevlerinin aç kalması önlenir. İkinci consumer, thread'e taşınmış SQLite, olay atlama/birleştirme veya transaction içine yeni await yoktur. Olay sırası, domain sahipliği ve ağ gönderiminin transaction dışında kalması korunur.

Yeni regresyon testi, ilk commit sonrası planlanan bir gözlemcinin 12 olaylık kuyruk tamamen tüketilmeden çalışmasını, transaction dışında olmasını ve kalıcı olay sırasının korunmasını denetler. Eski kodda gözlemci 12/12 olaydan sonra çalıştığı için test kaldı; düzeltmeyle geçti. 180 s canlı koşu `c5-perf-20261117T221747Z-b41e671a`: 1/694 HTTP 503, snapshot yaşı p95 0,530 s, maksimum 1,595 s. RobotStatus gecikmesi sürüyordu; bu düzeltme tek başına üç görevi çalıştırmadı.

Bu koşuda wrapper yoktu; iki wrapper'lı tekrar güncel readiness kapısını geçemedi ve görev gönderilmeden kapatıldı. Önceki wrapper'sız 150 s referansta 436/576 HTTP 503 ve snapshot yaşı p95 20,55 s vardı. Aynı profil/görev kümesi ve iki EXECUTING yükü kullanılsa da ilk referansta ilk görev 503 sonrası daha geç kabul edildi, kısa probe çakışması vardı ve robot/rota ilerlemesi birebir eşleşmiyor. Dolayısıyla bu iki sayı tarafsız bir hızlanma yüzdesi olarak sunulmaz. Mekanizma, deterministik regresyon ve ek probe olmayan hareket penceresinde de süren yayın kesintisiyle desteklenir.

### 2. SQLite WAL + FULL — tutuldu, bütün sistem kabulü değildir

Yalnız journal yöntemi değişti. `synchronous=FULL`, yabancı anahtarlar, tek consumer/yazar ve her olayın aynı atomik transaction'ı korunur. WAL açılamazsa başlangıç açık hata üretir; bellek testlerinin doğal `memory` modu ayrı kalır. Constructor, şema veya teslim politikası üzerinden otomatik restart/replay açmaz.

Salt okunur bir bağlantı eski snapshot'ı tutarken yeni atamanın görev/Outbox ile birlikte commit olmasını ve eski okuyucunun tek tutarlı nesli görmesini sınayan test eski modda `database is locked` ile kaldı, WAL ile geçti. Mevcut rollback, gerçek epoch, rezervasyon, retry ve process-crash testleri ilgili seçkide geçti. Dört canlı koşunun son SQLite backup'ında `integrity_check=ok` ve boş `foreign_key_check` sonucu alındı. Bu, güç kesintisi testi değildir. [DB kontrolü](performance-2026-11-18/database-checks.json).

`c5-perf-20261117T222323Z-0f9e7fb0` koşusunda gerçek üçlü hareket ve üç taşımanın tamamlanması görüldü. İlk 180 s: 0/704 HTTP 503, snapshot yaşı p95 0,438 s; COMMIT p95 26,8 ms; FM lag p95 0,173 s. Faz 0'da bunlar sırasıyla %83,5, 83,70 s, 86,5 ms ve 1,398 s idi. **Yükler 2 ve 3 EXECUTING olduğu için doğrudan yüzdesel kapasite/hızlanma sonucu çıkarılmaz.**

COMMIT tablosu boş Outbox claim transaction'larını da içerir. Olay türüne göre ayrılmış ROBOT_STATUS COMMIT p95 değerleri Faz 0'da 86,6 ms, WAL koşusunda 29,0 ms'dir; bütün türler `sqlite_commit_by_event_s` alanında tutulur. İş yükü ve event karışımı farkı yüzünden bu da genel kapasite garantisi değildir.

WAL dosyaları aynı yerel depolamada tutulur. Yedekler bütün süreçler kapandıktan sonra SQLite backup API ile alındı; canlı ana DB dosyasını tek başına kopyalama yapılmadı. Image SQLite sürümü 3.37.2. [SQLite'ın WAL belgesi](https://sqlite.org/wal.html), çoklu yazıcı/checkpointer yarışını bu sürümler için açıklar. Burada mevcut tek-yazıcı sözleşmesi geçerlidir: observer `mode=ro`, başka writer/checkpointer yok, backup manager kapandıktan sonradır. Bu koşullar dışında WAL güvenilirliği bu testle doğrulanmış değildir. [FULL sözleşmesi](https://sqlite.org/pragma.html#pragma_synchronous) ve [tasarım ayrıntısı](../../design/c3-2-sqlite-outbox.md).

### 3. Nav2 composition — ölçüldü, geri alındı

Gerçek ayrı süreçler doğrulandıktan sonra yalnız `use_composition:=True` denendi. Humble'ın `component_container_isolated` yürütücüsü robot başına bir namespaced container içinde 11 component çalıştırdı; 33 Nav2 süreçten 3 component sürecine geçildi. Üç robotun namespace, map/odom/base/scan parametreleri, `use_sim_time`, 10 Hz controller, lifecycle ve NavigateToPose action server readiness'i okundu. [Audit](performance-2026-11-18/composition/composition-audit.json). Dünya SDF'si, harita ve üç üretilmiş Nav2 YAML'si kontrolle byte eşitti. [Invariantlar](performance-2026-11-18/composition/composition-invariants.json).

Tam 180 s pencerelerde görev ilerlemesi farklıdır. Bu nedenle ayrıca ilk üç EXECUTING sonrasındaki **20 sim-s** eşleştirildi; iki pencerede de üç taşıma aktifti. Kontrol 37,97 duvar-s, aday 33,37 duvar-s sürdü. Tek eşleştirme istatistiksel/ölçek garantisi değildir.

| Eşleştirilmiş 20 sim-s | WAL kontrolü | Composition adayı |
|---|---:|---:|
| Nav2 toplam CPU ortalaması | %272,6 | %145,7 |
| Nav2 toplam RSS ortalaması | 991,7 MiB | 309,7 MiB |
| Nav2 thread context-switch/s ortalaması | 41168 | 19405 |
| cgroup bellek ortalaması | 1,64 GiB | 1,35 GiB |
| Gazebo bildirilen RTF ortalaması | 0,650 | 0,710 |
| /clock sim-s/duvar-s | 0,527 | 0,599 |
| AMCL XY p95 alpha/beta/gamma (m) | 0,045 / 0,047 / 0,081 | 0,054 / 0,044 / 0,059 |

RSS paylaşılan sayfaları birden fazla süreçte sayabilir; cgroup bellek file cache de içerir. CPU/context-switch kısa VM pencerelerinde yaklaşık ölçümlerdir. [Eşleştirilmiş veri](performance-2026-11-18/matched-three-executing.json).

CPU dışında `/clock`, TF güncelliği ve yayın gecikmesi de iyileşti. Bununla birlikte uzatılmış koşuda yine park dönüşü teması oluştu. **Güvenli tam senaryo kabulü olmadığı için composition kaynak değişikliği geri alındı; varsayılan yine False.** Denenmiş [tek değişiklikli patch](performance-2026-11-18/composition/enable-composition.patch) yalnız deney kanıtıdır, kabul edilmiş hafif ürün profili değildir. LiDAR, costmap, controller, AMCL, collision, fizik ve Docker limitleri değiştirilmedi. SDF'de 31 box, 12 cylinder ve 6 sphere collision zaten basit primitiftir. Üst LiDAR yatay resolution çarpanı 1 ve yaklaşık 360° FOV'dur. [Sensör/geometri envanteri](performance-2026-11-18/sensor-baseline.json).

## Faz 3: karşılaştırma ve kabul sınırı

Aşağıdaki ana pencereler 180 s'dir. Süreler gözlenen dağılımdır; sağdan sansürlenen son kesintiler üst sınır değildir. Sütunların yükleri açıkça farklıdır. Yield sütunundaki publisher ölçümü 100 ms dosya yoklamasıdır; wrapper'lı sütunlarda başarılı `_write` tamamlanma zamanları kullanılır. DOM STALE süreleri yaklaşık 250 ms örnekleme çözünürlüğündedir.

| Metrik | Faz 0, 2 EXECUTING | Yield, 2 EXECUTING | Yield + WAL, 3 EXECUTING | Composition adayı, geri alındı |
|---|---:|---:|---:|---:|
| En çok EXECUTING | 2 | 2 | 3 | 3 |
| RTF ortalama / p50 / p95 | 0,544 / 0,549 / 0,918 | 0,641 / 0,662 / 0,979 | 0,660 / 0,687 / 0,986 | 0,750 / 0,801 / 1,001 |
| /clock sim-s/duvar-s | 0,418 | 0,522 | 0,546 | 0,645 |
| /clock alım aralığı p95 / max (s) | 0,055 / 0,821 | 0,035 / 0,790 | 0,035 / 0,777 | 0,023 / 0,724 |
| Snapshot yaşı p95 / max (s) | 83,700 / 92,157 | 0,530 / 1,595 | 0,438 / 1,135 | 0,331 / 0,920 |
| API HTTP 503 / yoklama | 567/679 (%83,51) | 1/694 (%0,14) | 0/704 (%0,00) | 0/710 (%0,00) |
| FM event loop lag p95 / max (s) | 1,398 / 39,200 | ölçülmedi | 0,173 / 0,996 | 0,110 / 0,779 |
| SQLite COMMIT p95 / max (ms) | 86,5 / 751,9 | ölçülmedi | 26,8 / 437,2 | 20,7 / 424,5 |
| FM kuyruk p95 / max (olay) | 1382 / 1612 | ölçülmedi | 56 / 106 | 17 / 45 |
| Gerçek publisher aralığı p95 / max (s) | 9,594 / 23,543 | 0,797 / 2,180 (dosya yoklaması) | 0,581 / 1,252 | 0,481 / 1,148 |
| WS ürün aralığı p95 / max (s) | 9,558 / 23,569 | 0,784 / 1,616 | 0,626 / 1,238 | 0,518 / 1,247 |
| Chrome timer lag p95 / max (ms) | 12,6 / 46,9 | 4,8 / 903,1 | 14,6 / 121,0 | 8,4 / 129,4 |
| Chrome TF STALE olay / gözlenen toplam süre | alpha: 2 / 0,555 s; beta: 1 / 0,255 s; gamma: 0 / 0,000 s | alpha: 2 / 0,507 s; beta: 2 / 0,760 s; gamma: 2 / 0,760 s | alpha: 0 / 0,000 s; beta: 1 / 0,795 s; gamma: 0 / 0,000 s | alpha: 0 / 0,000 s; beta: 0 / 0,000 s; gamma: 0 / 0,000 s |
| cgroup bellek örneklenmiş max (GiB) | 1,73 | 1,70 | 1,70 | 1,41 |

WS taşıması ana pencerelerde kararlı kaldı: Chrome'daki 2 açılış/1 kapanış ilk StrictMode çevrimidir, sonrasında yeniden bağlantı fırtınası yoktur. Contact guard sonrası API/WS kapanmaları steady-state yayın aralığına karıştırılmaz. Uzatılmış probe'lardaki `137` çıkışları hedef container kapanırken öldürülen ölçüm süreçleridir; Docker `OOMKilled=false` gösterir.

Kontrol koşusunda üç hareketli odometri kaynağının damgaları ≤100 ms aralıkla eşleşen en uzun örnek dizisi 39,235 sim-s; bu aralıkta fiziksel yer değiştirmeler alpha 8,78 m, beta 6,22 m, gamma 9,41 m'dir. Bu, ayrı Gazebo fiziksel pozlarıyla desteklenen gerçek üçlü harekettir; kesintisiz zaman garantisi değildir. Üç taşıma sonucu iki varyantta da gerçek action UUID ve `completed_epoch=1` ile COMPLETED oldu. Kontrol completion stamp'leri beta 135,100; gamma 213,110; alpha 224,345 sim-s; composition beta 116,235; gamma 191,910; alpha 214,480 sim-s'dir. Başlangıç/ilerleme farkları nedeniyle bunlar doğrudan hızlanma yüzdesine çevrilmez.

AMCL değerlendirmesi gerçek damgayı fiziksel pozla eşler, en fazla 150 ms interpolasyon braketi kullanır. Ana WAL penceresinde XY maksimumları alpha/beta/gamma 0,213/0,093/0,082 m; composition'da 0,163/0,115/0,176 m. Tam pencerelerin rota/ilerlemesi farklıdır; tek örnek grubu lokalizasyon kalibrasyonu veya kötüleşmeme garantisi değildir. Completion stamp'inde eşli fiziksel dropoff hatası ölçülebilen kontrol görevlerinde gamma 0,197 m, alpha 0,252 m bulundu; beta için bu eşleşme kurulamadı. Eksik ölçüm sıfır yapılmadı. İlgili bütün XY/yaw dağılımları makine özetlerindedir.

### Kalan kabul engeli: görev sonrası park dönüşü teması

**FAIL — tam C5/hafif profil kabulü yok.** İki varyantta da üç taşıma tamamlandıktan sonra alpha park_3'e dönerken park_1'de IDLE duran beta ile temas oluştu:

| Koşu | İlk contact sim-s | İlk eşleşme | Sonuç |
|---|---:|---|---|
| Yield + WAL, ayrı Nav2 süreçleri | 265,670 | alpha body ↔ beta body | contact guard tetiklendi, koşu kapandı |
| Composition adayı | 249,115 | alpha ön köşe sensör kasası ↔ beta body; ardından body teması | contact guard tetiklendi, koşu kapandı |

Temas öncesi kalıcı kayıtlar park_1=beta OCCUPIED, park_2=gamma RESERVED, park_3=alpha RESERVED gösteriyor; aynı park kaynağının çift sahipliği görülmedi. Alpha RobotStatus `state=5`, epoch 2, station görevi; beta `state=1`, yüksüz ve taşıma kimliği boştu. Bu, güvenli fiziksel park yaklaşması kanıtı değildir. Contact guard atlanmadı, WORLD/TF/odometri üretilerek yer değiştirme yapılmadı. Guard tetiklenmesi ani fiziksel duruş garantisi olarak sunulmaz.

Temasın kök nedeni; peer gözlemi, yerel rota/kontrol, lokalizasyon ve fiziksel park yaklaşımı arasında ayrıştırılmadı. Değişikliksiz baseline'da üçlü tam görev/park koşusu kurulamadığı için yeni performans değişikliklerinden bağımsızlığı da kanıtlanmış değildir. Trafik/park/scheduler politikasını bu görevde değiştirmek veya eşiklerle hatayı gizlemek yapılmadı. Bu açık sorun çözülmeden güvenli üç robot demosu ilan edilmemelidir. Mevcut ayrı-süreç profilinde RTF hâlâ yaklaşık 0,66 ve gerçek kısa TF STALE olayları vardır.

## Doğrulama ve teslim durumu

- **DOĞRULANDI:** Değişikliksiz Faz 0, consumer fairness regresyonu, WAL okuyucu/yazar atomikliği; ilgili host Outbox/rota 122 geçti, dashboard 8 geçti. Native ilgili seçki 144 geçti / 0 skip. Tam host: 570 geçti / 2 kaldı / 23 skip; skip başarı değildir.
- Native ilk seçki 139 geçti / 5 kaldı: backend loglarının pytest root capture'a yayılmaması dört log kontrolünü ve log bekleyen bir rollback kontrolünü düşürdü. Otomatik eklenti yüklemesi kapalı, yalnız unit-test container'ındaki tekrar 144 geçti. Ürün logging veya güvenlik ayarı değiştirilmedi; ilk hata logu korunur.
- Tam hosttaki iki hata: tarihsel B6B.4 dosya-hash testi ve eski 5 contact sensor beklentisi. Başlangıç config hash'i zaten tarihsel manifestten farklıydı; Faz 0 SDF'sinde de robot başına 9 contact sensor vardı. [Başlangıç kanıtı](performance-2026-11-18/preexisting-tests-evidence.json). Tarihsel manifest veya beklenti bu görevde yeniden yazılmadı.
- **DOĞRULANDI, sınırlı kapsam:** Üç eşzamanlı hareket ve üç gerçek taşıma terminali. **FAIL:** görev sonrası güvenli park dönüşü. **HENÜZ TEST EDİLMEDİ:** eşdeğer üç-hareketli değişikliksiz tam senaryo, ölçüm yükü olmayan üçlü park karşılaştırması, power-loss, uzun dayanıklılık ve 3+ ölçek.
- **Tutulan ürün değişiklikleri:** commit sonrası asyncio yield ve WAL + FULL. **Geri alınan:** Nav2 composition. Kabul edilmiş yeni hafif sensör/fizik/Nav2 parametre profili yoktur; adayın ölçümü ve patch'i korunur.
- Önceki frontend TF STALE düzeltmesi, kullanıcı launcher değişiklikleri, V1–V6, config/IDL/Compose ve güvenlik eşikleri korundu. [SHA koruma kontrolü](performance-2026-11-18/preservation.json). Commit/push yapılmadı; çalışma ağacı inceleme içindir.

[Komutlar, oturumlar ve ham kanıt dizini](performance-commands-2026-11-18.md).
