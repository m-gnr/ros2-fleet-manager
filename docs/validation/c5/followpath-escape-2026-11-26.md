# C5 — FollowPath kaçışı ve yeniden planlama

**DOĞRULANDI.** Kontrollü ilerleyememe senaryosu normal başlatıcıda üç robotla geçti. Gazebo fiziksel kaçışı, denetleyici asıl hedefe yeni rotayı ve FM aynı görevin `COMPLETED` sonucunu kaydetti.

## Uygulama

Normal 30 × 18 m depo başlatıcısı, `fleet.nav2_escape_radius_m` tanımlandığında her robot için [depo davranış ağacını](../../../config/navigate-to-pose-escape.xml) üretir. Ana `NavigateRecovery` düğümü bir kurtarma hakkı verir. Etkin ana `FollowPath` isteğinin Humble action sonucu `ABORTED` olduğunda kaçış değerlendirilir. Humble sonucu ayrıntılı hata kodu taşımaz. Nav2 action erişimi, güncel TF, odometri ve iki ham costmap ile duruş doğrulanır.

- Yarıçap üzerindeki sekiz yön sırayla değerlendirilir. Varışın ve gerçek `GridBased` planner rotasının yerel ve global costmap’lerde robotun çevrel ayak iziyle geçilebilir olması gerekir. Rota hücreler arasında örneklenir. Bilinmeyen ve işgal edilen hücreler, pencere dışı rota ve planlayıcının hedefi izin verilenden fazla kaydırdığı sonuç elenir.
- Aynı simülasyon oturumunda robotlar tek bir kaçış kilidi paylaşır. Bir robot kaçış hareketini yürütürken diğeri kaçış hareketi başlatamaz. Terminal hareket ve güncel duruş teyidi belirsizse oturum yeni kaçışa kapalı kalır.
- Seçilen yol, iç `FollowPath` ile yürütülür. Duruş ve konum teyidinden sonra davranış ağacı aynı hedef için ana planlayıcıyı yeniden çağırır. Alım ve teslim geçişleri dış `NavigateToPose` sonucuna bağlıdır. FM görevi, ExecuteTask UUID’si, epoch ve yük bilgisi kendi mevcut akışında ilerler.
- Aday veya gerekli veri bulunamazsa, hareket başarısız olursa ya da kurtarma hakkı tükenirse üst hareket sonucu mevcut terminal hata akışına gider. Terminal görev tekrar açılmaz.

## İlk tam koşu

26 Kasım 2026, normal `./scripts/start_demo.sh` başlatıcısı, 30 × 18 m depo ve üç robot. Nav2 hız sınırı Alpha’da gerçek ilerleyememe üretti. Sınır, denetleyicinin `Failed to make progress` hatasında kaldırıldı. Görev `pick_C2 → delivery-01` için normal HTTP API üzerinden oluşturuldu. İlk tam koşu **FAIL** ile bitti.

| Aşama | Kanıt |
|---|---|
| İç abort | Denetleyici ilerleyememe hatası ve etkin `FollowPath` UUID’si `7d6a379c057bee03fc26c512553cf37a` için durum 6. |
| Kaçış planı | 31 pozlu iç plan, başlangıç (13,500, 1,500) m, yakın hedef (13,500, 0,700) m. |
| Gazebo hareketi | 35,840–42,315 sim-s aralığında (13,500, 1,500) m → (13,333, 0,850) m, fiziksel yer değiştirme 0,671 m. Kaçış `FollowPath` UUID’si `91c784346d7234da41bec66493d1df61` durum 4 verdi. |
| Asıl hedefe yeni yol | 42,400 sim-s’de 305 pozlu yeni plan; başlangıç (13,300, 0,850) m ve bitiş asıl alım hedefi (6,000, −0,750) m. Alım `NavigateToPose` UUID’si `f8e784d4-acdc-4a77-9f7e-12889b289ccf`. |

Kaçış penceresindeki 35 `RobotStatus` örneğinin tamamında görev aynı, epoch 1, faz `MOVING_TO_PICKUP` ve yük durumu `false` idi. Alım hedefi başarıyla sonlandı. Yüklü teslim sürüşünde iki ardışık plan isteği 20 ms içinde onaylanmayınca üst hedef abort oldu ve görev `FAILED` kapandı. Depo ağacının planlama, costmap temizleme ve ana takip düğümlerine 500 ms onay süresi verildi. Terminal görev politikası sürdü.

## Son canlı kabul

| Ölçüt | Sonuç |
|---|---|
| Gerçek iç abort | Alpha denetleyicisi `Failed to make progress` kaydetti. Etkin `FollowPath` UUID’si `0f569ad85ba5f4a0a30961d32b633245` durum 6 verdi. |
| Fiziksel kaçış | Yakın hedef (13,500, 0,700) m için 31 pozlu plan seçildi. Kaçış `FollowPath` UUID’si `87fcce7b143819d90ebd6ea84cbf56e3` durum 4 verdi. Gazebo pozları 35,175–41,755 sim-s aralığında (13,500, 1,500) m → (13,336, 0,824) m, yer değiştirme **0,696 m**. |
| Asıl hedefe yeni rota | 41,835 sim-s’de 305 pozlu plan, (13,300, 0,850) m → (6,000, −0,750) m. Aynı alım `NavigateToPose` UUID’si `0bc1b652-88e4-49da-b833-664116670984` başarıyla sonlandı. |
| Aynı görev | `web-17e64c0e-5e6c-44a1-b55e-3bfb541a4aee` ve `ExecuteTask` UUID’si `cb1d48f5-feef-4b5f-8e92-44e1aae39ffa` korundu. Kaçış aralığındaki 34 `RobotStatus` örneğinin tamamı epoch 1, `MOVING_TO_PICKUP` ve yüksüz. Yükleme asıl alım hedefinde gerçekleşti. `ExecuteTask` 130,770 sim-s’de başarılı bitti, gerçek `completed_epoch=1`. Görev API’de `COMPLETED`. |
| Gazebo teması | Ürün gözlemcisinde sıfır `UNSAFE_CONTACT` kaydı. Alım, teslim ve park dönüşü tamamlandı. |

Koşu, kontrollü tek kaçışı ölçtü. Eşzamanlı iki kaçış için ayrı canlı koşu yapılmadı. Ortak kilit yolu ve bacak başına tek hak, üretilen üç davranış ağacında test edildi.

## Regresyon

Son overlay üç paketle derlendi. Humble seçkisinde 173 test geçti ve bir test kaldı. Kalan depo testi robot başına beş temas sensörü bekliyor. Üretici dokuz sensör verdi ve aynı test değişiklik öncesi `b3dcad9` tabanında aynı sonuçla kaldı. `git diff --check` geçti.

[Canlı koşu ve regresyon komutları](followpath-escape-commands-2026-11-26.md).

[Beta–Gamma GUI karşılaşması ve güncel aday seçimi](followpath-escape-peer-encounter-2026-11-26.md).
