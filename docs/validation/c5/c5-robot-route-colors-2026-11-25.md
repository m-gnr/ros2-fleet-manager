# C5 — 3D robot kimlik renkleri ve Nav2 rotaları

**DOĞRULANDI · 25 Kasım 2026.** Temiz başlangıçtaki GitHub `main` SHA’sı `79a936a1edc419fa92d2e64efa529b21b78a7212`.

Gövde panelleri, harita etiketi, plan ve TF izi renklerini aynı [robot kimliği paletinden](../../../frontend/src/scene/robotIdentity.ts) alır. Panel malzemesindeki hafif renk katkısı ve etiketteki renkli kenar kimliği vurgular. Nav2 planı 2,75 px genişliğinde, %78 opak ve kesiklidir. Sürekli TF izi 1 px genişliğinde, en çok %48 opaktır ve son hareket ölçümünden itibaren mevcut 4,5 saniyelik sürede solar. Zemin halkası robot durumunu, mevcut durum metinleri canlılık ve hatayı gösterir.

## Canlı Chrome kontrolü

Depo kökünde `source .venv/bin/activate` ardından `./scripts/start_demo.sh` ile varsayılan üç robotlu profil başladı. Oturum `c5-demo-20261125T184646Z-d36da779a116`, Chrome `158.0.8127.38`. Görevler ürün API’sinden `pick_A1 → packing_1`, `pick_C2 → delivery-01` ve `inbound_1 → pick_B1` olarak gönderildi. Fleet Manager görevleri sırasıyla Gamma, Alpha ve Beta’ya atadı.

| Chrome görüntüsü | TSİ | Önceki yaklaşık 1 sn’de TF ötelemesi, Alpha / Beta / Gamma |
| --- | --- | --- |
| `c5-top.png` | 21:47:39 | 0,293 / 0,248 / 0,227 m |
| `c5-oblique.png` | 21:47:40 | 0,198 / 0,267 / 0,173 m |

İki karede de `3/3 TF LIVE`, üç gövde, üç etiket ve üç robotun kendi `/plan` akışından gözlemlenen kesikli rota görüldü. Alpha’dan Gamma’ya, sonra Beta’ya seçimde renkler sabit kaldı. **Yalnız seçili robot** görünür gövdeyi ve rotayı Gamma’dan Beta’ya taşıdı. Plan ve TF izi anahtarları katmanları gizleyip geri açtı. Görsel kabul bu gözlem penceresini kapsar.

## Frontend kontrolleri

- `npm --prefix frontend run build` geçti.
- `C5_UI_PORT=21764 C5_API_PORT=21762 npm --prefix frontend test` ile 35/35 Playwright testi geçti. Paket, seçim boyunca etiket renklerini ve seçili robot filtresini, mevcut TF `STALE` davranışını, plan zaman aşımını ve iz solmasını denetler.
- `git diff --check` geçti.
