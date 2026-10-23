# Aşama B3 Yeniden Koşusu Komut ve Çıktı Eki

[Ana B3 yeniden doğrulama kaydı](simulation-stage-b3-retry-2026-10-23.md).

---

## 1. Git İnceleme Raporu (Salt Okunur)

### 1.1 `git reflog` (Son 30 İşlem)

```text
19623b9 (HEAD -> main, origin/main, origin/HEAD) HEAD@{0}: commit (merge): Merge remote-tracking branch 'origin/main'
6c96554 HEAD@{1}: rebase (abort): returning to refs/heads/main
b4d1dd7 HEAD@{2}: pull --rebase (start): checkout b4d1dd752d2222165b7f45173d0da0d8cb0341c7
6c96554 HEAD@{3}: commit: feat: Aşama B3 iki robotlu Nav2 simülasyon doğrulaması
d816bec HEAD@{4}: commit: test: AMCL gerçek yakınsama ve Gazebo ground truth doğrulaması (Bölüm B)
c48b7be HEAD@{5}: commit: Aşama B2: tek robotlu Nav2 simülasyon doğrulaması
3100a78 HEAD@{6}: reset: moving to HEAD~1
b4d1dd7 HEAD@{7}: commit: test: nav2 lifecycle, AMCL lidar testleri yapıldı
3100a78 HEAD@{8}: commit: test: docker, simülasyon lidar testleri gerçekleştirildi
b1797b5 HEAD@{9}: commit: test: docker gazebo headless lidar testi yapıldı
8fc10af HEAD@{10}: commit: test: headless gazebo + ros bridge + arm64 docker iletişim testi gerçekleştirildi
ee063cc HEAD@{11}: commit: test: container to container action probe test
208b3d0 HEAD@{12}: commit: dds mesaj alma  testleri gerçekleştirildi
189fd96 HEAD@{13}: commit: transition record ve agent guidelines eklendi
f5a869d HEAD@{14}: commit: ajan takimatları ve dokümantasyonlar eklendi
c5a11e5 HEAD@{15}: commit: Fast API & Websocket & API mimari planları eklendi && mimari bağlantıları güncellendi
507fa74 HEAD@{16}: commit: fleet manager ve multi-robot ros mimarisi mimarileri pdf formatında yüklendi
3741f8f HEAD@{17}: commit: docs: initialize project documentation and scope
1fe94d3 HEAD@{18}: clone: from https://github.com/m-gnr/ros2-fleet-manager
```

### 1.2 `git log --oneline --graph --all -n 15`

```text
*   19623b9 (HEAD -> main, origin/main, origin/HEAD) Merge remote-tracking branch 'origin/main'
|\  
| * b4d1dd7 test: nav2 lifecycle, AMCL lidar testleri yapıldı
* | 6c96554 feat: Aşama B3 iki robotlu Nav2 simülasyon doğrulaması
* | d816bec test: AMCL gerçek yakınsama ve Gazebo ground truth doğrulaması (Bölüm B)
* | c48b7be Aşama B2: tek robotlu Nav2 simülasyon doğrulaması
|/  
* 3100a78 test: docker, simülasyon lidar testleri gerçekleştirildi
* b1797b5 test: docker gazebo headless lidar testi yapıldı
* 8fc10af test: headless gazebo + ros bridge + arm64 docker iletişim testi gerçekleştirildi
* ee063cc test: container to container action probe test
* 208b3d0 dds mesaj alma  testleri gerçekleştirildi
* 189fd96 transition record ve agent guidelines eklendi
* f5a869d ajan takimatları ve dokümantasyonlar eklendi
* c5a11e5 Fast API & Websocket & API mimari planları eklendi && mimari bağlantıları güncellendi
* 507fa74 fleet manager ve multi-robot ros mimarisi mimarileri pdf formatında yüklendi
* 3741f8f docs: initialize project documentation and scope
```

### 1.3 `git show c48b7be --stat`

