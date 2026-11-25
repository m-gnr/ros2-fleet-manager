# C5 — GUI açıkken üç robotlu sunum provası, Aşama 3

**GEÇTİ — 25 Kasım 2026.** Alpha şarja, Beta parka ve Gamma teslimata giderken fiziksel ötelemeleri toplam **11,025 sim-s** örtüştü. Sağ geçişte Alpha ile Beta, birbirinin yerel Nav2 costmap’inde **18 iki yönlü grid çiftinde** doğrulandı. Örneklenen en küçük merkez mesafesi **1,035 m**. Gazebo robotlar arası temas kaydetmedi. Üç hedef tamamlandı ve üstten depo görünümü hareketleri takip etmeye elverişliydi. [Kanıt özeti](uc-robot-trafik-provasi-asama-3-2026-11-25.json).

## Hazırlık ve tetikleme

Temiz başlangıç ve GitHub `main` SHA’sı `274a4083bcc6c5d7000e32497b13b5a3ea478ade`. Prova, mevcut çalışma dizininde bu commit doğrudan açılarak yürütüldü. [Aşama 2](uc-robot-trafik-provasi-asama-2-2026-11-25.md) araçları ve aynı 30 × 18 m profil, salt okunur kaynak ve ROS overlay ile kullanıldı. İzole oturum `c5-demo-20261125T173634Z-1026d28f07e7`, ROS domain 224. Mevcut `stage1_run.py --peer-awareness-experiment` üzerinden PeerRobotLayer etkinleştirildi. Başlatma aracının ilk hazırlık çağrısında API bağlantısı yanıt vermeden kapandı ve ilk container 143 koduyla durdu. Henüz görev yoktu. Hazırlık sorgusu bu geçici bağlantı durumunu bekleyecek şekilde düzeltildi ve görev gönderilen tek prova bu oturumda baştan sona tamamlandı.

Saatler Türkiye saatiyle verilmiştir. API açılışta `/api/robots` için **20:36:48.606**, `/api/tasks` için **20:36:48.610** saatinde 503 döndürdü. API hazırlığı 20:36:51.418’de, Chrome’da üç görünür robot ve `3/3 TF LIVE` 20:36:52.847’de kaydedildi. AMCL, Nav2, TF, artan RobotStatus sıraları, başlangıç costmap hücreleri, canlı API, boş görev kuyruğu ve ilerleyen WebSocket akışı birlikte doğrulandıktan sonra ilk görev **20:37:02.832**’de gönderildi.

Beta’nın `pick_B2 → shipping_2` hazırlık teslimatını Fleet Manager otomatik park dönüşüyle izledi. Gamma’nın `pick_A1 → packing_1` görevi, Beta hazırlık teslimatının son yaklaşımında gönderildi. Beta gerçekten `RETURNING_TO_PARK`, Gamma gerçekten `EXECUTING_TASK` iken sağ geçit eşiği `x ≥ 10,50 m, y ≥ 0,25 m` kullanıldı. Beta **136,885 sim-s**’de **(14,191, 0,269) m** konumuna gelince mevcut batarya API’si Alpha’ya `NORMAL` modunda %24 SoC uyguladı. Ayrı geri okuma 20:39:12.975’te `VERIFIED` döndü.

## Hareket ve hedefler

| Robot | Gerçek hedef | Fiziksel öteleme (sim-s) | Tamamlanma kanıtı |
|---|---|---|---|
| Alpha | `dock_6` | 137,935–166,845 | Nav2 başarı, SQLite `ARRIVED` ve `OCCUPIED`. İlk `BatteryState.is_charging=true` damgası 167,020 sim-s. Enerji 22,649 Wh’den 23,225 Wh’ye çıktı. |
| Beta | `park_2` | 112,735–149,520 | Nav2 başarı, SQLite `ARRIVED` ve `OCCUPIED`, RobotStatus `IDLE`. |
| Gamma | `pick_A1 → packing_1` | 92,225–276,115 | 279,735 sim-s’de eşleşen `ExecuteTask` UUID’siyle başarı ve `completed_epoch=1`. SQLite `COMPLETED`, Görevler ekranında “Tamamlandı”. |

Gazebo fiziksel pozları arasındaki öteleme hızı için Aşama 2’nin >0,01 m/s ölçütü kullanıldı. En uzun kesintisiz üçlü öteleme aralığı **138,950–149,520 sim-s** (10,570 sim-s).

## Sağ geçiş ve temas

