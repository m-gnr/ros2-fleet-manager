# C5 Aşama 2.0 — Dinamik batarya kontrolü doğrulaması

12 Kasım 2026. [Tasarım ve erişim sözleşmesi](../../design/c5-battery-simulation-control.md) · [Komut eki](battery-control-commands-2026-11-12.md) · [Ham kanıt](battery-control-2026-11-12/)

## Sonuç

Kullanıcının robot sayısından bağımsız simülasyon kontrolü talebi **ONAYLANDI** kapsamıdır. Config tabanlı envanter, namespace servisleri, kapasiteden hızlı profil, yetkili API, panel ve robot bazlı toplu sonuç uygulaması **IMPLEMENTED**. Aşağıdaki test kapsamları **DOĞRULANDI**; bu kayıt üç dock otomatik şarj veya yeni Gazebo kabulü vermez.

| Kontrol | Sonuç | Kanıt |
|---|---|---|
| Bütün host testleri | 460 geçti, 22 atlandı | [Son host koşusu](battery-control-2026-11-12/host-tests-final.log) |
| Gerçek ROS servisleri + ilgili C4 regresyonu | 51 geçti, 0 atlandı | [Cyclone DDS son koşusu](battery-control-2026-11-12/ros-tests-final.log) |
| TypeScript + Vite build | Geçti | [Build](battery-control-2026-11-12/frontend-build-final.log) |
| Chrome regresyonu + yeni panel testi | 24 geçti | [Chrome](battery-control-2026-11-12/chrome-tests-final.log) |
| Canlı iki simülatör → API → Chrome | Geçti | [Canlı sonuç](battery-control-2026-11-12/live-chrome-service-auth.log), [geri okumalar](battery-control-2026-11-12/live-chrome.json), [görüntü](battery-control-2026-11-12/live-chrome.png) |
| IDL build | Geçti | [colcon](battery-control-2026-11-12/idl-build.log) |
| Mermaid/SVG | Üretildi | [Render](battery-control-2026-11-12/diagram-render.log) |

Host atlamaları ROS/entegrasyon ortamı gerektiren testlerdir; geçiş sayısına katılmaz. ROS seçkisi yeni iki testin yanında `test_battery_ros2`, `test_c42_battery_ros2`, `test_c44_charging` ve yeni kontrol mantığını içerir. Bu seçki bütün C4/C5 Fortress kabulünün tekrarlandığı anlamına gelmez.

## Doğrulanan davranış

- Yetkili config'deki iki robot ve `/test/third` namespace'li üçüncü sentetik kayıt, aynı kontrol koduyla çözülür. Üç gerçek ROS Battery Simulator örneği üzerinde toplu yazma ve ayrı geri okuma yapılır. Üçüncü simülatör kaldırılınca yalnız onun kontrolü kapanır; diğer iki robot doğrulanmış sonuç verir.
- 40/100/350 Wh kapasite için 10 dakika hareketsiz tüketim %100 → %25, 10 dakika net şarj %25 → %80 üretir. Normal profil gerçek config katsayılarına döner. Bu deterministik enerji hesabı testidir; fiziksel kalibrasyon değildir.
- SoC sınırları, sonlu süreler, atomik robot içi doğrulama, yanlış robot ID'si, yanlış oturum, duplicate request/payload çakışması, kapasite uyumsuzluğu ve dikkate alınmayan profil yanıtı reddedilir veya doğrulanmamış sayılır.
- Toplu SoC açık onay ve güvenli test ortamı onayı olmadan başlamaz. Anahtarsız kontrol 401, yabancı Origin 403, yanlış ID 404, geçersiz girdi 422 döner. Servisler varsayılan kapalıdır; ROS servisi de her istek için anahtar doğrular; yanlış ROS anahtarı açıkça reddedilir. Kabul DDS loopback ile izole edildi.
- Kısmi servis hatası başarılı robotları gizlemez. Kayıp acknowledgement otomatik tekrar üretemez; sonuç `UNVERIFIED` olur. Her robotun gerçek uygulama yanıtı ve bağımsız geri okuması ayrı tutulur.
- Chrome fixture testinde üçüncü robot seçilir, toplu onay olmadan SoC uygulanamaz; servis geri okuması %25 iken değişmemiş gerçek telemetri %72,50 gösterilir. Komut yanıtından canlı telemetri uydurulmadığı doğrulanır. Kullanılamayan robotun tekli düğmesi kapalıdır.
- Canlı testte iki gerçek simülatörden biri %25'e ayarlanır; diğer robot >%99 kalır. Toplu profil 5/15 dakika olarak uygulandığında iki simülatörün gerçek güçleri 900/1120 W okunur; SoC ayrıca değiştirilmez. Servis logları robot, yayıncı oturumu, istek, simülasyon zamanı, önceki ve uygulanan parametreleri içerir.

