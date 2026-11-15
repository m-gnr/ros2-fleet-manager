# C5-B6B.2 — Komut eki

15 Kasım 2026. Bütün komutlar `main` worktree depo kökünden çalıştırıldı. Container kaynağı salt okunur bağladı; ağ kapalıydı. Kullanılan mevcut image `ros2-fleet-c5-validation:humble-fortress`, image ID `sha256:7fb7e7fc4aebe0d2b4097752e9b470e30d8ea7a8126bb1dee87d03f30330609d`.

Son doğrulama, yalnız IDL ve hedefli testler:

```sh
docker run --rm --network none -v "$PWD:/repo:ro" --entrypoint /bin/bash \
  ros2-fleet-c5-validation:humble-fortress \
  /repo/docker/experiments/c5-b6b2/run_protocol_tests.sh
```

[Runner](../../../docker/experiments/c5-b6b2/run_protocol_tests.sh) Humble ortamını yükler, yalnız `interfaces/fleet_interfaces` paketini `/tmp/b6b2` altında colcon ile derler; sonra aşağıdaki kapsamı çalıştırır. Host veya repo altında build/install çıktısı oluşturmaz. `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` ilgisiz ROS launch-testing discovery'sini engeller; cache plugin'i salt okunur mount için kapalıdır.

```sh
python3 -m pytest -p no:cacheprovider -q \
  tests/test_traffic_protocol.py tests/test_traffic_core.py \
  tests/test_traffic_protocol_ros2.py tests/test_executor_lifecycle_integration.py
```

Son stdout ve sonuç: `.............................................. [100%]`, **46 passed in 2.81s**, exit 0, 0 skip. Yeni protokol testleri + 13 B6B.1 çekirdek testi + 3 mevcut fake Nav2 lifecycle testi. Ürün launch/Gazebo/controller çalıştırılmadı.

Geliştirme koşuları: host ilk domain/adapter koşusu 26 geçti; station testleriyle 28 geçti; ürün config testiyle 29 geçti. İlk container invocation `set -u` ile Humble setup'taki tanımsız ortam değişkeninde durdu; test çalışmadı. Sonraki invocation'da otomatik launch-testing plugin'i ilgisiz test importunu tetikledi ve collection hatası verdi; geniş test çalıştırılmadı. Plugin kapatıldı. İlk gerçek hedefli koşu 32 geçti / 4 kaldı: eşleşmeyen RPC cevabı için gate WAITING kalıyordu (sender yine 0). RPC ret durumuna kalıcı kapanış eklendi; sonraki koşu 43 geçti. ACK/yarış ve config sınırı testlerinin eklenmesinden sonraki son 46 testlik koşu yukarıdadır; başarısız geliştirme koşuları kabul kanıtı sayılmaz.

Diyagram mevcut yerel Mermaid CLI ile yeniden üretildi:

```sh
node /Users/murat/.npm/_npx/bb964472b4759b27/node_modules/@mermaid-js/mermaid-cli/src/cli.js \
  -i docs/diagrams/src/traffic-permit-protocol.mmd \
  -o docs/diagrams/svg/traffic-permit-protocol.svg -b transparent
```

Çıkış 0. Bu host'a özgü cache yolu ürün kurulum talimatı değildir. Kaynak ve SVG birlikte teslim edilir. `git diff --check` çıkış 0; yeni belgelerin yerel bağlantıları ayrıca dosya varlığı üzerinden kontrol edilir. Hiçbir test fiziksel güvenlik veya canlı trafik kabulü değildir.
