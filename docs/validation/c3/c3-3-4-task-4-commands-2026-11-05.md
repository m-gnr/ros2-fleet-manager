# C3.3.4 Görev 4 — Doğrulama komutları

5 Kasım 2026 tarihinde depo kökünden çalıştırıldı. [Doğrulama raporu](c3-3-4-task-4-validation-2026-11-05.md)

## Git ve host

```sh
git status -sb
git branch --show-current
git rev-parse HEAD
git log -7 --oneline
git remote -v
git ls-remote origin refs/heads/main
git merge-base --is-ancestor fe2615b264efa2fda4e99806d07787f18e209c31 HEAD
git merge-base --is-ancestor fe280d292ec8ad427cc94c06a641f8993d3d53d7 HEAD
git merge-base --is-ancestor 1eb60a75f47f9ba5da840957d1c2412871731acb HEAD

export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor
# Ürün düzeltmesinden önce açığı yeniden üretti.
python3 -m pytest -q tests/test_fleet_manager_domain.py -k unblock_by_station_id
python3 -m pytest -q tests/test_fleet_manager_domain.py tests/test_fleet_manager_outbox.py \
  tests/test_ros2_status_subscriber.py tests/test_clear_robot_error_client.py
python3 -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test
python3 -m pytest -q docker/simulation-c3-3-3/test_config.py
git diff --check
```

İlk odak koşusunda SQLite'ın sonlu olmayan JSON sayılarını reddetmesi nedeniyle 3 test başarısız oldu. Geçersiz poz RobotStatus işlenirken kanıt olarak iptal edilip robotun son geçerli pozundan ayrı tutulduktan sonra odak koşusu geçti. İki Compose config test modülünü tek pytest komutunda toplama denemesi aynı modül adıyla, `--import-mode=importlib` denemesi ise yerel `check` import'u nedeniyle koleksiyonda durdu. C2.3 config testi hostta sabit `/config` yolu bulunmadığından 3 hata verdi. Modüller ayrı çalıştırıldı ve C2.3 config testi için Docker'da `/config` salt okunur bağlandı.

## ROS 2 Humble ve CycloneDDS

```sh
docker run --rm --name ros2-fleet-c334-task4-tests \
  -e ROS_DOMAIN_ID=53 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" -w /work --entrypoint bash \
  ros2-fleet-simulation-nav2-check:humble-fortress -c '
set -e
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:/repo/ros2_ws/src/fleet_robot_executor:$PYTHONPATH
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
  --ignore=tests/test_config.py tests/ ros2_ws/src/fleet_robot_executor/test
python3 -m pytest -q -p no:cacheprovider -p no:launch_testing -p no:launch_ros docker/simulation-c2-3/test_config.py
'
```

İmajın `jsonschema` sürümü `Draft202012Validator` içermediği için saf Python C1 seçkisi host koşusunda doğrulandı.

## Canlı Gazebo

Compose katmanları DDS → A → C3.3.3 ve DDS → A → C2.3 sırasıyla çözümlendi. İki servisin imajı Linux/arm64 `ros2-fleet-simulation-nav2-check:humble-fortress`, domain 42. Servis başına C3.3.3 için sekiz, C2.3 için dört bind mount yolu doğrulandı. Var olan imaj kullanıldı.

```sh
export DDS_TEST_PAYLOAD=c334-task4-20261105 ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=0
for layer in c3-3-3 c2-3; do
  docker compose -f docker/compose/docker-compose.dds.yml \
    -f docker/compose/docker-compose.simulation-check.yml \
    -f "docker/compose/docker-compose.simulation-${layer}.yml" config --format json
done

COMPOSE_PROJECT_NAME=ros2-fleet-c334-task4-live python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-task4-20261105 > /tmp/fleet-task4-live.log 2>&1
COMPOSE_PROJECT_NAME=ros2-fleet-c334-task4-repeat python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-task4-repeat-20261105 > /tmp/fleet-task4-repeat.log 2>&1
COMPOSE_PROJECT_NAME=ros2-fleet-c334-task4-c23 python3 scripts/run_c2_3.py \
  --domain 42 --token c334-task4-c23-20261105 > /tmp/fleet-task4-c23.log 2>&1
```

Kapanış kayıtları her koşunun hemen ardından toplandı. Sinyallerin aralığı Docker olaylarının nanosaniye damgalarından hesaplandı.

```sh
for project in live repeat c23; do
  for service in simulation backend; do
    name="ros2-fleet-c334-task4-${project}-${service}-1"
    docker inspect --format '{{.Name}} exit={{.State.ExitCode}} OOMKilled={{.State.OOMKilled}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} stop_timeout={{.Config.StopTimeout}}' "$name"
    docker events --since "$(docker inspect --format '{{.State.StartedAt}}' "$name")" \
      --until "$(docker inspect --format '{{.State.FinishedAt}}' "$name")" \
      --filter "container=$name" --filter event=kill --filter event=die \
      --format '{{.TimeNano}} {{.Action}} signal={{index .Actor.Attributes "signal"}} code={{index .Actor.Attributes "exitCode"}}'
  done
done
```

### Kapanış süresi tanısı

C2.3 ayrı Compose projesinde aynı test komutları ve imajla tekrarlandı. Geçici dosya yalnız simulation kapanış süresini değiştirir. Çözümlenen imaj, bind mount ve komutlar standart C2.3 ile karşılaştırıldı.

```sh
override=/tmp/fleet-task4-stop-30s.yml
printf '%s\n' services: '  simulation:' '    stop_grace_period: 30s' > "$override"
export DDS_TEST_PAYLOAD=c334-task4-stopdiag-20261105 ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=0
export COMPOSE_PROJECT_NAME=ros2-fleet-c334-task4-stopdiag
compose=(docker compose -f docker/compose/docker-compose.dds.yml \
  -f docker/compose/docker-compose.simulation-check.yml \
  -f docker/compose/docker-compose.simulation-c2-3.yml -f "$override")
"${compose[@]}" config --format json
"${compose[@]}" up --abort-on-container-exit --exit-code-from backend \
  > /tmp/fleet-task4-stopdiag.log 2>&1
```

Kapanış incelemesinde aynı `docker inspect` ve `docker events` komutları `stopdiag` projesi için çalıştırıldı.

## Diyagramlar

`parking-reservations.svg` ve `failure-operator-recovery.svg`, Mermaid CLI 11.12.0 ve [mevcut temayla](../organization/organization-commands-2026-10-26.md#mermaid-ve-svg-üretimi) üretildi. Her SVG XML olarak ayrıştırıldı ve kaynak Mermaid içeriğinin katalogdaki blokla eşleşmesi denetlendi.
