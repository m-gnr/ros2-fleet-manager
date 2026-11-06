# Fleet Visualizer Aşama 3 doğrulama raporu

6 Kasım 2026. **DOĞRULANDI** — İki gerçek robotlu Aşama 3 kabulü. [Teknik tasarım](../../../design/fleet-visualizer-stage-3.md) · [Komut eki](commands.md) · [Aşama 2 tarihsel kabulü](../stage-2/report.md).

## Git ve kapsam

Başlangıçta ana worktree `main` ve yerel `origin/main` aynı C4.5 commit'indeydi (`32e23fce62026a1d50aa2f04e85c8c38a6ee5d76`). Aşama 1 ayrı worktree'de `4503c25b7bc10cc91ee97ac230e1c70e2851ecb8` olarak duruyordu. Aşama 2 kabul raporu ve kodu `015865403d5bf3cae62647fbc149c5bbcee620a5` commit'indeydi. `feat/fleet-visualizer-multi-robot`, Aşama 2'nin bu commit'inden `ros2-fleet-manager-multi-robot` worktree'sine açıldı.

Aşama 3 değişikliği Visualizer, test probları ve ilgili belgelerdedir. C4.5 Compose katmanları ve ROS launch dosyaları kendi imajları, config girdileri ve ayrı DDS domain'leriyle kullanıldı. Ana worktree'deki değiştirilmiş ve izlenmeyen dosyalar yerinde korundu.

## Canlı iki robot ve poz doğruluğu

**DOĞRULANDI.** C4.5 enerji profilinde iki TurtleBot3 Burger aynı Gazebo Fortress dünyasında çalıştı. Humble/CycloneDDS grafiğinde namespaced TF zincirleri ayrı ayrı çözüldü. Chrome 156.0.8078.80, iki akışı tek WebSocket ile alıp aynı WebGL sahnesine çizdi. İki etiket, model tıklaması, liste seçimi, takip hedefinin yumuşak değişimi ve iki robotun kadrajı gözlendi. Chrome probunda JavaScript veya WebGL hatası kaydedilmedi.

| Robot | Canlı TF zinciri | Aynı damgalı ROS–WS–3D eşleşmesi | En büyük ROS–WS konum / yaw farkı |
| --- | --- | ---: | ---: |
| `robot_1` | `map → robot_1/odom → robot_1/base_link` | 18 | 0 m / 0 rad |
| `robot_2` | `map → robot_2/odom → robot_2/base_link` | 52 | 0 m / 6,7 × 10⁻¹⁶ rad |

Bağımsız ROS referansı, test ortamındaki birleşik TF akışını tf2 ile dinledi. Visualizer ise namespaced akışları ayrı buffer'larda çözdü. Örnekler robot, TF damgası, WebSocket oturumu ve epoch ile eşlendi. Eşleşen WebGL kökleri için `(x, 0, -y)` konum farkı 0 m, model ön vektörünün en büyük bileşke farkı 2,8 × 10⁻¹⁶ oldu. Robot başına sırasıyla 331 ve 1.014 ara kare, kendi iki ölçümünün doğrusal konum ve en kısa yaw aralığına karşı denetlendi. [Ölçümler](measurements/compare.json) · [Chrome sonuçları](measurements/result.json).

Şarj profilinde iki robot da ayrı zamanlarda hareket etti. Eşleşen ölçümlerde başlangıca göre en büyük yer değiştirme `robot_1` için 2,739 m, `robot_2` için 0,252 m oldu. Sırasıyla 150 ve 164 aynı damgalı örnekte ROS–WS konum farkı 0 m ve yaw farkı en fazla 4,5 × 10⁻¹⁶ rad olarak ölçüldü. İki robotun 3D kök konum farkı 0 m oldu. [Şarj profili ölçümü](measurements/charging-compare.json).

## Kesinti ve Fleet Manager sürekliliği

