# Visualize V2 — komut eki

Komutlar `/Users/murat/develop/ros2-fleet-manager-visualize` depo kökünden çalıştırıldı.

| Komut | Sonuç |
|---|---|
| `npm --prefix frontend run build` | Geçti; TypeScript ve Vite üretim derlemesi. |
| `C5_UI_PORT=18451 C5_API_PORT=18452 npm --prefix frontend test -- visualize-v1.spec.ts warehouse-profile.spec.ts` | 5/5 geçti. `visualize-v1.spec.ts` dosyası V1'den gelen görsel regresyon testini V2 bilgi balonu davranışına genişletir. Yerel API servisi çalışmadığı için fixture dışı `/api/task-catalog` isteği proxy hatası verdi; hedefli test sonucu geçti. |
| `C5_UI_PORT=18451 C5_API_PORT=18452 npm --prefix frontend test -- dashboard.spec.ts` | 14/23 geçti, 9 kaldı. Kalanların tümü eski GLB beklentisinde `grid` aldı. |
| `git diff --check` | Geçti. |

Mock WebSocket/TF fixture'ı canlı ROS veya Gazebo koşusu değildir. Başarısız eski testler ve koşulmayan entegrasyon ayrı tutuldu.
