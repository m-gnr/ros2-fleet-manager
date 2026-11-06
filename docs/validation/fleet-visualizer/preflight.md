# Fleet Visualizer ön incelemesi

6 Kasım 2026. Prototipin veri kaynağı ve çalışma sınırları için teknik inceleme.

## Depo ve çalışma ortamı

Başlangıçta `main`, `HEAD`, yerel `origin/main` ve uzak `refs/heads/main` aynı `32e23fce62026a1d50aa2f04e85c8c38a6ee5d76` commit'indeydi. `docs/README.md` düzenlemesi, izlenmeyen `docs/gereksinim-literatur-ozgunluk-2026-10-27.pdf` ve `docs/reports/` ana çalışma ağacındaydı. Yeni `feat/fleet-visualizer-3d-mvp` dalı aynı commit'ten kardeş worktree'de açıldı.

Docker Desktop Linux VM ve ARM64 imajlarıyla depo katmanları çözüldü. [C2.3](../c2/c2-3-validation-2026-10-24.md) simülasyonu Fortress `ign gazebo -s -r --headless-rendering`, DART, yazılım OGRE2/EGL, ROS köprüsü, namespaced Nav2/AMCL, Map Server, TF yardımcı düğümü ve Executor kullanır. C4.5 katmanları gerçek Battery Simulator ve testte başlatılan Fleet Manager ile çalışır. Her koşu ayrı Compose bridge ağı ve dışarıdan verilen DDS domain kullanır. `config/dds.env` CycloneDDS ve konteynerler arası keşfi seçer. Canlı Visualizer ARM64 Humble imajına dayalı ayrı bir konteyner olarak aynı ağa katıldı.

Filo kaynağı `config/fleet.yaml`, ID ve namespace eşleşmeleri `robot_1 ↔ /robot_1` ve `robot_2 ↔ /robot_2`. Nav2 şablonunda `map` global frame, `@ODOM_FRAME@` ve `@BASE_FRAME@` ise koşunun verdiği adlardır. ROS namespace ve frame dizgesi ayrı kavramlardır. Tek robotlu koşuda `view_frames` ve `tf2_echo` aşağıdaki zinciri doğruladı.

| Bağlantı | Kaynak | Canlı örnek |
| --- | --- | --- |
| `map → robot_1/odom` | Nav2 AMCL, namespaced TF ve kök rölesi | 5,208 Hz, 1 sn ileri damga toleransı |
| `robot_1/odom → robot_1/base_link` | Gazebo DiffDrive odometrisini alan TF yardımcı düğümü | 29,612 Hz |
| `robot_1/base_link → robot_1/base_link/lidar` | TF yardımcı düğümünün statik sensör bağlantısı | `/robot_1/tf_static`, z = 0,15 m |
| `map → robot_1/base_link` | Bileşke TF | 29,750000000 sn, x = −2 m, y = −0,5 m, yaw yaklaşık 0 rad |

C4.5 koşusunda aynı adlandırmayla `map → robot_2/odom → robot_2/base_link` bileşkesi, kök TF okuması ve seçili namespaced akışın aynı damgadaki örnekleriyle doğrulandı.

### RobotStatus ve C5

Executor `/<namespace>/robot_status` üzerinde nominal 5 Hz yayımlar. Canlı endpoint QoS değeri RELIABLE, VOLATILE, KEEP_LAST 10 idi. Üst `header.stamp` durum yayınına, iç `pose.header.stamp` odometri ölçümüne aittir. C2.3 örneğinde bunlar sırasıyla 69,200 ve 69,190 sn, `pose.header.frame_id` ise `map` idi. Executor, odometriyi çalışma moduna göre damgalı map TF ile veya başlangıç pozu üzerinden map koordinatına taşır. `RobotStatus.pose` çerçeve etiketi tek başına hangi dönüşümün kullanıldığını ayırt etmeye yetmediği için TF kesintisinde otomatik yedek olarak seçilmedi.

