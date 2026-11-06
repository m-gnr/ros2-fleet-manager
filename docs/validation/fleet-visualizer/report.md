# Fleet Visualizer Aşama 1 doğrulama raporu

6 Kasım 2026. **DOĞRULANDI** — Gazebo Fortress'ta hareket eden tek robotun gerçek ROS pozu Chrome'daki 3D modele aktarıldı. Aşağıdaki sayılar bu çalışmada yeniden alınan kanıtlardır. [Başlangıç ve lisans incelemesi](preflight.md), [komut eki](commands.md), [kullanım ve veri sözleşmesi](../../../fleet-visualizer/README.md).

## Git ve teslimat kapsamı

Başlangıçta `main`, yerel `origin/main` ve uzak `main` C4.5 kabul commit'i `32e23fce62026a1d50aa2f04e85c8c38a6ee5d76` üzerindeydi. Kullanıcının doküman değişiklikleri ve izlenmeyen dosyaları ana çalışma ağacında korundu. `feat/fleet-visualizer-3d-mvp` aynı commit'ten ayrı worktree'de açıldı.

| Yol | İçerik |
| --- | --- |
| `fleet-visualizer/bridge/` | Python 3.10 Humble ROS okuyucusu, tazelik/epoch takibi, sınırlandırılmış WebSocket, Docker tarifi ve ayrı birim testleri |
| `fleet-visualizer/frontend/` | React, TypeScript, Vite, R3F, Three.js ve Drei OrbitControls, telemetri doğrulayıcısı, 3D sahne, lockfile ve Chrome kontrolü |
| `fleet-visualizer/validation/` | Bağımsız kök TF örnekleyicisi ve aynı damga üzerinden kanıt birleştirme |
| `fleet-visualizer/README.md`, `docs/validation/fleet-visualizer/`, `docs/README.md` | Kullanım, ön inceleme, komutlar, ölçümler ve dizin bağlantısı |

WareTrack'in incelenen commit'inde kaynak lisansı bulunamadı. Sade geometri, kamera ve panel ayrımı tasarım referansı oldu. Uygulama, protokol ve varlıklar özgün geliştirildi. Filo tanımı ve C1 doğrulayıcısı, mevcut Humble imajları ve test sürücüleri yeniden kullanıldı.

## Çalışma ortamı ve veri doğruluğu

Apple Silicon ARM64, Docker Desktop Engine 29.9.2, ROS 2 Humble, Gazebo Fortress headless, DART, yazılım OGRE2/EGL, Nav2/AMCL ve CycloneDDS. Chrome 156.0.8078.80, 1280 × 850 viewport, headless WebGL. C2.3 ve C4.5 farklı DDS bridge ağlarında ve domain'lerde çalıştı. Visualizer ayrı Docker konteyneri ve macOS loopback WebSocket kullandı.

