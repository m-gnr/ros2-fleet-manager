# C5 Docker preflight — komutlar ve ölçümler — 17 Kasım 2026

Dal: `demo/alpha-beta-stable`  
Çalışma ağacı: `/private/tmp/ros2-fleet-manager-c5-alpha-beta-stable`

## Hedefli testler

```sh
python3 -m unittest tests.test_docker_simulation_preflight -v
python3 -m py_compile scripts/docker_simulation_preflight.py tests/test_docker_simulation_preflight.py
bash -n scripts/run_c5_dashboard.sh
```

Sonuç: 4/4 test geçti; Python derleme ve Bash sözdizimi kontrolü geçti. Testlerde Docker CLI taklit edildi; gerçek Compose/Gazebo/Nav2 başlatılmadı.

Test adımları:

- `test_single_simulation_free_environment_reaches_compose_up`: çakışmasız durumda launcher Compose `up` çağrısına geçer.
- `test_other_simulation_blocks_startup_without_stopping_containers`: diğer simülasyonda başlangıç durur; `docker stop` çağrısı yapılmaz.
- `test_explicit_concurrent_override_is_logged_and_reaches_compose`: açık override kayda geçer ve Compose `up` çağrısına geçer.
- `test_unavailable_resource_measurement_fails_closed`: VM ölçümü başarısız olduğunda Compose çağrısı yapılmaz.

## Salt okunur canlı ölçüm

```sh
python3 scripts/docker_simulation_preflight.py --project-name current-preflight-readonly
```

Sonuç kodu `1`: yeni başlangıç için üç aktif simülasyon çakışması bulundu. Bu komut sadece `docker ps`, `inspect`, `stats`, `top` ve `info` okudu; container durdurma/silme veya Compose çağrısı yapmadı.

Bu örnekte Docker VM 8 CPU ve 7934.4 MiB RAM bildirdi. Çalışan container ölçüm toplamı %903.8 CPU ve 3687.0 MiB RAM oldu. CPU toplamı bildirilen kapasiteyi geçti ve uyarı çıktı. Üç aktif simülasyon `c5-alpha-beta-gamma-live-retry1-20261117`, `c5-alpha-beta-stable-live-20261117`, `c5-alpha-beta-manual-20261117` idi; ayrıntılar [rapordadır](docker-simulation-preflight-2026-11-17.md).

## Kullanım

Normal C5 başlatma yolu preflight'i otomatik çalıştırır:

```sh
scripts/run_c5_dashboard.sh up -d
```

Aktif başka simülasyon varken bilinçli birlikte çalıştırma:

```sh
scripts/run_c5_dashboard.sh up -d --allow-concurrent-simulation
```

Override yalnızca çakışma kapısını açar; ölçüm başarısızsa başlangıç yine durur. Launcher hiçbir oturumu otomatik kapatmaz.
