# C5 Aşama 1.7D — Doğrulama komutları

[Doğrulama raporu](c5-stage1-7d-validation-2026-11-07.md)

## Ayrı worktree ve üretim derlemeleri

Komutlar ilgili worktree kökünden çalıştırıldı. Başlangıç derlemesi kaynak düzenlemesinden önce alındı. Chrome önizlemeleri loopback üzerinde çalıştı.

```sh
git worktree add -b feat/c5-warehouse-zones-and-walls ../ros2-fleet-manager-c5-warehouse-zones b21c642
cd ../ros2-fleet-manager-c5-warehouse-zones
mkdir -p /tmp/c5-wh17d
npm --prefix frontend ci
npm --prefix frontend run build -- --outDir /tmp/c5-wh17d/base --emptyOutDir

# Başlangıç önizlemesi, ayrı terminalde
C5_UI_PORT=19617 C5_API_PORT=19618 npm --prefix frontend run preview -- --outDir /tmp/c5-wh17d/base

# Görsel değişiklikten sonra, ayrı terminalde
npm --prefix frontend run build -- --outDir /tmp/c5-wh17d/release --emptyOutDir
C5_UI_PORT=19657 C5_API_PORT=19658 npm --prefix frontend run preview -- --outDir /tmp/c5-wh17d/release
```

## Üretim Chrome

İki derleme, aynı 2 Hz ürün snapshot’ı ve robot başına 10 Hz kontrollü TF örneğiyle çalıştırıldı. Betik, ölçümden önce GLB ve iki robotun çizilmesini bekler. İlk görsel tur için `quick` kipi yalnız 1440×900’ü çeker. Chrome testleri Vite üretim önizlemesine bağlanır.

```sh
awk '/^```js$/{body=1;next} body&&/^```$/{exit} body' \
  docs/validation/c5/c5-stage1-7b-commands-2026-11-07.md > /tmp/c5-wh17d/check.mjs
node /tmp/c5-wh17d/check.mjs 19617 /tmp/c5-wh17d/before
node /tmp/c5-wh17d/check.mjs 19657 /tmp/c5-wh17d/iteration quick
node /tmp/c5-wh17d/check.mjs 19657 /tmp/c5-wh17d/after
C5_UI_PORT=19657 C5_API_PORT=19658 C5_BROWSER_TEST_DIR=/tmp/c5-wh17d/playwright \
  npm --prefix frontend test -- --workers=1
git diff --check
```

## Canlı iki robotlu Fortress

[Aşama 1.6 canlı Fortress dizisi](c5-stage1-6-visual-commands-2026-11-06.md#canlı-fortress) aşağıdaki ortamla çalıştırıldı. Çözümlenen Compose bağlamaları bu worktree ve boş kanıt dizinini gösterdi. Var olan üç image `create --no-build` ile kullanıldı. İki Nav2 yaşam döngüsü yöneticisi ACTIVE ve son frontend derlemesi hazır olduğunda backend başlatıldı. Bağımsız ROS okuyucuları iki robotun map → base_link TF ve Nav2 planlarını kaydetti.

```sh
export DDS_TEST_PAYLOAD=fleet-c5-warehouse-17d ROS_DOMAIN_ID=131
export C5_UI_PORT=19657 C5_API_PORT=19658 C5_SCENE_PORT=19659
export C5_REQUIRE_COMPACT=1 C5_VERIFY_WAREHOUSE=1 C5_STARTUP_TIMEOUT_MS=360000
export C5_UI_ORIGIN="http://127.0.0.1:$C5_UI_PORT"
export C43_EVIDENCE_DIR=/tmp/c5-wh17d/live

# Canlı dizi içindeki tarayıcı ve kaynak karşılaştırmaları
node frontend/tests/live-acceptance.mjs
sqlite3 "$C43_EVIDENCE_DIR/c5-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
python3 docker/simulation-c5/compare_scene_evidence.py "$C43_EVIDENCE_DIR"
awk '/^```python$/{body=1;next} body&&/^```$/{exit} body' \
  docs/validation/c5/c5-stage1-7b-commands-2026-11-07.md > /tmp/c5-wh17d/check-independent.py
python3 /tmp/c5-wh17d/check-independent.py "$C43_EVIDENCE_DIR"
```

## Geometri ölçümü

Tarayıcı, GLB yüklendiğinde duvar ve stok gruplarının dünya uzayında eksen hizalı kutularını kaydetti. Aşağıdaki betik bağımsız ROS okumalarını Three.js XZ düzlemine çevirir. Ardışık TF ve aynı plan içindeki Nav2 noktaları arasında her doğru parçasının dekorun yatay ayak izine en kısa uzaklığını hesaplar. 1440×900 varsayılan kamerasından, parçalar boyunca en fazla 5 cm aralıkla TF için 0,10 m ve Nav2 için 0,039 m yüksekliğe görüş ışını atar. Test, temsili kapı ve rafların boşluklarını dolu sayan ihtiyatlı grup kutuları kullanır.

```sh
node frontend/tests/warehouse-clearance.mjs "$C43_EVIDENCE_DIR" /tmp/c5-wh17d/after/metrics.json
```