C2.3 tek robot koşusunda `map → robot_1/odom → robot_1/base_link` gözlendi. C4.5 sırasında ikinci robotun aynı yapıda bileşke dönüşümü bağımsız olarak doğrulandı. `RobotStatus` 5 Hz ve RELIABLE/VOLATILE, KEEP_LAST 10. Görsel kaynak seçili TF zinciridir. `RobotStatus.pose` ve C4 batarya alanlarının değerlendirmesi [ön incelemede](preflight.md#robotstatus-ve-c5).

Canlı `ros2 node info` çıktılarında her köprü için yalnız `/clock` ve seçilen robotun `/tf` aboneliği yer aldı. Publisher, servis ve action listeleri boştu. `robot_2` seçimi ile aynı anda hareket edebilen iki robotlu ROS grafiğinden yalnız seçili zincir işlendi. WebSocket istemcisi robot, kaynak, çerçeve, sürüm, oturum, epoch, damga ve sonlu sayı denetimlerinden geçti. Prototipin Docker mount'u yalnız salt okunur filo config'ini kapsadı.

### Chrome ve hareket kanıtı

| Canlı koşu | WebSocket pozları | Tarayıcıda tam pozla kaydedilen kareler | Aynı damgada ROS + WebSocket + 3D |
| --- | ---: | ---: | ---: |
| C2.3 `robot_1` | 1462 | 954 | 952 |
| C4.5 enerji `robot_2` | 470 | 29 | 29 |

Chrome kontrolü her kaydedilen karede Three.js grubunun konumunu ve ön vektörünü WebSocket paketiyle karşılaştırdı. Yazılım render koşusunda bazı ölçümler bir sonraki paket geldiğinde interpolasyon içinde kaldı. Kök TF, WebSocket ve 3D modelin birleştirilebildiği örneklerde en büyük ROS–WebSocket konum farkı **0 m**, yaw farkı **8,88 × 10⁻¹⁶ rad** idi. C2.3 içinde başlangıçtan ölçülen en büyük uzaklık 2,400 m idi.

Tek robotlu koşudan bir ölçüm:

| ROS saati | Kök TF ve WebSocket `map` | Three.js sahnesi |
| --- | --- | --- |
| 20,978000000 sn | x = 0,376554 m, y = −0,162729 m, yaw = 1,663786 rad | X = 0,376554 m, Z = 0,162729 m, ön vektörün X/Z bileşenleri −0,092856 / −0,995680 |

Chrome'da başlangıç, hareket, `STALE`, `DISCONNECTED` ve yeniden bağlantı ekranları kaydedildi. Orbit sürükleme, yakınlaştırma ve takip düğmesi çalıştırıldı. Tarayıcı otomasyonunda sayfa hatası görülmedi.

### Kesinti ve bağımsız kapanış

- C2.3 sürücüsü bittikten sonra TF yardımcısı geçici duraklatıldı. Chrome WebSocket için `CONNECTED`, poz için `STALE` gösterdi ve son geçerli 57,426000000 sn pozu korundu. Besleme geri gelince 58,786000000 sn ve sonrasındaki ölçümler alındı.
- Köprü durdurulunca tarayıcı `DISCONNECTED` gösterdi ve 75,480000000 sn pozunu tuttu. Köprü tekrar açıldığında yeni süreç kimliğiyle 94,826000000 sn ölçümü doğrulandı. Aynı köprü sürecine tekrar bağlanmada eski pozun reddi ayrı WebSocket testinde doğrulandı.
- C4.5 enerji profilinde köprü 14:59:24 TSİ'de durdu. Fleet Manager 14:59:26,729 TSİ'de `ALL_C4_5_ENERGY_TESTS_PASSED` yazdı. Nav2 teslimatı tamamladı, ROS düğümleri ve `RobotStatus` yayını köprü kapalıyken gözlendi. SQLite bütünlük kontrolü C4.5 test çıktısında `ok`, yabancı anahtar sorgusu boştu.

## Gecikme ve kaynak kullanımı

Köprü 20 Hz ve 1 sn tazelik eşiğiyle, tek WebSocket istemcisi ve iz kaydı açıkken ölçüldü. ROS damgası, WebSocket gönderimi başlarken köprünün gözlediği son `/clock` ile karşılaştırıldı. TF alımından `send()` tamamlanmasına kadar konteynerin monotonik saati, tarayıcı alımından tam pozun işlendiği kareye kadar Chrome `performance.now()` kullanıldı. Tarayıcıya ağ üzerinden tek yön teslim süresi ayrı ölçülmedi. Yüzdelikler örneklerden hesaplandı.

| Koşu ve ölçüm | n | p50 ms | p95 ms | En büyük ms |
| --- | ---: | ---: | ---: | ---: |
| C2.3 ROS damgası → WS gönderimi başlangıcı, simülasyon saati | 1462 | 17,00 | 32,00 | 232,00 |
| C2.3 köprü TF alımı → WS gönderimi tamamlandı, monotonik | 1462 | 14,30 | 30,14 | 40,75 |
| C2.3 Chrome alımı → tam poz karesi, monotonik | 954 | 46,70 | 49,10 | 61,40 |
| C4.5 ROS damgası → WS gönderimi başlangıcı, simülasyon saati | 470 | 20,00 | 35,00 | 35,00 |
| C4.5 köprü TF alımı → WS gönderimi tamamlandı, monotonik | 470 | 17,86 | 32,86 | 46,81 |
| C4.5 Chrome alımı → tam poz karesi, monotonik | 29 | 56,70 | 60,50 | 61,00 |

`docker stats --no-stream` her durum için sekiz örnek aldı. Ölçüm C2.3 görevleri bittikten sonra duran robot ve çalışan simülasyonla yapıldı. Chrome sayfası yeniden bağlantıyı gözlemek için iki pencerede de açıktı. Tablo Docker konteynerlerini kapsar. Chrome ve Vite'ın macOS CPU/RAM'i ayrı ölçülmedi.

| Koşul | Konteyner | CPU medyanı (min–maks) | RAM medyanı (min–maks) |
| --- | --- | --- | --- |
| Köprü açık | Simülasyon | %171,58 (%159,74–%215,99) | 474,25 MiB (473,9–474,8) |
| Köprü açık | Visualizer köprüsü | %5,87 (%5,66–%10,29) | 48,46 MiB (48,23–48,75) |
| Köprü kapalı | Simülasyon | %206,80 (%170,64–%221,92) | 475,40 MiB (474,6–475,5) |

Docker CPU yüzdesi birden çok çekirdeği kullanınca %100'ü aşar. Kısa ve ardışık iki pencerenin simülasyon yükü değiştiği için simülasyondaki farktan nedensel bir performans sonucu çıkarılmadı. Köprü konteynerinin kaynakları ayrı ölçüldü.

## Testler ve regresyon

| Kapsam | Bu çalışmadaki sonuç |
| --- | --- |
| Fleet config doğrulayıcısı | Geçti, iki robot |
| Visualizer Python, host | 10 geçti, Humble'a özgü test modülü atlandı |
| Visualizer Python, Humble | 13 geçti, atlama yok |
| Visualizer frontend | 7 geçti, TypeScript/Vite üretim derlemesi başarılı |
| Depo host Python + Executor | 409 geçti, 28 atlandı, 0 başarısız |
| Depo Humble/CycloneDDS + Executor | İzole tekrar 457 geçti, 0 başarısız |
| Canlı C2.3 | 7/7, gerçek hareket ve Chrome doğrulaması |
| Canlı C3.3.3 T01–T10 | 10/10, Visualizer kapalı |
| Canlı C4.5 enerji | Geçti, köprü görev sırasında durduruldu |
| Canlı C4.5 şarj | Geçti, fiziksel dock devri ve şarj sonrası güvenli preemption |

İlk Humble regresyonunda Visualizer henüz çalışmıyorken `test_discovery_waits_for_ros_node_identity` DDS keşfinde yayıncı listesini boş gördü. Sonuç 456 geçti / 1 kaldı. Tekrar yeni konteynerde, canlı simülasyon yükü olmadan geçti. İlk C2.3 ön incelemesinde test sürücüsü uzun süre açık kalmış simülasyona geç katıldı ve AMCL ilk poz beklemesinde kaldı. Nihai koşuda iki C2.3 servisi birlikte başlatıldı ve yedi senaryo tamamlandı.

C4.5 şarj profili ayrı DDS domain'inde Visualizer kapalıyken çalıştı. Fiziksel dock devri, şarj sonrası duruş kanıtı ve LOW görevinin daha yeni epoch ile devamı doğrulandı. SQLite bütünlük kontrolü `ok` ve yabancı anahtar sorgusu boştu. Bu regresyon seçkisi C4.1–C4.4'ü Humble test takımı ve C4.5'in iki bütünleşik profili üzerinden kapsadı. Aşama bazlı C4.1–C4.4 Compose koşuları yeniden çalıştırılmadı.

C2.3 ile C4.5 enerji koşularında Visualizer, simulation ve backend çıkış kodları 0, `OOMKilled=false`. C3.3.3 ve C4.5 şarj koşularında iki konteyner de 0 ve `OOMKilled=false` ile kapandı. Simulation `SIMULATION_SHUTDOWN clean=true`, köprü `VISUALIZER_SHUTDOWN clean=true` kaydetti. `diagnostic_odom` yolu Humble testinde doğrulandı. Canlı kabul TF üzerinden yapıldı. Vite derleyicisi 500 kB üstü JavaScript chunk uyarısı verdi. Bu kurulumda derlenen JavaScript 1.093,78 kB, gzip 308,11 kB idi.

Ham ROS ölçümleri, WS mesajları, Three.js kareleri, Docker çıktıları ve PNG'ler `/tmp/fleet-viz-evidence/` altında kaydedildi. Bu worktree'nin izlenmeyen `fleet-visualizer/artifacts/2026-11-06/` dizininde ekran görüntüleri ve ölçüm kayıtlarının bir kopyası bulunur. Git kaydı Visualizer dalında yalnız yukarıdaki kapsamı içerir. Uzak `main` başlangıç SHA'sında kaldı. Push ve merge yapılmadı.
