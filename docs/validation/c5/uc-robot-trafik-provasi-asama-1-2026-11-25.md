# C5 — Üç robotlu trafik provası, Aşama 1

**GEÇTİ — 25 Kasım 2026.** GitHub `main` üzerindeki 30 × 18 m Gazebo deposunda üç robot aynı anda ötelendi. Hareket sırasında her robotun global Nav2 costmap’inde diğer iki robotun merkezi lethal işaretlendi. Gazebo robotlar arası temas kaydetmedi. Gamma teslimatı tamamladı, Beta parka vardı ve Alpha şarja başladı. Sonuç bu oturum, deneysel PeerRobotLayer ve gözlenen geçişler için geçerlidir. [Küçük kanıt özeti](uc-robot-trafik-provasi-asama-1-2026-11-25.json).

## Oturum ve komutlar

Temiz `main`, başlangıçta GitHub ile aynı SHA’daydı. Eski ve kirli yerel `main` bulunduğundan GitHub ayrı bir dizine klonlandı. Oturum `c5-demo-20261125T165517Z-16fb37c0b59e`, ROS domain 228 ve oturum adına özel Gazebo partition kullandı. Kaynak dizini container’a salt okunur bağlandı. Mevcut 30 × 18 m profil, Nav2 şablonu ve deneysel başlatma yolu kullanıldı. Hostta çalışan prova aracı hazırlık teslimatını, gözlem zamanlamasını ve yetkili batarya isteğini yönetti. İlk çağrı bu aracın kabuk değişkeni kaçışı yüzünden container oluşmadan kesildi. Aracın kaçışı düzeltildi ve boş bir kanıt dizininde tek canlı koşu başlatıldı.

| Adım | Çalıştırılan komut veya ürün uçları |
|---|---|
| Başlangıç | `git status --short --branch`, `git worktree list`, `git ls-remote origin refs/heads/main`, `git clone --branch main --single-branch -- https://github.com/m-gnr/ros2-fleet-manager <izole-dizin>` |
| Başlatma | `bash ../evidence/run_attempt.sh ../evidence ../evidence/attempt-2 <BAŞLANGIÇ_SHA>` ve izole container’da `python3 docker/simulation-warehouse-grid/stage1_run.py config/fleet.warehouse-30x18.yaml /evidence/live --api-port 21830 --scene-port 21831 --origin http://127.0.0.1:21832 --ros-overlay /c5-cache/install --peer-awareness-experiment` |
| Hazırlık ve ölçüm | `python docker/simulation-warehouse-grid/test_startup_readiness.py` (3 geçti), `docker exec <oturum> … peer_awareness_probe.py config/fleet.warehouse-30x18.yaml /evidence/live/peer-probe.jsonl --duration 1100` ve mevcut ROS/SQLite gözlemcisi. `1100` probe üst süre sınırıdır. |
| Senaryo | `GET /api/task-catalog`, `POST /api/tasks`, `GET /api/robots`, `GET /api/tasks`, `GET /api/stations`, `GET /api/sim/batteries` ve `POST /api/sim/batteries`. Mevcut Battery Simulator kontrolü yalnız Alpha’nın SoC’sini %24’e aldı. `NORMAL` modunda uygulama ve ayrı geri okuma `VERIFIED` döndü. |
| Kapanış ve replay | Sahiplik ve salt okunur workspace bağı denetimiyle `docker stop --time 120 <oturum>`, ardından `docker inspect`, `docker logs --timestamps` ve `docker ps`. `python3 ../evidence/analyze.py ../evidence/attempt-2`, `python3 docker/simulation-warehouse-grid/peer_awareness_analyze.py ../evidence/attempt-2 ../evidence/attempt-2/repository-replay.json` ve `git diff --check`. |

Depodaki önceki ölçüm yöntemi için [peer farkındalığı raporu](peer-awareness-2026-11-18.md) ve [komut eki](peer-awareness-commands-2026-11-18.md).

## Atamalar ve eşzamanlı hareket

| Robot | Gerçek rol ve hedef | Öteleme aralığı (sim-s) | Terminal kanıtı |
|---|---|---:|---|
| Gamma | Teslimat, `pick_A1 → packing_1` | 85,680–252,350 | `ExecuteTask` başarılı, UUID `7005a4bf-cc0b-4a8a-a1ee-7a08bad79568`, `completed_epoch=1`, 255,745 sim-s. Eşleşen SQLite görevi `COMPLETED`. |
| Beta | Park dönüşü, `park_2` | 105,840–139,895 | Nav2 başarılı, SQLite `ARRIVED` ve `park_2 OCCUPIED`, RobotStatus `IDLE`. Son park yaklaşım örneği yaklaşık (13,60, 2,60) m. |
| Alpha | Şarj dönüşü, `dock_6` | 115,920–144,760 | Nav2 başarılı, SQLite `ARRIVED` ve `dock_6 OCCUPIED`. İlk `BatteryState.is_charging=true` 144,915 sim-s. Enerji 22,657 Wh’den 23,235 Wh’ye yükseldi. |

Fleet Manager, Beta’ya önce `pick_B2 → shipping_2` hazırlık teslimatını atadı. Bu görev 105,005 sim-s’de tamamlanınca mevcut park akışı başladı. Ölçülen teslimat Beta hazırlık teslimatının son yaklaşımında gönderildi. Alpha’nın SoC kontrolü, Beta park dönüşünde sağ geçide yaklaşırken uygulandı. Gamma için teslimat sonrasında otomatik `park_1` ataması oluştu. Kabul penceresi Beta’nın park varışını kapsıyor.

