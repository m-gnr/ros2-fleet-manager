# Fleet Visualizer Aşama 2 doğrulama raporu

6 Kasım 2026. **DOĞRULANDI** — Tek robotlu yeni depo sahnesi, kamera ve telemetri davranışı gerçek Gazebo ve Chrome/WebGL ile doğrulandı. [Teknik tasarım](../../../design/fleet-visualizer-stage-2.md) · [Komut eki](commands.md) · [Aşama 1 kabulü](../report.md).

## Git ve kapsam

- Başlangıçta `main`, yerel `origin/main` ve sorgulanan uzak `refs/heads/main` aynı C4.5 kabul commit'indeydi, `32e23fce62026a1d50aa2f04e85c8c38a6ee5d76`.
- Ana worktree'de `docs/README.md` değişikliği, izlenmeyen `docs/gereksinim-literatur-ozgunluk-2026-10-27.pdf` ve `docs/reports/` bulundu. `feat/fleet-visualizer-3d-mvp` ayrı kardeş worktree'de `4503c25b7bc10cc91ee97ac230e1c70e2851ecb8` üzerindeydi. İzlenen dosyalar temizdi. Git tarafından yoksayılan Aşama 1 ekran görüntüleri ve ölçümler `fleet-visualizer/artifacts/2026-11-06/` altında yerinde bırakıldı.
- Yeni `feat/fleet-visualizer-visual-upgrade` dalı Aşama 1 commit'inden `ros2-fleet-manager-visual-upgrade` worktree'sinde açıldı. Uzak sorguda iki Visualizer dalının da karşılığı bulunmadı. Push ve merge yapılmadı.

| Dosya grubu | Değişiklik |
| --- | --- |
| `fleet-visualizer/frontend/src/` | Temsili depo ve Burger geometrisi, kamera, telemetri paneli, kalite ayarı, sahneye poz beslemesi, sunum testleri |
| `fleet-visualizer/frontend/` | Lazy 3D yükleme, Three.js parçalaması, özgün yerel favicon, bağımlılık kaydı |
| `fleet-visualizer/frontend/validation/` | Canlı ve fixture Chrome/WebGL kontrolleri, renderer ve yükleme ölçümleri |
| `fleet-visualizer/README.md`, `docs/` | Kullanım, tasarım, doğrulama, komutlar ve seçili canlı ekran görüntüleri |

Aşama 2 farkı frontend ve belgelere sınırlıdır. Köprü, WebSocket sözleşmesi, TF çözümlemesi, koordinat dönüşümü ve C4 ürün kodu Aşama 1 ile aynıdır. C5'in onaylı FastAPI/WebSocket ve React/Vite/Konva yolu ayrı kalır.

## Sahne ve kullanıcı deneyimi

Aşama 1 ekranında yarım metre çizgili boş zemin, silindirik robot ve tek takip düğmesi vardı. Yeni serbest görünümde 1 m grid, raflar, kargolar, işaretli geçişler, depo sınırı ve kalıcı **TEMSİLİ DEPO** etiketi görülür. Yakın takipte Burger'ın katlı şasisi, tekerlekleri, LiDAR ve yön işareti okunur. Üstten görünüm raf ve koridorların yerleşimini gösterir. Gövde yaklaşık 0,138 × 0,178 × 0,192 m boyut referansıyla oluşturulmuş özgün geometridir. Halka, yön işareti ve robot etiketi gövde ölçüsünden bağımsız görsel kılavuzlardır. [ROBOTIS e-Manual](https://emanual.robotis.com/docs/en/platform/turtlebot3/features/)

Orbit, pan, zoom, takip, üstten ve sıfırlama Chrome'da çalıştırıldı. Takip hedefi geçiş tamamlandıktan sonra görünür robot kökünün X/Z konumuyla karşılaştırıldı. Ekran ölçümleri panelde ham ROS x, y, yaw ve simülasyon saati olarak gösterilir. WebSocket durumu ve ROS tazeliği bağımsızdır. Robot `fleet.yaml` içinden seçilir. Uygulama ilk geçerli örneğe kadar modeli gizler ve son doğrulanan pozu kesintide tutar.

## Chrome ve canlı ROS kanıtı

Apple Silicon ARM64, Docker Desktop Engine 29.9.2, ROS 2 Humble, CycloneDDS, Gazebo Fortress headless, DART ve mevcut Nav2/AMCL imajları kullanıldı. Üretim frontend'i Chrome 156.0.8078.80 headless WebGL'de açıldı. 1280 × 850, 1440 × 900 ve 1920 × 1080 canlı viewport'ları denetlendi. Ayrı fixture koşusu 390 × 844 boyutunu, klavye ile takip seçimini, Düşük kaliteyi ve açık `FRAME_ERROR` gösterimini de kapsadı.

