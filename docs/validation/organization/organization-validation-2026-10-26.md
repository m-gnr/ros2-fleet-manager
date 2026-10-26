# Depo düzeni ve algoritma dokümantasyonu doğrulaması

**Tarih:** 26 Ekim 2026. **Kapsam:** Dokümantasyon düzeni, README/AGENTS güncellemesi, Mermaid/SVG ve mevcut testlerin yeniden çalıştırılması. Yeni özellik, iş mantığı, IDL, config, Compose veya mevcut test değişikliği yapılmadı. Commit/push yapılmadı.

## Kaynaklar ve korunan çalışma

[Proje bağlamı](../../project-context.md), [nihai PDF](../../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.pdf), [Revize Karar 08](../../ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf), [v2.3 geçiş kaydı](../../architecture/architecture-v2.3-transition.md), [C1](../../configuration-c1.md), [C2–C3.3.3 kararları](../../decisions/README.md), kaynak kod ve [test kayıtları](../README.md) karşılaştırıldı. PDF'ler metin çıkarımıyla incelendi; yeni PDF veya PDF dönüşüm belgesi oluşturulmadı.

Başlangıçta `docs/README.md` değişikti; C4 öncesi rapor bağlantısı eklenmişti. `docs/reports/` kullanıcıya ait izlenmeyen dosyalar içeriyordu. Bu ekleme ve raporların içeriği korundu. `docs/project-context.md`, kişisel notlar, PDF'ler ve tarihsel test komut/çıktıları değiştirilmedi.

## Eski ve yeni yapı

| Önce | Sonra | Gerekçe |
|---|---|---|
| `docs/` kökünde altı C2/C3 karar kaydı | `docs/decisions/` | Kararları tek dizinde bulmak |
| `docs/architecture.md`, `docs/architecture-v2.3-transition.md` | `docs/architecture/` | Mimari kayıtları gruplamak |
| `docs/c3-2-sqlite-outbox.md` | `docs/design/` | Uygulama sözleşmesini teknik tasarımla gruplamak |
| Diyagram kataloğu yok | `docs/diagrams/{src,svg}/` ve katalog | 16 istenen + 2 ek algoritma |
| `backend/`, `fleet_config/`, `ros2_ws/`, `interfaces/`, `tests/`, `config/`, `docker/compose/` | Aynı | Import/build/çalıştırma yollarını gereksiz değiştirmemek |
| PDF, kişisel not ve test raporları | Aynı | Kaynak ve tarihsel kanıtı korumak |

Git geçmişi yeniden yazılmadı. Taşınan Markdown içerikleri yeni dosyada korundu; eski yollar yönlendirme dosyasıdır. Rename algılama Git'in benzerlik eşleştirmesine bağlıdır; bu görev staging veya commit yapmaz.

## Taşınan dosyalar

Aşağıdaki dosyaların eski yolu `docs/<dosya adı>` idi. Eski yollar PDF, kişisel bağlam ve tarihsel bağlantılar için yönlendirme olarak korunur.

- `docs/c3-3-integration-decisions-2026-10-24.md` → [docs/decisions/c3-3-integration-decisions-2026-10-24.md](../../decisions/c3-3-integration-decisions-2026-10-24.md)
- `docs/c2-executor-decisions-2026-10-24.md` → [docs/decisions/c2-executor-decisions-2026-10-24.md](../../decisions/c2-executor-decisions-2026-10-24.md)
- `docs/c3-fleet-manager-decisions-2026-10-24.md` → [docs/decisions/c3-fleet-manager-decisions-2026-10-24.md](../../decisions/c3-fleet-manager-decisions-2026-10-24.md)
- `docs/c3-3-3-dual-robot-integration-decisions-2026-10-24.md` → [docs/decisions/c3-3-3-dual-robot-integration-decisions-2026-10-24.md](../../decisions/c3-3-3-dual-robot-integration-decisions-2026-10-24.md)
- `docs/c3-3-2-ros2-adapter-decisions-2026-10-24.md` → [docs/decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md](../../decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md)
- `docs/c3-3-1-executor-safety-decisions-2026-10-24.md` → [docs/decisions/c3-3-1-executor-safety-decisions-2026-10-24.md](../../decisions/c3-3-1-executor-safety-decisions-2026-10-24.md)
- `docs/architecture.md` → [docs/architecture/architecture.md](../../architecture/architecture.md)
- `docs/architecture-v2.3-transition.md` → [docs/architecture/architecture-v2.3-transition.md](../../architecture/architecture-v2.3-transition.md)
- `docs/c3-2-sqlite-outbox.md` → [docs/design/c3-2-sqlite-outbox.md](../../design/c3-2-sqlite-outbox.md)

## AGENTS ve README değişiklikleri

