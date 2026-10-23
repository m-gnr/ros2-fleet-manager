# Docker yerleşimi karar taslağı: sınırlı DDS mesaj alımı

Tarih: 23 Ekim 2026.

Durum: Taslak — kullanıcı onayı bekleniyor.

## Bağlam

[Onaylı v2.3 geçiş kaydı](architecture-v2.3-transition.md), ExecuteTask/yürütücü yönünü ve kendi kapsam sınırlarını belirler; Docker yerleşimini onaylamaz. Kaydın Docker bölümü tarihsel öneri olarak korunur. `simulation`, `backend` ve `frontend` içeren üç servisli yerleşim hâlâ öneridir.

[DDS test kaydı](dds-validation-2026-10-22.md), iki container arasında gerçek mesaj alımının başarılı olduğunu belgeler. Bu taslak, mevcut kanıta dayanarak kullanıcıya yalnız aşağıdaki dar kapsamı onaya sunar. Kaynak önceliği [proje bağlamında](project-context.md) tanımlıdır.

## Seçenekler

1. Mevcut kanıtla yalnız iki container arasında belirtilen koşullarda DDS mesaj alımını kabul etmek; uygulama yerleşimi kararını açık bırakmak.
2. Dar kapsamlı kabulü de ertelemek; ek doğrulamalardan sonra yeniden değerlendirmek.

Tam Docker mimarisini onaylamak mevcut kanıtla desteklenmez ve bu taslağın seçenekleri arasında değildir.

## Seçilen yol

Kullanıcı onayına sunulan öneri **Seçenek 1**'dir. Henüz bir seçim onaylanmamıştır. Kullanıcı onay verirse kabul yalnız **linux/arm64, ROS 2 Humble, Cyclone DDS, ROS_DOMAIN_ID 42 ve tek Compose bridge ağı üzerinde iki container arasında DDS mesaj alınması** ile sınırlı olacaktır.

Bu kabul, tam Docker mimarisinin veya üç servisli yerleşimin onayı anlamına gelmeyecektir. Servis içerikleri ve uygulama yaşam döngüsü bu kayıtla karara bağlanmaz.

## Gerekçe

[Başarılı ikinci koşu](dds-validation-2026-10-22.md#koşular), backend'in beklenen mesaj içeriğini aldığını ve Compose ile iki container'ın sıfır çıkış koduyla tamamlandığını gösterir. Kanıt yalnız topic keşfine dayanmaz. Bu sonuç, sınanan DDS mesaj alımını kabul etmeyi önermek için yeterlidir; uygulama bileşenlerinin birlikte çalışmasını kanıtlamaz.

Image kimliği, paket sürümleri ve Docker ortamı için tek kaynak [gerçek test ortamı](dds-validation-2026-10-22.md#gerçek-test-ortamı) bölümüdür. Bu bilgiler burada tekrarlanmaz. Aynı bölümde belirtilen paket sürümü sabitleme sınırı nedeniyle yeni image için yeniden kanıt gerekir.

## Kapsam

- Yalnız `simulation` test yayıncısından `backend` test abonesine DDS mesaj alımı; bu servis adları gerçek uygulama bileşenlerinin doğrulandığı anlamına gelmez.
- linux/arm64, ROS 2 Humble, Cyclone DDS, ROS_DOMAIN_ID 42 ve tek Compose bridge ağı.
- Test kaydındaki image ve ayarlar altında, beklenen `std_msgs/msg/String` içeriğinin alındığı başarılı koşu. Mesaj kanıtı ve çıkış kodları [koşular bölümünde](dds-validation-2026-10-22.md#koşular), düzen ve QoS [test kaydında](dds-validation-2026-10-22.md#dosyalar-ve-ayarlar) bulunur.

## Kapsam dışı

Aşağıdakiler bu taslağın onay kapsamına girmez ve DDS mesaj alma kanıtından doğrulandıkları sonucu çıkarılamaz:

- Gazebo dünyası ve fizik/sensör çalışması.
- ROS–Gazebo köprüsü.
- Nav2 hazırlığı ve hareket yürütme.
- Action goal/result/cancel iletişimi.
- Fleet Manager.
- Frontend.
- Apply Configuration ve yeniden başlatma yaşam döngüsü.
- Farklı platform, RMW veya ağ koşulları.
- Uzun süreli dayanıklılık.

**Negatif kontrol yapılmadı:** Farklı domain ID kullanıldığında mesaj alınmaması sınanmadı. Domain ayrımı bu kayıtla doğrulanmış sayılmaz.

## Sonraki doğrulamalar

Aşağıdakiler ileride ayrı çalışmalar olarak ele alınacak doğrulama ihtiyaçlarıdır; bu taslak kapsamında yeni test eklenmedi veya çalıştırılmadı:

- Farklı domain ID ile mesaj alınmadığını negatif kontrolle doğrulamak.
- Image veya ortam değiştiğinde DDS mesaj alma kanıtını yeniden toplamak.
- Uygulama yerleşimi değerlendirilmeden önce action goal/result/cancel iletişimini, Nav2 hazırlığını ve Gazebo/ROS–Gazebo akışını ayrıca doğrulamak.
- Fleet Manager, frontend ve Apply Configuration için ilgili açık kararları kullanıcıyla netleştirmek; ardından bütünleşme ve yaşam döngüsü davranışlarını sınamak.
- Farklı platform/RMW/ağ veya uzun süreli dayanıklılık iddiası gerekiyorsa bunlar için ayrı kanıt toplamak.

Bu çalışmaların sonuçları ve daha geniş yerleşim onayı ayrı kayıtlarda ele alınmalıdır. Mevcut taslağın kapsamı kendiliğinden genişlemez.
