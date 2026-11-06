# C5 / Aşama 1 — Kısa performans ölçümü

`fleet-c5-accept` koşusu · İki gerçek Gazebo robotu · Apple Silicon macOS 26.6.2 · ARM64 Docker Desktop · Google Chrome 156.0.8078.80 headless. Tarayıcı ölçümü 1440 × 900 ve derlenmiş Vite paneliyle, tamamlanan görevler sonrası 5,07 sn boyunca alındı. [Canlı kabul](c5-stage1-validation-2026-11-06.md)

| Ölçüm | Değer |
|---|---:|
| Chrome `requestAnimationFrame` sıklığı | 60,0 Hz |
| Chrome frame aralığı p95 | 16,7 ms |
| Konva görünür canvas çizimi | 20 çizim, aralık p95 316,4 ms |
| Frontend kullanılan JS heap | 7,07 MiB |
| Chrome süreçleri CPU / RSS toplamı | %7,52 tek çekirdek / 877,28 MiB |
| FastAPI CPU / RSS | %0,59 tek çekirdek / 43,98 MiB |
| WebSocket | 20 mesaj, 3,94 Hz |
| WebSocket snapshot boyutu | Ortalama 2.623 bayt, en çok 2.632 bayt |
| FastAPI başlatma → yeni oturumun ilk geçerli snapshot'ı | 1,108 sn |
| FastAPI durdurma → yeni oturumun ilk geçerli snapshot'ı | 1,402 sn |

RAF, Chrome frame callback hızıdır. Konva çizimi yeni veri veya kamera hareketiyle tetiklenir. İki aralık farklı olayları ölçer. CPU, CDP süreç zamanı ve FastAPI için Linux `/proc` tick farkından hesaplandı. Chrome bellek toplamı paylaşılan sayfaları süreç başına sayabilir. JS heap tek ölçüm noktasıdır.

## Fleet Manager etkisi

| Terminal sonrası ölçüm | Yayıncı açık | Yayıncı kapalı |
|---|---:|---:|
| Süre / tur | 15,04 sn / 295 | 8,05 sn / 158 |
| 50 ms consumer sürüş aralığına ek gecikme p95 | 1,98 ms | 1,83 ms |
| Fleet Manager süreç CPU'su | %28,37 | %26,87 |
| Fleet Manager süreç RSS | 92,78 MiB | 93,16 MiB |

Aralık denetimi C4 TICK, tek Outbox gönderim çağrısı ve kalan uyku süresini kapsar. Açık pencerede tarayıcı 5,07 sn ölçüldü ve pencerenin sonuna doğru kapandı. Kapalı pencerede snapshot üretimi devre dışıydı. Açık ve kapalı ölçümler aynı senaryoda ardışık alındı. Zamanlama jitter'ı ve DDS/RCLPy işi de süreç CPU'suna dahildir. Bu iki kısa örnek gözlenen farkı verir. Tekrarlı A/B, tepe yük, uzun süreli bellek, başka platform veya üç robot performansı ölçülmedi.
