# Demo Launcher V1.1 — telemetry ve güvenli kapanış

17 Kasım 2026 · Taban `origin/main` `33f4759`. Değişiklikler mevcut C5 demo supervisor'ı ve üç robotlu profili kullanır; görev mantığı, V1–V6 arayüzü ve beş saniyelik yeniden bağlanma uyarısı değiştirilmedi.

## Bulgular ve düzeltmeler

- Chrome sayfasının yenilenmesi/DevTools etkileşimi sırasında `/ws/fleet` bağlantısı kapanabiliyor. Uvicorn, aynı anda devam eden bir WebSocket gönderiminde `Unexpected ASGI message 'websocket.send', after sending 'websocket.close'` üretiyordu. Bu özel kapanmış-soket durumu artık normal istemci kopuşu olarak ele alınıyor; diğer `RuntimeError` değerleri yükseltilmeye devam ediyor. Gerçek API snapshot'ı eskidiğinde frontend `STALE` göstermeyi ve beş saniyede yeniden bağlanma uyarısını sürdürür.
- Fleet Manager'ın ROS `MultiThreadedExecutor.shutdown()` çağrısında sınır yoktu; supervisor manager için 10 saniye bekleyip `SIGKILL` gönderiyordu. Executor kapanışı 5 saniye ile sınırlı, spinner thread'i için ayrıca 5 saniye bekleniyor; tamamlanmayan kapanış hata veriyor. Manager'a 20 saniyelik graceful kapanış süresi tanındı. Üst launcher, container durdurmasına 120 saniye ayırıyor ve sahibi olan `c5_demo_start.py` sürecini 150 saniyeye kadar bekliyor; süreci zorla öldürüp başarı saymıyor.
- Üç robotun Nav2 lifecycle istekleri önceki 5 saniyelik ortak deadline içinde tamamlanmıyor ve `SIMULATION_SHUTDOWN clean=false` ile simulation exit `1` oluşuyordu. Her lifecycle grubu için sınır 15 saniyeye çıkarıldı. Herhangi bir zorla öldürme veya sıfır dışı child kodu supervisor'ı hata ile bitiriyor; `shutdown.json` kodları başarı yerine geçmiyor.

## Doğrulamalar

| Kontrol | Sonuç | Kanıt / sınır |
|---|---|---|
| WebSocket kapanma regresyonu | **PASS** | `test_scene_socket_close_during_send_is_a_disconnect`; ASGI kapanış RuntimeError'ı disconnect olarak ele alındı. Diğer RuntimeError'lar için geniş yakalama yok. |
| C5 dashboard testleri | **PASS** | `uv run --with pytest --with fastapi --with starlette --with httpx --with websockets --with pyyaml --with jsonschema python -m pytest tests/test_c5_dashboard.py -q`: 8 passed. Starlette `httpx` deprecation uyarısı mevcut. |
| Derleme/sözdizimi ve diff | **PASS** | Değişen Python dosyaları `py_compile` ve `git diff --check` geçti. |
| Canlı bağlantı ve yeniden bağlanma | **PASS** | `c5-demo-20261117T163808Z-f8a447118edd`, domain 221: Chrome sayfa yenilemesi WS bağlantısını kapattı/açtı; 20 saniye boyunca API source `LIVE`, 3 robot telemetry ve pose LIVE kaldı, panel `Bağlı` ve `3/3 TF LIVE` gösterdi. API logunda kapanmış-soket RuntimeError'ı yoktu. |
| Gerçek Chrome/WebGL2 | **PASS** | Aynı arayüzde görünür 1312×865 canvas, WebGL2 context mevcut ve kayıp değil; üç robot LIVE. Bu kontrol AX fallback metnine dayanmadı. |
| Başlat/kapat çevrimi 1 | **PASS** | `c5-demo-20261117T163808Z-f8a447118edd`: terminalde `Ctrl+C`; API, manager, scene, 3 Executor, 3 Battery Simulator, observer ve simulation kodları `0`; container `0`, `OOMKilled=false`. İlgili portlar boş, launcher süreçleri kalmadı. |
| Başlat/kapat çevrimi 2 | **PASS** | `c5-demo-20261117T163952Z-8b0bdd4c387b`: GUI `3/3 TF LIVE`, 3/3 robot LIVE, WebGL2 doğrulandı. Terminal `Ctrl+C`; tüm child kodları `0`, container `0`, `OOMKilled=false`; portlar boş ve launcher süreçleri kalmadı. |

İlk tanı koşusunda API'ye `SIGTERM` denenmiş ve API child `-15` dönmüştü; Uvicorn shutdown logu temizdi. API ve manager için mevcut `SIGINT` kapanış işleyicileri kullanılarak son iki çevrimde tüm exit kodları `0` doğrulandı. Bu ara koşu kabul çevrimi sayılmadı.

Gerçek bağlantı/snapshot kesintisinde `STALE` ve uyarı davranışı bilerek aynen korunmuştur; bu çalışma kopuşu gizlemez.
