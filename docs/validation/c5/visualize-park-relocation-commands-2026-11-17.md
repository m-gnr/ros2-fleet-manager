# Visualize V2 park taşıma — komut eki

Komutlar `/Users/murat/develop/ros2-fleet-manager-visualize` kökünden çalıştırıldı.

| Komut | Sonuç |
|---|---|
| `docker inspect c5-20261117T081139Z-0ead015f09` ve container içi `/tmp/stage1/latest.json` okuması | Bağlı üç robotlu profil, canlı üç `LIVE` robot ve eski yuvalardaki farklı sahiplik doğrulandı. Salt okunur inceleme. |
| `python3` ile `load_config`, `raster`, `check_approaches` | Geçti; yeni istasyon pozları 0,45 m statik dairesel açıklığa sahip. |
| `python3` ile 0,25 m ızgarada 0,45 m açıklıklı BFS | Geçti; iki mevcut robot başlangıcından üç yeni yuvaya statik bağlantı bulundu. Bu Nav2 planı değildir. |
| `python3 frontend/scripts/generate_warehouse_profile.py` ve `--check` | Geçti; frontend özeti güncel YAML ile eşleşiyor. |
| `fleet_config.warehouse_assets.generate(..., 'routes')` | Geçti; yeni YAML'den `warehouse.sdf`, `map.pgm`, `map.yaml`, iki robotun Nav2 parametreleri üretildi. Geçici çıktı silindi. |
| `npm --prefix frontend run build` | Geçti; TypeScript ve Vite. |
| `C5_UI_PORT=18461 C5_API_PORT=18462 npm --prefix frontend test -- visualize-v1.spec.ts warehouse-profile.spec.ts` | Son koşu **5/5 geçti**. İlk hedefli koşu da 5/5 geçti; ara koşuda `park_2` hover beklentisi görünür balon bulamadı (4/5), `park_1` hover denetimine dönülerek son koşu geçirildi. `park_2` hover'ı ayrıca doğrulanmadı. Gerçek API bağlı değil; fixture dışı proxy isteği hata verdi. |
| `python3 -m pytest tests/test_warehouse_grid.py -q` | **Çalışmadı:** toplamada `ModuleNotFoundError: fastapi`. |
| `git diff --check` | Geçti. |

Gerçek ROS 2/Nav2 hareket koşusu yapılmadı; çalışan container farklı çalışma ağacına bağlıydı ve güvenlik akışı/aktif oturum değiştirilmedi.
