# ROS 2 Fleet Manager

Headless ROS 2 simülasyonunda çok robotlu pickup/dropoff görevlerini öncelik, rota ve enerji uygunluğuna göre yöneten; web üzerinden izleme ve kontrol hedefleyen filo yönetim projesi.

## Temel özellikler

- **Mevcut:** Tek `fleet.yaml`, şema/Pydantic doğrulaması; robot başına Executor; HIGH/MEDIUM/LOW ve atanabilir FIFO; güvenli preemption; SQLite Outbox ve ROS 2 adaptörleri.
- **Mevcut:** Robot başına batarya telemetrisi ve Nav2 enerji hesabı. Düşük SoC için şarj istasyonuna, teslimat sonrasında park veya güvenli bekleme alanına otomatik yönlendirme.
- **Mevcut:** Düşük SoC/FIFO şarj kuyruğu, fiziksel dock temasıyla şarj ve kanıtlı istasyon devri.
- **Planlanan:** FastAPI, WebSocket ve React + Konva 2D panel C5 kapsamındadır.

## Mimari genel bakış

Üç servisli hedef **ONAYLANDI**; nihai üç servis dağıtımı **HENÜZ TEST EDİLMEDİ**.

```mermaid
flowchart LR
    UI["frontend: React + Konva • planlanan"] <-->|"HTTP / WebSocket"| API["backend: Fleet Manager + SQLite<br/>FastAPI • planlanan"]
    API <-->|"ROS 2 / DDS"| SIM["simulation: Gazebo + Nav2 / AMCL + Executor<br/>Battery Simulator • C4.2 telemetri"]
```

`simulation`, robot başına bağımsız düğümleri barındırır. `backend`, görev/sahiplik kararlarını ve kalıcılığı yönetir. `frontend`, backend üzerinden telemetri ve görevleri gösterir; DDS ağına bağlanmaz.

### Mimari ve algoritmalar

[18 akışlık diyagram kataloğu](docs/diagrams/README.md), düzenlenebilir Mermaid ve SVG çıktılarıyla görev seçimi, iptal, epoch/session, Outbox, enerji, şarj/park ve panel akışlarını açıklar. Her akışın uygulama durumu ve kaynakları belirtilmiştir; [kod/karar farkları](docs/validation/organization/organization-validation-2026-10-26.md) ayrıca raporlanır.

## Kullanılan teknolojiler

Mevcut altyapı: Python, Pydantic, JSON Schema, SQLite, ROS 2 Humble/rclpy, Cyclone DDS, Nav2/AMCL, Gazebo Fortress ve Docker Compose. Python bağımlılıkları [requirements-c1.txt](requirements-c1.txt), image/build tanımları [docker/](docker/) altında tutulur. FastAPI, React ve Konva C5 hedefidir.

Kayıtlı canlı deney ortamı Apple Silicon / linux-arm64 container'lardır. Diğer platformlar ayrıca doğrulama gerektirir. Headless yazılım render ve Nav2 image bağımlılıkları için [Compose kılavuzuna](docker/compose/README.md) bakın.

## Klasör yapısı

