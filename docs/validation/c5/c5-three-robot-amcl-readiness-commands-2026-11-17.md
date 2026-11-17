# C5 — Üç robot AMCL readiness komut eki — 17 Kasım 2026

Çalışma ağacı: `/private/tmp/ros2-fleet-manager-c5-alpha-beta-stable`  
Dal: `demo/alpha-beta-stable`  
Canlı oturum: `c5-20261117T065353Z-77741f4968`  
Container image: `ros2-fleet-c5-validation:humble-fortress`

## Çalıştırılan kontroller

```sh
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
docker inspect -f '{{.Name}} {{.Config.Image}} {{range .Config.Env}}{{println .}}{{end}}' c5-20261117T065353Z-77741f4968
docker exec c5-20261117T065353Z-77741f4968 bash -lc 'source /opt/ros/humble/setup.bash; ros2 topic list | sort | grep -E "(amcl_pose|/scan|/odom|/tf$|/clock)"'
```

Yukarıdaki topic listesi alpha, beta ve gamma için `amcl_pose`, `odom`, `scan`, namespace `tf` ve ortak `/clock` gösterdi.

Etkin parametreler, `rcl_interfaces/srv/GetParameters` ile üç `/robot_{alpha,beta,gamma}/amcl/get_parameters` servisine tek ROS 2 probe üzerinden soruldu: `update_min_d`, `update_min_a`, `transform_tolerance`, `tf_broadcast`, `save_pose_rate`. Her üç düğüm aynı değerleri verdi: `0.1`, `0.1`, `1.0`, `true`, `0.5`.

Yaklaşık 8 saniyelik pasif ROS probe; üç namespaced `/amcl_pose`, `/odom`, `/scan`, `/tf` ve `/clock` abonesi açtı. Mesaj damgaları ve sayıları kaydedildi; `RobotReader`/`Telemetry` ile TF güncelliği gözlendi. Aynı probe lifecycle `GetState` servislerini ve `NavigateToPose` action server keşfini okudu. İlk graph/TF keşif örnekleri beklemeye alındı; gözlem penceresinin sonunda üç robotun TF snapshot'ı `LIVE`, Nav2 lifecycle/action koşulları hazırdı. Probe hiçbir goal göndermedi.

```sh
curl -fsS http://127.0.0.1:21482/api/health
curl -fsS http://127.0.0.1:21482/api/robots
curl -fsS http://127.0.0.1:21482/api/tasks
cat /tmp/c5-20261117T065353Z-77741f4968/live/startup-readiness.json
```

Son REST gözleminde health `source=LIVE`; alpha/beta/gamma `IDLE`, telemetry/pose/battery `LIVE`, `active_task_id=null`; task listesi `total=0` döndürdü. Readiness dosyası `status=READY`, `current_status=WAITING` ve 3 × AMCL/Nav2/TF ilk-ready zamanını içeriyordu. Anlık WAITING nedeni alanı yoktu.

Hiçbir görev oluşturulmadı, hareket komutu/Nav2 goal gönderilmedi, canlı servis restart edilmedi ve AMCL parametresi değiştirilmedi.
