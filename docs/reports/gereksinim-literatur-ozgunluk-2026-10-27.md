# ROS 2 Fleet Manager
## Gereksinim Analizi, Literatür Taraması ve Özgünlük Değerlendirmesi

**Araştırma ve teknik değerlendirme raporu**

27 Ekim 2026 · Sürüm 1.0

Depo tabanı: `63b8075456d56e49e8899ff26545da8e6b4ae86f`

**Odak:** İki robotlu depo lojistiğinde görev atama, güvenli kesme, durum tutarlılığı ve enerji farkındalığı.

Bu belge, proje kaynakları ile akademik yayınların ve açık kaynak yazılımların sınırlı, hedefli incelemesine dayanır. Yeni mimari karar, ürün kabulü veya emniyet sertifikasyonu değildir.

**Temel değerlendirme**

Proje, kontrollü bir araştırma ve eğitim platformu olarak teknik açıdan anlamlı ve geliştirmeye değerdir. Mevcut kanıtlar yeni bir görev atama algoritması ya da endüstriyel kullanıma hazır bir filo ürünü iddiasını desteklememektedir. Katkı potansiyeli, açık güvenlik sözleşmelerinin uygulanması ve bunların tekrarlanabilir deneylerle sınanmasıdır.

**Belge kapsamı**

Gereksinim gerekçeleri · 24 maddelik izlenebilirlik · Akademik bağlam · Açık kaynak karşılaştırması · Uygulama boşlukları · Koşullu sonuç

Hazırlama yöntemi: kaynak incelemesi, kod denetimi, host test tekrarı ve internet taraması. Mevcut PDF’ler, kişisel notlar, ürün kodu, konfigürasyon ve mimari kararlar değiştirilmemiştir.

<!-- pagebreak -->

# Yönetici özeti

Proje, birden fazla mobil robotun taşıma taleplerini öncelik, uygunluk, rota mesafesi, enerji ve kaynak sahipliği altında yürütmesini amaçlamaktadır. Temel problem yalnız hedefe ulaşmak değildir: bir görev kesilirken eski sonucun yeni atamayı kapatmaması, iletişim belirsizliğinin fiziksel duruş sayılmaması ve şarj/park alanının erken serbest bırakılmaması da gereklidir. Bu ayrımlar onaylı proje sözleşmelerinde açıkça yer almaktadır. [22], [23], [24], [25], [26]

27 Ekim depo incelemesinde C1 doğrulayıcısı, C2 Executor, C3 domain/Outbox/ROS adaptörleri ve iki robotlu test altyapısı bulunmuştur. C4 Battery Simulator, tamamlanmış şarj/park yönetimi, C5 FastAPI/React paneli ve nihai üç servisli uygulama Compose’u bulunmamıştır. Yeniden çalıştırılan host testleri **224 geçti, 19 atlandı** sonucunu vermiştir. Bu sonuç ROS/DDS ve Gazebo’nun bu tarihte yeniden doğrulandığı anlamına gelmez. [28], [29], [30], [31]

Literatür, görev atama, enerji farkındalığı ve çevrimiçi lojistik koordinasyonunun yerleşik araştırma alanları olduğunu göstermektedir. Open-RMF görev planlama, enerji, trafik koordinasyonu ve web bileşenleriyle; openTCS ise araç yönlendirme, dağıtım ve kaynak yönetimiyle önemli benzerlikler sunar. Dolayısıyla projenin gerekçesi bu yeteneklerin açık kaynakta bulunmadığı iddiası olamaz. [1], [2], [10], [11], [14], [15]

**Desteklenebilir katkı:** sınırlı kapsam içinde öncelik/FIFO, N=2 kesme koruması, Executor otoritesi, oturum/sıra/epoch/UUID ayrımı ve Outbox davranışlarının açık gereksinim–kod–test ilişkisiyle ele alınması. Bu, mevcut mekanizmaların özgün bir mühendislik düzenlemesi olabilir; bilimsel yenilik için karşılaştırmalı deney ve genellenebilir sonuç gerekir.

**Başlıca koşullar:** gerçek terminal epoch zorunluluğundaki fallback’in, enerji politikalarının runtime bağlantısının ve fiziksel kaynak serbest bırakma sınırlarının giderildiği ayrıca doğrulanmalıdır. Batarya ve web hedefleri tamamlanmadan uçtan uca ürün kabulü yapılamaz. [29], [31]

## Okuma haritası

| Bölüm | İçerik |
|---|---|
| 1–3 | Yöntem, problem, güncel uygulama |
| 4.1–4.6 | G01–G24 gereksinim analizi |
| 5.1–5.3 | Literatürün tematik sentezi |
| 6.1–6.3 | Kanıta dayalı karşılaştırma |
| 7–9 | Özgünlük, uygulanabilirlik, sonuç |
| Kaynakça ve Ek A | Kaynak kimlikleri ve test izlenebilirliği |

<!-- pagebreak -->

# 1. Araştırma yöntemi

**Tarama tarihi:** 27 Ekim 2026, Europe/Istanbul. İnceleme, sistematik derleme veya tüm açık kaynak evrenini kapsayan tarama değildir. Önceden tanımlanan proje sorularını yanıtlayan, kaynak kodla desteklenmiş hedefli bir literatür ve uygulama incelemesidir. Ayrı tarama eki, sorguları, seçme gerekçelerini, erişim sorunlarını ve incelenen commit’leri içerir.

Akademik kaynaklar yayıncı sayfaları, arXiv, üniversite arşivleri ve DOI metadata kayıtlarından; yazılım kaynakları resmî belgeler ve GitHub depolarından elde edilmiştir. Genel web araması keşif için kullanılmış, teknik çıkarımlar birincil kaynaklara dayandırılmıştır. Crossref, seçili yayınların yazar, başlık ve tarih kontrolünde kullanılmıştır. IEEE Xplore, Scopus veya Web of Science üzerinde eksiksiz veri tabanı taraması yapılmamıştır.

**Dahil etme ölçütleri:** görev atama, depo lojistiği, enerji/şarj, ROS 2 entegrasyonu, komut teslimi veya doğrulama sorularından en az birine doğrudan katkı; doğrulanabilir yazar/kurum; erişilebilir özet, belge veya kaynak kod. Temel çalışmalar ile 2024–2026 tarihli örnekler birlikte değerlendirilmiştir. Yalnız pazarlama anlatıları, kimliği doğrulanamayan depolar ve konu dışı optimizasyon çalışmaları ana karşılaştırmaya alınmamıştır.

**İnceleme derinliği:** bazı akademik çalışmaların yalnız özet ve metadata düzeyi okunabilmiştir. Bunlardan algoritmik ayrıntı, üstünlük veya deney tekrarı sonucu çıkarılmamıştır. Yazılım API ve test dosyaları okunmuş, karşılaştırılan sistemler kurulup çalıştırılmamıştır. GitHub `main/master` görüntüleri sabit commit’lerle kaydedilmiştir; bunların Humble uyumluluğu varsayılmamıştır. Nav2 ve ROS belgelerinde özellikle `humble` dalı incelenmiştir.

## Kanıtların yorumu

| Etiket | Anlam |
|---|---|
| ONAYLANDI | Proje kaynağında kabul edilmiş politika; kod/test başarısı değil. |
| DOĞRULANDI | Adı ve kapsamı belirtilen testin başarılı sonucu. |
| HENÜZ TEST EDİLMEDİ | İlgili kabul davranışı için yeterli koşu kanıtı yok. |
| ÖNERİ | Araştırmacı değerlendirmesi veya henüz onaylanmamış çalışma. |

Uygulama için ayrıca **MEVCUT**, **KISMİ**, **PLANLANAN** kullanılır. Bir gereksinim onaylı olup kısmen uygulanmış olabilir. Tablolardaki kabul ölçütleri kaynak davranışlarının sınanabilir anlatımıdır; yeni sayısal eşik veya yeni ürün politikası değildir. Kaynakta bulunmayan kabul ayrıntıları açık bırakılmıştır.

<!-- pagebreak -->

# 2. Problem, kullanım bağlamı ve sınır

Depo içi taşıma bağlamında görevler farklı önceliklerle gelir; robotların konumları, yükleri, bataryaları ve iletişim durumları değişir. En yakındaki robotun seçilmesi tek başına yeterli değildir: o robot yüklü, kesilemez fazda, düşük enerjili veya eski telemetriye sahip olabilir. Proje bu kısıtları merkezi görev sahipliği ile robotta yürütülen fiziksel süreç arasında ayırır. [22], [23], [24], [25]

## Paydaşlar ve kullanım senaryoları

| Paydaş / senaryo | Beklenti ve kaynak ilişkisi |
|---|---|
| Operatör | Taşıma talebi girme, ilerlemeyi izleme, hata nedenini görme ve koşullu hata temizleme; panel hedefi [22], [24]. |
| Geliştirici / araştırmacı | Deterministik politikaları değiştirmeden inceleme, olay kimliği ve kayıt üzerinden yarışları tekrar üretme [25], [26]. |
| Test sorumlusu | Birim, ROS/DDS ve fiziksel simülasyon kanıtlarını ayırma; aynı T numarasını farklı kayıtlarda eşdeğer saymama [28], [29], [30], [31]. |
| Normal taşıma | Uygun robot seçilir; Executor pickup, yükleme, dropoff ve boşaltmayı yürütür [22], [25]. |
| Acil taşıma | Önce uygun IDLE aranır; yoksa yalnız izinli LOW/MEDIUM görevi güvenli biçimde kesilir [23], [25]. |
| Enerji / kaynak | Şarj sırası, park rezervasyonu ve fiziksel ayrılma denetlenir; bütün akış henüz ürünleşmemiştir [22], [29]. |
| Hata / belirsizlik | Kesin Nav2 hatası ile iletişim kesintisi ayrılır; operatör müdahalesi eski FAILED işi otomatik başlatmaz [25]. |

