# C5 Battery Control / C4 süreklilik doğrulaması

14 Kasım 2026. Kök neden: doğrulanmış `ControlBattery` `set_soc` değişimi Battery Simulator tarafından yalnız yeni SoC/Wh içeren olağan `BatteryState` olarak yayınlanıyordu. Executor'ın C4.2 ölçüm kapısı, istasyonda doğrulanmış şarj dışında Wh artışını kaynak blokajına alıyordu; Fleet Manager'ın bağımsız denetimi de aynı artışı geçersiz kılıyordu. Böylece yetkili simülasyon kontrolü sonrası gerçek sonraki örnekler reddediliyordu.

Uygulama, başarılı yetkili SoC kontrolünden sonraki tek gerçek örneğe eşlenmiş `BatteryControlApplied` ROS kanıtını ve `control_request_id` işaretini ekler. Executor kanıt yayıncısının tekil robot namespace `battery_simulator` kaynağı olduğunu doğrular; kanıt robot/oturum/istek/SoC/Wh/kapasite/revision/damga ile eşleşmeli ve iki saniyeden yeni olmalıdır. İstek kimliği bir kez kullanılır; kapasite 10.000'e ulaşınca yeni kontroller senaryo resetine kadar reddedilir. Executor'ın doğruladığı örnek kanıtı kısa ömürlü `RobotStatus` alanlarıyla FM'e aktarılır; FM robotun aktif Battery Simulator oturumu ve aynı örnekle bir kez tüketir. Sıradan `BatteryState`, yanlış/tekrarlı/eskimiş kanıt ve tutarsız SoC/Wh mevcut C4 fail-closed yolunda kalır. Yeni ölçüm kontrol sonrası normal süreklilik başlangıcıdır. Şarj eşikleri, istasyon politikası ve güvenlik qualification/HOLD değiştirilmedi. API/ROS kontrolü halen açık `FLEET_SIM_BATTERY_CONTROL=1` ve test anahtarı ister.

## Doğrulama

- `test_c42_battery_measurement.py` ve `test_c42_battery_domain.py`: 35 geçti. Birim kapsamı kanıtsız enerji artışının blokajı, birebir eşleşen bir kullanımlık kanıt, yanlış robot/oturum, stale/tekrar kanıtların reddi ve sonraki SoC düşüşüdür.
- Python `compileall`: geçti.
- Battery Control API/ROS test komutunda API testleri eksik `fastapi` host bağımlılığı nedeniyle toplanamadı; ROS test modülü `rclpy` olmadığı için atlandı. Bunlar geçiş sayılmadı.
- ROS IDL derlemesi, ROS servis entegrasyon testleri ve Gazebo/Chrome panel denemesi: HENÜZ TEST EDİLMEDİ. Host'ta `ros2` ve `colcon` yoktur. Mevcut Chrome paneli `Bağlantı kesildi`, iki robot `STALE`, batarya `Kullanılamıyor` gösterdi; panel kontrolü yapılmadı.
- Gerçek `BatteryState → Fleet Manager → Executor/Nav2 → CHARGING` sonucu bu değişiklikle doğrulanmış değildir. Bu kayıt C5-A otomatik şarj demosu kabulü değildir.