Test sarmalayıcısı sadece köprünün `robot_1` TF girişini kesti. `robot_1` STALE olduğunda WebSocket CONNECTED, `robot_2` LIVE kaldı. `robot_1` kökü `(-2, 0, 0,5)`, takip hedefi `(-2, 0,12, 0,5)` ve ölçümü `3,185000000 sn` olarak sabit kaldı. Aynı aralıkta `robot_2` kökü yaklaşık 0,236 m yer değiştirdi ve yaw'ı değişti. Kapı açılınca iki akışın da yeni ölçümü kabul edildi. [Kesinti ölçümleri](measurements/isolated-cut.json).

Köprü durdurulunca Chrome iki robot için son pozları sakladı. Backend, köprü 18:08:05,771 ile 18:08:11,235 TSİ arasında kapalıyken 18:08:09,099'da `ALL_C4_5_ENERGY_TESTS_PASSED` kaydını üretti ve 0 ile çıktı. Yeniden bağlantıda iki robot kendi yeni ölçümleriyle LIVE oldu. Çalışan ROS grafiğinde Visualizer'ın yalnız `/clock`, `/robot_1/tf` ve `/robot_2/tf` abonelikleri vardı. Enerji SQLite bütünlük denetimi `ok`, foreign-key çıktısı boştu. Enerji profilindeki son simulation, backend ve köprü çıkış kodları 0, OOM alanları `false` oldu. Simulation ve köprü kendi temiz kapanış işaretlerini üretti. [ROS düğüm kaydı](measurements/ros-node-final.txt) · [Enerji kabul kaydı](measurements/energy-acceptance.txt).

Şarj profili park ve şarj akışının ardından HIGH preemption duruşunu yeniden doğruladı. Nav2 terminal iptalinden sonra odometri 0,0 m/s ve 0,0 rad/s gösterdi. Test koşusu 13 bağımsız örnek, eski terminal epoch 3'ün engellendiği kayıt ve LOW görevinin epoch 5'te yeniden başladığı kayıt üretti. `ALL_C4_5_CHARGING_TESTS_PASSED`, SQLite `ok`, boş foreign-key çıktısı ve üç konteynerde çıkış 0 gözlendi. [Şarj kabul kaydı](measurements/charging-acceptance.txt).

## Performans

Chrome, 1280 × 850, Standart kalite, DPR 1 ve açık ölçüm izi. Aşama 3 takip penceresi hareketli enerji koşusunda 4,00 sn, filo kadrajı penceresi iki robot canlı ve ikisi de kadrajdayken 5,01 sn sürdü. Kadraj ölçümünde fiziksel görev bitmişti. Aşama 2 C4.5 takip ölçümü 17,26 sn'lik tarihsel referanstır.

| Ölçüm | Aşama 2 takip | Aşama 3 takip | Aşama 3 filo kadrajı |
| --- | ---: | ---: | ---: |
| Ortalama FPS | 59,86 | 59,22 | 59,32 |
| p95 kare aralığı (ms) | 18,20 | 17,50 | 17,60 |
| En çok draw call / üçgen | 34 / 3.840 | 34 / 3.840 | 53 / 4.656 |
| En çok geometri / texture | 34 / 2 | 53 / 3 | 53 / 3 |
| Pencere sonu JS heap (MiB) | 11,99 | 9,42 | 14,38 |
| Chrome CPU / RSS | %26,66 / 961,47 MiB | %29,67 / 861,91 MiB | %40,54 / 884,88 MiB |
| WebSocket poz/sn, robot 1 / 2 | — | 17,60 / 19,53 | 19,48 / 19,68 |

Takip koşusunda diğer robot kadraj dışındaydı. İki model birlikte kadraja girdiğinde 19 draw call ve 816 üçgen daha gözlendi. Kısa pencereler, farklı hareket yükleri ve kamera görüşü ölçümlerin karşılaştırma sınırıdır. Chrome CPU bir tam çekirdek için %100 kabul eden süreç CPU farkıdır. RSS süreçlerin toplamıdır. Filo kadrajı sırasında Docker köprüsünün başlangıç örneği dışındaki dokuz örneği %15,12 CPU ve 50,57 MiB RAM medyanı verdi. Örnek aralıkları %12,12–19,01 ve 50,26–50,58 MiB idi. [Takip ölçümü](measurements/performance-follow.json) · [Filo ölçümü](measurements/performance-fit.json) · [Docker örnekleri](measurements/fit-bridge-stats.txt).

