# Visualize → main entegrasyon kapısı

17 Kasım 2026. **BLOKLU — merge ve push yapılmadı.** `feature/visualize` başlangıç HEAD'i `d89e88c` (`Checkpoint Visualize V1-V6 warehouse presentation`), yerel `main` HEAD'i `74c4ad4`, `origin/main` HEAD'i `6c355c4` (`merge: integrate three-robot stable C5 demo`).

## Kontroller

| Kontrol | Sonuç | Kanıt ve sınır |
|---|---|---|
| Frontend production build | **PASS** | `npm --prefix frontend run build`. |
| Chrome görsel regresyon | **PASS** | `visualize-v1.spec.ts`: 3/3; canlı Chrome’da V1–V6 sahnesi ve `3/3 TF LIVE` gözlendi. Mevcut simülasyon oturumu kullanıldı. |
| Backend/filo/istasyon/şarj/trafik birim regresyonu | **PASS** | C5 Humble image’ında 63 hedefli test; ayrıca Scheduler, Outbox, istasyon dispatch, şarj, trafik core/protocol/motion gate ve Executor paketinden 245 geçti. |
| ROS TF okuyucu | **PASS** | Humble + IDL overlay ile 4/4 ROS okuyucu testi geçti, skip yok. |
| Executor ROS düğüm testleri | **PARTIAL** | Paket testinde 10 geçti, 8 ROS düğüm testi gerekli runtime arayüzlerini içe alamadığı için skip edildi. |
| Üç robotlu güncel Chrome/TF | **PASS** | Canlı salt okunur panelde üç robotun tümü `LIVE`, `3/3 TF LIVE`; batarya/ürün telemetrisi geldi. Yeni Gazebo başlatma veya WebSocket örneği bu turda alınmadı. Önceki gerçek Gazebo/TF/WebSocket kanıtı [V2.3 kaydında](visualize-v2-3-validation-2026-11-17.md) bulunur. |
| Yeni üç robot Gazebo spawn + WebSocket | **NOT TESTED** | Mevcut oturum gözlemi yeni spawn/bağımsız WebSocket kabulü değildir. |
| Görev atama, fiziksel rezervasyon/park/şarj çevrimi | **NOT TESTED** | Görev göndermek Nav2 hareketi başlatır. Güncel güvenlik kabulü yoktur; bu turda hareket başlatılmadı. |
| C5 trafik ve hareket güvenliği (yerel `main` değişiklikleri) | **NOT TESTED** | İlgili permit/watchdog/trafik çalışması ayrı `main` worktree’sinde commit edilmemiş değişiklik olarak duruyor; feature worktree’sine kopyalanmadı veya commit edilmedi. |

## Merge kapısı

Hareket kabul kaydı, `motion_envelope: null`, kalifiye freshness/release eşiklerinin eksikliği ve native actuator yolundaki fail-closed nonzero reddini açıkça belirtir. Bu nedenle görev/park/şarj hareketi kullanıcı koşulundaki doğrulanmış ve yetkili güvenlik zincirini karşılamaz. [Gerçek hareket kabul kaydı](c5-b6c-real-motion-acceptance-2026-11-16.md) hareketi **NOT TESTED** olarak tutar.

Yerel `main` worktree’sinde ayrıca commit edilmemiş C5, Executor, Scheduler, permit, watchdog ve trafik değişiklikleri vardır. Bunlara dokunulmadı. `origin/main` üzerindeki commit, üç robotlu C5 entegrasyonudur; başka worktree’deki bu değişikliklerin tamamını kapsadığı varsayılmadı.

Zorunlu kontroller arasında **NOT TESTED** bulunduğundan kullanıcı talimatı uyarınca `origin/main` merge edilmedi ve push yapılmadı. Bu kayıttaki V1–V6 palet commit’i tasarım doğrulamasıyla sınırlıdır; entegrasyon kabulü veya hareket izni değildir.
