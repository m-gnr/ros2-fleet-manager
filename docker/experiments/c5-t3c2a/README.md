# C5-T3C-2A — Salt okunur ölçüm hazırlığı

**Hareket yetkisi yoktur.** Bu dizin launcher, ROS düğümü, actuator veya yeni
trafik servisi içermez. `measurements.py` yalnız kapalı/manifestli T3C-1B
arşivini okur; mevcut tam 14 senaryolu audit'i yeniden kullanır. Tarihsel
kanıtı yeni canlı çalışma veya hareketli frenleme kabulü diye sunmaz.

[Hazırlık ve BLOCKED geçiş raporu](../../../docs/validation/c5/c5-t3c2a-preparation-2026-11-25.md).
[Doğrulanmış komutlar](../../../docs/validation/c5/c5-t3c2a-preparation-commands-2026-11-25.md).

```bash
PYTHONPATH=.:backend .venv/bin/python docker/experiments/c5-t3c2a/measurements.py \
 docs/validation/c5/c5-t3c1b-last-two-2026-11-25 --output /tmp/c5-t3c2a-20261125/readme-review.json
```

Bu komut mevcut `.venv/bin/python` ile çalıştırıldı; ortam/sürüm ve
regresyon komutları yukarıdaki ekte kayıtlıdır. Çıktı yeni bir dosya olmalı ve
girdi arşivinin dışında kalmalıdır. Veri kaynağı canlı WAL/DB olmamalı;
DB hash'i arşiv manifestiyle eşleşir, boş olmayan WAL reddedilir. Özel
salt okunur audit bağlantısı `mode=ro&immutable=1` kullanır; ürün SQLite
veya önceki audit kaynakları değiştirilmez.

Çıktı özgün ölçüm yaşlarını, context/session/command hash'lerini ve farklı
saatlerdeki ham damgaları korur. Saat eşlemesi olmadan FM/native/writer
damgaları birbirinden çıkarılmaz. `writer_steady_ns` POST_UPDATE'dir;
pre-joint-write damgası bulunmadığında UNKNOWN kalır. Hız alanı WORLD-frame
olarak etiketlenir; gerçek gövde-ekseni hızı uydurulmaz.

Gözlenen örnek aralıkları ve küçük durağan hızlar üst sınır veya fren
kalibrasyonu değildir. StopInputs boş, StopEnvelope UNBOUNDED, hareketli
aşama BLOCKED, movement_authorized/ownership_release false kalır.
Nonzero, rearm, rollover, hold/resume veya release API'si yoktur.
