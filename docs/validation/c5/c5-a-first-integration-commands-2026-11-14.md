# C5-A — Gerçek komut eki

14 Kasım 2026. [Sonuç ve sınırlar](c5-a-first-integration-2026-11-14.md). Komutlar integration worktree kökünden çalıştırıldı. Aşağıdaki isim/dizinler bu açık koşuya aittir; aynı ad veya DB ile yeniden çalıştırılmamalıdır. Yeni tekrar için yeni container adı, kanıt kökü, boş DDS domain ve boş portlar seçilir. Eski kaynaklar silinmez. Image ve npm bağımlılıkları mevcut yerel bağımlılıklardır; yeni kurulum testi yapılmadı.

## Backend / Gazebo / iki Nav2 / Executor / batarya

Gerçek container inspect argv’sinden alınan başlatma komutu; named volume veya eski install üzerine yazmaz. Kaynak read-only, yeni SQLite container `/var/lib/fleet` içindedir. Canlı DB otomatik replay için tekrar kullanılmaz.

```sh
docker run -d --init --name fleet-c5-a-demo-live-20261114 --network fleet-c5-stage26-dds --add-host scene:127.0.0.1 -p 127.0.0.1:20182:20182 -e ROS_DOMAIN_ID=181 -e IGN_PARTITION=fleet-c5-a-demo-live-20261114 -e ROS_LOCALHOST_ONLY=0 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e LIBGL_ALWAYS_SOFTWARE=1 -e PYTHONDONTWRITEBYTECODE=1 -v /Users/murat/develop/c5-a-demo-evidence-20261114:/evidence -v /Users/murat/develop/ros2-fleet-manager-c5-auto-charging-integration:/workspace:ro -w /workspace --entrypoint bash ros2-fleet-c5-validation:humble-fortress -ec 'source /opt/ros/humble/setup.bash
colcon --log-base /evidence/idl-log build --base-paths interfaces/fleet_interfaces --build-base /evidence/idl-build --install-base /evidence/idl-install
source /evidence/idl-install/setup.bash
export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:${PYTHONPATH:-}
exec python3 docker/simulation-warehouse-grid/stage1_run.py config/fleet.warehouse-30x18.yaml /evidence/live-current-idl --api-port 20182 --scene-port 20183 --origin http://127.0.0.1:20181'
```

Derleme sonucu: **1 paket / 29,4 sn / başarılı**. Runner’ın `reset-verified.json` dosyası gerçek fiziksel reset, güncel duruş odometrisi ve iki aktif Nav2’yi doğruladıktan sonra Executor/FM açıldı.

## Frontend / Chrome

```sh
C5_UI_PORT=20181 C5_API_PORT=20182 npm --prefix frontend run dev > /Users/murat/develop/c5-a-demo-evidence-20261114/frontend.log 2>&1
```

Chrome adresi: `http://127.0.0.1:20181/?trace=1#overview`. Native Chrome arayüzünde Görevler → alım `pick_A1` → teslim `pick_B1` → Düşük → Görevi gönder kullanıldı. Gerçek görev ID’si sonuç kaydındadır. İkinci görev veya paralel rota başlatılmadı. Tamamlandı satırı, genel görünümde ortak depo ve 2/2 TF LIVE görsel olarak doğrulandı. Chrome AX’inde Canvas fallback metninin bulunması tek başına WebGL hatası değildir; gerçek screenshot’ta çizilmiş 3B depo görüldü, chrome://gpu WebGL donanım hızlandırmasını bildirdi.

## Odaklı read-only doğrulama

```sh
curl -sS http://127.0.0.1:20182/api/robots
curl -sS http://127.0.0.1:20182/api/tasks
curl -sS http://127.0.0.1:20182/api/warehouse-layout
docker logs --tail 15 fleet-c5-a-demo-live-20261114
git diff --check
```

API yanıtları kanıt köküne `*-verified.json` olarak kaydedildi. `observed-summary.json`, gerçek `ros.jsonl` okunarak çıkarıldı. Aynı UUID ve epoch ile COMPLETED görev, tek SENT/attempts=1 Outbox, gerçek completed_epoch=1, iki Nav2 SUCCEEDED ve boş unsafe-contact listesi Python assertion’larıyla doğrulandı. Çıktı `LIVE_CHAIN_VERIFIED web-12dd7189-f174-49ce-bb87-29163728342f 27f40f93-2de4-482b-8329-ef00a7ae2cf1 epoch=1 completed_epoch=1`.

İlk `fleet-c5-a-demo-20261114` denemesi eski `/tmp/c5-stage21-audit/install` kaynaklı ResumePerception import hatasıyla kaldı ve supervisor dünyayı temiz kapattı. Bu container ve `live/` logları korundu. Başarılı yeni container eski IDL mount’unu kullanmaz. Mevcut `c5-actuator-timeout-20261114` deneyine sinyal gönderilmedi. Başarılı demo açık bırakıldığı için bu koşunun kapanış doğrulaması henüz yapılmadı.