AGENTS, eski “C1/C2/FM yok” durumunu güncelledi; ayrıntıları mevcut karar belgelerine bağladı. Kişisel notları koruma, karar sorma, yasak Git işlemleri, config-driven, üç servis, preemption, fiziksel durum otoritesi, Wh ve test/dokümantasyon kuralları korundu. C3'ün 2 sn STALE / 5 sn uyarı onayı, otomatik FAILED yasağı ve C3.3 oturum/gerçek epoch/Outbox kuralları eklendi. Kullanıcının bu görevde istediği SVG çıktıları, önceki “görsel dosya ekleme” kuralının bu görevdeki açık istisnası olarak kaydedildi.

README; amaç, özellikler, mimari, teknolojiler, dizinler, doğrulanmış kontrol komutları, görev akışı, aşama durumu, testler, yol haritası ve kaynaklar çevresinde kısaltıldı. Yanlış “backend boş” ve eskimiş test sayıları kaldırıldı. Uygulama başlangıcı veya çalışan panel adresi sunulmadı.

Taşınan metinlerde göreli Markdown bağlantıları yeniden tabanlandı; kod blokları korunur. Harita yeni kanonik yollara bağlandı. Kaynak kod/Python import, Docker build context, Compose ve script yolları değiştirilmedi; ürün dosyası taşınmadığı için yol uyarlaması gerekmedi.

## Algoritma kapsamı

[Katalog](../../diagrams/README.md) 18/18 akış için amaç, girdi, çıktı, karar koşulu, kaynak belge/kod/test ve durum tablosu içerir. 18 Mermaid kaynağı ve 18 SVG üretildi. Kaynaklar İngilizce kebab-case, etiketler Türkçedir. Hata, bekleme, karar, işlem, başlangıç/bitiş ve altı bileşen kategorisi ayrıştırıldı.

Batarya, şarj kuyruğu, şarjdan çıkış ve panel **PLANNED**; config Apply, rezervasyon orkestrasyonu ve eksik güvenlik sınırları **PARTIAL** olarak gösterildi. **IMPLEMENTED** etiketi test kapsamından bağımsız olarak yalnız belirtilen kod akışının varlığını bildirir.

## Çözülmeyen kaynak ve kod farkları

Bunlar statik inceleme bulgularıdır; yeni mimari karar veya bu görevde düzeltilmiş hata değildir. İlgili kod/politika değişikliği yapılmadı. Diyagramlarda farklar açıkça işaretlendi; bu alanlarda hedefi uygulanmış kabul etmeyin.

| Konu | Kanıt / fark | Bu çalışmadaki işlem |
|---|---|---|
| İstasyon alanı | Nihai PDF bölüm 3 `fleet.stations`, bölüm 10 kök `stations`; [C1](../../configuration-c1.md) uygulama seçimini kaydeder, ayrı açık kullanıcı onayını belirtmez | Mevcut şema korundu; uygulama seçimi onay kanıtına dönüştürülmedi. Şema değişikliği gerektiren işte kullanıcı kararı gerekir |
| Eksik gerçek epoch | [event_loop.py](../../../backend/fleet_manager/event_loop.py) `_apply`: `completed_epoch` eksikse `assignment_epoch` fallback'i var; C3.3.2-DEC-05 gerçek alanı zorunlu tutar | Uzlaştırma diyagramında mevcut istisna kırmızı düğümle gösterildi |
| Fiziksel durum kopyası | [fleet_manager_core.py](../../../backend/fleet_manager/domain/fleet_manager_core.py) `_dispatch_assignment`, FM kopyasında `robot.state = STATE_EXECUTING_TASK` yazar | Onaylı Executor otoritesi korunur; bu atama işaretinin fiziksel durumla karışma riski raporlandı |
| Kaynak açma | [reservations.py](../../../backend/fleet_manager/domain/reservations.py) `unblock()` doğrudan FREE yapar; fiziksel ayrılma denetimi yok | Hedef kurtarma ile primitive farkı belirtildi; consumer üzerinden tamamlanmış unblock akışı yok |
| Tekil işgal primitive'i | Aynı dosyada `mark_occupied()` başka robotun OCCUPIED kaydını doğrudan çağrıda değiştirebilir; [consumer](../../../backend/fleet_manager/event_loop.py) OCCUPIED dalı ek sahiplik kontrolü yapar | Consumer sınırının koruması bütün doğrudan çağrılara genellenmedi |
| Enerji config bağlantısı | [builder](../../../backend/fleet_manager/builder.py) ilk şarj istasyonunu seçer; [scheduler](../../../backend/fleet_manager/domain/scheduler.py) marj/acil rezerv politikalarını enerji fonksiyonuna geçirmez | Çoklu istasyon seçimi ve tüm YAML politikalarının runtime'a taşındığı iddia edilmedi |
| Config fail-fast | Builder, import hatasında ham YAML ve bağımsız varsayılanlara döner; safe_waiting_areas kayıtlarını oluşturmaz | C1 CLI doğrulaması tüm başlangıç yollarına genellenmedi |
| Sıra doğrulama sınırı | Consumer negatif olmayan int denetler; 0 ve uint64 üst sınırını ayrıca reddetmez. Executor yayıncı guard taşmayı bloklar | Yayıncı ve consumer korumaları ayrı gösterildi |
| Rota izolasyonu | [route_cache.py](../../../backend/fleet_manager/adapters/route_cache.py) boş robot_id ile başka robot kaydını seçebilir. [route_resolver.py](../../../backend/fleet_manager/adapters/route_resolver.py) cache'e olaydan önce de yazar | Tam robot izolasyonu / yalnız consumer cache yazımı iddia edilmedi. Görev invalidation tetikleyicilerinin tam bağlantısı doğrulanmadı |
| Şarj/park | Executor durum geçişi yardımcıları var; CHARGING goal kabulü kapalı, otomatik erken çıkış/şarj kuyruğu/park orkestrasyonu yok | C4 hedef olarak gösterildi; mock batarya ürün otoritesi sayılmadı |
| Kurtarma duruş kontrolü | [state_machine.py](../../../ros2_ws/src/fleet_robot_executor/fleet_robot_executor/state_machine.py) odometri parametreleri verilmezse kontrolü atlar; ROS node vererek çağırır | ROS akışı ve doğrudan domain çağrısı ayrıldı |
| Reset ve duplicate | Güvenlik kayıtları bellekte; ürün düzeyi reset prosedürü ve terminal duplicate sonucunu geri sunma akışı tamamlanmamış | Test harness reset kanıtı ürün reset API'si olarak gösterilmedi |

