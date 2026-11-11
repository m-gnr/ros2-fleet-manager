# C5 Git kaynak checkpoint ve push denetimi

12 Kasım 2026. Başlangıç envanteri 11 Kasım, devam ve checkpoint işlemleri 12 Kasım. Kapsam yalnız Git denetimi, kaynak checkpoint’i ve normal feature push’tur. Ürün kodu, config değerleri, Nav2 ayarları, mevcut test sonuçları ve Aşama 1.3 kabul metni yeniden yazılmadı. **Aşama 2 başlatılmadı; final ürün kabulü verilmedi.**

## Başlangıç ve korunan çalışma ağaçları

C5: `/Users/murat/develop/ros2-fleet-manager-c5-warehouse-grid`, dal `feat/c5-warehouse-grid-layout`, HEAD `174ff21e01c898bf12c857b2d3b1a854a8cd8894`. `git fetch origin` sonrası remote HEAD `30373ff6ec6661130e0b2e78b382fdc768eda58c`; ahead/behind **14/0**. Devam sırasında aynı durum ve boş index doğrulandı; önceki aşamaların commit’leri tekrar oluşturulmadı.

Ana worktree `main` ve `origin/main`: `32e23fce62026a1d50aa2f04e85c8c38a6ee5d76`. Ana worktree’deki 9 kullanıcı dosyasının içerik SHA-256 değerleri başlangıçta alındı. Diğer çalışma ağaçlarında kullanıcı değişikliği yoktu. Hiçbir worktree silinmedi; merge/rebase/reset/clean/force push yapılmadı.

| Worktree (ortak kök `/Users/murat/develop/`) | Başlangıç HEAD | Değişmiş/izlenmeyen dosya |
|---|---|---:|
| `ros2-fleet-manager` | `32e23fce6202` | 9 |
| `ros2-fleet-manager-c5-2-safe-task-management` | `b7fcb05c3cbc` | 0 |
| `ros2-fleet-manager-c5-3d-dashboard` | `72e500eb84e0` | 0 |
| `ros2-fleet-manager-c5-dashboard` | `76a80abb5d35` | 0 |
| `ros2-fleet-manager-c5-ui-polish` | `b7fcb05c3cbc` | 0 |
| `ros2-fleet-manager-c5-warehouse` | `b682888ca4c0` | 0 |
| `ros2-fleet-manager-c5-warehouse-functional` | `b7b144b78da0` | 0 |
| `ros2-fleet-manager-c5-warehouse-grid` | `174ff21e01c8` | 1664 |
| `ros2-fleet-manager-c5-warehouse-presentation` | `b21c642a1737` | 0 |
| `ros2-fleet-manager-c5-warehouse-zones` | `23823f6f53bc` | 0 |
| `ros2-fleet-manager-multi-robot` | `7cf6e7edf31b` | 0 |
| `ros2-fleet-manager-nav2-routes` | `f3e39017514b` | 0 |
| `ros2-fleet-manager-visual-upgrade` | `015865403d5b` | 0 |
| `ros2-fleet-manager-visualizer` | `4503c25b7bc1` | 0 |

Dal adlarının tam eşlemesi [komut ekinde](../git-checkpoint-commands-2026-11-12.md) verilir.

## Eksiksiz dosya envanteri

[Başlangıç dosya envanteri](initial-inventory.tsv): 29 **Tracked modified**, 1635 **Untracked**, 1630 **Already committed**. Ayrıca **11131 Ignored** dosya, toplam 244553419 bayt: [grup dökümü ve DB listesi](ignored-summary.json). Ignored alan yalnız `git diff` ile değerlendirilmedi; dosyalar `git ls-files --others --ignored --exclude-standard -z` ile sayıldı, kaynak uzantıları/konumları ve istisnalar incelendi. Bağımsız gerekli kaynak bulunmadı. Kurulu bağımlılıklar ve üretilmiş ROS install dosyaları kaynak yerine geçirilmedi.

