# Tarama, kaynak değerlendirme ve doğrulama eki

**Tarih:** 27 Ekim 2026 (Europe/Istanbul)  
**İlgili rapor:** [Gereksinim Analizi, Literatür Taraması ve Özgünlük Değerlendirmesi](gereksinim-literatur-ozgunluk-2026-10-27.md)  
**Durum:** Araştırma kaydı; yeni mimari karar veya ürün kabulü değildir.

## Yöntem ve kapsam

Hedefli, sınırlı anlatısal tarama ve kaynak kod incelemesi yapılmıştır. PRISMA uyumlu sistematik derleme, meta-analiz veya bütün açık kaynak projelerinin envanteri değildir. Sonuç sayıları, arama motoru değişkenliği nedeniyle bir yayın evreni olarak sayılmamıştır. Ana raporda 21 dış kaynak ve 10 proje kaynak grubu kullanılmıştır; bunların tamamı akademik yayın değildir. Dokuz akademik çalışmanın inceleme derinlikleri aşağıdadır.

Platformlar: genel web arama/açma aracı, SAGE, AAAI, arXiv, CMU/yazar arşivi, ScienceDirect ve MDPI yayıncı kayıtları, Crossref metadata API, resmî ROS/Nav2/Gazebo/SQLite belgeleri, GitHub API ve sabit commit kaynak dosyaları. Scopus/Web of Science abonelikli taraması yapılmadı. Rakip yazılımlar kurulmadı veya benchmark çalıştırılmadı.

Dahil etme: projenin görev, enerji, güvenlik, tutarlılık veya simülasyon sorularıyla doğrudan ilişki; doğrulanabilir kurum/yazar; okunabilir birincil kanıt. Dışlama: konu dışı optimizasyon, yalnız pazarlama, kimliği/sürümü belirsiz kaynak. Özet düzeyindeki kayıtlar ayrıntılı yöntem kanıtı sayılmadı.

## Arama sorguları

Aşağıdaki sorgular bu oturumda gerçekten kullanıldı. Sıra, tematik kümeler içindeki keşif sırasıdır; bir tarama protokolüne sonradan eklenmiş eksiksiz veri tabanı sorgusu değildir.

1. `Gerkey Mataric 2004 formal analysis taxonomy task allocation multi robot systems DOI`
2. `Korsah Stentz Dias 2013 comprehensive taxonomy multi robot task allocation DOI`
3. `Wurman D Andrea Mountz 2008 coordinating hundreds cooperative autonomous vehicles warehouses DOI`
4. `Open RMF task planner battery priority interruption documentation github`
5. `site.ri.cmu.edu Korsah comprehensive taxonomy multi robot task allocation 2013`
6. `site.open-rmf.org task battery fleet adapter`
7. `site.github.com/open-rmf/rmf_ros2 RobotUpdateHandle interrupt resume priority`
8. `site.github.com/openTCS/opentcs README license charging orders`
9. `site.ri.cmu.edu "comprehensive taxonomy" "2013"`
10. `site.science.org "Robot Operating System 2" Macenski 2022`
11. `site.arxiv.org Nav2 navigation2 dynamically reconfigurable navigation 2020`
12. `site.mdpi.com energy aware task allocation charging mobile robots review`
13. `site.opentcs.org documentation dispatcher recharge peripheral reservations`
14. `site.github.com/robotics-upo/mrta task allocation ROS2`
15. `site.github.com/inorbit-ai/ros_amr_interop interoperability free_fleet massrobotics vda5050`
16. `site.arxiv.org lifelong multi agent path finding pickup delivery Ma 2017`
17. `"A comprehensive taxonomy for multi-robot task allocation" "10.1177"`
18. `site.opentcs.org "6.8" user guide`
19. `site.mdpi.com/2218-6581/14/6/75 "Task Scheduling" authors`
20. `site.opentcs.org/docs/6/user/opentcs-users-guide.html "withdraw" "order"`
21. `site.opentcs.org/docs/6/user/opentcs-users-guide.html "dispatcher" "priority"`

