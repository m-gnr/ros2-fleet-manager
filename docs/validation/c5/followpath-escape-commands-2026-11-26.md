# C5 — FollowPath kaçışı komutları

Depo kökünden normal başlatıcı çalıştırılır.

```sh
./scripts/start_demo.sh
```

Başlatıcının yazdığı oturum adı `SESSION` olarak kullanılır. API ve UI portları oturumun `session.json` dosyasından alınır. Kontrollü ilerleyememe deneyi boş bir oturumda normal görev API’sini kullanır. Prob, hedef robotu Nav2 hız sınırı üzerinden geçici olarak 0,001 m/s ile sınırlar. Gerçek controller hatasını görünce sınırı kaldırır. Ürün kaçış eklentisi gerçek action sonucuna göre çalışır.

```sh
API_PORT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["api_port"])' "/tmp/$SESSION/session.json")
UI_PORT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ui_port"])' "/tmp/$SESSION/session.json")
docker exec "$SESSION" bash -ec '
  source /opt/ros/humble/setup.bash
  source /c5-cache/install/local_setup.bash
  export PYTHONPATH=/workspace:/workspace/backend:${PYTHONPATH:-}
  exec python3 docker/simulation-warehouse-grid/followpath_escape_probe.py \
    config/fleet.warehouse-30x18.yaml /evidence/live/escape-probe.jsonl \
    --api-port "$1" --origin "http://127.0.0.1:$2" \
    --robot robot_alpha --pickup pick_C2 --dropoff delivery-01
' escape-probe "$API_PORT" "$UI_PORT"
```

Probun çıkış kodu tek başına kabul ölçütü değildir. `simulation.log` içindeki kaçış UUID’si, probun action ve rota kayıtları, Gazebo pozları, `ros.jsonl` ve temas gözlemcisi birlikte incelenir. Oturum `Ctrl+C` ile kapatılır ve `live/shutdown.json` kaydı denetlenir.

## Ham kanıt

| Koşu | Dizin |
|---|---|
| İlk tam koşu, teslim bacağında planner onay timeout’u | `/tmp/c5-demo-20261125T233312Z-7fbcd945f080/live/` |
| Son canlı kabul | `/tmp/c5-demo-20261125T233618Z-6a1591e247fa/live/` |

İki dizinde `escape-probe.jsonl`, `simulation.log`, `ros.jsonl`, `executor_robot_alpha.log`, `shutdown.json` ve `fleet.sqlite3` bulunur. Oturum adı UTC damgası içerir.

## Regresyon

Son demo colcon install dizini `OVERLAY` olarak belirtilir. Koşuda `/tmp/ros2-fleet-c5-overlay/a33b7b930246d6508dfb8e19e880325ba0cbf5377f531af4cb78c4641b7b163a/install` kullanıldı.

```sh
docker run --rm --network none -e ROS_DOMAIN_ID=173 \
  -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  -v "$PWD:/workspace:ro" -v "$OVERLAY:/overlay:ro" -w /workspace \
  ros2-fleet-c5-validation:humble-fortress bash -ec '
  source /opt/ros/humble/setup.bash
  source /overlay/local_setup.bash
  export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:${PYTHONPATH:-}
  python3 -m pytest -q -p no:cacheprovider tests/test_config.py tests/test_peer_awareness_config.py \
    tests/test_warehouse_operations.py tests/test_executor_safety.py tests/test_executor_state_machine.py \
    tests/test_traffic_child_binding.py tests/test_traffic_core.py tests/test_executor_ros2_node.py \
    tests/test_executor_lifecycle_integration.py tests/test_executor_safety_ros2.py
'
git diff --check
```

Son seçkinin logu `/tmp/c5-followpath-escape-final-tests-20261126.log`. Kalan `test_distributed_profile_clearance_capacity_and_old_profiles` testi, `git archive b3dcad9` ile alınan ayrı kaynak kopyasında aynı Humble imajı ve checkout’a ait şema ile tekrarlandı. Taban logu `/tmp/c5-followpath-escape-head-tests-20261126.log`.