| No | Kategori | Başlangıç / checkpoint durumu |
|---|---|---|
| 1 | 30 × 18 YAML, şema, config doğrulama | Tracked modified + Untracked → A |
| 2 | Gazebo SDF / Nav2 harita üretimi | Üretici/raster değişiklikleri + yeni occupancy → A |
| 3 | C5 görev API’si ve katalog | API/publisher modified, runtime/task_ingress untracked → B |
| 4 | SQLite / Outbox | Çekirdek zaten commit; yeni runtime/soket tek consumer bağlantısı → B |
| 5 | 3D depo ve görev ekranı | Modified bileşenler, yeni TaskComposer/Costmap → C |
| 6 | Feedback F1 | Zaten commit `7b2bc82`; yeni commit üretilmedi |
| 7 | Etkin DiffDrive track | Zaten commit `36e0b50`, 0,36 m |
| 8 | Güvenli footprint | Zaten commit `5ca037b`, local/global radius 0,30 m |
| 9 | AMCL beam | Zaten commit `7293256` |
| 10 | Battery lifecycle | Zaten commit `971e586` |
| 11 | Test ve araçlar | Değişmiş probe/run/serve ve testler, untracked stage1/browser araçları → D |
| 12 | Dokümantasyon/kabul | Değişmiş haritalar/diyagramlar, tarihsel raporlar ve küçük özetler → A/B/D |
| 13 | Log/video/ham kayıt | Untracked/ignored kayıtlar yerelde; eski committed arşivler kullanıcı izniyle korunur |
| 14 | Diğer kullanıcı dosyaları | Ana worktree’deki kişisel rapor/PDF/araştırma ve docs değişikliği korundu; checkpoint’e katılmadı |

[Commit listesi ve tam SHA’lar](checkpoint-commits.tsv): A `1406f56`, B `897be3c`, C `fcf8844`, D `b9d8a74`. Her commit öncesi açık dosya listesi, staged diff ve `git diff --cached --check` kontrol edildi. Ürün dosyaları başlangıçtaki içerikleriyle commit edildi. Bu denetim kaydı ayrıca bir docs commit’iyle eklenecektir.

## Yerelde bırakılanlar ve büyük dosyalar

[Yerel dosya ve SHA-256 manifesti](local-only-manifest.tsv) **1608** kaydı listeler: yeni checkpoint’e alınmayan ham kayıtlar, videolar, screenshot’lar, generated world/map/param dosyaları ve **25** ignored çalışma DB’si. Silme/taşıma yapılmadı. `warehouse-30x18/live-routes.json` ve `live-passing.json` ham poz/rota örnekleridir, yerelde bırakıldı. Küçük kontrollü `before/after-fixture.json` ve kaydedilmiş 117 kB costmap, tarayıcı aracının açık test girdileri olarak izlenir; sürekli canlı costmap kabulü değildir.

Mevcut tarihçede 46.368.687 bayt `stage1-2-2026-11-11/raw-evidence.tar.gz`, 18.237.747 bayt `stage1-1-2026-11-11/raw-evidence.tar.gz` ve başka ham arşivler zaten vardı. Kullanıcı, **“Mevcut arşivlerle normal push yap; yeni ham kanıt ekleme”** seçeneğini açıkça onayladı. Bu nedenle geçmiş yeniden yazılmadı ve eski arşivler push’un parçasıdır. [Arşiv içeriği kontrolü](archive-path-check.json), eski 8 arşivde toplam 17 tarihsel SQLite kanıt kopyasını gösterir. Bunlar yeni commit’lerde eklenen DB’ler değildir. Yeni checkpoint’lere `.log`, `.jsonl`, video, `.db/.sqlite*` veya ham arşiv eklenmedi.

## Gizli bilgi kontrolü

[Tarama özeti](secret-scan-summary.json): C5 HEAD tarihçesindeki blob’lar, arşiv üyeleri, mevcut izlenen dosyalar ve yeni kaynaklarda 8880 tarama girdisi / 5403434159 bayt (aynı içeriğin tarihçe/çalışma ağacı tekrarları dahildir). Private key, GitHub/OpenAI token, AWS anahtarı, kullanıcı-parolalı URL ve literal credential atamaları için **eşleşme yok**. Yeni commit dosyalarının ayrı taraması da temizdir. Ignored `.env`/anahtar dosyası bulunmadı. [17 eski SQLite kopyasının metin satırları](archived-sqlite-scan.json) ayrıca bellekte tarandı; eşleşme yok. Paket e-posta metadatası, tarihsel log ve `@` içeren dosya adları kimlik doğrulama anahtarı olarak değerlendirilmedi. Regex taraması bilinmeyen token biçimleri veya PDF/görüntü içindeki tüm kişisel veriler için mutlak yokluk kanıtı değildir. Gizli değerler rapora yazılmadı.

## Yalnız izlenen kaynaklarla yeniden üretim denetimi

