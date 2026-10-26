# C3 — Fleet Manager Resmî Karar Kaydı

> **24 Ekim 2026 C3.3.1 ek kaydı:** [Executor güvenliği kararları](c3-3-1-executor-safety-decisions-2026-10-24.md), sonraki yedi kullanıcı onayını ve önceki açık seçeneklere etkisini kaydeder. İlgili konularda bu ek kayıt esas alınır; uygulama ve test başarısı iddia edilmez.

> **24 Ekim 2026 ek kaydı:** [C3.3 teknik kararları](c3-3-integration-decisions-2026-10-24.md), kaynak sıra/oturum, belirsiz teslim, saat ayrımı ve açık goal reddi için sonraki kullanıcı kararlarını kaydeder. İlgili eski seçenekler ve uygulama sınırları bu kayıtta gerekçeleriyle açıklanır; C3.3 uygulaması veya entegrasyon başarısı iddia edilmez.

**Tarih:** 24 Ekim 2026\
**Durum:** ONAYLANDI / TEKNİK SÖZLEŞME\
**Kapsam:** Aşama C3 — `fleet_manager` Çekirdeği, Görev Kuyruğu, Zamanlayıcı ve Olay Döngüsü\
**İlgili Belgeler:** [AGENTS.md](../../AGENTS.md), [project-context.md](../project-context.md), [DOC-ARCH-2026-10-23-FINAL](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md), [Revize Karar 08](../ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf), [C2 Karar Kaydı](c2-executor-decisions-2026-10-24.md)

---

## 1. Onaylanan Kullanıcı Kararları

Aşağıdaki kararlar kullanıcı tarafından resmî olarak onaylanmış ve Aşama C3 için kilitlenmiştir:

### C3-DEC-01: `RobotStatus` Stale Eşiği Kilitlendi (2.0 Saniye)
- 5 Hz periyotla yayınlanan `RobotStatus` telemetri mesajı son **2.0 saniye** boyunca güncellenmeyen robotlar Fleet Manager tarafından `STALE` olarak işaretlenir.
- `STALE` durumundaki robotlar uygunluk filtresinden derhal çıkarılır ve yeni lojistik görev atamalarına kapatılır.
- Robot telemetrisi yeniden 2.0 saniye penceresi içinde güncel veri üretmeye başladığında uygunluk filtresine tekrar dahil edilir.
- **Gerekçe:** İletişimi veya lokalizasyonu kesilmiş robota görev atayarak simülasyonda kilitlenme (deadlock) veya hedef sapması yaşanması engellenir.

### C3-DEC-02: Aktif Görevde İletişim Kesintisi Sınırları ve Otomatik FAILED Yasağı
- Aktif bir taşıma görevi icra eden robot ile telemetri iletişimi **5.0 saniye** kesilirse Fleet Manager operatör uyarısı (`COMMUNICATION_WARNING`) üretir.
- **Kesin Kural:** İletişim kaybı 10.0 saniyeye ulaşsa veya aşsa dahi **görev otomatik olarak `FAILED` yapılmaz, robot durumu otomatik olarak `ERROR` ilan edilmez**.
- **Fiziksel Durum Otoritesi:** Robotun fiziksel dünyadaki gerçek durumunun tek otoritesi `fleet_robot_executor` bileşenidir. Fleet Manager, sırf DDS veya ağ gecikmesi nedeniyle uzaktan fiziksel durum ataması yapamaz.
- Güvenli duruş, haberleşmenin geri gelmesi ve operatör müdahalesi için Bölüm 3'te listelenen seçenekler doğrultusunda ayrı bir kurtarma protokolü tasarlanacaktır.

### C3-DEC-03: Nav2 Eşitliğinde En Uzun Süredir Boşta Kalan (IDLE) Robot Tercihi
- Göreve aday birden fazla uygun robotun Nav2 rota mesafeleri birbirine eşitse ($|\Delta d| \le 10^{-4}\text{ m}$):
  1. Öncelikle **en uzun süredir `STATE_IDLE` durumunda bekleyen** robot seçilir (`idle_duration` veya `last_task_completed_timestamp` metriği ile).
  2. Boşta kalma süreleri de eşitse, sistem determinizmi sağlamak amacıyla alfabetik olarak en küçük `robot_id` (ör. `robot_1` < `robot_2`) tercih edilir.
- **Gerekçe:** Filo robotları arasında çalışma süresi dengelenir (wear leveling); aynı zamanda testlerde %100 tekrarlanabilir deterministik atama sağlanır.

