# Battery Simulator kapanış düzeltmesi

Önce: `SignalHandlerOptions.NO`, varsayılan Python SIGINT (KeyboardInterrupt), SIGTERM için kontrollü handler yok; `rclpy.spin` global executor'ı; sonra node destruction/context shutdown.

Bağımsız 30 canlı deneme: 23 SIGINT temiz, 7 SIGTERM -15. Orijinal `_take_subscription RuntimeError` yeniden üretilemedi. Aynı eski traceback'i çözüldü olarak sınıflandırmak için yeterli kanıt yoktur.

Sonra: SIGINT/SIGTERM yalnız durma bayrağı koyar; sahip olunan SingleThreadedExecutor en çok 0,2 s bekleme ile döner, mevcut callback tamamlanır; executor shutdown → node destruction → context shutdown → eski signal handler'ları geri yükleme. Abonelik/yükleme/şarj kararları değişmez; RuntimeError bastırılmaz.

Beklenen etki: SIGTERM'in temiz kapanması ve native take sırasında asenkron Python exception enjeksiyonunun kaldırılması. Yan etki: sinyalden sonra mevcut callback ve bir spin süresi beklenebilir; kilitlenen callback için yeni zorunlu kill politikası eklenmedi. Geri dönüş: yalnız node.py kapanış diff'ini geri alma. Önce/sonra 30 canlı sinyal denemesi ve ROS regresyonu gereklidir. İlk F4 traceback kök nedeni BELİRSİZ kalır.
