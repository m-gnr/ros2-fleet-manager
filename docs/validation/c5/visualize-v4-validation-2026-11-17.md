# Visualize V4 — zemin ve aydınlatma

**17 Kasım 2026 · `feature/visualize` · commit/push yapılmadı.** Bu kayıt V1–V3 sunumunun üzerine gelen Three.js zemin, raf yüzeyi ve ışık değişikliğini kapsar.

## Uygulama

- 30 × 18 m zemine 1 m aralıklı, yüzde 16 opaklıklı gri-mavi kılavuz çizgileri tek `LineSegments` çizimiyle eklendi. Çizgiler zemin üstünden 3 mm, koridor boyası, bölge yazıları, operasyon işaretleri ve park yuvalarının altındadır; aynı düzlem kullanılmaz.
- Eski sert raf tabanı kutuları kaldırıldı. Her rafın mevcut ayak izini değiştirmeyen, tek instanced shader çiziminde kenara doğru saydamlaşan temas gölgesi eklendi. Düşük kalite seçeneği bu katmanı kapatmaya devam eder.
- Raf kutuları aynı instanced geometriyi ve renklerini kullanır. Metalness sıfır, roughness artırılmıştır; tek yönlü yumuşak ana ışık ve hemisphere ışığı üst/yan/ön yüzlerde hafif ton farkı üretir.
- Zemin, duvar ve raflar açık gri-mavi palette tutuldu. Shadow map, post-processing, parlama ve yeni fiziksel geometri eklenmedi.

## Doğrulama

| Kontrol | Sonuç |
|---|---|
| Üretim derlemesi | **DOĞRULANDI** — TypeScript ve Vite geçti. |
| V1–V4 Chrome görsel/regresyon testi | **DOĞRULANDI (mock Chrome)** — 2/2 geçti; 50 zemin segmenti, tüm raf temas gölgeleri ve `shadowMapEnabled: false` ayrıca denetlendi. |
| Depo profil regresyonu | **DOĞRULANDI (mock Chrome)** — 4/4 geçti. |
| TF/Path kaynak ayrımı | İlk eşzamanlı test koşusunda planın oluşması 5 saniyede zaman aşımına uğradı; aynı test tek başına yeniden çalıştırıldığında **1/1 geçti**. Bu ilk hata gizlenmez ve V4 görsel katmanına bağlanmış bir kanıt değildir. |
| Görsel inceleme | Genel, üstten ve yakın Chrome görüntülerinde soluk zemin çizgileri, raf temas gölgeleri, yüz tonları ve V1–V3 işaretleri incelendi. Boş canvas görülmedi. |
| Kısa render karşılaştırması | Aynı mock TF fixture'ı ve 2 saniyelik trace penceresinde V3 `228` draw call / `18.788` üçgen / `42` trace frame; V4 `229` / `18.688` / `47` ölçüldü. Tek koşuluk trace frame sayısı FPS garantisi değildir; draw call artışı `+1`, üçgen farkı `-100`dür. |
| Gerçek ROS/Gazebo canlı koşu | **HENÜZ TEST EDİLMEDİ.** V2.3'ün tarihsel üç robotlu canlı kanıtı V4 render kabulü olarak sunulmaz. |

Görseller: [genel](visualize-v4-screenshots/overview.png) · [üstten](visualize-v4-screenshots/top.png) · [yakın](visualize-v4-screenshots/near.png). Komutlar ve kapsam [komut ekinde](visualize-v4-commands-2026-11-17.md) kayıtlıdır.
