# C3.3.4-FINAL doğrulama komutları

5 Kasım 2026. Komutlar depo kökünden çalıştırıldı. [C4 geçiş kontrol listesi](c3-3-4-final-c4-gate-2026-11-05.md)

## Başlangıç ve otomatik regresyon

```sh
git status -sb
git branch -vv
git rev-parse HEAD '@{upstream}'
git log -14 --oneline
git ls-remote --exit-code origin refs/heads/main

export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor
python3 -m fleet_config config/fleet.yaml
python3 -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test
python3 -m pytest -q docker/simulation-c3-3-3/test_config.py

docker run --rm --name fleet-final-ros-tests \
  -e ROS_DOMAIN_ID=62 -e ROS_LOCALHOST_ONLY=1 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" -w /work --entrypoint bash \
  ros2-fleet-simulation-c3-3-3-backend:humble-fortress -c '
set -e
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:/repo/ros2_ws/src/fleet_robot_executor:$PYTHONPATH
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros tests/ ros2_ws/src/fleet_robot_executor/test
python3 -m pytest -q -p no:cacheprovider -p no:launch_testing -p no:launch_ros tests/test_executor_safety_ros2.py
for test in docker/simulation-c2-3/test_config.py docker/simulation-c3-3-3/test_config.py; do
  python3 -m pytest -q -p no:cacheprovider -p no:launch_testing -p no:launch_ros "$test"
done
'
```

İlk Humble tam seçkisi 355 geçti. Ardından aynı pytest çağrısına `--import-mode=importlib` ile alınan iki ayrı container config modülü `from check import …` sırasında collection hatası verdi. Modüller ayrı pytest süreçlerinde çalıştırıldığında 3 + 3 geçti.

## Compose ve izole canlı koşular

```sh
export DDS_TEST_PAYLOAD=c334-final-config ROS_DOMAIN_ID=61 C333_HIGH_PREEMPTION=1
for layer in c2-3 c3-3-3; do
  docker compose -f docker/compose/docker-compose.dds.yml \
    -f docker/compose/docker-compose.simulation-check.yml \
    -f "docker/compose/docker-compose.simulation-${layer}.yml" config --format json
done

COMPOSE_PROJECT_NAME=fleet-final-full-1 python3 scripts/run_c3_3_3.py --domain 61 --token c334-final-full-1
COMPOSE_PROJECT_NAME=fleet-final-full-2 python3 scripts/run_c3_3_3.py --domain 61 --token c334-final-full-2
COMPOSE_PROJECT_NAME=fleet-final-c23-final python3 scripts/run_c2_3.py --domain 61 --token c334-final-c23-final
COMPOSE_PROJECT_NAME=fleet-final-high-supported python3 scripts/run_c3_3_3.py --domain 61 --token c334-final-high-supported --high-preemption
COMPOSE_PROJECT_NAME=fleet-final-auto-supported python3 scripts/run_c3_3_3.py --domain 61 --token c334-final-auto-supported --auto-routes
COMPOSE_PROJECT_NAME=fleet-final-energy-supported python3 scripts/run_c3_3_3.py --domain 61 --token c334-final-energy-supported --energy-policy
COMPOSE_PROJECT_NAME=fleet-final-high-verified python3 scripts/run_c3_3_3.py --domain 61 --token c334-final-high-verified --high-preemption
```

Çalıştırıcı stdout/stderr ve dönüş kodu her koşu için ayrı tutuldu. Image'lar yeniden build edilmeden mevcut Nav2 ve C3.3.3 backend etiketleri kullanıldı. Başlangıçta bağımsız kaynak kopyası `git archive HEAD | tar -x -C /tmp/fleet-c334-final/baseline-src` ile oluşturuldu. Baseline ve ilk observer koşusu bu kopyadan çalıştırıldı. O koşuların container ortamı, runner'ın `--domain 61` değerine rağmen `42` idi. `config/dds.env` düzeltmesinden sonra iki servis için `61` ayrıca çözümlenen config ve Docker inspect ile denetlendi.

İlk kapanış tanısında Docker, birikmiş ağlar nedeniyle yeni alt ağ oluşturamadı. Bu görevde oluşturulan iki baseline projesinin inspect, olay ve veritabanı kanıtı alındıktan sonra yalnız bu projeler `down` ile kaldırıldı. Sonraki koşularda aynı işlem kanıt alındıktan sonra her test projesi için uygulandı.

```sh
# Her çalıştırıcı bitince, kendi proje adı ve ilgili DB dosyası ile
project=fleet-final-high-verified
for service in simulation backend; do
  name="$project-$service-1"
  docker inspect --format '{{.Name}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' "$name"
  start=$(docker inspect --format '{{.State.StartedAt}}' "$name")
  finish=$(docker inspect --format '{{.State.FinishedAt}}' "$name")
  docker events --since "$start" --until "$finish" --filter "container=$name" \
    --filter event=kill --filter event=die \
    --format '{{.TimeNano}} {{.Action}} signal={{index .Actor.Attributes "signal"}} exit={{index .Actor.Attributes "exitCode"}}'
done
docker cp "$project-backend-1:/tmp/c3_3_3_t04-high-e2e.db" /tmp/fleet-c334-final/high-verified.db
docker compose -p "$project" -f docker/compose/docker-compose.dds.yml \
  -f docker/compose/docker-compose.simulation-check.yml \
  -f docker/compose/docker-compose.simulation-c3-3-3.yml down
```

```sql
PRAGMA integrity_check;
SELECT task_id, status, robot_id, assignment_epoch, goal_uuid,
       json_extract(snapshot, '$.created_at'), json_extract(snapshot, '$.preemption_count')
FROM tasks ORDER BY task_id;
SELECT task_id, kind, state, assignment_epoch, goal_uuid, attempts
FROM outbox_events ORDER BY sequence;
SELECT station_id, state, reserved_by, occupied_by FROM reservations ORDER BY station_id;
SELECT count(*) FROM processed_events WHERE outcome='ROUTE_APPLIED';
```

## Nav2 gözlemi ve diyagram

Salt okunur ROS gözlemcisi simulation container'ında ayrı `docker exec -i` ile çalıştırıldı. Her 0,5 sn duvar zamanı örneğinde en yeni `/clock`, robot başına `odom`, `cmd_vel_nav`, `cmd_vel`, `plan`, DWB `evaluation`, `amcl_pose`, map→base TF ve Gazebo `dynamic_pose/info` kaydedildi. İkinci seçkide scan minimum menzili ve yerel costmap ön hattı da kaydedildi. Gerçek pitch, Gazebo quaternion'ından `asin(2 × (w × y − z × x))` ile hesaplandı. Bitiş/başlangıç `/clock` farkı duvar zamanı farkına bölünerek gerçek zaman faktörü örneği çıkarıldı. Odometri gecikmesi `clock − odom.header.stamp` medyanıdır.

```sh
docker exec -i fleet-final-full-1-simulation-1 bash -c \
  'source /opt/ros/humble/setup.bash; python3 -' \
  < /tmp/fleet-c334-final/nav-observe.py > /tmp/fleet-c334-final/full-1-nav.jsonl

npx --offline --yes --package @mermaid-js/mermaid-cli@11.12.0 mmdc \
  -i docs/diagrams/src/safe-preemption.mmd -o docs/diagrams/svg/safe-preemption.svg \
  -c /tmp/fleet-task7/mermaid.json -b white
git diff --check
```

Ham loglar, JSONL gözlemleri, SQLite kopyaları, container incelemeleri ve yeniden çalıştırma betiği yerelde `/tmp/fleet-c334-final/` altında tutuldu.
