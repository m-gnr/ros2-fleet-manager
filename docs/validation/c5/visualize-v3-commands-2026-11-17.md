# Visualize V3 — komut eki

Komutlar `/Users/murat/develop/ros2-fleet-manager-visualize` depo kökünde veya tabloda belirtilen `frontend/` çalışma dizininde 17 Kasım 2026 tarihinde çalıştırıldı.

| Komut | Sonuç |
|---|---|
| `npm run build` (`frontend/`) | Geçti; TypeScript ve Vite üretim derlemesi. |
| `C5_UI_PORT=5202 C5_API_PORT=8202 C5_BROWSER_TEST_DIR=/tmp/visualize-v3-final npm test -- visualize-v1.spec.ts` (`frontend/`) | 2/2 geçti. Son 1,30 model ölçeği ve 34 px boş halka ile üç robot/yaw/state, etiket çakışması ve state paleti denetlendi. Fixture dışı task-catalog isteği için yerel API bulunmadığından beklenen proxy uyarısı oluştu. |
| `C5_UI_PORT=5198 C5_API_PORT=8198 C5_BROWSER_TEST_DIR=/tmp/visualize-v3-warehouse npm test -- warehouse-profile.spec.ts` (`frontend/`) | 4/4 geçti. Yerel API bulunmadığından fixture dışı WebSocket proxy uyarıları oluştu. |
| `C5_UI_PORT=5199 C5_API_PORT=8199 C5_BROWSER_TEST_DIR=/tmp/visualize-v3-routes npm test -- dashboard.spec.ts -g "keeps product and TF validity separate"` (`frontend/`) | 1/1 geçti; gerçek gözlemlenen plan ve epoch temizleme yolu. |
| `git diff --check` | Geçti. |

Toplam hedefli Chrome sonucu 7/7'dir. Test WebSocket/TF verisi fixture'dır; gerçek ROS, Gazebo, fiziksel hareket veya canlı Nav2 görevi bu koşuda çalıştırılmadı.
