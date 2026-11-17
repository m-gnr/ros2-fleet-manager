# Üç robot tek komut demo launcher'ı

17 Kasım 2026 · Taban `origin/main` `2122d0a`. Launcher, `scripts/c5_demo_start.py` ve mevcut `stage1_run.py` canlı C5 altyapısını kullanır. Yeni simülasyon akışı, profil, istasyon/park yerleşimi veya V1–V6 arayüz davranışı eklemez.

## Kullanım ve sahiplik

```sh
./scripts/start_demo.sh
```

Başlatıcı benzersiz container adı, ROS domain ID ve boş loopback portları seçer. Profil/readiness denetimleri ve gerçek API/robot snapshot'ı READY olmadan GUI adresi yazılmaz. Vite `127.0.0.1` üzerinde başlar; Chrome mevcutsa açılır. Görev gönderilmez. `Ctrl+C`, SIGTERM, SIGHUP ve ebeveyn PID kaybı aynı cleanup yoluna girer. Önce bu oturumun Vite süreci doğrulanıp kapatılır, sonra sadece kimliği/worktree mount'ı/image'ı doğrulanan launcher container'ı `docker stop --timeout 60` ile kapanır. Container supervisor'ı API/manager/bridge, robot düğümleri, Nav2/AMCL ve Gazebo'yu sırayla kapatır. Container, volume, kanıt ve cache silinmez. Belirsiz süreç veya container sahipliğinde launcher o kaynağı koruyup hata verir.

`fleet_interfaces` ve `fleet_perception` overlay'i kaynak dosyaları ve image ID'sinden türetilen SHA-256 anahtarıyla `/tmp/ros2-fleet-c5-overlay/<hash>` altında tutulur. Kaynak veya image değişince farklı cache anahtarı oluşur. Aynı cache eşzamanlı açılışta `flock` ile korunur. Eski cache/build logları otomatik silinmez. Frontend bağımlılığı eksikse launcher Docker başlatmadan durur; kullanıcı `frontend` içinde `npm ci` çalıştırmalıdır.

## Doğrulamalar

| Kontrol | Sonuç | Kanıt / sınır |
|---|---|---|
| Shell/Python statik kontrol | **PASS** | `bash -n scripts/start_demo.sh`; `python3 -m py_compile scripts/start_demo.py scripts/c5_demo_start.py`. |
| Temiz worktree bağımlılık ön kontrolü | **PASS** | İlk deneme `node_modules` yokken açık hata ile Docker başlatmadan durdu. İzole `frontend` için `npm ci --ignore-scripts --no-audit --no-fund` 99 paketi kurdu. |
| Üç robot gerçek canlı başlangıç | **PASS** | `./scripts/start_demo.sh`: iki ardışık cache'li READY koşusu `robot_alpha`, `robot_beta`, `robot_gamma`, AMCL/Nav2/TF, LIVE API snapshot ve boş görev sayısını doğruladı. Son cache koşuları domain 221 ve 231 kullandı; portlar otomatik seçildi. |
| Chrome filo ve WebSocket | **PASS** | Yerel Chrome gerçek GUI'de `3/3 TF LIVE`, 3 robot LIVE ve görev sayısı 0 gösterdi. Ürün WebSocket bağlantısı `Bağlı` idi. Görev veya hareket komutu gönderilmedi. |
| V1–V6 WebGL sahnesi | **FAIL / DOĞRULANMADI** | Chrome, `3D görünüm için WebGL desteği gerekiyor.` fallback'ini gösterdi. WebGL context/sahne çizimi doğrulanamadı. V1–V6 kodu veya güvenlik ayarı değiştirilmedi. |
| İlk kaynak/image cache build | **PASS** | `fleet_interfaces` ve `fleet_perception` colcon build başarıyla tamamlandı; preflight `PASS`. Cache anahtarı `d3c739d774adce8f7214b7f8d34d8b56a68b31df0d5f346f904cb59f8a267ba8`; image/source metadatası `source.json` içinde. |
| Cache ile yeniden başlatma | **PASS** | Aynı fingerprint ile ikinci READY koşusu başarılı; cache'de tek `build_*` colcon log dizini kaldı, yeniden build yapılmadı. |
| SIGINT / Ctrl+C kapanışı | **PASS** | Launcher'a SIGINT verildi. Son koşular container exit `0`; `shutdown.json` içinde API, manager, scene, 3 Executor, 3 Battery Simulator, observer ve simulation exit `0`; API/UI portları boş. |
| SIGHUP ve ebeveyn kaybı | **PASS** | Başlangıç sırasındaki SIGHUP ve ayrı parent sürecinin kaybı kendi oturum container'ını durdurdu (exit `143`, sinyal nedeniyle); launcher/runner kalmadı ve ilgili portlar boştu. Bir önceki bağımsız demo oturumu etkilenmedi. |
| Başarısız başlangıç cleanup'ı | **PASS** | İzole denemede yalnız yeni `c5_demo_start.py` child'ı başarısız sonlandırıldı. Launcher kendi container'ını kontrollü durdurdu (exit `143`); launcher, runner ve port listener'ı kalmadı. |
| Yeniden başlatma | **PASS** | Her kapanıştan sonra yeni benzersiz container/domain ile temiz READY koşusu tamamlandı. |

Canlı GUI kanıtı kullanıcı ortamındaki Chrome ve bu makinedeki Docker Desktop / Apple Silicon container'ları içindir. WebGL desteği başarısız olduğundan tüm görsel kabul tamamlanmış sayılmaz. Bu launcher'ı üç robotlu panel başlatma/kapatma kolaylığı olarak kullanın; hareket veya ürün kabulü sonucu çıkarmayın.