## Kaynak değerlendirme notları

| Kaynak | İnceleme düzeyi ve kullanım | Sınır |
|---|---|---|
| [1] Gerkey/Matarić | Yayıncı başlık/yazar/DOI, yazar PDF’sindeki özet/giriş; MRTA sınıflaması. | Tam algoritmik yeniden türetim yapılmadı. |
| [2] Korsah vd. | CMU ve SAGE metadata/özet; bağımlılık ve ortak kısıtlar. | Tam metin abonelik sınırı; yalnız özetin desteklediği çıkarım. |
| [3] Wurman vd. | AAAI 2007 yazar metni ve 2008 AI Magazine atıf kaydı ayrıştırıldı. | Endüstriyel ölçek sonuçları bu projeye taşınmadı. |
| [4] Ma vd. | Yazar PDF’si özet/giriş; MAPD ve trafik ayrımı. | DOI doğrulanamadı; uydurulmadı. |
| [5] ROS 2 makalesi | arXiv v1 özet, yazar listesi, dergi DOI ve bibliyografya. | Vaka performansı yeniden ölçülmedi. |
| [6] Marathon 2 | arXiv v2 özet, yazar listesi ve IROS DOI. | Nav2’nin tüm sürümleri/eklentileri incelenmedi. |
| [7] Bagchi vd. | Yayıncı arama metni/özet ve Crossref; 2024 tarih/yazar/DOI. | Tam deney tablosu incelenmedi; performans sayısı alınmadı. |
| [8] Tomy vd. | Yayıncı arama metni/özet ve Crossref; şarj çizelgeleme bağlamı. | Doğrudan açmada 403; tam metin okundu denmedi. |
| [9] Chang vd. | 2026 yayıncı arama metni ve Crossref başlık/yazar/tarih/DOI. | Doğrudan açmada 429; kendi bataryasını şarj eden depo robotuyla aynı problem değil. |
| [10] RMF root | Sabit commit README ve paket kapsamı. | Tek release kurulumunun tüm bileşenleri sınanmadı. |
| [11] rmf_task | TaskPlanner.hpp, test_TaskPlanner.cpp, LICENSE.md okundu. | Test kodu okundu; çalıştırılmadı. |
| [12] rmf_ros2 | RobotUpdateHandle.hpp ve lisans; interrupt, cancel, reassign, park rezervasyonu. | Aynı N=2/fiziksel iptal politikası bulundu denmedi. |
| [13] rmf-web | README, api-server README, lisans; dashboard, DB ve test açıklaması. | DB kaydı, robot komut Outbox garantisi sayılmadı. |
| [14] openTCS kaynak | README.adoc, users-guide-02_howtos.adoc, dağıtım MIT lisansı ve test dosya ağacı. | Diğer lisanslı varlıklar için MIT genellemesi yapılmadı. |
| [15] openTCS 6.7.0 | Resmî kılavuzun indekslenmiş bölümleri: model, block, park/şarj ve istemciler. | Web açmada timeout; main commit ile aynı sürüm değil. |
| [16] Nav2 Humble | İki action IDL, README/lisans; plan ve yürütme ayrımı. | Docking/diğer eklentiler kapsamlı incelenmedi. |
| [17] ROS Actions | Resmî tasarım: cancel, result, goal, feedback ayrımı. | Fiziksel duruşu garanti eden uygulama standardı değil. |
| [18] QoS | Humble RST resmî GitHub kaynağı okundu. | docs.ros.org Anubis erişim engeli verdi. |
| [19] Outbox | Örüntünün yazarına ait teknik tanım. | Hakemli robotik deney değil. |
| [20] SQLite | Resmî atomik commit açıklaması. | Robot ve ağla dağıtık atomiklik iddiası yok. |
| [21] Gazebo Fortress | Resmî belge giriş ve kapsamı. | Bu araştırmada yeni canlı simülasyon koşusu yok. |
| [22]–[30] proje belgeleri | Kaynak önceliğiyle karar/tasarım/doğrulama ve diyagram kataloğu. | Tarihsel uygulama durumları güncel kabul edilmedi. |
| [31] mevcut depo | Domain, consumer, builder, persistence, adapters, Executor, config, IDL ve ilgili testler. | Tüm olası yürütme yollarının biçimsel doğrulaması değil. |

