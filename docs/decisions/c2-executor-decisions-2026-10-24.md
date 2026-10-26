# C2 — Robot Executor Resmî Karar Kaydı

> **24 Ekim 2026 C3.3.1 ek kaydı:** [Executor güvenliği kararları](c3-3-1-executor-safety-decisions-2026-10-24.md), sonraki yedi kullanıcı onayını ve önceki açık seçeneklere etkisini kaydeder. İlgili konularda bu ek kayıt esas alınır; uygulama ve test başarısı iddia edilmez.

> **24 Ekim 2026 ek kaydı:** [C3.3 teknik kararları](c3-3-integration-decisions-2026-10-24.md), kaynak sıra/oturum, belirsiz teslim, saat ayrımı ve açık goal reddi için sonraki kullanıcı kararlarını kaydeder. İlgili eski seçenekler ve uygulama sınırları bu kayıtta gerekçeleriyle açıklanır; C3.3 uygulaması veya entegrasyon başarısı iddia edilmez.

**Tarih:** 24 Ekim 2026\
**Durum:** ONAYLANDI / TEKNİK SÖZLEŞME\
**Kapsam:** Aşama C2 — `fleet_robot_executor` ve `fleet_interfaces` arayüzleri\
**İlgili Belgeler:** [AGENTS.md](../../AGENTS.md), [project-context.md](../project-context.md), [DOC-ARCH-2026-10-23-FINAL](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md)

---

## 1. Onaylanan Kullanıcı Kararları

Aşağıdaki kararlar kullanıcı tarafından resmî olarak onaylanmış ve Aşama C2 için kilitlenmiştir:

### C2-DEC-01: `RobotStatus.msg` İçine `current_phase` Alanı Eklendi
- `RobotStatus.msg` içine `uint8 current_phase` alanı eklenmiştir.
- Faz değerleri `ExecuteTask.action` geri bildirimiyle (feedback) birebir tutarlıdır:
  - `uint8 PHASE_NONE = 0` (Görev dışı durumlar: IDLE, CHARGING, ERROR vb.)
  - `uint8 PHASE_MOVING_TO_PICKUP = 1`
  - `uint8 PHASE_LOADING = 2`
  - `uint8 PHASE_MOVING_TO_DROPOFF = 3`
  - `uint8 PHASE_UNLOADING = 4`
- **Gerekçe:** Fleet Manager ve web arayüzü telemetri akışı, action feedback mekanizmasına bağımlı kalmaksızın 5 Hz periyodik durum topic'i üzerinden anlık lojistik fazı izleyebilir.

### C2-DEC-02: `ExecuteTask.action` Öncelik Sabitleri Kilitlendi
- `ExecuteTask.action` Goal alanında yer alan `uint8 priority` için açık IDL sabitleri tanımlanmıştır:
  - `uint8 PRIORITY_HIGH = 1`
  - `uint8 PRIORITY_MEDIUM = 2`
  - `uint8 PRIORITY_LOW = 3`
- **Gerekçe:** Sayısal öncelik tanımları IDL seviyesinde tekilleştirilmiş; Python veya domain tarafında bağımsız farklı sayısal değerler oluşturulması engellenmiştir.

### C2-DEC-03: İki Aşamalı C2 Test Stratejisi
- C2 doğrulaması iki katmanda yürütülecektir:
  1. **Birim Testleri (Saf Python):** ROS 2 ve simülasyon bağımlılığı olmadan durum makinesi geçişleri, faz kilitleri ve güvenli iptal kontrolleri `pytest` ile doğrulanır.
  2. **Entegrasyon Testleri (Docker Compose):** B3 Retry oturumunda doğrulanan iki robotlu (`/robot_1`, `/robot_2`) ayrık namespace altyapısı korunarak headless Gazebo + Nav2 + Robot Executor uçtan uca test edilir.

---

## 2. Güncellenen Arayüz Sözleşmeleri (C2 Nihai)

### 2.1 `interfaces/fleet_interfaces/action/ExecuteTask.action`
```action
# Goal
string task_id
uint64 assignment_epoch
geometry_msgs/PoseStamped pickup_pose
geometry_msgs/PoseStamped dropoff_pose
uint8 priority

uint8 PRIORITY_HIGH = 1
uint8 PRIORITY_MEDIUM = 2
uint8 PRIORITY_LOW = 3
---
# Result
uint8 status
uint64 completed_epoch
builtin_interfaces/Time completion_stamp
string error_reason

uint8 STATUS_SUCCEEDED = 1
uint8 STATUS_FAILED = 2
uint8 STATUS_PREEMPTED = 3
---
# Feedback
uint8 current_phase
geometry_msgs/PoseStamped current_pose
float32 distance_to_goal
float32 battery_soc

uint8 PHASE_MOVING_TO_PICKUP = 1
uint8 PHASE_LOADING = 2
uint8 PHASE_MOVING_TO_DROPOFF = 3
uint8 PHASE_UNLOADING = 4
```

