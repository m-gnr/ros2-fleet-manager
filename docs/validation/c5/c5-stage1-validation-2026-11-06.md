# C5 / Aşama 1 — Salt okunur panel doğrulaması

**DOĞRULANDI** · 6 Kasım 2026 · Apple Silicon, ROS 2 Humble, CycloneDDS, Gazebo Fortress ve gerçek Google Chrome 156.0.8078.80. Panel Vite production derlemesinden yerel olarak sunuldu. [Komutlar ve başlatma](c5-stage1-commands-2026-11-06.md) · [Performans](c5-stage1-performance-2026-11-06.md)

## Sonuçlar

| Seçki | Geçti | Atlandı |
|---|---:|---:|
| Tam host Python ve Executor | 413 | 28 |
| Tam ROS 2 Humble ve CycloneDDS | 461 | 0 |
| Humble C2.3 ve C3.3.3 config | 6 | 0 |
| C5 Chrome frontend testleri | 5 | 0 |
| C4.5 canlı enerji profili | 1 | 0 |
| C4.5 canlı şarj/taşıma ve C5 Chrome | 1 | 0 |

Host atlamaları ROS 2/kurulu IDL gerektiren testlerdir. C5 backend testlerinin dördü iki tam seçkiye dahildir. Fleet config iki robot için geçerliydi. TypeScript ve Vite üretim derlemesi geçti. npm audit sıfır bilinen açık bildirdi. Derleme 500 kB üstü chunk ve Zod açıklama işaretleri için uyarı verdi. Humble testinde Starlette, TestClient bağımlılığına ilişkin deprecation uyarısı verdi.

## Canlı kabul

- Chrome iki robotun geçerli bataryasını ve `map` pozunu aldı. Her iki robotun ölçülen konumu ilk poza göre 0,25 m'den fazla değişti. Klavyeyle robot seçimi doğru ayrıntı panelini ve ölçüm değerini açtı.
- Her iki robot aynı fiziksel `dock_1` kaynağında sırayla şarj oldu. WebSocket'teki şarj sahibi, istasyonun işgal kaydı ve robotun doğrulanmış batarya ölçümüyle eşleşti. Şarj durumu Chrome istasyon tablosunda görüldü.
- `c45-low`, `c45-parallel` ve `c45-urgent` tarayıcıda atandı ve tamamlandı. LOW, güvenli kesme sonrasında kuyrukta tekrar göründü. C4.5 kabulü Nav2 terminal iptali ve 13 bağımsız odometri örneğiyle duruşu, daha yüksek yeni epoch ile LOW'un devamını ve gecikmiş terminalin reddini doğruladı.
- Kaynak snapshot'ı sıra 452'de iki robotun SoC/Wh alanları aynı damgalı BatteryState ile eşleşti. RobotStatus'taki poz ve yaw, aynı poz ölçüm damgasıyla doğrulandı. Üç terminal görev ile istasyon sahiplikleri SQLite satırlarına eşitti. `dock_1` serbest, `park_1` `robot_2` tarafından işgal edilmişti.
- FastAPI durdurulduğunda Chrome bağlantı kaybını, son konumu ve kullanılamayan bataryayı gösterdi. FastAPI oturumu değişti, yayıncı oturumu korundu ve sıra 10'dan 16'ya ilerledi. Chrome sekmesi aktif görevler sırasında kapatıldı. Yeni sekme ilerlemiş kaynak sırasını aldı, görevlerin tamamlandığını gösterdi ve kritik JavaScript/Konva hatası kaydetmedi.
- Sadece GET ve salt okunur WebSocket rotaları denetlendi. Canlı `POST /api/tasks` 405 döndü. Backend testleri eski snapshot, yeni oturum, yavaş istemci, bağlantı sınırı, yanlış Origin ve commit rollback yollarını kapsadı.
- Her iki canlı projede backend ve simulation çıkış kodu 0, `OOMKilled=false` ve `SIMULATION_SHUTDOWN clean=true` gözlendi. SQLite bütünlüğü `ok`, yabancı anahtar ihlali yoktu. Canlı C3.3.3 T01–T10 sonuçları tarihsel kayıttadır. Bu koşuda C3.3.3 config ve tam Humble regresyonları yeniden çalıştırıldı.

[Genel görünüm · 1440 px](screenshots/overview-1440.png) · [Fiziksel şarj](screenshots/charging.png) · [Bağlantı kesintisi](screenshots/connection-loss.png)

Diğer canlı ekran görüntüleri (1280, 1920, 390 px ve görev/istasyon görünümleri), `browser-metrics.json`, `verified-source.json`, Docker/Chrome logları ve SQLite kanıtı bu koşunun `/tmp/fleet-c5/accept/` dizininde tutuldu. İlk canlı denemede doğrulama gözlemcisi, henüz eski olan snapshot'ı sonraki SQLite sahipliğiyle karşılaştırdı. Karşılaştırma terminal commit sonrasında alınmış görüntüye sabitlendi. İkinci koşuda kaynak karşılaştırması ve ürün senaryosu geçti, Chrome boş favicon isteğinde 404 kaydetti. Sekme simgesi eklendi ve son koşu temiz tamamlandı.

## Kapsam

Aşama 1 kabulü iki robotlu yerel doğrulama düzeneğini kapsar. Temsili 2D zemin, gerçek navigasyon engellerini göstermez. Anlık yetkili şarj sırası, görev ETA ve ilerleme yüzdesi görüntülenmez. Canlı Fleet Manager kurtarma, nihai üç servisli ürün dağıtımı ve görev kontrolü sonraki kapsamdır. [Mimari ve güvenlik sınırları](../../design/c5-readonly-dashboard.md)
