# Aşama 1.3 — Kalıcı düzeltme kapısı

11 Kasım 2026. **KANIT KAPISI GEÇTİ — YALNIZ GÖZLEM MODELİ ALANI.** Bu teknik seçim görevin kanıta dayalı düzeltme kapısı içindir; yeni mimari karar veya final kabul değildir. Seçime kadar varyantlar yalnız generated dosyalarında çalıştı; aşağıdaki seçimden sonra ortak şablonda tek model alanı değiştirildi.

## Kanıtlanan sorun ve sınırlar

Yeni A/pickup-2 aynı damgalı fiziksel raf açıklığı yaklaşık 0,399 m; TF map açıklığı yaklaşık 0,274 m. Güvenli circle+padding 0,31 m. Aynı local/global gridde tahmini merkez 99 (inscribed), gerçek fiziksel merkezin aynı frame'e dönüştürülmüş noktası 73; DWB BaseObstacle retleri ve terminal ABORTED var. Fiziksel hedefin kendisinde 0,44 m güvenli çember artık açıklığı vardır. Bu nedenle hedefin mutlak geometrik erişilemezliği kanıtlanmadı. AMCL map ayrışması ve sahte statik engel çatışması güçlü biçimde gösterildi; hareket/gözlem modelinin ayrı payları test ediliyor.

## Alternatifler

| Seçenek | İlk değerlendirme | Güvenlik ve karar |
|---|---|---|
| sigma_hit 0,20→0,05 | 3/3 Nav2 abort | REDDEDİLDİ; fiziksel kabul 0/3, covariance azalması yeterli değil |
| alpha1 0,20→0,02 | Fiziksel kabul 0/3; bir abort | REDDEDİLDİ; tek başına kanıtlı iyileşme yok |
| İzole raf ayırt ediciliği | Lidar görünürlüğü kanıtlandı; fiziksel kabul 1/3 | Ürüne taşınmaz; yalnız hipotez testi. Raf/istasyon sözleşmesi değiştirilmez |
| alpha4 0,20→0,002 | Saf dönüşte mikrometre öteleme karşısında modelin dönmeden öteleme varyansı şüphesi | Duyarlılık, farklı heading ve bağımsız kabul kapıları bekleniyor; fazla güvenli odom varsayımı farklı hareketlerde bozulabilir |
| alpha3 0,20→0,02 | Öteleme varyansını ayrı ayrıştırma | Henüz sonuç yok; ayrı üç koşu |
| sigma_hit 0,20→0,10; max_beams 60→180 | Daha ılımlı gözlem genişliği / ışın sayısı ayrı deneyler | Her biri tek alan ve ≥3 koşu; birleşik tuning yapılmaz |
| DWB/controller davranışını değiştirmek | AMCL etkisinden ayrı kanıt henüz yok | Güvenlik kontrolünü gevşetmek yok; yalnız lokalizasyon düzeldikten sonra artık hata sürerse ayrı değerlendirme |
| Hedef/raf taşımak | Statik hedef erişilemezliği kanıtlanmadı | Uygulanmaz; gerekirse ayrı kullanıcı kararı |
| Radius/collision küçültmek, TF offset, kabul eşiğini büyütmek, sahte başarı | Yasak | Uygulanmaz |

## Seçilirse değişecek dosya ve geri dönüş

En küçük olası ürün değişikliği, `config/simulation-c2-3-params.template.yaml` içinde yalnız kanıtlanan AMCL alanının eski→yeni değeridir. Bu ortak şablon olduğundan C3/C4 etkisi vardır; yalnız warehouse pickup başarısı yeterli değildir. Önce farklı heading'lerde karşılaştırma, sonra beş temiz dünya kabulü ve etkilenen canlı C3/C4 regresyonları gerekir. Kalıcılaştırma için gerçek fiziksel hata, güvenli duruş/contact ve action sonucu birlikte iyileşmelidir. Şablona yapılacak değişikliği yalnız ilgili satırı eski değere döndürerek geri almak mümkündür; başka kullanıcı diff'i geri alınmaz.

İlk alpha4 koşusu fiziksel kriteri sağladı (0,316666 m), ancak bridge kapanışı -11 ve simulation_exit=1 olduğu için temiz kabul REDDEDİLDİ. Kanıt silinmedi. Yeni ayrı `alpha4-0002-repeat` dizini üç bağımsız dünya için açıldı; bu tekrar önceki kapanış hatasını ortadan kaldırmış sayılmaz. Kök nedeni kanıtlanmadan bridge veya batarya kodu değiştirilmedi.

