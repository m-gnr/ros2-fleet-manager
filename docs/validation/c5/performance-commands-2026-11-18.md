# C5 performans — komut ve ham kanıt eki

18 Kasım 2026, Europe/Istanbul. Workspace `/Users/murat/develop/ros2-fleet-manager-demo`, dal `codex/telemetry-stale-fix`. Komutlar depo kökünden çalıştırıldı. Bunlar bu koşuların kaydıdır; genel kurulum veya nihai üç servisli dağıtım talimatı değildir. [Sonuç ve kabul sınırı](performance-2026-11-18.md).

## İzolasyon ve kaynak koruma

Başlangıçta `docker ps` boştu. Kullanıcının 9228 debug portlu mevcut Chrome oturumu korunup ölçüm için yeni geçici profilli Chrome kullanıldı. Her simülasyon yeni container, `IGN_PARTITION`, ROS domain ve boş DB ile açıldı. Workspace container'a salt okunur bağlandı. Yalnız bu çalışmanın manifest/root/image/env doğrulaması yapılan süreçleri kapatıldı; başka worktree veya oturum temizliği yapılmadı. Eski container'lar silinmedi. Commit/push yoktur.

İlk envanter:

```sh
pwd
git status --short
git branch --show-current
docker ps --format '{{.ID}} {{.Names}} {{.Status}} {{.Ports}}'
```

Başlangıçtaki 2.035 takipli dosyanın SHA-256 manifesti Faz 0 boyunca karşılaştırıldı. Faz 0 bitişinde değişen takipli dosya yoktu. Son karşılaştırmada yalnız bu işin 7 takipli dosyası değişmişti; diğer 2.028 dosya, önceki frontend TF düzeltmesi ve launcher değişiklikleri byte olarak korundu. [Bitiş kontrolü](performance-2026-11-18/preservation.json). Önceki kullanıcı diff'i [Faz 0 source.diff](performance-2026-11-18/phase0/source.diff) içindedir; bizim optimizasyon diff'imiz diye yorumlanmaz.

## Oturumlar

| Oturum | Ölçüm | Sonuç / kanıt |
|---|---|---|
| `c5-perf-20261117T214912Z-d41750a1` | wrapper'sız 3 robot; 35 s minimal, 35 s probe, 150 s hareket, 45 s minimal hareket | Ek ölçüm kontrolü; ilk iki probe penceresi kısmen çakıştı. En çok 2 EXECUTING. [Ham veri](performance-2026-11-18/external-reference/sha256.json) |
| `c5-perf-20261117T220400Z-6ece89b2` | Faz 0; manager zamanlama wrapper'ı; sırayla 25/25/180 s | Standart readiness geçti; 2 EXECUTING + 1 queued. [Özet](performance-2026-11-18/phase0/summary.json), [iç süreler](performance-2026-11-18/phase0/details.json), [ham manifest](performance-2026-11-18/phase0/sha256.json) |
| `c5-perf-20261117T221747Z-b41e671a` | yalnız consumer yield, wrapper'sız, 180 s | 2 EXECUTING; 1/694 HTTP 503. [Özet](performance-2026-11-18/fairness-only/summary.json), [ham manifest](performance-2026-11-18/fairness-only/sha256.json) |
| `c5-perf-20261117T222323Z-0f9e7fb0` | yield + WAL, 180 s + planlanan 220 s uzatma | 3 gerçek hareket ve 3 COMPLETED; park dönüşünde contact guard. [Özet](performance-2026-11-18/fairness-wal/summary.json), [iç süreler](performance-2026-11-18/fairness-wal/details.json), [ham manifest](performance-2026-11-18/fairness-wal/sha256.json) |
| `c5-perf-20261117T223516Z-175dc2e9` | aynı kod + yalnız composition True, 180 s + planlanan 220 s uzatma | 3 gerçek hareket ve 3 COMPLETED; yine contact guard, composition geri alındı. [Özet](performance-2026-11-18/composition/summary.json), [iç süreler](performance-2026-11-18/composition/details.json), [ham manifest](performance-2026-11-18/composition/sha256.json) |

Domain/port/image/mount bilgileri her dizindeki `session.json` ve `inspect.json` dosyalarındadır. Yüzdelikler nearest-rank yöntemiyle hesaplandı. Sabit test portları ürün sabiti değildir.

