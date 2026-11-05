# C3.3.4 Görev 2 — Doğrulama komutları

5 Kasım 2026 tarihinde depo kökünden çalıştırıldı. [Doğrulama raporu](c3-3-4-task-2-validation-2026-11-05.md)

## Host

```sh
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor

# Ürün kodu değiştirilmeden önce 1 geçti, 7 başarısız, 34 seçim dışı.
python3 -m pytest -q tests/test_fleet_manager_outbox.py \
  -k 'blocked_session or trusted_session_release' --tb=short

# Düzeltme sonrası 73 geçti.
python3 -m pytest -q tests/test_fleet_manager_outbox.py \
  tests/test_fleet_manager_domain.py tests/test_ros2_status_subscriber.py

# 227 geçti, ROS çalışma zamanı gerektiren 16 test atlandı.
python3 -m pytest -q -rs tests/

# 3 geçti.
python3 -m pytest -q docker/simulation-c3-3-3/test_config.py
```

## ROS 2 Humble ve CycloneDDS

Yerel Linux/arm64 Nav2 imajında `colcon` üç paket derledi. Aynı kapsayıcı ayarlarıyla `tests/` dizininin tamamını çalıştırma denemesi, imajdaki `jsonschema` paketinde `Draft202012Validator` bulunmadığı için toplama aşamasında durdu. Host konfigürasyon testleri yukarıdaki ayrı koşuda tamamlandı. Aşağıdaki ROS ve domain seçkisinde 171 test geçti. İmaj 19 metaschema uyarısı üretti.

```sh
docker run --rm --name ros2-fleet-c334-session-tests \
  -e ROS_DOMAIN_ID=53 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -w /work --entrypoint bash \
  ros2-fleet-simulation-nav2-check:humble-fortress -c '
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src || exit
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:/repo/ros2_ws/src/fleet_robot_executor:$PYTHONPATH
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
  tests/test_executor_*.py tests/test_c2_3_config.py tests/test_ros2_*.py \
  tests/test_task_review_holds.py tests/test_clear_robot_error_client.py \
  tests/test_fleet_manager_domain.py tests/test_fleet_manager_outbox.py
'
```

## Canlı Gazebo

DDS → A → C3.3.3 ve DDS → A → C2.3 için `docker compose config --format json` çıktısında her iki servisin imajı, domain 42 ve host bind mount yollarının varlığı doğrulandı. C3.3.3 servislerinde sekizer, C2.3 servislerinde dörder bind mount çözümlendi. Canlı koşular ayrı Compose projelerinde mevcut Nav2 imajıyla yapıldı.

```sh
COMPOSE_PROJECT_NAME=ros2-fleet-c334-session python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-session-20261105

COMPOSE_PROJECT_NAME=ros2-fleet-c334-session-c23 python3 scripts/run_c2_3.py \
  --domain 42 --token c334-session-c23-20261105

COMPOSE_PROJECT_NAME=ros2-fleet-c334-session-retry python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-session-retry-20261105

# Aşağıdaki başlangıç commit'i karşılaştırmasından sonra, güncel kodla.
COMPOSE_PROJECT_NAME=ros2-fleet-c334-session-final python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-session-final-20261105
```

Başlangıç commit'i için ayrı worktree kullanıldı. Aynı imaj, domain ve bind mount kontrolleri bu worktree içinde tekrarlandı.

```sh
baseline=$(mktemp -d "$PWD/../ros2-fleet-task2-baseline.XXXXXX")
git worktree add --detach "$baseline" fe2615b264efa2fda4e99806d07787f18e209c31
(
  cd "$baseline" || exit
  COMPOSE_PROJECT_NAME=ros2-fleet-c334-session-baseline python3 scripts/run_c3_3_3.py \
    --domain 42 --token c334-session-baseline-20261105
)
git worktree remove "$baseline"
```

## Simulation kapanışı

`docker inspect` ile backend ve simulation çıkış kodları ile `OOMKilled` alanı kontrol edildi. Docker olayları `--filter container=<simulation>` ile koşu zaman aralığında incelendi. `kill` olaylarının `signal` alanları ve `die` olaylarının `exitCode` alanları karşılaştırıldı. Görev 1 için aynı kontrol `ros2-fleet-c334-epoch-simulation-1` ve `ros2-fleet-c334-c23-simulation-1` kapsayıcılarına uygulandı.

```sh
export COMPOSE_PROJECT_NAME=ros2-fleet-c334-session-stop
export DDS_TEST_PAYLOAD=c334-session-stop-20261105 ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=0
docker compose -f docker/compose/docker-compose.dds.yml \
  -f docker/compose/docker-compose.simulation-check.yml \
  -f docker/compose/docker-compose.simulation-c3-3-3.yml \
  up -d --no-deps --no-build simulation

# Her iki lifecycle_manager_navigation için Managed nodes are active görüldükten sonra.
time docker stop --time 20 ros2-fleet-c334-session-stop-simulation-1
docker inspect --format '{{.Name}} code={{.State.ExitCode}} oom={{.State.OOMKilled}}' \
  ros2-fleet-c334-session-stop-simulation-1
docker logs ros2-fleet-c334-session-stop-simulation-1 2>&1 | rg 'FORCED_KILL|PROCESS_EXIT'
```

Başarısız T02 koşularında `docker cp` ile backend kapsayıcılarından `/tmp/c3_3_3_t02.db` kopyalandı. SQLite üzerinde `tasks`, `reservations`, `processed_events` ve `robots.snapshot` kayıtları incelendi.

## Diyagramlar

`status-session-order`, `parking-reservations` ve `safe-preemption` SVG'leri [mevcut tema](../organization/organization-commands-2026-10-26.md#mermaid-ve-svg-üretimi) ve Mermaid CLI 11.12.0 ile yeniden üretildi. Üç SVG XML olarak ayrıştırıldı. Katalogdaki Mermaid blokları kaynakla karşılaştırıldı.
