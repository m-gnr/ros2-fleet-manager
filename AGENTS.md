## Başlamadan önce

- Mimari, planlama veya uygulama işinden önce `docs/project-context.md` dosyasını oku.
- Birincil nihai mimari referansı [ROS 2 Fleet Manager Nihai Mimari Kararlar](docs/ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.pdf) belgesidir: DOC-ARCH-2026-10-23-FINAL, v1.0, 23 Ekim 2026, 13 sayfa. İlgili bölümleri çalışmaya başlamadan önce oku.
- Kullanıcının kişisel notları korunur. Bu notları değiştirme, silme, özetleyip üzerine yazma.
- Eski README veya notlardaki farklı politikaları güncel kararların yerine sessizce uygulama. Çözülmemiş çelişki görürsen ilgili işi durdur ve sor.
- Karar gerektiren bir şeyi tek başına kilitleme. Bağlamı ve seçenekleri yaz, kullanıcıya sor. PDF'de açıkça onaylanan kararları tekrar öneri durumuna düşürme; önerileri de onaylanmış sayma.
- Hedef mimarinin onayı, uygulamanın tamamlandığı veya testlerinin geçtiği anlamına gelmez. Depodaki güncel uygulama ve test kanıtlarını ayrıca kontrol et.

## Doğruluk kaynakları

| Konu | Kaynak |
|---|---|
| Kullanıcı kuralları ve kalıcı proje bağlamı | `AGENTS.md`, `docs/project-context.md` |
| Birincil nihai mimari kararlar | `docs/ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.pdf` |
| Ayrıntılı karar geçmişi ve geçiş gerekçeleri | `docs/ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf`, `docs/architecture-v2.3-transition.md` |
| Doğrulama kanıtları ve hazırlık durumu | `docs/` altındaki aşama/test raporları ve B4 denetim raporu |
| Düzenlenebilir filo, robot, harita, istasyon ve batarya tanımları | `config/fleet.yaml` |
| Konfigürasyon şeması | `config/fleet.schema.json` ve ilgili doğrulayıcı |
| ROS arayüzleri (mesaj/action/servis) | `interfaces/` |
| Uygulanmış servis düzeni | `docker-compose.yml` |

- Nihai PDF, eski kararları ve 23 Ekim kararlarını birleştiren mimari başvuru belgesidir. Kullanıcı koruma ve çalışma kurallarını ortadan kaldırmaz.
- PDF bölüm 3'teki tarihsel kaynak sırası korunur: proje bağlamı/AGENTS, Revize Karar 08, v2.3 geçiş kaydı, 23 Ekim kararları, B4 raporu, eski belgeler. PDF'nin açık çelişki çözümlerini eski hükümlerle geri alma.
- PDF'de çözümlenmiş eski hükümler: ağırlıklı CostBased atama, FM'nin taşıma için doğrudan Nav2 hedefi yürütmesi, birimsiz SoC enerji hesabı, ayrı `stations.yaml`, MEDIUM preemption ve üç servisli yapının yalnızca öneri sayılması artık geçerli değildir.
- [Revize Karar 08](docs/ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf) ve [onaylı v2.3 geçiş kaydı](docs/architecture-v2.3-transition.md) ayrıntı ve geçmiş için korunur. Geçiş kaydının onayı tek başına Docker yerleşimi onayı değildir; üç servisli hedefin onayı nihai PDF'deki 23 Ekim kararından gelir.
- Eski belgeleri sessizce silme veya yeniden yazma. Hangi hükmün hangi kararla değiştiğini ilgili `.md` kaydında gerekçesiyle belirt. Çözülmemiş kaynak veya belge içi çelişkide kendi başına karar verme.
- Compose, config ve kod mevcut uygulamayı gösterir; hedef mimariyle uyuşmamaları hedef kararın değiştiği anlamına gelmez.

## Mimari durum ve kapsam

