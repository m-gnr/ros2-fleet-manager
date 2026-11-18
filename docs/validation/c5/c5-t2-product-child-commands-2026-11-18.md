# C5-T2 komut ve kanıt eki

Komutlar workspace kökünden çalıştırıldı. Konteyner workspace mount'u salt
okunur; yeni build dizini `/tmp/c5-t2-build-20261118`. Son canlı test ayrı
domain 218, partition `c5-t2-20261118-identity-a6` ve Docker bridge ağı
kullandı; host portu yayımlanmadı. Tek canlı simülasyon vardı. Test image'ı
`c5-b6b5-build:local`, ROS test/build image'ı
`ros2-fleet-c5-validation:humble-fortress`; çözülmüş image/binary SHA'ları
[isolation.json](c5-t2-product-child-2026-11-18/isolation.json) içindedir.

## Son host seçki — exit 0, 350 PASS

```bash
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator /tmp/c5-perf-test-venv/bin/python -m pytest -q -p no:cacheprovider tests/test_traffic_product_child.py tests/test_traffic_child_binding.py tests/test_peer_awareness_config.py tests/test_traffic_protocol.py tests/test_traffic_motion_gate.py tests/test_traffic_core.py tests/test_fleet_manager_outbox.py tests/test_fleet_manager_domain.py tests/test_executor_safety.py tests/test_executor_state_machine.py tests/test_b6b4_topology.py tests/test_c43_station_dispatch.py tests/test_c44_charging.py tests/test_ros2_route_resolver.py
```

## Native build, ROS Python ve Peer regresyonu

Salt okunur `/workspace` ve yazılabilir `/build` mount'lu ROS test image'ı
içinde aşağıdaki komutlar çalıştırıldı. İlk build, yeni IDL ve BT observer
paketini derler; build/up varsayımına dayanılmaz. Son ROS seçki ayrıca
domain 223, localhost-only, network none ile tekrarlandı: **66 PASS / exit 0**.
Peer testinin **10 gtest / 11 wrapper dahil PASS / exit 0** sonucu ayrıdır.

```bash
source /opt/ros/humble/setup.bash
colcon --log-base /build/log build --base-paths interfaces/fleet_interfaces ros2_ws/src/fleet_nav2_observer ros2_ws/src/fleet_perception --build-base /build/build --install-base /build/install
source /build/install/local_setup.bash
export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:$PYTHONPATH
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python3 -m pytest -q -p no:cacheprovider tests/test_traffic_product_child.py tests/test_traffic_product_child_ros2.py tests/test_traffic_protocol_ros2.py tests/test_executor_ros2_node.py tests/test_executor_lifecycle_integration.py tests/test_executor_safety_ros2.py
colcon --log-base /build/log test --build-base /build/build --install-base /build/install --packages-select fleet_perception --event-handlers console_direct+
colcon --log-base /build/log test-result --test-result-base /build/build --verbose
```

## Native sıfır sınırı — 2 program, exit 0

Değişmeyen T1 native build'i salt okunur `/native` mount'uyla kullanıldı.

```bash
docker run --rm --name c5-t2-native-check --network none -v /tmp/c5-t1-native-zero-20261118:/native:ro c5-b6b5-build:local bash -ec '/native/authorization-test; /native/native-test'
```

## Son gerçek Nav2 kimlik koşusu — a6, exit 0

```bash
docker run --rm --init --name c5-t2-live-identity --network bridge --workdir /workspace --env ROS_DOMAIN_ID=218 --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp --env ROS_LOCALHOST_ONLY=0 --env IGN_PARTITION=c5-t2-20261118-identity-a6 -v /Users/murat/develop/ros2-fleet-manager-demo:/workspace:ro -v /tmp/c5-t2-build-20261118:/build:ro -v /tmp/c5-t1-native-zero-20261118:/b6b7-native:ro -v /tmp/c5-t2-live-20261118:/evidence c5-b6b5-build:local bash -ec 'source /opt/ros/humble/setup.bash; source /build/install/local_setup.bash; export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH; python3 docker/experiments/c5-t2/identity.py config/fleet.warehouse-30x18.yaml /evidence/a6'
```

a1 aynı mount'larla network none, localhost-only, domain 213 kullandı.
a2–a5 bridge/localhost=0 ve sırasıyla 214–217 domain'leriydi. Fixture'ın
test koşulları/düzeltmeleri ana raporda açık tutulur. Ham hatalar ve ara
koşu logları [checks](c5-t2-product-child-2026-11-18/checks/) ve
[live](c5-t2-product-child-2026-11-18/live/) altındadır. `.gz` dosyaları
orijinal byte'ları kayıpsız korur; manifest saklanan byte'ları hash'ler.

## Diyagram ve son kapı

Mermaid CLI 11.12.0 yerel cache'inden SVG ve PNG üretildi; PNG görsel olarak
okunabilirlik/taşma açısından incelendi. Test kodu/source, eski kanıtların
manifestleri, secrets taraması, default None/launcher izolasyonu ve kaynak
whitespace kontrolü commit öncesi tekrar denetlendi. Ham build loglarındaki
whitespace kayıpsız `.gz` arşivde korunur. Son kontroller ve manifest
[kanıt dizininde](c5-t2-product-child-2026-11-18/) tutulur.

Kaynak dayanağı: kurulu Humble `nav2_behavior_tree` 1.1.20 header'ı ve
[upstream BtActionNode](https://github.com/ros-navigation/navigation2/blob/humble/nav2_behavior_tree/include/nav2_behavior_tree/bt_action_node.hpp),
[FollowPathAction](https://github.com/ros-navigation/navigation2/blob/humble/nav2_behavior_tree/plugins/action/follow_path_action.cpp).
Kurulu sürüm/binary incelemesi çalışma kaynağıdır; upstream dalının ileride
değişmeyeceği varsayılmadı.