Bağımsız ROS gözlemcisi `map → robot_1/odom → robot_1/base_link` ve ikinci koşuda `map → robot_2/odom → robot_2/base_link` TF zincirinin bileşkesini odometri örneği damgasında ölçtü. Chrome probu modelin ROS kökünü ve görsel yön işaretinin dünya vektörünü ayrı okudu. İki ardışık kabul edilmiş örnek arasında çizilen kareler ayrıca WebSocket uç noktalarıyla karşılaştırıldı.

| Yeni koşu | WS pozları | Aynı damgalı ROS–WS–3D | Doğrulanan interpolasyon karesi | En büyük ROS–WS konum / yaw farkı |
| --- | ---: | ---: | ---: | --- |
| C2.3, `robot_1` | 1.529 | 771 | 3.808 | 0 m / 6,66 × 10⁻¹⁶ rad |
| C4.5 enerji, `robot_2` | 374 | 41 | 1.078 | 0 m / 0 rad |
| C2.3 son build, `robot_1` | 1.658 | 68 | 4.896 | 0 m / 3,47 × 10⁻¹⁸ rad |
| C4.5 enerji son build, `robot_2` | 370 | 273 | 829 | 0 m / 6,66 × 10⁻¹⁶ rad |

WS → 3D kök konumu farkı dört koşuda da **0 m**. Yön işaretinin birim ön vektöründeki en büyük X/Z farkı 4,90 × 10⁻¹⁶. Aşama 1'de aynı damga örnekleri C2.3'te 952, C4.5'te 29'du. Tam poz karesi bir sonraki paket gelmeden 45 ms interpolasyonun bitmesini gerektirir. Bu yüzden paketlerin kare döngüsüne göre geliş anı aynı damgada yakalanan örnek sayısını etkiledi. Ara kareler de iki WebSocket uç noktası ve en kısa yaw yönüyle ayrı ayrı doğrulandı.

C2.3 son build örneğinde `20,604000000 sn` damgasındaki ROS ve WebSocket pozu x = 0,331090 m, y = −0,225587 m, yaw = 1,656367 rad idi. Three.js kökü X = 0,331090 m, Z = 0,225587 m ve işaretin ön vektörü X/Z = −0,085467 / −0,996341 olarak ölçüldü. Aynı damga kümesinde ilk pozdan en büyük hareket 2,347 m idi.

TF yardımcısı geçici durunca Chrome `CONNECTED / STALE` gösterdi. Robot ve takip hedefi 65,858000000 sn pozunda kaldı. Yardımcı çalışınca 84,456000000 sn ölçümü geldi. Köprü durunca `DISCONNECTED / STALE` gösterildi, 101,354000000 sn pozu ve takip hedefi korundu. Köprü yeni süreç kimliğiyle açılınca 103,666000000 sn pozu uygulandı. Canlı grafikte köprü yalnız `/clock` ve seçilen robotun `/tf` aboneliklerini açtı. Publisher, servis ve action listeleri boştu.

İlk Chrome denemesinde favicon isteği 404 döndü. Yerel SVG favicon eklendi. Sonraki prob denemesinde WebSocket paketleri karelerden önce sabitlendiği için sondaki 24 ara kare için paket uçları eksik kaldı. Prob, iki kare dizisini aynı tarayıcı anlık görüntüsünden aldıktan sonra paket karşılaştırmasını yapacak şekilde düzeltildi. Tablo başarılı koşuları ve Düşük kalite düzeltmesinden sonraki son build tekrarlarını içerir. Dört kabul koşusunda kritik JavaScript ve WebGL hatası kaydedilmedi.

## Render ve kaynak ölçümleri

| Son build Chrome ölçümü, takip modu, 1280 × 850 | C2.3 canlı | C4.5 enerji canlı |
| --- | ---: | ---: |
| Pencere / render sayısı | 11,16 sn / 670 | 17,26 sn / 1.033 |
| Ortalama FPS | 60,02 | 59,86 |
| p95 kare aralığı | 18,20 ms | 18,20 ms |
| En çok draw call / üçgen | 34 / 3.840 | 34 / 3.840 |
| En çok geometri / texture | 34 / 2 | 34 / 2 |
| Pencere sonu JS heap | 12,32 MiB | 11,99 MiB |
| Chrome süreçleri CPU / RSS | %26,60 / 960,50 MiB | %26,66 / 961,47 MiB |

