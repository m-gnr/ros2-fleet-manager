# Visualize V6 — komut eki

17 Kasım 2026. Bütün komutlar `/Users/murat/develop/ros2-fleet-manager-visualize` depo kökünden çalıştırıldı. Playwright `channel: chrome`, 1440 × 900 viewport ve mock WS/TF kullanır.

| Komut | Sonuç |
|---|---|
| `npm --prefix frontend run build` | V6 ilk uygulama ve son kaynak kontrolünde geçti. Mevcut Zod annotation uyarıları var. |
| `C5_UI_PORT=5231 C5_API_PORT=8231 C5_BROWSER_TEST_DIR=/tmp/visualize-v6-first npm --prefix frontend test -- visualize-v1.spec.ts warehouse-profile.spec.ts --workers=1 --reporter=line` | 7/7 geçti (24,8 sn); ilk görseller ve FPS örneği incelendi. |
| `C5_UI_PORT=5232 C5_API_PORT=8232 C5_BROWSER_TEST_DIR=/tmp/visualize-v6-final npm --prefix frontend test -- visualize-v1.spec.ts warehouse-profile.spec.ts dashboard.spec.ts -g 'three live robots\|robot state palette\|decorative vehicles\|C5-A starts\|profile hash retains\|catalog permissions\|floor text names\|keeps product and TF validity separate' --workers=1 --reporter=line` | Son kontrol 8/8 geçti (27,3 sn); dış geometri sınır denetimi ve TF/Path ayrımı dahil. |
| `git diff --check` | Geçti. |

Yukarıdaki Markdown tablosunda regex ayırıcıları `\|` ile kaçırılmıştır; terminalde kullanılan tek tırnaklı regex içindeki ayırıcılar düz `|` karakteridir.

FPS ölçümü `visualize-v1.spec.ts` içindeki `measure()` ile yapılır. Çevre kapalı/açık, kararlı kamera ve aynı fixture altında her RAF'ta canvas'a trace-only `fleet-visualizer:benchmark-frame` event'i gönderilir. Render event sayısı ve ilk/son event süresinden FPS hesaplanır; orta frame'in draw call/üçgen/geometri sayaçları alınır. Son [ham JSON](visualize-v6-screenshots/exterior-render-cost.json) ve Chrome ekran görüntüleri kalıcı kanıt klasöründedir.

Hareket durdurma testi çevre kutusunu kapatıp tick/fazın sabit kaldığını denetler. Ardından Chrome'da kontrollü `document.hidden` getter'ı ve `visibilitychange` event'iyle aynı denetim yapılır; getter kaldırılıp doğal görünürlük geri getirilir. Yeniden başlatmada faz sıçraması denetlenir. Tam 80 saniyelik gerçek zaman döngüsü yerine gidiş/dönüş/durma sınırları saf hareket fonksiyonundan örneklenir.

Fixture dışında kalan task-catalog/WS isteklerinde yerel API olmadığı için proxy ECONNREFUSED uyarıları oluştu; bunlar canlı backend kabulü sayılmaz. Commit/push, simülasyon başlatma veya navigasyon komutu yapılmadı.
