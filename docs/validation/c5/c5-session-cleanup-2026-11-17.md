# C5 — Güvenli oturum temizliği ve tek demo cold-start — 17 Kasım 2026

## Sonuç

**PARTIAL — güvenli cleanup ve idle üç robotlu cold-start tamamlandı; sonraki AMCL güncellik kontrolü kalıcı readiness'i doğrulamadı.** Aynı Git deposunun farklı worktree'lerinde çalışan üç eski C5 demo oturumu tespit edildi. Her oturumda görev girişi kapatıldı, görev/robot snapshot'ı alındı, Nav2 iptali gönderildi ve odometri ile poz kararlılığından hareketsiz duruş doğrulandı. Yalnız bu C5 deposuna ait simülasyon oturumları durduruldu. Yeni demo benzersiz session ID ve ROS domain ile açıldı; startup kapısı Alpha/Beta/Gamma AMCL, Nav2 ve TF fazlarının üçünü de `READY` olarak ölçtü. GUI `3/3 TF LIVE` gösterdi. Görev gönderilmedi; API görev listesi boş kaldı.

Sonradan yapılan hareketsiz canlı kontrolde tüm robotların Nav2 lifecycle düğümleri ve `NavigateToPose` action server'ları aktif, TF örnekleri canlıydı. AMCL lifecycle düğümleri aktif kalmasına rağmen `/robot_{alpha,beta,gamma}/amcl_pose` için 4 saniyelik `ros2 topic hz` aralığında yeni örnek gelmedi; kaydedilmiş örneklerin damgası `0.2 s` idi. Observer dosyası `status=READY` geçmiş başlangıç başarısını korurken `current_status=WAITING` gösterdi. Bu yüzden başlangıçta gerçek readiness geçişi doğrulanmıştır; sonradan sürekli AMCL tazeliği **doğrulanmamıştır**. Bu kontrol sırasında görev veya hareket başlatılmadı.

**Gamma kapanış ayrıntısı:** `c5-alpha-beta-gamma-live-retry1-20261117` container'ında güvenli duruş, Docker stop öncesinde doğrulandı. `docker stop --time 35` grace süresinden sonra container `exit 137` ile sonlandı (`OOMKilled=false`, `shutdown.json` oluşmadı). Bu, kontrollü kapanışın kanıtı değildir; Docker'ın grace süresi sonunda container'ı zorla sonlandırdığını gösterir. Öncesindeki duruş doğrulaması başarılı olduğu için güvenli durdurma şartı sağlanmıştı. Container silinmedi; writable layer, volume ve loglar korundu.

## Eski C5 oturumları

| Oturum / container | Kaynak worktree | Domain | API / GUI portları | Kapatma sonucu |
|---|---|---:|---|---|
| `c5-alpha-beta-gamma-live-retry1-20261117` · `0f790865…` | `alpha-beta-stable` | 197 | 21484 / 21486 | Güvenli duruş doğrulandı; Docker stop sonunda **exit 137**, OOM değil; `shutdown.json` yok |
| `c5-alpha-beta-stable-live-20261117` · `ddc92808…` | `alpha-beta-stable` | 199 | 21482 / 21481 | Güvenli duruş doğrulandı; stop exit 0; `shutdown.json` alt süreçlerde 0 |
| `c5-alpha-beta-manual-20261117` · `9735898…` | `alpha-beta-manual` worktree'si | 194 | 21382 / 21381 | Aynı Git ortak deposu ile eşleşti; güvenli duruş doğrulandı; stop exit 0; `shutdown.json` alt süreçlerde 0 |

Üç oturumun API snapshot'larında aktif görev yoktu. Gamma oturumunda bir terminal `FAILED` görev vardı; stable oturumunda bir terminal `FAILED` görev, manual oturumunda dört terminal görev vardı. Aktif görev sayısı tümünde sıfırdı. Alpha'nın bazı eski snapshot'larda `ERROR` görünmesi hareket kanıtı değildi; duruş ölçümü her robot için ayrıca yapıldı.

