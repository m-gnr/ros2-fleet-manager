# C5-B6B.6 — Komut eki

Depo kökü: `/Users/murat/develop/ros2-fleet-manager-c5-a-demo-integration`, dal `main`.
Başlangıç cwd'si `main-legacy` idi; mevcut main worktree kullanıldı, checkout yapılmadı.
Mevcut izlenen/izlenmeyen kullanıcı değişiklikleri korunur; commit/push yoktur.

Hedefli koşu (ürün servisi/dünya başlatmaz):

```bash
docker run --rm --network none -v "$PWD:/repo:ro" c5-b6b5-build:local \
  bash /repo/docker/experiments/c5-b6b6/run.sh
```

Image ID: `sha256:12d8398f68b6f8d43085ffd32236254b5753726c8c272a2c5b961889bc377139`.
Çalıştırıcı C++17 shared test ABI'yi `/tmp/b6b6-lease.so` olarak derler;
B6B.5 Lease.hh değişmez. ROS domain 186 ve IGN partition yalnız izole test
alanıdır, ürün ayarı/kimlik doğrulaması değildir. Read-only repo mount; dış ağ yok.
Timer/ROS readback içinde native lease çağrılır; fake gate ve iki bridge ayrı
process group'ları SIGKILL ile sonlandırılır; cleanup yalnız bu süreçleri kapatır.

İlk setup nounset, iki Python path ve discovery/probe callback yarış ve restart discovery hatalarının
logları [ham dizinde](c5-b6b6-authorization-2026-11-15/) korunur.
ROS setup sırasında nounset kapatıldı; setup'ın PYTHONPATH'i korundu;
producer subscription discovery el sıkışması eklendi; negatif discovery
probe callback'i komut sonucu sayılmayacak şekilde bekleme düzeltildi.
Restart discovery probe'ları yalnız geçersiz mesaj olarak tekrarlanır; uçtan uca
alındığı görülmeden süreli yetkili bilet üretilmez. Süre denetimi gevşetilmedi.
Bu ilk koşular başarı diye sayılmaz.

Diyagram üretimi yerel mevcut Mermaid CLI ile yapıldı:

```bash
/Users/murat/.npm/_npx/bb964472b4759b27/node_modules/.bin/mmdc \
  -i docs/diagrams/src/actuator-command-authorization.mmd \
  -o docs/diagrams/svg/actuator-command-authorization.svg
```

Ürün baseline: çalışma öncesi `git ls-files` içindeki docs dışı 350 dosyanın
mevcut byte SHA-256 değerleri. Hedefli test tamamını karşılaştırır; kullanıcı
ön değişikliklerini HEAD'e geri almaz. `motion_envelope: null` config baseline
kapsamındadır. Yeni test dosyaları ürüne import edilmez. Geniş regresyon yoktur.
