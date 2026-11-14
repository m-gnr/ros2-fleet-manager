# C5 — Köşe sensörü optimizasyonu ve izole HOLD/RESUME

14 Kasım 2026, Europe/Istanbul. **EXPERIMENTAL / PARTIAL**.
Ürün qualification ve gerçek FM→Executor HOLD/RESUME kabulü tamamlanmadı.

## Kullanıcı kararı, kaynak ve koruma

**ONAYLANDI:** Seçenek 3; mevcut üst LiDAR lokalizasyon için yerinde kalır,
engel algılama bağımsız gövde seviyesi sensörleriyle geliştirilir. D ön-LiDAR
ürün için reddedildi; [eski D deneyi](c5-front-lidar-geometry-comparison.md)
başarısızlıklarıyla birlikte tarihsel kanıttır. Bu çalışma yeni genel mimari,
merkezi trafik algoritması, 27 istasyon taraması veya C5 final kabulü değildir.

Feature worktree `/Users/murat/develop/ros2-fleet-manager-c5-auto-charging-integration`,
dal `feat/c5-auto-charging-integration`; temiz başlangıç HEAD
`21c7b16bb72e49a427e5a09c3f0d2c1b02662b7a`. `ca85106b` güncel HEAD sayılmadı.
Main HEAD `6bf27e4c72e086881eff6d2f38e78e78ce231ba1`; mevcut kullanıcı
README/PDF/kod/rapor değişiklikleri korunur. Sonraki açık kullanıcı talimatı
yalnız bu feature dalında mantıksal yerel commit'e izin verir.
Reset/clean/stash/rebase/push/merge kullanılmaz.

Yeni ham kanıt kökü:
`/Users/murat/develop/c5-obstacle-optimization-evidence-20261114`.
Başlangıç/son main ve feature Git status, worktree, HEAD, binary diff ve SHA-256
manifestleri bu köktedir. Kapsam tracked + ignore edilmeyen untracked normal
dosyalardır; symlink, ignored build/cache ve Git metadata hariçtir.
Eski Gazebo/Docker kanıtları yeniden çalıştırılmaz veya üzerine yazılmaz.
Yeni container `c5-obstacle-optimization-20261114`, mevcut
`ros2-fleet-c5-validation:humble-fortress` image SHA
`7fb7e7fc4aebe0d2b4097752e9b470e30d8ea7a8126bb1dee87d03f30330609d` kullanır;
workspace salt okunur, `/audit` yalnız yeni kanıt köküdür. Image rebuild yoktur.

## Geometri ve aday eleme

Mevcut model **özelleştirilmiş depo AGV'sidir**, birebir TurtleBot3 Burger değil:
0,50×0,30×0,10 m body, r=0,10 m tekerlekler, 2,484 kg toplam kütle,
0,30 m Nav2 robot radius, 30×18 m depo korunur. Ana üst LiDAR origin'i
base_link'e göre `(0;0;0,15 m)`, 180 ışın/5 Hz/360° nominal FOV ve AMCL beam
parametreleri değişmez. Gövde/tekerlek/caster collision ve inertia XML'i iki
aday arasında byte eşittir; yeni invariant testi bunu kontrol eder.

| Özellik | Referans | Seçilen deney: `side_mount` |
|---|---|---|
| İlk sensör link origin'i m | (0,26; 0,10; 0,0125) | (0,15; 0,23; 0,0125) |
| İkinci link origin'i m | (−0,26; −0,10; 0,0125) | (−0,15; −0,23; 0,0125) |
| Yaw | 0° / 180° | 90° / 270° |
| Optik origin link'e göre m | (0;0;0,0185) | Aynı |
| FOV / ışın / hız | −91°…+100° / 97 / 5 Hz | Aynı |
| Menzil | 0,1…10 m | Aynı |

