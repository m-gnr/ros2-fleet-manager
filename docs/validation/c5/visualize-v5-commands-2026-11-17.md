# Visualize V5 — komut eki

17 Kasım 2026, bütün komutlar `/Users/murat/develop/ros2-fleet-manager-visualize` depo kökünden çalıştırıldı. Chrome testleri Playwright `channel: chrome`, 1440 × 900 görünüm ve mock WS/TF verisi kullanır.

| Komut | Sonuç |
|---|---|
| `npm --prefix frontend run build` | V5 öncesi V4 build'i geçti. |
| `C5_UI_PORT=5225 C5_API_PORT=8225 C5_BROWSER_TEST_DIR=/tmp/visualize-v5-baseline npm --prefix frontend test -- visualize-v1.spec.ts --reporter=line` | V5 öncesi 2/2 geçti; üstten/eğik görüntüler incelendi. |
| `C5_UI_PORT=5226 C5_API_PORT=8226 C5_BROWSER_TEST_DIR=/tmp/visualize-v5-first npm --prefix frontend test -- visualize-v1.spec.ts --reporter=line` | İlk V5 görünümünde mevcut regresyon 2/2 geçti. |
| `npm --prefix frontend run build` | Son kaynakla geçti. Bir ara taslakta TS tuple hatası bulundu ve düzeltildi. |
| `C5_UI_PORT=5227 C5_API_PORT=8227 C5_BROWSER_TEST_DIR=/tmp/visualize-v5-final npm --prefix frontend test -- visualize-v1.spec.ts warehouse-profile.spec.ts --workers=1 --reporter=line` | 5/6; testin takip modu örnekleme yarışı. |
| `C5_UI_PORT=5228 C5_API_PORT=8228 C5_BROWSER_TEST_DIR=/tmp/visualize-v5-final-rerun npm --prefix frontend test -- visualize-v1.spec.ts warehouse-profile.spec.ts --workers=1 --reporter=line` | 5/6; testin target değerindeki yaklaşık 5×10⁻¹⁷ farkı kesin eşitlikle kıyaslaması. |
| `C5_UI_PORT=5230 C5_API_PORT=8230 C5_BROWSER_TEST_DIR=/tmp/visualize-v5-verified npm --prefix frontend test -- visualize-v1.spec.ts warehouse-profile.spec.ts --workers=1 --reporter=line` | Mod beklemesi ve sayısal tolerans düzeltildikten sonra 6/6 geçti (19,8 sn). |
| `C5_UI_PORT=5229 C5_API_PORT=8229 C5_BROWSER_TEST_DIR=/tmp/visualize-v5-routes npm --prefix frontend test -- dashboard.spec.ts -g 'keeps product and TF validity separate' --workers=1 --reporter=line` | 1/1 geçti. |
| `git diff --check` | Geçti. |

Kısa maliyet örneklemesi `visualize-v1.spec.ts` içinde aynı kararlı kamerada çevre kapalı/açık 2,5 saniyelik frame event pencereleriyle yapılır; ortadaki frame'in draw call/üçgen/geometri sayaçları JSON'a kaydedilir. Bu ölçüm sürekli render FPS benchmark'ı değildir. Doğrulanmış görseller ve JSON [kalıcı kanıt klasöründe](visualize-v5-screenshots/).

Commit/push yapılmadı; simülasyon başlatılmadı veya navigasyon komutu gönderilmedi.
