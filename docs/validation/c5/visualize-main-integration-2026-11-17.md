# Visualize → main regresyon karşılaştırması

17 Kasım 2026. Kontroller, temiz `codex/visualize-main-integration` worktree’sinde `origin/main` `6c355c47244adbb820bad1d8b5b8e71a32bc7b1c` tabanı ile `feature/visualize` birleştirilerek yapıldı. `origin/main` üzerindeki üç robotlu kararlı C5 commit’i doğrulandı. Yerel `main` worktree’sine ve oradaki commit edilmemiş C5 deneylerine dokunulmadı. GitHub’a push yapılmadı.

## Üç Playwright hatasının kök nedeni

| Hata | `origin/main` karşılaştırması | Kök neden ve sonuç |
|---|---|---|
| GLB beklenirken `grid` | Aynı test `origin/main` üzerinde de `grid` nedeniyle başarısız. | Güncel doğrulanmış depo profili statik grid’i kullanıyor; testin `.glb`/GLB yükleme beklentileri eski. Grid’i koruyup GLB’ye özgü testleri grid profili, kamera kontrolü, TF ve işaretler üzerinden doğrulayacak şekilde yeniledim. |
| Kamera değerleri `NaN` | Kamera testi `origin/main` üzerinde geçti. | Visualize grid’inde boş `parking-bays` için sıfır elemanlı `InstancedMesh` üretiliyordu. Bu nesnenin boş sınırları depo bounds hesabını bozup kameraya geçersiz değer taşıyordu. Boş kutu listesinde mesh oluşturmama ve layout effect’te güvenli çıkış ekledim. Kamera testi PASS. |
| `WAITING FOR TF` beklenmeyen sonuç | Aynı TF testi `origin/main` üzerinde de başarısız: eski `1 / 2 TF LIVE` beklentisi yerine `WAITING FOR TF`. | UI göstergesi yalnızca robotların tümü canlı olduğunda `n/n TF LIVE` gösteriyor; kısmi canlılıkta `WAITING FOR TF` tasarım davranışı. Test artık tek canlı ve tek bayat robotu ayrı ayrı doğruluyor. |

Diğer eski dashboard beklentileri de grid profilinde GLB raf ölçüleri, statik HTML işlem noktaları ve “seçili olmayan robot gizlenir” varsayımlarına dayanıyordu. V1–V6 davranışını değiştirmeden grid sahnesinin bounds/dekor/tooltip, seçili etiket ve etkin görev noktalarını doğrulayacak şekilde güncellendiler. Ürün akışı kesilmesi yeni websocket bağlantısı başlattığından test yeni bağlantıda snapshot/TF el sıkışmasını kullanıyor.

## Kontroller

| Kontrol | Sonuç | Kanıt ve sınır |
|---|---|---|
| Frontend Playwright tam koşu | **PASS** | `34 passed`, 1 worker. Fixture tabanlı browser koşusu; backend başlatılmadığı için task-catalog API/WS proxy bağlantı uyarıları beklendi. |
| Frontend production build | **PASS** | TypeScript + Vite build. Zod paketindeki Rollup `@__PURE__` açıklama uyarıları build’i durdurmadı. |
| Filo YAML / gamma profil doğrulaması | **PASS** | `fleet_config` 3 robotlu depo YAML’ını doğruladı. `robot_gamma` tam bir kayıt, namespace’ler benzersiz; başlangıç pozu `park_3` ile `(13.5, 4.0, π)` eşleşiyor. |
| Backend, scheduler, outbox, görev/istasyon/şarj/trafik/motion gate ve Executor testleri | **PASS / PARTIAL** | İzole Humble C5 imajında 255 geçti, 8 skip. Skip’ler test imajında `fleet_interfaces` kurulumuna bağlı Executor ROS node fixture’larıdır; bu nedenle tüm Executor node testleri PASS sayılmaz. |
| ROS TF okuyucu | **PASS** | Entegrasyon kaynağından salt okunur mount ve Humble IDL overlay ile 4/4 geçti. Shared `/tf`, namespaced TF, iki tampon ve rewind senaryoları dahil. |
| Warehouse profile generator | **PASS** | `generate_warehouse_profile.py --check`. |
| Güvenlik hareket zinciri | **NOT TESTED** | Görev atama/Nav2 veya park/şarj hareket komutu gönderilmedi. Mevcut hareket kabul kaydı güvenli yetkilendirme zincirini doğrulamıyor. |
| Üç robotlu yeni Gazebo spawn ve canlı WS | **NOT TESTED** | Bu koşuda yeni Gazebo başlatılmadı; browser koşusu simüle WebSocket fixture’ları kullandı. Önceki V2.3 canlı kanıtı tarihsel kapsamdır, bu entegrasyon koşusuna ait değildir. |

