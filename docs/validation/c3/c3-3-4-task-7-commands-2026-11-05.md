# C3.3.4 Görev 7 — Doğrulama komutları

5 Kasım 2026, depo kökünden. [Doğrulama raporu](c3-3-4-task-7-validation-2026-11-05.md)

## Başlangıç ve host regresyonu

```sh
git status -sb
git branch -vv
git rev-parse HEAD
git log -12 --oneline --decorate
git remote -v
git ls-remote --exit-code origin refs/heads/main

export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor
# Düzeltme öncesi builder regresyonu
python3 -m pytest -q tests/test_fleet_builder.py
# Düzeltme sonrası
python3 -m fleet_config config/fleet.yaml
python3 -m pytest -q tests/test_config.py tests/test_fleet_builder.py tests/test_fleet_manager_domain.py \
  tests/test_fleet_manager_outbox.py tests/test_task_review_holds.py tests/test_ros2_route_resolver.py
python3 -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test
python3 -m pytest -q docker/simulation-c3-3-3/test_config.py
```

İlk builder seçkisi 5 beklenen regresyon hatası ve 7 başarı verdi. Son odak seçkisi 234 geçti. Tam host seçkisi 321 geçti, ROS/IDL ortamı gerektiren 25 test atlandı. Ayrı C3.3.3 config seçkisi 3 geçti.

## Compose ve image

```sh
export DDS_TEST_PAYLOAD=c334-task7-config ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=0
for layer in c3-3-3 c2-3; do
  docker compose -f docker/compose/docker-compose.dds.yml \
    -f docker/compose/docker-compose.simulation-check.yml \
    -f "docker/compose/docker-compose.simulation-${layer}.yml" config --format json
done
C333_AUTO_ROUTES=1 docker compose -f docker/compose/docker-compose.dds.yml \
  -f docker/compose/docker-compose.simulation-check.yml \
  -f docker/compose/docker-compose.simulation-c3-3-3.yml config --format json
C333_ENERGY_POLICY=1 docker compose -f docker/compose/docker-compose.dds.yml \
  -f docker/compose/docker-compose.simulation-check.yml \
  -f docker/compose/docker-compose.simulation-c3-3-3.yml config --format json
docker compose -f docker/compose/docker-compose.dds.yml \
  -f docker/compose/docker-compose.simulation-check.yml \
  -f docker/compose/docker-compose.simulation-c3-3-3.yml build backend
docker run --rm -v "$PWD:/repo:ro" -w /repo --entrypoint python3 \
  ros2-fleet-simulation-c3-3-3-backend:humble-fortress -m fleet_config config/fleet.yaml
# Eski image ile beklenen iki hata, ayrı komutlar
docker run --rm -v "$PWD:/repo:ro" -w /repo -e PYTHONPATH=/repo --entrypoint python3 \
  ros2-fleet-simulation-nav2-check:humble-fortress \
  -c 'from backend.fleet_manager.builder import build_fleet_manager_from_config; build_fleet_manager_from_config()'
docker run --rm --entrypoint python3 ros2-fleet-simulation-nav2-check:humble-fortress \
  -c 'from jsonschema import Draft202012Validator'
```

Çözülmüş config üzerinde domain 42, C3.3.3 için servis başına sekiz ve C2.3 için dört salt okunur bind mount'un kaynakları, iki ayrı C3.3.3 koşu bayrağı ve image adları kontrol edildi. İlk image tarifi Ubuntu apt dizini indirmesinde bekledi ve durduruldu. Sabit hash ile doğrulanan pip wheel'ine geçildikten sonra 60 sn indirme sınırı da aşıldı. 300 sn indirme sınırıyla son tarif başarıyla derlendi. Linux/arm64 backend image kimliği `sha256:5cebe63528351c0f451ad18349f934135a986a79d72686e391dfad8383cdcb8d`. Image içinde C1 doğrulayıcısı iki robotun config'ini başarıyla doğruladı.

## ROS 2 Humble ve CycloneDDS

```sh
docker run --rm --name ros2-fleet-c334-task7-ros-tests \
  -e ROS_DOMAIN_ID=53 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" -w /work --entrypoint bash \
  ros2-fleet-simulation-c3-3-3-backend:humble-fortress -c '
set -e
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:/repo/ros2_ws/src/fleet_robot_executor:$PYTHONPATH
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
  tests/ ros2_ws/src/fleet_robot_executor/test
python3 -m pytest -q -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
  docker/simulation-c2-3/test_config.py
'
docker run --rm -v "$PWD:/repo:ro" -w /repo -e PYTHONPATH=/repo \
  --entrypoint python3 ros2-fleet-simulation-c3-3-3-backend:humble-fortress \
  -m pytest -q -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
  tests/test_fleet_manager_outbox.py::test_yaml_policy_rechecks_preemption_and_commits_one_assignment
```

