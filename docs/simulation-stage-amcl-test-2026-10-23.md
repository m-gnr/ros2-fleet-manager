# Tek Robotlu AMCL Gerçek Yakınsama Sınaması: Bölüm B

Tarih: 23 Ekim 2026 (Europe/Istanbul).

## Durum ve Kapsam

**BÖLÜM B SONUCU: 1 BAŞARILI, 1 BAŞARISIZ (Toplam canlı koşu: 2/2). Eşik gevşetilmedi; Koşu 2 katı toleransın 1.9 mm üzerinde kaldığı için başarısız olarak kaydedildi.**

B2 aşamasında başlangıç pozu robotun gerçek konumuyla aynı verilmişti. Bu bölümde AMCL'nin gerçek yakınsama kabiliyeti, başlangıç pozu kasıtlı olarak kaydırılarak (`x: 0.5 m`, `y: 0.3 m`, `yaw: 0.3 rad`; bileşke hata: `0.5831 m`) ve robot kısa bir rota boyunca sürülerek sınandı.

B1 ve B2 dosyalarına dokunulmadı; yeni bağımsız yapılandırma (`config/simulation-amcl-test*`) ve Compose override (`docker-compose.simulation-amcl-test.yml`) kullanıldı. Docker yerleşimi onaylanmış sayılmaz. [Proje bağlamındaki](project-context.md) kaynak önceliği geçerlidir.

---

## 1. Sınama Yöntemi ve Ground Truth Ölçümü

1. **Gazebo Ground Truth**:
   - Robotun Gazebo dünyasındaki gerçek konumu tahmin edilmedi veya odometriden türetilmedi.
   - Gazebo Fortress `SceneBroadcaster` eklentisinin `/world/amcl_validation_world/dynamic_pose/info` başlığı üzerinden yayınladığı `ignition.msgs.Pose_V` mesajı, `ros_gz_bridge` ile ROS 2 `tf2_msgs/msg/TFMessage` tipine köprülendi.
   - Test istemcisi (`backend`), `validation_robot` modelinin dünya koordinatlarındaki gerçek pozunu doğrudan bu köprüden anlık olarak okudu.
