# Visualize V4 — komut eki

Komutlar `/Users/murat/develop/ros2-fleet-manager-visualize` depo kökünde veya tabloda belirtilen `frontend/` çalışma dizininde 17 Kasım 2026 tarihinde çalıştırıldı.

| Komut | Sonuç |
|---|---|
| `npm run build` (`frontend/`) | Geçti; TypeScript ve Vite üretim derlemesi. |
| `C5_UI_PORT=5214 C5_API_PORT=8214 C5_BROWSER_TEST_DIR=/tmp/visualize-v4-final npm test -- visualize-v1.spec.ts --reporter=line` (`frontend/`) | 2/2 geçti. Üç robot/yaw/state ve görsel kadraj regresyonlarına V4 zemin segmenti, raf gölgesi ve kapalı shadow map denetimi eklendi. Yerel API bulunmadığından fixture dışı task-catalog isteğinde beklenen proxy uyarısı oluştu. |
| `C5_UI_PORT=5215 C5_API_PORT=8215 C5_BROWSER_TEST_DIR=/tmp/visualize-v4-warehouse npm test -- warehouse-profile.spec.ts --reporter=line` (`frontend/`) | 4/4 geçti. Yerel API bulunmadığından fixture dışı WebSocket proxy uyarıları oluştu. |
| `C5_UI_PORT=5216 C5_API_PORT=8216 C5_BROWSER_TEST_DIR=/tmp/visualize-v4-routes npm test -- dashboard.spec.ts -g "keeps product and TF validity separate" --reporter=line` (`frontend/`) | Eşzamanlı üç test sürecinin ilk koşusunda 0/1; plan trace değeri 5 saniye içinde oluşmadı. |
| `C5_UI_PORT=5217 C5_API_PORT=8217 C5_BROWSER_TEST_DIR=/tmp/visualize-v4-routes-rerun npm test -- dashboard.spec.ts -g "keeps product and TF validity separate" --reporter=line` (`frontend/`) | Tek başına yeniden koşuda 1/1 geçti; gözlemlenen plan ve epoch temizleme yolu. |
| V3/V4 kısa trace örnekleri | Aynı `visualize-v1.spec.ts` fixture'ında geçici sayaçla 2 saniye ölçüldü; ölçüm kodu tutulmadı. V3: 228 draw call, 18.788 üçgen, 42 trace frame. V4: 229 draw call, 18.688 üçgen, 47 trace frame. |
| `git diff --check` | Geçti. |

Son seri hedefli sonuç 7/7'dir. Test WebSocket/TF verisi fixture'dır; gerçek ROS, Gazebo, fiziksel hareket veya canlı Nav2 görevi bu koşuda çalıştırılmadı.
