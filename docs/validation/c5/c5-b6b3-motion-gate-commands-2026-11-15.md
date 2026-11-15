# C5-B6B.3 — Komut eki

15 Kasım 2026. Aşağıdaki komutlar `/Users/murat/develop/ros2-fleet-manager-c5-a-demo-integration` depo kökünde çalıştırıldı. Image ID: `sha256:7fb7e7fc4aebe0d2b4097752e9b470e30d8ea7a8126bb1dee87d03f30330609d`. Ağ kapalı, kaynak mount salt okunur; build veya ROS/Gazebo runtime yok.

```sh
docker run --rm --network none -v "$PWD:/repo:ro" --entrypoint /bin/bash \
  ros2-fleet-c5-validation:humble-fortress -c \
  'cd /repo; export PYTHONPATH=/repo:/repo/ros2_ws/src/fleet_robot_executor; export PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; python3 -m pytest -p no:cacheprovider -q tests/test_traffic_motion_gate.py tests/test_traffic_protocol.py tests/test_traffic_core.py' \
  > docs/validation/c5/c5-b6b3-motion-gate-2026-11-15/offline-tests.txt 2>&1
```

Sonuç: **69 passed**, exit 0, 0 skip. [Çıktı](c5-b6b3-motion-gate-2026-11-15/offline-tests.txt). Host geliştirme koşuları 26/26 ve 67/67 geçti; bunlar son koşunun yerine konmaz.

Kurulu topoloji okuması:

```sh
docker run --rm --network none --entrypoint /bin/bash \
  ros2-fleet-c5-validation:humble-fortress -c \
  'dpkg-query -W ros-humble-nav2-bringup ros-humble-nav2-controller ros-humble-nav2-behaviors; sha256sum /opt/ros/humble/share/nav2_bringup/launch/navigation_launch.py; cat /opt/ros/humble/share/nav2_bringup/launch/navigation_launch.py' \
  > docs/validation/c5/c5-b6b3-motion-gate-2026-11-15/installed-navigation.txt
rg -n 'cmd_vel|create_publisher.*Twist|navigation_launch|bringup_launch|diff-drive-system|motion_envelope' \
  ros2_ws/src docker/simulation-warehouse-grid/serve.py docker/simulation-c3-3-3/check.py \
  fleet_config/warehouse_assets.py config/fleet.warehouse-30x18.yaml \
  > docs/validation/c5/c5-b6b3-motion-gate-2026-11-15/source-topology.txt
```

İki komut exit 0. Ayrıca tüm docker test araçlarındaki hız yayınları `rg` ile okundu; C4.1 battery_check ve stage12_probe doğrudan yayıncıları tasarımda belirtildi. Canlı graph toplanmadı.

Diyagram yerel mevcut Mermaid CLI ile üretildi:

```sh
node /Users/murat/.npm/_npx/bb964472b4759b27/node_modules/@mermaid-js/mermaid-cli/src/cli.js \
  -i docs/diagrams/src/traffic-motion-gate.mmd \
  -o docs/diagrams/svg/traffic-motion-gate.svg -b transparent
git diff --check
```

Çıkış 0. Mermaid cache yolu bu host'a özgüdür; ürün kurulum talimatı değildir. Yeni Markdown yerel bağlantıları dosya varlığıyla denetlendi. SVG XML parse kontrolü geçti. Bu kontroller fiziksel veya ROS çalışma kanıtı değildir.