Optik düzlem base_link'e göre z=0,031 m'dir; fiziksel world yüksekliği gerçek
pose ile belirlenir. Her sensörde 0,020×0,030×0,015 m, 0,015 kg kasa ve
r=0,004 m, h=0,010 m, 0,002 kg head vardır. Head merkezi link'e göre
z=0,0125 m'dir; optik düzlem opak kasa/head üstündedir. İki sonlu sensörün
0,034 kg kütlesi ve link inertia hesabı korunur; taşınan rigid link'in pozu ve
dünya yönelimindeki inertia dönüşür. Kasa Nav2 küresinin içinde
r=0,291933 m, head r=0,280201 m'dir. Ürün generator'ının own-collision,
sonlu kasa çakışması ve sürekli FOV kontrolleri aşılmaz.

Önce az sayıda aile analitik olarak elendi. Her geçen aday için 0,75/1/1,5 m,
5° bearing adımı ve dört peer heading'i: 864 örnek, gerçek SDF box/cylinder/
sphere ilk-yüzey kesişimi. Bunlar **geometrik öngörü**, gerçek scan değildir.

| Aday | Geometrik sonuç |
|---|---|
| Mevcut iki sensör | 4 sıfır-hit örneği; minimum 0 |
| Merkezlenmiş yaw −4,5°, x=0,262 | Own body ile FOV kesişimi: RET |
| Daha dış y=0,115 | Sonlu kasa 0,30 m küreyi aşıyor: RET |
| Yaw −9°, x=0,265 | Sonlu kasa küreyi aşıyor: RET |
| −92°…101°, 99 ışın | 4 sıfır-hit örneği devam |
| Aynı FOV, 193 ışın | 4 sıfır-hit örneği devam |
| y=0,110, aynı yaw | 4 sıfır-hit örneği devam |
| Yan köşe (0,15;0,23), yaw 90° | 0 sıfır-hit, minimum 3; own-intersecting ray 0 |
| Yan köşe, yaw 85,5° | 0 sıfır-hit, minimum 2 |

Minimum 3 ışın sağlayan yan köşe seçildi; ek sensör veya daha yüksek ışın
sayısı gerektirmiyor. Bu seçim **ürün montaj onayı veya sürekli görüş garantisi
değildir**. Üç ayrı ekranlama çıktısı `screen`, `screen-v2`, `screen-v3` altında
korunur. Referansın kaçırdığı örnekler 0,75 m, bearing 95°/275°, peer heading
90°/270°'dir. Örneklenmeyen heading, pitch/roll, mesafe ve fiziksel toleranslar
açık kalır.

## Gerçek Gazebo karşılaştırması

Gerçek Fortress/DART/OGRE2 yazılım render; Humble/CycloneDDS kullanıldı.
Nav2 controller/smoother 1.1.20, CycloneDDS RMW 1.3.5. Native IDL + perception
paketleri yeni `/audit/ros` altında **2 paket PASS, 13,5 s** derlendi.

Her dünya ayrı partition ile sıralı başlatılır. Body/wheel/caster/sensör contact
kanıtına dayalı guard etkindir; zararlı temasta world pause ve FAIL uygulanır.
Fizik motoru başlamadan ayrı YAML başlangıç pozları verilir; çalışan robotun
physical pose/odom/scan/TF'si veya action terminali üretilmez. AMCL ofseti
`initialpose` üzerinden açık test girdisidir; truth değildir.

Referans 3×3 m local costmap, 0,05 m grid, 0,30 m radius, controller/smoother
sınırları korunur. [Önceki 5×5 m / 0,10 m/s C adayı](c5-safe-motion-profile-2026-11-13.md)
bu seriye karıştırılmaz; güvenli ürün profili sayılmaz.

Ham scan → aynı config'den gerçek sensör TF → ölçüm damgasında TF sorgusu →
ObservedObstacleLayer'ın **gerçek kullanılan ObservationBuffer stamp'i** →
sonraki local grid eşleşmesi kaydedilir. İlk-alım TF başarısızlığı ve sonradan
başarı ayrı tutulur. 0,015 m ilk-yüzey sınıflandırma payı ve bir hücre lethal
komşuluğu offline yöntem sınırlamalarıdır; güvenlik payı değildir. Hücre birden
fazla kaynakla işaretlenebilir; eşleşme tek-kaynak nedensellik iddiası taşımaz.