Yerel 3 × 3 m pencerelerde, **139,085–149,2925 sim-s** arasında Beta→Alpha **20/21** ve Alpha→Beta **19/19** grid doğrulandı. İki yönü aynı anda karşılayan **18** çiftte en büyük grid damgası farkı 215 ms sim zamanıydı. Gerçek `OccupancyGrid` içinde PeerRobotLayer merkezinin ve zaman eşlemeli TF ile projekte edilen Gazebo pozunun hücre değeri her doğrulanmış yönde `100` idi. Grid–rapor ve peer–fiziksel poz eşlemeleri 50 ms içinde yapıldı. Örneğin 144,670 sim-s’de Beta’nın gridinde Alpha’nın rapor ve fiziksel hücreleri `[48,16]` ve `[47,15]` idi. 144,680 sim-s’de Alpha’nın gridinde Beta için `[12,43]` ve `[12,42]` idi.

**145,495 sim-s**’de en yakın eşzamanlı örnekte Beta (14,064, 2,329) m, Alpha (13,270, 2,992) m’deydi. Merkez mesafesi **1,035 m**. On sekiz Gazebo temas kanalının her birinde bir yayıncı gözlendi. Robotlar arası temas, temas durdurması ve terminal `NavigateToPose ABORTED` sayısı **0**. Mesafe gözlenen örnekler için geçerlidir.

## GUI ve güncellik

Chrome’un üstten görünümünde üç robotun konumu, Nav2 planları ve TF izleri takip edildi. Görev penceresinde `/ws/fleet` üzerinden **1.264** ürün snapshot’ı alındı. En uzun alım aralığı 0,728 duvar-s. Üç robot için sırasıyla Alpha 40, Beta 142, Gamma 224 plan paketi alındı. WebSocket yeniden bağlanması, genel bağlantı kesintisi veya haritada `3/3 TF LIVE` kaybı gözlenmedi. Robot kartlarında 20:38:29.432, 20:38:36.966, 20:38:44.067, 20:40:30.609, 20:41:05.866 ve 20:41:11.562’de kısa “Kullanılamıyor” uyarıları göründü. Sonraki normal örnekler ilk uyarı örneğinden en geç 0,405 duvar-s sonra alındı. Harita ve rota takibi sürdü.

| Durum | İlk görev isteği ile hedeflerin doğrulanması arasındaki gözlem |
|---|---|
| Panel poz `STALE` | ROS gözlemcisinde 10, Chrome WebSocket akışında 7 snapshot. Gözlemci zamanları 20:38:29.394–20:42:32.428. |
| Panel `UNAVAILABLE` | ROS gözlemcisinde 9, Chrome WebSocket akışında 6 snapshot. Gözlemci zamanları 20:38:29.394–20:41:11.579. |
| RobotStatus `STALE` | 0. Gözlenen en uzun RobotStatus alım aralığı 1,418 duvar-s. |
| PeerRobotLayer `current=false` | 157 yerel örnek 20:39:51.044–20:42:28.952 arasında. 42 global örnek 20:39:51.916–20:42:28.920 arasında. |

Doğrulanan yakın karşılaşma penceresinde bu dört durumun örnek sayısı 0. Tekil olayların duvar ve simülasyon zamanları kanıt dizinindeki `gui-review.json` dosyasındadır.

## Kanıt, kapanış ve Git

- Kanıt dizini `~/develop/fleet-traffic-stage3-2026-11-25.F5O348/prova/`. `gui-ready.png` görev öncesini, `gui-overlap.png` **20:39:22.389**’da üçlü hareketi ve yakın geçişi, `gui-completed.png` **20:42:41.801**’de üç hedefin son durumunu, `gui-deliveries.png` **20:42:42.240**’ta Gamma’nın tamamlanan görevini gösterir. Görüntü SHA-256 değerleri kanıt özetindedir.
- Mevcut `test_startup_readiness.py` **3/3** geçti. Önceki aşamanın `analyze.py`, `local_replay.py`, `verify_acceptance.py` ve deponun `peer_awareness_analyze.py` komutları bu oturumun kanıtına çalıştırıldı. `acceptance-check.txt` tüm 12 denetimi doğruladı. Ham ölçümler `live/{ros.jsonl,peer-probe.jsonl,contact-monitor.jsonl,tf-map-odom.jsonl,tf-static.jsonl,fleet.sqlite3}`, API geçişleri `scenario.jsonl` ve Chrome ölçümleri `browser.jsonl` içindedir.
- Yalnız prova oturumunun Docker container’ı, Chrome profili ve Vite süreci kapatıldı. Üst container ve 11 alt süreç kodu 0. SQLite `integrity_check=ok`, yabancı anahtar ihlali 0. Prova portları boş.
- Başlangıç SHA’sı `274a4083bcc6c5d7000e32497b13b5a3ea478ade`. Teslim SHA’sı bu raporu ekleyen commit’tir. Uzak SHA doğrulaması ve geri dönüş komutu kanıt kökündeki `git-delivery.txt` makbuzunda saklanır.
