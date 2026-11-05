# C3.3.4 Görev 5+6 — Robot bazlı canlı Nav2 rota doğrulaması

**Tarih:** 5 Kasım 2026. [Komut eki](c3-3-4-task-5-6-commands-2026-11-05.md) · [Rota ve Outbox sözleşmesi](../../design/c3-2-sqlite-outbox.md#canlı-nav2-rota-çözümü)

## Başlangıç ve kök neden

Yerel `main`, upstream `origin/main` ve GitHub'daki `refs/heads/main`, `ed13291dc8af1e721a7fec69b47d39d24d5abb65` üzerindeydi. Görev 1–4 commit'leri sırasıyla `fe2615b`, `fe280d2`, `1eb60a7` ve `ed13291` olarak geçmişte doğrulandı. Görev 4 commit'i GitHub'da mevcuttu. Başlangıçta `docs/README.md` değişikliği ve iki izlenmeyen kullanıcı yolu bulunuyordu.

`Scheduler` rota çağrısında robot kimliğini iletmiyordu. Sağlayıcının boş kimlik varsayılanı, aynı hücrelere ait ilk kaydı başka bir robot adına kullanabiliyordu. Rota yokluğunda Scheduler ile ROS planner arasında ürün bağlantısı kurulmamıştı. Resolver önce ortak önbelleğe yazıyor, sonra `ROUTE_RESOLVED` gönderiyordu. Consumer olay için yeni zamanlama başlatmıyor ve önbellek değişikliği SQLite COMMIT ile korunmuyordu. Tarihsel T02 ve T04 kontrollü rota beslemesine, T03 bağımsız planner sorgusuna dayanıyordu.

Ürün değişikliği öncesi seçki beş beklenen regresyon hatası üretti. Boş kimlik başka robotun sonucuna erişti, üç geçersiz mesafe saklandı ve canlı rota bağlantısı eksikti.

## Uygulama

- `route_cache.py` ve `scheduler.py` robot kimliğini, başlangıç/hedef hücrelerini ve harita revizyonunu korur. Hücre 0,20 m, TTL 30 sn. Boş kimlik, bilinmeyen robotun başka robota ait kaydı, sonlu olmayan/negatif uzunluk, eski revizyon ve dolmuş TTL kullanılmaz.
- `builder.py` varsayılan robot bazlı cache sağlayıcısını kurar. `ros2_adapter_node.py` Scheduler ile aynı cache'i kullanır ve YAML robot/namespace eşlemesiyle ilgili planner istemcilerini oluşturur. `route_resolver.py` yalnız başarılı ROS action sonucu ve geçerli çok pozlu Path için mesafe döndürür. Planner hazır değilse sorgu beklemez. 2 sn zaman aşımında geç kabul edilen goal dahil iptal istenir. Kuş uçuşu mesafe kullanılmaz.
- `event_loop.py` ve `route_planning.py` eksik rota taleplerini SQL transaction içinde toplar, COMMIT sonrasında robot başına tek etkin planner sorgusu başlatır. Tek tüketici, sonuç olayını sorgu UUID'si, robot, harita nesli, görev, oturum, epoch ve robot başlangıç hücresi bağlamıyla doğrular. Başarılı COMMIT sonrasında cache yayımlanır. Takip eden zamanlama mevcut domain ve Outbox geçişlerini kullanır. Geçersiz rota ilgili adayı eler. Aynı anahtar sonraki bir geçişte en erken iki saniye sonra yeniden denenebilir.
- `fleet_manager_core.py` ve `models.py` canlı rota için RobotStatus konum örneğinin geçerlilik penceresini korur. Scheduler güncel SoC ile robot → pickup, pickup → dropoff ve dropoff → güvenli şarj mesafelerini mevcut Wh hesabına verir. Preemption terminalinden sonra duran robotun güncel pozuyla normal aday ve sahiplik kontrolleri yeniden uygulanır.
- Test değişiklikleri `tests/test_fleet_manager_outbox.py`, `test_ros2_route_resolver.py`, `test_ros2_adapter_integration.py` ve yeni sağlayıcı imzasını kullanan mevcut domain, builder ve adaptör testlerindedir. Canlı varyant `docker/simulation-c3-3-3/check.py`, ilgili Compose katmanı ve `scripts/run_c3_3_3.py` üzerinden ayrılır. Tasarım, doğrulama dizini ve [Mermaid/SVG rota diyagramı](../../diagrams/README.md#17-route-cache) güncellendi.

## Otomatik testler

| Koşu | Sonuç |
|---|---|
| Scheduler, builder, domain, rota, Outbox ve inceleme bekletmesi | **DOĞRULANDI**, 146 geçti |
| Tam host Python ve Executor | **DOĞRULANDI**, 307 geçti, ROS ortamı gerektiren 25 atlandı |
| ROS 2 Humble / CycloneDDS, Fleet Manager ve Executor | **DOĞRULANDI**, 262 geçti, 26 mevcut jsonschema uyarısı |
| C3.3.3 container yolundan bağımsız config seçkisi | 3 geçti |
| C2.3 config, Docker içinde `/config` bağlı | 3 geçti |

Rota ve Outbox regresyonları aynı koordinatların iki robot için farklı sonuçlarını, devam eden rota nedeniyle bekleyen görevi, eksik üç ayağın her birini, güncel SoC/kaçış enerjisini, TTL, hücre değişimi, harita nesli, geç yanıt, tekrar, eşzamanlı sorgu birleştirme ve COMMIT geri almayı kapsadı. Sonuç beklenirken değişen oturum, stale telemetri ve süresi geçmiş poz örneği adaylığı engelledi. ROS testinde `r1` ve `r2` kimlikleri sırasıyla `/west` ve `/east` planner'larına bağlandı. İki gerçek DDS action sunucusu aynı uç noktalar için farklı Path döndürdü ve Scheduler daha kısa pickup rotasına sahip robotu seçti.

## Canlı Gazebo

### T02-AUTO-ROUTES

Ayrı Compose projeleri, temiz SQLite ve sıfır cache kaydıyla açıldı. T01 başlangıç kontrolü her koşuda iki Executor'dan güncel IDLE RobotStatus aldı. Varyantta elle cache girdisi yazılmadı ve görevler için testten `TICK` gönderilmedi. Her koşuda dokuz `ROUTE_APPLIED` kaydı, iki farklı robotun gerçek planner sonuçlarını gösterdi. Varyant, tarihsel T02'nin pickup/dropoff pozlarını ve 120 sn tamamlama eşiğini kullandı.

Son koşuda ölçülen Nav2 mesafeleri aşağıdadır. Güvenli şarj ayağı `dock_1` hedeflidir.

| Görev | Planner | Robot → pickup | Pickup → dropoff | Dropoff → şarj |
|---|---|---:|---:|---:|
| `task_t02_r1` | `/robot_1/compute_path_to_pose` | 0,500 m | 0,500 m | 2,122 m |
| `task_t02_r1` | `/robot_2/compute_path_to_pose` | 3,906 m | 0,500 m | 2,122 m |
| `task_t02_r2` | `/robot_2/compute_path_to_pose` | 0,500 m | 0,500 m | 4,547 m |

- **İlk koşu (`auto`), BAŞARISIZ.** İki görev doğru robotlara atandı ve her iki `EXECUTE_TASK` kaydı `SENT` oldu. `task_t02_r2` tamamlandı. `task_t02_r1` dropoff sürüşünde kabul süresini aştı ve son SQLite görüntüsü `ASSIGNED` kaldı.
- **Bağımsız tekrar (`auto-repeat`), DOĞRULANDI.** Aynı başlangıç ve eşiklerle iki gerçek `ExecuteTask` gönderildi. İki robot pickup, yükleme, dropoff ve boşaltmayı tamamladı. Backend'in SQLite denetiminde ve durdurulan container'dan alınan DB'de her iki görev `COMPLETED`, her iki komut `SENT`, atama epoch'ları 1 idi.
- **Son kaynakla koşu (`auto-final`), DOĞRULANDI.** Dokuz rota sonucu, iki `SENT` komut, iki `COMPLETED` görev ve iki epoch 1 ayrı container veritabanında tekrar doğrulandı.

### C3.3.3 ve C2.3 regresyonları

- **C3.3.3 `full`**, T01–T10 **10/10 geçti**. T02 iki kontrollü atamayı ve iki SQLite `COMPLETED` kaydını doğruladı. T03 gerçek Nav2 yolunu (2,10 m), erişilemez hedefte fallback yasağını ve Wh hesabını ayrı doğruladı. T04 güvenli terminal `PREEMPTED`, sayaç ve duruş sonrası yeni epoch/UUID ile tek HIGH Outbox kaydını doğruladı. T04'te duruş sonrası rota kontrollü olarak sağlandı. Canlı planner ile preemption zinciri bu Gazebo seçkisinde **HENÜZ TEST EDİLMEDİ**. Kontrollü asenkron planner ile aynı zincir Outbox regresyonunda doğrulandı.
- **C2.3 `c23`**, T01–T07 **7/7 geçti**. Tek robot lojistik döngüsü, güvenli preemption, HIGH koruması, Nav2 abort ve operatör kurtarması, epoch ve namespace kontrolleri geçti.

| Koşu | Nav2 `Failed to make progress` | Backend / simulation çıkışı | Simulation sinyalleri |
|---|---|---|---|
| C2.3 | 0 | 0 / 137 | SIGTERM → 3,017 sn → SIGKILL |
| T02-AUTO-ROUTES ilk | `robot_1` 4, `robot_2` 4. Kabul süresi aşıldı. | 1 / 137 | SIGTERM → 3,026 sn → SIGKILL |
| C3.3.3 T01–T10 | `robot_1` 4. T02 tamamlandı. | 0 / 137 | SIGTERM → 3,028 sn → SIGKILL |
| T02-AUTO-ROUTES tekrar | `robot_2` 4. T02 tamamlandı. | 0 / 137 | SIGTERM → 3,021 sn → SIGKILL |
| T02-AUTO-ROUTES son | `robot_2` 4. T02 tamamlandı. | 0 / 137 | SIGTERM → 3,019 sn → SIGKILL |

Docker her simulation container için `OOMKilled=false` bildirdi. Çıkış 137, backend çıktıktan sonra Compose durdurma yolunda gözlendi. Son varyant koşusunda, durdurma sinyalinden sonra robot_1 lifecycle yöneticisi bt_navigator heartbeat kaybı bildirdi. Simulation kapanışı ayrıca başarısız kaldı.

## Açık kalan doğrulama

- T02'de dropoff ilerleme kararsızlığı tekrarlandı. Başarılı koşular dayanıklılık veya tekrar edilebilirlik garantisi sağlamaz.
- Harita revizyonu ve gecikmiş sonuç reddi otomatik testte doğrulandı. Canlı harita değişim bildirimi bu doğrulamanın parçası değildi.
- C4 öncesi geçici batarya telemetrisi kullanıldı. Görev 7 YAML politika bağlama çalışması ve ürün Battery Simulator kapsam dışı kaldı.

## Git kaydı

Başlangıç `ed13291dc8af1e721a7fec69b47d39d24d5abb65`. Bu raporu ekleyen görev commit'inin mesajı `feat(fleet-manager): integrate robot-specific live Nav2 routing`. Raporun kendi commit hash'i Git geçmişinden alınır. Push hedefi `origin/main` ve normal fast-forward'dur. Son uzak hash ile yerel HEAD eşleşmesi push sonrasında ayrı denetlenir. Komutlar [Git doğrulama ekinde](c3-3-4-task-5-6-commands-2026-11-05.md#git-doğrulaması) yer alır. Başlangıçtaki `docs/README.md` ve izlenmeyen `docs/gereksinim-literatur-ozgunluk-2026-10-27.pdf`, `docs/reports/` çalışma ağacında kullanıcıya ait yollar olarak bırakıldı.
