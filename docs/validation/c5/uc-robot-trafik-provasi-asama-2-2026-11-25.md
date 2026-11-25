# C5 — Yakın park ve şarj yaklaşımı, Aşama 2

**GEÇTİ — 25 Kasım 2026.** Değişikliksiz 30 × 18 m Gazebo profilinde Beta parka, Alpha şarja, Gamma teslimata giderken sağ geçişte Beta ile Alpha birbirinin yerel costmap’inde doğrulandı. En küçük örneklenen merkez mesafesi **0,972 m**. Gazebo robotlar arası temas kaydetmedi ve üç hedef doğrulandı. Sonuç bu demonstrasyon koşusuna aittir. [Kanıt özeti](uc-robot-trafik-provasi-asama-2-2026-11-25.json).

## Oturumlar ve tetikleme

Başlangıçta temiz `main` ve GitHub `main` aynı `73166da1a0569155eadc318fcfb3993ed0a7ab00` SHA’sındaydı. [Aşama 1](uc-robot-trafik-provasi-asama-1-2026-11-25.md) aynı sağ geçişte 4,261 m eşzamanlı örnek minimumu vermişti. Mevcut kaynaklar salt okunur bağlandı. Her iki yeni oturumda üç robotun AMCL, Nav2, TF ve RobotStatus hazırlığı ile deneysel PeerRobotLayer doğrulandı.

| Oturum | Sonuç |
|---|---|
| `c5-demo-20261125T171038Z-6ac01e33b891`, domain 201 | Beta hazırlık teslimatının pickup etabındayken `GET /api/tasks` bir HTTP 503 döndürdü. Prova aracı koşuyu erken sonlandırdı. Planlanan y ≥ 0,15 m tetiklemesi uygulanmadı. Kontrollü çıkış 0. |
| `c5-demo-20261125T171850Z-2a7c4ebdab69`, domain 214 | Prova aracına geçici API okuma hatası için sınırlı tekrar eklendi. Beta’nın gerçek `RETURNING_TO_PARK` durumunda sağ geçişte x ≥ 10,50 m, y ≥ 0,25 m şartı kullanıldı. Eşik sağlandığında, 145,810 sim-s’de Beta (14,167, 0,346) m’deydi ve Gamma teslimat rotasındaydı. Mevcut Battery Simulator API’si Alpha’ya %24 SoC, `NORMAL` uyguladı ve ayrı geri okuma `VERIFIED` döndü. |

Beta’nın park dönüşü, `pick_B2 → shipping_2` hazırlık teslimatı tamamlanınca Fleet Manager tarafından başlatıldı. Ölçülen Gamma teslimatı Beta hazırlık teslimatının son yaklaşımında gönderildi. Tetik için Gazebo fiziksel pozu ve gerçek görev durumları kullanıldı.

## Hareket ve hedef sonuçları

| Robot | Rol | Fiziksel öteleme (sim-s) | Sonuç |
|---|---|---:|---|
| Beta | `park_2` | 122,185–158,025 | Nav2 başarı, SQLite `ARRIVED` ve `OCCUPIED`, RobotStatus `IDLE`. |
| Alpha | `dock_6` | 146,790–181,650 | Nav2 başarı, SQLite `ARRIVED` ve `OCCUPIED`. İlk `BatteryState.is_charging=true` 181,980 sim-s, ölçülen enerji 22,627 → 23,091 Wh. |
| Gamma | `pick_A1 → packing_1` | 101,570–267,715 | 270,445 sim-s’de eşleşen `ExecuteTask` başarı, `completed_epoch=1`, SQLite `COMPLETED`. |

Üç rol 146,600–158,275 sim-s arasında etkin, Gazebo fiziksel pozlarına göre üçlü öteleme toplam 11,025 sim-s idi. En uzun kesintisiz örnek aralığı **147,350–158,025 sim-s**. Öteleme, fiziksel poz örnekleri arasındaki hızın >0,01 m/s olmasıyla ölçüldü.

## Sağ geçiş ve iki yönlü yerel costmap kanıtı

**147,1175–157,675 sim-s** arasında 19 yakın grid çifti doğrulandı. 3 × 3 m yerel pencerelerde Beta→Alpha **19/19**, Alpha→Beta **19/19**. Her yön için gerçek `OccupancyGrid` içinde hem güncel PeerRobotLayer merkezinin hem de Gazebo pozunun projeksiyonunun maliyeti `100`. Her eşleşmede grid ile rapor en fazla 50 ms, peer damgası ile Gazebo fiziksel örneği en fazla 50 ms sim zamanı farkla bağlandı. Ölçülen iki yönün grid damgası farkı en çok 15 ms idi. Aynı zamana getirilen Gazebo örnekleri, kaydedilen statik `map ← warehouse_grid` ve zaman eşlemeli `map ← <robot>/odom` TF’si ile iki gridin içine ayrı ayrı projekte edildi.

Örnek olarak 147,640 sim-s’de Beta’nın gridinde Alpha’nın rapor ve fiziksel hücresi `[36,8]`. 147,655 sim-s’de Alpha’nın gridinde Beta’nın rapor hücresi `[15,45]`, fiziksel hücresi `[15,43]`. Dört hücre de `100`. Eşleşen fiziksel örnekler ve peer merkezleri arasındaki en büyük fark 0,130 m.