Beş reddedilen başlangıç ayrıca korunur: [başlangıç listesi](performance-2026-11-18/startup-attempts.json). İlk araç denemesi `startup_readiness` import yolunu bulamadı; geçerli baseline değildir. Sonraki dört denemede launcher'ın güncel readiness kapısı WAITING kaldı; 300 s dolmadan kendi oturumları elle kapatıldı ve görev gönderilmedi. Bunlar 300 s timeout testi veya başarılı başlangıç sayılmaz. Son başarılı Faz 0'da observer wrapper'ı kullanılmadı. Kaynak/ayar veya readiness eşiği gevşetilmedi.

## Ölçüm araçları ve kullanılan çağrılar

Araç sürümleri [arşivde](performance-2026-11-18/tools/start.py) tutulur; ürün bileşeni veya desteklenen demo launcher alternatifi değildir. Çalıştırılırken `/tmp/c5-perf-tools` altındaydılar. `start.py` mevcut `scripts/c5_demo_start.py` fonksiyonunu çağırır, standart config/reset/readiness kapılarını kullanır; `--instrumented` yalnız ölçüm wrapper'ını ekler. Son arşiv sürümünde yabancı workspace manifestini reddeden ek assertion vardır. `stop.py` yalnız aktif manifestteki ve mount/env/image kimliği doğrulanan kendi container/Vite sürecini kapatır. Bu tek-oturum araçları eşzamanlı iki çalıştırma için tasarlanmamıştır.

Kullanılan temel çağrılar:

```sh
python3 /tmp/c5-perf-tools/start.py --instrumented
python3 /tmp/c5-perf-tools/baseline_sequence.py
python3 /tmp/c5-perf-tools/summary.py /tmp/c5-perf-20261117T220400Z-6ece89b2
python3 /tmp/c5-perf-tools/details.py /tmp/c5-perf-20261117T220400Z-6ece89b2
python3 /tmp/c5-perf-tools/stop.py
```

`baseline_sequence.py` launcher başarı kaydını bekledi; `idle-minimal 25 minimal` → `idle-probes 25 probes` → `baseline-three-moving 180 chrome submit` çağrılarını birbirleri bittikten sonra yaptı. Ana görevli koşularda Chrome 15 s ısındı, ardından katalog/API üzerinden üç MEDIUM görevi gönderildi. UUID aynı tutularak 503 isteği yeniden denenebildi; fazladan görev kimliği üretilmedi.

Yield koşusu:

```sh
python3 /tmp/c5-perf-tools/start.py
python3 /tmp/c5-perf-tools/moving_sequence.py fairness-uninstrumented
```

WAL ve composition koşuları:

```sh
python3 /tmp/c5-perf-tools/start.py --instrumented
python3 /tmp/c5-perf-tools/moving_sequence.py fairness-wal
python3 /tmp/c5-perf-tools/run_window.py wal-tail 220 chrome
python3 /tmp/c5-perf-tools/stop.py

python3 /tmp/c5-perf-tools/start.py --instrumented
python3 /tmp/c5-perf-tools/moving_sequence.py composition
python3 /tmp/c5-perf-tools/run_window.py composition-tail 220 chrome
python3 /tmp/c5-perf-tools/stop.py
```

İkinci blokta `serve.py` için yalnız composition bool'u geçici True idi; sonrasında False'a geri döndürüldü. Denenmiş [patch](performance-2026-11-18/composition/enable-composition.patch) `git apply --check` kontrolünü geçti; teslimde uygulanmış değildir. `matched.py`, iki koşuda ilk 3 EXECUTING sonrası 20 sim-s'yi ayrıca eşledi.

Her görevli pencerede:

- `sample.py`: Gazebo `/world/warehouse_grid/stats` JSON; 100 ms snapshot yaşı/sequence yoklaması; 1 s `/proc` CPU/RSS/thread context-switch ve cgroup memory/cpu/pressure örneklemesi.
- `ros.py`: ayrı salt okunur ROS node; kaynak damgası, alım monotonic/UTC, Clock/Odometry/TF/physical/AMCL/scan. Clock ve sensor QoS küçük kuyruklu alıcı örneklemesidir; tüm yayınların kayıpsız yakalandığı iddia edilmez. Yayın damgası sim-s, alım aralığı duvar-s olarak ayrılır.
- Mevcut `scripts/c5_telemetry_probe.py`: 250 ms `/api/fleet`, bağımsız WebSocket; 503, scene, ürün ve heartbeat kayıtları.
- `chrome.mjs`: gerçek headless Chrome, **varsayılan Metal renderer**; 250 ms DOM STALE, WS, long task ve 50 ms timer gecikmesi. SwiftShader zorlanmadı. Kullanıcının açık Chrome profili değiştirilmedi.
- `runtime_probe.py`: yalnız manager'da gerçek COMMIT/BEGIN/transaction, event türü/süresi/kuyruk, async loop lag, gerçek Nav2 sorgu süresi ve publisher write zamanı. Çıktı saniyede bir ayrı dosyaya yazılır. Transaction süresi domain işini de içerir; COMMIT ayrıca ölçülür. Yazma sonu kayıtlarında ana pencereler için publisher hatası görülmedi.

