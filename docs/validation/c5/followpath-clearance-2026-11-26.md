# C5 — İlk 253 costmap bandından kontrollü çıkış

**Canlı kabul geçti.** Normal depo demosunda Beta–Gamma karşılaşmasında Gamma fiziksel olarak uzaklaştı, aynı hedefe yeni rota aldı ve aynı yüklü taşıma görevini tamamladı. Gazebo temas kaydetmedi.

## Uygulama

Standart depo ağacı, etkin iç `FollowPath` abort’undan sonra aracın duruşunu teyit eder. Ölçülen başlangıç yerel veya global ham costmap’te 253 ise düz ve kısa çıkış adayları değerlendirilir. Aday, normal geçilebilir alanda duruş payıyla bitmelidir. Her iki costmap’te 254 ve 255 hücreleri reddedilir. Döndürme ve öteleme boyunca Gazebo SDF’deki bütün çarpışma parçalarını kapsayan dışbükey ayak izi, hücrelerin gerçek kareleri ve örnekler arası süpürme payıyla kontrol edilir.

Global fiziksel ayak izi Gazebo’nun ölçülen pozu ve mevcut dünya–map dönüşümü üzerinden kontrol edilir. Yerel ayak izi güncel odom costmap’inde denetlenir. Birleşik costmap’teki 254 ve 255 merkez hücreleri her durumda reddedilir. Bant içinde statik ve sensör kaynaklı ayak izi çakışmaları, robot katmanından hemen önceki güncel grid üzerinden denetlenir. Hareketli robotların birbirinden ayrılması, her robotun güncel Gazebo pozu ve kendi SDF çarpışma izdüşümüyle doğrulanır. Dairesel sınırlar, ayak izi denetiminden önce uzak çiftleri elemek için kullanılır. İki birleşik costmap merkezi de banttan çıktığında tam birleşik ayak izi denetimi tekrar uygulanır. Diğer robotların Gazebo pozları ayrıca ortak çerçevede ve kaynak zamanıyla doğrulanır. Başlangıç bandında costmap açıklığının azalması, yakındaki robota yaklaşma veya fiziksel zarfların örtüşmesi rotayı eler. Bandın dışına çıkmış costmap’e yeniden 253 girişi reddedilir.

Çıkış manevrası ilk `NavigateToPose` içinde, sınırlı hızla çalışan ayrı bir Nav2 `FollowPath` denetleyicisinden yürütülür. Denetleyici her hız komutundan önce güncel pozlar ve costmap’lerle kalan kısa segmenti yeniden doğrular. Hareket komutu boyunca tek-robot kilidi tutulur. Çıkış, duruş ve Gazebo yer değiştirme teyidinden sonra ana ağaç aynı hedefe gerçek Nav2 planını hesaplar. Terminal hata sözleşmesi korunur.

## Doğrulama

Depo kökünde `./scripts/start_demo.sh` ile oturum başlatıldı. Chrome görev formundan üç `MEDIUM` öncelikli `pick_C2 → delivery-01` gönderildi. Hedef tıklama zamanları 18,95 / 20,45 / 22,15 sim-s. ROS gözlemcisi `received_global_plan` ve action durumlarını, demo gözlemcisi fiziksel poz, temas, terminal action ve SQLite verilerini kaydetti.

```sh
PYTHONPATH="$PWD:$PWD/backend:$PWD/ros2_ws/src/fleet_robot_executor:$PWD/ros2_ws/src/fleet_battery_simulator" \
  python3 -m pytest -q tests/test_config.py tests/test_peer_awareness_config.py \
  tests/test_executor_safety.py tests/test_executor_state_machine.py \
  tests/test_traffic_child_binding.py tests/test_traffic_core.py
docker exec "$SESSION" bash -ec '
  source /opt/ros/humble/setup.bash
  cmake --build /c5-cache/build/fleet_nav2_escape --target clearance_test
  ctest --test-dir /c5-cache/build/fleet_nav2_escape --output-on-failure
'
git diff --check
```

151 seçili regresyon, 12 geometri kontrolü ve PeerRobotLayer CTest seçkisi geçti. Geometri denetimi başlangıç bandından çıkışı, lethal ve bilinmeyen kareyi, fiziksel çakışmayı, güncelliği, yaklaşmayı ve banda geri girişi kapsadı.

### Canlı koşular

