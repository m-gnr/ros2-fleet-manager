# C4 kabul kontrol listesi

6 Kasım 2026. Bu liste C4 ürün yolu ve iki robotlu Fortress kabulü içindir. [C4.5 sonuç raporu](c4-5-validation-2026-11-06.md)

**C4 TAMAMLANDI.** Son iki kabul tekrarı, önceki aşamaların regresyonları ve kapanış kontrolleri geçti.

| Kritik kontrol | Durum | Kanıt |
|---|---|---|
| Robot başına hareket ve bekleme tüketimi | GEÇTİ | C4.1 odometri ve Gazebo saati. C4.5 park ve taşıma boyunca ayrı Wh ölçümü. |
| Tek batarya otoritesi | GEÇTİ | Her robot namespace'inde bir gerçek Battery Simulator. C4.5 grafiğinde geçici besleyici yok. |
| BatteryState → RobotStatus → SQLite | GEÇTİ | C4.2 ve C4.5 damga, Wh ve SoC eşleşmesi. |
| Güncel Wh, Nav2 rotası ve rezerv ile görev ataması | GEÇTİ | C4.5 enerji profili. Ölçülen farklı Wh aynı görev için iki ayrı uygunluk sonucu verdi. |
| Otomatik şarj yönlendirmesi | GEÇTİ | C4.3 ve C4.5 gerçek Nav2 dock yaklaşımı. |
| Güvenli park ve bekleme | GEÇTİ | C4.3 ve C4.5 canlı park. Uygun güvenli bekleme ve alan yokluğu için odaklı domain testleri. |
| Fiziksel dock teması ve şarj | GEÇTİ | C4.4 ve C4.5 gerçek DART çarpışma çiftleri, damgalı dünya pozu, duruş ve lease. |
| Düşük SoC/FIFO şarj kuyruğu | GEÇTİ | C4.4 odaklı FIFO testi ve C4.5 düşük SoC önceliğiyle fiziksel devir. |
| %80/%100 ve görev için erken ayrılma | GEÇTİ | Canlı %80 devir ve %100 kalma. Dinamik enerjiyle %80 öncesi çıkış ve zorla çıkarmama için C4.4 odaklı testler. |
| İstasyonun fiziksel ayrılma ve devri | GEÇTİ | C4.4 ve C4.5 iki poz kanıtı ile 0,35 m sınırı. |
| Öncelik ve güvenli preemption | GEÇTİ | C4.3 bağımsız duruş kanıtı, C3.3.3 regresyonu, C4.5 MEDIUM teslimatı ve şarj sonrası HIGH/LOW etkileşimi. |
| Stale veri, oturum ve iletişim güvenliği | GEÇTİ | C4.5 gerçek batarya yayın kesintisi, C3.3.3 T07/T08 ve C4.4 lease, duplicate, epoch ve SESSION_BLOCKED testleri. |
| SQLite ve Outbox bütünlüğü | GEÇTİ | C4.3/C4.4 COMMIT geri alma. C4.5 ayrı veritabanları, tekil mantıksal komut ve geç terminal reddi. |
| Nav2 kararlılığı | GEÇTİ | Son C4.5 canlı profilleri, C3.3.3 ve HIGH regresyonu. |
| Docker ve ROS temiz kapanış | GEÇTİ | Backend/simulation 0/0, `OOMKilled=false`, lifecycle ve supervisor kapanış kayıtları. |
| İki robotlu uçtan uca kabul | GEÇTİ | İki bağımsız kabul tekrarı. Her tekrar enerji ve şarj profili için ayrı temiz dünya, SQLite ve log kullandı. |

| C4 dışı veya genişletilmiş kapsam | Durum |
|---|---|
| Nihai üç servisli dağıtım, FastAPI, WebSocket, React/Konva ve config Apply | HENÜZ DOĞRULANMADI |
| 3+ robot, uzun süre dayanıklılık ve tepe yük | HENÜZ DOĞRULANMADI |
| Fiziksel batarya ve dock elektroniği kalibrasyonu | HENÜZ DOĞRULANMADI |
