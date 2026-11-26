# C5 — Beta–Gamma karşılaşmasını tekrar etme

Depo kökünden normal başlatıcı çalıştırıldı.

```sh
./scripts/start_demo.sh
```

Chrome’da çalışan oturumun `Görev oluştur` formu Playwright üzerinden kullanıldı. Alım `pick_C2`, teslim `delivery-01` ve öncelik `Orta` seçilerek üç kez `Görevi gönder` tıklandı. İlk tekrar için tıklama hedefleri referans kabul zamanlarına yakın olarak 19,45, 20,85 ve 22,85 sim-s idi. `/clock` bilgisi ürün gözlemcisinin `live/ros.jsonl` kaydından okundu. Her `POST` isteği ile HTTP sonucu oturuma kaydedildi. Salt okunur ROS gözlemcisi üç robotun gerçek `received_global_plan` rotaları ve action durumlarını ayrıca kaydetti.

```sh
node /tmp/c5-escape-gui-replay-20261126.mjs "$SESSION" 19.45 20.85 22.85
docker exec -i "$SESSION" bash -ec '
  source /opt/ros/humble/setup.bash
  export PYTHONPATH=/workspace:${PYTHONPATH:-}
  exec python3 - "$1"
' ros-replay /evidence/live/escape-gui-ros.jsonl < /tmp/c5-escape-ros-replay-20261126.py
```

## Oturum kanıtı

| Koşu | Oturum dizini |
|---|---|
| Kullanıcının referansı | `/tmp/c5-demo-20261125T234857Z-97d9ade6b64c` |
| Referans zamanlarına yakın ilk tekrar | `/tmp/c5-demo-20261125T235727Z-d2638b21c9cc` |
| Üçüncü GUI gönderimi 10 sim-s geciktirilmiş tekrar | `/tmp/c5-demo-20261126T000328Z-8ac1d3cabd11` |
| Sıkışmayı yeniden üreten koşu | `/tmp/c5-demo-20261126T000758Z-fe2c40a3d45d` |
| Container içi hareket kilidiyle tekrar | `/tmp/c5-demo-20261126T001125Z-c63824e1f30c` |

İlk tekrarın tıklama hedefleri 19,45 / 20,85 / 22,85 sim-s, gecikmeli koşunun 19,45 / 20,85 / 32,85 sim-s, son iki koşunun 18,95 / 20,45 / 22,15 sim-s. Oturum kökünde GUI istek kayıtları ve prob kaynak kopyaları, `live/` altında `simulation.log`, `escape-gui-ros*.jsonl`, `ros.jsonl`, `fleet.sqlite3` ve `shutdown.json` bulunur. İlk otomasyon hazırlığında görev sekmesine ulaşma zaman aşımı oldu ve görev gönderilmedi. Bu hazırlık denemesi tabloya alınmadı.

## Hareket kilidi

Aynı container içinde iki süreçle `flock` denendi. İlk süreç dosyayı açık ve kilitli tutarken ikinci süreçte `flock -n` komutu, bind mount altında başarılı oldu ve container’ın `/tmp` dizininde reddedildi. Son oturumda `escape-lease-verification.cpp`, ürünün `EscapeLease` sınıfıyla üç bağımsız kontrol çalıştırdı. Bir süreç kilidi tutarken diğerinin ret alması, sonucu teyitsiz hareketin kilidi kapalı tutması ve terminal teyitten sonra tekrar alınabilmesi doğrulandı. Sonuç `escape-lease-verification.log` içinde.

## Regresyon

```sh
PYTHONPATH="$PWD:$PWD/backend:$PWD/ros2_ws/src/fleet_robot_executor:$PWD/ros2_ws/src/fleet_battery_simulator" \
  python3 -m pytest -q tests/test_config.py tests/test_peer_awareness_config.py \
    tests/test_executor_safety.py tests/test_executor_state_machine.py \
    tests/test_traffic_child_binding.py tests/test_traffic_core.py
git diff --check
```

151 test geçti, atlama yok. Normal başlatıcı, `fleet_interfaces`, `fleet_nav2_escape` ve `fleet_perception` overlay paketlerini Humble imajında derledi.
