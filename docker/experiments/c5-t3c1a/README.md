# C5-T3C-1A — Ayrı native işçi, tek sıfır yazıcı

Yalnız açık deney fixture'ı. Varsayılan launcher/GUI tarafından yüklenmez.
Nonzero, rearm, rollover, hold/resume ve fiziksel release API'si yoktur.
[Sonuç ve sınırlar](../../../docs/validation/c5/c5-t3c1a-native-worker-2026-11-19.md).

- `worker.cc`, mevcut B6B.7 `AuthorizedZero` ve B6B.5 `Lease` sınıflarını
  değiştirmeden ayrı süreçte kullanır. FM zarfı/ACK imzası ve tam body korunur.
  ACK yalnız native doğrulamasıdır; işçi artık açıkça
  `NATIVE_VERIFIER_PROCESS` olarak etiketlenir. Joint readback/sağlık uydurmaz.
- Aynı `DiffDrive.cc`, yalnız `C5_SPLIT_ZERO_ONLY` build'inde `Veto` kullanır.
  JSON/HMAC, işçi mutex'i, transport callback'i veya bloklayan yayın son
  fizik yazıcısında bulunmaz. Her PreUpdate hedefi kesin sıfırdır.
  Mevcut teker odometrisi aynı joint konumlarından hesaplanır; yayını işçiye
  taşınır. İşçi kaybı odometriyi de keser; sağlık bağlantısı 1B'ye açıktır.
- Supervisor config'deki robotlardan `SOCK_SEQPACKET|SOCK_NONBLOCK`
  socketpair'leri üretir. Gazebo boot token'ı, gerçek `SCM_CREDENTIALS`
  PID/UID'si, native receiver session, context/body hash ve ilerleyen sıra
  birlikte denetlenir. Anahtar/provision fizik yazıcısına verilmez.
- Alıcı fizik callback'inde adım başına en çok bir sabit boyutlu kayıt okur.
  Bilet ve komut lease'i kendi monotonik saatindedir; kaynak saati çıkarılmaz.
  İlerleyen report tek başına komut lease'ini yenilemez. Yeni komut sırası
  gerekir. Geç/bozuk/yanlış bağlam, EOF ve timeout kapalı kilit üretir.
- İlk permit/context öncesi `NO_COMMAND`, mevcut Lease gibi hareket lease'i
  değildir. Soğuk render'ın süresini aştığı ilk **gözlem** biletleri atılır;
  eski ACTIVE kaydı kabul edilmez. Context bağlandıktan sonra timeout
  kilidi kalıcıdır. Bu ayrım STALE/lease süresini değiştirmez.
- Kilit sonrası gözlem/odometri akışı sürebilir; hiçbir yanıt `live` veya
  kabul sayısını yeniden yükseltmez. Supervisor otomatik restart yapmaz.
- Ayrı `split-recorder`, fizik tarafının nonblocking trace kanalını okur.
  PreUpdate seçimi ve gerçek PostUpdate joint/gövde hızı ayrı alanlardır.
  Recorder kaybı yetki üretmez; kaybolan kanıt güvenlik başarısı sayılmaz.
- `physics.cc` tek stock Physics nesnesine Configure/Update yönlendirir;
  tamamlanan pozitif-dt, unpaused çağrıyı sayar. Engine algoritmasını
  değiştirmez; ikinci Physics veya joint writer değildir. Yüklü DART/stock
  Physics/native mapping'leri ve gerçek fizik hızları ayrıca kaydedilir.

`world.py` mevcut T3A dünyası/TF/Nav2/bridge supervision'ını kullanır;
`split-server` yalnız bu açık testte FD'leri taşıyan aynı Fortress Server
API'sini çalıştırır. Ek Compose servisi veya trafik otoritesi oluşturulmaz.
Fixture, kontrollü restart negatif testi için işçi endpoint'inin bir
kopyasını supervisor'da tutar. Bu güvenilen test rolüdür; aynı UID/root'a
karşı OS izolasyonu kalifiye değildir. Gerçek yeni PID yine son yazıcıya
kabul ettirilemez. Retained endpoint nedeniyle kill/IPC kaybı EOF yerine
deadline ile algılanabilir; gerçek EOF ayrıca native testte sınanır.

Build: depo kökünden `bash docker/experiments/c5-t3c1a/build.sh YENI_DIZIN`.
Doğrulanmış izole koşu komutu ve domain/build eşlemeleri sonuç raporundadır.
`live.py` yalnız yeni DB/session/reset ve güncel readiness ile gerçek T3A
FM/Executor görevini kullanır, Scheduler'ın gerçek atamasını izler.
`*-worker-fault.json` ve restart talebi yalnız negatif fixture girişleridir;
bozuk/kayıp kayıt üretirler, sıfır inhibisyonunu kaldıramazlar.

Physics/Gazebo/host veya güvenilen son yazıcı arızasına karşı bağımsız
donanım freni yoktur. Durağan testler hareketli fren kalifikasyonu değildir.
Sağlık veto'sunun tamamı, kalibre StopEnvelope ve kaynak erişim ayrımı 1B+
bağımlılığıdır; ölçülmeyen bounds UNBOUNDED kalır.
