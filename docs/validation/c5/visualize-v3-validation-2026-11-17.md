# Visualize V3 — robot öncelikli depo görünümü

**17 Kasım 2026 · `feature/visualize` · commit/push yapılmadı.** Bu kayıt V1/V2 sunumunun üzerine gelen görsel değişikliği kapsar.

## Uygulama

- Robot gövdesi yalnız Three.js sunum grubunda 1,30 kat büyütüldü. Fiziksel model, collision, footprint, TF, Nav2 ve YAML koordinatları değiştirilmedi. Görsel raf kesiti ve etiket zarfı aynı sunum ölçeğini kullanır.
- Robot modelinin özgün malzemeleri görünür bırakıldı. Sabit 34 px, içi boş ince zemin halkası ve dışarı taşan küçük üçgen gerçek TF yaw değerine göre döner; mevcut ekran etiket yerleştiricisi robot işaretleriyle çakışmayı engeller.
- Fleet Manager snapshot'ındaki güncel gerçek `state` yalnız zemin halkası ve yön üçgeninde dört renk ailesine bağlandı: IDLE `#64748B`, aktif hareket/görev `#6554B5`, CHARGING `#44846B`, ERROR `#C45151`. Bayat veya bağlantısız ürün verisine durum rengi atanmaz. V1 alım/bırakma renkleri korunur.
- Mevcut TF geçmişi kısa ve solan iz olarak kullanılır. İz son 2,8 m, 9 saniye ve 48 örnekle sınırlıdır; son hareketten 4,5 saniye sonra görünmez. Nav2 çizgisi yalnız doğrulanmış gözlemlenen plan paketi varken çizilir.
- Izgara raflarının geometri ve konumları değişmeden açık gri-mavi tonlara geçirildi; yatay kenarlar inceltildi. İz ve rota durum renklerinden ayrı, nötr düşük kontrastlı tonlardadır.

## Doğrulama

| Kontrol | Sonuç |
|---|---|
| Üretim derlemesi | **DOĞRULANDI** — TypeScript ve Vite geçti. |
| Robot/yaw/state Chrome testi | **DOĞRULANDI (mock Chrome)** — üç canlı robot, üç ayrı TF yaw, IDLE/görevde/şarjda zemin halkaları, sabit 34 px işaret ve genel/üstten/yakın kadrajlarda etiket çakışmaması geçti. ERROR ve iki dönüş state'i saf eşleme testinde doğrulandı. |
| Depo profil regresyonu | **DOĞRULANDI (mock Chrome)** — 4/4 geçti. |
| TF/Path kaynak ayrımı | **DOĞRULANDI (mock Chrome)** — gözlemlenen planın epoch sınırında temizlenmesi testi geçti. |
| Görsel inceleme | Genel, üstten ve yakın Chrome görüntülerinde robot işaretleri, yön okları, açık raf paleti ve V1 görev işaretleri incelendi. |
| Gerçek ROS/Gazebo canlı koşu | **HENÜZ TEST EDİLMEDİ.** V2.3'ün tarihsel üç robotlu canlı kanıtı bu V3 render değişikliğinin canlı kabulü olarak sunulmaz. |

Görseller: [genel](visualize-v3-screenshots/overview.png) · [üstten](visualize-v3-screenshots/top.png) · [yakın](visualize-v3-screenshots/near.png). Komutlar ve kapsam [komut ekinde](visualize-v3-commands-2026-11-17.md) kayıtlıdır.