Paydaş tanımları mevcut işlevlerden türetilmiş analizdir; yeni kullanıcı araştırması veya saha görüşmesi yapılmamıştır. Gerçek depo verimlilik kaybı, görev geliş dağılımı ve operatör iş yükü ölçülmediğinden sayısal iş değeri iddia edilemez.

**Sistem içi hedef:** en az iki robot, bağımsız Nav2/AMCL, robot başına Executor ve Battery Simulator; FM, SQLite, REST/WebSocket ve ROS verisini gösteren React/Konva paneli. Hedef dağıtım üç servistir: simulation, backend, frontend. Frontend DDS ağına katılmaz; video aktarılmaz. [22]

**Kapsam dışı:** fiziksel robot güvenlik sertifikasyonu, küresel çarpışmasız trafik/dar koridor çözümü, otomatik palet mekanizması, elektriksel şarj arızaları, çoklu aktif FM ve canlı çökme sonrası otomatik devam. Üçüncü robotun dinamik eklenmesi, web senaryoları ve iki robotlu takas genişletilmiş kapsamdır. Bağımsız Nav2 yığınları trafik koordinasyonu garantisi değildir. [22], [23], [25]

<!-- pagebreak -->

# 3. Güncel uygulama ve kanıt sınırı

İnceleme, depo HEAD’i ile mevcut çalışma ağacı üzerinde yapılmıştır. Başlangıçta `docs/README.md` değişikti ve `docs/reports/` altında kişisel raporlar vardı; bunlar korunmuştur. Aşağıdaki durum geçmiş özetin kopyası değil, dosya ve işlev incelemesinin sonucudur. [29], [30], [31]

| Alan | 27 Ekim 2026 bulgusu | Kanıt sınırı |
|---|---|---|
| C1 | Şema, Pydantic doğrulayıcı, YAML ve testler MEVCUT. | CLI doğrulaması Apply API veya canlı hot-add değildir. |
| C2 | Executor durum makinesi, ROS node, action/service IDL MEVCUT. | Ürün reset prosedürü ve bütün duplicate yanıt yolları tamamlanmış sayılmaz. |
| C3 | Kuyruk, zamanlayıcı, Wh uygunluğu, SQLite Outbox ve adaptörler MEVCUT/KISMİ. | Onaylı sözleşmeye uymayan sınır yolları vardır. |
| C4 | Bağımsız ürün Battery Simulator PLANLANAN. | Mock besleyici sabit test girdisidir; fiziksel enerji kanıtı değildir. |
| C5 | FastAPI, WebSocket, React/Konva PLANLANAN. | Panel kabulü ve nihai üç servisli ürün çalışması yoktur. |

**Yeniden çalıştırılan kontrol:** host pytest **224 passed, 19 skipped, 3.75 s**, çıkış 0. Config CLI **VALID: 2 robots**. Süre bir benchmark değildir. Atlanan testler başarı hanesine yazılmamış, ROS/Gazebo koşuları yeniden başlatılmamıştır.

**Tarihsel kanıt:** C3.3.3 raporu 24 Ekim’de T01–T10 için 10/10 bildirir. Ancak çalıştırıcıda T05 N=2 ve T06 istasyon ayrılması saf domain girdileriyle; T07 zaman ilerletme ile; T08 oturum olayı enjeksiyonuyla sınanır. T02 ve T04 rota önbelleği önceden doldurulur. T03 gerçek Nav2 sorgusunu ayrıca denetler. Bu nedenle bütün senaryoları fiziksel şarj, gerçek süreç restartı ve tam dinamik rota zinciri olarak sunmak yanlıştır. [28], [31]

**Yeniden görülen önemli farklar:** `event_loop.py` eksik `completed_epoch` için `assignment_epoch` fallback’i tutar; `scheduler.py` enerji marjı/acil rezerv YAML politikalarını çağrıya iletmez; `builder.py` ilk şarj istasyonunu seçer ve import hatasında ham YAML’a döner. `reservations.unblock()` fiziksel ayrılma koşulunu kendisi denetlemez. FM atama sırasında robot durum kopyasına yazmaktadır. [29], [31]

Bu bulgular yeni mimari karar gerektirmeden raporlanabilir; bu görevde düzeltilmemiştir. `stations` yerleşimindeki belgesel çelişki de kapatılmamıştır: mevcut C1 kök alanı korunur, ayrı kullanıcı onayının eksikliği yeni onaya dönüştürülmez. [27], [29]

<!-- pagebreak -->

# 4.1. Görev atama ve öncelik

Öncelik, uygunluk ve adalet farklı özelliklerdir. Atanabilir FIFO, uygun olmayan işi atlayarak kaynak kullanımını sağlar; başlamamış LOW görevine sonlu bekleme garantisi vermez. N=2 yalnız yeniden başlayan işi korur. Bu sınır onaylı aging yokluğu ile tutarlıdır; bekleme sorununu çözmek için yeni politika eklenmemiştir. [23], [25]

| ID | Açıklama ve gerekçe | Kaynak / öncelik ve onay |
|---|---|---|
| G01 | **Öncelik ve atanabilir FIFO.** Uygunsuz kuyruk başı tüm filoyu bekletmemeli; yaş korunmalıdır. | [23], [25] MVP / ONAYLANDI |
| G02 | **Nav2 mesafesiyle robot seçimi.** Kuş uçuşu mesafe engelleri ve erişilebilirliği temsil etmez. | [22], [25] MVP / ONAYLANDI |
| G03 | **Kesilebilir taşıma filtresi.** Acil talep fiziksel yükleme ve yük güvenliğini bozmamalıdır. | [23], [25] MVP / ONAYLANDI |
| G04 | **Tamamlanan kesme ve N=2.** Tekrarlı kesilme, başlamış işin sürekli geri bırakılmasını sınırlamalıdır. | [23], [25] MVP / ONAYLANDI |

| ID | Kabul ölçütü | Uygulama durumu | Test kanıtı / sınır |
|---|---|---|---|
| G01 | HIGH→MEDIUM→LOW; sınıf içinde original created_at; uygun adayı olmayan iş atlanır, yaş yenilenmez. | MEVCUT: task_queue ve schedule_tick. | test_fleet_manager_domain: FIFO/priority; R01 davranışının tüm kombinasyonları için kapsama sınırı sürer. |
| G02 | Uygun IDLE öncelikli; en kısa pickup rotası, eşitlikte en uzun IDLE, ardından robot ID; rota yoksa atama yok. | KISMİ: scheduler ve route resolver var; cache robot izolasyon sınırı açık. | test_t04_nearest_idle_robot_selection; eşitlik ve route_failure testleri; tarihsel T03. |
| G03 | Yalnız yeni HIGH; uygun IDLE yokken LOW/MEDIUM, pickup öncesi, yüksüz ve sayaç<2; çalışan HIGH korunur. | MEVCUT: scheduler ve Executor yerel faz kilidi. | test_t03_no_preemption_by_low_or_medium; test_t07/test_t08; Executor testleri. |
| G04 | Sayaç yalnız terminal PREEMPTED sonrası artar; N=2 sonrası yeniden başlayan iş korunur; created_at sabittir. | MEVCUT: task/model ve core; lojistik tam akış KISMİ. | test_n2_preemption_counter_and_immunity; test_t09_preempted_task_preserves_original_created_at. |

Test adları Ek A’daki dosyalara bağlanır. “MEVCUT” etiketi bütün hata yollarının doğrulandığı anlamına gelmez. Kabul tanımı onaylı kaynaklardan türetilmiştir; bu rapor yeni onay vermez.

<!-- pagebreak -->

# 4.2. Yürütme ve fiziksel güvenlik

Buradaki güvenlik, uygulama değişmezlerinin korunması anlamındadır. Fiziksel emniyet sertifikası veya insanlarla ortak çalışma güvenliği sonucu değildir. Özellikle goal kabulü, cancel kabulü ve terminal fiziksel duruş üç ayrı kanıt seviyesidir. [23], [25]

| ID | Açıklama ve gerekçe | Kaynak / öncelik ve onay |
|---|---|---|
| G05 | **Sorumluluk ayrımı.** Merkezi seçim ile fiziksel taşıma yürütümü çift komut üretmemelidir. | [22], [24], [25] MVP / ONAYLANDI |
| G06 | **Fiziksel durum otoritesi.** Feedback veya kabul yanıtı fiziksel fazı kanıtlamaz. | [24], [25] MVP / ONAYLANDI |
| G07 | **Güvenli terminal iptal.** İptalin kabulü robotun durduğu anlamına gelmez. | [25] MVP / ONAYLANDI |
| G08 | **Atama kimliği ve gerçek sonuç epoch’u.** Geç sonuç yeni sahibin işini kapatmamalıdır. | [25] MVP / ONAYLANDI |

| ID | Kabul ölçütü | Uygulama durumu | Test kanıtı / sınır |
|---|---|---|---|
| G05 | FM→ExecuteTask→Executor→NavigateToPose; pickup/yük/dropoff/boşaltma Executor’da. | MEVCUT: IDL, node, state_machine, action_client. | Executor yaşam döngüsü testleri; tarihsel C2.3 taşıma. |
| G06 | RobotStatus fiziksel görünüm; feedback ilerleme; result görev sonucu. Servis kabulü FM’de IDLE üretmez. | KISMİ: servis adaptörü uygun; core atamada state kopyasına yazıyor. | test_idle_before_terminal_cannot_double_assign; test_clear_robot_error_client; statik fark. |
| G07 | İlgili Nav2 goal STATUS_CANCELED, güncel odometri ve sıfır hız birlikte; doğal başarı/abort korunur. | MEVCUT: node, stop_detector, safety; eşiklerin kalibrasyonu ayrı. | test_executor_safety_ros2: ROS bağımlı; bu koşuda atlandı. Tarihsel C3.3.1 ve C3.3.3 T04. |
| G08 | task_id, assignment_epoch, UUID ve gerçek completed_epoch eşleşir; eksik/yanlış sonuç sahipliği kapatmaz. | KISMİ: adaptör gerçek alanı taşır; consumer fallback sözleşme açığıdır. | test_each_assignment_identity_component_is_required; test_old_result_after_next_assignment_and_invalid_result; fallback ayrı açık. |

