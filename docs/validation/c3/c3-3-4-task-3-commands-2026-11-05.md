# C3.3.4 Görev 3 — Doğrulama komutları

5 Kasım 2026 tarihinde depo kökünden çalıştırıldı. [Doğrulama raporu](c3-3-4-task-3-validation-2026-11-05.md)

## Başlangıç ve host

```sh
git rev-parse HEAD
git branch --show-current
git status --short
git merge-base --is-ancestor fe2615b264efa2fda4e99806d07787f18e209c31 HEAD
git merge-base --is-ancestor fe280d292ec8ad427cc94c06a641f8993d3d53d7 HEAD
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor

# Ürün düzeltmesi öncesi 7 geçti, 16 başarısız, 36 seçim dışı.
python3 -m pytest -q tests/test_fleet_manager_outbox.py \
  -k 'preempt or terminal_during_cancel' --tb=short

# 93 geçti.
python3 -m pytest -q tests/test_fleet_manager_domain.py \
  tests/test_fleet_manager_outbox.py tests/test_ros2_route_resolver.py

# 245 geçti, ROS çalışma zamanı gerektiren 16 test atlandı.
python3 -m pytest -q -rs tests/

# 10 geçti, 5 ROS çalışma zamanı testi atlandı.
python3 -m pytest -q -rs ros2_ws/src/fleet_robot_executor/test

# 3 geçti.
python3 -m pytest -q docker/simulation-c3-3-3/test_config.py
```

İlk odak komutunda rota testi dosyasının adı yanlış yazıldığı için test yürütülmedi. Yukarıdaki düzeltilmiş komut geçerli odak koşusudur.

## ROS 2 Humble ve CycloneDDS

Üç paket, mevcut Linux/arm64 Nav2 imajında `colcon` ile derlendi. İmajın `jsonschema` sürümünde `Draft202012Validator` bulunmadığı için saf Python C1 testi olan `tests/test_config.py` host koşusunda doğrulandı. Aşağıdaki ROS komutu geri kalan kök testleri ve Executor paket testlerini içerir. İlk koşuda 204 test geçti ve SQLite denetleyicisini kaldıran iki yeni test başarısız oldu. Python 3.10 uyumlu test düzeneğiyle aynı komut 206 test geçirdi. Her iki koşuda da 23 metaschema uyarısı görüldü.

```sh
docker run --rm --name ros2-fleet-c334-task3-tests \
  -e ROS_DOMAIN_ID=53 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -w /work --entrypoint bash \
  ros2-fleet-simulation-nav2-check:humble-fortress -c '
set -e
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:/repo/ros2_ws/src/fleet_robot_executor:$PYTHONPATH
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
  --ignore=tests/test_config.py tests/ ros2_ws/src/fleet_robot_executor/test
'
```

## Canlı Gazebo

DDS → A → C3.3.3 ve DDS → A → C2.3 katmanları için `docker compose config --format json` çıktısı denetlendi. Her servis mevcut `ros2-fleet-simulation-nav2-check:humble-fortress` Linux/arm64 imajına ve domain 42'ye çözümlendi. C3.3.3'te servis başına sekiz, C2.3'te dört bind mount yolu doğrulandı. Canlı koşular bu imajla, ayrı Compose projelerinde ve imajı yeniden derlemeden yapıldı.

```sh
export DDS_TEST_PAYLOAD=c334-task3-20261105 ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=0
for layer in c3-3-3 c2-3; do
  docker compose -f docker/compose/docker-compose.dds.yml \
    -f docker/compose/docker-compose.simulation-check.yml \
    -f "docker/compose/docker-compose.simulation-${layer}.yml" config --format json
done

COMPOSE_PROJECT_NAME=ros2-fleet-c334-task3-live python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-task3-20261105 > /tmp/fleet-task3-live.log 2>&1
COMPOSE_PROJECT_NAME=ros2-fleet-c334-task3-c23 python3 scripts/run_c2_3.py \
  --domain 42 --token c334-task3-c23-20261105 > /tmp/fleet-task3-c23.log 2>&1
COMPOSE_PROJECT_NAME=ros2-fleet-c334-task3-repeat python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-task3-repeat-20261105 > /tmp/fleet-task3-repeat.log 2>&1
```

Kapanış incelemesinde backend ve simulation kapsayıcılarının `.State.ExitCode`, `.State.OOMKilled`, `.State.StartedAt`, `.State.FinishedAt` ve `.Config.StopTimeout` alanları `docker inspect` ile okundu. Simulation için kapsayıcı adı ve koşu zaman aralığıyla `docker events` sorgulanıp sinyallerin arası nanosaniye damgalarından hesaplandı.

```sh
for project in live c23 repeat; do
  name="ros2-fleet-c334-task3-${project}-simulation-1"
  docker events --since "$(docker inspect --format '{{.State.StartedAt}}' "$name")" \
    --until "$(docker inspect --format '{{.State.FinishedAt}}' "$name")" \
    --filter "container=$name" --filter event=kill --filter event=die \
    --format '{{.TimeNano}} {{.Action}} signal={{index .Actor.Attributes "signal"}} code={{index .Actor.Attributes "exitCode"}}'
done
```

## Diyagram

`safe-preemption.svg`, Mermaid CLI 11.12.0 ve [mevcut temayla](../organization/organization-commands-2026-10-26.md#mermaid-ve-svg-üretimi) üretildi. SVG XML olarak ayrıştırıldı ve `safe-preemption.mmd` dosyasının katalogdaki Mermaid bloğuyla eşleştiği doğrulandı. `git diff --check` çalıştırıldı.