Pencereler takip modu sabitlendikten sonra başladı ve hareket eşiği gözlenince bitti. Başlangıçtaki durağan örnekleri de kapsar. DPR 1, izleme açık ve ekran görüntüsü alımı pencerenin dışındaydı. Kare aralığı Chrome monotonik saatiyle ölçülen ardışık render başlangıçlarıdır. GPU işlem süresi veya GPU belleği bayt cinsinden ölçülemedi. Three.js kaynak sayıları tabloya alındı. CPU, Chrome CDP süreç CPU süresi farkının duvar süresine oranıdır. Bir tam çekirdek %100'e karşılık gelir. RSS, Chrome süreçlerinin toplamıdır ve paylaşılan sayfaları birden fazla kez sayabilir.

| Chrome alımından tam poz karesine | Aşama 1 p50 / p95 | Aşama 2 son build p50 / p95 | Aşama 2 son build örnek |
| --- | ---: | ---: | ---: |
| C2.3 | 46,70 / 49,10 ms | 47,40 / 57,70 ms | 68 |
| C4.5 enerji | 56,70 / 60,50 ms | 47,30 / 50,10 ms | 273 |

Bu ölçüm 45 ms interpolasyon penceresi ve uygun kareyi bekleme süresini kapsar. Başlangıç tarayıcı WebSocket mesaj alımı, bitiş doğru pozun işlendiği WebGL karesinin başlangıcıdır. Aşama 1'de Chrome FPS, heap ve süreç CPU/RSS ayrı ölçülmemişti. C2.3 ve C4.5 için poz gecikmesi yönleri farklı çıktığından genel hızlanma sonucu çıkarılmadı.

| Köprü, Docker, 8 örnek / durum | CPU medyanı (min–maks) | RAM medyanı (min–maks) |
| --- | ---: | ---: |
| Aşama 1 tarihsel C2.3, canlı besleme | %5,87 (%5,66–%10,29) | 48,46 MiB (48,23–48,75) |
| Aşama 2 C2.3, canlı besleme | %7,21 (%6,14–%7,76) | 49,03 MiB (48,96–49,29) |
| Aşama 2 C2.3, TF duraklatıldı | %5,83 (%5,12–%6,78) | 49,27 MiB (49,14–49,60) |

Docker örnekleri C2.3 görevleri bitmişken, simülasyon çalışırken ve bir Chrome istemcisi bağlıyken alındı. 64,25 sn'lik en uzun kesintisiz dizide 1.286 gönderim ve ortalama 20,00 poz/sn gözlendi. TF kesintisinde WebSocket durum kalp atışları sürdü. ROS damgasından gönderime p95 yaş C2.3'te 33,00 ms, C4.5'te 35,00 ms (simülasyon saati). Köprü TF alımı → WebSocket gönderiminin tamamlanması p95 sırasıyla 30,30 ve 33,24 ms (köprü monotonik saati). Tarayıcıya tek yön ağ gecikmesi ayrı ölçülmedi. Sonuçlar kısa, ardışık örnek pencereleri ve farklı çalışma yükleriyle sınırlı.

DPR 2 olan Chrome fixture bağlamında kalite değişimi ölçüldü. Standart 1,5×, 34 draw call, 34 geometri ve 2 texture kullandı. Düşük 1×, 32 draw call, 32 geometri ve 1 texture kullandı. İlk denemede DPR hemen güncellendi ve gölge kaldırma işlemi durağan sahnede yeni kare istemedi. Kalite ayarı değişince sahnenin yeniden render edilmesi sağlandı. Ölçüm son build ile tekrarlandı.

## Paket ve ilk yükleme

Aşama 1 build'i aynı Node.js 22.15.0, npm 10.9.2 ve Vite 7.3.7 ile tekrar alındı. Aşama 2'de panel önce açılır. 3D modülü, Three.js çekirdeği ve WebGL renderer chunk'ları asenkron yüklenir. Üretim build'i varsayılan 500 kB chunk uyarısını vermedi.

| JavaScript | Aşama 1 | Aşama 2 |
| --- | ---: | ---: |
| İlk giriş dosyası | 1.093,78 kB / 308,11 kB gzip | 205,10 kB / 65,27 kB gzip |
| En büyük chunk | 1.093,78 kB | 374,83 kB |
| Tam 3D yükleme toplamı | 1.093,78 kB / 308,11 kB gzip | 1.111,02 kB / 314,47 kB gzip |

İlk JavaScript giriş dosyası %81,2 küçüldü. 3D sahne dahil toplam JavaScript %1,6 büyüdü. Gzip toplamı, her chunk için Vite'ın raporladığı değerin toplamıdır.