Test adları Ek A’daki dosyalara bağlanır. “MEVCUT” etiketi bütün hata yollarının doğrulandığı anlamına gelmez. Kabul tanımı onaylı kaynaklardan türetilmiştir; bu rapor yeni onay vermez.

<!-- pagebreak -->

# 4.3. Tutarlılık, teslim ve yaşam döngüsü

SQLite işlemi veritabanı içindeki değişiklikleri birlikte korur; ağ ve robot fiziksel dünyası aynı transaction’a katılmaz. Retry bu boşlukla başa çıkar, fakat exactly-once ağ teslimi iddiası kurulamaz. Yeni oturum otomatik uzlaştırma yetkisi vermez. [25], [26]

| ID | Açıklama ve gerekçe | Kaynak / öncelik ve onay |
|---|---|---|
| G09 | **Yayın sırası ve oturum.** Gecikmiş telemetri ve restart aynı sıra akışı sayılmamalıdır. | [25] MVP / ONAYLANDI |
| G10 | **Atomik tek consumer ve Outbox.** Durum güncellendiği halde komut kaybolması veya çift sahiplik engellenmelidir. | [25], [26] MVP / ONAYLANDI |
| G11 | **İdempotent teslim ve açık ret.** Yanıt kaybı yeni görev değildir; açık ret kontrolsüz reassignment yaratmamalıdır. | [25], [26] MVP / ONAYLANDI |
| G12 | **İletişim zamanı ve restart sınırı.** Ağ sessizliği fiziksel hata veya reset kanıtı sayılamaz. | [25], [26] MVP / ONAYLANDI |

| ID | Kabul ölçütü | Uygulama durumu | Test kanıtı / sınır |
|---|---|---|---|
| G09 | status_seq oturumda 1’den başlar; eski/duplicate reddedilir; session değişimi atama/kaynak bırakmayı kilitler. | KISMİ: guard ve session blokajı var; consumer 0/uint64 üst sınırı tam değil. | test_sequence_does_not_wrap; test_session_change_preserves_ownership_and_blocks_robot. |
| G10 | Domain, rezervasyon, olay ve Outbox aynı SQLite transaction; commit sonrası bellek; ağ dışarıda. | MEVCUT: event_loop, store, schema. Cache callback yazımı domain garantisine genellenmez. | test_atomic_assignment_reservation_and_outbox; rollback/commit failure/concurrent producers testleri. |
| G11 | Retry aynı command/task/epoch/UUID/yük; ret HELD_FOR_REVIEW ve task_review_holds; duplicate kayıt kapasitesinde yeni kabul durur. | KISMİ: sender/guard/hold var; terminal duplicate sonucu geri sunma ürün akışı eksik. | test_retry_preserves_identity_and_blocks_later_send; test_task_review_holds_lifecycle; safety duplicate testleri. |
| G12 | 2 sn STALE, 5 sn uyarı; timeout FAILED/ERROR yapmaz; dolu DB otomatik devam etmez; ağ monotonik, fizik /clock. | MEVCUT/KISMİ: saatler ve başlangıç engeli var; ürün reset prosedürü eksik. | test_communication_loss_no_automatic_failure_and_reservation_ownership; test_restart_preserves_evidence_but_refuses_resume. |

Test adları Ek A’daki dosyalara bağlanır. “MEVCUT” etiketi bütün hata yollarının doğrulandığı anlamına gelmez. Kabul tanımı onaylı kaynaklardan türetilmiştir; bu rapor yeni onay vermez.

<!-- pagebreak -->

# 4.4. Enerji ve şarj kaynakları

Enerji uygunluğu ile enerji ölçümü ayrıdır: FM hesaplanan yeterliliği kullanır; hedef Battery Simulator tüketimin tek otoritesidir. Sabit bir SoC sınırı bütün görevleri temsil etmez. Mevcut katsayılar kalibre edilmiş fiziksel performans kanıtı değildir. [22], [27]

| ID | Açıklama ve gerekçe | Kaynak / öncelik ve onay |
|---|---|---|
| G13 | **Wh tabanlı atama uygunluğu.** Görev ve güvenli şarja erişim için yeterli enerji birlikte aranmalıdır. | [22], [25], [27] MVP / ONAYLANDI |
| G14 | **Bağımsız Battery Simulator.** Tüketim tek otoriteden gelmeli, simülasyon durunca fiziksel enerji akışı durmalıdır. | [22], [27] C4 / ONAYLANDI |
| G15 | **Şarj sırası ve çıkış.** Düşük enerjili robotun erişimi ile devam eden şarjın korunması dengelenmelidir. | [22], [23] C4 / ONAYLANDI |
| G16 | **Fiziksel kaynak sahipliği.** Mantıksal bırakma fiziksel boşlukla karıştırılmamalıdır. | [22], [25] MVP / ONAYLANDI |

| ID | Kabul ölçütü | Uygulama durumu | Test kanıtı / sınır |
|---|---|---|---|
| G13 | E_required=k·(L1+L2)+k·L_escape+E_margin ≤ E_remaining−E_emergency; kaçış/marj bir kez. | KISMİ: energy formülü var; YAML policy aktarımı ve çoklu güvenli şarj seçimi eksik. | test_required_energy_formula; test_energy_eligibility_sufficient/insufficient; statik builder/scheduler farkı. |
| G14 | Robot başına düğüm; k·delta_s ve P·delta_t/3600; /clock; şarjda yarıçap+duruş+dock_contact. | PLANLANAN: ürün düğümü yok; mock_battery_feeder otorite değildir. | HENÜZ TEST EDİLMEDİ; mevcut Wh fonksiyon testi batarya entegrasyonu değildir. |
| G15 | Düşük SoC önce, eşitte FIFO; yer verme %80 öncesi yok; enerji uygunsa görev için erken çıkış; bekleyen yoksa %100. | PLANLANAN: bazı enum/yardımcılar var, bütün politika yok. | HENÜZ TEST EDİLMEDİ; tarihsel T06 bu kuralın kabulü değildir. |
| G16 | Tek sahip; ayrılma doğrulanmadan FREE yok; belirsiz/işgal edilen hata kaynağı BLOCKED. | KISMİ: normal rezervasyon var; unblock ve doğrudan mark_occupied sınırları açık. | test_single_ownership_enforcement; test_physical_departure_rule; tarihsel T06 sentetik poz kullanır. |

Test adları Ek A’daki dosyalara bağlanır. “MEVCUT” etiketi bütün hata yollarının doğrulandığı anlamına gelmez. Kabul tanımı onaylı kaynaklardan türetilmiştir; bu rapor yeni onay vermez.

<!-- pagebreak -->

# 4.5. Lojistik, kurtarma ve yapılandırma

Görev başarısı, lojistik dönüş başarısı ve kaynağın fiziksel boşalması ayrı olaylardır. Aynı şekilde doğrulanan YAML, bütün runtime girişlerinin bu doğrulamayı kullandığını göstermez. Bu ayrımlar ürün kabulünün parça testlerinden daha geniş olmasını gerektirir. [25], [26], [27]

| ID | Açıklama ve gerekçe | Kaynak / öncelik ve onay |
|---|---|---|
| G17 | **Görev sonrası park / bekleme.** Görevsiz robotlar rastgele koridor hedeflerine gönderilmemelidir. | [22], [23] C4 / ONAYLANDI |
| G18 | **Lojistik sürüş kesmesi.** Park dönüşü taşıma işinin kesilme sayacıyla karıştırılmamalıdır. | [23], [25] MVP / ONAYLANDI |
| G19 | **Terminal hata ve manuel kurtarma.** Başarısız taşıma kendiliğinden tekrar edilmemeli, yüklü robot serbest bırakılmamalıdır. | [22], [23], [25] MVP / ONAYLANDI |
| G20 | **Config-driven filo ve fail-fast.** Robot/istasyon bilgisi farklı katmanlarda ayrışmamalıdır. | [22], [27] MVP / ONAYLANDI |

| ID | Kabul ölçütü | Uygulama durumu | Test kanıtı / sınır |
|---|---|---|---|
| G17 | Düşük enerji şarja; yeterli enerji en yakın boş rezerve parka; yoksa güvenli alan, o da yoksa duruş ve alarm. | KISMİ/PLANLANAN: rezervasyon primitive’leri var, orkestrasyon ve safe_waiting builder bağlantısı yok. | HENÜZ TEST EDİLMEDİ: tam görev-sonrası zincir. |
| G18 | Park dönüşü LOW dahil kesilebilir; enerji uygunluğu ve güvenli iptal; fiziksel doluluk korunur; taşıma sayacı artmaz. | KISMİ: durum yardımcıları var; uçtan uca park/şarj akışı tamamlanmamış. | Domain/Executor parça testleri; tam lojistik senaryo HENÜZ TEST EDİLMEDİ. |
| G19 | Etkin Nav2 hata→FAILED/ERROR; otomatik retry/reassignment yok; ClearRobotError doğru epoch, yüksüz ve güvenli duruş ister. | KISMİ: ROS node denetimleri var; saf state_machine çağrısında odometri atlanabilir; kaynak kurtarma bütün değil. | test_failed_result_blocks_resource_and_never_requeues; Executor hata testleri; tarihsel C2.3. |
| G20 | fleet.yaml tek kaynak; şema+Pydantic+dosya referansı kontrolü; bozuk config açık hata; robot sayısı koda gömülmez. | KISMİ: C1 güçlü; builder import fallback ve yinelenen varsayılanlar var. stations çelişkisi açık. | test_config, test_fleet_builder; CLI VALID: 2 robots. Canlı robot ekleme kanıtı yok. |