| Gerçek koşu / alpha | Exit | Üst LiDAR | İlk köşe | İkinci köşe | Used-observation→lethal: üst / ilk / ikinci |
|---|---:|---:|---:|---:|---|
| reference-front | 0 | 0/20 | 20/20 | 0/20 | 0 / 6 / 0 |
| reference-back | 0 | 0/20 | 0/20 | 20/20 | 0 / 0 / 5 |
| reference-side | 0 | 0/20 | 20/20 | 20/20 | 0 / 8 / 10 |
| reference-seam | 0 | 0/20 | 0/20 | 0/20 | 0 / 0 / 0 |
| reference-opposite | 0 | 0/20 | 0/20 | 0/20 | 0 / 0 / 0 |
| side_mount-front | 0 | 0/19 | 0/20 | 20/20 | 0 / 0 / 6 |
| side_mount-back | 1 | 0/20 | 20/20 | 0/20 | 0 / 5 / 0 |
| side_mount-side | 0 | 0/19 | 19/19 | 0/19 | 0 / 4 / 0 |
| side_mount-seam | 0 | 0/18 | 18/18 | 0/18 | 0 / 6 / 0 |
| side_mount-opposite | 0 | 0/20 | 0/20 | 20/20 | 0 / 0 / 7 |

Her hit hücresi ilk-yüzey hit içeren scan / damgada truth ile eşleşen scan sayısıdır.
Seam/opposite bearing 95°/275°, peer göreli yaw 90°; merkez ayrımı 0,75 m.
Diğer üç yön ön/arka/yan, karşıt robot yönelimleriyle aynı merkez ayrımındadır.
`side_mount-back` sensör verisi vardır fakat bridge SIGABRT/−6 yüzünden **FAIL**; temiz kabul değildir.
İki robotun bütün kaynakları makine özetindedir; eksik scan sayısı 20 diye doldurulmaz.

**Dönüş:** bir metre arkadaki sabit peer ile gerçek Spin: referans α 98 eşli stamp’in
1’inde iki sensörde de peer-hit yok; aday α 100/100 eşli stamp’te en az bir sensörde
peer-hit verir. β sırasıyla 97/97 ve 100/100 görünür stamp verir. Gerçek açısal yol
1,583071 / 1,592343 rad; tepe ω≈0,50 rad/s, iki terminal STATUS_SUCCEEDED=4.
Bu 5 Hz örneklerde iyileşmedir; örnekler arası kesintisiz marking garantisi değildir.
Bütün A/B ilk-yüzey ölçümlerinde self-surface dönüşü ve own collision arkasından
peer dönüşü **0** ölçüldü.

| A/B bütün kaynaklarda gözlenen maksimum | Referans s | Aday s |
|---|---:|---:|
| Scan geliş aralığı | 0,405719 | 0,441826 |
| Scan sim-time yaşı | 0,110 | 0,155 |
| Kullanılmış observation yaşı | 0,290 | 0,260 |

İlk callback’te sayısal TF hazır olmayan scan’ler vardır: referans 688, aday 718.
İlk-alım sayısal TF’li örnekler 617/574; ertelenmiş başarılar ayrıca makine dosyasındadır.
Bu hazır-olmama sayıları Nav2’nin observation kullanamadığı sayıları değildir.
Observation/marking kanıtı kendi stamp eşleşmesiyle ayrıca değerlendirilir.

### AMCL koruma karşılaştırması

Aynı üst LiDAR ve AMCL beam ayarlarıyla her robotun initialpose girdisi
(+0,15 m;+0,10 m;+0,10 rad) kaydırıldı; gerçek `request_nomotion_update` ile
20 s yerleşme sonrası dört gerçek AMCL örneği/robot ölçüldü.

| Koşu / robot | XY min–maks. m | Yaw maks. rad | map→base TF XY maks. m |
|---|---:|---:|---:|
| reference-offset / robot_alpha | 0.032159–0.045855 | 0.006308 | 0.052134 |
| reference-offset / robot_beta | 0.002712–0.023779 | 0.004305 | 0.018858 |
| side_mount-offset / robot_alpha | 0.032159–0.045855 | 0.006308 | 0.052134 |
| side_mount-offset / robot_beta | 0.002712–0.023779 | 0.004305 | 0.018858 |

