# C5 Aşama 1.7C — Doğrulama komutları

[Doğrulama raporu](c5-stage1-7c-validation-2026-11-07.md)

## Git ve üretim derlemesi

İlk derleme, yeni worktree henüz `b682888` ile aynıyken alındı. Komutlar ilgili worktree kökünden çalıştırıldı. Önizlemeler yalnız loopback üzerinde dinledi.

```sh
git status --short
git branch -avv
git worktree list
git log -1 --oneline
git worktree add -b feat/c5-warehouse-presentation-polish ../ros2-fleet-manager-c5-warehouse-presentation b682888
cd ../ros2-fleet-manager-c5-warehouse-presentation
mkdir -p /tmp/c5-wh17c
npm --prefix frontend ci
npm --prefix frontend run build -- --outDir /tmp/c5-wh17c/base --emptyOutDir
C5_UI_PORT=19517 C5_API_PORT=19518 npm --prefix frontend run preview -- --outDir /tmp/c5-wh17c/base

# Değişiklikten sonra, ayrı terminalde
npm --prefix frontend run build -- --outDir /tmp/c5-wh17c/release --emptyOutDir
C5_UI_PORT=19557 C5_API_PORT=19558 npm --prefix frontend run preview -- --outDir /tmp/c5-wh17c/release
shasum -a 256 frontend/src/scene/assets/warehouse-aisle.glb /tmp/c5-wh17c/release/assets/*.glb
git diff --check
```

Statik Burger önizlemesi, mevcut `Burger` bileşeniyle izole R3F sahnesinde Chrome’dan saydam PNG olarak alındı. Kamera `[.31, .27, -.34]` noktasından `[0, .085, 0]` hedefine baktı. FOV 33°, CSS viewport 336×184, Chrome DPR 2. Bileşenin temas gölgesi kapalıydı. `cwebp -crop 199 26 278 313 -q 86` ile gövdeyi çevreleyen 278×313 alan yerel WebP’ye dönüştürüldü.

## Chrome ve ölçüm

[Aşama 1.7B Chrome ölçüm betiği](c5-stage1-7b-commands-2026-11-07.md#tarayıcı-ölçüm-betiği) iki üretim derlemesine aynı fixture akışını verdi. Betik 5 sn ölçümden önce GLB ve iki TF robotunun çizilmesini bekledi. İlk düzeltme turu `quick` kipiyle yalnız 1440×900’de görüntülendi. Playwright, açık üretim önizlemesini kullandı.

```sh
awk '/^```js$/{body=1;next} body&&/^```$/{exit} body' \
  docs/validation/c5/c5-stage1-7b-commands-2026-11-07.md > /tmp/c5-wh17c/check.mjs
node /tmp/c5-wh17c/check.mjs 19517 /tmp/c5-wh17c/before
node /tmp/c5-wh17c/check.mjs 19557 /tmp/c5-wh17c/release-shots
C5_UI_PORT=19557 C5_API_PORT=19558 C5_BROWSER_TEST_DIR=/tmp/c5-wh17c/playwright \
  npm --prefix frontend test -- --workers=1
```

Dekor kutuları GLB düğümlerinin dönüştürülmüş konum özniteliklerinden ölçüldü. Önceki düzen için `git show b682888:frontend/src/scene/warehouseDecor.ts` ile alınan kaynak, Three.js `Box3.setFromObject(part, true)` ile malzeme gruplamasından önce örneklendi. Yeni düzen için `fleet-visualizer:storage` olayındaki kutular kullanıldı. Burger ekran ölçüsü, 0,138 × 0,192 × 0,178 m boyutlu yönlendirilmiş gövde zarfının sekiz köşesinin kaydedilen TF kökü, kamera ve CSS viewport’a göre projeksiyonudur.

`config/map/map.yaml` ve `map.pgm` üzerinden 254 değerli hücre merkezleri çıkarıldı. 1440×900 başlangıç kamerasından, merkezlerin 0,10 m üzerindeki noktalara çizilen ışınlar depo stok kutularına karşı kontrol edildi. Aynı kontrol canlı TF ve 0,039 m yükseklikteki Nav2 rota köşeleri için tekrarlandı. Ayak izi açıklığı XZ düzleminde en yakın stok kutusuna uzaklıktır. AABB testi, rafların gözeneklerini dolu kabul eden ihtiyatlı bir ölçümdür. [Ham geometri ölçümü](stage1-7c/geometry.json)

## Canlı Fortress

[Aşama 1.6 canlı Fortress komut dizisi](c5-stage1-6-visual-commands-2026-11-06.md#canlı-fortress) aynı biçimde kullanıldı. Her koşu ayrı Compose projesinde ve boş SQLite kanıt dizininde başladı. Son koşu aşağıdaki ortam değerleriyle çalıştı.

```sh
export DDS_TEST_PAYLOAD=fleet-c5-warehouse-17c-release ROS_DOMAIN_ID=130
export C5_UI_PORT=19557 C5_API_PORT=19558 C5_SCENE_PORT=19559
export C5_REQUIRE_COMPACT=1 C5_VERIFY_WAREHOUSE=1 C5_STARTUP_TIMEOUT_MS=360000
export C5_UI_ORIGIN="http://127.0.0.1:$C5_UI_PORT"
export C43_EVIDENCE_DIR=/tmp/c5-wh17c/live-release
```

Dizi çözümlenen Compose konfigürasyonunu kaydetti, var olan image’larla `create --no-build` çalıştırdı ve backend’i iki Nav2 yaşam döngüsü yöneticisi ACTIVE olunca başlattı. Tarayıcıyla eşzamanlı bağımsız TF ve `/plan` okuyucuları çalıştı. Kapanıştan önce SQLite bütünlüğü ve ROS–Chrome karşılaştırması kaydedildi. Ayrı başlangıç ve sahne köprüsü önceki doğrulama düzeniyle aynı kaldı.

```sh
node frontend/tests/live-acceptance.mjs
sqlite3 "$C43_EVIDENCE_DIR/c5-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
python3 docker/simulation-c5/compare_scene_evidence.py "$C43_EVIDENCE_DIR"
awk '/^```python$/{body=1;next} body&&/^```$/{exit} body' \
  docs/validation/c5/c5-stage1-7b-commands-2026-11-07.md > /tmp/c5-wh17c/check-independent.py
python3 /tmp/c5-wh17c/check-independent.py "$C43_EVIDENCE_DIR"
```