Test adları Ek A’daki dosyalara bağlanır. “MEVCUT” etiketi bütün hata yollarının doğrulandığı anlamına gelmez. Kabul tanımı onaylı kaynaklardan türetilmiştir; bu rapor yeni onay vermez.

<!-- pagebreak -->

# 4.6. Arayüz, panel ve dağıtım

İşlevsel olmayan gereksinimler burada sorumluluk izolasyonu, yapılandırılabilirlik, gözlenebilirlik ve yeniden üretilebilirlik olarak izlenir. Azami filo sayısı, p95 gecikme, kesintisiz çalışma süresi ve emniyet seviyesi için onaylı genel kabul eşikleri bulunmadığından yeni değer eklenmemiştir. [22], [25]

| ID | Açıklama ve gerekçe | Kaynak / öncelik ve onay |
|---|---|---|
| G21 | **Veri ve namespace sözleşmesi.** Robot verileri/eylemleri kimlik ve birim karışıklığı yaratmamalıdır. | [22], [25], [27] MVP / ONAYLANDI |
| G22 | **REST/WebSocket ve 2D panel.** Operatör tek görünümden gerçek ROS durumunu izleyebilmelidir. | [22], [24] C5 / ONAYLANDI |
| G23 | **Kontrollü config Apply.** Aktif taşıma sırasında yapılandırma değişikliği sahipliği bozmamalıdır. | [22], [24] Hedef ONAYLANDI; işletim ayrıntıları açık |
| G24 | **Dağıtım ve doğrulanabilirlik.** Simülasyon sonucu tekrarlanabilir ve kapsamı açık olmalıdır. | [22], [25], [28] MVP / ONAYLANDI |

| ID | Kabul ölçütü | Uygulama durumu | Test kanıtı / sınır |
|---|---|---|---|
| G21 | Ürün IDL ve robot namespace’leri; Wh/m/W/% birimleri; bağımsız TF/AMCL; TransportProbe yalnız testtir. | MEVCUT: üç ürün IDL; config’den iki robot test kurulumu. | test_c3_3_3_config; tarihsel T10; arayüz ve config statik kontrolü. |
| G22 | Görev/durum REST uçları, /ws/fleet ve React+Konva; video veya ayrı hareket simülasyonu yok; web’den görev izlenir. | PLANLANAN: ürün API/WS/UI kodu yok. Replay/backpressure ayrıntıları belirlenmemiş. | HENÜZ TEST EDİLMEDİ; 10 Hz hedefi var, gecikme/hacim kabul ölçütleri belirlenmemiş. |
| G23 | running/desired/pending revision; POST /api/config/apply; aktif görev/yük yokluğu ve kontrollü restart. | PLANLANAN: C1 doğrulama var; Apply runtime yok. Restart sahibi/başarısızlık ayrıntıları açık. | HENÜZ TEST EDİLMEDİ; eksiksiz kabul ölçütü henüz belirlenmemiş. |
| G24 | Üç servis; headless Humble/Fortress; en az iki bağımsız Nav2; birim→ROS→canlı kanıt; yeni robot config’den. | KISMİ: test Compose katmanları mevcut; kök ürün Compose’u yok. | 224 geçti/19 atlandı; tarihsel iki robot kanıtı. 3+ ölçek/1 saat dayanıklılık doğrulanmadı; süre öneridir. |

Test adları Ek A’daki dosyalara bağlanır. “MEVCUT” etiketi bütün hata yollarının doğrulandığı anlamına gelmez. Kabul tanımı onaylı kaynaklardan türetilmiştir; bu rapor yeni onay vermez.

<!-- pagebreak -->

# 5.1. Görev atama ve depo koordinasyonu

Gerkey ve Matarić’in taksonomisi, “hangi robot hangi görevi yapmalı?” sorusunu biçimsel sınıflara ayırarak görev atamanın yalnız deneysel bir yazılım tercihi olmadığını gösterir. İncelenen proje, her taşımanın tek robota verildiği ve robotun aynı anda tek etkin taşıma yaptığı merkezi, olay güdümlü bir düzene yakındır. Ancak bu sınıflama projenin küresel optimum bulduğunu göstermez; burada uygulanan kural uygunluk filtresi sonrasında yerel seçimdir. [1]

Korsah, Stentz ve Dias, görevler arası bağımlılık ve ortak kısıtların önemini vurgulayan iTax yaklaşımını sunar. Projedeki şarj kapasitesi, kaynak sahipliği ve kesilmez fazlar da kararların birbirinden bütünüyle bağımsız olmadığını gösterir. Bununla birlikte mevcut zamanlayıcı uzun ufuklu çok görevli optimizasyon yapmamaktadır. Onaylı politika, bu karmaşıklığı öngörülebilir kurallarla sınırlama tercihidir; optimum çözüm iddiası değildir. [2], [25]

Wurman, D’Andrea ve Mountz’ın depo koordinasyonu çalışması görev yönetimi ile çok araçlı fiziksel operasyonun çok daha büyük sistemlerde ele alındığını gösterir. Bu kaynak, problemin uygulama önemini destekler; projedeki iki robotlu deneyin yüzlerce araç ölçeğini temsil ettiğini göstermez. Ayrıca ticari depo düzeni ile burada kapsam dışı bırakılan otomatik palet ve trafik koordinasyonu aynı kabul sınırında değildir. [3], [22]

Ma ve arkadaşlarının çevrimiçi pickup-and-delivery çalışması, görev akışını çarpışmasız çok ajanlı yol bulmayla birlikte ele alır. Bu yaklaşım ile projenin bağımsız Nav2 yığınları arasında önemli bir fark vardır: görev ataması geçerli olsa bile ortak koridordaki hareketlerin birlikte çözüldüğü söylenemez. Bu raporda trafik problemi bir eksik MVP özelliği olarak yeniden dayatılmamış, sonuçların dış geçerlilik sınırı olarak kaydedilmiştir. [4]

## Sentez

Projenin güçlü sorusu “en iyi genel MRTA algoritması hangisidir?” değil, “bu sınırlı lojistik politikasının asenkron mesajlar ve fiziksel fazlar altında ihlal edilmediği nasıl gösterilir?” sorusudur. Bu odak hem uygulanabilirliği artırır hem de hangi tür bilimsel sonuçların henüz desteklenmediğini belirler.

Öncelik, atanabilir FIFO ve en kısa pickup mesafesi tanınan karar ilkeleridir. Bunları bir araya getirmek, tek başına yeni algoritma oluşturmaz. N=2 seçiminin katkısı da ancak kesme sıklığı, bekleme ve tamamlanma üzerindeki etkisi karşılaştırmalı olarak ölçülürse değerlendirilebilir. Bu ölçüm **ÖNERİ** olup onaylı politikayı değiştirmez.

<!-- pagebreak -->

# 5.2. Enerji, şarj ve dinamik çizelgeleme

Tomy ve arkadaşlarının çalışması şarj planlamasını belirsizlik altında çok amaçlı karar verme problemi olarak ele alır. Bu, yalnız bir doluluk eşiği kullanmanın görev fırsatlarıyla etkileşimi temsil etmekte sınırlı kalabileceğini gösterir. Projenin rota tabanlı enerji uygunluğu sabit eşikten daha görev bağımlı bir karar üretir; ancak öğrenilmiş görev geliş modeli veya belirsizlik optimizasyonu içermez. Yayın özetinden bu projeye nicel kazanım aktarılmamıştır. [8]

Bagchi, Nair ve Das’ın 2024 çalışması dinamik, dağıtık görev atamasında enerji tüketimi ve uyarlanabilir şarj eşiğini ele alır. Proje ise tek consumer ve merkezi sahiplik kullanmaktadır. Bu fark, bir üstünlük sıralaması değil farklı amaç ve karmaşıklık düzeyidir: dağıtık kararın hata modelleri ile merkezi deney platformunun hata modelleri aynı değildir. Çalışmanın tam deney protokolü bu taramada incelenememiştir. [7]

Chang ve arkadaşlarının 2026 çalışması öncelikli dinamik talepleri CBBA ve ACO bileşimiyle ele alır. Buradaki mobil robotlar araçlara şarj hizmeti verir; problem, depo taşıma robotlarının kendi bataryalarını doldurmasından farklıdır. Kaynak güncel çok amaçlı çizelgeleme örneği olarak kullanılmıştır; proje için doğrudan çözüm veya aynı kapsamda benchmark değildir. Yayıncı özeti ve DOI metadata doğrulanmış, tam metin erişiminde 429 hatası nedeniyle ayrıntılı yöntem denetimi yapılmamıştır. [9]

## Projedeki Wh modelinin yeri

`E_required = k × (L(current,pickup) + L(pickup,dropoff)) + k × L(dropoff,safe_charge) + E_margin`

`E_available = E_remaining − E_emergency`

Birimlerin Wh, m, Wh/m ve W olarak ayrılması, simülasyon ile karar mekanizması arasındaki sözleşmeyi açıklığa kavuşturur. Kaçış mesafesi ve marj iki kez eklenmez. Ancak yeterlilik eşitsizliği; uzun istasyon kuyruğu, bilinmeyen bekleme süresi veya kalibrasyon hatasına karşı sınırsız garanti sağlamaz. Bağımsız Battery Simulator ve kalibrasyon olmadan modelin fiziksel doğruluğu gösterilmiş sayılamaz. [22], [27], [31]

