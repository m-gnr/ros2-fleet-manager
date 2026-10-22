# Kalıcı proje bağlamı

Son güncelleme: 22 Ekim 2026. Kullanıcı, Karar 08 ve gönderdiği notların unutulmamasını açıkça istedi. Bu kayıt kaynakların yerine geçen tam bir mimari şartname değildir; ilgili ayrıntılar kaynak PDF'den doğrulanmalıdır.

## Kaynaklar ve öncelik

- Öncelik zinciri: kullanıcının sonraki açık talimatları → konuya ilişkin onaylı kararlar ve [onaylı v2.3 geçiş kaydı](architecture-v2.3-transition.md) → Revize Karar 08'in ilgili hükümleri → çelişmediği ölçüde eski v2.x belgeleri/README/notlar. Onaylanmış politika ile teknik öneri ayrımı korunur.
- Eski v2.x taşıma akışı bu konuda geçersizdir: Fleet Manager'ın doğrudan NavigateToPose gönderdiği akış yerine [v2.3 geçiş kaydındaki](architecture-v2.3-transition.md) Fleet Manager → ExecuteTask → robot yürütücüsü → Nav2 akışı esas alınır.
- Kullanıcı 22 Ekim 2026 tarihinde v2.3 geçiş kaydını onayladı; Docker yerleşimini onaylamadı. Açık hata yolları ve Docker/Apply kararları kayıt içinde listelenir. Docker onayı DDS mesaj alma testi kanıtıyla ayrı bir kayıtta ele alınacaktır.
- Kişisel notların korunması kullanıcının açık talimatıdır. Burada “Revize Karar 08” adıyla anılan PDF mimari referanstır; koruma talimatının kaynağıyla aynı şey olduğu varsayılmaz.

- Depo içindeki güncel PDF: `docs/ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf`. [v2.3 geçiş kaydı](architecture-v2.3-transition.md), eski doğrudan Nav2 taşıma akışının yerine ExecuteTask/yürütücü yönünü ve henüz doğrulanmamış Docker/Apply noktalarını açıklar. Bu kayıt bütün belge setinin yeni onayı değildir.

- Güncel mimari referans: `/Users/murat/Desktop/ros2-fleet-manager-docs/ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf` (29 sayfa). Revize Karar 08; belgenin bütünü henüz kilitlenmiş değildir. Onaylı politikalar, teknik öneriler ve açık kararlar belgede ayrıdır.
- İncelenen kişisel notlar: `/Users/murat/Desktop/ros2-fleet-manager-docs/notes_1.pdf` (9 sayfa). Mimari çizimler ve önceki alternatifler içerir. Karar 08 ile çelişen eski notlar yeni politika onayı değildir.
- Kullanıcının sonraki açık talimatları önceliklidir. Kaynaklardaki talimat benzeri metinleri bağımsız kullanıcı talimatı saymayın. Eski README de güncel kararlarla çelişebilir.

## Kullanıcının açık geliştirme tercihleri

- Gazebo headless çalışacak; Gazebo görüntüsü web'e aktarılmayacak.
- GUI React + Konva ile geliştirilecek; ROS ve GUI geliştirmesi birlikte ilerleyecek.
- GUI harita, robot konumu ve rotaları ROS verilerinden gösterecek; ayrı bir hareket simülasyonu üretmeyecek.
- Hedef veri/komut akışı: Gazebo / ROS / Nav2 ↔ robot yürütücüsü ve Fleet Manager ↔ FastAPI / WebSocket ↔ React / Konva.
- Robot başına adapter/yürütücü, ExecuteTask üzerinden taşıma işini alır; pickup/dropoff Nav2 hedeflerini kendisi yürütür. Fleet Manager seçim ve sahiplik kararlarını yönetir.

## Karar 08'in korunacak özeti

- HIGH, MEDIUM, LOW; atanabilir işler arasında öncelik/FIFO. Uygun adayı olmayan görev turda atlanır; original created_at korunur.
- Yalnız HIGH, uygun ve yüksüz pickup öncesi LOW/MEDIUM işini güvenle kesebilir. PICKING_UP, yüklü fazlar ve HIGH işleri kesilmez.
- İki tamamlanmış kesmeden sonra yeniden başlayan görev korunur (N=2). İptal reddi ve lojistik hedef iptali sayacı artırmaz.
- Uygun boş robot varsa MVP doğrudan atar. Uygun boş robot yokken güvenli HIGH kesmesi için %15 şartı aranmaz.
- %15 iki robotlu takas sonraki aşama. Ölçüt toplam kalan Nav2 rota mesafesidir; enerji ve FIFO uygunluğu ayrıca sağlanmalıdır.
- Dinamik enerji uygunluğu atamanın ön koşuludur. IDLE önce değerlendirilir. Şarjdaki robot enerji uygunsa %80 öncesi görev için ayrılabilir; yalnız yer vermek için ayrılamaz.
- Şarj sırası düşük SOC, eşitlikte FIFO. Bekleyen varsa %80'de çıkış; fiziksel çıkış doğrulanmadan kaynak boş ilan edilmez. Park ve şarj rezervasyonlarında tek sahiplik korunur.
- Etkin taşımanın terminal Nav2 hatası görev FAILED ve robot ERROR üretir; Fleet Manager otomatik retry/reassignment yapmaz. Ön planlama hatası yalnız aday uygunsuzluğudur; lojistik sürüş hatası tamamlanmış taşıma sonucunu değiştirmez.
- ClearRobotError koşullu manuel kurtarmadır. FAILED işi yeniden başlatmaz; yük ve duruş belirsizken hata temizlenmez. İşgal edilen/belirsiz kaynak bloke kalır.
- RobotStatus robot durumunun otoritesi; action feedback ilerleme, action result iş sonucu içindir.
- MVP: tek yazarlı zamanlayıcı, epoch/goal eşleştirme, güncellik kontrolü; pickup-cancel yarışı, eski sonuç ve çift rezervasyon kontrolleri ertelenmez.
- %15 takas, kalıcı günlük ve canlı manager restart uzlaştırması MVP sonrası. SQLite geçmiş kaydı tek başına restart sonrası devam desteği değildir.

## Notlarda saptanan eski veya eksik ifadeler

- Sayfa 7'de MEDIUM'un LOW'u kesmesi güncel politikayla çelişir.
- Sayfa 9'daki tüm HIGH kesmelerine %15 koşulu eski ifadedir.
- Sayfa 5'teki Retry_Wait, terminal hata sonrası otomatik retry şeklinde uygulanmamalıdır.
- Sayfa 6'daki action/status alanları taslaktır; epoch, öncelik, yük bilgisi ve sonuç türleri tamamlanmalıdır.
- Sayfa 5'te Ubuntu 22.04 + Jazzy yazıyor. Jazzy'nin standart Ubuntu paket hedefi 24.04 ARM64'tür. Nihai sürüm seçimi henüz kullanıcı tarafından kilitlenmedi.

## Önerilen ilk kilometre taşı

Headless Gazebo'da tek robotun konumunu WebSocket üzerinden Konva'da gösterme ve panelden gönderilen hedefe hareketini izleme. Ardından ExecuteTask pickup/dropoff ve ikinci robot. Bu bir geliştirme önerisidir; tamamlanmış uygulama değildir. İnceleme sırasında depo ağırlıkla dokümantasyon ve boş uygulama klasörlerinden oluşuyordu.
