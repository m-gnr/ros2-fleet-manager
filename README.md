# ROS 2 Fleet Manager

11 Kasım fiziksel doğrulaması: odometri/footprint ve kapanış düzeltmeleri sınandı; **F2 ve paralel görev regresyonu açık, Aşama 1.2 kabul edilmedi**. [Rapor](docs/validation/c5/c5-stage1-2-physical-localization-2026-11-11.md)

Headless ROS 2 simülasyonunda çok robotlu pickup/dropoff görevlerini öncelik, rota ve enerji uygunluğuna göre yöneten; web üzerinden izleme ve kontrol hedefleyen filo yönetim projesi.

## Temel özellikler

- **Mevcut:** Tek `fleet.yaml`, şema/Pydantic doğrulaması; robot başına Executor; HIGH/MEDIUM/LOW ve atanabilir FIFO; güvenli preemption; SQLite Outbox ve ROS 2 adaptörleri.
- **Mevcut:** Robot başına batarya telemetrisi ve Nav2 enerji hesabı. Düşük SoC için şarj istasyonuna, teslimat sonrasında park veya güvenli bekleme alanına otomatik yönlendirme.
- **Mevcut:** Düşük SoC/FIFO şarj kuyruğu, fiziksel dock temasıyla şarj ve kanıtlı istasyon devri.
- **Mevcut:** C5 Aşama 1.6, salt okunur operasyon özetini, seçili robotu ve ROS TF/Path tabanlı açık 3D depoyu kompakt genel görünümde birleştirir.

- **Mevcut:** 30 × 18 m ortak depo profili, dağıtılmış pick/teslim kataloğu, costmap bindirmesi ve tek consumer’a bağlı görev oluşturma. [Doğrulama kapsamı](docs/validation/c5/warehouse-30x18-validation-2026-11-11.md)

## Mimari genel bakış

Üç servisli hedef **ONAYLANDI**; nihai üç servis dağıtımı **HENÜZ TEST EDİLMEDİ**.

```mermaid
flowchart LR
    UI["React + TypeScript + Three.js"] <-->|"HTTP / WebSocket"| API["FastAPI"]
    API -->|"Katalog görevi / yerel soket / SUBMIT_TASK"| FM
    ROS["Salt okunur TF / Path köprüsü"] --> API
    FM["Fleet Manager + SQLite"] -->|"Commit sonrası snapshot"| API
    FM <-->|"ROS 2 / DDS"| SIM["simulation: Gazebo + Nav2 / AMCL + Executor<br/>Battery Simulator ve fiziksel dock"]
```

`simulation`, robot başına bağımsız düğümleri barındırır. `backend`, görev/sahiplik kararlarını ve kalıcılığı yönetir. `frontend`, backend üzerinden telemetri ve görevleri gösterir; DDS ağına bağlanmaz.

### Mimari ve algoritmalar

[18 akışlık diyagram kataloğu](docs/diagrams/README.md), düzenlenebilir Mermaid ve SVG çıktılarıyla görev seçimi, iptal, epoch/session, Outbox, enerji, şarj/park ve panel akışlarını açıklar. Her akışın uygulama durumu ve kaynakları belirtilmiştir; [kod/karar farkları](docs/validation/organization/organization-validation-2026-10-26.md) ayrıca raporlanır.

## Kullanılan teknolojiler

Mevcut altyapı: Python, Pydantic, JSON Schema, SQLite, ROS 2 Humble/rclpy, Cyclone DDS, Nav2/AMCL, Gazebo Fortress ve Docker Compose. Python bağımlılıkları [requirements-c1.txt](requirements-c1.txt), image/build tanımları [docker/](docker/) altında tutulur. C5, FastAPI ve Vite üzerinde TypeScript, React, Three.js ve React Three Fiber kullanır.

Kayıtlı canlı deney ortamı Apple Silicon / linux-arm64 container'lardır. Diğer platformlar ayrıca doğrulama gerektirir. Headless yazılım render ve Nav2 image bağımlılıkları için [Compose kılavuzuna](docker/compose/README.md) bakın.

## Klasör yapısı