```text
commit c48b7be2c93a10e7024a051fcc5172e17913e025
Author: m-gnr <m_gnr@icloud.com>
Date:   Fri Oct 23 16:04:05 2026 +0300

    Aşama B2: tek robotlu Nav2 simülasyon doğrulaması

 config/map/map.pgm                                 | Bin 0 -> 57615 bytes
 config/map/map.yaml                                |   7 +
 config/simulation-nav2-check.json                  |  36 ++
 config/simulation-nav2-check.schema.json           | 120 +++++
 config/simulation-nav2-params.yaml                 | 331 +++++++++++++
 docker-compose.simulation-nav2-check.yml           |  25 +
 docker/simulation-nav2-check/Dockerfile            |   7 +
 docker/simulation-nav2-check/check.py              | 518 +++++++++++++++++++++
 docker/simulation-nav2-check/test_config.py        |  42 ++
 docker/simulation-nav2-check/tf_helper.py          |  61 +++
 docs/simulation-stage-b2-2026-10-23.md             |  76 +++
 docs/simulation-stage-b2-commands-2026-10-23.md    | 469 +++++++++++++++++++
 .../simulation-stage-b2-continuation-2026-10-23.md | 134 ++++++
 ...on-stage-b2-continuation-commands-2026-10-23.md | 360 ++++++++++++++
 14 files changed, 2186 insertions(+)
```

### 1.4 `git reset --soft HEAD~1` Analizi ve Raporu

1. **Hangi Commit Geri Alındı?**:
   - `git reflog` çıktısındaki `HEAD@{6}: reset: moving to HEAD~1` işleminde geri alınan commit, `HEAD@{7}` konumundaki `b4d1dd7` ("test: nav2 lifecycle, AMCL lidar testleri yapıldı") commit'idir.
2. **İçeriği B2 Commit'ine Karıştı mı?**:
   - **Evet, içeriği doğrudan ve tamamen B2 commit'ine (`c48b7be`) taşınmıştır.**
   - `--soft` parametresi kullanıldığı için çalışma dizini ve sahnelenmiş alan (staged/index) korunmuş, `b4d1dd7` içerisindeki tüm dosyalar (map, YAML konfigürasyonları, JSON şemaları, `check.py`, `tf_helper.py` ve dokümantasyonlar) sahnelenmiş olarak kalmıştır.
   - Ardından `simulation-stage-b2-2026-10-23.md` ve `simulation-stage-b2-continuation-2026-10-23.md` dosyalarındaki AMCL başlangıç pozu ve odometri ifadelerinde küçük metin düzeltmeleri yapılmış ve tamamı `c48b7be` ("Aşama B2: tek robotlu Nav2 simülasyon doğrulaması") başlığıyla yeniden commit edilmiştir.
   - Ancak `b4d1dd7` commit'i daha önce uzak sunucuya (`origin/main`) push edilmiş olduğu için, yerelde reset yapılıp `c48b7be`, `d816bec`, `6c96554` commit'leri oluşturulduktan sonra uzak sunucuyla senkronizasyon sırasında dallanma oluşmuş ve bu durum `19623b9` birleştirme (merge) commiti ile sonlanmıştır.
   - Kullanıcı talimatı gereği bu durum üzerinde herhangi bir düzeltme (reset/rebase) yapılmamış, salt okunur olarak raporlanmıştır.

---

## 2. Birim Testleri ve Yapılandırma Doğrulaması

```sh
docker run --rm -v $(pwd)/config:/config:ro -v $(pwd)/docker/simulation-b3-retry:/opt/simulation-b3-retry:ro -w /opt/simulation-b3-retry ros2-fleet-simulation-nav2-check:humble-fortress python3 -m unittest discover -s /opt/simulation-b3-retry -p "test_*.py"
```

Çıkış kodu: 0

```text
...
----------------------------------------------------------------------
Ran 3 tests in 0.009s

OK
```

Compose dosyası doğrulaması:

```sh
env DDS_TEST_PAYLOAD=test-config docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-b3-retry.yml config
```

Çıkış kodu: 0

---

## 3. Canlı Koşu 1 (`simulation-b3-retry-20261023-01`)

```sh
python3 scripts/run_b3_retry.py --token simulation-b3-retry-20261023-01 --domain 45
```

Çıkış kodu: 0

### 3.1 Backend JSON Olayları

