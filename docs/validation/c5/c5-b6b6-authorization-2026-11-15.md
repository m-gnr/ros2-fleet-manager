# C5-B6B.6 — Hareketsiz actuator komut yetkilendirmesi

15 Kasım 2026 · `main`, mevcut worktree. **IMPLEMENTED / DOĞRULANDI:** test-only
imzalı sıfır zarfı, receiver session/sequence/permit/context/bilet doğrulaması;
gerçek ROS/IGN taşıma, fake actuator ve değişmeyen B6B.5 native Lease.
**PARTIAL:** actuator güven sınırı ROS readback test callback'indedir, native
DiffDrive girişine entegre değildir. Ürün hareket kabulü verilmez.
[Tasarım ve güven kaynakları](../../design/c5-b6b6-actuator-authorization.md) ·
[Komut eki](c5-b6b6-authorization-commands-2026-11-15.md) ·
[Ham log](c5-b6b6-authorization-2026-11-15/targeted-tests.txt) ·
[Mermaid](../../diagrams/src/actuator-command-authorization.mmd) ·
[SVG](../../diagrams/svg/actuator-command-authorization.svg).

Son koşu: **17 passed / 0 failed / 0 skipped**, 6.59 s, exit 0.
İlk başarısız kurulum/discovery koşuları ham dizinde korunur; son başarıya
katılmaz. Geniş regresyon, hareketli Gazebo, robot deneyi veya ürün FollowPath yok.

## On hedefin kanıt ayrımı

Aşağıdaki her satırda fiziksel duruş **HENÜZ TEST EDİLMEDİ**: dünya, fizik,
robot ve teker sürücüsü başlatılmadı. Sıfır hedef fiziksel stop kanıtı değildir.

| Hedef | Mesaj kabul/reddi | Transport erişimi | Fiziksel duruş |
|---|---|---|---|
| 1. Yetkili test kaynağı / doğru sıra | Doğru HMAC + session/context/permit + canlı tek kullanımlık bilet; artan 1→2 kabul, yalnız sıfır diagnostic | ROS→IGN→ROS String roundtrip geçti; ACL iddiası yok | HENÜZ TEST EDİLMEDİ |
| 2. Eski session / duplicate | Eski source ve actuator session ret; aynı sıra ret, receipt/deadline yenilenmez | İçeriğin ulaşması engellenmedi | HENÜZ TEST EDİLMEDİ |
| 3. Aynı sıra / farklı payload | Yetkili anahtarla yeniden imzalı değişiklik CHANGED_PAYLOAD; yanlış MAC ayrıca UNAUTHENTICATED | Ulaşması engellenmedi | HENÜZ TEST EDİLMEDİ |
| 4. Timeout sonrası yetkisiz rearm | Yanlış anahtar lease'i değiştirmez; doğru anahtar/yeni sıra da BLOCKED_REARM | Ağdan rearm API yok; yazma erişimi açık | HENÜZ TEST EDİLMEDİ |
| 5. Gate restart | Fake gate SIGKILL; native timeout; yeni süreçten geçerli zarf kilidi açmadı. Eski session ayrı fixture testinde ret | Yeniden bağlantı mümkün; kimlik izni uygulanmadı | HENÜZ TEST EDİLMEDİ |
| 6. Bridge restart | ROS→IGN bridge SIGKILL; native timeout; restart sonrası doğru zarf kilidi açmadı | Bridge yeniden bağlandı, erişim engeli değil | HENÜZ TEST EDİLMEDİ |
| 7. Doğrudan ROS bypass | Ayrı rogue ROS publisher yanlış anahtarlı zarfı ulaştırdı, sink reddetti | **ENGELLENMEDİ**, gerçek DDS erişimi var | HENÜZ TEST EDİLMEDİ |
| 8. Doğrudan IGN bypass | `ign topic` yanlış anahtarlı zarfı ulaştırdı, sink reddetti | **ENGELLENMEDİ**, gerçek IGN erişimi var | HENÜZ TEST EDİLMEDİ |
| 9. Komut kesilmesi | Çalışan runner/timer native steady Lease üzerinden TIMED_OUT gözledi; replay/yetkisiz akış kabul receipt'i üretmedi | Yeni paket yokluğu/reddi erişim kontrolü değildir | HENÜZ TEST EDİLMEDİ |
| 10. Varsayılan C5-A | 350 izlenen docs dışı dosya mevcut baseline ile aynı SHA-256; config/launcher/IDL ve motion_envelope:null korunur | Ürün ağı başlatılmadı/değiştirilmedi | HENÜZ TEST EDİLMEDİ |

Ek hedefler: geçersiz ve süresi dolmuş permit, bitmiş bilet, yanlış context,
yanlış saat alanı, bozuk zarf ve imzalı nonzero ret. Test-only hiçbir kabul
nonzero hedef veya ürün hareket izni oluşturmaz. Timeout, ownership veya permit
release üretmez. Ticket/permit süreleri receiver monotonic alanındadır;
`issued_at` başka saatten çıkarılmaz. Kaynak zamanından semantik yaş
kalifikasyonu yapılmadı; imzalı paket receiver bileti sona erdikten sonra geçmez.

## Kesin çıkış kararı

- **Yetkisiz yazma engellenmedi.** ROS ve IGN injection'ları ulaşabildi. Yalnız
  test verifier'ında anahtarsız komut kabulü engellendi; yalnız alarm/tespit
  değil, lease refresh de yapılmadı. Ürün stock Twist bypass'larının hiçbiri
  kapanmış sayılmaz. ROS SROS2 policy ve IGN süreç/OS yazma sınırı **UNVERIFIED**.
- **Replay sınırı:** HMAC doğrulamasından sonra test readback actuator sink'i;
  session + kesin artan sequence + tam payload + yerel süreli tek kullanımlık
  bilet + live fixture permit. Native stock DiffDrive bu sözleşmeyi almaz.
- **Watchdog bağımsızlığı:** Gate/ROS→IGN bridge süreçleri yokken çalışan test
  actuator runner'ında değişmeyen native B6B.5 steady Lease timeout'u doğrulandı.
  Runner/update-loop donması, server plugin yaşam döngüsü ve bağımsız donanım
  frenleme **HENÜZ TEST EDİLMEDİ**. Timer çalışmadığında zaman tek başına frenlemez.
- **Gerçek hareketi durduran engeller:** native tek giriş doğrulaması; bütün
  ROS/IGN yazarlarına gerçek erişim sınırı; korunan anahtar/oturum yaşam döngüsü;
  gerçek FM permit/context/sağlık bağları; ürün hız/yük/dönüşte kalifiye duruş
  zarfı ve bağımsız fiziksel stop gözlemi. `motion_envelope: null` devam eder.
- **B6B.7 ÖNERİ:** sıfır-only native callback entegrasyonu ve ham Twist alternatif
  girişini kaldıran test bileşeni; ardından DDS allow-only policy ve ayrı IGN
  OS erişim sınırının negatif yazma testleri. Hareket açılması önerilmez.

Kullanıcı değişiklikleri korundu. Ürün dosyası/config/launcher/GUI değişikliği,
commit veya push yapılmadı. Eski test kayıtları değiştirilmedi.

## 15 Kasım commit öncesi tekrar

İlk tekrar **16/17** geçti; sequence refresh testinde timeout sınırında tek assertion `BLOCKED_REARM` yerine ilk geçiş durumu `TIMED_OUT` gördü. Sonraki tam targeted koşu **17/17 geçti**, exit 0; [ham çıktı](c5-b6b6-authorization-2026-11-15/recheck-targeted-tests.txt). İlk başarısız koşu başarı olarak sayılmadı.
