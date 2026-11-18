# B6B.7 — Native sıfır komut doğrulama deneyi

18 Kasım 2026. **PARTIAL / test-only.** Ürün hareket izni yoktur. [Aşama raporu](../../../docs/validation/c5/traffic-integration-2026-11-18.md)
ve [komut eki](../../../docs/validation/c5/traffic-integration-commands-2026-11-18.md)
gerçek test kapsamını belirler. Varsayılan launcher bu dizini import etmez.

`CMakeLists.txt` B6B.5'in aynı DiffDrive/joint yazıcısını `C5_AUTH_ZERO_ONLY`
koluyla derler; Lease aynen kullanılır. Ayrı C++ sınıf adları ve yalnız
`c5::test::AuthorizedZeroDiffDrive` alias'ı vardır. Ham Twist callback'i bu
build'de abone edilmez; doğrudan çağrı bile receipt yenileyemez. Her PreUpdate
ve UpdateVelocity hedefi/teker hedefini sıfırlar. Nonzero açma alanı yoktur.

`AuthorizedZero.hh`, B6B.6'nın receiver-session, HMAC, sequence, yerel tek
kullanımlık bilet ve değişmez context denetimini gerçek native callback'e alır.
Wire `{body: JSON_metni, mac: HMAC_SHA256}` şeklindedir; HMAC tam body byte'larını
bağlar. Float/Unicode yeniden serileştirme farkıyla geçerli imza bozulmaz.
Duplicate JSON key, aşırı derinlik/boyut, yanlış tip ve sonlu olmayan değerler
reddedilir. Bir bilet vardır; tüketilince yenisi üretilir. Yanlış MAC, eski sıra,
session veya context receipt'i yenilemez. Yetkili nonzero, timeout, sim rewind
ve enable değişimi kilitler; ağdan rearm yoktur. Süreler açık fixture dosyası
alanlarıdır; ürün safety threshold'u veya kalifiye duruş bütçesi değildir.

Provision dosyası owner-only, aynı UID'ye ait normal dosya olmalıdır; symlink
izlenmez. Test araçları `/run/c5-b6b7/` altında 0600 dosyalar üretir. Bunlar
yalnız trusted fixture'dır: aynı UID/root'un anahtara erişemediği veya transport
ACL kurulduğu iddia edilmez. Publisher adı kimlik kanıtı değildir. Anahtar
rapora/SDF'ye konmaz; SDF yalnız dosya yolunu taşır. Native session rastgeledir,
receiver restart'ında değişir. Kaynak `issued_at` yalnız diagnostic'tir;
receiver ve kaynak saatleri birbirinden çıkarılmaz. Tazelik biletin receiver
monotonik deadline'ıyla sınanır; yeni bir imzanın eski hız niyetini yenilemesini
anlamsal olarak doğrulamaz.

`server.py` mevcut warehouse üreticisini kullanır; robotlar config'den gelir.
SDF'deki tek stock sürücüyü native sıfır sürücüyle değiştirir. Peer katmanı,
fiziksel model, LiDAR, reset/contact guard ve Nav2 ayarları korunur. Mevcut
supervisor aynen kullanılır; fixture komut bridge'i test tarafından ayrı
başlatılır, dolayısıyla kaybında fizik ve native durum okuyucusu çalışabilir.
`test_live.py`, gerçek joint command component'lerini, bağımsız fiziksel pozu
ve doğrudan ROS/IGN negatiflerini kaydeder. Sıfır hedef, fiziksel frenlemeden
ayrı sonuçtur; duran dünyadaki bu deney hareketli stop kanıtı değildir.

`test_child.py`, gerçek Nav2 sunucusuna yalnız sıfır uzunluklu FollowPath
gönderir. Üst atama/COMMIT ayrı SQLite domain fixture'ıdır; ürün ExecuteTask'ı
gönderilmez, Outbox dispatcher kurulmaz. Gerçek accepted handle'ın UUID ve
tam Path hash'i yeni yetkisiz gözlem API'siyle eşlenir. SUCCEEDED terminali
fiziksel release değildir; mevcut consumer release'i reddeder. Bu test
paralel bir ürün FM/traffic servisi veya uçtan uca taşıma kabulü değildir.

Sonraki gerçek hareket bağlantısı için: kimliği doğrulanmış sağlık/context
üreticisi; gerçek ExecuteTask→FollowPath yaşam döngüsü; actuator'a atomik permit
uygulaması; kalifiye hız/yük/belirsizlik/duruş tüpü; bağımsız timeout/duruş;
kontrollü hold/resume ve fiziksel release gerekir. Bu eksikler giderilmeden
sıfır inhibisyonu kaldırılmaz veya varsayılan demoya bağlanmaz.