### 2.2 `interfaces/fleet_interfaces/msg/RobotStatus.msg`
```msg
std_msgs/Header header
string robot_id
uint64 current_epoch
uint8 state
uint8 current_phase
bool is_loaded
geometry_msgs/PoseStamped pose
float32 battery_soc_percent
float64 battery_energy_wh
string current_task_id

uint8 STATE_IDLE = 1
uint8 STATE_EXECUTING_TASK = 2
uint8 STATE_CHARGING = 3
uint8 STATE_RETURNING_TO_CHARGE = 4
uint8 STATE_RETURNING_TO_PARK = 5
uint8 STATE_ERROR = 6

uint8 PHASE_NONE = 0
uint8 PHASE_MOVING_TO_PICKUP = 1
uint8 PHASE_LOADING = 2
uint8 PHASE_MOVING_TO_DROPOFF = 3
uint8 PHASE_UNLOADING = 4
```

### 2.3 `interfaces/fleet_interfaces/srv/ClearRobotError.srv`
```srv
string robot_id
uint64 expected_epoch
---
bool accepted
string reason
uint8 resulting_state
```

---

## 3. Netleştirilecek Teknik Konular ve Seçenekler

Aşağıdaki konular onaysız kesinleştirilmemiştir; uygulama öncesi değerlendirilecek açık seçeneklerdir:

### 3.1 `assignment_epoch` ve Hata Temizleme Sürüm Ayrımı
- **Mevcut Durum:** `assignment_epoch` Fleet Manager tarafından göreve atanan monotonik sayaçtır. Robot Executor'ın `ClearRobotError` sırasında bu epoch'u kendiliğinden artırması, FM'in atama otoritesiyle çelişebilir.
- **Seçenek A (Önerilen - Görev Epoch'unu Koruma / FM Otoritesi):** Robot Executor `ClearRobotError` icrasında `assignment_epoch` değerini kendiliğinden artırmaz. `expected_epoch == current_epoch` eşleşmesini teyit edip robotu `STATE_IDLE` durumuna alır ve `current_task_id = ""` temizler. Bir sonraki yeni görevin `assignment_epoch` değeri Fleet Manager tarafından atanır.
- **Seçenek B (Dahili Kurtarma Sayacı):** `RobotStatus` içine görevden bağımsız ayrı bir `recovery_sequence` eklenir; `assignment_epoch` yalnızca lojistik görevlerde kullanılır.
- **Karar:** Kullanıcı onayı alınana kadar `assignment_epoch` Executor tarafından otomatik artırılmayacak; Seçenek A uygulanacaktır.

### 3.2 Güvenli İptal ve Çok Kriterli Duruş Teyidi
- Yalnızca `cmd_vel = 0` komutu yayınlamak fiziksel duruş kanıtı sayılmaz.
- Güvenli iptal için aşağıdaki 3 koşul **aynı anda** sağlanmalıdır:
  1. Nav2 `cancel_goal_async()` çağrısının terminal iptal sonucu (`STATUS_CANCELED`) vermesi.
  2. Robot odometrisinden güncel simülasyon zaman damgalı ölçüm alınması (stale odom koruması).
  3. Odometri hızlarının eşik altında olması: $\|\mathbf{v}\| \le v_{\text{threshold}}$ ve $|\omega| \le \omega_{\text{threshold}}$.

### 3.3 Duruş Teyidi Alınamazsa Güvenli Hata Davranışı
- İptal talebi sonrası robot durdurulamazsa veya odometri zaman aşımına uğrarsa robot **asla `PREEMPTED` veya `IDLE` ilan edilemez**.
- **Seçenek 1 (Fail-Safe ERROR - Önerilen):** İptal timeout süresi aşılırsa görev `STATUS_FAILED` (hata: `CANCEL_STOP_TIMEOUT`), robot durumu `STATE_ERROR` yapılır. Fiziksel kontrol netleşene kadar robot atamaya kapatılır ve `ClearRobotError` gerektirir.
- **Seçenek 2 (İkinci Fren Girişimi):** 2.0 saniye boyunca aktif `cmd_vel = 0` tekrarlanır; duruş teyidi gelmezse `STATE_ERROR` tetiklenir.

### 3.4 Kalibrasyonsuz Parametreler (Öneri Olarak Kalanlar)
- Yükleme ve boşaltma simülasyon süreleri (`loading_duration_sec: 2.0`, `unloading_duration_sec: 2.0`) onaylı politika değildir; yapılandırılabilir parametre önerisidir.
- Sıfır hız eşikleri ($v \le 0.01\text{ m/s}, \omega \le 0.01\text{ rad/s}$) deneysel olarak kalibre edilmemiştir; öneri eşiklerdir.