**ÖNERİ - araştırma değeri:** Mevcut politika korunarak tahmin edilen enerji ile simülasyonda tüketilen enerjinin karşılaştırılması; yükleme beklemesi, istasyon doluluğu ve rota uzamasının etkisinin ayrı raporlanması. Bu öneri bir kabul eşiği koymaz. A-DEC-03’teki kalibrasyon yöntemi de ayrı onay olmadan zorunlu deney tasarımı olarak sunulamaz.

<!-- pagebreak -->

# 5.3. Tutarlılık ve simülasyonla doğrulama

ROS 2; modüler düğümler, iletişim ve yaşam döngüsü için altyapıdır. Macenski ve arkadaşlarının mimari incelemesi bu rolü açıklar. Nav2’nin Marathon 2 çalışması ise davranış ağacı tabanlı navigasyonun önemini gösterir. Bu kaynaklar projenin teknoloji seçimiyle uyumludur; ROS 2 kullanmanın uygulama seviyesinde tek sahiplik veya fiziksel güvenlik kanıtı olduğunu söylemez. [5], [6]

ROS 2 action tasarımı goal, feedback, result ve cancel etkileşimlerini ayırır. Bu nedenle projede “iptal kabul edildi” bilgisinden “robot durdu ve yeni göreve hazır” sonucuna doğrudan geçmemek yerindedir. QoS reliability ve durability ayarları da ağ davranışını etkiler; işin yalnız bir kez fiziksel yürütülmesi için uygulama kimliği ve duplicate denetimi ayrıca gerekir. Humble QoS belgesi resmî GitHub kaynağından okunmuştur; web sayfası erişim engeli vermiştir. [17], [18]

Transactional Outbox örüntüsü, durum güncellemesi ve gönderilecek komutun aynı veritabanı işleminde saklanmasıyla çift yazım sorununu sınırlar; gönderici yinelenen mesaj üretebildiğinden alıcı idempotency’si gerekir. Projedeki yaklaşım bu bilinen örüntünün robot görevlerine uyarlanmasıdır. SQLite atomik commit mekanizması veritabanı sınırında anlamlıdır; fiziksel robotla dağıtık atomiklik sağlamaz. Bu ayrım, canlı restart sonrası otomatik devamın kapsam dışı tutulmasını açıklayan teknik bir gerekçedir. [19], [20], [26]

Gazebo Fortress fizik/sensör simülasyonu için uygun bir bağımlılıktır; buna rağmen simülasyon çalışması donanım, insan güvenliği veya üretim ortamı dayanıklılığına eşdeğer değildir. Bu projede birim testleri, ROS/DDS entegrasyonu ve canlı Nav2/Gazebo katmanlarının ayrı olması güçlü bir doğrulama yaklaşımıdır. Kanıtın katmanlar arasında abartılmaması gerekir. [21], [28]

## Öne çıkan doğrulama açığı

Başarılı test toplamı, gereksinim kapsam yüzdesi değildir. Örneğin consumer’ın gerçek epoch eksikliğini fallback ile kapatması, olumlu kimlik testleri geçerken varlığını sürdürebilir. Benzer biçimde doğrudan rezervasyon primitive’i ile consumer üzerinden korunan yol aynı güvenceyi vermez. Böylece raporun merkezi bulgusu, “testler yeşil” ile “sözleşme tüm girişlerde korunuyor” önermelerinin ayrı olduğudur. [29], [31]

**ÖNERİ:** Kabul ölçütünü olay izi ve değişmez bazında değerlendirmek; gecikmiş sonuç, duplicate komut, faz yarışı ve oturum değişimini bağımsız hata enjeksiyonlarıyla sınamak. Bu, yeni mimari gereksinim değil mevcut sözleşmeleri sınayacak araştırma yönüdür.

<!-- pagebreak -->

# 6.1. Açık kaynak karşılaştırması: kapsam ve politika

Bu matris ürün eşdeğerliği iddiası değildir. Open-RMF birlikte çalışan çok sayıda paketten oluşan filo çerçevesi; openTCS AGV kontrol çerçevesidir. Proje ise bu bileşenlerin tümüne alternatif olacak olgunlukta olmayan, belirli politikalara odaklı uygulamadır. İncelenen commit’ler tarama ekinde sabitlenmiştir. [10], [11], [12], [13], [14], [15]

| Ölçüt | Bu proje | Open-RMF | openTCS |
|---|---|---|---|
| Amaç / kapsam | İki robotlu taşıma, açık kesme ve sahiplik politikaları; trafik çözümü kapsam dışı [22], [25]. | Filo ve bina altyapısı koordinasyonu; trafik ve görev paketleri [10]. | Heterojen AGV yönlendirme, dispatch ve kaynak planlama çerçevesi [14], [15]. |
| Lisans / kod | Yerel LICENSE Apache-2.0; kaynak bu depoda [31]. | İncelenen task, ROS ve web depolarında Apache-2.0 [11], [12], [13]. | Ana dağıtım MIT; üçüncü taraf varlıkların ayrı lisansları var [14]. |
| ROS 2 / simülasyon | Humble/Fortress test katmanları; nihai ürün dağıtımı eksik [28], [31]. | ROS 2 ve demo ekosistemi; main sürümü Humble kabulü değildir [10], [13]. | Çekirdek ROS 2’ye özgü değil; sanal araç/loopback var. Gazebo entegrasyonu incelenmedi [14], [15]. |
| Görev atama | Atanabilir FIFO, uygun IDLE, Nav2 pickup mesafesi [25], [31]. | TaskPlanner maliyet/strateji, greedy veya A* seçeneği [11]. | Dispatcher ve değiştirilebilir yönlendirme/planlama bileşenleri [14], [15]. |
| Öncelik / kesme | HIGH, faz/yük kapısı, N=2; uçların bazıları kısmi [25], [31]. | BinaryPriority örneği; interrupt/resume/cancel API. Aynı N=2 sözleşmesi belgelenmemiş [11], [12]. | Emir seçimi ve geri çekme altyapısı; aynı HIGH/N=2 politikası belgelenmemiş [15]. |
| Enerji / şarj | Wh uygunluğu mevcut; tüketim ve sıra orkestrasyonu planlanan [22], [31]. | Batarya kısıtları, enerji modelleri ve şarj görevleri [11]. | Boş araç için otomatik şarj konumu seçimi belgeli; aynı Wh eşitsizliği belgelenmemiş [14], [15]. |

**Terimler:** “Yok”, incelenen ürün ağacında bulunmayan bileşen için kullanılır. “Belgelenmemiş”, okunan kaynakta özelliğin aynı sözleşmeyle tanımlanmadığını söyler; evrensel yokluk iddiası değildir. “İncelenmedi”, değerlendirme yapılmadığını; “kapsam dışı” ürün sorumluluğuna dahil olmadığını belirtir.

Open-RMF API’sinde kesme ve iptal yeteneklerinin bulunması, proje politikasının olduğu gibi mevcut olduğunu göstermez. Tersine, aynı N=2 kuralının incelenen belgelerde bulunmaması da bunun yeni bir bilimsel fikir olduğunu kanıtlamaz. Karşılaştırma düzeyi “mekanizma var mı?” ve “aynı politika sözleşmesi var mı?” şeklinde ayrılmıştır.

<!-- pagebreak -->

# 6.2. Açık kaynak karşılaştırması: işletim ve kanıt

| Ölçüt | Bu proje | Open-RMF | openTCS |
|---|---|---|---|
| Kaynak rezervasyonu | Tek şarj/park sahibi; fiziksel ayrılma kapısı kısmi. Küresel trafik kapsam dışı [25], [29], [31]. | Trafik koordinasyonu; RobotUpdateHandle’da park rezervasyonu seçeneği [10], [12]. | Point/path/location ve block kaynakları; araç tahsisiyle trafik yönetimi [15]. |
| Hata kurtarma | FAILED/ERROR, manuel ClearRobotError; iletişim kaybı hata değildir; ürün reset akışı eksik [25], [31]. | Issue, cancel, kill, reassign API’leri; aynı konservatif reset politikası belgelenmemiş [12]. | Emir ve araç işletim akışları mevcut; aynı epoch/session güvenlik sözleşmesi belgelenmemiş [15]. |
| Kalıcılık | SQLite Outbox ve atomik olay; dolu DB ile otomatik devam yok [26], [31]. | Web API veritabanı desteği var; robot komutları için aynı Outbox/atomiklik ve restart garantisi incelenmedi [13]. | Model saklama/işletim çerçevesi; eşdeğer transaction Outbox ve çökme devam garantisi incelenmedi [15]. |
| Yapılandırma | Tek fleet.yaml hedefi; C1 mevcut, Apply eksik, builder fallback açığı [27], [31]. | Filo/adapter parametreleri ve web yapılandırması [10], [12], [13]. | Tesis modeli, sürücüler, kernel ve istemci yapılandırması [14], [15]. |
| Kullanıcı arayüzü | React/Konva ve API planlanan; ürün paneli yok [22], [31]. | rmf-web API ve dashboard paketleri mevcut [13]. | Model Editor ve Operations Desk mevcut [15]. |
| Test / doğrulama | Birim, ROS/DDS, Gazebo kayıtları; güncel host 224/19; kanıt sınırları açık [28], [29], [30], [31]. | TaskPlanner test kaynağı ve web test altyapısı incelendi; bu raporda çalıştırılmadı [11], [13]. | Java test ağacı ve sanal araç yaklaşımı mevcut; bu raporda çalıştırılmadı [14], [15]. |

## Karşılaştırmanın sonucu

Benzer ve bazı alanlarda daha kapsamlı açık kaynak çözümler bulunmaktadır. Open-RMF’nin trafik ve bina entegrasyonu, openTCS’nin tesis/araç kontrolü ve mevcut arayüzleri projenin hedeflerinden farklı ama doğrudan ilgili yeteneklerdir. Bu özellikleri “rakiplerde yok” şeklinde göstermenin kanıt temeli yoktur.