## Canlı kapsam ve korunmuş çalışmalar

Canlı kontrol testi izole DDS domain'inde kontrollü `/clock`, iki gerçek Battery Simulator, gerçek FastAPI ve gerçek Chrome kullandı. GUI snapshot'ının batarya alanları gerçek BatteryState'den; fiziksel robot durumları `NO_DATA`, pozlar ve istasyonlar boştur. Bu test Fleet Manager / Executor / Gazebo uçtan uca şarj kabulü değildir.

**HENÜZ TEST EDİLMEDİ:** Bu yeni kontrol yolunun Gazebo dünyası + Fleet Manager + Executor ile tam entegrasyonu; yeni bir tam 10+10 dakika Gazebo kabulü; gerçek Gazebo üç robot; üç dock tam otomatik şarj, dar koridor, 27 istasyon taraması, tepe yük ve dayanıklılık. Üçüncü robot kanıtı yalnız sentetik config ve gerçek ROS servislerinin ölçekten bağımsız çözümlemesidir.

Mevcut C4 fiziksel dock kapısı, istasyon sahipliği, FM görev/şarj politikaları, session/epoch ve Outbox koduna yazma yolu eklenmedi. C4 regresyonu mevcut testlerle kontrol edildi; önceki tarihsel kabul sonuçları yeni koşu gibi sunulmadı.

Başlangıçta bulunan `docs/README.md` değişiklikleri, untracked PDF, `docs/reports/`, `docs/research/` korundu. Önceki uzun şarj çalışmasının `ros2-fleet-manager-c5-auto-charging` worktree'si, kanıtları ve `fleet-c5-stage2-dock6-final` container'ı değiştirilmedi veya durdurulmadı. Bu aşamanın kendi container'ı ayrı bridge/loopback/domain kullandı. Commit/push yoktur.

## İlk denemeler ve sınırlamalar

İlk sistem Python denemesi eksik bağımlılıklardan toplama hatası verdi; venv ile düzeltildi. İlk ROS komutundaki PYTHONPATH eksikliği atlamaya yol açtı; bu çıktı başarı sayılmadı. Fast DDS, eski C4 testinin kasıtlı yanlış tipli publisher'ını yaratmayı reddetti; kayıtlı C4 RMW seçimi Cyclone DDS ile test geçti. İlk probe snapshot'ındaki UUID olmayan oturum, mevcut frontend sözleşmesince reddedildi; yalnız probe düzeltildi. Son ROS servis anahtarı regresyonunun eşzamanlı koşusunda eski C4 Executor restart testi ilk BatteryState DDS beklemesinde 3 saniyelik timeout verdi (50 geçti / 1 kaldı); ayrı domain 218 koşusunda bu kez eski clock-rewind testi aynı ilk BatteryState beklemesinde kaldı (`ros-discovery-timeout.log`). C4.2 `Rig.add_source` hazırlığı yalnız publisher/subscription eşleşmesini bekliyordu; Executor alıcı graph'ındaki yayıncı node kimliğinin keşfi bağımsızdır. Fixture artık bu kimlik keşfini de bekler; test iddiaları, ürün ret koşulları ve timeout sınırı değiştirilmedi. Bu düzeltmeden sonraki ayrı domain 219 son koşusu tabloda verilmiştir. Önceki iki hata çıktısı korundu; bunlar yeni kontrol yazımının başarısı olarak sayılmadı. Ayrıntılar ve ilk çıktılar komut ekinde korunur.

Konfigürasyon değişikliği kontrollü restart ile yüklenir; canlı hot-add/Apply API bu aşamada uygulanmadı. Backend gateway ile simulation simülatörleri ayrı servislerde ortak gizli anahtarla çalışabilir; bu dağıtımın container arası yeni canlı kabulü yapılmadı. DDS özel simülasyon ağında tutulmalıdır. API anahtarı süreç/görev düzeyindedir; çok kullanıcılı hesap/rol sistemi yoktur. Denetim kayıtları ROS logudur; bu aşama ayrıca kalıcı merkezi audit veritabanı sağlamaz.