## Entegrasyon durumu ve sınırlar

`backend/dashboard`, `backend/fleet_manager` ve `ros2_ws/src/fleet_robot_executor` kaynaklarında `origin/main`’e göre değişiklik yok; C5 görev, Executor, Scheduler, Nav2 ve güvenlik kodu korunmuştur. Ana akış düzeltmesi (5 saniyelik reconnect uyarısı) da değiştirilmedi. `stage1_observer.py` yalnız gerekli DB tablolarının tamamı mevcut olunca snapshot okumaya başlıyor. TF okuyucu namespaced abonelikleri korurken ortak `/tf` aboneliği ekliyor ve robot kimlik filtresini `RobotReader` üzerinde tutuyor.

Filo YAML çakışması V2.3’te doğrulanmış park slotlarına göre çözüldü: alpha/park_1 `(13.5, 1.5)`, beta/park_2 `(13.5, 2.75)`, gamma/park_3 `(13.5, 4.0)`, yaw `π`. `robot_gamma` için çift kayıt veya profil kaybı yoktur. Görsel depo sınırları ve park bölgesi de bu slotları kapsar.

`origin/main` ile Visualize birleştirmesi yalnız geçici entegrasyon branch’inde tamamlandı; yerel merge commit’i `65e6bd6260a31386f7ec2a932b9f386b19d1a640` (`codex/visualize-main-integration`) olarak oluşturuldu. `main` ve `origin/main` değişmeden durur. Kullanıcının GitHub push onayı bekleniyor. Hareket zincirinin **NOT TESTED** olması sebebiyle görev/park/şarj canlı kabulü veya hareket izni sonucu çıkarılmamalıdır.

## Son canlı kabul denemesi — 17 Kasım 2026

Bu entegrasyon worktree’sinde frontend production build tekrar **PASS**, beş hedefli Playwright testi tekrar **PASS (5/5)** oldu. Önceki tam Playwright koşusunun sonucu **PASS (34/34)** olarak kaldı.

Yeni izole üç robotlu Gazebo oturumu başlatılmadı. Başlatıcının normal yolu ortak Git deposundaki eski C5 oturumlarını temizleyebilir; bu nedenle mevcut oturumları korumak için temizlik atlama seçeneği gerekir. Kontrol anında başka worktree’lere bağlı iki aktif Gazebo/C5 oturumu yaklaşık 1.64 GiB + 1.73 GiB bellek ve toplamda birden fazla CPU çekirdeği kullanıyordu. Üçüncü simülasyonu eklemek çalışan demoları etkileyebileceğinden başlatma yapılmadı ve mevcut süreçlere müdahale edilmedi.

Bu sebeple entegrasyon commit’inden Alpha/Beta/Gamma spawn, gerçek TF ve WebSocket, Chrome 3/3 LIVE, park koordinatları ve 3D sahne **NOT TESTED** durumundadır. Başka worktree’den çalışan API salt okunur incelendi; entegrasyon kanıtı sayılmadı. Hareket yetkisi doğrulanmadığından görev veya hareket komutu gönderilmedi (**NOT TESTED**).

GitHub `refs/heads/main` son salt okunur sorguda `6c355c47244adbb820bad1d8b5b8e71a32bc7b1c` döndürdü; entegrasyon dalı bu commit’in üzerinde yerel olarak dört commit ilerideydi. Zorunlu canlı kabul kalemleri doğrulanmadığı için push yapılmadı. HEAD `548792574a19c46dc3feb43c749907f5d6009e3d` durumunda kaldı; bu son doğrulama notu çalışma ağacında commit edilmemiştir.