İki varyantın her robotunda ana LiDAR XML SHA’sı bütün koşularda aynı;
AMCL parametreleri, eski body/wheel/caster collision/inertia ve local-costmap
parametreleri invariant testinde eşittir. Bu örneklerde D’de gözlenen AMCL
gerilemesi yoktur; tek koşu çifti uzun süreli/istatistiksel lokalizasyon garantisi değildir.
Ofset koşusunda aday β için bir unpaired obstacle stamp vardır; eşli görünürlük
hesabına eklenmez.

## İzole demo ve qualification sınırı

İzole deneyde alpha başlangıcı (−5;2;0), beta (5;2;π); beta'ya hareket
komutu verilmez. Alpha için hedef (−3;2;0), ayrı BackUp 0,30 m ve ayrı bridge
kaybı deneyleri hazırlanır. Ölçülen tüm alpha physical_pose örneklerinin
0,30 m footprint'li süpürülmüş AABB'si `x∈[−6,5;−1,5], y∈[0,5;3,5]` bölgesiyle
karşılaştırılır. Gerçek görev/rota/recovery kabulü bu offline örnek denetimine
indirgenmez. Gelecekteki bütün Nav2 recovery/rota sapmaları için canlı sınır
kanıtı veya fiziksel kapatma sağlanmış değildir.

Tek robotlu kabul iki robot trafik kabulüne bağlanmaz. İzole kabul için gerekli
kanıtlar: gerçek tüm komut yolları/Spin/BackUp dahil swept alanın korunması,
statik engellere/sınıra yeterli açıklık, sensör kaynak/frame/stamp/TF/observation
sağlığı, mevcut hız sınırlarında lineer/açısal/birleşik hızdan gerçek kayıp→cancel→
eşleşen terminal→güncel sürekli duruş, saat/taşıma/scheduling belirsizliği,
contact guard ve yerel çalışma koşullarıdır. Tek robot hesabı
`D_free ≥ v*T_loss_to_cancel + B_stop + U + M` olur; ikinci hareketli robotun
hızı eklenmez. `U` ve `M` kanıtsız sıfır alınmaz; gözlenen sonlu maksimumlar
doğrudan gelecek üst sınırı ilan edilmez. İzolasyon iyileştirilmiş görünürlüğü
fiziksel duruş qualification'ına dönüştürmez.

**Ürün `_perception_envelope_qualified=False`, `motion_envelope=null` korunur.**
Yeni test flag'i, doğrudan state/SQLite değişimi, sentetik health/qualification
veya admission bypass yoktur. Mevcut kapı caller-supplied bound/hash ile dahi
açılmıyor. Doğrulanmış izole zarf kurulamadığı için qualification mekanizmasını
açan ürün değişikliği yapılmaz.

### İzole fiziksel ölçümler ve araç düzeltmesi

21 toplam gerçek dünya girişiminin 14’ü A/B, 5’i ilk izole seri, 2’si düzeltilmiş
subject doğrulamasıdır. **18 temiz kapanış / 3 native FAIL**; zararlı temas
bildirimi 0. İlk izole Spin ve açısal kayıp dünyaları bridge kapanış hatası
nedeniyle FAIL kalır. Örneklenmiş alpha footprint sınırı beş ilk izole ve iki
subject koşusunda da belirtilen dikdörtgen içindedir; bu, bütün gelecekteki
Nav2 recovery'lerini sınırlayan bir ürün mekanizması değildir.

İlk izole rota gerçek STATUS_SUCCEEDED=4 ile 1,824155 m fiziksel yol yaptı;
hedef toleransı nedeniyle 2 m geometrik hedef kadar gitmesi beklenmez.
BackUp −0,05 m/s gerçek hız ve 0,303770 m yol ile STATUS_SUCCEEDED=4 aldı.
Bunların tam fiziksel footprint sınırları sırasıyla
`x=[−5,300000;−2,877393], y=[1,700000;2,323639]` ve
`x=[−5,603770;−4,700000], y=[1,700000;2,300000]` m’dir.