```json
{"event": "CONFIG_VALID", "role": "backend", "token": "simulation-b3-retry-20261023-01"}
{"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp", "token": "simulation-b3-retry-20261023-01"}
{"event": "WAITING_FOR_CLOCK_AND_SENSORS"}
{"event": "CLOCK_AND_SENSORS_OK", "clock": 1.81, "robot_1_scans": 10, "robot_2_scans": 10, "robot_1_odom_frame": "robot_1/odom", "robot_2_odom_frame": "robot_2/odom", "robot_1_gt": [1.000000005689777, 1.5, 0.1999998861964761, 1.8930741510996536e-20], "robot_2_gt": [-1.000000005689777, -1.5, 0.1999998861964761, -3.141592653589587]}
{"event": "CHECKING_LIFECYCLE_STATES"}
{"event": "LIFECYCLE_ACTIVE", "total_nodes": 12, "states": {"/robot_1/map_server": "active", "/robot_1/amcl": "active", "/robot_1/controller_server": "active", "/robot_1/planner_server": "active", "/robot_1/behavior_server": "active", "/robot_1/bt_navigator": "active", "/robot_2/map_server": "active", "/robot_2/amcl": "active", "/robot_2/controller_server": "active", "/robot_2/planner_server": "active", "/robot_2/behavior_server": "active", "/robot_2/bt_navigator": "active"}}
{"event": "CHECKING_TF_CHAINS"}
{"event": "TF_CHAINS_VALID", "robot_1_trans": [1.0, 1.5000000000000002], "robot_2_trans": [-1.0, -1.5000000000000002]}
{"event": "CHECKING_AMCL_INITIAL_POSES"}
{"event": "AMCL_INITIAL_POSE", "robot": "robot_1", "x": 1.0, "y": 1.5000000000000002, "error_m": 2.220446049250313e-16}
{"event": "AMCL_INITIAL_POSE", "robot": "robot_2", "x": -1.0, "y": -1.5000000000000002, "error_m": 2.220446049250313e-16}
{"event": "AMCL_INITIAL_POSES_VALID"}
{"event": "WAITING_FOR_ACTION_SERVERS"}
{"event": "SENDING_NAVIGATE_TO_POSE_GOAL", "robot": "robot_1", "target_x": 2.5, "target_y": 1.5, "target_yaw": 0.0}
{"event": "SENDING_NAVIGATE_TO_POSE_GOAL", "robot": "robot_2", "target_x": -2.5, "target_y": -1.5, "target_yaw": 3.14159265359}
{"event": "GOAL_ACCEPTED", "robot": "robot_1"}
{"event": "GOAL_ACCEPTED", "robot": "robot_2"}
{"event": "NAVIGATION_WINDOW_START", "monotonic": 380.570487214, "wall_time": 1792763581.3792248}
{"event": "MONITORING_PARALLEL_NAVIGATION"}
{"event": "NAVIGATION_PROGRESS", "robot_1_done": false, "robot_2_done": false, "inter_robot_dist_m": 4.1602252114341765, "min_inter_robot_dist_m": 3.60555128177623}
{"event": "NAVIGATION_WINDOW_END", "monotonic": 386.1302888, "wall_time": 1792763586.9390264}
{"event": "GOALS_COMPLETED_CHECKING_RESULTS"}
{"event": "DESTINATION_REACHED", "robot": "robot_1", "status": 4, "dist_gt_m": 0.17146489880712512, "dist_amcl_m": 0.2938988727341325, "dist_odom_m": 1.9238241955423494, "tolerance_m": 0.35, "primary_eval": "PASS"}
{"event": "DESTINATION_REACHED", "robot": "robot_2", "status": 4, "dist_gt_m": 0.2001543526901038, "dist_amcl_m": 0.25770107392418484, "dist_odom_m": 4.070290325346218, "tolerance_m": 0.35, "primary_eval": "PASS"}
{"event": "BACKEND_CONTAINER_CGROUP", "source": "backend_container_cgroup", "run_duration_s": 11.4, "scan_rates_hz": {"robot_1": 5.0, "robot_2": 5.0}, "total_scans": {"robot_1": 44, "robot_2": 44}, "min_inter_robot_distance_m": 3.6056, "peak_memory_mb": 84.0, "current_memory_mb": 83.95, "cpu_usage_usec": 4382226}
{"event": "B3_PASS", "token": "simulation-b3-retry-20261023-01", "robot_1_gt_m": 0.17146489880712512, "robot_2_gt_m": 0.2001543526901038, "robot_1_amcl_m": 0.2938988727341325, "robot_2_amcl_m": 0.25770107392418484, "min_inter_robot_distance_m": 3.6056, "backend_cgroup_peak_mb": 84.0}
```

### 3.2 Host `docker stats` Kaynak Ölçüm Raporu

