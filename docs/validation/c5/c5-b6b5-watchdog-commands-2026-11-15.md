# C5-B6B.5 komut eki — 15 Kasım 2026

Komutlar `main` worktree kökü `/Users/murat/develop/ros2-fleet-manager-c5-a-demo-integration`
içinden çalıştırılır. İlk dizin `main-legacy` idi; branch değiştirilmedi.

```sh
bash docker/experiments/c5-b6b5/run.sh docs/validation/c5/c5-b6b5-watchdog-2026-11-15/final
```

Betik taban image ID doğrulaması, geliştirici image build, ağsız iki temiz native
build, CTest, incremental build, hash karşılaştırması, ELF/ldd ve pozitif/negatif
plugin loader testini tek hata-kapalı zincirde yürütür. Herhangi bir başarısız
komut nonzero çıkış verir. Native testler Gazebo server veya fizik motoru açmaz;
komut callback'ine yalnız sıfır Twist verilir. Host lease testinde deterministik
steady-clock noktaları kullanılır; gerçek callback testinde 270 ms beklenir.

İlk Dockerfile denemesinde yerel config image ID'si registry manifest digest'i
gibi kullanıldığı için image çözümleme FAIL oldu; `image-build.log` korunur.
Yerel tag + çalıştırıcıdaki exact image ID kontrolü ile düzeltildi.
`image-build-retry.log` geliştirici image hazırlığının ham çıktısıdır.

```sh
c++ -std=c++17 -Wall -Wextra -Werror docker/experiments/c5-b6b5/test_lease.cc -o /tmp/c5-b6b5-lease-test
/tmp/c5-b6b5-lease-test
```

Host testi ayrı hedefli kontrol; native ABI testinin yerine geçmez.
Build paket listesi, compiler, source/binary hash ve loader maps kanıtı [ham dizinde](c5-b6b5-watchdog-2026-11-15/).

Son koşu exit 0: her temiz build 2/2 CTest PASS (0 skip), üç binary hash eşit; SystemLoader/maps ve yanlış yol exit 3 PASS. İlk `run/` genel native Loader kontrolü de geçti; son `final/` gerçek Gazebo SystemLoader ile yapıldı.