- Durumları ayrı tut: **ONAYLANDI** (hedef karar), **DOĞRULANDI** (kapsamı belli test kanıtı), **HENÜZ TEST EDİLMEDİ**, **ÖNERİ**. Bir karar hem onaylı hem henüz test edilmemiş olabilir.
- PDF'nin 23 Ekim tarihli durumuna göre Fleet Manager, Robot Executor, Battery Simulator, FastAPI ve React UI henüz kodlanmamıştır; `fleet.yaml` C1 çıktısıdır. Bu tarihsel bilgiyi güncel depo incelemesi yapmadan bugünün durumu gibi tekrarlama.
- MVP: en az iki robot, bağımsız Nav2/AMCL, robot başına Executor ve Battery Simulator, öncelik/FIFO, güvenli preemption, şarj/park yönetimi, SQLite Outbox, FastAPI ve React + Konva 2D panel. Video akışı aktarılmaz.
- Genişletilmiş kapsam: üçüncü robotun dinamik eklenmesi, web üzerinden senaryo başlatma ve iki robotlu takas. C1'de üç robotlu config doğrulamak, üçüncü robotun canlı performansını doğrulamak değildir.
- Kapsam dışı: fiziksel robot entegrasyonu, dar koridor için küresel çarpışmasız trafik planlaması, otomatik palet mekanizması, şarj istasyonu elektriksel arızaları, çoklu aktif Fleet Manager ve canlı manager çökmesi sonrası otomatik devam. Manager çökmesinde senaryo reset esastır.

## Onaylı hedef mimari

### Üç servisli yerleşim

| Servis | Sorumluluk |
|---|---|
| `simulation` | ROS 2 Humble, Gazebo Fortress headless, DART, OGRE2/EGL yazılım render, `ros_gz_bridge`, Map Server; robot başına namespace içinde Nav2, AMCL, Robot Executor ve Battery Simulator |
| `backend` | Fleet Manager, görev kuyruğu ve zamanlayıcı, ROS 2 action/topic istemcisi, şarj/park rezervasyonları, FastAPI, WebSocket ve kalıcı volume üzerinde SQLite |
| `frontend` | React + Konva 2D harita, robot durumları ve görev arayüzü; backend ile HTTP/REST ve WebSocket |

- Hedef üç servisli Docker Compose düzenidir. Robot başına Compose servisi ekleme; robot düğümlerini config'den üret.
- `simulation` ile `backend` ROS 2/DDS üzerinden haberleşir. `frontend` DDS ağına bağlanmaz.
- Üç servisli hedef **ONAYLANDI**; nihai Compose düzeninin canlı uçtan uca çalışması PDF tarihinde **HENÜZ TEST EDİLMEDİ**. İki container DDS testlerini bunun yerine kanıt gösterme.
- C1 yalnızca konfigürasyon altyapısıdır; üç servisin tüm uygulamasını C1 kapsamına alma.

### Görev yürütme ve durum otoritesi

- Akış: `Fleet Manager -> ExecuteTask -> Robot Executor -> NavigateToPose -> Nav2`.
- Fleet Manager görev kabulü, HIGH/MED/LOW öncelik, atanabilir görevler arasında FIFO, en yakın uygun robot seçimi, dinamik enerji uygunluğu ve kaynak rezervasyonlarını yönetir. Ağırlıklı CostBased optimizasyonunu geri getirme.
- Fleet Manager çekirdeği tek olay tüketim döngüsü ve SQLite Outbox kullanır.
- Robot Executor robot başına `ExecuteTask` action sunucusudur; pickup, yükleme, dropoff ve boşaltma adımlarını yönetir. Taşıma adımlarını FM içinde doğrudan `NavigateToPose` çağrılarıyla yürütme.
- Nav2 rota planlama, yerel engel kaçınma ve hız kontrolünden sorumludur. FM enerji/mesafe için planner sorgulayabilir; bu, taşıma yürütücülüğünü devralması anlamına gelmez.
- Fiziksel robot durumunun otoritesi Robot Executor'dır. FM'deki robot kaydı `RobotStatus` verisinin kopyasıdır; FM'de ikinci bir fiziksel robot durum makinesi oluşturma.
- Sonuçları `task_id`, `assignment_epoch` ve action goal UUID ile eşleştir. Eski sonuçların yeni atamayı değiştirmesine izin verme.
- Arayüzleri PDF bölüm 11'e göre `interfaces/` altında yönet: `ExecuteTask.action`, `RobotStatus.msg`, `ClearRobotError.srv`. Kimlik, epoch, durum, hata ve enerji alanlarını ilgili dokümanlarla birlikte güncelle.

