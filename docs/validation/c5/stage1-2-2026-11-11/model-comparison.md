# Çalışan fiziksel model ile TurtleBot3 Burger karşılaştırması

Bu inceleme deneylerden önce kaynak üzerinden başlatılmış, başvuru bağlantılarıyla tamamlanmıştır. Ürün adı veya batarya model anahtarı gerçek Burger fiziği kanıtı değildir.

| Özellik | Bu koşunun Fortress SDF'si | ROBOTIS Humble Burger URDF'si |
|---|---|---|
| Gövde collision | merkezli 0,50×0,30×0,10 m kutu | (-0,032;0;0,070) ofsetli 0,140×0,140×0,143 m kutu |
| Ana gövde kütlesi | 2,0 kg | yaklaşık 0,826 kg |
| Tekerlek yarıçapı / uzunluğu | 0,100 / 0,040 m | 0,033 / 0,018 m |
| Tekerlek merkez açıklığı | 0,400 m | 0,160 m |
| Tekerlek dış genişliği | 0,440 m | 0,178 m |
| Destek | arka ve ön küre; r=0,05 m, sürtünme 0 | arka destek kutusu |
| Lidar | ideal GPU lidar, merkezde xy/yaw ofseti yok; 180 ışın, 5 Hz, 10 m | ayrı tarayıcı link'i ve donanım geometrisi |
| Odometri | Fortress DiffDrive joint position integrasyonu | gerçek platformda actuator/encoder temelli zincir |
| Görsel | test dünyasında kutu ve silindirler; Chrome nominal Burger görseli | mesh tabanlı Burger |

Kaynaklar: [çalışan SDF üreticisi](../../../../docker/simulation-c3-3-3/check.py), [dock/pose ekleri](../../../../docker/simulation-c4-4/dock_world.py), [ROBOTIS Humble URDF](https://raw.githubusercontent.com/ROBOTIS-GIT/turtlebot3/humble/turtlebot3_description/urdf/turtlebot3_burger.urdf), [ROBOTIS özellikleri](https://emanual.robotis.com/docs/en/platform/turtlebot3/features/). Harici kaynaklar 11 Kasım 2026 tarihinde okunmuştur. Kaynak dalı değişebilir; bu tablo bu tarihte okunan alanları belirtir.

Zincir: Gazebo `JointPosition` → `DiffDriveOdometry` → Gazebo odom → ros_gz_bridge → ROS `/robot_*/odom` → warehouse TF helper → odom→base_link. AMCL scan/map üzerinden map→odom üretir. Ground truth ayrı PosePublisher → physical_pose yolundadır; odometri yerine kullanılmaz. [Fortress DiffDrive kaynak kodu](https://raw.githubusercontent.com/gazebosim/gz-sim/ign-gazebo6/src/systems/diff_drive/DiffDrive.cc) joint konumlarını odometriye verdiğini gösterir; kurulu paket binary'sinin birebir derleme hash'iyle kaynak eşlemesi bu incelemede kanıtlanmış değildir.

Gerçek üretilmiş dünya 5 ms fizik adımı kullanır; eski tek robot template'indeki 1 ms değeri bu profilin değeri değildir. ROS header damgaları simülasyon saatidir. Kontrollü komut süreleri `/clock` ile; timeout ve kapanış süreleri monotonic ile ölçülür. Tekerleklerde özel sürtünme tanımı yoktur; desteklerde ODE mu/mu2=0 vardır. DART'ın varsayılan temas/sürtünme çözümü, bu XML'den kalibre edilmiş lastik modeli olarak çıkarılamaz. Wheel joint ekseni model Y, tekerlek silindir ekseni roll π/2 ile Y doğrultusudur; ileri/geri deneyi dönüş işaretlerini sınar.

Deney sonrası uygulama: ortak Fortress robot üreticisinde diff-drive etkin açıklığı 0,36 m yapıldı; fiziksel tekerlek merkezleri 0,40 m olarak kaldı. Bağımsız 90°/180° ölçümleri bu etkin değeri destekler; yeni düşük hızlı dönüşlerde fark yaklaşık 0,001 rad’dır. Kavisli Nav2 rotalarında kalan hata ve farklı temas/hız profillerine genelleme sınırı [Aşama 1.2 raporunda](../c5-stage1-2-physical-localization-2026-11-11.md) ayrı tutulur.

Footprint uygulaması: mevcut Navfn/DWB dairesel kontrol yaklaşımı için local/global robot_radius=0,30 m seçildi; bu değer 0,291548 m gerçek collision dönüş zarfını kapsar, mevcut padding/inflation korunur. Geometrik eksiklik giderilse de son fiziksel pickup 1/5 ve paralel beta Nav2 abort olduğundan operasyonel kabul açık kalır. [Varyant sonuçları ve geri dönüş](../c5-stage1-2-physical-localization-2026-11-11.md#6-footprint-hesabı-ve-erişim)
