# Mimari ve algoritma diyagramları

26 Ekim 2026 kaynak incelemesi. Bu katalog mevcut kararların görsel anlatımıdır; yeni mimari karar değildir. [İnceleme ve fark raporu](../validation/organization/organization-validation-2026-10-26.md) hedef ile kodun ayrıldığı yolları kaydeder.

## Durum ve görsel dil

- **IMPLEMENTED:** Belirtilen akışın kodu vardır; bütün ürünün veya her hata yolunun canlı doğrulandığı anlamına gelmez.
- **PARTIAL:** Kodun bir kısmı vardır; eksik bağlantı veya karar/kod farkı aşağıda belirtilir.
- **PLANNED:** Hedef akış; ürün uygulaması yoktur. Öneri ayrıntıları onaylı politika sayılmaz.
- **UNVERIFIED:** Uygulaması/kanıtı bu incelemede belirlenemeyen akış için ayrılmıştır; bu katalogda böyle etiketlenmiş akış yoktur.

Mavi: Fleet Manager; mor: Executor; turkuaz: Nav2/simülasyon; sarı: batarya; gri silindir: veritabanı; pembe: UI/API. Yeşil yuvarlatılmış düğüm başlangıç/bitiş, beyaz baklava karar, kırmızı hata/blokaj, kesik turuncu bekleme anlamına gelir. Durum ve metin de anlamı taşır; yalnız renge bağlı değildir.

Her akış için `.mmd` düzenlenebilir kaynak, `.svg` türetilmiş çıktıdır. GitHub'da bölüm altındaki SVG doğrudan görünür; aynı kaynak Mermaid kod bloğu olarak da sunulur. Kaynak ve katalog kopyası birlikte güncellenmelidir.

## Kapsam tablosu