```text
backend/fleet_manager/   Domain, tek consumer, SQLite ve ROS adaptörleri
fleet_config/           Paylaşılan filo doğrulayıcı ve CLI
backend/dashboard/      Snapshot, REST/WebSocket ve katalog görev girişi
frontend/               React/TypeScript 3D operasyon paneli
fleet-visualizer/bridge Salt okunur ROS TF/Path köprüsü
ros2_ws/src/             Robot Executor ve Battery Simulator ROS 2 paketleri
interfaces/             Ürün IDL ve ayrı DDS probe test arayüzü
config/                 fleet.yaml, şema, harita ve test yapılandırmaları
docker/compose/         Doğrulama Compose katmanları
docker/                 Dockerfile ve container test araçları
scripts/                Canlı test çalıştırıcıları
tests/                  Host/ROS otomatik testleri
docs/architecture/      Mimari kayıtlar ve kaynak dizini
docs/decisions/         C2–C3.3.3 onaylı karar kayıtları
docs/design/            Ayrıntılı tasarımlar ve Outbox sözleşmesi
docs/diagrams/          Mermaid kaynakları, SVG ve kapsam kataloğu
docs/validation/        Tarihli test raporları ve komut ekleri
```

PDF'ler, kişisel notlar ve tarihsel bağlantılar korunur. Ayrıntılı belge dizini [docs/README.md](docs/README.md) altındadır.

## Kurulum ve çalıştırma

Yerel C5 paneli için [iki robotlu başlatma komutlarını](docs/validation/c5/c5-stage1-5-commands-2026-11-06.md) izleyin. Host test seçkisi [C1](requirements-c1.txt) ve [C5 test bağımlılıklarını](requirements-c5-test.txt) kullanır.

```sh
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator
python3 -m fleet_config config/fleet.yaml
python3 -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test
```

Docker/Compose kuruluysa yalnız yapılandırmayı kontrol eden, container başlatmayan komut:

```sh
DDS_TEST_PAYLOAD=organization-audit docker compose -f docker/compose/docker-compose.dds.yml config --quiet
```

Canlı simülasyon için [katman sırası ve image önkoşullarını](docker/compose/README.md) izleyin. İki robotlu C4 kabul komutları ve regresyonlar [C4.5 komut ekinde](docs/validation/c4/c4-5-commands-2026-11-06.md) bulunur.

Tek filo kaynağı [fleet.yaml](config/fleet.yaml); alanlar ve birimler [C1 belgesinde](docs/configuration-c1.md) açıklanır. 1/2/3 robot config doğrulaması canlı hot-add veya üç robot performans kanıtı değildir.

## Görev yürütme akışı

1. Fleet Manager görevi öncelik/FIFO sırasına alır; rota ve Wh uygunluğuna göre en yakın uygun robotu seçer.
2. Atama ve Outbox atomik kaydedilir. `ExecuteTask` robotun Executor'ına gönderilir.
3. Executor, Nav2 ile pickup → yükleme → dropoff → boşaltma adımlarını yürütür.
4. Battery Simulator robot başına `BatteryState` üretir. Executor ölçüm damgasını, Wh ve SoC'yi doğrulayıp `RobotStatus` ile iletir. Fleet Manager yeni atamadan önce telemetri güncelliğini denetler.
5. Fleet Manager uygun istasyon için canlı Nav2 rotasını ve Wh rezervini denetler. İstasyon rezervasyonu ile `NavigateToStation` Outbox komutu aynı transaction'da kaydedilir. Executor aynı robotun Nav2 düğümüyle hareketi yürütür.
6. `RobotStatus` fiziksel durumu bildirir. Eşleşen epoch/UUID taşıyan terminal result görevi kapatır. Güvenli preemption için Nav2 iptal terminali ve ardışık duruş kanıtı gerekir.

## Mevcut geliştirme durumu