## Temiz canlı kabul — 17 Kasım 2026

Kullanıcının açık kapatma izniyle çalışan proje konteynerleri ve ilişkili Vite süreçleri durduruldu; konteynerler, kalıcı volume’ler ve önceki `/tmp` kanıtları silinmedi. Tek yeni oturum `c5-20261117T143336Z-7006b7b414` (ROS domain 209) olarak başlatıldı ve kontrollerden sonra `docker stop --timeout 60` ile exit code 0 alarak kapandı. Başlatıcı ilk iki denemede eksik ROS overlay’i ve container içinden `scene` host çözümlemesi nedeniyle başarısız oldu; [scripts/c5_demo_start.py](../../../scripts/c5_demo_start.py) içinde overlay derleme ve `scene:127.0.0.1` eşlemesi eklenince son oturum READY oldu. Başlangıç preflight’ı `fleet_interfaces` + `fleet_perception` 2/2 derlemesini, eklenti kaydı/kütüphane yüklemesini ve import/argüman kontrollerini PASS doğruladı.

| Kontrol | Sonuç | Kanıt ve sınır |
|---|---|---|
| Gerçek üç robot spawn ve reset | **PASS** | Gazebo readiness Alpha/Beta/Gamma için AMCL, Nav2 ve TF fazlarını READY verdi. Fiziksel reset kanıtı park slotlarına ölçülen poz hatasını yaklaşık `1.41e-7 m` olarak kaydetti. |
| `/tf` ve namespace TF | **PASS** | Salt okunur ROS subscriber ortak `/tf` ve `/robot_alpha/tf`, `/robot_beta/tf`, `/robot_gamma/tf` üzerinden robot frame’lerini aldı; `/tf` yayıncısı ve dört subscriber görüldü. |
| API/WebSocket | **PASS** | API health `LIVE`; WebSocket `fleet.scene.v1` üzerinden üç robot roster’ı, `scene_connected`, üç `data_status=LIVE` ve üç robot için poz güncellemeleri geldi. |
| Chrome canlı filo | **PASS** | Entegrasyon Vite portunda Chrome `3/3 TF LIVE` gösterdi. Üç robotun ürün telemetrisi LIVE, görev sayısı sıfır ve hepsi IDLE idi. |
| Gamma ve park slotları | **PASS** | YAML doğrulaması `robot_gamma` için tek kayıt gösterdi. Canlı pozlar alpha `(13.5, 1.5)`, beta `(13.5, 2.75)`, gamma `(13.5, 4.0)`, yaw `π`; Chrome park etiketlerini gösterdi. |
| V1–V6 3D sahne | **FAIL** | Chrome `3D görünüm için WebGL desteği gerekiyor` fallback’ini gösterdi. Bu browser oturumunda WebGL sahnesi render edilmedi; depo geometrisi ve kamera görünümünün canlı görsel kabulü yapılmış sayılmaz. Tasarım veya kontrol devre dışı bırakılmadı. |
| Frontend build ve hedefli Playwright | **PASS** | `npm run build` başarılı; beş hedefli test geçti. Önceki tam koşu 34/34 PASS kaydı geçerlidir. |
| Görev/hareket güvenliği | **NOT TESTED** | Görev, Nav2 veya hareket komutu gönderilmedi; yalnız reset/park başlangıç durumu ve telemetri gözlendi. |
| Kontrollü kapanış | **PASS** | Yeni simülasyon konteyneri exit code 0 ile kapandı; oturum kanıtı `/tmp/c5-20261117T143336Z-7006b7b414` altında korundu. |

Chrome WebGL kabulü başarısız olduğu için bu çalışmada entegrasyon commit’i push edilmedi. Başlatıcı düzeltmeleri ve bu kayıt entegrasyon dalında yerel bir commit olarak saklandı; sonraki canlı WebGL kabulüne kadar GitHub’a gönderilmedi. `chrome://gpu` tanı sayfası tarayıcı URL politikası tarafından engellendi; bu kısıt alternatif yöntemle aşılmadı. Mac üzerinde Apple M3 GPU ve Chrome GPU süreci mevcut olsa da bunlar WebGL/WebGL2 context oluşturulabildiğini tek başına kanıtlamaz.
