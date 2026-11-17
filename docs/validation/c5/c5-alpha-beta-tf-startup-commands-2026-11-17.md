# C5 Alpha/Beta TF cold-start komut eki — 17 Kasım 2026

Çalışma dizini: `/private/tmp/ros2-fleet-manager-c5-alpha-beta-stable`
Dal: `demo/alpha-beta-stable`
Başlangıç HEAD'i: `f68c991d8b397c4c72257f599402b98c587c481e`

Bu ekte yalnız bu düzeltme koşusunun komutları ve ölçümleri yer alır. Önceki manuel demo farklı container ve worktree'de çalışmaya devam etti.

## Kod kontrolleri

```sh
python3 docker/simulation-warehouse-grid/test_startup_readiness.py
python3 -m py_compile backend/dashboard/api.py \
  docker/simulation-warehouse-grid/stage1_run.py \
  docker/simulation-warehouse-grid/stage1_observer.py \
  docker/simulation-warehouse-grid/startup_readiness.py
git diff --check
```

Sonuç: readiness birim testi `Ran 3 tests ... OK`; Python derleme ve whitespace/diff kontrolleri başarılı.

Bu cold-start koşusunda `fleet_interfaces` derlemesi 1/1 paket başarılı tamamlandı. Canlı simülasyon izole test container'ında `c5-alpha-beta-stable-live-20261117` adı, ROS domain `199` ve IGN partition `c5-alpha-beta-stable-live-20261117` ile başlatıldı; portlar yalnız localhost'a bağlandı. Eski manuel demo'ya DNS alias eklemeden API'nin aynı-container bridge erişimini doğrulamak için `/etc/hosts`/`--add-host scene` kullanılmadı. Kanıt/log dizini:

```text
/tmp/c5-alpha-beta-stable-live-20261117/live/
```

`stage1_run.py` içinde observer önce fiziksel reset kapısını, sonra AMCL/Nav2/TF readiness kapısını tamamlar; ardından manager ve API çocuk süreçlerini başlatır. Bu koşu hiçbir görev POST etmedi.

## Ölçüm ve servis kontrolleri

```sh
cat /tmp/c5-alpha-beta-stable-live-20261117/live/startup-readiness.json
curl -fsS http://127.0.0.1:21482/api/health
curl -fsS http://127.0.0.1:21482/api/robots
curl -fsS http://127.0.0.1:21482/api/tasks
curl -sS -o /dev/null -w 'UI HTTP %{http_code}\n' http://127.0.0.1:21481/
docker inspect -f '{{.Name}} {{.State.Status}}' c5-alpha-beta-stable-live-20261117
```

Son gözlemde health `source=LIVE`; Alpha/Beta `state=IDLE`, `telemetry=LIVE`, `pose_reliability=LIVE`, `battery_reliability=LIVE`, `active_task_id=null`; task listesi `total=0`; GUI HTTP `200`; test container `running` oldu. Başlatıcı readiness ölçümü `READY`, `current_status=READY` verdi. Her robotun AMCL/TF/Nav2 ilk-ready zamanları rapordaki tabloda yer alır.

Chrome GUI `http://127.0.0.1:21481/` adresinde açıldı; ilk bağlantı aşamasından sonra yenileme gerektirmeden iki robot haritada göründü ve `2/2 TF LIVE` oldu. Görev gönderilmedi; son REST snapshot'ında iki robot başlangıç pozlarında ve IDLE idi.

## Demo'yu kapatma

Bu doğrulama koşusunu kapatmak için yalnız yeni container'ı durdurun:

```sh
docker stop --timeout 35 c5-alpha-beta-stable-live-20261117
```

GUI Vite dev server'ı başlatan ayrı terminal/session `Ctrl-C` ile kapatılır. Önceki manuel demo container'ı bu komutun hedefi değildir.
