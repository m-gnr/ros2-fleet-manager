# C5 — Üstten depo açıklığı ve etiket denetimi

8 Kasım 2026 · [20 × 12 m filo profili](../../../config/fleet.warehouse-grid.yaml) · [Önceki canlı hareket kaydı](warehouse-grid-20x12-validation-2026-11-08.md)

[Önce](warehouse-grid-clearance/before.png) · [Önce üstten](warehouse-grid-clearance/before-top.png) · [Sonra](warehouse-grid-clearance/after.png) · [Sonra üstten ve Nav2 rotası](warehouse-grid-clearance/after-top.png) · [Yakın etiketler](warehouse-grid-clearance/after-zoom.png) · [Mobil kadraj](warehouse-grid-clearance/after-mobile.png)

## Ölçülen şarj ve alım erişimi

`rack_a4` kuzey yüzünden 0,50 m kısaltıldı. Şarj ceplerinin önündeki boyalı çizgiler ilk 2,00 m’yi gösterir. İki metrelik açıklık fiziksel pedin ön yüzünden başlayarak bir metre genişliğinde ölçüldü.

| Dock | Map merkezi (m) | En yakın raf ve merkez mesafesi | Ped önünden ilk sabit engele |
|---|---|---|---|
| `dock_1` | (5,25; 5,25) | `rack_a4`, 3,25 m | 2,95 m, raf |
| `dock_2` | (6,50; 5,25) | `rack_a4`, 3,25 m | 2,95 m, raf |
| `dock_3` | (7,75; 5,25) | `rack_a4`, 3,25 m | 2,95 m, raf |
| `dock_4` | (9,00; 5,25) | `rack_a4`, 3,34 m | 10,90 m, güney duvarı |

Batıdaki üç rafın kapıya bakan ucu 0,50 m kısaltıldı. Kapıdan gelen giriş bağlantısı, merkez hattı X = −9,25 m olan mavi erişim şeridine açılıyor. Üç alım merkezi X = −8,25 m’de ayrı ceplerde. Kapı → şerit → cep poligonları için merkez hattının en yakın duvar veya rafa mesafesi sırasıyla 0,70 m, 1,00 m ve 0,70 m. [Geometri ve rota ölçümü](warehouse-grid-clearance/inspection.json)

## Gerçek Nav2 planı

Fortress ve iki Nav2 yığını güncel YAML’den üretilen SDF ve haritayla açıldı. Nav2 `ComputePathToPose` ile `pickup_1` → ana koridor A → batı enine geçit → ana koridor C → `delivery-01` için beş plan alındı. Planlar 957 nokta olarak üstten Chrome görünümüne aktarıldı. Düz koridor bölümlerinin merkez sapması en fazla 2,50 cm. Segmentler ve plan parçaları arasındaki bağlantılar duvar ve raf dikdörtgenlerine karşı ölçüldü.

| Parça | Rota çizgisinden en yakın engel |
|---|---:|
| Alım bağlantısı | 1,08 m · `rack_a1` |
| Ana koridor A | 1,10 m · `rack_a1` |
| Batı enine geçit | 0,85 m · `rack_a1` |
| Ana koridor C | 1,10 m · `rack_c2` |
| Teslim bağlantısı | 0,70 m · doğu duvarı |

Rota çizgisinin 0,50 m altına indiği segment yok. Robot merkezi çevresindeki ihtiyatlı 0,45 m fiziksel zarf çıkarıldığında batı enine geçitte yaklaşık 0,40 m, teslimin doğu duvarı yanında yaklaşık 0,25 m pay kalıyor. [Segment ölçümleri](warehouse-grid-clearance/inspection.json)

## Görsel kabul

Şarj, Park ve Alım grup etiketleri boş zemine yerleşir ve bölge sınırına ince çizgiyle bağlanır. Konum hesabı rafların ekran izdüşümünü ve bölge boyalarını dışarıda bırakır. Uzakta tek satır özet, yakında üye ayrıntıları kullanılır. Üretim Chrome üstten testinde üç etiketin kutusu bütün raf ve bölge kutularından ayrıydı. Yakın görüntü Park ve Şarj ayrıntılarını gösterir. Varsayılan kamera daha dik açıdan bakar. Üstten görünüm TF göstergesine ayrıca boşluk bırakır. Masaüstü ve 390×844 sıfırlama kadrajlarında geometri köşeleri görünüm sınırları içinde kaldı. 84 Python ve 23 Playwright regresyon testi geçti. [Chrome kanıtı](warehouse-grid-clearance/chrome-evidence.json) · [Playwright](warehouse-grid-clearance/playwright.log) · [Python](warehouse-grid-clearance/python.log)

## Doğrulanamayanlar ve düzeltilen ilk deneme

- Kapıdan üç alım cebine erişim geometriyle, örnek alım–teslim rotası gerçek Nav2 planıyla doğrulandı. Bu turda rotalar robotlara fiziksel hareket hedefi olarak verilmedi.
- Her dock’un düz yaklaşma şeridi ölçüldü. Yanaşma, geri çıkış ve dolu komşu ceplerle manevra bu turda yeniden sürülmedi.
- Dar görüş veya başka bir kamera açısı yeterli boş zemin bırakmazsa etiket gizlenir. Tüm özel kamera açıları ve aynı anda birden fazla operasyon görevi sınanmadı.
- İlk görsel denemelerde Park etiketi, raf izdüşümüyle çakışınca gizlendi. Son yerleşimde park bağlantı noktası ve daha dik varsayılan kamera birlikte doğrulandı.

## Tekrarlama

Depo kökünde çalıştırılan komutlar:

```sh
PYTHONPATH=. python -m pytest -q tests/test_config.py tests/test_c5_dashboard.py tests/test_warehouse_grid.py
npm --prefix frontend run build -- --outDir /tmp/c5-grid-clearance/release --emptyOutDir
mkdir -p /tmp/c5-grid-clearance/release-live
docker run --rm --init --name fleet-grid-clearance \
  -e ROS_DOMAIN_ID=141 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e ROS_LOCALHOST_ONLY=0 \
  -e LIBGL_ALWAYS_SOFTWARE=1 -v "$PWD:/workspace:ro" -v /tmp/c5-grid-clearance/release-live:/evidence \
  --entrypoint bash ros2-fleet-c5-validation:humble-fortress /workspace/docker/simulation-warehouse-grid/run.sh inspection
```

Önceki 20 × 12 m üretim çıktısı ve snapshot fixture’ı sırasıyla `/tmp/c5-grid-large/release` ve `/tmp/c5-grid-large/fixture.json` yolundan kullanıldı. Ayrı terminallerde iki önizleme açıkken:

```sh
PYTHONPATH=. python tests/test_warehouse_grid.py /tmp/c5-grid-clearance/fixture.json
C5_UI_PORT=19867 C5_API_PORT=19869 npm --prefix frontend run preview -- --outDir /tmp/c5-grid-large/release
C5_UI_PORT=19868 C5_API_PORT=19869 npm --prefix frontend run preview -- --outDir /tmp/c5-grid-clearance/release
node frontend/tests/warehouse-grid-acceptance.mjs http://127.0.0.1:19867 http://127.0.0.1:19868 \
  /tmp/c5-grid-clearance/fixture.json /tmp/c5-grid-clearance/browser /tmp/c5-grid-large/fixture.json '' \
  /tmp/c5-grid-clearance/release-live/inspection/inspection.json
C5_UI_PORT=19868 C5_API_PORT=19869 npm --prefix frontend test -- --workers=1
git diff --check
```