Aynı şekilde kaynak kodda test bulunması, karşılaştırılan projelerin bu rapor koşullarında başarıyla sınandığı anlamına gelmez. Kurulum, performans, aynı görev kümesi, aynı harita ve aynı arıza senaryolarıyla karşılaştırmalı çalışma yapılmamıştır. Bu nedenle tablo kalite puanı veya ürün sıralaması değildir.

Özel geliştirme, onaylı dar politikayı anlaşılır ve denetlenebilir biçimde incelemek için gerekçelendirilebilir. Gerçek işletmede heterojen robotlar, çok katlı bina altyapısı veya ortak trafik alanları gerekiyorsa mevcut çerçeveleri uyarlamak daha güçlü bir başlangıç adayıdır. Bu bir **ÖNERİ** değerlendirmesidir; proje mimarisini değiştirmez.

<!-- pagebreak -->

# 6.3. Altyapı ile filo uygulamasının ayrılması

Nav2 veya ROS 2’de bir filo özelliğinin bulunmaması, bu bileşenlerin eksik ürünler olduğu anlamına gelmez. Bunlar karşılaştırmanın farklı katmanlarıdır. Aşağıdaki hücrelerde “kapsam dışı” bileşenin rolünü ifade eder; ekosistemde hiçbir paket bulunmadığını ileri sürmez.

| Ölçüt | Nav2: navigasyon bileşeni | ROS 2: iletişim/çalışma altyapısı |
|---|---|---|
| Amaç | Yol planlama, kontrol ve navigasyon davranışı [6], [16]. | Düğümler, mesajlar, servisler ve action iletişimi [5], [17]. |
| Lisans / erişim | İncelenen navigation2 deposu Apache-2.0; açık kaynak [16]. | Paket bazında lisans; tek bir ürün lisansı varsayılmaz. İncelenen belgeler açık erişim [5], [18]. |
| ROS 2 / simülasyon | ROS 2 yerel; proje bunu Gazebo ile kullanır [6], [16], [28]. | Simülasyonla kullanılabilir altyapı; kendi başına fizik motoru değildir [5], [21]. |
| Görev atama | Filo iş seçimi kapsam dışı; ComputePathToPose rota sağlar [16]. | İşletme seviyesinde filo ataması kapsam dışı [5], [17]. |
| Öncelik / preemption | Action iptali ve navigasyon davranışı; HIGH/FIFO/N=2 filo politikası kapsam dışı [6], [16], [17]. | Cancel/result protokolü sağlar; fiziksel duruş politikası uygulamaya aittir [17]. |
| Enerji / şarj | Bu incelemede Humble iki action IDL’sinin kapsamında değil; diğer eklentiler incelenmedi [16]. | Batarya yönetimi politikası kapsam dışı [5], [18]. |
| Kaynak rezervasyonu | Park/şarj sahipliği ve filo trafik rezervasyonu incelenen API kapsamı dışında [16]. | İşletme kaynağı rezervasyonu kapsam dışı [5], [17]. |
| Hata / kalıcılık | Navigasyon sonucu ve recovery; görev Outbox’ı incelenen kapsam dışında [6], [16]. | QoS ve action sonucu, uygulama transaction’ı veya restart uzlaştırması değildir [17], [18]. |
| Yapılandırma | Planner ve navigator arayüzleri; robot/harita bağlamı [6], [16]. | Namespace ve iletişim ayarları; tek fleet.yaml zorunluluğu yok [17], [18]. |
| Arayüz | Tam filo web paneli incelenen bileşenin kapsamı dışında [6], [16]. | Filo operatör paneli kapsam dışı [5]. |
| Doğrulama | Marathon 2 yayınında deney; bu taramada Nav2 yeniden çalıştırılmadı [6]. | Mimari vaka çalışmaları; bu projenin davranış testi değildir [5]. |

Bu ayrım projenin rolünü netleştirir: Nav2’ye alternatif yol planlayıcı geliştirmek yerine, mevcut navigasyonu iş yaşam döngüsü, sahiplik ve operatör görünümüyle birleştirmek. Bu entegrasyon anlamlıdır; tek başına algoritmik yenilik değildir.

<!-- pagebreak -->

# 7. Boşluk ve özgünlük değerlendirmesi

| Katkı düzeyi | Desteklenebilen değerlendirme | Eksik kanıt |
|---|---|---|
| Algoritmik / bilimsel | Öncelik, FIFO, mesafe seçimi, Wh bütçesi ve Outbox bilinen yaklaşımlardır [1], [2], [7], [19]. | Yeni algoritma, ispat, üstünlük veya genellenebilir deney sonucu yok. |
| Mimari / entegrasyon | FM–Executor–Nav2 sınırı ve tek tüketicili kalıcı komut akışı somut uygulanmıştır [24], [25], [26], [31]. | Bütün hata girişlerinde sözleşme uyumu; C4/C5 ve nihai dağıtım eksik. |
| Güvenlik sözleşmeleri | Faz/yük kilidi, terminal iptal, kimlik, sıra/oturum ve fiziksel kaynak kapılarının birlikte izlenmesi değerli [25], [31]. | Mevcut fallback ve primitive açıkları nedeniyle bütünleşik güvence tamamlanmamış. |
| Tekrarlanabilir doğrulama | Katmanlı test kodu, komut kayıtları ve tarihsel koşu belgeleri mevcut [28]. | Ortak benchmark, hata kapsama analizi, tekrarlı uzun koşu ve tam C4 deneyleri eksik. |
| Eğitim / araştırma | Politikaların karar–kod–test zinciriyle açıklanabildiği sınırlı platform [23], [24], [25], [26], [27], [28], [29], [30], [31]. | Kullanıcı çalışması veya öğrenme başarımı ölçümü yok; değer gerekçeli potansiyel. |

**Gerçek farklılaşma adayı**, yeni bir filo yönetimi kategorisi yaratmak değil, belirli politika birleşiminin açık ve denetlenebilir gerçekleştirimidir. Örneğin N=2 korumasını, eski sonuçların ayıklanmasını ve fiziksel kaynak sahipliğini aynı senaryo kayıtlarında takip etmek araştırma için faydalı olabilir. Bu birleşimin incelenen rakiplerde tam aynı biçimde belgelenmemesi, dünyada ilk olduğu anlamına gelmez.

Open-RMF’de batarya-aware görev planlama, interrupt/resume ve park rezervasyonu; openTCS’de otomatik park/şarj ve kaynak kontrolü bulunması, projenin birçok hedefinin öncülleri olduğunu gösterir. Burada potansiyel katkı “bu işlevleri ilk kez sağlamak” değil, seçilmiş davranışları sınırları belli bir uygulamada öğretilebilir ve sınanabilir hâle getirmektir. [11], [12], [13], [14], [15]

Tarama, evrensel yokluk veya kesin doğrudan eşdeğer bulunamadığı sonucunu destekleyecek genişlikte değildir. Bu nedenle “açık kaynak böyle bir proje yoktur” ve “dünyada ilk” ifadeleri kullanılmamıştır. Tam eşdeğerlik kararı için aynı politika sözleşmelerini rakip kurulumlarda çalıştırmak gerekir.

**ÖNERİ - yayınlanabilir katkıya dönüşüm:** belirli bir hipotez seçmek; örneğin kimlik ve oturum korumalarının gecikmiş/tekrarlı mesajlarda yanlış sahiplik geçişini nasıl engellediğini kontrollü hata enjeksiyonuyla göstermek. Başarı ölçütü yalnız tamamlanan görev sayısı değil, ihlal edilen değişmez ve belirsizlikte bloke edilen atamadır. Bu öneri yeni ürün gereksinimi değildir.

<!-- pagebreak -->

# 8. Teknik uygulanabilirlik ve riskler

Problem–çözüm uyumu, merkezi görev seçiminin robot yerel yürütümünden ayrılmasına dayanır. Bu ayrım, iş politikasını Nav2’den bağımsız sınamayı mümkün kılar. Humble/Fortress için tarihsel entegrasyon ve güncel saf Python testlerinin geçmesi teknoloji zincirinin en azından dar senaryolarda kullanılabildiğini destekler. Buna karşılık ürünleştirme karmaşıklığı, yeni ekran geliştirmekten çok bütün durum geçişlerinin uçlarda aynı sözleşmeyi korumasındadır. [24], [25], [26], [27], [28], [29], [30], [31]

| Risk / bağımlılık | Etki | Gerekçeli sonraki çalışma (ÖNERİ) |
|---|---|---|
| Gerçek completed_epoch fallback’i | Eksik kanıtla sahiplik kapatma riski. | Eksik terminal alanı olumsuz testle görünür kılma; ayrı uygulama görevinde düzeltme [25], [31]. |
| Config–enerji bağlantısı | YAML’da değişen güvenlik marjının runtime’da uygulanmaması. | Politika değerlerinin uçtan uca akışını sınama; birden çok istasyon senaryosu [27], [31]. |
| Fiziksel kaynak primitive’leri | Doğrudan çağrı consumer korumasını aşabilir. | Normal/yanlış çağrı yollarını ve işgal belirsizliğini ayrı test etme [29], [31]. |
| Batarya ve şarj eksikliği | Görev bitiminde enerji/istasyon zinciri kabul edilemez. | Onaylı C4 sırasına göre simülasyon ve dock koşullarını doğrulama [22]. |
| Ürün reset akışı eksikliği | Test harness dışı güvenli başlangıç belirsizliği. | Fiziksel reset kanıtının operasyonel prosedürünü ayrıca netleştirme [25]. |
| Tek consumer / sıralı Outbox | Bir gönderim hatası sonraki komutları geciktirebilir. | Kuyruk bekleme ve hata yayılımını ölçme; eşik uydurmama [26]. |
| Web/Apply eksikliği | Kullanıcıdan göreve uçtan uca iş akışı yok. | C5 kabulünü C4 sonrası gerçek ROS verisiyle yapma [22], [24]. |
| Ölçek / trafik sınırı | İki robot sonucu yoğun depo veya dar koridora aktarılamaz. | Sınırı koruma; genişleme istenirse ayrı karar/deney [22], [28]. |