En küçük eşzamanlı örnek mesafe **0,972 m**, 147,875 sim-s. Aynı anda Beta (14,200, 0,854) m’de, Alpha (13,480, 1,507) m’deydi. Alpha, Beta’nın izinin batısında kuzeye yöneldi. Beta park cebine dönerken Alpha kuzeye devam etti. Bu mesafe ölçülen örnekten gelir ve genel güvenlik sınırı teşkil etmez.

## Tepki, temas ve güncellik

- **Rota.** Karşılaşma çevresinde Beta’nın 15, Alpha’nın 18 güncel Nav2 planı gözlendi. Aynı hedefe art arda yayımlanan rotaların sağ geçişteki en büyük yanal farkı Beta 0,224 m, Alpha 0,100 m. İncelenen ardışık planlarda 0,25 m’yi aşan rota sapması görülmedi.
- **Bekleme.** Aktif sürüşte 5 sim-s ve üzeri ötelemesiz aralık görülmedi. En uzun örnekler Beta 0,280, Alpha 3,920, Gamma 4,270 sim-s. Ölçüt, dönme dahil ötelemesiz aralıkları kapsıyor.
- **Temas ve abort.** 18 Gazebo temas kanalında birer yayıncı, **0 robotlar arası temas** ve **0 temas durdurması**. Kabul hedeflerinde terminal `NavigateToPose ABORTED` **0**. Beta’nın hazırlık teslimatında iki iç `FollowPath` handle abort kaydı ve koşu genelinde 15 goal-ACK timeout uyarısı var. Kapanışta Gamma’nın teslimattan sonra aldığı otomatik park hedefi iptal edilirken bir `Aborting handle` satırı oluştu.
- **RobotStatus STALE** 0. En uzun gözlenen RobotStatus mesaj aralığı 1,361 duvar-s.
- **Panel pose STALE** 10 anlık görüntü. **Panel UNAVAILABLE** 10 anlık görüntü. **Bağımsız TF** görev penceresinde `LIVE`.
- **Costmap current=false** 74 yerel ve 22 global rapor örneği. Doğrulanan yakın karşılaşma aralığında current=false, panel pose STALE veya panel UNAVAILABLE örneği **0**.

**Öneri.** Sunum provasını aynı tetikle tekrarlayın. Ölçülen 19 iki yönlü yerel grid çifti ve temassız üç varış bu koşuya aittir. Tekrar koşusu, aynı geçişin ve güncellik bulgularının tekrarlanabilirliğini ölçer.

## Komutlar, ham kanıt ve kapanış

- Git başlangıcı `git status --short --branch`, `git worktree list`, `git rev-parse HEAD`, `git ls-remote origin refs/heads/main`.
- Başlatma `bash ../stage2-evidence/run_attempt.sh <araç-dizini> <oturum-dizini> <başlangıç-SHA> 0.15` ve `0.25`. Araç, ROS overlay ile mevcut `stage1_run.py config/fleet.warehouse-30x18.yaml /evidence/live … --peer-awareness-experiment` çağrısını izole Docker oturumunda çalıştırdı. Mevcut `test_startup_readiness.py` sonucu 3 geçti. Salt okunur `peer_awareness_probe.py` ve temas gözlemcisi yeniden kullanıldı. `tf_monitor.py` gerçek TF mesajlarını kaydetti.
- Görevler `GET /api/task-catalog` ve `POST /api/tasks`. Batarya kontrolü `GET/POST /api/sim/batteries` ile yapıldı. Durum izlemesi `GET /api/robots`, `GET /api/tasks`, `GET /api/stations`.
- Kapanış `docker stop --time 120 <oturum>`, `docker inspect`, `docker logs --timestamps`, `docker ps`. Provaya ait iki container ve alt süreçlerinin çıkış kodu 0. SQLite bütünlük kontrolü `ok`, yabancı anahtar ihlali 0.
- Replay `python3 ../stage2-evidence/analyze.py <oturum-dizini>`, `python3 ../stage2-evidence/local_replay.py <oturum-dizini>`, deponun `peer_awareness_analyze.py` aracı ve `python3 ../stage2-evidence/verify_acceptance.py <oturum-dizini>`.

Host kanıt kökü `~/develop/fleet-traffic-stage1-2026-11-25.nU7gvy/stage2-evidence/`. `attempt-1/` ve `attempt-2/` altında `session.json`, `scenario.jsonl`, `container-state.json` ve `live/` var. Ham kanıt `live/{ros.jsonl,peer-probe.jsonl,contact-monitor.jsonl,tf-map-odom.jsonl,tf-static.jsonl,simulation.log,fleet.sqlite3}`. İkinci oturumda `local-grid-matches.jsonl`, `encounter.json`, `analysis.json` ve `acceptance-check.txt` yeniden okuma sonuçlarıdır. Kanıt dosyası hash’leri kökteki `sha256.txt` içindedir.

## Git teslimi

- **BAŞLANGIÇ_SHA** `73166da1a0569155eadc318fcfb3993ed0a7ab00`.
- **TESLİM_SHA** bu raporu ekleyen commit, `git log -1 --format=%H -- docs/validation/c5/uc-robot-trafik-provasi-asama-2-2026-11-25.md`.
- **GITHUB_MAIN_SHA** normal `git push origin main` sonrası `git ls-remote origin refs/heads/main` ile karşılaştırılır. Push kaydı ve doğrulanmış değerler kanıt kökündeki `git-delivery.txt` içindedir.
- Geri dönüş `git revert <TESLİM_SHA>`.