| No | Kategori / algoritma | Durum | Kaynak / SVG |
|---|---|---|---|
| 1 | Sistem — [Sistem ve Docker mimarisi](#01-system-architecture) | PARTIAL | [Mermaid](src/system-architecture.mmd) · [SVG](svg/system-architecture.svg) |
| 2 | Görev — [Görev kabulü ve atanabilir FIFO](#02-task-admission-fifo) | IMPLEMENTED | [Mermaid](src/task-admission-fifo.mmd) · [SVG](svg/task-admission-fifo.svg) |
| 3 | Görev — [Robot seçimi ve Wh uygunluğu](#03-robot-selection-energy) | PARTIAL | [Mermaid](src/robot-selection-energy.mmd) · [SVG](svg/robot-selection-energy.svg) |
| 4 | Yürütme — [Robot Executor görev yaşam döngüsü](#04-executor-lifecycle) | IMPLEMENTED | [Mermaid](src/executor-lifecycle.mmd) · [SVG](svg/executor-lifecycle.svg) |
| 5 | Yürütme — [Güvenli preemption ve N=2](#05-safe-preemption) | IMPLEMENTED | [Mermaid](src/safe-preemption.mmd) · [SVG](svg/safe-preemption.svg) |
| 6 | Güvenlik — [RobotStatus sıra ve oturum yönetimi](#06-status-session-order) | PARTIAL | [Mermaid](src/status-session-order.mmd) · [SVG](svg/status-session-order.svg) |
| 7 | Güvenlik — [DDS goal ve cancel protokolü](#07-dds-goal-cancel) | IMPLEMENTED | [Mermaid](src/dds-goal-cancel.mmd) · [SVG](svg/dds-goal-cancel.svg) |
| 8 | Güvenlik — [Assignment epoch ve UUID uzlaştırması](#08-assignment-reconciliation) | PARTIAL | [Mermaid](src/assignment-reconciliation.mmd) · [SVG](svg/assignment-reconciliation.svg) |
| 9 | Kalıcılık — [SQLite Outbox ve tek consumer](#09-sqlite-outbox-consumer) | IMPLEMENTED | [Mermaid](src/sqlite-outbox-consumer.mmd) · [SVG](svg/sqlite-outbox-consumer.svg) |
| 10 | Enerji — [Wh batarya hesabı](#10-battery-wh-integration) | PLANNED | [Mermaid](src/battery-wh-integration.mmd) · [SVG](svg/battery-wh-integration.svg) |
| 11 | Enerji — [Şarj sırası ve istasyon seçimi](#11-charging-queue-selection) | PLANNED | [Mermaid](src/charging-queue-selection.mmd) · [SVG](svg/charging-queue-selection.svg) |
| 12 | Enerji — [Şarjdan ayrılma ve yüzde 80](#12-charging-exit-policy) | PLANNED | [Mermaid](src/charging-exit-policy.mmd) · [SVG](svg/charging-exit-policy.svg) |
| 13 | Kaynak — [Park rezervasyonu ve güvenli bekleme](#13-parking-reservations) | PARTIAL | [Mermaid](src/parking-reservations.mmd) · [SVG](svg/parking-reservations.svg) |
| 14 | Kurtarma — [FAILED / ERROR ve operatör kurtarma](#14-failure-operator-recovery) | PARTIAL | [Mermaid](src/failure-operator-recovery.mmd) · [SVG](svg/failure-operator-recovery.svg) |
| 15 | Konfigürasyon — [fleet.yaml yaşam döngüsü](#15-fleet-config-lifecycle) | PARTIAL | [Mermaid](src/fleet-config-lifecycle.mmd) · [SVG](svg/fleet-config-lifecycle.svg) |
| 16 | Panel — [REST / WebSocket ve 2D panel](#16-rest-websocket-gui) | PLANNED | [Mermaid](src/rest-websocket-gui.mmd) · [SVG](svg/rest-websocket-gui.svg) |
| 17 | Rota — [Asenkron rota ve önbellek](#17-route-cache) | PARTIAL | [Mermaid](src/route-cache.mmd) · [SVG](svg/route-cache.svg) |
| 18 | Güvenlik — [Duplicate kayıtları ve restart engeli](#18-duplicate-restart-guard) | PARTIAL | [Mermaid](src/duplicate-restart-guard.mmd) · [SVG](svg/duplicate-restart-guard.svg) |

<a id="01-system-architecture"></a>

## 01. Sistem ve Docker mimarisi

**Durum:** PARTIAL. **Amaç:** Üç servisli hedefte bileşen sahipliğini göstermek.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Filo config, görev isteği, ROS telemetrisi | Görev komutları ve hedef panel görünümü | Frontend yalnız HTTP/WS; robot düğümleri config ile çoğalır. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [c3-3-3-dual-robot-integration-decisions-2026-10-24.md](../decisions/c3-3-3-dual-robot-integration-decisions-2026-10-24.md)

**Kaynak kod:** [builder.py](../../backend/fleet_manager/builder.py) · [README.md](../../docker/compose/README.md)

**Test / kanıt:** [c3-3-3-validation-2026-10-24.md](../validation/c3/c3-3-3-validation-2026-10-24.md)

**Sınır / fark:** Kök üç servis Compose yoktur. C3.3.3 iki servis testinde geçici batarya besleyicisi kullanılır; gerçek Battery Simulator değildir.

![Sistem ve Docker mimarisi](svg/system-architecture.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "01 · Sistem ve Docker mimarisi · PARTIAL"
---
flowchart TB
 subgraph UI["frontend • PLANNED"]
 U["React + Konva • 2D panel"]:::ui
 end
 subgraph BACK["backend • PARTIAL"]
 API["FastAPI / WebSocket • PLANNED"]:::ui
 FM["Fleet Manager • tek consumer"]:::fm
 DB[("SQLite + Outbox")]:::db
 API <-->|"Olay ve komut"| FM
 FM <-->|"Atomik kayıt"| DB
 end
 subgraph SIM["simulation • PARTIAL"]
 CFG["fleet.yaml → robot başına namespace"]:::fm
 EX["Robot Executor • fiziksel durum otoritesi"]:::executor
 NAV["Nav2 / AMCL • robot başına"]:::nav
 GZ["Gazebo headless / bridge / Map Server"]:::nav
 BAT["Battery Simulator • PLANNED"]:::battery
 CFG --> EX
 CFG --> NAV
 CFG --> BAT
 EX -->|"NavigateToPose"| NAV
 NAV <-->|"Odometri / sensör / hız"| GZ
 GZ -->|"/clock ve odometri"| BAT
 BAT -.->|"Hedef batarya yayını"| EX
 end
 U <-->|"HTTP / WebSocket"| API
 FM -->|"DDS ExecuteTask / cancel / ClearRobotError"| EX
 EX -->|"RobotStatus / feedback / result"| FM
 FM <-->|"ComputePathToPose"| NAV

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="02-task-admission-fifo"></a>

## 02. Görev kabulü ve atanabilir FIFO

**Durum:** IMPLEMENTED. **Amaç:** Kuyruğun uygun olmayan görev yüzünden durmamasını açıklamak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| SUBMIT_TASK, task_id, priority, created_at; TICK | Atama, kesme talebi veya kuyrukta bekleme | HIGH→MEDIUM→LOW; aynı sınıfta created_at; aging yok. |

**Kaynak belge:** [c3-fleet-manager-decisions-2026-10-24.md](../decisions/c3-fleet-manager-decisions-2026-10-24.md)

**Kaynak kod:** [task_queue.py](../../backend/fleet_manager/domain/task_queue.py) · [fleet_manager_core.py](../../backend/fleet_manager/domain/fleet_manager_core.py) · [event_loop.py](../../backend/fleet_manager/event_loop.py)

**Test / kanıt:** [test_fleet_manager_domain.py](../../tests/test_fleet_manager_domain.py)

![Görev kabulü ve atanabilir FIFO](svg/task-admission-fifo.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "02 · Görev kabulü ve atanabilir FIFO · IMPLEMENTED"
---
flowchart TD
 A(["SUBMIT_TASK"]):::terminal --> B{"Kimlik yeni ve öncelik geçerli mi?"}:::decision
 B -->|"Hayır"| X["Kabul hatası"]:::error
 B -->|"Evet"| Q["Öncelik ve created_at ile kuyruğa ekle"]:::fm
 Q --> T(["TICK"]):::terminal
 T --> N["Sıradaki HIGH / MEDIUM / LOW görevi"]:::fm
 N --> H{"İnceleme kilidi var mı?"}:::decision
 H -->|"Evet"| SK["Bu tur atla; tarih ve öncelik aynı"]:::wait
 H -->|"Hayır"| R{"Uygun boş / park dönüşü adayı?"}:::decision
 R -->|"Var"| AS["Kuyruktan çıkar; epoch + UUID ile ata"]:::fm
 R -->|"Yok"| P{"HIGH ve güvenli kesme adayı?"}:::decision
 P -->|"Evet"| C["HIGH beklemeye; CANCEL_TASK üret"]:::fm
 P -->|"Hayır"| SK
 AS --> NEXT{"Taranacak görev kaldı mı?"}:::decision
 C --> NEXT
 SK --> NEXT
 NEXT -->|"Evet"| N
 NEXT -->|"Hayır"| END(["Yeni olay / TICK bekle"]):::terminal

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="03-robot-selection-energy"></a>

## 03. Robot seçimi ve Wh uygunluğu

**Durum:** PARTIAL. **Amaç:** Mesafe sıralamasından önce enerji ve durum filtresini göstermek.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| RobotStatus, görev pozları, rota mesafeleri, batarya modeli | En yakın uygun aday veya aday yok | Güncel, oturum engeli yok, yüksüz, aktif atamasız; rota ve enerji zorunlu. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [c3-fleet-manager-decisions-2026-10-24.md](../decisions/c3-fleet-manager-decisions-2026-10-24.md)

**Kaynak kod:** [scheduler.py](../../backend/fleet_manager/domain/scheduler.py) · [energy.py](../../backend/fleet_manager/domain/energy.py) · [builder.py](../../backend/fleet_manager/builder.py)

**Test / kanıt:** [test_fleet_manager_domain.py](../../tests/test_fleet_manager_domain.py) · [test_fleet_builder.py](../../tests/test_fleet_builder.py)

**Sınır / fark:** Fark: builder ilk şarj istasyonunu safe_charge seçer; çoklu istasyon erişim seçimi tamamlanmış değildir. Scheduler enerji kontrolüne fleet policies marj/rezervini geçirmez; fonksiyon varsayılanları kullanılır. Hedef formül ile kod arasındaki bu yapılandırma boşluğu korunarak raporlandı.

![Robot seçimi ve Wh uygunluğu](svg/robot-selection-energy.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "03 · Robot seçimi ve Wh uygunluğu · PARTIAL"
---
flowchart TD
 A(["Aday robot"]):::terminal --> F{"Güncel / oturum açık / yüksüz / atanabilir mi?"}:::decision
 F -->|"Hayır"| NO["Adayı ele; görevi FAILED yapma"]:::wait
 F -->|"Evet"| L["L1: robot→pickup; L2: pickup→dropoff<br/>L3: dropoff→safe_charge"]:::nav
 L --> R{"Üç rota geçerli mi?"}:::decision
 R -->|"Hayır"| NO
 R -->|"Evet"| EN["E_required = k × L1 + k × L2 + k × L3 + margin<br/>E_available = C × SoC/100 − C × reserve/100"]:::battery
 EN --> OK{"E_required ≤ E_available?"}:::decision
 OK -->|"Hayır"| NO
 OK -->|"Evet"| SORT["En küçük L1<br/>Eşitlik: en uzun IDLE, sonra robot_id"]:::fm
 SORT --> OUT(["Seçilen aday"]):::terminal

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="04-executor-lifecycle"></a>

## 04. Robot Executor görev yaşam döngüsü

**Durum:** IMPLEMENTED. **Amaç:** Pickup/dropoff adımlarının tek yürütücüsünü göstermek.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| ExecuteTask goal, Nav2 sonucu, simülasyon zamanı | Terminal sonuç ve RobotStatus | Kabul güvenliği, yerel faz kilidi, ilgili goal UUID. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [c2-executor-decisions-2026-10-24.md](../decisions/c2-executor-decisions-2026-10-24.md) · [c3-3-1-executor-safety-decisions-2026-10-24.md](../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md)

**Kaynak kod:** [node.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py) · [state_machine.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/state_machine.py)

**Test / kanıt:** [test_executor_state_machine.py](../../tests/test_executor_state_machine.py) · [test_executor_lifecycle_integration.py](../../tests/test_executor_lifecycle_integration.py)

**Sınır / fark:** Şarj/park sürüş orkestrasyonu bu taşıma yaşam döngüsünün tamamlanmış parçası değildir.

![Robot Executor görev yaşam döngüsü](svg/executor-lifecycle.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "04 · Robot Executor görev yaşam döngüsü · IMPLEMENTED"
---
flowchart TD
 A(["ExecuteTask goal"]):::terminal --> G{"Reset / duplicate / kimlik / durum uygun mu?"}:::decision
 G -->|"Hayır"| RE["Goal reddi veya güvenli blokaj"]:::error
 G -->|"Evet"| P["MOVING_TO_PICKUP → Nav2"]:::nav
 P -->|"Başarı + faz kilidi"| LOAD["LOADING / PICKING_UP<br/>Kesilemez"]:::executor
 LOAD -->|"Yükleme tamam"| D["Yüklü MOVING_TO_DROPOFF → Nav2"]:::nav
 D -->|"Başarı"| UN["UNLOADING • kesilemez"]:::executor
 UN -->|"Boşaltma tamam"| END(["SUCCEEDED + gerçek completed_epoch<br/>Executor IDLE, yüksüz"]):::terminal
 P -->|"Güvenli kesme"| C["Preemption alt akışı"]:::executor
 P -->|"Kesin terminal hata"| ERR["FAILED + ERROR"]:::error
 D -->|"Kesin terminal hata"| ERR
 P -->|"Teslim / sonuç belirsiz"| W["Sahipliği tut; blokaj"]:::wait

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="05-safe-preemption"></a>

## 05. Güvenli preemption ve N=2

**Durum:** IMPLEMENTED. **Amaç:** HIGH atamasından önce terminal duruş el sıkışmasını göstermek.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Yeni HIGH, çalışan görev/faz/yük, sayaç, Nav2 ve odometri | PREEMPTED sonrası yeniden kuyruklama ve HIGH ataması | Boş uygun robot önce; kurban LOW/MED, pickup öncesi, yüksüz, sayaç < 2. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [c3-3-1-executor-safety-decisions-2026-10-24.md](../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md) · [c3-3-3-dual-robot-integration-decisions-2026-10-24.md](../decisions/c3-3-3-dual-robot-integration-decisions-2026-10-24.md)

**Kaynak kod:** [scheduler.py](../../backend/fleet_manager/domain/scheduler.py) · [event_loop.py](../../backend/fleet_manager/event_loop.py) · [node.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py) · [stop_detector.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/stop_detector.py)

**Test / kanıt:** [test_fleet_manager_domain.py](../../tests/test_fleet_manager_domain.py) · [test_executor_safety.py](../../tests/test_executor_safety.py)

**Sınır / fark:** İptal reddi ve timeout kesilme sayacını artırmaz. %15 takas kullanılmaz. Park dönüşünü kesme ayrı lojistik kuralıdır.

![Güvenli preemption ve N=2](svg/safe-preemption.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "05 · Güvenli preemption ve N=2 · IMPLEMENTED"
---
flowchart TD
 H(["Yeni HIGH"]):::terminal --> ID{"Uygun IDLE / boş aday var mı?"}:::decision
 ID -->|"Evet"| DIR["Doğrudan ata"]:::fm
 ID -->|"Hayır"| V{"LOW/MED + pickup öncesi + yüksüz<br/>N < 2 + güncel + rota/enerji uygun?"}:::decision
 V -->|"Hayır"| W["HIGH kuyrukta bekler"]:::wait
 V -->|"Evet"| C["En kısa pickup adayına cancel<br/>HIGH için yeni atama henüz yok"]:::fm
 C --> X{"Executor yerel faz kilidiyle kabul eder mi?"}:::decision
 X -->|"Hayır"| W
 X -->|"Evet"| NAV["İlgili Nav2 goal'u iptal et; fren uygula"]:::nav
 NAV --> T{"Gerçek Nav2 terminal sonucu?"}:::decision
 T -->|"SUCCEEDED"| N["Gerçek faz akışına devam<br/>PREEMPTED üretme"]:::executor
 T -->|"ABORTED"| E["FAILED / ERROR; HIGH yeniden değerlendirilir"]:::error
 T -->|"Belirsiz"| B["Sahipliği tut; güvenli blokaj"]:::wait
 T -->|"STATUS_CANCELED"| O{"Güncel odometri ve sıfır hız?"}:::decision
 O -->|"Hayır"| BRAKE["Frenle ve teyit bekle"]:::wait
 BRAKE --> O
 O -->|"Evet"| R["Eşleşen terminal PREEMPTED"]:::executor
 R --> Q["Kurban sayaç +1; orijinal created_at ile kuyruk<br/>N=2 ise üçüncü çalışmada koruma"]:::fm
 Q --> NEW["Bekleyen HIGH için yeni epoch + UUID"]:::fm

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="06-status-session-order"></a>

## 06. RobotStatus sıra ve oturum yönetimi

**Durum:** PARTIAL. **Amaç:** Fiziksel durum, iletişim tazeliği ve oturum engelini ayırmak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| RobotStatus, status_seq, publisher_session_id, monotonik alım zamanı | Durum kopyası veya STALE / SESSION_BLOCKED | Aynı oturumda artan sıra; ilk durumda IDLE/yüksüz/atamasız doğrulaması. |

**Kaynak belge:** [c3-fleet-manager-decisions-2026-10-24.md](../decisions/c3-fleet-manager-decisions-2026-10-24.md) · [c3-3-1-executor-safety-decisions-2026-10-24.md](../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md) · [c3-3-2-ros2-adapter-decisions-2026-10-24.md](../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md) · [c3-3-3-dual-robot-integration-decisions-2026-10-24.md](../decisions/c3-3-3-dual-robot-integration-decisions-2026-10-24.md)

**Kaynak kod:** [event_loop.py](../../backend/fleet_manager/event_loop.py) · [fleet_tracker.py](../../backend/fleet_manager/domain/fleet_tracker.py) · [status_subscriber.py](../../backend/fleet_manager/adapters/status_subscriber.py) · [safety.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/safety.py)

**Test / kanıt:** [test_ros2_status_subscriber.py](../../tests/test_ros2_status_subscriber.py)

**Sınır / fark:** Consumer, yayıncıdaki uint64 guard ile aynı sınır doğrulamasını yapmaz: negatif olmayan int kabul eder; 0 ve üst sınır kontrolü eksiktir. Yayıncı guard ile consumer aynı bileşen değildir.

![RobotStatus sıra ve oturum yönetimi](svg/status-session-order.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "06 · RobotStatus sıra ve oturum yönetimi · PARTIAL"
---
flowchart TD
 EX["Executor: oturum UUID; uint64 sıra 1’den başlar"]:::executor --> OV{"Sayaç taşar mı?"}:::decision
 OV -->|"Evet"| EB["Executor kabulünü blokla"]:::error
 OV -->|"Hayır"| CB["ROS callback → monotonik alım → consumer"]:::fm
 CB --> S{"Oturum aynı / ilk oturum mu?"}:::decision
 S -->|"Değişti veya zaten engelli"| BLOCK["SESSION_BLOCKED<br/>Atama ve kaynak bırakma kilidi"]:::error
 BLOCK --> RESET["Operatör + kontrollü senaryo reset"]:::wait
 S -->|"Evet"| SEQ{"Sıra önceki kabulden büyük mü?"}:::decision
 SEQ -->|"Hayır"| ST["STALE: durumu değiştirme"]:::wait
 SEQ -->|"Evet"| EP{"Epoch / aktif görev / alım zamanı uygun mu?"}:::decision
 EP -->|"Hayır"| ST
 EP -->|"Evet"| UPDATE["RobotStatus kopyasını güncelle<br/>Aktif sahipliği result gelene kadar koru"]:::fm
 UPDATE --> FIRST{"İlk durumda IDLE + yüksüz + atamasız mı?"}:::decision
 FIRST -->|"Hayır"| HOLD["İlk durum doğrulamasını bekle"]:::wait
 FIRST -->|"Evet"| EL["Diğer uygunluk filtrelerine geç"]:::fm
 EL --> TIME["2 sn kesinti: STALE<br/>5 sn aktif görev kesintisi: uyarı<br/>Otomatik FAILED / ERROR yok"]:::wait

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="07-dds-goal-cancel"></a>

## 07. DDS goal ve cancel protokolü

**Durum:** IMPLEMENTED. **Amaç:** Kabul, ret, belirsiz teslim ve terminal sonucu ayırmak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Kalıcı Outbox komutu; goal/cancel yanıtı | SENT, RETRY, HELD_FOR_REVIEW veya terminal olay | Goal yanıtı 5 sn, cancel yanıtı 3 sn monotonik; kabul duruş değildir. |

**Kaynak belge:** [c3-3-2-ros2-adapter-decisions-2026-10-24.md](../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md) · [c3-3-1-executor-safety-decisions-2026-10-24.md](../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md)

**Kaynak kod:** [action_client.py](../../backend/fleet_manager/adapters/action_client.py) · [outbox_sender.py](../../backend/fleet_manager/adapters/outbox_sender.py) · [event_loop.py](../../backend/fleet_manager/event_loop.py)

**Test / kanıt:** [test_ros2_action_client.py](../../tests/test_ros2_action_client.py) · [test_ros2_outbox_sender.py](../../tests/test_ros2_outbox_sender.py)

**Sınır / fark:** Yeniden teslim ikinci yürütme değildir; terminal duplicate için tekrar sonuç sunma protokolü tamamlanmış sayılmaz.

![DDS goal ve cancel protokolü](svg/dds-goal-cancel.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "07 · DDS goal ve cancel protokolü · IMPLEMENTED"
---
flowchart TD
 O[("Outbox komutu")]:::db --> SEND["ExecuteTask: sabit UUID / task / epoch / yük"]:::fm
 SEND --> RES{"Goal yanıtı?"}:::decision
 RES -->|"5 sn içinde yok"| RET["RETRY • aynı komut kimliği ve yük"]:::wait
 RET --> SEND
 RES -->|"Açık REJECT"| HOLD[("HELD_FOR_REVIEW<br/>task_review_holds")]:::db
 HOLD --> OP["Operatör incelemesi; kör reassignment yok"]:::wait
 RES -->|"ACCEPT"| AC["Goal handle + result / feedback aboneliği<br/>SENT görev tamamlandı demek değildir"]:::fm
 AC --> C["Kesme gerekiyorsa aynı goal handle ile cancel"]:::fm
 C --> CR{"Cancel yanıtı?"}:::decision
 CR -->|"3 sn içinde yok"| RT["Cancel RETRY; sahiplik korunur"]:::wait
 CR -->|"Ret"| RQ["Bekleyen HIGH kuyruğa döner"]:::fm
 CR -->|"Kabul"| WAIT["Terminal PREEMPTED ve duruş kanıtını bekle"]:::wait
 AC -->|"Result"| MATCH["Epoch / UUID uzlaştırması"]:::fm
 WAIT --> MATCH

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="08-assignment-reconciliation"></a>

## 08. Assignment epoch ve UUID uzlaştırması

**Durum:** PARTIAL. **Amaç:** Gecikmiş sonuçların yeni atamayı kapatmamasını açıklamak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Action feedback/result/cancel, aktif atama | Uygulanan olay veya STALE | robot/task/assignment_epoch/goal_uuid ve gerçek completed_epoch. |

**Kaynak belge:** [c3-3-1-executor-safety-decisions-2026-10-24.md](../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md) · [c3-3-2-ros2-adapter-decisions-2026-10-24.md](../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md)

**Kaynak kod:** [event_loop.py](../../backend/fleet_manager/event_loop.py) · [fleet_manager_core.py](../../backend/fleet_manager/domain/fleet_manager_core.py) · [action_client.py](../../backend/fleet_manager/adapters/action_client.py)

**Test / kanıt:** [test_fleet_manager_outbox.py](../../tests/test_fleet_manager_outbox.py) · [test_ros2_action_client.py](../../tests/test_ros2_action_client.py)

**Sınır / fark:** Eksik epoch dalı hedef davranış değildir; mevcut event_loop fallback’i açıkça gösterilir. Adaptör gerçek epoch gönderir, ancak consumer sınırı eksik alanı bağımsız reddetmez.

![Assignment epoch ve UUID uzlaştırması](svg/assignment-reconciliation.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "08 · Assignment epoch ve UUID uzlaştırması · PARTIAL"
---
flowchart TD
 A(["Action olayı"]):::terminal --> M{"Aktif robot + task + epoch + UUID eşleşir mi?"}:::decision
 M -->|"Hayır"| ST["STALE; sahipliği koru"]:::wait
 M -->|"Evet"| K{"Olay türü?"}:::decision
 K -->|"Feedback"| F["Sıra denetimi; ilerlemeyi işle<br/>Fiziksel durum otoritesi değişmez"]:::fm
 K -->|"Cancel yanıtı"| C["Son cancel_command_id kontrolü<br/>Kabul terminal sonuç değildir"]:::fm
 K -->|"Result"| CE{"Gerçek completed_epoch mevcut mu?"}:::decision
 CE -->|"Evet"| EQ{"Aktif epoch ile eşit mi?"}:::decision
 CE -->|"Hayır: mevcut kod"| GAP["FARK: assignment_epoch kopyalanıyor<br/>Onaylı sözleşme bunu yasaklar"]:::error
 GAP --> EQ
 EQ -->|"Hayır"| ST
 EQ -->|"Evet"| TERM["SUCCEEDED / FAILED / PREEMPTED işle<br/>Görev sonucu ve sahiplik güncelle"]:::fm

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="09-sqlite-outbox-consumer"></a>

## 09. SQLite Outbox ve tek consumer

**Durum:** IMPLEMENTED. **Amaç:** Bellek ve veritabanının atomik geçişini açıklamak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Thread-safe olaylar ve Outbox gönderim sonuçları | Commit edilmiş durum / kalıcı komut veya rollback | event_id duplicate; transaction dışında ağ; restartta boş DB zorunlu. |

**Kaynak belge:** [c3-2-sqlite-outbox.md](../design/c3-2-sqlite-outbox.md) · [c3-3-2-ros2-adapter-decisions-2026-10-24.md](../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md)

**Kaynak kod:** [event_loop.py](../../backend/fleet_manager/event_loop.py) · [store.py](../../backend/fleet_manager/persistence/store.py)

**Test / kanıt:** [test_fleet_manager_outbox.py](../../tests/test_fleet_manager_outbox.py)

**Sınır / fark:** Kuyruk bellektedir; commit öncesi olaylar süreç çökmesinde kalıcı değildir. SENT ağda exactly-once veya görev başarısı garantisi vermez.

![SQLite Outbox ve tek consumer](svg/sqlite-outbox-consumer.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "09 · SQLite Outbox ve tek consumer · IMPLEMENTED"
---
flowchart TD
 S(["Runtime başlangıcı"]):::terminal --> DB{"DB senaryo kaydı içeriyor mu?"}:::decision
 DB -->|"Evet"| RESET["ScenarioResetRequired<br/>Kanıt DB korunur; otomatik replay yok"]:::error
 DB -->|"Hayır"| Q["Callback / API üreticisi → asyncio.Queue"]:::fm
 Q --> TX[("Tek consumer: BEGIN transaction")]:::db
 TX --> DUP{"event_id işlendi mi?"}:::decision
 DUP -->|"Evet"| D(["DUPLICATE"]):::terminal
 DUP -->|"Hayır"| COPY["Domain kopyası üzerinde kimlik / sıra / olay işle"]:::fm
 COPY --> SAVE[("tasks + reservations + processed_events<br/>outbox_events + review kayıtları")]:::db
 SAVE --> OK{"COMMIT başarılı mı?"}:::decision
 OK -->|"Hayır"| R["ROLLBACK; eski bellek korunur"]:::error
 OK -->|"Evet"| PUB["Yeni bellek görünümünü yayımla"]:::fm
 PUB --> CLAIM[("OUTBOX_CLAIM: PENDING / RETRY → SENDING")]:::db
 CLAIM --> NET["Transaction dışında gönder"]:::fm
 NET --> FIN[("OUTBOX_FINISH<br/>SENT / RETRY / SUPERSEDED")]:::db
 FIN --> Q

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="10-battery-wh-integration"></a>

## 10. Wh batarya hesabı

**Durum:** PLANNED. **Amaç:** C4 fiziksel tüketim ve şarj hesabının birimlerini açıklamak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| /clock, odometri mesafesi, k Wh/m, güç W, kapasite Wh, temas | Wh, yüzde SoC ve batarya yayın alanları | Şarj için yarıçap + tam duruş + dock_contact; tüketim sürekli. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [configuration-c1.md](../configuration-c1.md)

**Kaynak kod:** Ürün uygulaması / bu akışa ait doğrulama henüz yok.

**Test / kanıt:** Ürün uygulaması / bu akışa ait doğrulama henüz yok.

**Sınır / fark:** Bağımsız Battery Simulator yoktur. /clock geri sıçrama ve kesinti ayrıntıları açık kalır; diyagram yeni timeout politikası seçmez. C3 enerji uygunluğu bu fiziksel integratör değildir.

![Wh batarya hesabı](svg/battery-wh-integration.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "10 · Wh batarya hesabı · PLANNED"
---
flowchart TD
 A(["Simülasyon örneği /clock"]):::terminal --> IN["delta_s metre; delta_t saniye<br/>Önceki enerji Wh"]:::battery
 IN --> USE["E = E − k × delta_s − P_idle × delta_t / 3600<br/>Yükleme / boşaltmada da tüketim"]:::battery
 USE --> C{"İstasyon yarıçapında + hareketsiz<br/>+ dock_contact true mu?"}:::decision
 C -->|"Evet"| CH["E = E + P_charge × delta_t / 3600"]:::battery
 C -->|"Hayır"| LIM["Enerjiyi fiziksel kapasite sınırlarında tut"]:::battery
 CH --> LIM
 LIM --> SOC["SoC = 100 × E / C_usable"]:::battery
 SOC --> PUB["battery_energy_wh / battery_soc_percent<br/>battery_capacity_wh / is_charging / battery_stamp"]:::battery
 PUB --> NEXT(["Sonraki simülasyon örneği"]):::terminal

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="11-charging-queue-selection"></a>

## 11. Şarj sırası ve istasyon seçimi

**Durum:** PLANNED. **Amaç:** Şarj talep sırasını kaynak sahipliğinden ayırmak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Düşük enerji isteği, SoC, talep zamanı, istasyonlar | Rezervasyon veya güvenli bekleme | Düşük SoC önce, eşitlikte FIFO; tek sahiplik. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf](../ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf)

**Kaynak kod:** [reservations.py](../../backend/fleet_manager/domain/reservations.py)

**Test / kanıt:** [test_fleet_manager_domain.py](../../tests/test_fleet_manager_domain.py)

**Sınır / fark:** Rezervasyon primitive’leri mevcut olsa da otomatik şarj kuyruğu/yürütücüsü yoktur. Çoklu istasyon seçimi için yeni eşitlik veya maliyet politikası belirlenmedi.

![Şarj sırası ve istasyon seçimi](svg/charging-queue-selection.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "11 · Şarj sırası ve istasyon seçimi · PLANNED"
---
flowchart TD
 A(["Şarj ihtiyacı"]):::terminal --> Q["Şarj kuyruğu: düşük SoC → FIFO"]:::fm
 Q --> FREE{"Uygun boş istasyon var mı?"}:::decision
 FREE -->|"Hayır"| W["Park / güvenli bekleme<br/>Şarj talebi bekler"]:::wait
 FREE -->|"Evet"| PICK["Sıra hakkı olan robot için<br/>uygun istasyon seç"]:::fm
 PICK --> RES{"Tek sahipli rezervasyon başarılı mı?"}:::decision
 RES -->|"Hayır"| W
 RES -->|"Evet"| NAV["Executor üzerinden istasyona git<br/>Komut sözleşmesi henüz tamamlanmadı"]:::executor
 NAV --> DOCK{"Konum + duruş + temas doğrulandı mı?"}:::decision
 DOCK -->|"Hayır"| WAIT["Teyit bekle; enerji ekleme"]:::wait
 DOCK -->|"Evet"| CH["OCCUPIED / şarj başlar"]:::battery

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="12-charging-exit-policy"></a>

## 12. Şarjdan ayrılma ve yüzde 80

**Durum:** PLANNED. **Amaç:** Görev için erken ayrılma ile yer verme politikasını ayırmak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Şarjdaki robot, görev uygunluğu, SoC, bekleyen robotlar | Görev için çıkış, yer verme veya şarjda kalma | Dinamik enerji uygunluğu %80 öncesi görev çıkışına izin verir. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf](../ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf)

**Kaynak kod:** [state_machine.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/state_machine.py)

**Test / kanıt:** Ürün uygulaması / bu akışa ait doğrulama henüz yok.

**Sınır / fark:** Mevcut Executor CHARGING durumunda taşıma goal kabul etmez; erken ayrılma orkestrasyonu uygulanmamıştır. Diyagram hedef politikadır.

![Şarjdan ayrılma ve yüzde 80](svg/charging-exit-policy.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "12 · Şarjdan ayrılma ve yüzde 80 · PLANNED"
---
flowchart TD
 A(["CHARGING"]):::terminal --> JOB{"Alınabilecek görev ve dinamik enerji yeterli mi?"}:::decision
 JOB -->|"Evet"| DEPART["Görev için ayrılma<br/>%80 altı da olabilir"]:::fm
 JOB -->|"Hayır"| SOC{"SoC ≥ %80 mi?"}:::decision
 SOC -->|"Hayır"| STAY["Şarjda kal<br/>Yer vermek için zorla çıkarma yok"]:::battery
 SOC -->|"Evet"| QUEUE{"Şarj bekleyen robot var mı?"}:::decision
 QUEUE -->|"Hayır"| FULL["%100’e kadar kalabilir"]:::battery
 QUEUE -->|"Evet"| EXIT["Park / bekleme için çıkış"]:::fm
 DEPART --> REL["RELEASING • kaynak hâlâ sahipli"]:::fm
 EXIT --> REL
 REL --> P{"Fiziksel ayrılma doğrulandı mı?"}:::decision
 P -->|"Hayır"| WAIT["FREE yapma; teyit bekle"]:::wait
 P -->|"Evet"| FREE(["Kaynak FREE"]):::terminal

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="13-parking-reservations"></a>

## 13. Park rezervasyonu ve güvenli bekleme

**Durum:** PARTIAL. **Amaç:** Görev sonrası hedef politikayı ve mevcut kaynak yaşam döngüsünü göstermek.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Görev sonucu, enerji, boş park/bekleme alanı, pose | Park/şarj yönlendirmesi veya güvenli duruş; kaynak sahipliği | Fiziksel ayrılmadan FREE yok; hata BLOCKED. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [c3-fleet-manager-decisions-2026-10-24.md](../decisions/c3-fleet-manager-decisions-2026-10-24.md) · [c3-3-3-dual-robot-integration-decisions-2026-10-24.md](../decisions/c3-3-3-dual-robot-integration-decisions-2026-10-24.md)

**Kaynak kod:** [reservations.py](../../backend/fleet_manager/domain/reservations.py) · [event_loop.py](../../backend/fleet_manager/event_loop.py)

**Test / kanıt:** [test_fleet_manager_domain.py](../../tests/test_fleet_manager_domain.py) · [test_fleet_manager_outbox.py](../../tests/test_fleet_manager_outbox.py)

**Sınır / fark:** Otomatik görev sonrası park/şarj yöneticisi yoktur. Mevcut nearest-free primitive Öklid mesafesi kullanır. `unblock()` doğrudan FREE yapar; hedef ayrılma teyidini sağlamaz ve consumer üzerinden tamamlanmış kurtarma akışı değildir.

![Park rezervasyonu ve güvenli bekleme](svg/parking-reservations.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "13 · Park rezervasyonu ve güvenli bekleme · PARTIAL"
---
flowchart TD
 A(["Görev tamam; yüksüzlük teyidi"]):::terminal --> LOW{"Enerji düşük mü? • hedef politika"}:::decision
 LOW -->|"Evet"| C["Şarj akışı • PLANNED"]:::battery
 LOW -->|"Hayır"| PARK{"Boş park var mı?"}:::decision
 PARK -->|"Hayır"| SAFE{"Güvenli bekleme alanı var mı?"}:::decision
 SAFE -->|"Hayır"| STOP["Güvenli duruş + operatör alarmı"]:::error
 PARK -->|"Evet"| RES["En yakın boş alanı tek sahipli rezerve et"]:::fm
 SAFE -->|"Evet"| RES
 RES --> OCC["Varış: OCCUPIED"]:::fm
 OCC -->|"Her öncelikte yeni görev / ayrılma"| REL["RELEASING"]:::fm
 REL --> P{"Mesafe > tolerance_radius + departure_margin?"}:::decision
 P -->|"Hayır"| WAIT["Sahipliği koru"]:::wait
 P -->|"Evet"| FREE(["FREE"]):::terminal
 OCC -->|"ERROR"| BLOCK["BLOCKED; operatör ve fiziksel teyit gerekir"]:::error

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="14-failure-operator-recovery"></a>

## 14. FAILED / ERROR ve operatör kurtarma

**Durum:** PARTIAL. **Amaç:** Kesin hata, planlama uygunsuzluğu ve iletişim belirsizliğini ayırmak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Nav2 terminal sonuç, iletişim, ClearRobotError ve odometri | FAILED/ERROR, reddedilmiş veya kabul edilmiş manuel kurtarma | expected_epoch eşit; robot ERROR; yüksüz ve güvenli duruş. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [c3-3-1-executor-safety-decisions-2026-10-24.md](../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md) · [c3-3-2-ros2-adapter-decisions-2026-10-24.md](../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md)

**Kaynak kod:** [node.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py) · [state_machine.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/state_machine.py) · [service_client.py](../../backend/fleet_manager/adapters/service_client.py) · [reservations.py](../../backend/fleet_manager/domain/reservations.py)

**Test / kanıt:** [test_clear_robot_error_client.py](../../tests/test_clear_robot_error_client.py) · [test_executor_state_machine.py](../../tests/test_executor_state_machine.py)

**Sınır / fark:** Node odometriyle denetler; saf state_machine.clear_robot_error çağrısında odometri verilmezse duruş kontrolü atlanabilir. Kaynak unblock primitive’i ayrıca fiziksel kontrol yapmaz. Bu farklar düzeltilmedi.

![FAILED / ERROR ve operatör kurtarma](svg/failure-operator-recovery.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "14 · FAILED / ERROR ve operatör kurtarma · PARTIAL"
---
flowchart TD
 A(["Hata / belirsizlik"]):::terminal --> TYPE{"Hangi aşama?"}:::decision
 TYPE -->|"Atama öncesi rota yok"| Q["Adayı ele; görev kuyrukta"]:::wait
 TYPE -->|"İletişim timeout / oturum değişimi"| W["Uyarı / güvenli blokaj<br/>Otomatik FAILED / ERROR yok"]:::wait
 TYPE -->|"Etkin taşıma terminal Nav2 hatası"| E["Executor ERROR + görev FAILED<br/>İşgal edilen kaynak BLOCKED"]:::error
 E --> OP["Operatör: ClearRobotError"]:::ui
 OP --> C{"Robot ID ve expected_epoch doğru<br/>ERROR + yüksüz + güncel güvenli duruş?"}:::decision
 C -->|"Hayır"| R["İsteği reddet"]:::error
 C -->|"Evet"| ID["Executor IDLE; epoch korunur<br/>FAILED görev yeniden başlamaz"]:::executor
 ID --> FM["FM yeni RobotStatus bekler"]:::fm
 FM --> PH["Kaynak için ayrıca fiziksel ayrılma teyidi<br/>Kurtarma orkestrasyonu eksik"]:::wait

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="15-fleet-config-lifecycle"></a>

## 15. fleet.yaml yaşam döngüsü

**Durum:** PARTIAL. **Amaç:** Mevcut doğrulama ile planlanan Apply sürecini ayırmak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Tek fleet.yaml, şema, varlık dosyaları; hedef desired_revision | Doğrulanmış config veya açık hata; planlanan running_revision | Duplicate anahtar, tip, birim, benzersizlik, dosya yolu kontrolleri. |

**Kaynak belge:** [configuration-c1.md](../configuration-c1.md) · [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [architecture-v2.3-transition.md](../architecture/architecture-v2.3-transition.md)

**Kaynak kod:** [loader.py](../../fleet_config/loader.py) · [models.py](../../fleet_config/models.py) · [builder.py](../../backend/fleet_manager/builder.py)

**Test / kanıt:** [test_config.py](../../tests/test_config.py) · [test_fleet_builder.py](../../tests/test_fleet_builder.py)

**Sınır / fark:** C1 kök stations kullanır; onay belirsizliği raporda tutulur. Builder ImportError halinde ham YAML fallback kullanır: doğrulama zinciri bütün başlangıç yollarında zorunlu değildir. Apply API ve revision runtime yoktur.

![fleet.yaml yaşam döngüsü](svg/fleet-config-lifecycle.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "15 · fleet.yaml yaşam döngüsü · PARTIAL"
---
flowchart TD
 A(["fleet.yaml"]):::terminal --> Y["YAML: duplicate / anahtar kontrolü"]:::fm
 Y --> J["JSON Schema → Pydantic semantik kontrol"]:::fm
 J --> P["Harita image / Nav2 dosyaları ve use_sim_time"]:::fm
 P --> OK{"Geçerli mi?"}:::decision
 OK -->|"Hayır"| ERR["Açık hata ile dur"]:::error
 OK -->|"Evet"| LOAD["Config'den robot / istasyon kayıtları"]:::fm
 LOAD -.->|"PLANNED: web değişikliği"| DES["desired_revision / pending_revision"]:::ui
 DES --> APPLY["POST /api/config/apply • PLANNED"]:::ui
 APPLY --> SAFE{"Aktif görev yok ve yüklü robot yok mu?"}:::decision
 SAFE -->|"Hayır"| WAIT["Apply engellenir"]:::wait
 SAFE -->|"Evet"| RESTART["Kontrollü restart + hazır olma teyidi<br/>Operasyon ayrıntıları açık"]:::fm
 RESTART --> RUN(["running_revision güncelle • PLANNED"]):::terminal

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="16-rest-websocket-gui"></a>

## 16. REST / WebSocket ve 2D panel

**Durum:** PLANNED. **Amaç:** UI ile ROS arasındaki sorumluluk ve veri yönünü açıklamak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Kullanıcı görevi, RobotStatus, harita/rota, kalıcı olaylar | Görev yanıtı, snapshot/stream/replay ve 2D görünüm | UI DDS kullanmaz; kabul yanıtı görev tamamlanması değildir. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [architecture-v2.3-transition.md](../architecture/architecture-v2.3-transition.md)

**Kaynak kod:** Ürün uygulaması / bu akışa ait doğrulama henüz yok.

**Test / kanıt:** Ürün uygulaması / bu akışa ait doğrulama henüz yok.

**Sınır / fark:** FastAPI, WebSocket ve React/Konva uygulaması yoktur. REST şema, replay cursor, bağlantı kopması ve backpressure ayrıntıları burada yeni karar olarak seçilmez. Video akışı aktarılmaz.

![REST / WebSocket ve 2D panel](svg/rest-websocket-gui.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "16 · REST / WebSocket ve 2D panel · PLANNED"
---
flowchart LR
 U["Kullanıcı / React + Konva"]:::ui -->|"HTTP görev isteği"| API["FastAPI REST"]:::ui
 API -->|"Komut olayı"| Q["FM tek consumer"]:::fm
 Q -->|"Görev kabul / kimlik"| API
 Q -->|"ExecuteTask"| EX["Robot Executor"]:::executor
 EX -->|"RobotStatus / result"| Q
 Q -->|"Kalıcı görev ve olay"| DB[("SQLite")]:::db
 Q -->|"Durum görünümü"| WS["WebSocket snapshot / stream / replay"]:::ui
 DB -.->|"Replay ayrıntısı C5'te"| WS
 WS -->|"Koordinat / durum / görev"| U
 NAV["ROS harita / rota"]:::nav -->|"Backend adaptasyonu"| WS

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="17-route-cache"></a>

## 17. Asenkron rota ve önbellek

**Durum:** PARTIAL. **Amaç:** Ağ sorgusunun consumer transaction dışında kalmasını göstermek.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Robot, start/goal, map_revision, monotonik zaman | Nav2 yol uzunluğu veya None | 0.20 m hücre, 30 sn TTL, 2 sn sorgu timeout; Euclidean fallback yok. |

**Kaynak belge:** [c3-3-2-ros2-adapter-decisions-2026-10-24.md](../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md)

**Kaynak kod:** [route_cache.py](../../backend/fleet_manager/adapters/route_cache.py) · [route_resolver.py](../../backend/fleet_manager/adapters/route_resolver.py) · [ros2_adapter_node.py](../../backend/fleet_manager/adapters/ros2_adapter_node.py)

**Test / kanıt:** [test_ros2_route_resolver.py](../../tests/test_ros2_route_resolver.py)

**Sınır / fark:** Resolver önce cache’e doğrudan yazar, ardından consumer’a olay gönderir; diyagramdaki olay yolu tek yazma yolu değildir. Cache API ve sorgu kodu mevcut; görev atama/iptal/çıkışındaki tüm invalidation tetikleyicilerinin canlı bağlantısı kanıtlanmış değildir. Boş robot_id sorgusu başka robot kaydıyla eşleşebilir; tam robot izolasyonu diye sunulmaz.

![Asenkron rota ve önbellek](svg/route-cache.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "17 · Asenkron rota ve önbellek · PARTIAL"
---
flowchart TD
 A(["Rota ihtiyacı"]):::terminal --> K["robot_id + start/goal hücreleri + map_revision"]:::fm
 K --> HIT{"Önbellek geçerli mi?<br/>TTL ≤ 30 sn; yer değiştirme ≤ 0.20 m"}:::decision
 HIT -->|"Evet"| D(["Yol uzunluğu m"]):::terminal
 HIT -->|"Hayır"| N["Consumer dışında ComputePathToPose"]:::nav
 N --> RES{"2 sn içinde geçerli sonuç?"}:::decision
 RES -->|"Hayır"| NONE["None; görev bekler; Euclidean yok"]:::wait
 RES -->|"Evet"| LEN["Path segment uzunluklarını topla"]:::nav
 LEN --> EVENT["ROUTE_RESOLVED → consumer → cache"]:::fm
 EVENT --> D
 INV["Hedef / harita / poz / görev değişimi<br/>Onaylı invalidation tetikleyicileri"]:::fm -.-> K

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

<a id="18-duplicate-restart-guard"></a>

## 18. Duplicate kayıtları ve restart engeli

**Durum:** PARTIAL. **Amaç:** Tekrar teslimin ikinci yürütme üretmemesini açıklamak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| task_id, epoch, goal UUID, değişmez yük, reset kanıtı | Tek yürütme kaydı veya ret/blokaj | Senaryo boyunca kayıt; kapasitede tahliye yok; restart otomatik replay değil. |

**Kaynak belge:** [c3-3-1-executor-safety-decisions-2026-10-24.md](../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md) · [c3-3-2-ros2-adapter-decisions-2026-10-24.md](../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md)

**Kaynak kod:** [safety.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/safety.py) · [node.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py)

**Test / kanıt:** [test_executor_safety.py](../../tests/test_executor_safety.py) · [test_executor_safety_ros2.py](../../tests/test_executor_safety_ros2.py)

**Sınır / fark:** Ürün düzeyinde operatör reset prosedürü ve terminal duplicate sonucunu yeniden sunma protokolü tamamlanmamıştır; test harness kabul açılması ürün reset API’si değildir.

![Duplicate kayıtları ve restart engeli](svg/duplicate-restart-guard.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "18 · Duplicate kayıtları ve restart engeli · PARTIAL"
---
flowchart TD
 START(["Executor süreci başlar"]):::terminal --> BLOCK["Yeni oturum UUID; kabul bloklu"]:::executor
 BLOCK --> RESET{"Kontrollü reset kanıtı var mı?"}:::decision
 RESET -->|"Hayır"| WAIT["Atama kapalı"]:::wait
 RESET -->|"Test harness kanıtı"| A["Goal kimliği ve değişmez yük"]:::executor
 A --> DUP{"Task/epoch veya UUID kaydı var mı?"}:::decision
 DUP -->|"Evet"| REJ["İkinci yürütmeyi reddet<br/>Terminal kayıtlar da korunur"]:::error
 DUP -->|"Hayır"| CAP{"Kapasite var ve kabul açık mı?"}:::decision
 CAP -->|"Hayır"| REJ
 CAP -->|"Evet"| RUN["Aktif kaydı belleğe al; bir kez yürüt"]:::executor
 RUN --> TERM{"Sonuç kimliği / yük / gerçek epoch eşleşir mi?"}:::decision
 TERM -->|"Hayır"| HOLD["Güvenli blokaj + inceleme"]:::error
 TERM -->|"Evet"| STORE["Terminal kaydı senaryo boyunca sakla"]:::executor
 STORE --> RESTART(["Restart: kayıt kaybı → yeniden reset engeli"]):::terminal

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef nav fill:#ccfbf1,stroke:#0f766e,color:#134e4a,stroke-width:1.5px;
 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef db fill:#e2e8f0,stroke:#475569,color:#0f172a,stroke-width:1.5px;
 classDef ui fill:#fce7f3,stroke:#be185d,color:#831843,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef error fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
```

</details>

## Üretim ve doğrulama

Mermaid CLI 11.12.0 ile kaynaklar SVG'ye çevrilir; bu araç ürün bağımlılığı değildir. Komutlar, görüntü denetimi ve sınırlar [doğrulama komut ekinde](../validation/organization/organization-commands-2026-10-26.md) bulunur. GitHub sunucusunda render testi yapılmadı; yerel Mermaid render ve SVG gömme kontrolü bununla karıştırılmaz.

## Eksik akışlar

C4 fiziksel batarya, şarj kuyruğu, erken ayrılma ve otomatik park orkestrasyonu; C5 REST/WS/panel; kontrollü Apply ve ürün reset prosedürü tamamlanmamıştır. Genişletilmiş iki robotlu takas MVP'de kapalıdır; onaysız yürütme algoritması çizilmedi. Küresel trafik/deadlock çözücüsü kapsam dışıdır.