### Güvenli preemption

- Çalışan taşıma görevini yalnızca yeni bir HIGH görev kesebilir. LOW ve MEDIUM bunu yapamaz; çalışan HIGH görev kesilemez.
- IDLE ve enerji açısından uygun robot varsa HIGH görevi ona ata; çalışan görevi kesme.
- Kesilecek LOW/MEDIUM görev pickup öncesinde olmalı, `PICKING_UP` başlamamış olmalı, robot yüksüz (`loaded == NONE`) olmalı ve görev daha önce iki kez kesilmemiş olmalıdır.
- Kesilen görev orijinal `created_at` ile kuyruğa döner. N=2 kez kesilen görev üçüncü çalışmaya başladığında pickup öncesinde bile korunur.
- Executor iptali kabul ederse Nav2 hedefini durdurur ve sıfır hızı teyit eder. FM, terminal `PREEMPTED` action sonucunu almadan aynı robota yeni HIGH görev atayamaz; yalnız iptal kabulü yeterli değildir.
- İki robotlu takas MVP'de kapalıdır (`extra_swap_enabled = false`). %15 Nav2 rota kuralını tüm HIGH atamalarına uygulama; bu genişletilmiş kapsamdır.
- `RETURNING_TO_PARK` dönüşü LOW dahil her görev için kesilebilir. Bu, taşıma görevlerinin HIGH-only preemption kuralından ayrı bir park dönüşü kuralıdır.

### Hata kurtarma

- Etkin taşıma görevinin terminal Nav2/seyrüsefer veya planlama hatasında görev `FAILED`, robot `ERROR` olur. FM otomatik retry veya başka robota reassignment yapmaz.
- Robotun işgal ettiği kaynakları `BLOCKED` tut. Hata temizlenmesini kaynağın fiziksel olarak boşaldığına kanıt sayma.
- Kurtarma operatörün açık `ClearRobotError.srv` çağrısıyla, yüksüz ve güvenli duruş koşullarında yapılır. `loaded == ONBOARD` ise isteği reddet; `expected_epoch` sözleşmesini koru.
- Hata temizleme eski `FAILED` görevi yeniden başlatmaz.
- Atama öncesindeki rota/enerji uygunluğu sorgusunun başarısızlığını etkin görev hatasıyla karıştırma: atama yapılmaz, görev kuyrukta bekler.

### Wh enerji modeli ve Battery Simulator

- Temel enerji birimi Wh, kullanıcıya gösterim yüzde SoC'dir. Kapasite Wh, mesafe m, hareket katsayısı Wh/m, güç W olarak açıkça belgelenir.
- PDF bölüm 7'deki formülleri uygula:

```text
E_remaining = C_usable * (SoC / 100)
d_total = L(p_current, p_pickup) + L(p_pickup, p_dropoff)
E_escape = k * L(p_dropoff, p_safe_charge_station)
E_required = k * d_total + E_escape + E_margin
Atanabilirlik: E_required <= E_remaining - C_usable * SoC_emergency / 100
```

- `L`, Nav2 planner yol uzunluğudur. Kaçış enerjisini veya güvenlik marjını mesafeye ayrıca ekleyerek çift sayma.
- Planner yol hesaplayamazsa enerji uygunluğu başarısızdır; görevi o robota atama, kuyrukta tut.
- Robot başına bağımsız `battery_simulator`, enerji hesabının tek otoritesidir. FM ve Executor ikinci bir tüketim/şarj hesabı yürütmez.
- Hareket tüketimi odometri mesafesinden `k * delta_s` ile hesaplanır. Bekleme gücü yükleme/boşaltma dahil sürekli tüketilir.
- Zaman kaynağı yalnız Gazebo `/clock` ve `use_sim_time: true` olmalıdır. Wh hesabında süre saat cinsindedir; `delta_t` saniyeyse güç terimini `P * delta_t / 3600` olarak dönüştür.
- Şarj yalnız robot tanımlı istasyon yarıçapında, tamamen hareketsiz ve `dock_contact == true` iken enerji ekler.
- Batarya yayını `battery_energy_wh`, `battery_soc_percent`, `battery_capacity_wh`, `is_charging`, `battery_stamp` alanlarını taşır.
- 100 Wh, 0.20 Wh/m, 2 W, 20 W, 10 Wh marj ve %8 acil rezerv PDF'de örnek/kalibrasyonsuz değerlerdir. Örnek YAML'daki %25 düşük enerji eşiği gibi taslak değerleri de ayrıca onaylı kesin parametre sayma. %80 normal şarj hedefi ise açıkça onaylı politikadır.