```json
{
  "run_token": "simulation-b3-retry-20261023-01",
  "domain_id": 45,
  "exit_code": 0,
  "run_duration_s": 15.73,
  "nav_duration_s": 5.56,
  "entire_run_stats": {
    "simulation-b3-retry-simulation": {
      "sample_count": 7,
      "avg_cpu_pct": 154.63,
      "peak_cpu_pct": 262.6,
      "peak_mem_mb": 611.5
    },
    "simulation-b3-retry-backend": {
      "sample_count": 6,
      "avg_cpu_pct": 42.31,
      "peak_cpu_pct": 57.14,
      "peak_mem_mb": 48.25
    }
  },
  "navigation_window_stats": {
    "simulation-b3-retry-simulation": {
      "sample_count": 3,
      "avg_cpu_pct": 143.14,
      "peak_cpu_pct": 168.7,
      "peak_mem_mb": 459.6
    },
    "simulation-b3-retry-backend": {
      "sample_count": 2,
      "avg_cpu_pct": 55.38,
      "peak_cpu_pct": 57.14,
      "peak_mem_mb": 48.25
    }
  }
}
```

### 3.3 Koşu 1 Temizlik Komutu

```sh
env DDS_TEST_PAYLOAD=cleanup docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-b3-retry.yml down -v --remove-orphans
docker network prune -f
```

Çıkış kodu: 0

---

## 4. Canlı Koşu 2 (`simulation-b3-retry-20261023-02`)

```sh
python3 scripts/run_b3_retry.py --token simulation-b3-retry-20261023-02 --domain 46
```

Çıkış kodu: 0

### 4.1 Backend JSON Olayları

```json
{"event": "CONFIG_VALID", "role": "backend", "token": "simulation-b3-retry-20261023-02"}
{"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp", "token": "simulation-b3-retry-20261023-02"}
{"event": "WAITING_FOR_CLOCK_AND_SENSORS"}
{"event": "CLOCK_AND_SENSORS_OK", "clock": 1.808, "robot_1_scans": 10, "robot_2_scans": 10, "robot_1_odom_frame": "robot_1/odom", "robot_2_odom_frame": "robot_2/odom", "robot_1_gt": [1.000000005689777, 1.5, 0.1999998861964761, 1.8930741510996536e-20], "robot_2_gt": [-1.000000005689777, -1.5, 0.1999998861964761, -3.141592653589587]}
{"event": "CHECKING_LIFECYCLE_STATES"}
{"event": "LIFECYCLE_ACTIVE", "total_nodes": 12, "states": {"/robot_1/map_server": "active", "/robot_1/amcl": "active", "/robot_1/controller_server": "active", "/robot_1/planner_server": "active", "/robot_1/behavior_server": "active", "/robot_1/bt_navigator": "active", "/robot_2/map_server": "active", "/robot_2/amcl": "active", "/robot_2/controller_server": "active", "/robot_2/planner_server": "active", "/robot_2/behavior_server": "active", "/robot_2/bt_navigator": "active"}}
{"event": "CHECKING_TF_CHAINS"}
{"event": "TF_CHAINS_VALID", "robot_1_trans": [1.0, 1.5000000000000002], "robot_2_trans": [-1.0, -1.5000000000000002]}
{"event": "CHECKING_AMCL_INITIAL_POSES"}
{"event": "AMCL_INITIAL_POSE", "robot": "robot_1", "x": 1.0, "y": 1.5000000000000002, "error_m": 2.220446049250313e-16}
{"event": "AMCL_INITIAL_POSE", "robot": "robot_2", "x": -1.0, "y": -1.5000000000000002, "error_m": 2.220446049250313e-16}
{"event": "AMCL_INITIAL_POSES_VALID"}
{"event": "WAITING_FOR_ACTION_SERVERS"}
{"event": "SENDING_NAVIGATE_TO_POSE_GOAL", "robot": "robot_1", "target_x": 2.5, "target_y": 1.5, "target_yaw": 0.0}
{"event": "SENDING_NAVIGATE_TO_POSE_GOAL", "robot": "robot_2", "target_x": -2.5, "target_y": -1.5, "target_yaw": 3.14159265359}
{"event": "GOAL_ACCEPTED", "robot": "robot_1"}
{"event": "GOAL_ACCEPTED", "robot": "robot_2"}
{"event": "NAVIGATION_WINDOW_START", "monotonic": 545.272630621, "wall_time": 1792763746.082953}
{"event": "MONITORING_PARALLEL_NAVIGATION"}
{"event": "NAVIGATION_PROGRESS", "robot_1_done": false, "robot_2_done": false, "inter_robot_dist_m": 4.183021054501034, "min_inter_robot_dist_m": 3.60555128177623}
{"event": "NAVIGATION_PROGRESS", "robot_1_done": false, "robot_2_done": false, "inter_robot_dist_m": 4.958856605745218, "min_inter_robot_dist_m": 3.60555128177623}
{"event": "NAVIGATION_WINDOW_END", "monotonic": 550.732316374, "wall_time": 1792763751.5426385}
{"event": "GOALS_COMPLETED_CHECKING_RESULTS"}
{"event": "DESTINATION_REACHED", "robot": "robot_1", "status": 4, "dist_gt_m": 0.2166785043864889, "dist_amcl_m": 0.3439237235826541, "dist_odom_m": 1.8910947559717493, "tolerance_m": 0.35, "primary_eval": "PASS"}
{"event": "DESTINATION_REACHED", "robot": "robot_2", "status": 4, "dist_gt_m": 0.2054382922399168, "dist_amcl_m": 0.327696938869142, "dist_odom_m": 4.083389510613083, "tolerance_m": 0.35, "primary_eval": "PASS"}
{"event": "BACKEND_CONTAINER_CGROUP", "source": "backend_container_cgroup", "run_duration_s": 10.99, "scan_rates_hz": {"robot_1": 5.0, "robot_2": 5.0}, "total_scans": {"robot_1": 44, "robot_2": 44}, "min_inter_robot_distance_m": 3.6056, "peak_memory_mb": 50.21, "current_memory_mb": 50.21, "cpu_usage_usec": 4234256}
{"event": "B3_PASS", "token": "simulation-b3-retry-20261023-02", "robot_1_gt_m": 0.2166785043864889, "robot_2_gt_m": 0.2054382922399168, "robot_1_amcl_m": 0.3439237235826541, "robot_2_amcl_m": 0.327696938869142, "min_inter_robot_distance_m": 3.6056, "backend_cgroup_peak_mb": 50.21}
```