Soğuk Chrome bağlamında aynı fixture pozu ve yerel üretim sunucusuyla üçer yükleme ölçüldü. İlk içerik boyaması medyanı Aşama 1'de 6,12 sn (6,12–9,13), Aşama 2'de 5,69 sn (5,13–11,09). İlk tam poz karesi medyanı sırasıyla 6,18 sn (6,18–9,19) ve 5,80 sn (5,23–11,20). JavaScript kaynak isteği 1'den 4'e çıktı. Chrome Navigation ve Performance API'nin tarayıcı saati kullanıldı. Üç örnek ve geniş süre aralığı nedeniyle bu ölçüm ilk yükleme hızındaki farkı genellemek için yetersizdir.

## Regresyon ve sınırlar

| Kapsam | Bu çalışmadaki sonuç |
| --- | --- |
| C1 filo yapılandırması | Geçti, iki robot |
| Frontend TypeScript/Vite, Vitest, npm audit | Build başarılı, 11/11 test geçti, npm denetiminde açık bildirimi yok |
| Chrome/WebGL fixture | Geçti, 4 boyut, 2 bağlantı, NO_DATA, FRAME_ERROR, epoch ve Düşük kalite |
| Visualizer Python, host | 10 geçti, 1 ROS modülü atlandı |
| Visualizer Python, Humble | 13 geçti, atlama yok |
| Depo host Python + Executor | 409 geçti, 28 ROS testi atlandı |
| Depo Humble/CycloneDDS + Executor | 457 geçti, atlama yok |
| Canlı C2.3 | 7/7, Nav2 duruş/preemption, gerçek hareket ve Chrome |
| Canlı C3.3.3 | T01–T10, 10/10, temiz kapanış |
| Canlı C4.5 enerji | Geçti, `robot_2` Chrome doğrulaması ve kapatma sonrası teslimat |
| Canlı C4.5 şarj | Geçti, fiziksel dock devri, terminal Nav2 duruş kanıtı ve LOW görevinin epoch 3'ten 5'e geçerek sürmesi |

C4.5 enerji son build koşusunda Fleet Manager, köprünün temiz kapanışından 3,33 sn sonra teslimat kabulünü yazdı. Süre Docker UTC log damgalarından hesaplandı. C2.3, C3.3.3 ve iki C4.5 koşusunun konteynerleri 0 ile çıktı, OOM kaydı yoktu. Simülasyon ve çalışan köprüler temiz kapanış işaretlerini yazdı.

C4.1–C4.4 için ayrı canlı Compose koşuları tekrarlanmadı. Enerji tüketimi, oturum ve epoch, Outbox transaction geri alma ve test SQLite bütünlüğü Humble regresyonunda kapsandı. C4.5'in iki profili ve C3.3.3 gerçek Nav2/şarj/preemption yolları için seçildi. Visualizer sürecinin erişimi WebSocket telemetrisi ve salt okunur filo yapılandırmasıyla sınırlıydı.

Sahne yerleşimi temsili, tek robotla sınırlı ve fiziksel navigasyondan ayrıdır. Yazılım bu koşularda iki robotu farklı oturumlarda seçti. Chrome ve Docker ölçümleri kısa yerel örnek pencereleridir. Harici ekran kartı, uzun süreli GPU bellek testi veya daha yüksek yük için performans garantisi vermez.

## Ekran görüntüleri

| Canlı ekran | Dosya |
| --- | --- |
| Serbest, 1280 × 850 | [PNG](screenshots/serbest-1280x850.png) |
| Robot hareket ederken takip, 1280 × 850 | [PNG](screenshots/takip-1280x850.png) |
| Üstten, 1440 × 900 | [PNG](screenshots/ustten-1440x900.png) |
| Sıfırlama sonrası, 1920 × 1080 | [PNG](screenshots/sifirla-1920x1080.png) |
| Bağlı ve STALE, 1280 × 850 | [PNG](screenshots/stale-1280x850.png) |
| DISCONNECTED, 1280 × 850 | [PNG](screenshots/disconnected-1280x850.png) |

Aşama 2 worktree'sinin `fleet-visualizer/artifacts/stage-2/` dizini ham ROS, WS, renderer, Docker ve Chrome kayıtlarını içerir. `final-build/live-single/` altında canlı yeniden bağlantı, `final-build/live-c45/` altında ikinci robot ve `fixture/` altında FRAME_ERROR ile dar ekran görüntüleri vardır. Aşama 1 karşılaştırma görüntüsü, özgün worktree'de `fleet-visualizer/artifacts/2026-11-06/single-final/initial.png` konumundadır.