| Gecikme p50 / p95 | `robot_1` | `robot_2` |
| --- | ---: | ---: |
| TF alımı → köprü WS gönderim tamamlanması | 22,34 / 38,23 ms | 17,82 / 35,82 ms |
| Tarayıcı WS alımı → tam kök pozunun çizildiği kare | 57,85 / 68,10 ms | 55,45 / 61,20 ms |

İkinci ölçüm 45 ms'ye kadar ara çizimi ve kare bekleme süresini içerir. Köprü ve tarayıcı ayrı monotonik saatler kullanır. Tek yön ağ gecikmesi ayrı ölçülmedi.

## Regresyon ve yeniden koşular

| Kapsam | Yeni sonuç |
| --- | --- |
| Host ürün Python ve Executor | 409 geçti, 28 ROS bağımlı test atlandı |
| Tam Humble/CycloneDDS ürün ve Executor | Son izole koşu 457 geçti |
| C2.3 ve C3.3.3 container config testleri | 3 + 3 geçti |
| Visualizer Python | Host 15 geçti, ROS modülü atlandı. Humble imajında 19 geçti |
| Visualizer frontend | 16 geçti, üretim derlemesi geçti |
| Chrome fixture | Serbest, takip, üstten, sıfırlama, dar ekran, kalite, epoch ve yeniden bağlantı geçti |
| C3.3.3 canlı | T01–T10, 10/10 geçti ve iki konteyner 0 ile kapandı. [Kabul kaydı](measurements/c333-acceptance.txt) |
| C4.5 enerji | Canlı kabul geçti, köprü kapalıyken teslimat ve SQLite doğrulandı |
| C4.5 şarj | Canlı kabul, iki robotun ayrı hareketi ve güvenli preemption geçti |

İlk Chrome denemesi backend'in soğuk derlemesi sırasında 90 sn'lik hareket bekleme penceresini aştı. İkinci denemede Nav2 rota sorguları süre aşımına uğradı ve enerji profili 1 ile çıktı. Bu denemenin simülasyonu 25 sn'lik Docker durdurma süresi sonunda 137 ile sonlandı. Geçen koşu temiz simülasyon, boş SQLite kanıt dizini ve önceden derlenmiş aynı imajla tekrarlandı. Son temiz kapanışta 90 sn'lik Docker süresi verildi.

İlk tam ROS koşusunda Executor sıra testi 456 geçen testin yanında bir kez kaldı. Ardından aynı Executor testi tek başına geçti. İlk izole tam tekrarda iki C4.2 DDS keşif testi kaldı. Son izole tam tekrarın 457 testi geçti. Humble/Python 3.10 köprü testindeki zaman aşımı sınıfı `asyncio.TimeoutError` ile düzeltildi. Fixture testinde düzenli durum paketi eklenerek tarayıcıya canlı köprünün kalp atışı davranışı sağlandı.

Ayrı C2.3, C4.1–C4.4 ve C3.3.3 HIGH-E2E canlı profilleri yeniden çalıştırılmadı. Canlı HIGH duruş kanıtı C4.5 şarj profilinden alındı. Üç ve üzeri robotla canlı yük, gerçek Gazebo saat geri sarımı ve başka TF adlandırma düzenleri **HENÜZ TEST EDİLMEDİ**. Geri sarım, eski paket, robot başına epoch ve `NO_DATA` deterministik testlerde doğrulandı.

## Ekran görüntüleri

- [İki robot aynı canlı kadrajda](screenshots/two-robots-fit.png)
- [robot_1 STALE ve robot_2 LIVE](screenshots/robot-1-stale-robot-2-live.png)
- [robot_2 seçimi ve takip kamerası](screenshots/robot-2-follow.png)
- [Şarj profili sırasında iki ayrı hareket sonrası kadraj](screenshots/charging-both-moved.png)
