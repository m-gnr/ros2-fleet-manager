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
| 8 | Güvenlik — [Assignment epoch ve UUID uzlaştırması](#08-assignment-reconciliation) | IMPLEMENTED | [Mermaid](src/assignment-reconciliation.mmd) · [SVG](svg/assignment-reconciliation.svg) |
| 9 | Kalıcılık — [SQLite Outbox ve tek consumer](#09-sqlite-outbox-consumer) | IMPLEMENTED | [Mermaid](src/sqlite-outbox-consumer.mmd) · [SVG](svg/sqlite-outbox-consumer.svg) |
| 10 | Enerji — [Wh batarya hesabı ve telemetri](#10-battery-wh-integration) | IMPLEMENTED | [Mermaid](src/battery-wh-integration.mmd) · [SVG](svg/battery-wh-integration.svg) |
| 11 | Enerji — [Şarj sırası ve istasyon seçimi](#11-charging-queue-selection) | IMPLEMENTED | [Mermaid](src/charging-queue-selection.mmd) · [SVG](svg/charging-queue-selection.svg) |
| 12 | Enerji — [Şarjdan ayrılma ve yüzde 80](#12-charging-exit-policy) | IMPLEMENTED | [Mermaid](src/charging-exit-policy.mmd) · [SVG](svg/charging-exit-policy.svg) |
| 13 | Kaynak — [Park rezervasyonu ve güvenli bekleme](#13-parking-reservations) | IMPLEMENTED | [Mermaid](src/parking-reservations.mmd) · [SVG](svg/parking-reservations.svg) |
| 14 | Kurtarma — [FAILED / ERROR ve operatör kurtarma](#14-failure-operator-recovery) | PARTIAL | [Mermaid](src/failure-operator-recovery.mmd) · [SVG](svg/failure-operator-recovery.svg) |
| 15 | Konfigürasyon — [fleet.yaml yaşam döngüsü](#15-fleet-config-lifecycle) | PARTIAL | [Mermaid](src/fleet-config-lifecycle.mmd) · [SVG](svg/fleet-config-lifecycle.svg) |
| 16 | Panel — [REST / WebSocket ve 3D panel](#16-rest-websocket-gui) | PARTIAL | [Mermaid](src/rest-websocket-gui.mmd) · [SVG](svg/rest-websocket-gui.svg) |
| 17 | Rota — [Asenkron rota ve önbellek](#17-route-cache) | IMPLEMENTED | [Mermaid](src/route-cache.mmd) · [SVG](svg/route-cache.svg) |
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

**Sınır / fark:** Kök üç servis Compose henüz planlanandır. C3.3.3 geçici test besleyicisini kullanır. Robot başına Battery Simulator, Executor ve Fleet Manager ürün akışı [C4.5 Fortress kabulünde](../validation/c4/c4-5-validation-2026-11-06.md) çalıştırıldı. C5 salt okunur 3D yüzü [iki robotlu Chrome kabulünde](../validation/c5/c5-stage1-5-validation-2026-11-06.md) bu akışı izler.

![Sistem ve Docker mimarisi](svg/system-architecture.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "01 · Sistem ve Docker mimarisi · PARTIAL"
---
flowchart TB
 subgraph UI["frontend • PARTIAL"]
 U["React + Three.js • 3D panel"]:::ui
 end
 subgraph BACK["backend • PARTIAL"]
 API["FastAPI / WebSocket • salt okunur"]:::ui
 FM["Fleet Manager • tek consumer"]:::fm
 DB[("SQLite + Outbox")]:::db
 FM -->|"Commit sonrası snapshot"| API
 FM <-->|"Atomik kayıt"| DB
 end
 subgraph SIM["simulation • PARTIAL"]
 CFG["fleet.yaml → robot başına namespace"]:::fm
 EX["Robot Executor • fiziksel durum otoritesi"]:::executor
 NAV["Nav2 / AMCL • robot başına"]:::nav
 GZ["Gazebo headless / bridge / Map Server"]:::nav
 BAT["Battery Simulator • tüketim ve fiziksel şarj"]:::battery
 CFG --> EX
 CFG --> NAV
 CFG --> BAT
 EX -->|"NavigateToPose"| NAV
 NAV <-->|"Odometri / sensör / hız"| GZ
 GZ -->|"/clock, odometri, fiziksel poz ve temas"| BAT
 BAT -->|"BatteryState • robot başına"| EX
 end
 R["Salt okunur TF / Path köprüsü"]:::ui
 NAV -->|"Gözlemlenen plan ve TF"| R
 R -->|"Ayrı görsel veri"| API
 U <-->|"GET / Tek WebSocket"| API
 FM -->|"ExecuteTask / NavigateToStation / cancel / ClearRobotError"| EX
 FM -->|"DockLease • kayıtlı kaynak sahibi"| BAT
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
| RobotStatus, görev pozları, Nav2 rota mesafeleri, robotun batarya modeli ve filo YAML politikaları | En yakın uygun aday veya aday yok | Güncel, oturum engeli yok, yüksüz, aktif atamasız; rota ve enerji zorunlu. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [c3-fleet-manager-decisions-2026-10-24.md](../decisions/c3-fleet-manager-decisions-2026-10-24.md)

**Kaynak kod:** [scheduler.py](../../backend/fleet_manager/domain/scheduler.py) · [energy.py](../../backend/fleet_manager/domain/energy.py) · [builder.py](../../backend/fleet_manager/builder.py)

**Test / kanıt:** [test_fleet_manager_domain.py](../../tests/test_fleet_manager_domain.py) · [test_fleet_builder.py](../../tests/test_fleet_builder.py)

**Sınır / fark.** Builder güvenli kaçış hedefi olarak ilk şarj istasyonunu seçer. Çoklu istasyon erişim seçimi planlanan kapsamdır. Scheduler filo YAML'ındaki doğrulanmış acil rezervi ve güvenlik marjını robotun batarya modeli, doğrulanmış kalan Wh ve üç Nav2 rota mesafesiyle birlikte değerlendirir.

![Robot seçimi ve Wh uygunluğu](svg/robot-selection-energy.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "03 · Robot seçimi ve Wh uygunluğu · PARTIAL"
---
flowchart TD
 A(["Aday robot"]):::terminal --> F{"RobotStatus ve batarya güncel mi?<br/>Oturum açık, yüksüz ve atanabilir mi?"}:::decision
 F -->|"Hayır"| NO["Adayı ele; görevi FAILED yapma"]:::wait
 F -->|"Evet"| L["L1: robot→pickup; L2: pickup→dropoff<br/>L3: dropoff→safe_charge"]:::nav
 L --> R{"Üç rota geçerli mi?"}:::decision
 R -->|"Hayır"| NO
 R -->|"Evet"| EN["E_required = k × L1 + k × L2 + k × L3 + margin<br/>E_available = Ölçülen Wh − C × reserve/100"]:::battery
 P["Doğrulanmış filo YAML<br/>Acil rezerv (%) ve güvenlik marjı (Wh)"]:::fm --> EN
 B["Robotun batarya modeli ve doğrulanmış Wh"]:::battery --> EN
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

**Sınır / fark:** Taşıma terminalinden sonra C4.3 istasyon yönlendirmesi ayrı bir action ve sahiplik kaydı kullanır.

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

**Durum:** IMPLEMENTED. **Amaç:** Terminal duruş teyidini ve sonraki zamanlama turunda yapılan uygunluk kontrolünü göstermek.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Yeni HIGH, çalışan görev/faz/yük, sayaç, Nav2 ve odometri | PREEMPTED sonrası yeniden kuyruklama ve normal atama | Önce uygun boş robot aranır. Kurban LOW/MED, pickup öncesi, yüksüz ve sayaç < 2 olmalıdır. Sonraki tur güncel koşulları yeniden değerlendirir. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [c3-3-1-executor-safety-decisions-2026-10-24.md](../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md) · [c3-3-3-dual-robot-integration-decisions-2026-10-24.md](../decisions/c3-3-3-dual-robot-integration-decisions-2026-10-24.md)

**Kaynak kod:** [scheduler.py](../../backend/fleet_manager/domain/scheduler.py) · [event_loop.py](../../backend/fleet_manager/event_loop.py) · [node.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py) · [stop_detector.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/stop_detector.py)

**Test / kanıt:** [test_fleet_manager_domain.py](../../tests/test_fleet_manager_domain.py) · [test_executor_safety.py](../../tests/test_executor_safety.py) · [Görev 3 doğrulama kaydı](../validation/c3/c3-3-4-task-3-validation-2026-11-05.md)

**Sınır / fark:** İptal reddi ve timeout kesilme sayacını artırmaz. %15 takas kullanılmaz. Park dönüşünü kesme ayrı lojistik kuralıdır. İki iptal yolu da Nav2 terminalinden sonra aynı odometri duruş penceresini kullanır. [C4.3 duruş doğrulaması](../validation/c4/c4-3-validation-2026-11-06.md#high-preemption-kök-neden-ve-düzeltme)

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
 NAV --> T{"Monotonik sınır içinde<br/>gerçek Nav2 terminal sonucu?"}:::decision
 T -->|"SUCCEEDED"| N["Gerçek faz akışına devam<br/>PREEMPTED üretme"]:::executor
 T -->|"ABORTED"| E["FAILED / ERROR; HIGH yeniden değerlendirilir"]:::error
 T -->|"Belirsiz veya süre doldu"| B["Sahipliği tut; güvenli blokaj<br/>Geç sonuç otomatik açmaz"]:::wait
 T -->|"STATUS_CANCELED"| O{"Terminal sonrası sıralı odometri<br/>0,20 sn boyunca duruşu doğruladı mı?"}:::decision
 O -->|"Hayır"| BRAKE["Frenle ve teyit bekle"]:::wait
 BRAKE --> O
 O -->|"Evet"| R["Eşleşen terminal PREEMPTED"]:::executor
 R --> Q["Kurban sayaç +1; kurban ve HIGH<br/>orijinal created_at ile kuyrukta"]:::fm
 Q --> S["Sonraki normal zamanlama turu"]:::fm
 S --> EL{"Güvenilir oturum, güncel uygun durum,<br/>sahiplik boş, yüksüz, rota ve enerji uygun?"}:::decision
 EL -->|"Uygun aday yok"| W
 EL -->|"Uygun aday var"| NEW["Yeni epoch + UUID ve tek<br/>EXECUTE_TASK Outbox kaydı"]:::fm

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
 S -->|"Değişti veya zaten engelli"| BLOCK["SESSION_BLOCKED<br/>Telemetri ve yeni atama kilidi"]:::error
 BLOCK --> KEEP["RESERVE, OCCUPIED, RELEASE reddedilir<br/>Mevcut istasyon sahipliği korunur"]:::db
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

**Durum:** IMPLEMENTED. **Amaç:** Gecikmiş sonuçların yeni atamayı kapatmamasını açıklamak.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Action feedback/result/cancel, aktif atama | Uygulanan olay veya STALE | robot/task/assignment_epoch/goal_uuid ve gerçek completed_epoch. |

**Kaynak belge:** [c3-3-1-executor-safety-decisions-2026-10-24.md](../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md) · [c3-3-2-ros2-adapter-decisions-2026-10-24.md](../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md)

**Kaynak kod:** [event_loop.py](../../backend/fleet_manager/event_loop.py) · [fleet_manager_core.py](../../backend/fleet_manager/domain/fleet_manager_core.py) · [action_client.py](../../backend/fleet_manager/adapters/action_client.py)

**Test / kanıt:** [test_fleet_manager_outbox.py](../../tests/test_fleet_manager_outbox.py) · [test_ros2_action_client.py](../../tests/test_ros2_action_client.py)

**Sınır / fark:** Terminal sonuçta eksik, geçersiz veya uyuşmayan epoch için `STALE` kaydı ve uyarı üretilir. Görev ve kaynak sahipliği korunur.

![Assignment epoch ve UUID uzlaştırması](svg/assignment-reconciliation.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "08 · Assignment epoch ve UUID uzlaştırması · IMPLEMENTED"
---
flowchart TD
 A(["Action olayı"]):::terminal --> M{"Aktif robot + task + epoch + UUID eşleşir mi?"}:::decision
 M -->|"Hayır"| ST["STALE; sahipliği koru"]:::wait
 M -->|"Evet"| K{"Olay türü?"}:::decision
 K -->|"Feedback"| F["Sıra denetimi; ilerlemeyi işle<br/>Fiziksel durum otoritesi değişmez"]:::fm
 K -->|"Cancel yanıtı"| C["Son cancel_command_id kontrolü<br/>Kabul terminal sonuç değildir"]:::fm
 K -->|"Result"| CE{"Gerçek completed_epoch bir tam sayı ve aktif epoch ile eşit mi?"}:::decision
 CE -->|"Hayır"| LOG["Epoch uyarısını kaydet"]:::wait --> ST
 CE -->|"Evet"| TERM["SUCCEEDED / FAILED / PREEMPTED işle<br/>Görev sonucu ve sahiplik güncelle"]:::fm

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

**Durum:** IMPLEMENTED. C4.1 tüketimi, C4.2 telemetriyi ve C4.4 fiziksel şarjı uygular.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Gazebo /clock, odometri, k Wh/m, taban güç W, kapasite Wh | Kalan Wh, yüzde SoC, kapasite ve simülasyon damgası | Zaman tüketimi ileri saatte işler. Mesafe yalnız ardışık, geçerli odometri örneklerinden gelir. |

**Kaynak belge:** [Nihai mimari kararlar, bölüm 8](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md#8-battery-simulator-mimarisi-ve-hesaplama-kuralları)

**Kaynak kod:** [Batarya çekirdeği](../../ros2_ws/src/fleet_battery_simulator/fleet_battery_simulator/consumption.py) · [ROS düğümü](../../ros2_ws/src/fleet_battery_simulator/fleet_battery_simulator/node.py)

**Test / kanıt:** [C4.1 tüketim raporu](../validation/c4/c4-1-validation-2026-11-06.md) · [C4.2 entegrasyon raporu](../validation/c4/c4-2-validation-2026-11-06.md)

**Sınır / fark:** Her düğüm bir robotu izler. Geri sarmada simülatör enerjiyi korur, Executor ve Fleet Manager ise yeni atamayı senaryo resetine kadar kilitler. [C4.4 fiziksel şarjı](../validation/c4/c4-4-validation-2026-11-06.md) kısa süreli sahiplik ve temas kanıtı kullanır.

![Wh batarya hesabı](svg/battery-wh-integration.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "10 · Wh batarya hesabı ve telemetri · IMPLEMENTED"
---
flowchart TD
 O["Robot odometrisi<br/>Sıralı örnekleri beklet"]:::battery --> D
 C(["Gazebo /clock"]):::terminal --> T{"Saat nasıl değişti?"}:::decision
 T -->|"İlk örnek veya geri sarma"| R["Zaman ve odometri referansını kur<br/>Enerjiyi koru"]:::battery
 T -->|"Aynı veya geçersiz"| W(["Sonraki geçerli saat örneği"]):::terminal
 T -->|"İleri"| D["Saate yetişen odometriyi işle<br/>Kopuk veya geçersiz adımı sayma"]:::battery
 D --> DOCK{"Geçerli dock teması ve sahipliği var mı?"}:::decision
 DOCK -->|"Evet"| CH["Şarj Wh = P_charge × delta_t / 3600"]:::battery
 DOCK -->|"Hayır"| ZERO["Şarj Wh = 0"]:::battery
 CH --> E
 ZERO --> E
 E["E = sınırla(E + şarj Wh − hareket Wh − taban Wh)"]:::battery
 E --> S["SoC = 100 × E / C_usable"]:::battery
 S --> P["Robot namespace'inde BatteryState<br/>Wh, SoC, kapasite, şarj istasyonu ve ölçüm damgası"]:::battery
 R --> P
 P --> W
 P --> EX{"Executor: kaynak tek ve aynı mı?<br/>Robot, Wh, SoC ve ölçüm damgası geçerli mi?"}:::decision
 EX -->|"Evet"| RS["RobotStatus: ölçülen Wh ve SoC<br/>Özgün batarya ölçüm damgası"]:::executor
 EX -->|"Kaynak yok, belirsiz veya ölçüm eski"| NO["Ölçüm güncel değil<br/>Yeni atamaya kapalı"]:::wait
 RS --> FM["Fleet Manager: sıra, oturum ve ölçüm yaşı<br/>Rota ve güncel Wh ile uygunluk"]:::fm

 classDef battery fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:1.5px;
 classDef decision fill:#fff,stroke:#334155,color:#0f172a,stroke-width:2px;
 classDef terminal fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:2px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef wait fill:#fff7ed,stroke:#c2410c,color:#7c2d12,stroke-dasharray:5 3;
```

</details>

<a id="11-charging-queue-selection"></a>

## 11. Şarj sırası ve istasyon seçimi

**Durum:** IMPLEMENTED. Düşük SoC ve FIFO sırası ile dock sahipliğinin yönetimi.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Düşük enerji isteği, SoC, talep zamanı, istasyonlar | Rezervasyon veya güvenli bekleme | Düşük SoC önce, eşitlikte FIFO; tek sahiplik. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf](../ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf)

**Kaynak kod:** [reservations.py](../../backend/fleet_manager/domain/reservations.py)

**Test / kanıt:** [test_fleet_manager_domain.py](../../tests/test_fleet_manager_domain.py)

**Sınır / fark:** Şarj için kaynak sahibi ile damgalı fiziksel kanıt eşleşir. [C4.4 kanıtı](../validation/c4/c4-4-validation-2026-11-06.md)

![Şarj sırası ve istasyon seçimi](svg/charging-queue-selection.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "11 · Şarj sırası ve istasyon seçimi · IMPLEMENTED"
---
flowchart TD
 A(["Şarj ihtiyacı"]):::terminal --> Q["Şarj kuyruğu: düşük SoC → FIFO"]:::fm
 Q --> FREE{"Uygun boş istasyon var mı?"}:::decision
 FREE -->|"Hayır"| W["Park / güvenli bekleme<br/>Şarj talebi bekler"]:::wait
 FREE -->|"Evet"| PICK["Sıra hakkı olan robot için<br/>uygun istasyon seç"]:::fm
 PICK --> RES{"Tek sahipli rezervasyon başarılı mı?"}:::decision
 RES -->|"Hayır"| W
 RES -->|"Evet"| NAV["NavigateToStation ile istasyona git"]:::executor
 NAV --> LEASE["OCCUPIED kaydı + geçerli DockLease"]:::db
 LEASE --> DOCK{"Sahiplik, fiziksel konum,<br/>duruş ve temas geçerli mi?"}:::decision
 DOCK -->|"Hayır"| WAIT["Teyit bekle ve şarjı kapalı tut"]:::wait
 DOCK -->|"Evet"| CH["Battery Simulator şarjı başlatır"]:::battery

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

**Durum:** IMPLEMENTED. Görev için erken ayrılma ve %80 sonrası yer verme.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Şarjdaki robot, görev uygunluğu, SoC, bekleyen robotlar | Görev için çıkış, yer verme veya şarjda kalma | Dinamik enerji uygunluğu %80 öncesi görev çıkışına izin verir. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf](../ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf)

**Kaynak kod:** [state_machine.py](../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/state_machine.py)

**Test / kanıt:** [C4.4 şarj politikası ve fiziksel devir](../validation/c4/c4-4-validation-2026-11-06.md)

**Sınır / fark:** Uygun boş robotlara öncelik verilir. Fiziksel ayrılma iki güncel pozla doğrulanır.

![Şarjdan ayrılma ve yüzde 80](svg/charging-exit-policy.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "12 · Şarjdan ayrılma ve yüzde 80 · IMPLEMENTED"
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
 REL --> P{"Güncel RobotStatus ve Gazebo pozu<br/>ayrılma eşiğini aştı mı?"}:::decision
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

**Durum:** IMPLEMENTED. Görev sonrasında veya düşük SoC ile uygun istasyona yönlendirme.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| Görev sonucu, enerji, boş park/bekleme alanı, pose | Park/şarj yönlendirmesi veya güvenli duruş; kaynak sahipliği | Fiziksel ayrılmadan FREE yok; hata BLOCKED. |

**Kaynak belge:** [ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) · [c3-fleet-manager-decisions-2026-10-24.md](../decisions/c3-fleet-manager-decisions-2026-10-24.md) · [c3-3-3-dual-robot-integration-decisions-2026-10-24.md](../decisions/c3-3-3-dual-robot-integration-decisions-2026-10-24.md)

**Kaynak kod:** [station_dispatch.py](../../backend/fleet_manager/domain/station_dispatch.py) · [reservations.py](../../backend/fleet_manager/domain/reservations.py) · [event_loop.py](../../backend/fleet_manager/event_loop.py)

**Test / kanıt:** [C4.3 doğrulaması](../validation/c4/c4-3-validation-2026-11-06.md)

**Sınır / fark:** C4.3 adayları robotun Nav2 rota mesafesiyle sıralar. C4.4 şarj kuyruğunu ve fiziksel dock devrini ekler. Normal bırakma ve operatörün iç `UNBLOCK` olayı ayrı akışlardır. [Fiziksel kanıt koşulları](../design/c3-2-sqlite-outbox.md#istasyon-bırakma-ve-blocked-kurtarma)

![Park rezervasyonu ve güvenli bekleme](svg/parking-reservations.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "13 · Park rezervasyonu ve güvenli bekleme · IMPLEMENTED"
---
flowchart TD
 A(["Görev tamamlandı veya SoC düşük"]):::terminal --> F{"Güncel telemetri, yüksüz ve sahipsiz robot?"}:::decision
 F -->|"Hayır"| WAIT["Sahipliği koru veya bekle"]:::wait
 F -->|"Evet"| LOW{"YAML düşük SoC eşiğinin altında mı?"}:::decision
 LOW -->|"Evet"| C["Şarj istasyonu adayı"]:::battery
 LOW -->|"Hayır"| PARK["Park adayı"]:::fm
 C --> ROUTE
 PARK --> ROUTE
 ROUTE{"Boş hedef, Nav2 rotası ve yeterli Wh?"}:::decision
 ROUTE -->|"Hayır"| SAFE{"Uygun güvenli bekleme alanı var mı?"}:::decision
 SAFE -->|"Hayır"| STOP["Güvenli duruş + operatör alarmı"]:::error
 ROUTE -->|"Evet"| RES["Tek sahipli rezervasyon + Outbox"]:::db
 SAFE -->|"Evet"| RES
 RES --> NAV["Executor → NavigateToPose"]:::executor
 NAV --> TERM{"Eşleşen terminal ve güncel duruş?"}:::decision
 TERM -->|"Başarılı ve yarıçap içinde"| OCC["Varış: OCCUPIED"]:::fm
 TERM -->|"Güvenli park iptali"| REL
 TERM -->|"Nav2 hatası"| BLOCK
 TERM -->|"Belirsiz"| WAIT
 OCC -->|"Her öncelikte yeni görev / ayrılma"| REL["RELEASING"]:::fm
 REL --> P{"Kabul edilen RobotStatus ile mesafe<br/>> tolerance_radius + departure_margin?"}:::decision
 P -->|"Hayır"| WAIT
 P -->|"Evet"| FREE(["FREE"]):::terminal
 OCC -->|"ERROR"| BLOCK["BLOCKED · sahiplik korunur"]:::error
 REL -->|"ERROR"| BLOCK
 BLOCK --> OP["Operatör isteği · UNBLOCK"]:::ui
 OP --> PROOF{"Aynı oturumda ERROR sonrası güncel<br/>ve geçerli poz ile fiziksel ayrılma var mı?"}:::decision
 PROOF -->|"Hayır"| BLOCK
 PROOF -->|"Evet · atomik kayıt"| FREE
 SESSION["SESSION_BLOCKED<br/>Kaynak olaylarını reddet"]:::error --> WAIT

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

**Sınır / fark:** ROS node, ClearRobotError isteğinde duruşu odometriyle denetler. Saf state machine çağrısında odometri verilmezse bu kontrol atlanabilir. Kaynak kurtarma için FM ayrıca operatör isteği ve fiziksel ayrılma kanıtı arar. [İstasyon kurtarma sözleşmesi](../design/c3-2-sqlite-outbox.md#istasyon-bırakma-ve-blocked-kurtarma)

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
 FM --> PH["Operatör UNBLOCK isteği<br/>Aynı oturumda güncel fiziksel ayrılma kanıtı"]:::wait

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

## 16. REST / WebSocket ve 3D panel

**Durum:** PARTIAL. C5 Aşama 1.5 salt okunur operasyon ve 3D TF/Path izlemeyi uygular. 11 Kasım 2026 güncellemesiyle katalogdan görev girişi, yerel soket ve tek consumer bağlantısı eklenmiştir. Host API/SQLite ve Chrome kanıtı ile canlı Nav2 hareket kapsamı [30 × 18 m kaydında](../validation/c5/warehouse-30x18-validation-2026-11-11.md) ayrılır. Kök üç servis kabulü bu kayıtla genişletilmez.

| Girdiler | Çıktılar | Koşullar |
|---|---|---|
| Kabul edilmiş RobotStatus, görev ve rezervasyon kayıtları, ROS TF ve gözlemlenen Nav2 Path | Sürümlü ürün snapshot’ı ve ayrı TF/Path mesajları | Her kaynağın oturum, sıra, zaman ve koordinat çerçevesi ayrı denetlenir. |

[Entegrasyon sözleşmesi](../design/c5-3d-operations.md) kaynak sınırlarını açıklar. [Kaynak kod](../../backend/dashboard) · [Chrome/Fortress doğrulaması](../validation/c5/c5-stage1-5-validation-2026-11-06.md)

![REST / WebSocket ve 3D panel](svg/rest-websocket-gui.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "16 · REST / WebSocket ve 3D panel · PARTIAL"
---
flowchart LR
 EX["Robot Executor"]:::executor -->|"RobotStatus / terminal sonuç"| Q["FM tek consumer"]:::fm
 Q -->|"Atomik durum ve Outbox kaydı"| DB[("SQLite")]:::db
 Q -->|"Commit sonrası yetkili görünüm"| S["Sınırlı son snapshot"]:::fm
 S -->|"Özel geçici dosya"| API["FastAPI / kaynak sınırı"]:::ui
 ROS["Salt okunur TF / Path köprüsü"]:::executor -->|"Robot ID / map / gözlemlenen plan"| API
 API -->|"Tek WebSocket • ayrı ürün ve TF mesajları"| U["React + Three.js 3D paneli"]:::ui
 API -.->|"Kaynak başına süre ve oturum"| R["Yeniden eşitleme"]:::wait
 R -.-> U
 Y["Tek filo YAML / yaklaşma kataloğu"]:::fm -->|"SDF / harita / sahne"| API
 U -->|"Nokta ID seçimi / istek UUID"| W{"Origin / oturum / profil özeti geçerli mi?"}:::decision
 W -->|"Evet"| I["Yerel görev soketi"]:::ui
 I -->|"SUBMIT_TASK / aynı UUID ile retry"| Q
 W -->|"Hayır"| B["İstek reddi"]:::error

 classDef fm fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:1.5px;
 classDef executor fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:1.5px;
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

**Durum:** IMPLEMENTED. Scheduler robot kimliğini üç rota ayağında korur. Ağ sorgusu ve önbelleğe yayın ilgili COMMIT işlemlerinden sonra yapılır.

| Girdiler | Çıktılar | Karar koşulları |
|---|---|---|
| RobotStatus, görev pozları, harita revizyonu, monotonik zaman | Nav2 mesafeleri ve yeniden zamanlama | 0,20 m hücre, 30 sn TTL, 2 sn sorgu timeout. |

**Kaynak belge:** [C3.3.2 kararları](../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md) · [Outbox ve rota tasarımı](../design/c3-2-sqlite-outbox.md#canlı-nav2-rota-çözümü)

**Kaynak kod:** [route_planning.py](../../backend/fleet_manager/adapters/route_planning.py) · [route_cache.py](../../backend/fleet_manager/adapters/route_cache.py) · [route_resolver.py](../../backend/fleet_manager/adapters/route_resolver.py)

**Test / kanıt:** [Görev 5+6 doğrulama raporu](../validation/c3/c3-3-4-task-5-6-validation-2026-11-05.md)

**Sınır / fark:** Canlı harita revizyonu bildiriminin kaynağı çalışma ortamına bağlıdır. T03 bağımsız planner sondası kendi önbelleğini yönetir.

![Asenkron rota ve önbellek](svg/route-cache.svg)

<details>
<summary>Düzenlenebilir Mermaid görünümü</summary>

```mermaid
---
title: "17 · Robot bazlı canlı Nav2 rotası · IMPLEMENTED"
---
flowchart TD
 A(["Görev veya güncel telemetri"]):::terminal --> S["Adayları ve üç rota ayağını değerlendir"]:::fm
 S --> K{"Robot, başlangıç/hedef hücreleri<br/>ve harita revizyonu eşleşiyor mu?"}:::decision
 K -->|"Geçerli kayıt · TTL < 30 sn"| E{"Güncel telemetri ve Wh yeterli mi?"}:::decision
 K -->|"Eksik rota"| C["İsteği COMMIT sonrasına bırak"]:::db
 C --> Q["Robotun kendi ComputePathToPose uç noktası<br/>Robot başına tek etkin sorgu"]:::nav
 Q --> R{"2 sn içinde geçerli Path?"}:::decision
 R -->|"Hayır"| W["Adayı ele, sonraki geçişte<br/>aynı anahtar için 2 sn bekle"]:::wait
 R -->|"Evet"| V{"Olay, harita nesli ve<br/>görev/robot bağlamı güncel mi?"}:::decision
 V -->|"Hayır"| X["Eski sonucu at"]:::wait
 V -->|"Evet"| P["Olay COMMIT edildikten sonra<br/>mesafeyi önbelleğe yaz"]:::db
 P -->|"Yeniden zamanla"| S
 E -->|"Evet"| O["Atama ve ExecuteTask Outbox kaydı<br/>aynı transaction"]:::db
 E -->|"Hayır"| W2["Görev kuyrukta kalır"]:::wait

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

C4 şarj kuyruğu, erken ayrılma ve otomatik park orkestrasyonu; C5 REST/WS/panel; kontrollü Apply ve ürün reset prosedürü tamamlanmamıştır. Genişletilmiş iki robotlu takas MVP'de kapalıdır; onaysız yürütme algoritması çizilmedi. Küresel trafik/deadlock çözücüsü kapsam dışıdır.
