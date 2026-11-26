# C5 — Beta–Gamma karşılaşmasında FollowPath kaçışı

**Canlı kabul geçmedi.** Beta ve Gamma’nın iç abort’ları yeniden üretildi. Kaçış hareketi için uygun rota doğrulanamadı.

## Referans ve değişiklik

26 Kasım 2026 referans oturumunda Chrome panelinden üç `MEDIUM` öncelikli `pick_C2 → delivery-01` görevi gönderildi. Gazebo’daki Beta–Gamma merkez mesafesi Gamma’nın alım abort’u civarında yaklaşık 0,589 m, Beta’nın yüklü teslim abort’u civarında 0,611 m idi. İki denetleyici de `Controller patience exceeded` kaydetti. Kaçışlar `no traversable escape candidate` ile bitti. Referans ikili costmap örnekleri ve aday retleri kaydedilmedi.

Yeni arama, bu profilde sekiz yönü 0,80 m, 0,60 m ve 0,40 m’de dener. Plan elde edilince önce robotun ölçülen güncel konumu, sonra rota örnekleri ayrı ayrı doğrulanır. Ayak izi, ham costmap eşikleri ve iki costmap zorunluluğu korunur. Varış için gereken fiziksel yer değiştirme, seçilen adayın gerçek uzaklığından hesaplanır.

`FLEET_ESCAPE_REJECT` satırı aday numarası, aday yarıçapı, hedef, kontrol edilen nokta, costmap, hücre ve ham maliyeti verir. `FLEET_ESCAPE_SEARCH` toplam denenen adayları, Nav2’den alınan boş olmayan yolları ve ret sayılarını verir.

| Kayıt | Anlamı |
|---|---|
| `candidate_blocked` | Aday hedefte ayak izi için gerekli açıklık yok. |
| `planner_no_path` | Nav2 isteği kabul etmedi, süre doldu veya geçerli action/path sonucu gelmedi. |
| `route_start_blocked` | Plan geldi. Ölçülen robot konumundaki ilk kontrol costmap engeline takıldı. |
| `route_blocked` | Başlangıç geçti. Sonraki rota örneğinde costmap engeli bulundu. |
| `route_invalid` | Rota çerçevesi, ucu veya uzunluğu kaçış sözleşmesini karşılamadı. |

## Referans zamanlarına yakın GUI tekrarı

Üç gönderim de HTTP 201 aldı. Alım çıkışları Alpha, Beta ve Gamma için sırasıyla 21,210, 21,665 ve 23,625 sim-s’de başladı. 60–95 sim-s penceresinde Beta–Gamma örneklerinin en yakın eşleşmesi 78,715 sim-s’de 0,720 m idi. Bu koşuda üç görev de `COMPLETED` oldu ve temas kaydı yoktu. İç denetleyici hatası ve kaçış tetiklenmediği için koşu kaçış kabulü sayılmadı.

## Üçüncü GUI gönderiminin geciktirildiği tekrar

İlk iki tıklama aynı zamanlara hedeflendi. Gamma’nın görevini alan üçüncü tıklama 32,85 sim-s’de yapıldı. Üç gönderim HTTP 201 aldı. 60–95 sim-s penceresinde Beta–Gamma örneklerinin en yakın eşleşmesi 84,820 sim-s’de 0,715 m idi. Üç görev `COMPLETED` oldu ve temas kaydı yoktu. Bu koşuda da iç abort ve kaçış tetiklenmedi.

## Sıkışmanın yeniden üretildiği GUI koşusu

Alım hareketlerinin kabul zamanları Alpha’da 20,020, Beta’da 21,210 ve Gamma’da 23,405 sim-s idi. Beta yüklü teslimde, Gamma yüksüz alımda `Controller patience exceeded` sonucunu aldı. Gazebo’da 81,5–83,0 sim-s penceresindeki en yakın eşleşen merkez örnekleri 0,740 m aralıklıydı.

| Robot | Denenen aday | Aday dolu | Plan yok | Başlangıç reddi | Rotanın ilerisi engelli | Geçersiz rota |
|---|---:|---:|---:|---:|---:|---:|
| Beta | 24 | 10 | 5 | 9 | 0 | 0 |
| Gamma | 24 | 11 | 0 | 13 | 0 | 0 |
| Toplam | 48 | 21 | 5 | 22 | 0 | 0 |

Nav2’nin ürettiği **22 rotanın tamamı**, sonraki örnekler değerlendirilmeden ölçülen robot konumunda elendi. Beta’nın dokuz rotasında global costmap merkez hücresi (6,825, −1,075) m, Gamma’nın 13 rotasında (7,425, −0,975) m idi. İki hücrenin ham maliyeti de **253** idi. Adayların 0,60 ve 0,40 m’ye yaklaşması başlangıç engelini kaldırmadı. Beta’da tüm adaylara göre en sık tek ret dolu aday pozuydu. Gamma’da ve toplamda başlangıç reddi en sık nedendi.

Hiçbir iç kaçış hareketi gönderilmedi. Gamma’nın görevi 82,570 sim-s’de, Beta’nın görevi 82,710 sim-s’de `NAV2_ABORTED` ile sonlandı. Her iki sonuç gerçek `completed_epoch=1` taşıdı. Alpha aynı koşuda teslimatı tamamladı. Gazebo gözlemcisi sıfır `UNSAFE_CONTACT` kaydetti. **Bu koşu fiziksel kaçış kabulünden geçmedi.**

## Hareket kilidi

Bu koşuda iki robotun aday aramaları çakıştı. Aynı Docker Desktop container’ında iki ayrı süreçle yapılan deneyde kanıt dizininin bind mount’u iki `flock` isteğini de kabul etti. Container’a ait `/tmp` üzerindeki ikinci istek reddedildi. Ürün kilidi bu nedenle container dosya sistemine taşındı. Planlama robot başına bağımsız. Kilit, doğrulanmış kaçış rotasının hareket komutundan önce alınır ve terminal duruş teyidine kadar tutulur.

Container içi kilit derlendi ve ayrı süreçle kilit alma, teyitsiz hareket sonrası kilidin kapalı kalması ve terminal teyitten sonra kilidin yeniden alınması doğrulandı. Normal başlatıcıyla yapılan son GUI tekrarında Beta ve Gamma yine kaçış aramasına girdi.

| Robot | Denenen aday | Aday dolu | Plan yok | Başlangıç reddi | Rotanın ilerisi engelli | Geçersiz rota |
|---|---:|---:|---:|---:|---:|---:|
| Beta | 24 | 10 | 7 | 0 | 0 | 7 |
| Gamma | 24 | 11 | 0 | 13 | 0 | 0 |

Gamma’nın Nav2’den dönen 13 rotasının tamamı global costmap’in (7,275, −0,925) m merkez hücresindeki **253** maliyetiyle elendi. Beta’da en sık ret dolu adaydı. Beta’ya dönen yedi rota, başlangıç değerlendirmesinden önce çerçeve, çözünürlük veya rota ucu denetiminde elendi. İki görev sırasıyla Gamma için 78,690, Beta için 79,360 sim-s’de `NAV2_ABORTED` ile sonlandı. Gazebo temas kaydetmedi. Fiziksel kaçış başlamadığı için son sürüm de canlı kabulden geçmedi. Commit ve push yapılmadı.

[Komutlar ve ham kanıt](followpath-escape-peer-encounter-commands-2026-11-26.md).