Üç rolün RobotStatus penceresi **115,890–142,705 sim-s**. Gazebo fiziksel pozlarında örnekler arası öteleme hızı >0,01 m/s ölçütüyle üçlü öteleme **toplam 23,660 sim-s**, en uzun kesintisiz örnek aralığı **116,725–139,895 sim-s**. Aralıklar örneklenen hareketin ilk ve son zamanıdır.

## Costmap, temas, bekleme, abort ve güncellik

- Fiziksel reset, üç robotun AMCL ve Nav2 hazırlığı, gerçek `map → odom → base_link` TF’si ve ilerleyen RobotStatus sıraları ilk görevden önce doğrulandı. Her global gridde iki peer merkezi için robot başına en az iki örnek `100` çıktı.
- Eşzamanlı fiziksel hareket örneklerinde altı yönün her birinde **13/13 lethal** hücre bulundu. Ölçüm aynı frame’de, PeerRobotLayer raporu ile en fazla 50 ms sim zamanı farkıyla eşleşen gerçek `OccupancyGrid` hücrelerini okudu. 3 × 3 m kayan yerel pencerelerde üç rolün ortak aralığında diğer robotların merkezleri pencere dışındaydı. Altı yönün canlı kabulü global gridlere dayanır.
- On sekiz Gazebo temas kanalında birer ROS yayıncısı gözlendi. İki gözlem akışında robotlar arası temas **0**, mevcut temas durdurma kaydı **0**. Aktif sürüşte 5 sim-s ve üzeri ötelemesiz aralık görülmedi. En uzun örneklenen aralık Gamma 3,920, Beta 2,765, Alpha 0,210 sim-s. Nav2 action `ABORTED` sayısı **0**. Gamma’da tek `compute_path_to_pose` goal-ACK timeout uyarısı görüldü, ilgili taşıma tamamlandı.
- Ölçülen harekette bağımsız TF okuyucusunda zincir kaybı görülmedi. 180,005 sim-s’de Beta’nın yerel peer raporu bir örnekte Alpha’yı güncel saymadı ve `current=false` oldu. Sonraki rapor 180,130 sim-s’de `current=true`. Üçlü hareket penceresi bu olaydan önce bitti.
- RobotStatus `telemetry=STALE` **0**. Gözlenen mesaj aralıklarının en büyüğü Alpha 0,547, Beta 0,521, Gamma 0,603 duvar-s. 208,640 sim-s’de Gamma’nın bir panel anlık görüntüsü `telemetry=UNAVAILABLE` ve `pose_reliability=STALE` verdi. Aynı aralıkta bağımsız TF örnekleri `LIVE`, son RobotStatus alım yaşı 0,101 duvar-s idi. Ayrı TF probe’unda açılış ve kontrollü kapanış geçişlerine ait `FRAME_ERROR` ve kapanışta `STALE` de kaydedildi.

## Sağ taraftaki park ve şarj geçişi

Gazebo’nun örneklenen gerçek izleri, sağ tarafta (x ≥ 10,50 m) geometrik olarak kesişmedi. En yakın iz örnekleri y ≈ 2,60 m’deydi. Alpha (13,26, 2,59) m’den 121,870 sim-s’de, Beta (13,60, 2,60) m’den 140,000 sim-s’de geçti. Bu iki örnek uzayda 0,331 m, zamanda 18,130 sim-s aralıklıydı. İki hareketin en çok 50 ms farkla eşlenen sağ taraf örneklerinde merkezler arası en küçük uzaklık 4,261 m idi. Bu değerler örnekleme kapsamındadır.

**İkinci aşama için öneri.** Sağ geçitte iki rotanın aynı alanı daha küçük zaman farkıyla kullandığı bir varyasyonla eşzamanlı yaklaşmayı ölçün. Bu koşuda en yakın iz örnekleri arasında 18,130 sim-s vardı.

## Ham kanıt ve kapanış

Ham dosyalar hostta `~/develop/fleet-traffic-stage1-2026-11-25.nU7gvy/evidence/attempt-2/` dizinindedir. `session.json` izole oturum, SHA, image, overlay ve gerçek başlatma argümanlarını içerir. `scenario.jsonl` API istek/yanıtlarını, `stationary-verification.json` hazırlık ve görev öncesi hücre eşleşmelerini içerir. `live/ros.jsonl`, `live/peer-probe.jsonl`, `live/contact-monitor.jsonl`, `live/simulation.log` ve `live/generated/` birincil ölçümlerdir. `role-grid-matches.jsonl`, `role-trajectories.json`, `analysis.json`, `repository-replay.json` ve `acceptance-check.txt` replay kayıtlarıdır.

`live/shutdown.json` ve `container-state.json` on alt süreç ile üst container için çıkış kodu 0 gösterir. `docker-after.txt` kapanış sonrası çalışan container olmadığını gösterir. `live/fleet.sqlite3` için `integrity_check=ok`, foreign key ihlali 0. Hash listesi aynı dizindeki `sha256.txt` dosyasındadır.

## Git teslimi ve geri dönüş

- **BAŞLANGIÇ_SHA** `0cf8f66d7c95b91b7b73e9677e82953f0016ce9e`.
- **TESLİM_SHA** bu raporu ekleyen Git commit’idir. `git log -1 --format=%H -- docs/validation/c5/uc-robot-trafik-provasi-asama-1-2026-11-25.md` ile okunur.
- **GITHUB_MAIN_SHA** push sonrasında `git ls-remote origin refs/heads/main` ile teslim commit’iyle karşılaştırılır. Doğrulanmış değerler ve push çıktısı hosttaki `evidence/git-delivery.txt` makbuzuna yazılır. Commit’in kendi SHA’sı commit oluşturulduktan sonra hesaplanır.
- Geri dönüş komutu `git revert <TESLİM_SHA>`.
