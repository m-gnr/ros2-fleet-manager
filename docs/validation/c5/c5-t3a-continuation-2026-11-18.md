# C5-T3A — Güvenli durdurma ve devam notu

18 Kasım 2026. **KULLANICI TALEBİYLE DURDURULDU / PARTIAL. T3A kabulü yoktur.**
Durdurma talebinden sonra yeni geliştirme veya test başlatılmadı. Commit,
push, reset, clean, stash, checkout ve dosya silme yapılmadı.

## Süreç ve Git durumu

- Aktif T3A Docker/Gazebo/ROS/test süreci kalmamıştı; ek sinyal göndermek
  gerekmedi. Başka worktree veya kullanıcı sürecine dokunulmadı.
- İki canlı koşunun simulation (Gazebo/Nav2), FM, command bridge, üç Executor,
  üç Battery Simulator ve observer süreçleri kontrollü kapanmıştı. Her iki
  simulation kaydı `SIMULATION_SHUTDOWN clean=true` içerir.
- `replan-a1` alt süreçleri 0 ile kapandı; test runner timeout nedeniyle 1'di.
  `replan-a2` runner 0; normal alt süreçler 0. Bilerek aynı DB ile denenen
  `manager_restart` 1 / `ScenarioResetRequired` verdi; bu beklenen rettir.
- Dal: `codex/c5-t3a-native-permit-context`. HEAD, `origin/main` ve salt okunur
  `ls-remote` sonucu **f94ed776c616334c17a3ce6b79e4bf5192d75508**.
  Index boş; bütün T3A kaynakları çalışma ağacında, commit edilmemiştir.

[Durdurma envanteri](c5-t3a-continuation-2026-11-18/stop-state.json) ·
[Belgeleme öncesi Git status](c5-t3a-continuation-2026-11-18/git-status-before-documentation.txt).

## Korunan değişiklikler

**7 modified + 12 untracked = 19 kaynak/test dosyası** korundu. Bu devam
notu, harita bağlantıları ve kanıt arşivi ayrıca eklenmiştir.

| Alan | Kaynaklar / yapılan iş |
|---|---|
| FM | `event_loop.py`, `schema.sql`, `store.py`, yeni `persistence/traffic_native.py`, `adapters/native_zero.py`: aynı consumer/transaction ve trafik Outbox'ından değişmez sıfır aktarımı; receiver session/sıra için kalıcı cursor. |
| Native | `c5-b6b7/AuthorizedZero.hh`, `CMakeLists.txt`, yeni `test_live_permit.cc`: opt-in canlı context, tam karar hash'leri, mevcut HMAC/sequence/ticket/lease, imzalı native readback; nonzero yine reddedilir. |
| Executor | `traffic.py`, yeni `native_zero.py`: T2 MovementGate bağlamı eşleşen sıfır zarflarının anahtarsız aktarımı; `send`/APPLIED açılmaz. |
| Ortak yardımcı | Yeni `fleet_config/native_zero.py`: mevcut B6B.7 zarfı, MAC domain ayrımı, immutable karar paketi ve owner-only key okuma. |
| Testler | `test_traffic_protocol.py` fixture eki, yeni `test_native_permit_context.py`, `test_native_permit_ros2.py`. |
| İzole canlı fixture | Yeni `docker/experiments/c5-t3a/{world.py,executor.py,manager.py,live.py,single_plan.xml}`; ayrı gerçek süreçler, native sıfır sürücü, stock Twist bridge mapping'i yok. |

