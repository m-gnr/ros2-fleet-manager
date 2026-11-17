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

`origin/main` merge’i bu geçici entegrasyon branch’inde çözülmüş ve dosyalar test edilmiştir. Bu rapor anında merge commit’i henüz oluşturulmamıştır; `main` ve `origin/main` değişmeden durur. Kullanıcının GitHub push onayı bekleniyor. Hareket zincirinin **NOT TESTED** olması sebebiyle görev/park/şarj canlı kabulü veya hareket izni sonucu çıkarılmamalıdır.