## Özel geliştirme mi, uyarlama mı?

Özel geliştirme, öğretilebilirlik ve onaylı davranışların doğrudan kontrolü için savunulabilir. Mevcut açık kaynak çerçeveyi uyarlamak ise hazır trafik, arayüz ve heterojen filo yeteneklerini yeniden geliştirme yükünü azaltabilecek bir seçenektir. Ancak bu rapor maliyet veya geliştirme süresi ölçmediğinden hangi seçeneğin daha ucuz olduğunu söylemez. Projeye devam kararı, dar araştırma amacını korumaya ve açık boşlukları kapatmaya bağlı olumlu bir değerlendirmedir.

<!-- pagebreak -->

# 9. Sonuç ve doğrulama gündemi

**Sonuç:** ROS 2 Fleet Manager projesi, açık politika ve güvenlik sözleşmelerinin kontrollü simülasyonda incelenmesini amaçlayan bir araştırma/eğitim uygulaması olarak mantıklı, uygulanabilir ve geliştirmeye değerdir. Bu sonuç; mevcut C1–C3 kodu, yeniden geçen host testleri, tarihsel ROS/Nav2 entegrasyon kanıtı ve görev–yürütüm sorumluluklarının açık ayrımıyla desteklenmektedir. [24], [25], [26], [27], [28], [29], [30], [31]

Olumlu sonuç koşulludur. C4 ve C5 tamamlanmamıştır; test edilmiş parçalar henüz bütün hedef ürün değildir. Tespit edilen epoch, config–enerji, kaynak serbest bırakma ve runtime doğrulama sınırları giderilmeden güvenlik sözleşmelerinin eksiksiz uygulandığı söylenemez. İki robot ve kısa koşular ölçeklenebilirlik, endüstriyel emniyet veya performans üstünlüğü garantisi vermez.

**Bilimsel yenilik değerlendirmesi:** mevcut kanıtla yeni bir atama algoritması veya rakiplerden daha iyi sonuç iddiası desteklenmemektedir. Open-RMF ve openTCS benzer, bazı alanlarda daha geniş yeteneklere sahiptir. Buna rağmen bu proje, belirli davranış birleşiminin izlenebilir uygulaması ve hata enjeksiyonlu doğrulaması bakımından katkı potansiyeli taşır. Potansiyel, tamamlanmış bilimsel katkı olarak sunulmamalıdır. [1], [2], [10], [11], [14], [15], [16], [17], [18], [19], [20]

## Öncelikli doğrulama gündemi - ÖNERİ

1. Onaylı güvenlik değişmezleriyle kod arasındaki farklar için olumsuz test kanıtı üretmek: eksik gerçek epoch, yanlış kaynak sahibi, oturum değişiminde bırakma ve geç sonuç.

2. C4 kapsamında fiziksel simülasyon tüketimi, şarj kabulü, kuyruk ve ayrılmayı gerçek /clock ve odometriyle bağlamak; kalibrasyonsuz katsayıları açık tutmak.

3. C5 kapsamında görev girişi, ROS durum görünümü, hata bildirimi ve kontrollü Apply akışını ayrı kabul etmek; replay ve başarısız Apply ayrıntılarını karar verilmeden uygulamaya dönüştürmemek.

4. Katkı iddiasına yönelik eşlenik senaryolar seçmek; aynı harita, görev akışı ve hata enjeksiyonu altında davranış değişmezlerini raporlamak. Rakip kıyaslaması yapılırsa sürüm ve yapılandırmalar sabitlenmelidir.

Bu gündem C1→C2→C3→C4→C5 bağımlılığını değiştirmez. Bir saat dayanıklılık, üçüncü robot CPU limiti ve kalibrasyon deneme sayıları ayrı onay olmadığı sürece öneri olarak kalır.

## Açık kalan bilgi

Saha görev dağılımı, operatör kabulü, kalibre edilmiş enerji katsayıları, genel performans hedefleri ve gerçek robot güvenliği bu raporda belirlenmemiştir. `stations` yerleşimiyle ilgili belgesel onay boşluğu korunmuştur. Rapor, bu konuları sessizce karara bağlamaz; sonraki uygulama veya araştırmanın açık sınırları olarak kaydeder.

<!-- pagebreak -->

# Kaynakça I - Akademik çalışmalar

Numaralı atıflar tıklanabilirdir. Dış kaynak erişim tarihi 27 Ekim 2026’dır. “2026 erişimi”, yayın yılı iddiası değildir. Ayrıntılı erişim ve commit kaydı tarama ekindedir.

**[1]** Brian P. Gerkey; Maja J. Matarić (2004). A Formal Analysis and Taxonomy of Task Allocation in Multi-Robot Systems. IJRR 23(9), 939–954. DOI: 10.1177/0278364904045564.

**[2]** G. Ayorkor Korsah; Anthony Stentz; M. Bernardine Dias (2013). A comprehensive taxonomy for multi-robot task allocation. IJRR 32(12), 1495–1512. DOI: 10.1177/0278364913496484.

**[3]** Peter R. Wurman; Raffaello D’Andrea; Mick Mountz (2008). Coordinating Hundreds of Cooperative, Autonomous Vehicles in Warehouses. AI Magazine 29(1), 9–20. DOI: 10.1609/aimag.v29i1.2082. 2007 konferans metni ile 2008 dergi kaydı ayrılmıştır.

**[4]** Hang Ma; Jiaoyang Li; T. K. Satish Kumar; Sven Koenig (2017). Lifelong Multi-Agent Path Finding for Online Pickup and Delivery Tasks. AAMAS 2017. DOI bu taramada doğrulanmadı; yazar arşivi kullanıldı.

**[5]** Steve Macenski; Tully Foote; Brian Gerkey; Chris Lalancette; William Woodall (2022). Robot Operating System 2: Design, Architecture, and Uses In The Wild. Science Robotics 7(66). DOI: 10.1126/scirobotics.abm6074. arXiv:2211.07752v1.

**[6]** Steve Macenski; Francisco Martín; Ruffin White; Jonatan Ginés Clavero (2020). The Marathon 2: A Navigation System. IROS 2020. DOI: 10.1109/IROS45743.2020.9341207. arXiv:2003.00368v2.

**[7]** Menaxi J. Bagchi; Shivashankar B. Nair; Pradip K. Das (2024). On a dynamic and decentralized energy-aware technique for multi-robot task allocation. Robotics and Autonomous Systems. DOI: 10.1016/j.robot.2024.104762. İnceleme: özet/metadata.

**[8]** Milan Tomy; Bruno Lacerda; Nick Hawes; Jeremy L. Wyatt (2020). Battery charge scheduling in long-life autonomous mobile robots via multi-objective decision making under uncertainty. Robotics and Autonomous Systems 133, 103629. DOI: 10.1016/j.robot.2020.103629. İnceleme: özet/metadata.

**[9]** Meiyu Chang; Zhaoyu Ku; Xuanyu Xing; Tianhao Wang; Huajun Dong (2026). ICBBA-ACO-Based Multi-Robot Task Allocation for Smart Charging Stations. Machines 14(8), 953. DOI: 10.3390/machines14080953. İnceleme: yayıncı arama metni ve Crossref; tam metin erişimi sınırlı.

<!-- pagebreak -->

# Kaynakça II - Açık kaynak ve altyapı

Numaralı atıflar tıklanabilirdir. Dış kaynak erişim tarihi 27 Ekim 2026’dır. “2026 erişimi”, yayın yılı iddiası değildir. Ayrıntılı erişim ve commit kaydı tarama ekindedir.

**[10]** Open-RMF geliştiricileri (2026 erişimi). RMF root repository, README; sistem kapsamı ve paket ekosistemi. Commit 146c053b61bc. DOI uygulanamaz.

**[11]** Open-RMF geliştiricileri (2026 erişimi). rmf_task: TaskPlanner.hpp, test_TaskPlanner.cpp ve LICENSE.md. Commit 79a276d44f69. Planlama API ve test kaynağı. DOI uygulanamaz.

**[12]** Open-RMF geliştiricileri (2026 erişimi). rmf_ros2: RobotUpdateHandle.hpp ve LICENSE.md. Commit b892a9a4b80e. Kesme, iptal, durum ve park rezervasyonu API. DOI uygulanamaz.

**[13]** Open-RMF geliştiricileri (2026 erişimi). rmf-web: README, API server README ve lisans. Commit 7aa50a43ae49. Arayüz/veritabanı/test kapsamı. DOI uygulanamaz.

**[14]** openTCS geliştiricileri / Fraunhofer IML (2026 erişimi). openTCS kaynak ağacı, README.adoc, users-guide-02_howtos.adoc ve dağıtım lisansı. Commit 742b0e6df9cc. DOI uygulanamaz.

**[15]** The openTCS developers. openTCS User’s Guide, sürüm 6.7.0. Çevrimiçi indekslenmiş resmî belge: kaynak modeli, scheduler/dispatcher, Operations Desk, park/şarj. Erişimde timeout nedeniyle doğrudan içerik kapsamı sınırlı; main kaynak ağacıyla aynı sürüm sayılmadı. DOI uygulanamaz.

**[16]** Nav2 geliştiricileri (2026 erişimi). navigation2, humble dalı: ComputePathToPose.action, NavigateToPose.action, README ve LICENSE. Commit 3c3db59d6969. DOI uygulanamaz; akademik karşılığı [6].