İlk tam ROS koşusunda üç paket derlendi ve test sonucu 349 geçti, 1 kaldı. Test kancasının Python 3.10 uyumlu sıfırlanmasından sonra ayrı odak koşusu 1 geçti. Aynı image ile tam tekrar 350 geçti. C2.3 config seçkisi 3 geçti.

## Canlı koşular ve kapanış

```sh
mkdir -p /tmp/fleet-task7
COMPOSE_PROJECT_NAME=ros2-fleet-c334-task7-c23 python3 scripts/run_c2_3.py \
  --domain 42 --token c334-task7-c23-20261105 > /tmp/fleet-task7/c23.log 2>&1
COMPOSE_PROJECT_NAME=ros2-fleet-c334-task7-energy python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-task7-energy-20261105 --energy-policy > /tmp/fleet-task7/energy.log 2>&1
COMPOSE_PROJECT_NAME=ros2-fleet-c334-task7-auto python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-task7-auto-20261105 --auto-routes > /tmp/fleet-task7/auto.log 2>&1
COMPOSE_PROJECT_NAME=ros2-fleet-c334-task7-full python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-task7-full-20261105 > /tmp/fleet-task7/full.log 2>&1
COMPOSE_PROJECT_NAME=ros2-fleet-c334-task7-full-repeat python3 scripts/run_c3_3_3.py \
  --domain 42 --token c334-task7-full-repeat-20261105 > /tmp/fleet-task7/full-repeat.log 2>&1

for run in c23 energy auto full full-repeat; do
  rg -n 'SCENARIO_.*PASS|ENERGY_POLICY_|AUTO_ROUTE_|Failed to make progress|"event": "FAIL"' "/tmp/fleet-task7/$run.log"
  for service in simulation backend; do
    name="ros2-fleet-c334-task7-$run-$service-1"
    docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' "$name"
    start=$(docker inspect --format '{{.State.StartedAt}}' "$name")
    finish=$(docker inspect --format '{{.State.FinishedAt}}' "$name")
    docker events --since "$start" --until "$finish" --filter "container=$name" \
      --filter event=kill --filter event=die \
      --format '{{.TimeNano}} {{.Action}} signal={{index .Actor.Attributes "signal"}} exit={{index .Actor.Attributes "exitCode"}}'
  done
done
docker cp ros2-fleet-c334-task7-auto-backend-1:/tmp/c3_3_3_t02-auto-routes.db /tmp/fleet-task7/auto.db
docker cp ros2-fleet-c334-task7-full-backend-1:/tmp/c3_3_3_t02.db /tmp/fleet-task7/full.db
docker cp ros2-fleet-c334-task7-full-repeat-backend-1:/tmp/c3_3_3_t02.db /tmp/fleet-task7/full-repeat.db
```

T02-AUTO-ROUTES ile ilk ve tekrar T02 SQLite kopyalarında görev ve Outbox sorguları çalıştırıldı. Rota olaylarının sayısı T02-AUTO-ROUTES veritabanından alındı.

```sql
SELECT task_id, status, robot_id, assignment_epoch FROM tasks ORDER BY task_id;
SELECT task_id, json_extract(payload, '$.assigned_robot_id'), state
FROM outbox_events WHERE kind = 'EXECUTE_TASK' ORDER BY task_id;
SELECT count(*) FROM processed_events WHERE outcome = 'ROUTE_APPLIED';
```

## Diyagram ve Git

`robot-selection-energy.svg`, [depo teması](../organization/organization-commands-2026-10-26.md#mermaid-ve-svg-üretimi) ile üretildi. SVG XML olarak ayrıştırıldı. Katalogdaki Mermaid bloğu kaynak `.mmd` ile karşılaştırıldı. Chromium ile 11 düğümde etiket sınırları 2 px toleransla denetlendi ve taşma bulunmadı.

```sh
npx --offline --yes --package @mermaid-js/mermaid-cli@11.12.0 mmdc \
  -i docs/diagrams/src/robot-selection-energy.mmd -o docs/diagrams/svg/robot-selection-energy.svg \
  -c /tmp/fleet-task7/mermaid.json -b white
git diff --check
git diff --cached --check
git status -sb
git branch -vv
git ls-remote --exit-code origin refs/heads/main
git commit -m 'fix(fleet-manager): wire YAML energy policies into scheduler'
git push origin main:main
git rev-parse HEAD '@{upstream}'
git log -1 --diff-filter=A --format='%H %s' -- docs/validation/c3/c3-3-4-task-7-validation-2026-11-05.md
git ls-remote --exit-code origin refs/heads/main
```