Her robot için `/navigate_to_pose/_action/cancel_goal` cancel-all isteği gönderildi. Duruş probu odometri örneklerini ve 2 saniyelik poz/yaw kararlılığını izledi; üç robot için hız yaklaşık sıfır ve konum kararlıydı. Sonlandırma öncesi container içindeki kritik süreçlerin PID ve başlangıç zamanları tekrar karşılaştırıldı. Eski C5 API/UI portları kapandı. `c5-v031-stall-20261117` ve `c5-actuator-timeout-20261114` container'ları incelendi: ikisinin de komutu yalnızca `sleep infinity`, ROS/Nav2/Gazebo süreci yoktu; bu yüzden simülasyon oturumu sayılmayıp dokunulmadı.

## Yeni idle demo ve readiness

- Session ID: `c5-20261117T065353Z-77741f4968`
- ROS_DOMAIN_ID: `206`; IGN partition aynı benzersiz session kimliğine bağlı.
- Container: `c5-20261117T065353Z-77741f4968`, running.
- API: `http://127.0.0.1:21482`; GUI: `http://127.0.0.1:21484/`; scene bridge: 21483.
- Kanıt dizini: `/tmp/c5-20261117T065353Z-77741f4968`.
- Başlangıç readiness: `READY`; `required_phases=[amcl, nav2, tf]`; toplam yaklaşık 6.03 s.

| Robot | AMCL | Nav2 | Gerçek TF |
|---|---:|---:|---:|
| Alpha | 3,102 ms | 5,781 ms | 4,124 ms |
| Beta | 3,113 ms | 5,784 ms | 4,130 ms |
| Gamma | 3,120 ms | 6,030 ms | 4,133 ms |

Canlı API snapshot'ında `/api/health` `source=LIVE`; `/api/robots` üç robotu da `IDLE`, telemetry/pose `LIVE` ve `active_task_id=null` gösterdi. `/api/tasks`: `total=0`, `queued=0`, `active=0`. Chrome GUI'de `3/3 TF LIVE`, üç canlı robot kartı ve görev sayısı 0 görsel olarak doğrulandı. Yeni simülasyonda görev POST'u yapılmadı. Demo doğrulama sonrasında çalışır bırakıldı.

Canlı ROS tekrar kontrolünde `/robot_alpha`, `/robot_beta`, `/robot_gamma` için AMCL ve `bt_navigator` lifecycle `active [3]`, `NavigateToPose` action server sayısı 1 ve namespace'li `/tf` örnekleri görüldü. AMCL konu örneklerinin güncelliği tazelenmedi; startup observer `current_status=WAITING` bulgusu bu nedenle readiness'in devamlılığına dair açık sınırlamadır.

## Veri ve kapsam

Cleanup yalnızca runtime kontrol soketini ve eşleşen runtime servislerini etkiledi. Kaynak kodu, YAML, SQLite, log, kanıt dizini, container veya Docker volume silinmedi. Üç eski container stop sonrası Docker'da mevcut kaldı. Gamma container'ında `shutdown.json` bulunmaması exit 137 ile tutarlıdır; temiz kapanış kanıtı olarak yorumlanmadı. Yeni oturumun SQLite içeriğine görev yazılmadı.

Cleanup sahipliği; Compose/container bilgileri, `stage1_run.py` C5 supervisor komutu, `/workspace` bind mount'unun hedef Git `common-dir` ile aynı olması, `/evidence` mount'u, session/ROS domain, API port eşleşmesi, C5 API/task socket/UI imzaları ve container child process listesiyle doğrulandı. Bu sayede farklı worktree aynı projeye bağlanırken başka Git deposu ve ilgisiz ROS/Docker süreçleri korunur.

## Test ve doğrulama

Son koşu: cleanup testleri 12/12, preflight testleri 4/4, toplam 16/16 geçti. Startup readiness testi 3/3 geçti. Filo profili doğrulaması üç robotla geçti. Python compile, shell syntax ve `git diff --check` geçti. Gerçek Docker cleanup üç eski C5 simülasyon oturumunu kapattı; Gamma'da exit 137 istisnası raporlandı. Gerçek cold-start başlangıç readiness'i ve API/GUI/TF doğrulaması geçti; sonradan AMCL güncelliğinin devamı doğrulanmadı. Bu nedenle genel sonuç **PARTIAL**.

Bu kayıt görev yürütme, scheduler, trafik, Nav2 parametreleri veya çarpışma davranışında değişiklik yapmaz. Commit/push yapılmadı.