### Taramada görülüp ana karşılaştırmaya alınmayan adaylar

- `inorbit-ai/ros_amr_interop`: ROS 2 birlikte çalışabilirlik adaptörü; tam filo zamanlayıcısı ile aynı ürün kategorisi olmadığından ayrıntılı matrise alınmadı. Ücretli InOrbit platformunun bütün yetenekleri açık kaynak depoya atfedilmedi.
- “Task Scheduling with Mobile Robots—A Systematic Literature Review” (2025): keşifte görüldü; yazar/metin denetimi tamamlanmadığından raporun kanıt kaynağına eklenmedi.
- “Energy-Aware Task Allocation for Teams of Multi-Mode Robots” (2025), “A Resilient and Energy-Aware Task Allocation Framework for Heterogeneous Multirobot Systems” ve 2026 enerji dengesi makalesi: keşif adayları; ilgili fakat farklı robot modelleri veya sınırlı erişim nedeniyle esas sentezde kullanılmadı.
- `robotics-upo/mrta` sorgusu doğrulanmış ek bir uygulama girdisine dönüşmedi; bulunamama sonucu olarak kullanılmadı.
- `open-rmf/rmf_web` yanlış adresi 404 verdi; doğru depo `open-rmf/rmf-web` ile inceleme sürdürüldü.

## Sabitlenmiş yazılım görüntüleri

GitHub API üzerinden branch commit kimliği ve kaynak ağacı okundu. Aşağıdaki tarihler commit tarihidir; erişim tarihi 27 Ekim 2026’dır. Main sürümlerindeki özellikler Humble sürümüne geriye doğru atfedilmemiştir.