### C3-DEC-04: Başlamamış Görevlerde Aging Uygulanmaması (Katı Olmayan / Work-Conserving FIFO)
- MVP kapsamında henüz hiç başlamamış LOW öncelikli görevler için aging (bekleme süresine bağlı otomatik öncelik artırma) **uygulanmaz**.
- Sistem, Revize Karar 08 ile onaylanan **atanabilirler arası FIFO (work-conserving)** prensibini korur:
  - Tarama her zaman HIGH $\rightarrow$ MEDIUM $\rightarrow$ LOW sırasıyla yapılır.
  - Bir görev aday yetersizliği veya enerji eksikliği nedeniyle atanamazsa o turda atlanır (`skip`), sıradaki göreve geçilir; zaman damgası veya önceliği değiştirilmez.
  - $N=2$ preemption koruması, yalnızca **başlamış ve güvenli kesmeye uğramış** görevlerin üçüncü kez çalışırken kesilmesini engeller; hiç başlamamış LOW görevlere çalışma garantisi vermez.

---

## 2. Teknik İlkeler ve Mimari Sözleşmeler

### 2.1 Nav2 Rota Başarısızlığı ve Enerji Uygunluğu Sözleşmesi
- Robotun göreve atanabilmesi için dinamik Wh enerji yeterlilik koşulu ($E_{\text{required}} \le E_{\text{available}}$) zorunludur.
- $d_{\text{total}} = L(\mathbf{p}_{\text{current}}, \mathbf{p}_{\text{pickup}}) + L(\mathbf{p}_{\text{pickup}}, \mathbf{p}_{\text{dropoff}})$ formülündeki $L$, Nav2 küresel yol uzunluğudur.
- **Kesin Kural:** Nav2 planner geçici arıza, engel blokajı veya harita kopukluğu nedeniyle yol hesaplayamazsa, **Euclidean (kuş uçuşu) fallback mesafesiyle enerji uygunluğu kesinlikle ONAYLANMAZ**.
- Rota planı üretilemediğinde adayın enerji kontrolü otomatik olarak **BAŞARISIZ** sayılır. Robot o görev için adaylıktan elenir; görev `FAILED` yapılmaz, kuyrukta bekletilir.

### 2.2 Fiziksel İşgal Süresince Rezervasyon Serbest Bırakma Yasağı
- Şarj istasyonları ve park alanları `FREE` $\rightarrow$ `RESERVED` $\rightarrow$ `OCCUPIED` $\rightarrow$ `RELEASING` $\rightarrow$ `FREE` yaşam döngüsüyle yönetilir.
- **Kesin Kural:** İstasyondan görev almak veya parktan çıkmak üzere ayrılan bir robotun alanı, robot fiziksel olarak alanı terk etmeden kesinlikle `FREE` ilan edilemez.
- Robotun odometri ve AMCL pozu üzerinden istasyon tolerans yarıçapının dışına çıktığı ($\|\mathbf{p}_{\text{robot}} - \mathbf{p}_{\text{station}}\| > r_{\text{tolerance}} + \delta_{\text{margin}}$) doğrulanana kadar kaynak durumu `OCCUPIED` veya `RELEASING` olarak tutulur.
- Robot `STATE_ERROR` durumuna düşerse, bulunduğu fiziksel kaynak `BLOCKED` olarak işaretlenir ve operatör müdahalesine kadar başka robota tahsis edilemez.

### 2.3 SQLite Outbox, Tek Consumer ve Idempotency Sınırları
Sistem bütünlüğü birbirini tamamlayan üç ayrık mekanizmayla güvenceye alınır; ancak dağıtık bir sistemde mutlak yarış koşulu yokluğu iddia edilmez:

1. **Tek Consumer Olay Döngüsü (`asyncio.Queue`):**
   - Fleet Manager iç çekirdeğinde tek bir tüketici döngüsü işletilir. Gelen telemetri, REST komutları ve action sonuçları sıraya konur ve tekil olarak tüketilir. Bu mekanizma çekirdek içi bellek yarışlarını (race condition) ortadan kaldırır.
2. **SQLite Outbox ve Atomik Transaction:**
   - Görev durumu, robot durumu, kaynak rezervasyonu ve dış dünyaya gönderilecek ROS eylemleri tek bir SQLite transaction'ı (`BEGIN IMMEDIATE` ... `COMMIT`) içinde atomik olarak yazılır. Yarım kalmış durum geçişleri önlenir.