2. **Kasıtlı Başlangıç Kayması (Offset)**:
   - Gazebo'da robot gerçekte `(x: 0.0, y: 0.0, yaw: 0.0)` konumunda başlatıldı.
   - AMCL parametrelerinde başlangıç pozu `x: 0.5, y: 0.3, yaw: 0.3` olarak verildi.
   - Başlangıçta ölçülen AMCL poz hatası: **0.5831 m** (beklenen minimum ofset eşiği olan 0.45 m'nin üzerinde olduğu doğrulandı).
   - Bu sırada AMCL'nin ilk `map -> odom` transformu `[0.500, 0.300, 0.0]` olarak kaydedildi.
3. **Robot Hareketi ve Parçacık Filtresi Güncellemesi**:
   - AMCL parçacık filtresinin hareket bazlı güncelleme eşikleri `update_min_d: 0.1 m` ve `update_min_a: 0.1 rad`dır.
   - Robot `/cmd_vel` üzerinden 6.0 saniye boyunca `linear.x = 0.2 m/s` ve `angular.z = 0.15 rad/s` hızlarıyla dairesel bir yay boyunca sürüldü (~1.05–1.07 m doğrusal yol, ~0.95–0.99 rad açısal dönüş).
   - Hareket sırasında robot 10'dan fazla filtre güncelleme adımını tetikledi ve 180 ışınlı Lidar ile 10x10 m odanın duvarlarını taradı.
4. **Başarı Ölçütü**:
   - Hareket durduktan ve filtre oturduktan sonra AMCL poz hatası (`math.hypot(amcl_x - gt_x, amcl_y - gt_y)`), kayıtlı tolerans eşiği olan **0.4000 m**'nin altına inmelidir.
   - Eşik gevşetilmez; 0.4000 m üzeri sonuçlar doğrudan başarısızlık sayılır.

---

## 2. Canlı Koşu Sonuçları (En Fazla 2 Koşu Sınırı: 2/2)

Koşular arasında `docker compose down -v --remove-orphans` ile tüm container'lar ve DDS ağı tamamen kaldırıldı; ikinci koşu sıfır ağ ortamında başlatıldı.

| Ölçüt / Aşama | Koşu 1 (`amcl-test-20261023-01`) | Koşu 2 (`amcl-test-20261023-02`) | Değerlendirme |
|---|---|---|---|
| Başlangıç Ground Truth Pozu | `(x: 0.0000, y: 0.0000, yaw: 0.0000)` | `(x: 0.0000, y: 0.0000, yaw: 0.0000)` | ÖLÇÜLDÜ (Gazebo SceneBroadcaster) |
| Başlangıç AMCL Pozu | `(x: 0.5000, y: 0.3000, yaw: 0.3000)` | `(x: 0.5000, y: 0.3000, yaw: 0.3000)` | UYGULANDI (Kasıtlı ofset) |
| Başlangıç Poz Hatası | **0.5831 m** | **0.5831 m** | DOĞRULANDI (> 0.45 m eşiği) |
| Başlangıç `map -> odom` TF | `[0.5000, 0.3000, 0.0]` | `[0.5000, 0.3000, 0.0]` | ÖLÇÜLDÜ |
| Sürüş Süresi ve Hızı | 6.0 sn (`v=0.2 m/s, w=0.15 rad/s`) | 6.0 sn (`v=0.2 m/s, w=0.15 rad/s`) | UYGULANDI |
| Bitiş Ground Truth Pozu | `(x: 1.0718, y: 0.6434, yaw: 0.9948)` | `(x: 1.0477, y: 0.5994, yaw: 0.9531)` | ÖLÇÜLDÜ (Gazebo SceneBroadcaster) |
| Bitiş AMCL Pozu | `(x: 1.3276, y: 0.9305, yaw: 1.0505)` | `(x: 1.3207, y: 0.8943, yaw: 1.0152)` | ÖLÇÜLDÜ |
| Bitiş `map -> odom` TF | `[0.4287, 0.2853, 0.0]` | `[0.3937, 0.2802, 0.0]` | ÖLÇÜLDÜ (Düzeltme yönünde ilerledi) |
| Hata İyileşmesi (Azalma) | **0.1986 m** düzelme | **0.1812 m** düzelme | DOĞRULANDI (Her iki koşuda yakınsadı) |
| **Son AMCL Poz Hatası** | **0.3845 m** | **0.4019 m** | Koşu 1: **GEÇTİ**, Koşu 2: **KALDI** |
| Tolerans Eşiği | 0.4000 m | 0.4000 m | Değiştirilmedi / gevşetilmedi |
| Test İstemcisi Çıkış Kodu | 0 (`AMCL_TEST_PASS`) | 1 (`FAIL: ValueError`) | Koşu 1 temiz geçti, Koşu 2 hata verdi |

---

## 3. Bulgular ve Hata Analizi

1. **AMCL Düzeltme Yönü**: Her iki koşuda da AMCL'nin `map -> odom` transformu ve poz kestirimi gerçek konuma doğru belirgin biçimde hareket etti (Koşu 1'de 19.9 cm, Koşu 2'de 18.1 cm hata azalması).
2. **Eşik Aşımı Nedeni**: Parçacık filtresi (Monte Carlo Localization) stokastik bir yapıya sahiptir. 10x10 m boş simetrik bir odada 6 saniyelik kısa bir yay sürüşünde parçacık bulutunun varyansı tam olarak daralmamış ve Koşu 2'de son hata **0.4019 m** seviyesinde kalarak **0.4000 m** katı sınırını **1.9 milimetre (0.0019 m)** ile aşmıştır.
3. **Kural Uygulaması**: Kullanıcı talimatı gereği eşik gevşetilmedi; başarısızlık gizlenmedi ve doğrudan raporlandı. Canlı koşu üst sınırı 2 olduğu için ek deneme yapılmadı.

---

## 4. Doğrulanan ve Doğrulanmayan Kapsam

### Doğrulananlar
- Gazebo Fortress içinden `SceneBroadcaster` ile robotun yerel ve dünya koordinatlarında ground truth pozunun ROS 2'ye aktarılabildiği.
- Kasıtlı 0.5831 m ofsetin AMCL başlangıcında uygulandığı ve `map -> odom` transformuna yansıdığı.
- Sürüş sırasında AMCL'nin odometri ve Lidar verileriyle parçacık filtresini güncelleyip gerçek konuma doğru düzeltme yaptığı (hata her iki koşuda ~0.18–0.20 m azaldı).
- Koşu 1'de AMCL hatasının 0.3845 m'ye inerek 0.4000 m eşiğinin altına indiği.

### Doğrulanmayanlar ve Sınırlar
- Koşu 2'de 0.4000 m başarı eşiği sağlanamadı (son hata: 0.4019 m); bu nedenle 2'de 2 tam başarı sağlanamadı.
- Robot daha uzun mesafe sürülmedi veya harita içi köşelere yönlendirilmedi (kısa mesafe sınırı korundu).
- İki robotlu yerleşim (B3) bu bölümde sınanmadı.