Wrapper'sız ilk hareket referansının son bölümünde ek profiler:

```sh
docker exec c5-perf-20261117T214912Z-d41750a1 /tmp/py-spy record \
  --pid 655 --rate 20 --duration 25 --format raw --nonblocking \
  --output /evidence/manager-moving-profile.txt
```

py-spy 0.4.3 ARM64 binary'si yalnız ölçüm container'ının `/tmp` alanına kondu. Nonblocking örnekleme süreci durdurmaz; örnek hatası olabileceği için tek başına kesin süre/CPU atfı yapılmadı. Ana thread 484 örneğinin 317'si COMMIT stack'indeydi. Sonraki wrapper gerçek çağrı sürelerini ayrıca ölçtü.

Ölçüm etkisi hareket altında tümüyle ayrıştırılmadı. Sıralı boşta kontrolü yaklaşık %4,3 RTF farkı verdi; bu tek sıra host/ısınma etkisini ayıramaz. Ek ROS/Chrome olmadan 45 s hareket referansında da 17,4 s publisher aralığı görüldü. Gazebo/TF'deki her duraksama measurement overhead'den bağımsız sayılmaz. Contact'ın probe'suz üçlü karşılaştırması **yapılmadı**.

## Test komutları ve gerçek sonuçları

```sh
python3 -m pytest tests/test_fleet_manager_outbox.py tests/test_ros2_route_resolver.py -q
python3 -m venv --system-site-packages /tmp/c5-perf-test-venv
/tmp/c5-perf-test-venv/bin/python -m pip install --disable-pip-version-check -r requirements-c5-test.txt
/tmp/c5-perf-test-venv/bin/python -m pytest tests/test_c5_dashboard.py -q
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
  /tmp/c5-perf-test-venv/bin/python -m pytest tests -q
git diff --check
```

İlk yeni fairness testi eski kodda 1 FAIL; işlem sonrası yield ile ilgili seçki 121 PASS oldu. Yeni WAL okuyucu testi eski modda 1 FAIL (`database is locked`); WAL sonrası ilgili seçki **122 PASS**. Dashboard **8 PASS**. İlk host toplama denemeleri eksik FastAPI/PYTHONPATH nedeniyle kaldı; yalnız `/tmp` test venv'i ve komut ortamı düzeltildi. Ürün gereksinimleri/image değişmedi.

Son tam host sonucu: **570 PASS / 2 FAIL / 23 SKIP**. [Tam log](performance-2026-11-18/checks/host-final.log). İki kalan test ve başlangıç kanıtı raporda ayrıdır; tarihsel hash manifesti/5-sensor beklentisi değiştirilmedi.