**Düzeltilen somut ölçüm hatası:** önceki gözlemci herhangi bir robotun
watchdog’u sağlıksız olunca alpha’yı iptal ediyordu. İlk doğrusal izole kayıpta
0,418187 s’lik polling anında beta sağlıksız, alpha hâlâ sağlıklıydı; alpha’nın
ilk fault callback’i 0,441668 s’dedir. Bu girişim **alpha’nın kayıp→cancel
zamanı veya otomatik ürün HOLD kanıtı değildir**. Yeni `subject_watchdog_ready`
aktif robotun tek watchdog’unu seçer; eksik/duplicate subject reddedilir. İki
robotun health durumu ve `subject_robot` ham olayda korunur. Test, sağlıklı
alpha/sağlıksız beta durumunun alpha’yı durdurma koşulu olamayacağını doğrular.
Eski runtime değiştirilmeden ayrı `isolated-subject` runtime/kanıt grubu üretildi.

| Düzeltilmiş subject deneyi | Lineer kayıp | Açısal kayıp |
|---|---:|---:|
| Cancel anındaki gerçek v m/s / ω rad/s | 0,226316 / ≈0 | ≈0 / 0,500000 |
| Bridge kesme→alpha sağlıksız polling s | 0,373128 | 0,452448 |
| Bridge kesme→cancel s | 0,373248 | 0,452577 |
| Cancel→eşleşen gerçek CANCELED terminal s | 0,034921 | 0,010255 |
| Cancel sonrası toplam fiziksel XY yolu m | 0,035626 | 0,000000106 |
| Cancel sonrası toplam fiziksel açısal yol rad | 0,000054 | 0,089995 |
| Mevcut eşikler altında kalan odom suffix sim-s | 7,770 | 7,665 |
| Son 5 sim-s fiziksel örnek / max damga aralığı s | 143 / 0,035 | 143 / 0,035 |
| Bu son fiziksel pencerede XY/açısal yol | 0 m / 0 rad | 0 m / 0 rad |

Her iki düzeltilmiş girişim temiz exit 0 ve contact `unsafe=false` ile kapandı.
İki gerçek terminal aynı deney goal UUID’siyle eşleşen STATUS_CANCELED=5’tir.
Lineer eşik-altı suffix’in başında toplam 0,000797 m artık fiziksel yol vardır;
ilk küçük hız örneği tam duruş ilan edilmez. Son beş saniyede kaydedilen
143 gerçek physical_pose örneği ayrıca sabittir. Bu, 0,035 s örnekler arası
sürekli-zaman garantisi veya ürün HELD_CONFIRMED olayı değildir. Kaynak geri
getirme bu araçta kapanış içindir; operatör RESUME ve ikinci ürün HOLD yoktur.

**OPEN:** İzole ürün qualification için bütün mümkün rota/recovery sınırının
korunması, azami birleşik hareket/duruş, açıklık-belirsizlik bütçesi ve native
bridge kararlılığı hâlâ eksiktir. Tek robotlu kabul iki robot trafik kabulünü
beklediği için değil, bu kendi yerel koşulları tamamlanmadığı için açılmadı.

## Gerçek ürün HOLD/RESUME sonucu

**NOT TESTED:** FM gerçek görev başlatma ve Executor fiziksel hareketinden
bridge kaybı→otomatik HOLD→Nav2 terminal→sürekli duruş→aynı HOLD'un SQLite
COMMIT'i→kaynak geri geldiğinde kilit→yetkili API RESUME→aynı görev/faz yeni
UUID→ikinci kayıpta tekrar HOLD zinciri. Ayrı regresyon fixture PASS'leri bu
tek fiziksel zincirin kabulü sayılmaz. Qualification şartı sağlanmadan ürün
hareketi açılmadı. İzole Nav2 gözlemci cancel deneyi ürün HOLD değildir.

## Regresyonlar, FAIL ve açık kapsam

