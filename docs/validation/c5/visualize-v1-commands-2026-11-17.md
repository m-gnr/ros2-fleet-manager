# Visualize V1 — komut eki

Komutlar depo kökünden, `/Users/murat/develop/ros2-fleet-manager-visualize` içinde çalıştırıldı.

| Komut | Sonuç |
|---|---|
| `npm --prefix frontend ci` | Geçti; 99 paket kuruldu. |
| `npm --prefix frontend run build` | Geçti; TypeScript ve Vite üretim derlemesi. |
| `C5_UI_PORT=18451 C5_API_PORT=18452 npm --prefix frontend test -- visualize-v1.spec.ts warehouse-profile.spec.ts` | 4/4 geçti. API fixture dışı `/api/task-catalog` istekleri yerel API servisi çalışmadığından proxy hatası verdi; hedefli test sonucu geçerli. |
| `C5_UI_PORT=18451 C5_API_PORT=18452 npm --prefix frontend test -- warehouse-profile.spec.ts dashboard.spec.ts` | 16/25 geçti, 9 kaldı. Sekiz eski GLB/şematik beklentisi ve bir eski görev etiketi beklentisi; ayrıntılar [raporda](visualize-v1-validation-2026-11-17.md). |
| `git diff --check` | Geçti. |

Geri bildirimdeki eşit boyut düzeltmesinden sonra üretim derlemesi ve dört hedefli test yeniden çalıştırıldı: ikisi de geçti. Test, Chrome sahnesinde iki rolün 0,92 m iç kare ve 1,24 m görsel taban ölçüsünü okudu. Ekran görüntüleri aynı koşudan yenilendi.

Gerçek ROS/Gazebo çalıştırılmadı; test fixture'ı fiziksel hareket veya canlı ürün kabulü kanıtı değildir.
