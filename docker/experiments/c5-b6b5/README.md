# C5-B6B.5 test-only watchdog

**PARTIAL / ürün bağlantısı yok.** Fortress 6.18.0, Linux aarch64, C++17.
Kaynak `upstream/DiffDrive.cc`, B5G ile aynı binary'yi taşıyan B5E deneyinden
alındı; Apache-2.0 başlıkları korunur. B5G binary SHA-256:
`fb0722ac45e8a7f6a89937b4a9bf7fff22268bce2a71180c7317050876d9c45a`.
Bu eşleşme eski binary'nin kaynak derleme zincirinin kriptografik ispatı değildir.

Depo kökünden `bash docker/experiments/c5-b6b5/run.sh <yeni-göreli-kanıt-dizini>`.
Betik yerel taban image ID'sini doğrular; Dockerfile geliştirme paketini exact
sürümle ister. Apt transitif paketleri snapshot ile sabitlenmez: image'ın başka
tarihte sıfırdan aynı byte'larla üretilmesi garanti değildir. Tam paket listesi ve
build image ID'si kaydedilir; iki temiz native build ve incremental build aynı
image üzerinde karşılaştırılır. Çıktı dizini önceden varsa durur; ürün profili
ve çalışan container'lara dokunmaz. Runtime testinde ağ kapalıdır.

`IGN_GAZEBO_SYSTEM_PLUGIN_PATH` derlenen library dizinini göstermelidir.
Filename `libc5-actuator-diff-drive.so`, alias `gz::sim::systems::DiffDrive`;
ROS overlay native plugin yüklemez. Yükleme testi Gazebo'nun kullandığı
SystemPaths ve native plugin Loader ile gerçek shared object'i instantiate eder;
Configure/PreUpdate/PostUpdate ABI'leri ve `/proc/self/maps` doğrulanır.
Bu test tam Gazebo server/dünya kabulü değildir.

## Sıfır hedef sözleşmesi

- NO_COMMAND: başlangıç; hedef ve teker hedefleri sıfır.
- ACTIVE: yalnız geçerli sıfır receipt akışı; hareket yetkisi **değildir**.
  Receipt/deadline steady-clock; deadline eşitliğinde timeout. Aynı içerikli
  sıfır refresh aktifken deadline yeniler; anlamsal yenilik ispatı değildir.
- TIMED_OUT: deadline doldu; sıfır korunur, `timed_out=true`.
- BLOCKED_REARM: timeout sonrası her receipt, enable değişimi, nonzero/NaN/Inf
  veya sim zamanı geri dönüşü kilitler. Yeni receipt kaydedilir fakat deadline
  yenilenmez; timeout geçmişi korunur. Ağ üzerinden rearm yolu yoktur.

B5G'nin tekrar ACTIVE olurken eski flag'i taşıma sorunu kaldırılır: timeout
sonrası ACTIVE geçişi yoktur. Taze instance NO_COMMAND başlar. Ham Twist eski
komut/yeni komut ayrımını veya süreçler arası session doğrulamasını sağlayamaz:
**BLOCKER**. İlk sıfır replay'in ACTIVE telemetrisi oluşturması dahi freshness
kanıtı değildir. Kimlikli/yetkili rearm tasarımı burada onaylanmaz.

Lease PreUpdate'te pause kontrolünden önce değerlendirilir; sim zamanı durmuşken
steady deadline ilerler. Update callback'i hiç çalışmıyorsa bu plugin zamanında
fren garantisi veremez. Sim geri dönüşü ve steady geri dönüşü kapalı duruma
geçer; tam world reset/unload yaşam döngüsü bu testlerde doğrulanmaz.

[Doğrulama ve engeller](../../../docs/validation/c5/c5-b6b5-watchdog-2026-11-15.md).

## 18 Kasım native yetkilendirme uzantısı

`DiffDrive.cc`, yalnız ayrı B6B.7 build'inin seçtiği `C5_AUTH_ZERO_ONLY` derleme
kolunu da içerir. B6B.5'in varsayılan ham sıfır callback'i ve Lease davranışı
korunur; iki eski CTest yeniden geçti. B6B.7, aynı fizik/joint yazıcısını ve
değişmeyen Lease'i kullanarak StringMsg/HMAC kontrolünü native callback'e alır;
ayrı C++ sınıf sembolleri ve `c5::test::AuthorizedZeroDiffDrive` alias'ı kullanır.
Stock alias'ları bu build'de dışa aktarılmaz. Her iki build de yalnız sıfır
hedef üretebilir. [Yeni test kapsamı ve açık bağımlılıklar](../../../docs/validation/c5/traffic-integration-2026-11-18.md).
Eski kaynak/binary SHA kayıtları tarihsel kanıttır; yeni kaynakla eşleştiği
iddia edilmez ve bu değişiklikte yeniden yazılmaz.
