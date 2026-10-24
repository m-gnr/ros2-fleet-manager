# C3.2 SQLite Outbox ve Tek Consumer Doğrulama Raporu

**Tarih:** 24 Ekim 2026. **Durum: DOĞRULANDI** — saf Python, SQLite ve asyncio kapsamı.

Referanslar: [C3 karar kaydı](../../c3-fleet-manager-decisions-2026-10-24.md), [uygulama sözleşmesi](../../c3-2-sqlite-outbox.md), [C3.1 raporu](c3-1-validation-2026-10-24.md), [tam komut/çıktı eki](c3-2-commands-2026-10-24.md).

## Değişiklikler

- `backend/fleet_manager/persistence/`: beş tabloluk şema, yabancı anahtarlar, aktif görev tek sahipliği, transaction, JSON domain görüntüleri ve Outbox kayıtları.
- `backend/fleet_manager/event_loop.py`: tek consumer, commit sonrası bellek yayını, kalıcı duplicate/sıra denetimi, üçlü atama kimliği, soyut gönderici ve tekrar deneme.
- `backend/fleet_manager/domain/fleet_manager_core.py`: aktif ataması bulunan robotun gecikmiş IDLE telemetrisiyle ikinci kez atanmasını engelleyen filtre. Diğer C3.1 algoritmaları yeniden kullanıldı.
- `tests/test_fleet_manager_outbox.py`: 29 yeni test. Dokümantasyon haritaları ve README güncellendi; kişisel notlar, mimari kararlar ve PDF'ler değiştirilmedi.

## Sonuç ve kapsam

Ortam: macOS 26.6.2 arm64, Python 3.13.13, SQLite 3.53.1; bağımlılıklar `requirements-c1.txt` ile sağlandı.

Tam regresyon sonucu **174 geçti, 10 atlandı**, çıkış kodu **0**. Bunun 29 testi C3.2, 145 testi önceki C1–C3.1 kapsamındadır. Önceki 25 C3.1 domain testi de geçti. Test ortamı ve her testin adı komut ekinde bulunur.

| Test alanı | Kanıt |
|---|---|
| Atomiklik | Görev/robot/rezervasyon/Outbox/işlenen olay kayıtları; dört farklı tablo yazmasında enjekte edilmiş SQLite hatasıyla tüm kayıtların ve belleğin geri alınması. |
| COMMIT hatası | Ertelenmiş yabancı anahtar ihlalinde COMMIT başarısız; bellek yayımlanmadı, görev QUEUED kaldı, Outbox oluşmadı. |
| Kilit ve süreç çökmesi | İkinci SQLite bağlantısının yazma kilidi altında olay reddi ve tekrar başarısı. Ayrı Python sürecinin commit öncesi `os._exit(17)` ile kapanmasında kayıt geri alındı, `integrity_check` sonucu `ok`. |
| Duplicate/eski olay | Aynı olay kimliği, farklı kimlikli aynı terminal sonuç, task/epoch/UUID'nin her birinin uyuşmazlığı ve sonraki atamadan sonra eski sonucun gelmesi. |
| Sıralama | Status/feedback sıra numarası; eski epoch; IDLE telemetrisi terminalden önce gelince aktif atamanın korunması. |
| Preemption | İptal kabulünden sonra yeni atama yok; PREEMPTED sonrası HIGH ataması ve Outbox atomik; orijinal FIFO zamanı/sayaç korundu. Doğal tamamlanma/hata HIGH görevi mahsur bırakmadı. Eski iptal yanıtı yeni iptal isteğini kapatmadı. |
| Tekrar/gönderim | RETRY zamanına kadar sonraki komut bekledi; tekrar aynı kimliği kullandı. Gönderim consumer'ı durdurmadı. Terminalden sonra geç gönderim hatası eski komutu yeniden gönderime açmadı. Gönderici iptalinde belirsiz teslim kaydı RETRY oldu. |
| Yeniden başlatma | PENDING, SENDING, RETRY, SENT durumlarında yeniden açılan veritabanı kanıtı korudu; yeni runtime `ScenarioResetRequired` ile durdu. Aktif görev devamı veya otomatik replay yapılmadı. |
| Eşzamanlı üreticiler | 30 benzersiz görev ve 30 duplicate birlikte sunuldu; 20 eşzamanlı tick sonunda iki robotta yalnız iki atama/Outbox kaydı oluştu. Olay giriş sırası korundu; ikinci consumer reddedildi. |
| Kaynak ve iletişim | Tek sahiplik, fiziksel ayrılmaya kadar RELEASING, hata sonrası BLOCKED. İletişim kaybında uyarı logu; otomatik FAILED/ERROR yok. |

## Eksikler ve doğrulama sınırları

Atlanan 10 test ROS 2 Humble ve kurulu `fleet_interfaces` gerektirir: 3 yaşam döngüsü entegrasyon testi ve 7 ROS düğüm testi. Önceki C2 canlı simülasyon kanıtı korunur; bu koşu yeni canlı ROS başarısı değildir.

ROS 2 adaptörleri, API, frontend ve Battery Simulator geliştirilmedi. İç olay zarfında zorunlu `status_seq`, mevcut ROS mesajına eklenmedi; uçtan uca sıra eşlemesi henüz doğrulanmadı. Gönderici testleri bellek içi sahte transport kullanır. Ağda exactly-once teslim, canlı yeniden başlatma, yüksek erişilebilirlik veya nihai üç servis dağıtımı garantisi verilmez. SQLite dosyasının kalıcılığı aktif görevi otomatik sürdürme yetkisi değildir; senaryo reset politikası korunur.