| Kontrol | Güncel sonuç / ham kayıt |
|---|---|
| Tam host, subject düzeltmesi sonrası | **655 PASS / 35 SKIP**, 22,73 s; `host-full-final.log` |
| İlk tam host | 653 PASS / 35 SKIP; `host-full.log` |
| Tam Humble/CycloneDDS, subject düzeltmesi sonrası | **744 PASS / 0 SKIP**, 67,44 s; `ros-full-final.log` |
| İlk tam Humble/CycloneDDS | 743 PASS / 0 SKIP; `ros-full.log` |
| Yeni geometri invariant + subject negatif testi | 2 PASS; `subject-fix-tests.log` |
| Geometri/ilk-yüzey/duruş analyzer odaklı seçki | 20 PASS; `focused-final.log` |
| Native IDL/perception build | 2 paket PASS; `native-build.log` |
| Gerçek Gazebo | 21 girişim, 18 temiz kapanış, **3 native FAIL**, 0 zararlı temas bildirimi |
| Python compile ve `git diff --check` | PASS |

Tam seçki API yetki/Origin, HTTP/socket→consumer, SQLite audit/Outbox rollback,
HOLD sırasında HIGH ve station ownership, stale/duplicate RESUME, gerçek DDS
source/publisher kimliği, TF/stamp, kullanılmamış observation, tek/çift kaynak
kaybı, görev UUID/epoch ve C3/C4 regresyonlarını içerir. Bunlar kontrollü katman
negatifleridir; yeni montajla bütün negatiflerin gerçek Gazebo kabulü değildir.
Host SKIP’leri başarı sayılmaz. Testte kasıtlı diagnostic storage/saturation
ve unresolved ownership logları saklanır. Frontend ürün kodu değişmedi;
yeni Chrome/Vite koşusu bu çalışmada **NOT TESTED**.

Üç native FAIL'in tümünde kapanışta `free(): corrupted unsorted chunks` vardır:
`physical/side_mount-back` obstacle bridge −6; `isolated/side_mount-isolated_spin`
ana bridge −6; `isolated/side_mount-isolated_turn_loss` ana bridge −6.
SIGSEGV/−11 bu yeni seride gözlenmedi; eski D serisinin −11 kaydı silinmez.
Allocator mesajı root-cause veya düzeltilmiş native bug iddiası değildir.
Önceden derlenmiş bridge'e kanıtsız shutdown sırası/ayar değişikliği yapılmadı.
Temiz subject koşuları eski native başarısızlıkları kapatmaz.

Üçüncü obstacle sensörü **eklenmedi ve önerilmedi**: seçilmiş iki sensörde
ölçülen dar kör örnekler düzelebiliyorsa üçüncü sensör ihtiyacı gösterilmiş
olmaz. Örneklenmeyen sürekli sektörler ve farklı fiziksel şartlar **OPEN**;
üçüncü sensörün gereksizliği bütün demo/ürün hareketleri için kanıtlanmış değildir.

İlk invariant test girişimi yanlış biçimde AMCL `scan_topic='scan'` bekledi;
mevcut namespace'li `/robot_alpha/scan` sözleşmesi korundu ve test beklentisi
düzeltildi. İlk FAIL logu korunur; ürün konfigürasyonu değiştirilmedi.

Komutlar [ekte](obstacle-optimization-2026-11-14/commands.md), gerçek ölçümler ve
ham hata referansları [makine özetinde](obstacle-optimization-2026-11-14/results.json)
tutulur. Tarihsel testler yeni koşu sayılmadı.

## Yerel commit ve kapanış

Ölçüm aracı, subject düzeltmesi, geometri invariantları ve teknik belge commit’i:
`7e211e3ada149554269a788ec49616f67f00377d`. Rapor/kanıt commit’i ayrıdır; kendi SHA’sına döngüsel referans
yazılmaz. Kesin teslim SHA’sı ham kökte `delivery-head.txt`, son Git kayıtları
`feature-end-*` dosyalarında tutulur.

Yeni test container’ı bitişte durduruldu ve silinmedi. Önceki container/image/
volume’lara start/stop/remove/build uygulanmadı. Main kaynakları, kullanıcı
değişiklikleri, kök README, PDF/notlar ve eski kanıtlar korunur. Bitiş kaynak
manifest karşılaştırması ham kökteki `source-comparison.json` içindedir.