3. **Idempotency ve Mesaj Sıralaması (Deduplication):**
   - Ağdan gecikmeli, mükerrer veya sırasız gelen action feedback/result mesajları `(task_id, assignment_epoch, goal_uuid)` üçlüsü ve `status_seq` denetimiyle süzülür. Bayat epoch veya yinelenen olaylar iş mantığına girmeden elenir.
4. **Dağıtık Sınır ve Gerçekçi Güvence:**
   - DDS ağ gecikmeleri, container yeniden başlatmaları ve donanım kesintileri altında "hiçbir yarış koşulu olamaz" iddiasında bulunulamaz. Bu mekanizmalar yarış risklerini en aza indirmek ve yarış anında tutarsız durumu engelleyip fail-safe moda geçmek için tasarlanmıştır.

---

## 3. İletişim Kaybı İçin Açık Kalan Kurtarma Seçenekleri

C3-DEC-02 uyarınca aktif görevde 10 saniye iletişim kesildiğinde otomatik `FAILED` yapılmayacaktır. Bu durum için uygulanabilecek mimari seçenekler aşağıdadır ve kullanıcı onayına kadar **AÇIK ÖNERİ** olarak takip edilecektir:

### Seçenek A: Executor Tarafında Yerel Watchdog ve Emniyetli Duruş (Önerilen)
- Robot Executor, Fleet Manager veya DDS ağından belirli bir süre (`heartbeat_timeout`, ör. 5.0 sn) sinyal alamazsa Nav2 hedefini yerel olarak durdurur ve sıfır hızda güvenli beklemeye geçer.
- İletişim geri geldiğinde durumunu Fleet Manager'a raporlar; görev askıda (`PAUSED`) kalır.
- Operatör arayüzden "Görevi Sürdür" (`Resume`) veya "Görevi İptal Et" (`Cancel`) komutu verir.

### Seçenek B: Fleet Manager Tarafında Askıya Alma (`COMM_LOST_SUSPENDED`)
- Fleet Manager 10.0 saniye dolduğunda görevi `COMM_LOST_SUSPENDED` statüsüne alır ve robotu rezervasyonlarıyla birlikte dondurur.
- Yeni görev ataması yapılmaz; diğer robotlar bu alana yönlendirilmez.
- İletişim geri geldiğinde robotun gerçek fazı ve pozu sorgulanır; durum tutarlıysa göreve devam ettirilir, tutarsızsa operatöre alarm verilir.

### Seçenek C: Yapılandırılabilir Kurtarma Penceresi (`reconnect_grace_period`)
- İletişim koptuktan sonra 5 sn'de uyarı, örneğin 30 sn'lik bir kurtarma penceresi (`reconnect_grace_period`) tanınır.
- Bu süre içinde robot durum mesajı geri gelirse görev kesintisiz devam eder.
- Süre dolarsa operatör onayıyla `ClearRobotError.srv` benzeri kontrollü bir manuel iptal prosedürü devreye sokulur.

---

## 4. Karar Etkisi ve Doğrulama Matrisi

| Karar | Etkilenen Modül | Test Senaryosu | Beklenen Kanıt |
|---|---|---|---|
| **C3-DEC-01** | `scheduler.py`, `fleet_service.py` | Stale Robot Testi | 2.0 saniye telemetrisi gelmeyen robot uygun olsa bile göreve atanmaz. |
| **C3-DEC-02** | `event_loop.py`, `outbox.py` | İletişim Kesintisi Testi | 5 sn kesintide uyarı loglanır; 10 sn dolduğunda görev FAILED yapılmaz, askıda tutulur. |
| **C3-DEC-03** | `scheduler.py` | Eşit Mesafe Tie-Break | Mesafeleri eşit iki robottan IDLE süresi büyük olan seçilir; eşitlikte `robot_1` atanır. |
| **C3-DEC-04** | `task_queue.py`, `scheduler.py` | T01-T02 ve Starvation | LOW işler beklerken HIGH/MED işler atanır; LOW işin önceliği suni olarak artırılmaz. |
| **Teknik Düzeltme** | `energy.py`, `route_client.py` | Nav2 Rota Hatası Testi | Nav2 mesafe üretemezse Euclidean fallback kullanılmaz, enerji onayı verilmez. |
| **Teknik Düzeltme** | `reservations.py` | Fiziksel Ayrılma Testi | Robot tolerans yarıçapı içindeyken kaynak FREE yapılmaz; ayrılınca FREE olur. |
