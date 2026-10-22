## Başlamadan önce
- Mimari, planlama veya uygulama işinden önce `docs/project-context.md` dosyasını oku.
- Eski README veya notlardaki farklı politikaları güncel kararların yerine sessizce uygulama. Çelişki görürsen dur ve sor.
- Kullanıcının kişisel notları korunur. Bu notları değiştirme, silme, özetleyip üzerine yazma.
- Mimari yön için [Revize Karar 08](docs/ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf) ve [onaylı v2.3 geçiş kaydı](docs/architecture-v2.3-transition.md) esas alınır. Karar 08, ExecuteTask/yürütücü yönünü de kapsar: Fleet Manager ExecuteTask gönderir; robot yürütücüsü pickup/dropoff Nav2 hedeflerini yürütür. Kaynak önceliği [proje bağlamında](docs/project-context.md) tanımlıdır. Geçiş kaydının onayı Docker yerleşiminin onayı değildir.
- Karar gerektiren bir şeyi tek başına kilitleme. Seçenekleri yaz, kullanıcıya sor.

## Doğruluk kaynakları
| Konu | Kaynak |
|---|---|
| Kararlar ve proje bağlamı | `docs/` |
| Robot, harita, görev, batarya ayarları | `config/` |
| ROS arayüzleri (mesaj/action/servis) | `interfaces/` |
| Servis düzeni | `docker-compose.yml` |

## Config-driven kurallar
- Robot sayısı, isimleri, namespace'leri, başlangıç pozları, harita yolu, batarya eşikleri ve Nav2 parametreleri gibi sonradan değişebilecek değerleri koda yazma. `config/` altına taşı ve belgele.
- Yeni robot eklemek sadece config değişikliği olmalı. Kod veya Compose dosyası değiştirmeyi gerektiriyorsa tasarımı düzelt.
- Her config dosyası için şema/doğrulama olsun. Başlangıçta doğrula, hatalıysa net mesajla çık.
- Varsayılan değerler tek yerde tanımlı olsun. Aynı değeri iki yerde tekrarlama.
- Ortama özgü değerler (port, domain ID) env değişkeni veya `.env` ile gelsin.
- `config/` simülasyon container'ında salt okunur bağlanır. Çalışma anında yazma.

## Çalışma kuralları
- Yeni bir ayar eklerken config dosyasını, şemayı ve ilgili dokümanı birlikte güncelle.
- Değişiklikten sonra ilgili testi veya doğrulamayı çalıştır. Çalıştıramadıysan "doğrulanmadı" diye işaretle ve kullanıcıya bildir.

## Dokümantasyon kuralları
- Kod, config, arayüz veya Compose değişikliği yaptığında ilgili dokümanı aynı değişiklikte güncelle. Doküman güncellemesi işin parçasıdır.
- Dokümanlar `docs/` altında `.md` formatında tutulur. Yeni PDF ekleme. Mevcut PDF'leri silme veya üzerine yazma; `.md`'ye çevirme ayrı ve açık bir görev olarak yapılır.
- Bir bilgi tek yerde yazılır, diğer yerlerden bağlantıyla referans verilir.
- Dil: README ve `docs/` şimdilik Türkçe yazılır. İleride İngilizceye geçilecek; başlıkları sabit tut, cümleleri kısa ve çevrilmesi kolay yaz. Bir dosyada iki dil karıştırma. Mevcut dosyaları kendiliğinden çevirme, çeviri ayrı ve açık bir görevdir.
- Kod yorumları, commit mesajları, değişken/fonksiyon isimleri ve config alan adları İngilizce olur. Kod, komut, dosya adı ve teknik terimler olduğu gibi kalır.
- Karar gerektiren konuları karar kaydı olarak yaz: bağlam, seçenekler, seçilen yol, gerekçe. Alınmamış kararı alınmış gibi yazma.
- Mimari değişiklikte diyagramı da güncelle. Mermaid kullan, görsel dosya ekleme. Diyagram etiketleri dokümanla aynı dilde olsun.
- Her config dosyası için alanları, birimleri ve varsayılanları açıklayan bir doküman veya şema yorumu olsun.
- Kodun ne yaptığını değil, neden öyle yapıldığını açıkla.

## README.md standardı
README kısa, güncel ve çalıştırılabilir olmalı. Ayrıntı için `docs/` içine yönlendirsin. Şu sırayı izle:

1. **Proje adı ve tek cümlelik açıklama**
2. **Mimari özeti**: Mermaid diyagramı + üç servisin (`simulation`, `backend`, `frontend`) birer cümlelik görevi
3. **Gereksinimler**: Docker, Docker Compose sürümü, varsa GPU/donanım notu
4. **Hızlı başlangıç**: kopyala-yapıştır ile çalışan komutlar (`docker compose up`), ardından tarayıcıda açılacak adres
5. **Konfigürasyon**: `config/` yapısı, yeni robot ekleme adımları, env değişkenleri
6. **Proje yapısı**: klasör ağacı ve her klasörün tek satırlık açıklaması
7. **Geliştirme**: test, derleme ve lint komutları
8. **Sorun giderme**: bilinen sorunlar (ör. container'lar arası ROS/DDS keşfi çalışmıyorsa ne yapılır)
9. **Dokümantasyon bağlantıları**: `docs/` altındaki ana dosyalar
10. **Yol haritası**: planlanan ama uygulanmamış özellikler
11. **Lisans ve katkı** (gerekirse)

README kuralları:
- Her komutu yazmadan önce çalıştır. Çalıştıramadığın komutu "doğrulanmadı" diye işaretle ve kullanıcıya bildir.
- Sürüm numarası ve port gibi değerleri config'den ayrı tekrar yazma, mümkünse config dosyasına bağlantı ver.
- Ekran görüntüsü veya diyagram ekliyorsan kodla birlikte güncelle.
- Uygulanmamış özellikleri "yapıldı" gibi yazma. Planlananı "Yol haritası" altına koy.

## Komutlar
- Hepsini başlat: `docker compose up`
- Backend testleri: `<komut>`
- ROS paketlerini derle: `<komut>`
- Lint: `<komut>`