Tam yollar, boyutlar ve SHA-256 değerleri
[source-inventory.json](c5-t3a-continuation-2026-11-18/source-inventory.json)
içindedir. [Tracked diff](c5-t3a-continuation-2026-11-18/tracked-source.diff)
ve [19 dosyanın kaynak snapshot'ı](c5-t3a-continuation-2026-11-18/source-snapshot.tar.gz)
ayrıca saklandı. Snapshot devam için kopyadır; çalışma ağacına otomatik
çıkarılmamalı veya mevcut dosyaların üzerine yazılmamalıdır.

## Mevcut test kanıtları

Yeni koşu başlatılmadan, tamamlanmış loglar kaydedildi. Seçkiler örtüşür;
tek bir benzersiz toplam olarak toplanmaz. Tam depo suite'i çalıştırılmadı.

| Tamamlanan seçki | Sonuç |
|---|---|
| Geniş host regresyonu | **363 PASS**, exit 0 |
| Native/ROS tipli Python seçki | **72 PASS**, exit 0 |
| Temiz B6B.7 native build / CTest | **3 PASS**, exit 0; eski iki test + yeni live-context component testi |
| Ara hedefli Python seçki | **156 PASS**, exit 0 |
| İlk Python denemesi | **2 FAIL / 154 PASS**: trafik Outbox `PENDING` kısıtı yakaladı. Kısıt gevşetilmedi; native ACK ayrı immutable bağlı kayıt olarak tutuldu. |

### Canlı denemeler

- **replan-a1 / domain 211 — BAŞARISIZ:** Trafik geometrisi güncel ilk
  RobotStatus'lar gelmeden kuruldu; mevcut STALE koruması robotları blokladı.
  Permit `ROBOT_BLOCKED` ile reddedildi, native context kurulmadı. Scheduler
  o anda uygun Beta'yı seçti; fixture'ın Alpha varsayımı da yanlıştı. Bu bir
  Scheduler politikası değişikliği gerektirmez. Blokaj kaldırılmadı.
- **replan-a2 / domain 212 — SINIRLI OLUMLU KOŞU:** Başlangıç sırası
  düzeltildi; trafik geometrisi güncel gerçek durumlar geldikten sonra
  kuruldu ve fixture Scheduler'ın gerçek atamasını izledi. Script kendi
  `PASS_REAL_FM_NATIVE_ZERO_ONLY` sonucunu verdi: gerçek FM/native sıfır ACK,
  replan/revoke ve aynı DB ile FM restart reddi gözlendi. Native örnek sayısı
  1.220 + 1.216 + 1.213; `movement_authorized=false`, `physical_stop=UNKNOWN`,
  `ownership_release=false`. **Bu tek koşu tamamlanmış T3A entegrasyon kabulü
  değildir; durdurma talebinden sonra yeniden test veya bağımsız son kabul
  incelemesi yapılmadı.**

`negative`, `executor-loss`, `bridge-loss`, `fm-loss` senaryoları yazılmıştır,
**HENÜZ CANLI ÇALIŞTIRILMADI**. İlgili hatalı imza/kimlik/generation, replay,
rollback ve yanıt kaybı kontrollerinin unit/component kanıtı canlı süreç
kaybı kanıtı yerine kullanılamaz.

Loglar ve SQLite/ROS/native kanıtları [checks](c5-t3a-continuation-2026-11-18/checks/),
[live](c5-t3a-continuation-2026-11-18/live/) ve
[native-build](c5-t3a-continuation-2026-11-18/native-build/) altında kayıpsız
korunur. İlk hatalar ve başarısız koşu silinmedi. Orijinaller `/tmp/c5-t3a-*`
altında bırakıldı; native binary/build dizini `/tmp/c5-t3a-native-20261118`.
Provision anahtarları arşive alınmadı.

## Güvenlik sınırı ve devam

Varsayılan launcher, ürün Executor node'u, Scheduler, STALE/safety eşikleri
ve `Lease.hh` taban ile aynı kaldı; kaynak karşılaştırması stop-state
kaydındadır. Native nonzero yetkisi açılmadı. Yeni native bağ yalnız açık
fixture'dadır; varsayılan `start_demo.sh`, PeerRobotLayer ve native deney
aktivasyonu değiştirilmedi. Fiziksel release ve hold/resume tamamlanmadı.
Native imzalı ACK geçmiş doğrulamayı anlatır; süreçler arası gerçek atomiklik,
güncel fiziksel duruş veya hareketten frenleme kanıtı değildir. Sağlık/duruş
zarfı, key/OS rol izolasyonu ve kayıp/restart matrisi açık bağımlılıklardır.

**Sonraki oturumun ilk adımı:** Yeni kullanıcı devam talebinden sonra mevcut
kaynakları koruyarak, boş kanıt dizini ve ayrı domain/partition ile **güncel
RobotStatus geldikten sonra trafik geometrisi kurulan, Scheduler'ın gerçek
atamasını izleyen temiz canlı senaryoyu** çalıştırmak. Eski blokaj, DB veya
receiver context'i yeniden açılmamalı. Commit/push için yeni talimat olmadan
işlem yapılmamalı.

Tek devam promptu:

> C5-T3A devam notunu oku; mevcut değişiklikleri koru. Önce süreç envanterini
> kontrol et, sonra güncel RobotStatus sonrası trafik geometrisi kuran ve
> Scheduler'ın gerçek atamasını izleyen tek temiz izole canlı senaryoyla
> devam et. Native yalnız sıfır ve varsayılan kapalı kalsın; commit/push yapma.
