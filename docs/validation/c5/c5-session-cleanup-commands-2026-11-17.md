# C5 güvenli session cleanup — komut ve kanıt eki — 17 Kasım 2026

Bu ek 17 Kasım'da gerçek ortamda çalıştırılan cleanup, cold-start ve son test komutlarını kaydeder. Oturum cleanup script'i container silmez; yalnız doğrulanmış C5 servislerini durdurur.

## Ön kontrol ve cleanup

```bash
git status --short
git diff -- config/fleet.warehouse-30x18.yaml
python3 scripts/c5_session_cleanup.py --workspace "$PWD" --audit-dir /tmp/c5-session-cleanup
```

İlk cleanup denemesi görev kataloğunun ingress kapatıldıktan sonra `503` dönmesini başarısızlık saydı; o aşamada container durdurulmadı. Probe, API health'in `LIVE` kaldığını ve catalog'un devre dışı olduğunu kabul edecek şekilde düzeltildi. Sonraki gerçek cleanup PASS oldu. Her eski C5 oturumunda task ingress kapatıldı, API robot/görev durumu kaydedildi, Nav2 cancel-all ve odometri/poz duruşu doğrulandı; sonra `docker stop --time 35` uygulandı.

Cleanup audit dosyası:

```text
/tmp/c5-session-cleanup/cleanup-72c16e1e967b4f098234037346ba8640.json
```

Container incelemesinde Gamma `exit 137`, `OOMKilled=false`; stable ve manual container'ları exit 0 verdi. Gamma'nın `shutdown.json`'ı yoktu. Diğer iki oturumun shutdown kaydı tüm alt süreçlerde exit 0 gösterdi. Üç container da durdurulmuş olarak korundu; `docker rm`, `docker kill`, volume silme veya prune komutu çalıştırılmadı.

## Cold-start ve canlı gözlem

```bash
scripts/run_c5_dashboard.sh demo
curl -fsS http://127.0.0.1:21482/api/health
curl -fsS http://127.0.0.1:21482/api/robots
curl -fsS http://127.0.0.1:21482/api/tasks
docker inspect c5-20261117T065353Z-77741f4968 --format '{{.State.Status}} {{.State.ExitCode}} {{.HostConfig.PortBindings}}'
```

Sonuç: session `c5-20261117T065353Z-77741f4968`, ROS domain `206`, container running, API `21482`, GUI `21484`, scene bridge `21483`. Health `LIVE`; Alpha/Beta/Gamma `IDLE`/telemetry `LIVE`, aktif görev yok; görev listesi boş. Gerçek startup readiness JSON'unda her robot AMCL, Nav2 ve TF fazlarını geçti. Chrome'da `3/3 TF LIVE` gözlendi. Task POST yapılmadı.

Sonradan yapılan read-only canlı ROS kontrolü:

```bash
docker exec c5-20261117T065353Z-77741f4968 bash -lc 'source /opt/ros/humble/setup.bash; export ROS_DOMAIN_ID=206; for robot in alpha beta gamma; do ros2 lifecycle get /robot_${robot}/amcl; ros2 lifecycle get /robot_${robot}/bt_navigator; ros2 action info /robot_${robot}/navigate_to_pose; done'
docker exec c5-20261117T065353Z-77741f4968 bash -lc 'source /opt/ros/humble/setup.bash; export ROS_DOMAIN_ID=206; for robot in alpha beta gamma; do timeout 4 ros2 topic hz /robot_${robot}/amcl_pose; done'
```

Nav2 lifecycle `active [3]`, her action server için 1 server ve üç namespace'li TF topic'inde canlı örnek doğrulandı. AMCL lifecycle aktifti; fakat 4 saniyede yeni `/amcl_pose` örneği görülmedi ve observer `current_status=WAITING` kaydetti. Başlangıçta readiness fazları geçmiştir; AMCL'nin sonradan sürdürülen tazeliği doğrulanmamış olduğundan raporun genel sonucu PARTIAL'dır.

## Testler ve statik doğrulama

```bash
python3 -m py_compile scripts/c5_session_cleanup.py scripts/c5_launch_guard.py scripts/c5_demo_start.py docker/simulation-warehouse-grid/c5_safe_stop_probe.py
bash -n scripts/run_c5_dashboard.sh
git diff --check
python3 -m fleet_config config/fleet.warehouse-30x18.yaml
python3 docker/simulation-warehouse-grid/test_startup_readiness.py
python3 -m unittest tests.test_c5_session_cleanup tests.test_docker_simulation_preflight -v
```

Sonuç: syntax/compile ve diff kontrolleri geçti; YAML profili 3 robotla geçerli; startup readiness 3/3; cleanup suite 12/12 ve preflight suite 4/4, toplam 16/16.

## İlgili sınırlar

- Cleanup testleri tek/çoklu eski oturum, Nav2/Executor sonlanması, aynı Git deposunun başka worktree'si, başka projenin korunması, SQLite/log/volume koruması, duruş belirsizliğinde fail-closed, başarısız cleanup'ta launch blokajı, benzersiz session/domain, launcher yarışı, orphan GUI ve PID/start-time uyuşmazlığını kapsar.
- Gamma exit 137, kontrollü duruşun başarısız olduğu anlamına gelmez. Robot duruşu container stop öncesi doğrulandı; container'ın Docker grace deadline sonrasında zorla sonlanması ayrı kaydedildi.
