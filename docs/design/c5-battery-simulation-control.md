# C5 Aşama 2.0 — Dinamik batarya simülasyon kontrolü

12 Kasım 2026. Kullanıcının bu aşamadaki açık talimatı **ONAYLANDI** kapsamıdır. Uygulama ve test durumu [doğrulama raporunda](../validation/c5/battery-control-validation-2026-11-12.md) ayrı tutulur. Bu belge C4 enerji/şarj politikasını değiştirmez.

## Envanter ve sorumluluk

API, Fleet Manager ile aynı `--fleet` dosyasından doğrulanan `FleetConfig.robots` envanterini kullanır. ID, namespace ve model kapasitesi buradan çözülür; frontend kendi robot listesi üretmez. Her kayıt için servis ve BatteryState yayıncısının tekilliği, mesajın robot ID'si, yayıncı oturumu, son alımın monotonik yaşı (en fazla 2 saniye) ve Wh/SoC tutarlılığı denetlenir. Yanlış kapasite veya belirsiz servis/publisher kontrolü kapatır. Kontrol ROS servisi de kendi robot ID'sini ve beklenen oturumu doğrular.

`/<configured_namespace>/sim/control_battery`, **tek** `fleet_interfaces/srv/ControlBattery` servisidir. Önerilen iki ayrı yazma servisi yerine birleştirilmesi, aynı robota SoC ve profil değişikliğinin tek callback içinde tamamen doğrulanmasını sağlar. Hiçbir yazma bayrağı olmayan istek gerçek simülatör durumunu okur. Yanıt robot, yayıncı oturumu, istek ID'si, revision, uygulanan SoC/Wh/kapasite, mod, süre ve etkin katsayıları içerir. Anahtar yanıta, fingerprint veya audit loguna eklenmez. Servis adı robot ID'sinden varsayılmaz; config namespace'i kullanılır.

Yeni robot, mevcut config sözleşmesindeki robot/model kaydı ve o robota ait Battery Simulator örneğiyle desteklenir. Yeni envanter kontrollü config/restart yaşam döngüsünde yüklenir; çalışan config dosyasını değiştirerek otomatik hot-add veya Apply API sağlanmaz. Envanterden çıkarma da bu yaşam döngüsünü izler. Çalışan simülatörün kaybolması ise tazelik/servis denetimiyle kontrolü kapatır.

Fleet Manager domain durumu, görev, dock lease, rezervasyon, session/epoch ve SQLite Outbox'a bu yol üzerinden yazılmaz. BatteryState mevcut C4 yoluyla ilerler. SoC düşürmek doğal ürün politikalarını tetikleyebilir; GUI bunu bir görev ya da şarj komutu olarak uygulamaz.

## Profil ve birimler

Normal mod simülatörün başlangıçtaki gerçek `BatteryModel` kopyasını geri yükler; model config'i değiştirilmez. Hızlı modda kapasite `C` (Wh), tükenme `T_d` (dakika), şarj `T_c` (dakika):

- `P_idle = C × 0.75 × 60 / T_d` W.
- `P_charge = P_idle + C × 0.55 × 60 / T_c` W.
- `k` (Wh/m) gerçek modeldeki hareket katsayısı olarak korunur; `k × delta_s` ayrıca tüketilir.

Şarj entegrasyonu bekleme tüketimini de çıkardığı için net %25 → %80 hedefinde `P_idle` telafisi gereklidir. Varsayılan 10/10 dakika, hareketsiz robotta %100 → %25 ve geçerli şarj koşullarında %25 → %80 için 600'er simülasyon saniyesidir. Saat kaynağı mevcut `/clock` akışıdır; duvar saati enerji entegrasyonuna katılmaz. Fiziksel dock, yarıçap, duruş, sahiplik ve güncel kanıt kapısı korunur; yalnız profil seçmek şarj başlatmaz.

SoC sonlu `[0,100]`, süreler sonlu `[1,1440]` dakika, etkin güç en fazla 1 MW kabul edilir. Sayısal süreler ve 5/10/15/30 dakika önerileri desteklenir. Bir robot için bütün alanlar doğrulanmadan hiçbir alan değiştirilmez. `%25`, `%80`, acil rezerv ve görev enerji politikaları düzenlenemez. Katsayılar kalibrasyon iddiası taşımaz.

## Ağ ve erişim

