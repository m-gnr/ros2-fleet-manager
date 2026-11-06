# C5 / Aşama 1 — Salt okunur operasyon paneli

Taban C4.5 kabul commit'i `32e23fc`. React/TypeScript/Vite/Konva ve FastAPI/WebSocket, [onaylı üç servisli mimarinin](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) C5 okuma yüzüdür. Bağımsız Visualizer ayrı dalda kalır.

## Yetkili kaynaklar

| Alan | Kaynak ve güvenilirlik |
|---|---|
| Robotun fiziksel durumu | FleetEventLoop'un session, sıra ve epoch kontrollerinden geçen, başarılı transaction sonrası görülen Executor RobotStatus. FM atamayı hazırlarken kendi kaydındaki durum alanını değiştirebildiği için fiziksel durum bu tahminden türetilmez. |
| Son poz | Doğrulanmış ve damgalı RobotStatus pozu. Yalnız ortak `map` çerçevesi ve sonlu koordinatlar çizilir. Geçersiz örnekte son doğrulanmış poz saklanır ve bayat işaretlenir. Başlangıç pozu ölçüm değildir. |
| Batarya | Battery Simulator → Executor RobotStatus → FleetTracker. C4'ün `has_fresh_battery` kontrolü, mevcut monotonik saat ve korumalı ROS simülasyon saatiyle kullanılır. Geçersiz SoC ve Wh boş taşınır. Ölçüm damgası simülasyon zamanıdır. |
| Görev | Commit edilmiş domain görev kuyruğu, bekleyen preemption, aktif ve terminal kayıtlar, review hold. SQLiteStore aynı koleksiyonları aynı transaction içinde saklar. Robot kartında taşıma sahipliği aktif domain kaydından gelir. |
| İstasyon | Commit edilmiş ReservationManager kaydı ve config'den doğrulanan istasyon pozu. Şarj kanıtı için geçerli C4 ölçümü ve doğrulanmış istasyon sahipliği birlikte kullanılır. Fiziksel boşluk pozdan hesaplanmaz. Anlık yetkili şarj sırası yayınlanmadığından sıralama sunulmaz. |

## Süreç ve saat sınırları

Ürün consumer'ı ve SQLite yazarı tektir. Okuma adaptörü isteğe bağlı etkinleşir. Consumer kabul edilmiş son RobotStatus kanıtını ve son geçerli harita örneğini robot başına birer kayıtla tutar. Örnekleyici yalnız consumer'ın kendi asyncio döngüsünde commit edilmiş çekirdek referansını, kanıt kopyasını ve saatleri alır. Önceki çekirdek nesli sonraki transaction sırasında değişmez. Görüntüleme dönüşümü ve seri yazım çalışan thread'de yapılır. Örnekleyici SQL sorgusu, yeni Scheduler, ROS bağlantısı veya HTTP geri çağrısı açmaz.

Tek son snapshot özel geçici dizinde atomik dosya değişimiyle yayınlanır. FastAPI ayrı süreçte, aynı çekirdek monotonik saat alanında okur. Dosya senaryo veritabanından ayrı, geçici ve boyut sınırlıdır. Web sunucusunun ve tarayıcının kapanışı consumer'a iletilmez. Kaynak süreci durursa veya dosya eskiyse GET geçici olarak kullanılamaz, WebSocket yeniden senkronizasyon ister. Web süreci yeniden başlarsa yalnız geçerli ve yeni snapshot yüklenir. FM yeniden başlarsa eski fiziksel durum veya görev sahipliği dosyadan geri yüklenmez. Mevcut senaryo reset kuralı geçerlidir.

Tarayıcı bağlantıyı ve veri güvenilirliğini ayrı izler. Bağlantı kaybında son konum korunur, güncel SoC/Wh ve şarj bilgisi gizlenir. Görev ve rezervasyon satırları son senkronizasyondan kalan kayıtlar olarak görünür. Yeni tam snapshot geldiğinde eski oturumun ekran önbelleği değiştirilir.

## İşletim ve sınırlamalar

[API ve güvenilirlik sözleşmesi](c5-readonly-api.md) süreç sınırlarını tamamlar. [Arayüz ve koordinat dönüşümü](c5-dashboard-ui.md) ölçümün ekrana nasıl taşındığını açıklar. [Çalıştırma ve doğrulama komutları](../validation/c5/c5-stage1-commands-2026-11-06.md) iki robotlu C4.5 kabul katmanını kullanır.

Bu aşamada doğrulama düzeneği simulation ve backend konteynerlerini, ayrı FastAPI sürecini ve host üzerindeki Vite sunumunu çalıştırır. Nihai ürün Compose dağıtımı ve üretim web sunumu ayrı aşamalardır. SQLite dosyası mevcut senaryo kurallarını izler. Canlı FM yeniden başlatma veya geçmişten fiziksel sahiplik kurtarma kapsam dışıdır.