**[17]** Geoffrey Biggs; Jacob Perron; Shane Loretz (2019; güncelleme 2020). Actions. ROS 2 Design. Goal/cancel/result protokolü. DOI uygulanamaz.

**[18]** ROS 2 geliştiricileri (2026 erişimi). Quality of Service settings, Humble belge kaynağı. Commit c32643f08f68. Web erişim engeli nedeniyle resmî GitHub RST kullanıldı. DOI uygulanamaz.

**[19]** Chris Richardson (tarih belirtilmiyor; 2026 erişimi). Pattern: Transactional outbox. microservices.io. Örüntü tanımı ve yinelenen teslim sınırı; hakemli robotik deney değildir. DOI uygulanamaz.

**[20]** SQLite geliştiricileri (tarih belirtilmiyor; 2026 erişimi). Atomic Commit in SQLite. Resmî teknik açıklama; veritabanı atomikliği. DOI uygulanamaz.

**[21]** Gazebo geliştiricileri (2026 erişimi). Gazebo Fortress Documentation. Simülasyon bağımlılığı ve belgeler. DOI uygulanamaz.

<!-- pagebreak -->

# Kaynakça III - Proje kaynakları

Numaralı atıflar tıklanabilirdir. Dış kaynak erişim tarihi 27 Ekim 2026’dır. “2026 erişimi”, yayın yılı iddiası değildir. Ayrıntılı erişim ve commit kaydı tarama ekindedir.

**[22]** Proje (23 Ekim 2026). Nihai Mimari Kararlar. DOC-ARCH-2026-10-23-FINAL v1.0, 13 sayfa; özellikle bölümler 3–11, 13–16. Sonraki C2/C3 kararlarıyla birlikte okunur.

**[23]** Proje (22 Ekim 2026). Revize Karar 08 v1.0, 29 sayfa. Özellikle s. 8, 12–19, 23–29. Onaylı politika ile öneri ve sonraki değişiklikler ayrıdır.

**[24]** Proje (22 Ekim 2026). Onaylı v2.3 mimari geçiş kaydı. Görev yürütücüsü, durum otoritesi ve kontrollü Apply sınırı.

**[25]** Proje (24 Ekim 2026). C2, C3, C3.3, C3.3.1, C3.3.2 ve C3.3.3 kararları. Karar dizinindeki altı kayıt; özellikle C3-DEC-01–04 ve C3.3.2-DEC-01–07.

**[26]** Proje (24 Ekim 2026). C3.2 SQLite Outbox ve Tek Consumer. Transaction, retry, senaryo reset sözleşmesi.

**[27]** Proje. C1 Konfigürasyon Altyapısı; fleet.yaml alan ve birimleri, şema ve doğrulama.

**[28]** Proje (23–26 Ekim 2026). Doğrulama dizini; DDS, A/B/AMCL, C2 ve C3 kayıtları. Sayılar kendi tarih ve kapsamlarına aittir.

**[29]** Proje (26 Ekim 2026). Depo düzeni ve doğrulama raporu. Kaynak/kod farkları ve tarihsel kanıt sınırları. 27 Ekim’de seçili bulgular koddan yeniden kontrol edildi.

**[30]** Proje (26 Ekim 2026). Mimari ve algoritma diyagramları: 18 Mermaid kaynağı ve SVG; IMPLEMENTED/PARTIAL/PLANNED etiketleri.

**[31]** Proje (27 Ekim 2026 incelemesi). Güncel kaynak kod, IDL, config ve test ağacı. HEAD 63b8075456d56e49e8899ff26545da8e6b4ae86f. Dosya/test eşlemesi Ek A’da; komut ve kontrol kayıtları tarama ekinde.

<!-- pagebreak -->

# Ek A. Gereksinim–kaynak–test izlenebilirliği

Aşağıdaki dosyalar depo köküne göre verilmiştir. G01–G24 tabloları açıklama, gerekçe, onay, kabul ve durum bilgilerini taşır; bu ek test giriş noktalarını tekilleştirir. Test dosyasının varlığı bütün gereksinimin kabulü değildir. Host koşusunda ROS bağımlı testler atlanmıştır.

| ID | Kaynak | Kod / test giriş noktası |
|---|---|---|
| G01–G04 | [23], [25] | [Domain testleri](../../tests/test_fleet_manager_domain.py); task_queue.py, scheduler.py, fleet_manager_core.py |
| G05 | [22], [24], [25] | [Executor yaşam döngüsü](../../tests/test_executor_lifecycle_integration.py); [state_machine](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/state_machine.py) |
| G06 | [24], [25] | [Outbox testleri](../../tests/test_fleet_manager_outbox.py); [hata temizleme istemcisi testi](../../tests/test_clear_robot_error_client.py) |
| G07 | [25] | [ROS güvenlik testleri](../../tests/test_executor_safety_ros2.py); [node](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py) |
| G08 | [25] | [event_loop](../../backend/fleet_manager/event_loop.py); [action client testleri](../../tests/test_ros2_action_client.py) |
| G09 | [25] | [status testleri](../../tests/test_ros2_status_subscriber.py); [safety testleri](../../tests/test_executor_safety.py) |
| G10 | [25], [26] | [Outbox testleri](../../tests/test_fleet_manager_outbox.py); [store](../../backend/fleet_manager/persistence/store.py) |
| G11 | [25], [26] | [hold testi](../../tests/test_task_review_holds.py); [sender testleri](../../tests/test_ros2_outbox_sender.py) |
| G12 | [25], [26] | [Outbox testleri](../../tests/test_fleet_manager_outbox.py); [route testleri](../../tests/test_ros2_route_resolver.py) |
| G13 | [22], [25], [27] | [energy](../../backend/fleet_manager/domain/energy.py); [scheduler](../../backend/fleet_manager/domain/scheduler.py) |
| G14–G15 | [22], [23], [27] | Ürün kabul testi yok; [mock feeder](../../docker/simulation-c3-3-3/mock_battery_feeder.py) yalnız test girdisi. |
| G16 | [25] | [reservations](../../backend/fleet_manager/domain/reservations.py); [domain testleri](../../tests/test_fleet_manager_domain.py) |
| G17–G18 | [22], [23], [25] | Tam lojistik kabul testi yok; [builder](../../backend/fleet_manager/builder.py), Executor durum yardımcıları. |
| G19 | [25] | [Executor testleri](../../tests/test_executor_state_machine.py); [C2.3 kaydı](../validation/c2/c2-3-validation-2026-10-24.md) |
| G20 | [27] | [config testleri](../../tests/test_config.py); [builder testleri](../../tests/test_fleet_builder.py) |
| G21 | [25], [27] | [IDL](../../interfaces/fleet_interfaces/); [iki robot config testleri](../../tests/test_c3_3_3_config.py) |
| G22–G23 | [22], [24] | Ürün uygulaması/kabul testi yok; [panel ve Apply diyagram kataloğu](../diagrams/README.md). |
| G24 | [22], [25], [28] | [Compose kılavuzu](../../docker/compose/README.md); [C3.3.3 çalıştırıcısı](../../docker/simulation-c3-3-3/check.py) |

**Belge denetimi:** 24 gereksinim kaydı; 21 dış kaynak ve 10 proje kaynak grubu. Kaynak grupları, yayın sayısı olarak sayılmamıştır. Ayrı [tarama ve doğrulama eki](gereksinim-literatur-ozgunluk-tarama-eki-2026-10-27.md), sorgu kaydını ve bu rapor için çalıştırılan kontrolleri içerir.

[1]: https://journals.sagepub.com/doi/pdf/10.1177/0278364904045564
[2]: https://journals.sagepub.com/doi/10.1177/0278364913496484
[3]: https://doi.org/10.1609/aimag.v29i1.2082
[4]: https://jiaoyangli.me/files/2017-AAMAS.pdf
[5]: https://arxiv.org/abs/2211.07752
[6]: https://arxiv.org/abs/2003.00368
[7]: https://www.sciencedirect.com/science/article/abs/pii/S0921889024001465
[8]: https://doi.org/10.1016/j.robot.2020.103629
[9]: https://www.mdpi.com/2075-1702/14/8/953
[10]: https://github.com/open-rmf/rmf/tree/146c053b61bc6d8db77ed37f6bb6a4a7d448f12f
[11]: https://github.com/open-rmf/rmf_task/tree/79a276d44f69be6639bdf4e03b1d39536268d63c
[12]: https://github.com/open-rmf/rmf_ros2/blob/b892a9a4b80e3abf7d4616b21dd57cfe98a31749/rmf_fleet_adapter/include/rmf_fleet_adapter/agv/RobotUpdateHandle.hpp
[13]: https://github.com/open-rmf/rmf-web/tree/7aa50a43ae4968dc8d8084b2505616a6a278198a
[14]: https://github.com/openTCS/opentcs/tree/742b0e6df9ccbabc660e585a85e55d585c0642fc
[15]: https://www.opentcs.org/docs/6/user/opentcs-users-guide.html
[16]: https://github.com/ros-navigation/navigation2/tree/3c3db59d6969d8ecee8e68468693d006397f4a0c
[17]: https://design.ros2.org/articles/actions.html
[18]: https://github.com/ros2/ros2_documentation/blob/c32643f08f68eb3cddf8955d91494157e4afac22/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst
[19]: https://microservices.io/patterns/data/transactional-outbox.html
[20]: https://sqlite.org/atomiccommit.html
[21]: https://gazebosim.org/docs/fortress/
[22]: ../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.pdf
[23]: ../ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf
[24]: ../architecture/architecture-v2.3-transition.md
[25]: ../decisions/README.md
[26]: ../design/c3-2-sqlite-outbox.md
[27]: ../configuration-c1.md
[28]: ../validation/README.md
[29]: ../validation/organization/organization-validation-2026-10-26.md
[30]: ../diagrams/README.md
[31]: ../../backend/fleet_manager/