- `c5-demo-20261126T061403Z-b7cc39b42796` oturumunda Beta ve Gamma’nın alım/teslim karşılaşması yeniden oluştu. Dairesel ayak izi denetimi costmap’te dolu alan tespit etti. İki robot da fiziksel kaçış başlatmadı.
- `c5-demo-20261126T062337Z-483fc339d98a` oturumunda Beta ve Gamma teslim bölgesinde yaklaşık 0,600 m merkez mesafesinde sıkıştı. Bu sürüm, robotları çevrel dairelerle karşılaştırdığı için çıkışı reddetti. Ardından her iki robotun fiziksel izdüşümünü kullanacak şekilde güncellendi.
- `c5-demo-20261126T063016Z-f02c3a624873` son uygulamayla normal başlatıcıdan çalıştı. Üç taşıma `COMPLETED` oldu ve temas kaydı yoktu. Kaçış tetiklenmediği için bu koşu kabul sayılmadı.

### Başarılı Beta–Gamma kabulü

`c5-demo-20261126T063540Z-d07bcf08ffdd` oturumu normal `./scripts/start_demo.sh` ile, varsayılan depo profili ve üç robotla çalıştı. Üç `MEDIUM` taşıma GUI’den 104,405 / 105,955 / 108,825 sim-s’de gönderildi. Üçü de HTTP 201 aldı. Gamma yüklü teslim sürüşünde Beta’yla karşılaştı.

| Ölçüt | Canlı kanıt |
|---|---|
| İç abort | `Controller patience exceeded`. Etkin `FollowPath` `89f0517a63803253350508c89f8d9875` için durum 6, 224,525 sim-s. |
| Fiziksel çıkış | 0,300 m’lik segment, iç `FollowPath` `828bf07cf893d9b2c35b3c251ae63225` ile yürütüldü ve durum 4 verdi. 224,545–230,680 sim-s arasında enterpole edilmiş Gazebo pozları (14,167, −6,385) m → (14,438, −6,376) m, yer değiştirme **0,271 m**. |
| Beta’dan ayrılma | Eşzamanlı merkez mesafesi **0,620 m → 1,669 m** oldu. Gamma’nın Beta’nın başlangıç noktasına mesafesi de 0,620 m’den 0,887 m’ye çıktı. |
| Asıl hedefe dönüş | 230,680 sim-s’de 32 pozlu yeni Nav2 planı, (14,450, −6,350) m → asıl teslim konumu (13,750, −6,750) m. Aynı `NavigateToPose` `2fe35d8c-428e-48b0-a747-a2bcaec29171` durum 4 verdi. |
| Görev ve yük | 35 kaçış dönemi `RobotStatus` örneğinde `MOVING_TO_DROPOFF`, yüklü ve epoch 1. Görev `web-4f7fcf9a-f108-431f-ae1c-3c251452ee5b`, `ExecuteTask` `1e1aa475-c2cc-456d-9980-7985310399bd` ile 246,130 sim-s’de tamamlandı. SQLite `COMPLETED`, gerçek `completed_epoch=1`. |
| Gazebo ve kapanış | Ürün gözlemcisinde sıfır `UNSAFE_CONTACT`. Kapanışta 11 süreç sıfır koduyla çıktı. |

Kaçış sırasında kısa süreli costmap güncellik uyarıları vardı. Bu çevrimlerde denetleyici hareket komutu üretmedi ve güncel veri gelince aynı iç hedef sürdü. Başarılı koşuda tek kaçış hareketi gönderildi. İki eşzamanlı uygun kaçış adayıyla ayrı bir canlı hareket testi yapılmadı. Koşu tamamlandığında commit ve push yapılmamıştı.

Ham kanıt `/tmp/c5-demo-20261126T063540Z-d07bcf08ffdd/` dizininde. GUI kayıtları `gui-escape-final.jsonl`, hareket ve görev kayıtları `live/simulation.log`, `live/escape-gui-ros.jsonl`, `live/ros.jsonl`, `live/executor_robot_gamma.log`, `live/fleet.sqlite3` ve `live/shutdown.json` dosyalarında. GUI ve ROS gözlemci kaynaklarının kopyaları oturum dizininde. Kabulde `NavigateToPose` ve `ExecuteTask` kimliklerini eşlemek için yerel Executor tanı satırı da kullanıldı. Bu satır kaçışın çalışması için gerekmiyor.

[Önceki Beta–Gamma referansı](followpath-escape-peer-encounter-2026-11-26.md).