### Şarj, park ve kaynak sahipliği

- Normal şarj hedefi %80 SoC'dir. Şarj kuyruğunda düşük SoC önce gelir, eşitlikte FIFO uygulanır.
- Robot başka robota yer açmak için %80 öncesinde zorla çıkarılamaz. Bekleyen görevi dinamik enerji koşuluyla yapabiliyorsa görev almak için erken ayrılabilir.
- Bekleyen robot yoksa %80 sonrasında istasyonda kalıp %100'e kadar şarj olabilir.
- Şarj veya park alanı fiziksel olarak terk edilmeden kaynak `FREE` ilan edilmez; pose/odometri teyidi ve tek sahiplik korunur.
- Görev bitiminde düşük enerjili robot şarja, yeterli enerjili robot en yakın boş rezerve parka gider. Park doluysa tanımlı güvenli bekleme alanını kullan; o da yoksa güvenli duruş ve operatör alarmı uygula.
- Park dönüşü görev için kesildiğinde rezervasyonu bırakma akışını uygula; fiziksel işgal sürüyorsa kaynağı erken `FREE` yapma.

## Config-driven kurallar

- Tek düzenlenebilir filo tanım kaynağı `config/fleet.yaml` olmalıdır. Ayrı `stations.yaml` veya aynı bilgileri tekrar eden ikinci bir filo config'i oluşturma.
- Robot sayısı, ID, isim, namespace, başlangıç pozu, harita yolu, Nav2 action adresi/parametreleri, batarya ve istasyon ayarlarını koda gömme. Filo tanımlarını `fleet.yaml` üzerinden yönet; harita gibi referans verilen varlıkları `config/` altında tut.
- Yeni robot eklemek yalnız config değişikliği olmalıdır. Kod veya Compose değişikliği gerektiriyorsa tasarımı düzelt. Bu ilke canlı hot-add özelliğinin MVP'de tamamlandığı anlamına gelmez.
- Her config dosyası için şema/doğrulama olsun. `fleet.yaml`, `config/fleet.schema.json` ve Pydantic doğrulayıcıyla başlangıçta doğrulanır; hata varsa net mesajla çık.
- Varsayılanlar tek yerde tanımlanır. Aynı değeri şema, kod ve dokümanda bağımsız varsayılanlar olarak çoğaltma.
- Ortama özgü değerler (port, domain ID) env değişkeni veya `.env` ile gelsin. PDF'deki test ortamı değerlerini koda sabitleme.
- `config/`, `simulation` container'ında salt okunur bağlanır. Simülasyon çalışma anında buraya yazmaz.
- Revizyon yaşam döngüsü `running_revision`, `desired_revision`, `pending_revision` kullanır. `POST /api/config/apply`, aktif görev ve yüklü robot olmadığını doğruladıktan sonra kontrollü servis yeniden başlatma akışını uygular. Bu yaşam döngüsü ilkesi C1'de tüm API'nin yazılmasını gerektirmez.
- **C1 öncesi netleştirilecek belge içi çelişki:** PDF bölüm 3 istasyonlar için `fleet.stations` derken bölüm 10 örnek YAML'ında `stations` kök düzeydedir. Tek dosya ilkesi kesinleşmiştir; alanın yerleşimini kullanıcıya sormadan şemada kilitleme. Örnek YAML'ı doğrudan nihai sözleşme sayma.

## C1-C5 geliştirme sırası

