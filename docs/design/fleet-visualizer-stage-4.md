# Fleet Visualizer Aşama 4 teknik tasarım

6 Kasım 2026. [Nav2 kaynak incelemesi](../validation/fleet-visualizer/stage-4/nav2-source.md) · [Doğrulama raporu](../validation/fleet-visualizer/stage-4/report.md).

## ROS ve yaşam döngüsü

TF hattı Aşama 3'ün robot başına buffer ve `map → odom → base_link` çözümünü kullanır. `--observed-nav2-plans` yalnız `map` TF modunda açılır. Bu seçenek, iki robotlu Humble/Nav2 kurulumunda gözlenen Planner Server topolojisini seçer. Robot kimliği ve namespace `fleet.yaml` kaydından gelir. Her robotun kendi `<namespace>/plan` aboneliği, planı ve damga sınırı vardır.

Köprü, kabul sırasında ROS grafiğinde tam bir yayıncı arar. Beklenen yayıncı aynı namespace'teki `planner_server` düğümüdür. `Path` tipi, RELIABLE / VOLATILE / KEEP_LAST (1) QoS'u ve keşfedilen endpoint GID'si izlenir. Eşleşen yayıncı kaybı, ikinci yayıncı veya GID değişimi eldeki planı temizler. Görünür plan için grafik en geç 250 ms'lik aralıklarla örneklenir. Humble `rclpy` callback'i paket başına yayıncı GID'si sağlamaz. Kimlik denetimi, güvenilen DDS ağında keşfedilmiş tek yazıcıya dayanır. [Humble abonelik kaynak kodu](https://github.com/ros2/rclpy/blob/humble/rclpy/src/rclpy/subscription.cpp#L85-L127).

Ham DDS mesajı için 112 KiB çözümleme sınırı ve abonelikte bir örneklik kuyruk kullanılır. Çözümlenen plan 2–1.024 nokta taşır. Path ve her PoseStamped `map` çerçevesinde ve aynı ROS damgasında olmalıdır. Üç konum bileşeni sonlu ve ±10.000 m aralığında, yönelimin normu 1'e en fazla 0,01 uzaklıkta olmalıdır. Bu kurallar, doğrulanan Navfn mesaj biçimine bağlıdır. Geçersiz yeni geometri var olan çizimi temizler. Artmayan, eski veya belirgin biçimde ileri tarihli damga alınmaz. Saat topic'i ile yayın sırasının küçük farkları için 100 ms ileri tolerans vardır. Çizim için ROS saati plan damgasına ulaşmalıdır.

Planın ömrü en fazla 2 sn'dir. Hem ROS damga yaşı hem monotonik alım yaşı sınırlandırılır. Varsayılan davranış ağacının yaklaşık 1 Hz yeniden planlaması sırasında bu pencere bir yenilemeye izin verir. TF güncelliği kaybolduğunda plan temizlenir. `bt_navigator` tarafından yayınlanan robot bazlı `NavigateToPose` durum topic'inde kabul, yürütme, iptal aşaması veya terminal geçişi gözlenirse eldeki plan geçersiz kılınır. Bu durum verisi bir Path'e goal UUID veya görev sahipliği atamaz. Gözlenemeyen geçişler, ERROR veya sessiz yayıncı için plan ömrü ve veri güncelliği sınırları geçerlidir. ROS saati geri sarıldığında plan, damga sınırı ve TF buffer'ı sıfırlanır. [Kaynak kararı ve yaşam döngüsü gözlemleri](../validation/fleet-visualizer/stage-4/nav2-source.md).

## WebSocket rota sözleşmesi

Mevcut `robot_pose` ve `data_status` mesajları V1 olarak devam eder. `/telemetry/fleet` robot `hello` mesajı, abonelik etkinse doğrulanacak `path_topic` alanını ilan eder. Eski `/telemetry` ucu yalnız poz ve durum taşır.

| Alan | `robot_path` | `robot_path_clear` |
| --- | --- | --- |
| `version`, `robot_id`, `stream_id`, `epoch`, `frame_id`, `source` | V1 robot kimliği. `frame_id=map`, `source=tf`. | Aynı kimlik. |
| `plan_source` | `nav2_observed_plan` | `nav2_observed_plan` |
| `source_topic` | Robotun `hello.path_topic` değeri | Aynı değer |
| `stamp_ns` | Plan başlığından onluk nanosaniye dizgesi | Temizlenen planın damgası |
| `ttl_ms` | Gönderim anında kalan monotonik ömür. 1–2.000 ms. | — |
| `points` | Metre cinsinden `[[x, y], ...]`. Sınır 1.024 nokta. | — |

ROS ve asyncio arasında robot başına yalnız son snapshot tutulur. Gönderici önce tüm robotların poz ve durumunu, sonra planlarını işler. Bağlantı başına robot başına en fazla 5 plan/sn gönderilir. Eski snapshot, yeni WebSocket bağlantısında yeniden yayınlanmaz. İlk plan için yeni bir poz da gönderilmiş olmalıdır. Bağlantıya özel gönderim zaman aşımı 1 sn'dir. İstemci mesaj sınırı 64 KiB, gelen WS komut sınırı 1 KiB ve bağlantı sınırı dörttür. Tarayıcı, robot, kaynak topic, stream, epoch ve artan plan damgası eşleşmesini yeniden denetler. Yerel TTL ve tazelik denetimi, gecikmiş temizleme paketine bağımlılığı kaldırır.

## Gerçekleşen iz ve çizim

İz yalnız tarayıcıda, kabul edilmiş `robot_pose` TF örneklerinden birikir. Robot modeli için kullanılan kareler arası interpolasyon ize girdi vermez. Artan damga şartıyla, 2,5 cm'den az yer değiştiren ardışık iz noktaları atlanır. Robot başına son 60 simülasyon saniyesi ve en fazla 512 nokta tutulur. Pencere yeni ölçümle ilerler. 500 ms'den uzun ölçüm/alım aralığı, önceki kabul edilmiş poza göre 30 cm'den büyük tek adım veya tazelik kaybı yeni segment başlatır. Aynı akış ve epoch ile bağlantı dönünce iz yeni segmentle sürer. Yeni stream, frame veya epoch eski izi sıfırlar. Geçersiz frame'li paket mevcut çerçeveyi değiştiremez.

Her iki katman metreyi koruyarak `(x, yükseklik, -y)` dönüşümünü kullanır. Plan, robot renginde kesikli 2,2 px çizgi ve uç işaretleriyle çizilir. İz ince ve süreklidir. Aradaki kesintiler ayrı çizgi çiftleriyle temsil edilir. Katmanlar sabit kapasiteli GPU buffer'ları kullanır. Yalnız geometri değiştiğinde buffer yazılır ve robot katmanı kaldırıldığında geometri ile materyal temizlenir. Sahne poz ve rota verisini mevcut harici akıştan okur. Katman seçenekleri çizimi etkiler. Sahnenin temsili depo geometrisi navigasyon girdisi üretmez.
