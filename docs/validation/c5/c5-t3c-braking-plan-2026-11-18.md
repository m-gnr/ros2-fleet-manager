# C5-T3C — Hareketli frenleme için önkoşullar ve deney planı

18 Kasım 2026. **ÖNERİ / HENÜZ TEST EDİLMEDİ.** Bu plan nonzero açma,
güvenlik bypass veya varsayılan launcher entegrasyonu onayı değildir.
[T3B'nin doğrulanmış altyapısı ve sınırları](c5-t3b-health-stop-2026-11-18.md)
hareketli duruş kabulünün yerine geçmez. T1/T2/T3A geçmiş kanıtları korunur.

## Hareket deneyinden önce gereken kapılar

1. Native update-loop, process ve bridge kaybında fiziksel actuator'u
   durdurabilen **bağımsız** mekanizma tasarlanmalı ve ayrı fault domain'i
   doğrulanmalı. Aynı Gazebo sürecini SIGSTOP etmek fiziği de durdurur;
   gerçek motorun frenlediğini göstermez. Aynı döngüdeki timer yeterli değildir.
2. Deney hareketi için ayrı açık yetkilendirme ve sınırlandırılmış test
   ortamı gerekir. T3B sıfır sürücüsüne nonzero/rearm/rollover eklemek,
   default demo/stock Twist yolunu açmak bu planın otomatik adımı değildir.
3. ROS kaynak kimliği ve session/context bağları kalifiye edilmeli.
   Humble graph GID gözlemi mesajın yayıncı kanıtı değildir. Mevcut
   ObservationHealth ve T2 observer yeniden kullanılmalı; kaynak ölçüm
   damgası, oturum/sıra, kullanılan ölçümler ve frame zinciri doğrulanmalı.
   SROS/OS erişim ve anahtar rolleri için gerçek negatif erişim testleri gerekir.
4. Gerçek sağlık çıktısının yerel izin/veto/actuator zincirine bağlanması,
   atomik yerel context uygulaması ve eski ACK/health ile yeniden açılmama
   doğrulanmalı. FM COMMIT, aktarım, doğrulama ve fiziksel uygulama ayrı kanıttır.
5. AMCL covariance'nin PSD/yaş sorunu ve lokalizasyonun **kesin hata sınırı**
   ele alınmalı. Sigma katsayısı seçmek tek başına bounded error kanıtı değildir.
6. Fiziksel model, yük, footprint, zemin/tutunma, wheel/actuator limitleri,
   mevcut Nav2 controller/behavior/smoother ayarları ve build hash'i sabitlenmeli.
   Değişen model/eski kalibrasyon aynı evidence hash'iyle kullanılamaz.

Bu mimari seçenekler henüz onaylanmış yeni ürün kararı değildir. Bağımsız
fail-safe ve kaynak kalifikasyonu çözülmeden hareketli kabul koşusu başlamaz.

## Ölçülecek büyüklükler

| Büyüklük | Gerekli deney/kanıt |
|---|---|
| Gövde hızı, açısal hız ve yol | Kalibre bağımsız pose/encoder gözlemi; stamp/frame, çözünürlük, örnekleme boşlukları ve hız hatası; yalnız komut hedefi yeterli değil |
| Minimum yavaşlama ve reaksiyonda maksimum ivme | İleri/geri/dönüş/birleşik hareket, yük ve zemin kapsamındaki gerçek hız eğrileri; jerk, slip, eğim ve kontrol doygunluğu etkileri |
| Algılama gecikmesi | Arızanın gerçek kaynağı kesildiği an → ilgili sağlık gözlemi; queued veri dahil |
| Hesaplama ve iletişim | Sağlık değerlendirmesi → kalıcı karar → aktarım; yük/kayıp/gecikme/tekrar altında kuyruk ve zaman bütçeleri |
| Actuator gecikmesi | Doğrulanmış duruş komutu veya bağımsız timeout → gerçek joint/gövde hızının tepki başlangıcı |
| Duruş süresi, mesafesi ve açısı | Kaynak kesimi/tehlike başlangıcından doğrulanmış ardışık durağan örneklere kadar; ölçüm boşluğunda oluşabilecek maksimum ek hareket dahil |
| Konum/hız hata ve marj | Ölçüm kalibrasyonu, model sapması ve kapsanmayan koşullar; keyfi katsayı veya yalnız covariance sigma'sı yok |

Kaynak ve alıcı monotonik saatleri doğrudan birbirinden çıkarılmaz. Yerel
süreler ve simülasyon saatindeki fiziksel ölçümler ayrı tutulur. Saat
eşlemesi/offset/hata modeli gerekiyorsa kalibre edilmeden toplam gecikme
garantisi verilmez. Durağan T3B ölçümleri bu tablodaki frenleme bounds'u
doldurmaz; eksikler bugün `StopInputs(None)` olarak sınırsız kalır.

## Hareket matrisi ve arızalar

- Önce tek robotta düşük hız; sonra **güncel config'deki** hız/dönüş
  sınırlarına kadar ayrı kademeler. Geri hareket, iki dönüş yönü, birleşik
  hareket, maksimum kapsam yükü ve farklı başlangıç ivmeleri ayrıca sınanır.
- Sonra iki ve üç robot: karşılıklı, kesişen ve aynı yönde yaklaşma; dar
  koridor, hareketsiz peer, park ve şarj yaklaşması. Her peer'in kendi
  duruş alanı ve belirsizliği toplam alanı genişletir; yol verme varsayılmaz.
- Hareket sırasında TF, odometry, AMCL, ObservationHealth gecikmesi/kaybı/
  geçersizliği, clock pause/rewind, kaynak session değişimi, eski epoch,
  child/Path değişimi ve permit iptali uygulanır.
- Executor/FM/bridge SIGKILL, ağ kopması ve gecikmiş/duplicate paketler;
  native update-thread durması ve bütün process ölümü ayrı testlerdir.
  Fizik hâlâ ilerlerken bağımsız frenin çalıştığı gözlenmelidir.
- Karşıt native/odometry gözlemleri, geç native health/ACK ve kalıcı DB
  kararı ile alıcının ayrışması sınanır. Release ve hold/resume ayrı kabul
  kapsamlarıdır; testin cleanup'ı sahipliği zorla bırakmaz.

Her koşul yeni izole senaryo/DB/reset kullanır. BLOCKED kaynak veya eski
session açılmaz. Arıza başlangıcı, tüm gözlem/komut/ACK/physical kanıtları,
build/config hash'leri ve başarısız denemeler korunur. Başarı ölçümü örnek
sayısından veya tek kısa koşudan türetilmez; tekrar/yük/süre kapsamı ayrıca
onaylanır. Denenmeyen bölge kalibrasyon dışıdır.

## Kabul için aranacak sonuçlar

Gerçek gözlenen duruş alanının ölçüm/model hatası dahil koşullu hesap alanı
içinde kaldığı; alanın mevcut B6B rezervasyon birleşimine bütünüyle sığdığı;
karşı robotun alanıyla çakışma hâlinde önceden bekleme/duruş sağlandığı
gösterilmelidir. Kaynak veya bağımsız fren belirsizliğinde varsayılan sonuç
hareket uygunsuz / bounded stop unknown olmalıdır. Physically stopped,
APPLIED ve resource release ayrı kalifiye kanıtlar gerektirir.

Başarılı bir alt deney tüm konfigürasyonlar, donanım veya gerçek dünya için
garanti değildir. Bu kapılar sağlanmadan T3C için **güvenli hareket kabulü
yoktur**; T3B'nin teslimi yalnız altyapı ve doğrulanmış durağan hata gözlemidir.