| Aşama | Kod / uygulama | Kanıt ve sınır |
|---|---|---|
| C1 | Konfigürasyon doğrulayıcı mevcut | 1, 2, 3 robot sözleşme testleri; Apply API yok |
| C2 | Executor ve ürün IDL mevcut | Tek robot canlı simülasyon tarihsel kanıtı |
| C3–C3.3.3 | Domain, Outbox, adaptör ve iki robot test altyapısı mevcut | Tarihsel canlı rapor var; statik incelemede açık güvenlik/entegrasyon farkları bulundu |
| C4 | Tüketim, telemetri, istasyon yönlendirmesi ve fiziksel şarj | İki robotlu uçtan uca kabul ve sınırlar [C4 kontrol listesinde](docs/validation/c4/c4-acceptance-2026-11-06.md) |
| C5 Aşama 1 | Salt okunur API, WebSocket ve operasyon paneli | [Tarihsel 2D doğrulaması](docs/validation/c5/c5-stage1-validation-2026-11-06.md) |
| C5 Aşama 1.5 | Açık temalı 3D depo, TF/Path ve ayrı ürün güncelliği | [Gazebo ve Chrome doğrulaması](docs/validation/c5/c5-stage1-5-validation-2026-11-06.md) |
| C5 Aşama 1.6 | Depo öncelikli genel görünüm, kamera kadrajı ve filo kartları | [Yerleşim ve canlı kabul](docs/validation/c5/c5-stage1-6-validation-2026-11-06.md) |
| C5 dağıtılmış depo | Ortak 30 × 18 m profil, katalog görev girişi ve costmap görünümü | [11 Kasım doğrulaması ve sınırları](docs/validation/c5/warehouse-30x18-validation-2026-11-11.md) |

## Testler ve doğrulama sonuçları

6 Kasım C4.2 doğrulamasında iki robotlu Fortress koşusu, ölçümün SQLite'a kadar taşınmasını, batarya kesintisinde Outbox atamasının engellenmesini ve aynı yayıncılar döndüğünde gerçek Nav2 teslimatını doğruladı. [Test sonuçları ve kapanış kanıtı](docs/validation/c4/c4-2-validation-2026-11-06.md)

C4.3 koşularında iki gerçek Executor ayrı park ve şarj istasyonu hedeflerini tamamladı. Nav2 terminali, güncel duruş, Gazebo konumu ve SQLite Outbox kayıtları karşılaştırıldı. Gerçek HIGH preemption regresyonunda sıralı odometri duruş penceresi bağımsız gözlemciyle doğrulandı. [C4.3 doğrulama raporu ve komut eki](docs/validation/c4/c4-3-validation-2026-11-06.md)

C4.4 koşusunda iki robot aynı dock'u sırayla kullandı. Battery Simulator fiziksel temas, geçerli sahiplik, konum ve duruşla şarj uyguladı. [C4.4 doğrulama raporu](docs/validation/c4/c4-4-validation-2026-11-06.md)

C4.5, gerçek Wh ile robot bazlı atamayı, batarya kesintisini, iki robotun şarj devrini ve şarj sonrası gerçek HIGH preemption akışını birleştirdi. [C4.5 uçtan uca raporu](docs/validation/c4/c4-5-validation-2026-11-06.md)

Tarihsel kanıtlar: C2.3 tek robotta 7/7 senaryo; C3.3.3 raporunda 10/10 senaryo; B3 Retry'da 2/2 temiz koşu. AMCL kasıtlı ofset testi **1 geçti / 1 kaldı**. Bunlar küresel çarpışmasız trafik, dar koridor deadlock, 3+ robot ölçeği veya nihai üç servis dağıtımı kanıtı değildir. [Tüm kayıtlar](docs/validation/README.md).

## Yol haritası

C5’in sonraki aşamaları katalog görev girişinin Executor/Battery ile birleşik canlı kabulünü ve nihai üç servis doğrulamasını kapsar. Üçüncü robotun dinamik eklenmesi ve iki robotlu takas genişletilmiş kapsamdır.

## Dokümantasyon bağlantıları

- [Dokümantasyon haritası](docs/README.md) ve [diyagram kataloğu](docs/diagrams/README.md)
- [Nihai mimari PDF](docs/ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.pdf), [sonraki kararlar](docs/decisions/README.md) ve [mimari kaynaklar](docs/architecture/README.md)
- [Kalıcı proje bağlamı](docs/project-context.md), [AGENTS.md](AGENTS.md) ve [doğrulama kayıtları](docs/validation/README.md)

Lisans: [Apache-2.0](LICENSE).

C5 Aşama 2.0: [dinamik batarya simülasyon kontrolü](docs/design/c5-battery-simulation-control.md) varsayılan kapalıdır. [Doğrulama kapsamı ve sınırları](docs/validation/c5/battery-control-validation-2026-11-12.md) izole ROS/Chrome kontrolünü ve sentetik üçüncü robot testini ayırır.