| Aşama | Çıktı | Kabul ölçütü |
|---|---|---|
| C1 - Konfigürasyon | `fleet.yaml`, `fleet.schema.json`, Pydantic doğrulayıcı, `test_config.py` ve sınır testleri | Kod değişmeden yalnız YAML ile 1, 2 ve 3 robotlu yapılandırmalar doğrulanır |
| C2 - Robot Executor | `ExecuteTask.action`, `RobotStatus.msg`, `fleet_robot_executor` | Tek robot simülasyonda ExecuteTask ile pickup, yükleme ve dropoff adımlarını başarır |
| C3 - Fleet Manager | Saf Python domain, tek consumer, öncelik/FIFO, preemption, SQLite Outbox | Simülasyonsuz T01-T09 testlerinde çift atama ve hatalı kesme olmaz; N=2 korunur |
| C4 - Batarya ve enerji | Bağımsız Battery Simulator, Wh modeli, şarj/park yöneticisi | Robot enerjisi bitmeden şarja gider; %80 ve görev için dinamik erken çıkış kurallarına uyar |
| C5 - API ve panel | FastAPI REST, WebSocket stream/replay, React + Konva | Web'den verilen görev 2D haritada izlenir, tamamlanınca durum güncellenir |

- Sırayı ve bağımlılıkları koru. Bir aşamanın çıktısını yazmak, kabul ölçütünün geçtiği anlamına gelmez.
- T01-T09 ayrıntılarını ilgili karar/test kaydından oku; yalnız numaralarına bakarak test kapsamı uydurma.

## Doğrulama sınırları ve açık öneriler

- PDF'nin kanıtları: iki container arasında DDS topic ve action goal/cancel/result; temel fizik ve Lidar; tek robot Nav2; B3 Retry'da iki robotun bağımsız Nav2 sürüşü için 2/2 temiz koşu.
- AMCL kasıtlı ofset sınaması 1 geçti / 1 kaldı sonucundadır. Tüm AMCL sınamalarını eksiksiz başarılı gösterme.
- İki robotlu sürüş kanıtı dinamik çarpışma önleme, dar koridor deadlock çözümü veya 3+ robot performansı kanıtı değildir. Bu alanlar ve üç servisli nihai uçtan uca dağıtım PDF tarihinde **HENÜZ TEST EDİLMEDİ**.
- Kaynak tüketimi ölçümleri kısa koşulara ve 0.5 saniyelik polling'e dayanır; ani tepe yükleri kaçabilir. Bunlardan ölçeklenebilirlik garantisi çıkarma.
- Aşağıdakiler **ÖNERİ** durumundadır; kullanıcı kararı olmadan zorunlu politika veya kesin kabul eşiği yapma:
  - A-DEC-01: `RobotStatus` 2.0 saniye kesilince STALE ve atama dışı bırakma.
  - A-DEC-02: iletişim kaybında 5.0 saniyede uyarı, 10.0 saniyede görevi `FAILED` yapma.
  - A-DEC-03: C4'te boş/yüklü üçer sürüşle batarya katsayılarını kalibre etme.
  - A-DEC-04: C5 sonunda macOS üzerinde bir saatlik üç servis dayanıklılık testi.
  - A-DEC-05: üçüncü robotta CPU limitini host çekirdeğine göre belirleme.
- Kalibrasyonsuz batarya katsayıları için deneysel doğrulama iddiasında bulunma. Sonradan onaylanan kararları ve yeni test kanıtlarını tarihli `.md` kayıtlarıyla belgele.

## Çalışma kuralları

- Yeni bir ayar eklerken config dosyasını, şemayı ve ilgili dokümanı birlikte güncelle.
- Değişiklikten sonra ilgili testi veya doğrulamayı çalıştır. Çalıştıramadıysan **doğrulanmadı** diye işaretle ve kullanıcıya bildir.
- Test sonucunu komut, kapsam ve sonuçla kaydet. Hedef mimari, tamamlanan kod ve doğrulanmış davranışı ayrı raporla.
- Kullanıcının kişisel notlarını veya mevcut PDF'leri bu güncellemenin parçası olarak değiştirme.

## Dokümantasyon kuralları