Güncel IDL, `robot_id`, `status_seq`, `publisher_session_id`, `current_epoch`, fiziksel durum ve faz, yük ve görev bilgisiyle birlikte damgalı pozu taşır. C4 yolunda `battery_soc_percent`, `battery_energy_wh`, bağımsız `battery_stamp`, dock/şarj istasyonu alanları ve fiziksel dock çıkışı için ayrı `physical_pose` bulunur. C2.3 örneğinde batarya ölçüm damgası sıfırdı. Visualizer bu alanları iş kararlarına dönüştürmeden TF'yi ayrı bir sunum akışına taşır. C5 FastAPI/WebSocket ürün altyapısı bu commit'te mevcut değildi. [C4 kabulü](../c4/c4-acceptance-2026-11-06.md), [C5 mimarisi](../../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md#14-c-aşaması-c1c5-geliştirme-yol-haritası).

### TF ve ROS endpoint denetimi

Kurulu Humble paketinde `TransformListener` dinamik `/tf` ve TRANSIENT_LOCAL `/tf_static` abonelikleri oluşturur. `Buffer(node=...)` Humble'da `tf2_frames` servisini açar. Prototip düğümsüz `Buffer()` ve seçilen namespace'e açık bir TF aboneliği kullanır. Bu iki bağlantının ikisi de dinamiktir. Düğüm başlarken rclpy'nin açtığı `/parameter_events` yayıncısı spin öncesinde kaldırılır. Kurulum sırasında middleware bir parametre olayı endpoint'i oluşturabilir. Çalışma grafiğinde seçili TF ile `/clock` dışında uygulama endpoint'i görülmedi.

`ros2 node info --no-daemon`, `ros2 topic info --no-daemon`, `topic echo`, `tf2_echo` ve `view_frames` ayrı DDS katılımcılarıyla keşif ve abonelik trafiği üretir. `view_frames` kendi TF frame graph altyapısını açabilir. Bu geçici gözlem araçları köprü endpoint envanterinden ayrı tutuldu. Hareket komutları yalnız izole kabul koşularının mevcut test sürücülerinden geldi.

## WareTrack

[Referans depo](https://github.com/raultoto/waretrack), geçici ayrı dizinde `5125a137ab5e12e9855bec9ceb55f8a227146aa4` commit'i üzerinden incelendi. Next.js istemci bileşenleri React Three Fiber ve Drei CameraControls kullanıyor. Depo, rıhtım, yol, kamyon ve forkliftler Three.js geometrilerinden kuruluyor. Three pointer olayları ve liste etkileşimleri ortak seçimi güncelliyor. Zustand + Immer deposundaki 10 Hz `tick` süreçleri rastgele sipariş, forklift ve araç simülasyonunu ilerletiyor. `useFrame` hareketi Catmull–Rom yollarındaki faz ve ilerleme üzerinden çiziyor. Kamera seçim üzerine odaklanıyor.

### Yeniden kullanılabilecek bileşenler

Bağımsız paketler olan React Three Fiber, Three.js ve Drei'nin kamera kontrolleri uygun. Sahne, kamera ve telemetri panelinin ayrılması ile sade geometriler genel tasarım referansı olarak kullanıldı.

### Yeniden yazılması gereken bileşenler

Sahte depo ve sevkiyat durumu, rota bazlı araç animasyonu, simülasyon saati, varlık seçimi ve store şekli ROS telemetri akışına doğrudan uymuyor. Visualizer'da WebSocket doğrulama, sahne ve robot geometrisi ayrı uygulandı. Tek robot seçimi C1 doğrulayıcısının sunduğu ID üzerinden başlangıçta yapılıyor.

### Lisans riskleri

İncelenen commit'te `LICENSE`, `COPYING`, kaynak için bir lisans bildirimi veya dış 3D varlıklar için ayrı hak kaydı bulunamadı. `package.json` paketi özel olarak işaretliyor. Bağımlılık lisansları bu deponun kendi kaynak kodu için izin sağlamaz. Sahne geometrileri kaynakta tanımlı, ikonlar Lucide bağımlılığından ve yazı tipi bir bağımlılıktan geliyor. Visualizer özgün geometri ve stil kullanıyor.

### Bu MVP için önerilen yaklaşım

Vite + React üzerinde salt okunur bir WebSocket istemcisi ve R3F sahnesi. ROS TF, pozun ölçüm kaynağı. Sunum en son geçerli örneği ve tazeliği taşır, gerektiğinde iki geçerli ölçüm arasına sınırlı interpolasyon uygular.