Ürün başlangıcında API uçları ve ROS kontrol servisi yoktur. Etkinleştirme için API ve simülatör süreçlerinde açık `FLEET_SIM_BATTERY_CONTROL=1` gerekir. API gateway ve her Battery Simulator aynı en az 32 karakterli `FLEET_SIM_BATTERY_TOKEN` anahtarını ister. ROS servisinin okuma ve yazma istekleri de bu anahtarla doğrulanır; yanlış anahtarda enerji/profil döndürülmez. Böylece backend ve simulation sorumlulukları ayrı servislerde kalabilir. DDS özel simülasyon ağıyla sınırlandırılmalıdır; anahtar düz ROS servis yükündedir, şifreli DDS taşımasının yerine geçmez. Bu kabul ortamı ek ağ izolasyonu için `ROS_LOCALHOST_ONLY=1` kullanır; kontrol açık kodda ortak network namespace zorunluluğu yoktur.

API aynı gizli `FLEET_SIM_BATTERY_TOKEN` ile HTTP erişimini de doğrular. `GET/POST /api/sim/batteries` Bearer doğrulaması kullanır; POST mevcut tam loopback browser Origin'i ve JSON ister. Token bundle/config/repo içine konmaz; GUI'de yalnız bileşen belleğinde tutulur. Host bind loopback'tir; kabul container'ındaki açık bind yalnız host loopback port eşlemesiyle kullanılır. Bu mekanizma genel ağ veya fiziksel robot kontrolü için yetkilendirme sistemi değildir.

POST en fazla 32 KiB alır; bilinmeyen alanları reddeder. Süreçleri etkinleştirmek yetkili test ortamının kurulmasıdır; her komutta ayrıca güvenli test ortamı onayı bulunur. Toplu SoC için ayrı `confirm_bulk_soc=true` gerekir. GUI'de SoC yazımı ayrıca işaretlenir; profil değiştirmek kendiliğinden SoC sıçratmaz.

## Toplu uygulama ve sonuç

Hedefler sunucudaki yetkili envanterden alınır. İstemcinin seçtiği tek robot veya bütün envanter desteklenir; istemci keyfi toplu robot listesi gönderemez. İstemci her hedefin gördüğü yayıncı oturumunu gönderir; değişen oturum işlemi reddettirir. Robot başına kilit vardır, robotlar birbirinden bağımsız uygulanır. Kayıp servis diğerlerini engellemez.

Her robot için servis uygunluğu/telemetri denetlenir, yazma yapılır, ardından ayrı servis okuması alınır. Uygulama yanıtının istenen SoC/profil ile eşleşmesi ve son okumanın robot/oturum/revision/katsayı eşleşmesi doğrulanır. Geri okunan gerçek SoC/Wh raporlanır; zaman akarken enerji değişebileceğinden iki okumada aynı SoC zorlanmaz.

Yanıt `atomic=false` ve robot başına `VERIFIED`, `REJECTED` veya `UNVERIFIED` içerir. Timeout/kayıp yanıt uygulamanın gerçekleşmediğini kanıtlamaz; otomatik retry veya rollback yoktur. Her ROS çağrısı en fazla 2 saniye bekler. Bir robotun başarısızlığı diğerinin doğrulanmış sonucunu gizlemez. `all_verified` yalnız bütün hedefler doğrulanmışsa true olur.

Simülatör, mutasyonları robot/oturum/istek/simülasyon zamanı/önceki ve uygulanan parametreler ile `BATTERY_CONTROL` olarak loglar; retleri ayrıca kaydeder. Denetim loglarının saklanması çalıştırıcının sorumluluğudur. Senaryo boyunca en fazla 10.000 değişiklik isteğinin fingerprint'i bellekte saklanır; kapasite dolunca yeni yazımlar reddedilir. Aynı istek ID'si ve aynı payload SoC'yi yeniden sıfırlamaz; farklı payload reddedilir. Restart önceki kontrol isteklerini replay etmez.

## Arayüz ve sınır

İstasyonlar / Şarj görünümündeki panel robot seçimi, canlı Wh/SoC ve tazelik, istenen SoC slider/hazır değerler, normal/hızlı profil, süreler, onaylar ve tekli/toplu uygulama içerir. Erişim anahtarı olmadan envanter açılmaz. Seçili robotun servisi veya telemetrisi kullanılamıyorsa tekli kontrol kapanır. Toplu deneme kullanılabilir robotları uygulayıp kapalı robotları ayrı raporlayabilir.

Servis son okuması, uygulama sonucu ve canlı BatteryState ayrı alanlardır. Komut yanıtı React filo telemetrisine yazılmaz. Gerçek telemetri gelmeden istenen SoC canlı veri gibi gösterilmez. WebSocket koparsa canlı alan maskelenir. Robot başına servis/iş mantığı React bileşeninde değil gateway ve kontrol katmanındadır.

[Mermaid kaynak](../diagrams/src/battery-simulation-control.mmd) · [SVG](../diagrams/svg/battery-simulation-control.svg)