**DOĞRULANDI — sınırlı statik/host kapsamı.** `b9d8a7447100206ce8fe31005be33c4906a8b637` için `git archive HEAD` yeni `/tmp/c5-git-audit-20261111/tracked-checkout` dizinine açıldı. Untracked ürün kaynağı kopyalanmadı. Python için önceden kurulu venv ve frontend için önceden kurulu `node_modules` kullanıldı; temiz bağımlılık kurulumu sınanmadı.

- Dört `fleet*.yaml` profili doğrulandı. 30 × 18 profilinden SDF, PGM/YAML harita, occupancy, scene, hedef kataloğu ve robot Nav2 parametreleri üretildi. Scene payload çözülmüş config ile eşit. [Dosya hash’leri ve statik kontroller](static-checks.json).
- Backend görev API/runtime/soket, mevcut SQLite/Outbox, frontend kaynakları ve lockfile’ı; F1, track, footprint, beam ve Battery lifecycle kaynakları Git’te var. Benzersiz gerekli ürün kaynağı Git dışında bulunmadı.
- Host seçkisi: **104 geçti, 1 atlandı, 1 uyarı**. Atlanan Battery shutdown testi ROS 2 Humble gerektirir, başarı sayılmaz. Uyarı Starlette/httpx deprecation. TypeScript/Vite build **geçti**. 132 Python dosyası AST, frontend `.mjs` araçları `node --check`, `run.sh` `bash -n` ile kontrol edildi.

**HENÜZ TEST EDİLMEDİ — temiz makinede tam sistem kurulumu/canlı yeniden üretim.** Aşağıdaki dış önkoşullar temiz checkout’ta hazır gelmez:

1. Python/Node çalışma zamanları, requirements/lockfile bağımlılıkları, Chrome/Playwright tarayıcısı. Bu turda bağımlılıklar yeniden indirilmedi.
2. ROS 2 Humble, Fortress, DART, OGRE2/EGL, bridge, Nav2 ve Docker image zinciri. `docker/simulation-c5/Dockerfile` C3.3.3 backend → Nav2 → lidar → simulation/DDS image’larına bağlıdır. Yerel `ros2-fleet-c5-validation:humble-fortress` etiketi Git nesnesi değildir. Sabitlenmiş apt sürümlerinin yeniden erişilebilirliği ve image build’i bu görevde doğrulanmadı. [Compose kılavuzu](../../../../docker/compose/README.md).
3. `interfaces/` ile Executor/Battery ROS paketlerinin `colcon` derlemesi. Tarihsel komutlardaki yerel `/types`/`install` mount’u yeni checkout’ta önce oluşturulmalıdır; ignored install ağacı kaynak değildir.
4. `stage13_plot.py`, `matplotlib` import eder; requirements dosyalarında bu yardımcı çizim bağımlılığı tanımlı değildir. İlgili yardımcı aracı çalıştırmak için ayrıca ortam hazırlığı gerekir; bu Git görevinde bağımlılık dosyası değiştirilmedi.
5. Ham tarayıcı/ROS kaydı, screenshot/video ve DB’ler yeni commit’lere alınmadı. Tarihsel raporlardaki bunlara giden bazı bağlantılar yalnız yerelde açılır. Tam tarihsel Chrome komutunun opsiyonel `live-routes.json` girdisi yereldedir; temiz checkout’ta yeniden Nav2 kaydı alınmalı veya opsiyonel canlı kayıt karşılaştırması verilmemelidir. Kaynak araç `run.sh routes <profil>` bu kaydı tekrar üretebilir; bu görevde çalıştırılmadı.

## Push ve açık Git riskleri

Normal push yalnız `origin feat/c5-warehouse-grid-layout` hedefine yapılır. Son fetch ve ancestor kontrolü push’tan hemen önce tekrarlanır; divergence olursa işlem durur. Bu docs commit’inden sonraki **yerel ve GitHub SHA eşleşmesi** son yanıtta ve yerelde üretilecek `push-verification.json` makbuzunda kaydedilir; kendi commit SHA’sını içine yazma döngüsü oluşturulmaz. Makbuz yeni bir ürün kaynağı değildir.

Açık riskler: mevcut tarihçedeki büyük ham arşivler/depo boyutu; GitHub’a gitmeyen ham kanıta bağlı tarihsel bağlantılar; tanımlanmamış yardımcı matplotlib bağımlılığı; temiz bağımlılık/image kurulumu ve canlı sistem yeniden üretiminin bu görev kapsamı dışında olması. Geçmişteki bridge kapanış bulguları çözüldü sayılmadı. Ana dal/diğer worktree’ler ve kaynak byte’ları push sonrasında tekrar karşılaştırılır.