Karar belgelerinin başlığındaki “henüz test edilmedi” ifadesi belge tarihindeki durumu anlatır; sonraki doğrulama raporları bu metinler yeniden yazılmadan ayrıca bağlandı. Eski mimari/Docker taslağındaki üç servisin öneri olduğu hükmü, 23 Ekim onayıyla değişmiştir; yeni bir çelişki gibi tekrar açılmadı.

### Tarihsel C3.3.3 kanıtının sınırı

[C3.3.3 raporu](../c3/c3-3-3-validation-2026-10-24.md) 10/10 bildirir. [Test çalıştırıcısında](../../../docker/simulation-c3-3-3/check.py) T05 N=2, T06 rezervasyon ve T07 tazelik kontrolleri saf domain/elle verilen veriyle yapılır; T08 yeni oturum olayı enjekte eder. Bunlar tam fiziksel restart/istasyon sürüşü senaryosu olarak sunulamaz. Bu düzenlemede canlı koşu yeniden yapılmadı ve tarihsel rapor değiştirilmedi.

## Çalıştırılan kontroller

Komutlar ve yeniden üretim ayrıntıları [komut ekindedir](organization-commands-2026-10-26.md).

| Kontrol | Sonuç / kapsam |
|---|---|
| Host pytest, `tests/` ve ROS paket test dizini | **224 passed, 19 skipped**, çıkış 0; atlamalar ROS bağımlılığı |
| Test keşfi | 242 test toplandı; modül düzeyi ROS atlamaları ayrıca var |
| Filo CLI | **VALID: 2 robots**; şema, semantik ve dosya referansları geçti |
| Compose | **10/10** belgelenmiş katman birleşimi çözümlendi; build context, Dockerfile ve bind kaynakları mevcut |
| Python | 88 izlenen Python dosyasının AST ayrıştırması geçti; seçili host paket importları geçti |
| Mermaid / SVG | **18/18** Mermaid CLI render; SVG/XML ve katalog kaynak eşliği kontrolü |
| Markdown | 66 Markdown dosyasında 638 yerel bağlantı ve 78 başlık/explicit anchor; 0 hata |
| Diff | `git diff --check`; ürün kodu/config/IDL/testler ve kişisel kaynaklarda değişiklik yok |

İlk Python yol taraması, yerel `ros2_ws/install/` içindeki container yoluna bağlı bozuk symlink'e rastladı. Üretilmiş ve Git tarafından izlenmeyen build/install çıktıları yerine izlenen kaynak dosyaları taranarak kontrol tamamlandı; yerel build çıktıları değiştirilmedi.

## Kalan doğrulama sınırları

- ROS bağımlı testler, colcon build ve canlı Gazebo/Nav2 yeniden çalıştırılmadı; host sonucu bunların yerini tutmaz. Ürün kodu değişmediğinden ağır canlı ortam başlatılmadı.
- Compose config çözümlemesi image build, container sağlığı veya canlı DDS testi değildir.
- Mermaid yerel render, SVG metin sınırları ve görüntüler kontrol edildi. GitHub sunucusunda yayın/önizleme yapılmadı; yerel görünüm ve standart Markdown/SVG gömme, GitHub canlı doğrulaması değildir.
- Dış URL'ler ve PDF iç bağlantıları taranmadı. Kullanıcının kişisel raporundaki eski yollar yönlendirmelerle çalışmaya devam eder.
- Yukarıdaki kod/karar farklarının düzeltilmesi ayrı uygulama görevidir. Bu rapor testlerin kapsamadığı güvenlik yollarını tamamlanmış ilan etmez.