- Kod, config, arayüz veya Compose değişikliği yaptığında ilgili dokümanı aynı değişiklikte güncelle. Doküman güncellemesi işin parçasıdır.
- Dokümanlar `docs/` altında `.md` formatında tutulur. Yeni PDF ekleme. Mevcut PDF'leri silme veya üzerine yazma; `.md`'ye çevirme ayrı ve açık bir görev olarak yapılır. Yukarıdaki mevcut nihai PDF'ye referans verilmesi bu kuralı değiştirmez.
- Bir bilgi tek yerde yazılır, diğer yerlerden bağlantıyla referans verilir. Bu dosyadaki uygulama kurallarının ayrıntıları için nihai PDF'ye yönlendir; yeni paralel mimari şartnameler oluşturma.
- Dil: README ve `docs/` şimdilik Türkçe yazılır. İleride İngilizceye geçilecek; başlıkları sabit tut, cümleleri kısa ve çevrilmesi kolay yaz. Bir dosyada iki dil karıştırma. Mevcut dosyaları kendiliğinden çevirme; çeviri ayrı ve açık bir görevdir.
- Kod yorumları, commit mesajları, değişken/fonksiyon isimleri ve config alan adları İngilizce olur. Kod, komut, dosya adı ve teknik terimler olduğu gibi kalır.
- Karar gerektiren konuları karar kaydı olarak yaz: bağlam, seçenekler, seçilen yol, gerekçe. Alınmamış kararı alınmış gibi yazma; onay bekliyorsa belirt.
- Mimari değişiklikte diyagramı da güncelle. Mermaid kullan, görsel dosya ekleme. Diyagram etiketleri dokümanla aynı dilde olsun.
- Her config dosyası için alanları, birimleri ve varsayılanları açıklayan bir doküman veya şema yorumu olsun.
- Kodun ne yaptığını değil, neden öyle yapıldığını açıkla.

## README.md standardı

README kısa, güncel ve çalıştırılabilir olmalı. Ayrıntı için `docs/` içine yönlendirsin. Şu sırayı izle:

1. **Proje adı ve tek cümlelik açıklama**
2. **Mimari özeti**: Mermaid diyagramı ve üç servisin (`simulation`, `backend`, `frontend`) birer cümlelik görevi; hedef ve doğrulanmış durum ayrımı
3. **Gereksinimler**: Docker, Docker Compose sürümü, varsa GPU/donanım notu
4. **Hızlı başlangıç**: kopyala-yapıştır ile çalışan komutlar (`docker compose up`), ardından tarayıcıda açılacak adres
5. **Konfigürasyon**: `config/` yapısı, `fleet.yaml`, yeni robot ekleme adımları ve env değişkenleri
6. **Proje yapısı**: klasör ağacı ve her klasörün tek satırlık açıklaması
7. **Geliştirme**: test, derleme ve lint komutları
8. **Sorun giderme**: bilinen sorunlar; örneğin container'lar arası ROS/DDS keşfi
9. **Dokümantasyon bağlantıları**: nihai mimari PDF, proje bağlamı ve diğer ana belgeler
10. **Yol haritası**: C1-C5 ilerlemesi, planlanan ama uygulanmamış özellikler
11. **Lisans ve katkı** (gerekirse)

README kuralları:

- Her komutu yazmadan önce çalıştır. Çalıştıramadığın komutu **doğrulanmadı** diye işaretle ve kullanıcıya bildir.
- Sürüm numarası ve port gibi değerleri config'den ayrı tekrar yazma; mümkünse config dosyasına bağlantı ver.
- Ekran görüntüsü veya diyagram varsa kodla birlikte güncelle; yeni mimari diyagramlarda Mermaid kuralını uygula.
- Uygulanmamış özellikleri yapılmış gibi yazma. Planlananı **Yol haritası** altına koy. Onaylı hedefi test edilmiş uygulama gibi sunma.

## Komutlar

Bu dosya hazırlanırken proje deposunda çalıştırma yapılmadı. Aşağıdaki komutların doğrulama durumu korunmalı; depo incelenmeden test, derleme veya lint komutu uydurulmamalıdır.

| İşlem | Komut | Durum |
|---|---|---|
| Hepsini başlat | `docker compose up` | Doğrulanmadı; nihai üç servisli canlı kurulum kanıtı değildir |
| Backend testleri | Henüz belirlenmedi | Depodaki gerçek test düzeninden bulunup çalıştırılacak |
| ROS paketlerini derle | Henüz belirlenmedi | Depodaki gerçek workspace düzeninden bulunup çalıştırılacak |
| Lint | Henüz belirlenmedi | Depodaki araç yapılandırmasından bulunup çalıştırılacak |
