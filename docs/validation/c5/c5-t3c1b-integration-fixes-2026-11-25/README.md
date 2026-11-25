# Üç hedefli entegrasyon koşusunun kanıtları

[Sonuç](../c5-t3c1b-integration-fixes-2026-11-25.md) ·
[Komutlar](../c5-t3c1b-integration-fixes-commands-2026-11-25.md).

- `live/`: üç temiz son koşu ve bütün başarısız/ara tekrarlar; core'lar kayıpsız gzip.
- `build/`: negatif kontrol testleri, başarısız derlemeler ve son başarılı bağımlılık testi.
- `commands/`: gerçek script/CLI log'ları, GDB stack'leri, kaynak/binary ve sonuç manifestleri.
- `runtime-source.tar.gz`: yalnız sabitlenmiş 499 kaynak/test dosyası ve tarihsel test fixture'ı.
- `manifest.json`: 1531 ham dosyanın özgün ve arşiv SHA-256 değerleri.
- `archive-verification.json`, `git-state.json`: bütünlük, korunmuş önceki çalışma ve Git/süreç durumu.

JSON/JSONL/log/SDF/YAML dosyaları kayıpsız gzip olabilir. Mevcut gzip,
SQLite backup ve scriptler kimlik olarak korunur. `.so`/native executable ve
provision anahtarları eklenmedi. Upstream kaynak arşivleri/hash'leri korunur.
Orijinal `/tmp/c5-t3c1b-recovery-20261124` dosyaları silinmedi.

Son hedefli audit üç koşu için başarılıdır; **tam 14'lü kabul değildir**.
Nonzero ve fiziksel release kapalıdır. Commit/push ve T3C-2 yapılmadı.