### 4.2 Host `docker stats` Kaynak Ölçüm Raporu

```json
{
  "run_token": "simulation-b3-retry-20261023-02",
  "domain_id": 46,
  "exit_code": 0,
  "run_duration_s": 15.39,
  "nav_duration_s": 5.46,
  "entire_run_stats": {
    "simulation-b3-retry-simulation": {
      "sample_count": 7,
      "avg_cpu_pct": 128.34,
      "peak_cpu_pct": 251.31,
      "peak_mem_mb": 612.4
    },
    "simulation-b3-retry-backend": {
      "sample_count": 6,
      "avg_cpu_pct": 38.54,
      "peak_cpu_pct": 49.64,
      "peak_mem_mb": 47.95
    }
  },
  "navigation_window_stats": {
    "simulation-b3-retry-simulation": {
      "sample_count": 2,
      "avg_cpu_pct": 138.0,
      "peak_cpu_pct": 140.25,
      "peak_mem_mb": 459.6
    },
    "simulation-b3-retry-backend": {
      "sample_count": 2,
      "avg_cpu_pct": 49.37,
      "peak_cpu_pct": 49.64,
      "peak_mem_mb": 47.95
    }
  }
}
```

### 4.3 Koşu 2 Temizlik Komutu

```sh
env DDS_TEST_PAYLOAD=cleanup docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-b3-retry.yml down -v --remove-orphans
docker network prune -f
```

Çıkış kodu: 0

---

## 5. Sistem Doğrulama ve Durum Çıktıları

### 5.1 `docker ps -a`

```sh
docker ps -a
```

Çıkış kodu: 0

```text
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```

### 5.2 `docker network ls`

```sh
docker network ls
```

Çıkış kodu: 0

```text
NETWORK ID     NAME      DRIVER    SCOPE
35480ff855c7   bridge    bridge    local
f4383e63729e   host      host      local
6bf49d79e0a8   none      null      local
```

### 5.3 `git status`

```sh
git status
```

Çıkış kodu: 0

```text
On branch main
Your branch is up to date with 'origin/main'.

Changes to be committed:
	modified:   docs/simulation-stage-b3-2026-10-23.md
	new file:   docker-compose.simulation-b3-retry.yml
	new file:   docker/simulation-b3-retry/check.py
	new file:   docker/simulation-b3-retry/test_config.py
	new file:   docker/simulation-b3-retry/tf_helper.py
	new file:   docs/simulation-stage-b3-retry-2026-10-23.md
	new file:   docs/simulation-stage-b3-retry-commands-2026-10-23.md
	new file:   scripts/run_b3_retry.py
```