## Seçim — kalıcı satır değişikliğinden önce

`selection-evidence.json` dokuz bağımsız temiz dünyayı doğrular: varsayılan heading 3/3 (0,222592 / 0,244016 / 0,154323 m), heading=0 3/3 (0,215976 / 0,246245 / 0,215592 m), heading=π 3/3 (0,243519 / 0,179314 / 0,235232 m). Aynı heading'lerin eski model karşılaştırmaları sırasıyla 1/3, 1/3, 1/3. Hepsi gerçek SUCCEEDED, zararlı temas kaydı yok, odom duruşu doğrulanmış ve dünya kapanışı 0. Bu sınırlı örnekleme bütün koşullarda garanti değildir.

Seçilen dosya `config/simulation-c2-3-params.template.yaml`; yalnız `amcl.ros__parameters.laser_model_type: likelihood_field → beam`. Gerekçe: aynı fizik/model/controller ve gürültü parametrelerinde ray-menzil temelli gözlem modeli hem fiziksel hedef hatasını hem raf köşesi erişimini daha tutarlı yaptı. Kaynak `beam_model.cpp` map ray menzilini, eski model dolu hücreye uç uzaklığını kullanır; z_short/z_max katkıları beam ile etkinleşir. Bu tek model alanı deneyi, bu alt mekanizmaların her birinin nedensel payını ayrı ayrı ispatlamaz.

Alternatifler: sigma_hit 0,05 ve 0,10 abortlar üretti; alpha1 düzelmedi; alpha3 kararsız; alpha4 üç temiz koşuda sınır yakınında 0,230/0,340/0,341 m; max_beams=180 2/3; likelihood_field_prob 2/3. Raf girintisi 1/3. Bu varyantlar ürün ayarı olarak seçilmedi.

Güvenlik: iki costmap r=0,30+mevcut padding, inflation, fiziksel collision, 0,36 m track, TF, istasyonlar, xy/yaw toleransları, hız/ivme sınırları, controller/recovery ve C3/C4 ürün kapıları korunur. Beam gözlem modeli AMCL CPU ve hareketli/harita dışı cisimlere tepkiyi etkileyebilir. İlk üç koşuda beta AMCL ortalama CPU yaklaşık %3,5–3,7, RTF yaklaşık 0,98–1,00; kısa ölçüm tepe/ölçek garantisi değildir.

Geri dönüş: yalnız bu alanı `likelihood_field` yapmak; diğer kullanıcı dosyalarını veya geçmişi geri almamak. Regresyonlar: beş yeni bağımsız ürün ayarlı pickup, gerçek tek/paralel görev ve Chrome/SQLite/Outbox/epoch/UUID/C4 batarya, tam host/Humble, canlı C3.3.3/HIGH, ilgili C4 tüketim/telemetri ve dock temas/ayrılma senaryoları. Ortak şablon başka profilleri de etkiler. Bu kapı onların henüz geçtiği veya C5 final kabulü anlamına gelmez. Önceki bridge kapanış -11 bulgusu açık kalır; model değişikliği bunu çözmüş sayılmaz.

## Uygulama sonrası doğrulama

Ürün şablonuyla beş yeni temiz dünya 5/5: 0,253855 / 0,214297 / 0,282275 / 0,199725 / 0,172636 m. Her biri gerçek SUCCEEDED, zararlı temas kaydı yok, duruş ve veri eşleşmesi geçerli; beş kapanış 0. Doğru test DNS eşlemesiyle yeni tek görev scenario-a2 ve paralel scenario-b karşılaştırmalarının tüm kontrolleri geçti. İlk scenario-a görevinde taşıma tamamlanmış fakat test zarfındaki eksik scene aliası nedeniyle TF/görsel kabul kalmıştı; başarısız kayıt korundu.

Tam host 455 geçti / 29 ROS atlaması; tam Humble 505 geçti / atlama yok. Canlı C3.3.3 T01–T10, gerçek T04-HIGH-E2E, C4.1 tüketim, C4.2 güncellik/teslim ve eski C4 profilinde C4.4 dock temas/ayrılma geçti. Beş projenin tüm container çıkışları 0, OOM yok, simulation clean=true; saklanan DB kontrolleri temiz. Bunlar 30×18 m Aşama 2/3 veya C5 final kabulü değildir. Önceki üç tuning dünyasındaki bridge -11 kapanışı ayrı AÇIK BULGU kalır; yeni modelin bunu giderdiği iddia edilmez.