| Depo | Dal | Tam commit | Commit tarihi (UTC) |
|---|---|---|---|
| open-rmf/rmf | main | [146c053b61bc6d8db77ed37f6bb6a4a7d448f12f](https://github.com/open-rmf/rmf/tree/146c053b61bc6d8db77ed37f6bb6a4a7d448f12f) | 2026-08-25T01:22:22Z |
| open-rmf/rmf_task | main | [79a276d44f69be6639bdf4e03b1d39536268d63c](https://github.com/open-rmf/rmf_task/tree/79a276d44f69be6639bdf4e03b1d39536268d63c) | 2026-10-12T03:37:02Z |
| open-rmf/rmf_ros2 | main | [b892a9a4b80e3abf7d4616b21dd57cfe98a31749](https://github.com/open-rmf/rmf_ros2/tree/b892a9a4b80e3abf7d4616b21dd57cfe98a31749) | 2026-10-12T03:35:57Z |
| open-rmf/rmf-web | main | [7aa50a43ae4968dc8d8084b2505616a6a278198a](https://github.com/open-rmf/rmf-web/tree/7aa50a43ae4968dc8d8084b2505616a6a278198a) | 2026-10-21T03:54:23Z |
| openTCS/opentcs | master | [742b0e6df9ccbabc660e585a85e55d585c0642fc](https://github.com/openTCS/opentcs/tree/742b0e6df9ccbabc660e585a85e55d585c0642fc) | 2026-09-17T07:14:31Z |
| ros-navigation/navigation2 | humble | [3c3db59d6969d8ecee8e68468693d006397f4a0c](https://github.com/ros-navigation/navigation2/tree/3c3db59d6969d8ecee8e68468693d006397f4a0c) | 2026-06-03T13:53:10Z |
| ros2/ros2_documentation | humble | [c32643f08f68eb3cddf8955d91494157e4afac22](https://github.com/ros2/ros2_documentation/tree/c32643f08f68eb3cddf8955d91494157e4afac22) | 2026-10-26T21:07:51Z |

## Kaynak dosyası konumları

- rmf_task: `rmf_task/include/rmf_task/TaskPlanner.hpp`, `rmf_task/test/unit/agv/test_TaskPlanner.cpp`, `LICENSE.md`.
- rmf_ros2: `rmf_fleet_adapter/include/rmf_fleet_adapter/agv/RobotUpdateHandle.hpp`, `LICENSE.md`.
- rmf-web: `README.md`, `packages/api-server/README.md`, `LICENSE.md`.
- openTCS: `README.adoc`, `opentcs-documentation/src/docs/asciidoc/users-guide-02_howtos.adoc`, `src/main/dist/LICENSE.txt`; test ağacında `opentcs-commadapter-loopback/.../VelocityControllerTest.java` ve HTTP handler testleri görüldü. Test gövdelerinin tamamı incelenmedi.
- navigation2: `nav2_msgs/action/ComputePathToPose.action`, `nav2_msgs/action/NavigateToPose.action`, README ve lisans.
- ros2_documentation: `source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst`.

## Yerel inceleme ve çalıştırılan kontroller

Komutlar depo kökünden çalıştırıldı. HEAD: `63b8075456d56e49e8899ff26545da8e6b4ae86f`. Başlangıçta `docs/README.md` değişikti; `docs/reports/` altında mevcut kişisel raporlar vardı. Bunlar üzerine yazılmadı. Ürün kodu/config/test/IDL/Compose değişikliği, commit veya push yapılmadı.

### Host testi — 27 Ekim 2026, yeni koşu

```bash
PYTHONPATH=.:./backend:./ros2_ws/src/fleet_robot_executor uv run --python 3.12 --with pytest --with pytest-asyncio --with jsonschema --with pyyaml --with pydantic pytest -q tests/ ros2_ws/src/fleet_robot_executor/test/
```

Sonuç: **224 passed, 19 skipped in 3.75s**, çıkış kodu 0. Bu komut geçici uv ortamı kullanır; bağımlılık sürümlerini sabitlemez. Bu nedenle mevcut koşu kanıtıdır, bütün makinelerde bit düzeyinde tekrar üretim garantisi değildir. ROS bağımlı testler atlandı; canlı DDS/Gazebo veya colcon yeniden çalıştırılmadı. Pytest süre değeri performans benchmark’ı değildir.

### Config kontrolü — 27 Ekim 2026, yeni koşu

```bash
PYTHONPATH=. uv run --python 3.12 --with jsonschema --with pyyaml --with pydantic python -m fleet_config config/fleet.yaml
```

Sonuç: **VALID: 2 robots; schema, semantic and file reference checks passed**, çıkış kodu 0. Bu sonuç Apply API, image build veya canlı hot-add kanıtı değildir.

### Tarihsel koşuların ayrımı

C2.3, C3.3.1–C3.3.3 ve AMCL sayıları önceki kayıtlarından alınmıştır; yeni test sayılmamıştır. AMCL ofset sonucu 1 geçti / 1 kaldı olarak korunur. C3.3.3 `check.py` içinde T02/T04 önbellek beslemesi, T05/T06 domain testi, T07 sentetik zaman, T08 olay enjeksiyonu yeniden incelenmiştir. T01–T09 numaraları Karar 08, C3.1 ve C3.3.3 arasında eşdeğer kabul edilmemiştir.

### Yeniden görülen kod/karar farkları

- `event_loop.py:197–199`: gerçek completed_epoch eksikse assignment_epoch fallback’i.
- `fleet_manager_core.py:417`: FM kopyasında state yazımı.
- `scheduler.py`: enerji çağrısına policy marj/acil rezerv değerleri iletilmiyor.
- `builder.py`: ilk şarj istasyonu; ImportError altında ham YAML/varsayılanlar; safe_waiting kayıtlarının oluşturulmaması.
- `reservations.py`: doğrudan unblock ve mark_occupied çağrıları; consumer korumasıyla aynı güvence değil.
- `event_loop.py`: sıra için negatif olmayan int kontrolü; 0 ve uint64 üst sınırı bütünleşik doğrulanmıyor.
- `safety.py`: senaryo belleği ve reset kanıtı sınırı; ürün reset API’si değil.

Bunlar statik bulgulardır; bu görevde yeni hata üretim testi eklenmedi veya ürün kodu düzeltilmedi. `stations` çelişkisi de karara bağlanmadı.

## Belge üretim ve kalite kontrolü

Markdown tek içerik kaynağı olarak PDF’ye dönüştürüldü. ReportLab, gömülü Arial fontları, A4, başlık/altbilgi, tıklanabilir atıflar ve tekrarlanan tablo başlıkları kullanıldı. Yeni PDF için kullanıcı açık izin verdi; mevcut PDF’ler korunmuştur. Araştırma kapsamını aşan yeni diyagram eklenmedi; mevcut Mermaid/SVG kataloğuna atıf yapıldı.

Son kontrol sonuçları aşağıdaki kalite kaydında tutulur. Kaynak metadata JSON’u düzenlenebilir bir kaynak listesidir, tam metin arşivi değildir.

## Son kalite kaydı

- PDF: **24 sayfa**, A4; gövde 10.4 punto, tablo metni 9.2 punto. Türkçe karakterleri içeren Arial fontları gömülü.
- Poppler `pdftoppm -r 90 -png` ile 24 sayfanın tamamı render edilip altı temas sayfasında görsel incelendi; yoğun gereksinim sayfası ayrıca tam boyutta kontrol edildi. İlk üretimdeki tek satırlık 25. sayfa taşması giderildi. Son düzenlemede değişen yöntem, sonuç ve izlenebilirlik sayfaları yeniden render edilip kontrol edildi.
- PDF metin/geometri denetimi: **24 sayfa, 408 tıklanabilir bağlantı, 0 sayfa sınırı taşması, 0 replacement karakteri**. Bu otomatik kontroller görsel kontrolün yerine kullanılmadı.
- Atıf denetimi: **31/31 kaynak kimliği tanımlı**, G01–G24 mevcut, tanımsız numaralı atıf yok. Rapor ve ekteki yerel dosya/klasör bağlantılarında **0 eksik hedef**.
- Dış bağlantıların 21’ine HTTP kontrolü yapıldı: **15 HTTP 200**, [1], [2], [7], [9] için 403; [8] ve [15] için yerel TLS doğrulama hatası. Web araştırmasındaki ek erişim sınırlamaları (403/429/timeout) yukarıda belirtilmiştir. Bu altı adres “tam erişim doğrulandı” sayılmadı; DOI/yayıncı indeksleri ve resmî kaynak alternatifleriyle kimlikleri kontrol edildi. Güvenlik doğrulaması kapatılmadı.
- Dış web bağlantıları paylaşılabilir; PDF’deki proje içi bağlantılar bu çalışma makinesinin depo konumuna gider. Başka makinede proje kaynaklarına erişmek için göreli bağlantıları koruyan Markdown sürümü ve depo birlikte kullanılmalıdır.
- `git diff --check`: geçti. İzlenen değişiklik yalnız docs/README.md’ye yeni rapor bağlantısı eklenmesidir; önceden var olan C4 rapor bağlantısı korunmuştur. Yeni rapor dosyaları docs/reports/ altındadır. Ürün kodu, config, test, IDL, Compose, kişisel raporlar ve mevcut PDF’ler değiştirilmedi; commit/push yapılmadı.

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