Native test ayrı, simülasyonsuz, benzersiz ROS domain'li, workspace/cache salt okunur bağlanan `--rm` container'da çalıştı. Tam argüman dizisi [komut JSON'unda](performance-2026-11-18/checks/native-tests-final-command.json). Seçki: Outbox, dashboard, route resolver, status subscriber, action client ve Outbox sender. İlk native çağrıda 139 PASS / 5 FAIL; root pytest capture'a log yayılmaması nedeniyle dört log assertion'ı ve log bekleyen bir rollback testi kaldı. Tanı probe'u logger `propagate=False` durumunu gösterdi. Yalnız test çağrısında `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` ile tekrar **144 PASS / 0 SKIP / 1 deprecation warning** verdi. [Son log](performance-2026-11-18/checks/native-tests-final.log), [ilk log](performance-2026-11-18/checks/native-tests.log). Ürün logger, timeout veya güvenlik ayarı değiştirilmedi. Bu unit seçki tam ROS/Gazebo güvenlik qualification'ı değildir.

## Contact ve kapanış kayıtları

Kontrol: [unsafe-contact](performance-2026-11-18/fairness-wal/live/unsafe-contact), [ros.jsonl.gz](performance-2026-11-18/fairness-wal/live/ros.jsonl.gz), [shutdown.json](performance-2026-11-18/fairness-wal/live/shutdown.json).

Composition: [unsafe-contact](performance-2026-11-18/composition/live/unsafe-contact), [ros.jsonl.gz](performance-2026-11-18/composition/live/ros.jsonl.gz), [shutdown.json](performance-2026-11-18/composition/live/shutdown.json).

İki 220 s uzatma güvenli senaryo PASS'i değildir: contact guard koşuyu kapattı; sampler/ROS probe hedef container kapanırken `137`, API/Chrome probe kalan gözlem süresi sonunda `0` verdi. Bu `0`, senaryonun başarılı olduğu anlamına gelmez. Docker OOM işareti false'tur. WAL kontrolünde Gazebo shutdown sırasında zorla sonlandırma, önceki bazı manuel kapanışlarda simulation nonzero vardı; bunlar temiz kapanış kabulü sayılmadı. Composition'ın görev sonrası endpoint audit'i de container kapanması nedeniyle `137` ile kesildi; ilk lifecycle/parametre/action audit'i dışında ek endpoint kabulü çıkarılmaz.

DB yedekleri `fleet.sqlite3.gz`, ölçümler `*.jsonl.gz`, process logları `*.log.gz` olarak saklanır. Dört DB backup'ı read-only açılarak integrity/foreign-key kontrolü yapıldı: [sonuç](performance-2026-11-18/database-checks.json). Bu çökme sonrası otomatik replay veya güç kesintisi kabulü değildir.


## Commit öncesi yeniden kontrol — 18 Kasım 2026

Kullanıcının sonraki açık talimatıyla mevcut düzeltmelerin commit/push teslimi hazırlandı; yukarıdaki “commit/push yapılmadı” ifadeleri önceki ölçüm oturumunun tarihsel durumudur. Yeni özellik veya park düzeltmesi yapılmadı. Depo kökünden yeniden çalıştırılan kontroller:

```sh
python3 -m pytest tests/test_fleet_manager_outbox.py tests/test_ros2_route_resolver.py -q
npm --prefix frontend run build
C5_UI_PORT=21620 C5_API_PORT=21618 npm --prefix frontend test -- --grep 'product-only outage|keeps product and TF validity separate' --workers=1
python3 -m unittest discover -s tests -p 'test_c5_session_cleanup.py'
git diff --check
git fetch origin
git rev-parse HEAD origin/main
git rev-list --left-right --count origin/main...HEAD
git diff HEAD -- docker/simulation-warehouse-grid/serve.py
```

Sonuç: Outbox/rota **122 geçti**, frontend build geçti, hedefli Playwright **2 geçti**, oturum temizliği **12 geçti**, whitespace kontrolü geçti. Sahte WebSocket testi sırasında canlı olmayan katalog API'sine Vite proxy `ECONNREFUSED` verdi; iki test de başarılıdır. Üç launcher/probe Python dosyası `ast.parse` ile sözdizimi kontrolünden geçti. Kalıcı ölçüm arşivinin `all-sha256.json` girdileri SHA-256 ile tekrar doğrulandı; uyuşmazlık yok.

Fetch sonrası başlangıç HEAD ve origin/main birlikte `9d67bd98ee6a9b7fce5e7335941634e728b80075`, ayrışma sayısı `0 0` idi. Nav2 `serve.py` HEAD ile aynı, `use_composition:=False`; arşivdeki True patch yalnız deney kanıtıdır ve uygulanmadı. Build/cache/geçici dosyalar teslim kapsamına alınmaz. Tam host/native ve canlı simülasyon testleri bu teslim kontrolünde yeniden çalıştırılmadı; yukarıdaki tarihsel sonuçlar değişmedi. Park çarpışması açık, tam güvenlik kabulü yoktur.

Staging sonrasında tam `git diff --cached --check`, ham pytest logları ve arşivlenmiş `source.diff` bağlam satırlarındaki whitespace nedeniyle uyarı verdi. SHA manifestine bağlı tarihsel ham kanıtlar değiştirilmedi. `git diff --cached --check -- . ':!docs/validation/c5/performance-2026-11-18'` ile arşiv dışındaki kaynak, test ve raporlar geçti.
