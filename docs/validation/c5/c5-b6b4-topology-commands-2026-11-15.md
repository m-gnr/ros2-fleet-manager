# C5-B6B.4 — Komut ve kanıt eki

15 Kasım 2026. Komutlar `/Users/murat/develop/ros2-fleet-manager-c5-a-demo-integration` depo kökünde çalıştırıldı. Image: `ros2-fleet-c5-validation:humble-fortress`, ID `sha256:7fb7e7fc4aebe0d2b4097752e9b470e30d8ea7a8126bb1dee87d03f30330609d`. Image build/pull veya B5 native build yapılmadı. Çalışan başka container'a exec/stop gönderilmedi.

## Hedefli ROS ve model testleri

```sh
docker run --rm --network none -e ROS_DOMAIN_ID=93 \
  -v "$PWD:/repo:ro" --entrypoint /bin/bash \
  ros2-fleet-c5-validation:humble-fortress \
  /repo/docker/experiments/c5-b6b4/run.sh \
  > docs/validation/c5/c5-b6b4-topology-2026-11-15/targeted-tests.txt 2>&1
```

**Sonuç:** exit 0, **46 passed, 0 skip**, 5.78 s. Domain 93 yalnız izole test ortamıdır. Runner `ROS_DOMAIN_ID` ister; localhost-only DDS ve süreç başına ayrı `IGN_PARTITION` kurar, kaynak mount'u salt okunurdur. `/opt/ros/humble/setup.bash` nounset-uyumlu olmadığından yalnız source sırasında `set +u` kullanılır. İlk setup denemesi bu yüzden test başlamadan exit 1 verdi; ürün/env değişmedi.

Runner yalnız `docker/experiments/c5-b6b4/test_ros_topology.py`, `tests/test_traffic_motion_gate.py`, `tests/test_b6b4_topology.py` seçkisini çalıştırır. Bütün fake node'lar ve child-process bridge/gate'leri koşu sonunda kapatılır. İlk 45 testlik geliştirme koşusu PASS; ek process/fixture denetimleri sonrası son 46 testlik koşu esastır. [İlk wrapper-kill hatası](c5-b6b4-topology-2026-11-15/initial-process-control-failure.txt) ve [graph lease kontrol hatası](c5-b6b4-topology-2026-11-15/discovery-lease-test-failure.txt) korunur. Sırasıyla süreç grubu kill ve süreç/çıktı/graph ayrımıyla düzeltildi. Bu testler hiçbir Gazebo server veya actuator başlatmaz.

## Kurulu kaynak ve varsayılan dosya kontrolü

```sh
docker run --rm --network none --entrypoint /bin/bash \
  ros2-fleet-c5-validation:humble-fortress -c \
  'dpkg-query -W ros-humble-nav2-bringup ros-humble-nav2-controller ros-humble-nav2-behaviors ros-humble-ros-gz-bridge; sha256sum /opt/ros/humble/share/nav2_bringup/launch/navigation_launch.py; cat /opt/ros/humble/share/nav2_bringup/launch/navigation_launch.py' \
  > docs/validation/c5/c5-b6b4-topology-2026-11-15/installed-navigation.txt
rg -n 'cmd_vel|create_publisher.*Twist|navigation_launch|bringup_launch|diff-drive-system|motion_envelope' \
  ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py \
  docker/simulation-warehouse-grid/serve.py docker/simulation-c3-3-3/check.py \
  config/fleet.warehouse-30x18.yaml \
  > docs/validation/c5/c5-b6b4-topology-2026-11-15/source-topology.txt
```

İki komut exit 0. Kurulu bridge executable `ros_gz_bridge parameter_bridge`; `ros_ign_bridge` paketi bu image'da yoktur. Paket keşfi okuma işlemidir. [Kaynak](c5-b6b4-topology-2026-11-15/installed-navigation.txt), [satır envanteri](c5-b6b4-topology-2026-11-15/source-topology.txt). `baseline.json` 10 korunacak kaynağın değişiklik öncesi SHA-256 değerlerini içerir; hedefli test bunları byte düzeyinde yeniden karşılaştırdı. Bu, C5-A canlı regresyon koşusu değildir.

Test çıktısındaki `B6B4_REPORT=` JSON kaydı `report.json` içine çıkarıldı; endpoint adları gerçek ROS graph sorgusundan gelir. Normal graph'ta tek final publisher; saldırı enjeksiyonunda ikincisi teknik olarak mümkündür. Gate kill sonrasında graph'ın hâlâ 1 göstermesi de kaydedilir.

## Doküman/diyagram kontrolleri

```sh
node /Users/murat/.npm/_npx/bb964472b4759b27/node_modules/@mermaid-js/mermaid-cli/src/cli.js \
  -i docs/diagrams/src/traffic-single-output.mmd \
  -o docs/diagrams/svg/traffic-single-output.svg -b transparent
git diff --check
```

Mermaid CLI host cache yolu bu makineye özgüdür; ürün kurulum komutu değildir. Exit 0; SVG XML ve yeni Markdown dosyalarının yerel bağlantı varlıkları ayrıca Python ile denetlendi. Bu kontroller ROS/aktüatör fiziksel kabulü değildir.