```text
backend/fleet_manager/   Domain, tek consumer, SQLite ve ROS adaptörleri
fleet_config/           Paylaşılan filo doğrulayıcı ve CLI
frontend/               Planlanan arayüz; henüz uygulama yok, boş dizin Git'te taşınmaz
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

Nihai uygulama Compose'u ve açılabilecek web paneli henüz yoktur. Python bağımlılıkları kurulu ortamda aşağıdaki komutlar 6 Kasım 2026'da depo kökünden çalıştırıldı.

```sh
export PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator
python3 -m fleet_config config/fleet.yaml
python3 -m pytest -q -rs tests/ ros2_ws/src/fleet_robot_executor/test
```

Docker/Compose kuruluysa yalnız yapılandırmayı kontrol eden, container başlatmayan komut:

```sh
DDS_TEST_PAYLOAD=organization-audit docker compose -f docker/compose/docker-compose.dds.yml config --quiet
```

Canlı simülasyon için [katman sırası ve image önkoşullarını](docker/compose/README.md) izleyin. C4.2 ve C2.3/C3.3.3 regresyon komutları [C4.2 komut ekinde](docs/validation/c4/c4-2-commands-2026-11-06.md) bulunur.

Tek filo kaynağı [fleet.yaml](config/fleet.yaml); alanlar ve birimler [C1 belgesinde](docs/configuration-c1.md) açıklanır. 1/2/3 robot config doğrulaması canlı hot-add veya üç robot performans kanıtı değildir.

## Görev yürütme akışı

1. Fleet Manager görevi öncelik/FIFO sırasına alır; rota ve Wh uygunluğuna göre en yakın uygun robotu seçer.
2. Atama ve Outbox atomik kaydedilir. `ExecuteTask` robotun Executor'ına gönderilir.
3. Executor, Nav2 ile pickup → yükleme → dropoff → boşaltma adımlarını yürütür.
4. Battery Simulator robot başına `BatteryState` üretir. Executor ölçüm damgasını, Wh ve SoC'yi doğrulayıp `RobotStatus` ile iletir. Fleet Manager yeni atamadan önce telemetri güncelliğini denetler.
5. Fleet Manager uygun istasyon için canlı Nav2 rotasını ve Wh rezervini denetler. İstasyon rezervasyonu ile `NavigateToStation` Outbox komutu aynı transaction'da kaydedilir. Executor aynı robotun Nav2 düğümüyle hareketi yürütür.
5. `RobotStatus` fiziksel durumu bildirir. Eşleşen epoch/UUID taşıyan terminal result görevi kapatır. İptal kabulü terminal `PREEMPTED` yerine geçmez.

## Mevcut geliştirme durumu

| Aşama | Kod / uygulama | Kanıt ve sınır |
|---|---|---|
| C1 | Konfigürasyon doğrulayıcı mevcut | 1, 2, 3 robot sözleşme testleri; Apply API yok |
| C2 | Executor ve ürün IDL mevcut | Tek robot canlı simülasyon tarihsel kanıtı |
| C3–C3.3.3 | Domain, Outbox, adaptör ve iki robot test altyapısı mevcut | Tarihsel canlı rapor var; statik incelemede açık güvenlik/entegrasyon farkları bulundu |
| C4 | C4.1 tüketim, C4.2 telemetri, C4.3 istasyon yönlendirmesi, C4.4 fiziksel şarj | İki robotlu Fortress ortamında park varışı, fiziksel dock teması, şarj ve kaynak devri doğrulandı. Bütün C4 kabulü C4.5 kapsamındadır |
| C5 | Planlanan | API, WebSocket ve frontend yok |

## Testler ve doğrulama sonuçları

6 Kasım C4.2 doğrulamasında iki robotlu Fortress koşusu, ölçümün SQLite'a kadar taşınmasını, batarya kesintisinde Outbox atamasının engellenmesini ve aynı yayıncılar döndüğünde gerçek Nav2 teslimatını doğruladı. [Test sonuçları ve kapanış kanıtı](docs/validation/c4/c4-2-validation-2026-11-06.md)

C4.3 koşularında iki gerçek Executor ayrı park ve şarj istasyonu hedeflerini tamamladı. Nav2 terminali, güncel duruş, Gazebo konumu ve SQLite Outbox kayıtları karşılaştırıldı. Gerçek HIGH preemption regresyonunda sıralı odometri duruş penceresi bağımsız gözlemciyle doğrulandı. [C4.3 doğrulama raporu ve komut eki](docs/validation/c4/c4-3-validation-2026-11-06.md)

C4.4 koşusunda iki robot aynı dock'u sırayla kullandı. Battery Simulator fiziksel temas, geçerli sahiplik, konum ve duruşla şarj uyguladı. [C4.4 doğrulama raporu](docs/validation/c4/c4-4-validation-2026-11-06.md)

Tarihsel kanıtlar: C2.3 tek robotta 7/7 senaryo; C3.3.3 raporunda 10/10 senaryo; B3 Retry'da 2/2 temiz koşu. AMCL kasıtlı ofset testi **1 geçti / 1 kaldı**. Bunlar küresel çarpışmasız trafik, dar koridor deadlock, 3+ robot ölçeği veya nihai üç servis dağıtımı kanıtı değildir. [Tüm kayıtlar](docs/validation/README.md).

## Yol haritası

C4.5 iki robotlu uçtan uca kabuldür. C5, API/panel ve nihai üç servis doğrulamasını kapsar. Üçüncü robotun dinamik eklenmesi ve iki robotlu takas genişletilmiş kapsamdır.

## Dokümantasyon bağlantıları

- [Dokümantasyon haritası](docs/README.md) ve [diyagram kataloğu](docs/diagrams/README.md)
- [Nihai mimari PDF](docs/ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.pdf), [sonraki kararlar](docs/decisions/README.md) ve [mimari kaynaklar](docs/architecture/README.md)
- [Kalıcı proje bağlamı](docs/project-context.md), [AGENTS.md](AGENTS.md) ve [doğrulama kayıtları](docs/validation/README.md)

Lisans: [Apache-2.0](LICENSE).
