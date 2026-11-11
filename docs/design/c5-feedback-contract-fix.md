# C5 feedback alan eşlemesi

11 Kasım 2026. Aşama 1.1 kapsamında kullanıcı F1 sözleşme düzeltmesini istedi. Fiziksel durum otoritesi, sahiplik ve Outbox politikası değişmez.

`ExecuteTaskActionClientBridge`, callback bağlamından robot/task/epoch/goal UUID ve goal başına artan yerel `status_seq` üretir. ROS feedback'i faz, mesafe ve gözlemsel SoC taşır. `ActionFeedback.parse`, consumer transaction'ında bilinen alanları ve tip/aralıklarını doğrular; beklenmeyen alanlar, eksik kimlik ve geçersiz değerler loglanan hata üretir, transaction geri alınır.

Domain çağrısı robot/task/epoch/goal UUID/faz alanlarını açık eşler. `status_seq` consumer'ın aynı feedback stream'indeki eski/tekrar sıra kapısında kalır. Önce aktif task/robot/epoch/UUID bağlamı doğrulanır; terminal sonrası feedback STALE olur. Mesafe ve feedback SoC doğrulanmış gözlemlerdir; FM enerji, poz, yük veya şarj kararlarını bunlarla güncellemez. Bu veriler ürün snapshot'ına yeni yetki kaynağı olarak eklenmedi. Batarya/poz için mevcut BatteryState→RobotStatus yolu kullanılır.

Feedback IDL'si bağımsız bir feedback sıra veya alma zamanı alanı taşımaz. Yerel sıra, callback geliş sırasını ifade eder; ROS ağında üretilme sırasının veya bağımsız feedback TTL'sinin kanıtı değildir. Bu düzeltme yeni bir tazelik politikası icat etmez. Feedback RobotStatus'un iki saniyelik tazeliğini yenilemez; fiziksel durum hâlâ Executor RobotStatus'a aittir.

Consumer olay hatasını kind/robot/task/epoch/goal bağlamıyla loglar. Action adaptörü feedback ve result callback future'larının sonucunu izler; exception aynı bağlamla görünür olur. Hatalı olay APPLIED sayılmaz, otomatik retry/görev atama/terminal değişimi veya Outbox sahte tamamlama yapılmaz. Kalıcı şema ve IDL değişmedi.

[Yeni entegrasyon seçkisi](../../tests/test_feedback_pipeline.py) gerçek adapter→consumer→domain→SQLite hattını çalıştırır; test mesafe sağlayıcısı fiziksel Nav2 kanıtı sayılmaz. Canlı yeniden kabul ve test sonuçları ayrı Aşama 1.1 doğrulama kaydındadır.
