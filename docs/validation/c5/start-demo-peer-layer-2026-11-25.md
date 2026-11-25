# C5 — Normal demo başlatıcısında PeerRobotLayer

25 Kasım 2026. Başlangıçtaki temiz çalışma ağacı, `HEAD`, `origin/main` ve GitHub `main` aynı `a4c0667fa16e99020d45102e236010068f817001` commit’indeydi.

**Canlı trafik kabulü başarısız.** Normal başlangıç ve altı costmap doğrulandı. Üç görevli koşuda robotlar arası temas kaydedilmedi. Alpha ve Beta’nın taşıma görevleri `packing_1` yakınında `NAV2_ABORTED` ile sonuçlandı. Kullanıcı mevcut başlatıcı değişikliğinin bu sonuçla yayımlanmasına sonradan açık onay verdi.

## Başlatma ve costmap doğrulaması

```sh
source .venv/bin/activate
./scripts/start_demo.sh
```

Başlatıcı, varsayılan `config/fleet.warehouse-30x18.yaml` profilini ve mevcut `stage1_run.py --peer-awareness-experiment` yolunu kullandı. Komut satırına argüman eklenmedi. Alpha, Beta ve Gamma’da `local_costmap` ve `global_costmap` için altı `Initialized plugin "peer_robot_layer"` satırı görüldü. Chrome başlatıcı URL’sini açtı. Gönderimden önce Chrome’da `Bağlı`, `3/3 TF LIVE`, üç `IDLE` robot, sıfır toplam ve aktif görev ile Görevler ekranında “Görev kaydı yok” doğrulandı. Test görevleri aynı URL’de Chrome’un Görevler formundan gönderildi.

Birinci oturum `c5-demo-20261125T181022Z-036d13e8d2e7`, ROS domain 231. İlk GUI gönderiminden önce zaman damgası farkı en fazla 50 ms olan güncel katman raporu ve gerçek `OccupancyGrid` eşleştirildi. Her güncel eşleşmede global grid iki peer merkezini birden `100` olarak işaretledi. Alpha 101/101, Beta 97/97, Gamma 101/101. Sırasıyla 3, 9 ve 5 ek eşleşmede rapor `current=false` idi.

## Alpha–Beta geçmişi ve tekrar

Rotalar ve öncelikler önceki oturumların SQLite görev snapshot’larından `created_at` sırasıyla okundu. Alım ve teslim pozları çalıştırılan profilin katalog noktalarıyla eşleştirildi. Robot seçimini Fleet Manager yaptı.

| Eski oturum | Kurtarılan GUI görev sırası | Gazebo teması |
|---|---|---|
| `c5-demo-20261125T175702Z-3dd31b8b52b2` | Üç kez `pick_A1 → packing_1` (LOW), sırasıyla Gamma, Beta, Alpha | 121,700 sim-s, `pick_A1` yakınında Alpha gövde ↔ Beta sol teker. Üç taşıma `EXECUTING` durumundaydı. |
| `c5-demo-20261125T175936Z-6accb0199643` | `pick_A1 → packing_1` (LOW), `pick_C2 → delivery-01` (MEDIUM), `inbound_1 → pick_B1` (LOW), ardından `pick_A1 → packing_1` (LOW) | 211,420 sim-s, yaklaşık (1,22; 2,74) m’de Alpha gövde ↔ Beta gövde. İlk üç taşıma `COMPLETED`, dördüncü `EXECUTING` durumundaydı. |

### Birinci tekrar

İlk dizinin üç LOW görevi GUI’den sırasıyla 21:16:20.822, 21:16:22.202 ve 21:16:23.923’te kabul edildi (TSİ, HTTP 201). FM atamaları Gamma, Beta ve Alpha ile eşleşti. İlk gönderim eski oturumdan daha uzun bir boşta bekleme sonrasında yapıldı. Önceki temasın çevresinde `pick_A1` yakınındaki en küçük örnek **0,920 m** idi. Yeni koşunun genel minimumu `packing_1` yakınında 420,315 sim-s’de **0,613 m** idi. Gazebo ve ürün temas koruması robotlar arası temas kaydetmedi. Eski temas olayı yeniden oluşmadı.

420,245 sim-s’de Alpha’nın yerel gridinde Beta hücresi `[24, 12]`, 420,475 sim-s’de Beta’nın gridinde Alpha hücresi `[31, 42]` idi. İki hücre de `100`. Katman raporları grid ile aynı damgadaydı. Poz örnekleri grid zamanından en fazla 50 ms uzaktaydı. Bu örnekte Beta hareket ederken Alpha teslim noktasındaydı.

Kullanıcı, Alpha ve Beta’nın `packing_1` çevresinde sıkışıp ilerleyemediğini gözlemledi. Gazebo pozlarında 437,0–443,7 sim-s aralığında her iki robotun merkezi 1 cm’den az yer değiştirdi. Gamma 401,180 sim-s’de `COMPLETED`. Alpha 443,715 ve Beta 444,800 sim-s’de `FAILED`. `ExecuteTask` sonuçları üç robotta da `completed_epoch=1` taşıdı. Alpha ve Beta terminal `NavigateToPose ABORTED`, `NAV2_ABORTED` ve `RobotStatus ERROR` üretti. Controller kayıtlarında iki robot için `No valid trajectories` ve `Controller patience exceeded` yer aldı.

### Durdurulan ikinci tekrar

`c5-demo-20261125T182319Z-c45d9dfad857`, ROS domain 202. Aynı normal komutla Chrome, üç `IDLE` robot, boş kuyruk ve altı katman yüklemesiyle açıldı. İlk üç görev GUI’den kabul edildi. Kullanıcının isteğiyle dördüncü görev gönderilmeden oturum kapatıldı. Karma görev dizisi için karşılaşma ve terminal sonuç kabulü tamamlanmadı.

## Kontrollü kapanış

İki oturumda da `Ctrl+C`, başlatıcının mevcut kapanış yolunu tetikledi. Başlatıcılar, container’lar ve her `shutdown.json` içindeki 11 alt süreç `0` ile çıktı. `lsof` ile API ve Vite portlarında dinleyici kalmadığı görüldü. Birinci oturumda kapanış sonrası SQLite bütünlük denetimi `ok` ve yabancı anahtar ihlali sayısı 0 idi. Kalıcı görev durumları GUI sonuçlarıyla eşleşti.

## Komut ve ham kanıt

- `bash -n scripts/start_demo.sh`, `python3 -m py_compile scripts/start_demo.py scripts/c5_demo_start.py`, `git diff --check` geçti. Başlatıcının profil doğrulaması ve `test_startup_readiness.py` 3/3 geçti. `python -m pytest -q tests/test_peer_awareness_config.py tests/test_c5_session_cleanup.py` mevcut test ortamında 16/16 geçti.
- Normal başlatma sonrası `docker exec` ile mevcut `peer_awareness_probe.py` çalıştırıldı. `/tmp/<oturum>/live/peer-probe.jsonl` costmap ve fiziksel pozları, `contact-monitor.jsonl` Gazebo temas kanallarını, `ros.jsonl` ürünün Action ve RobotStatus akışını tutar. On sekiz temas kanalında birer yayıncı görüldü. Oturum dizinindeki `gui-replay.jsonl` Chrome’un GUI gönderim yanıtlarını, `gui-ready.png` ve `gui-empty.png` görev öncesi ekranları, `gui-tasks.png` terminal durumları gösterir.
