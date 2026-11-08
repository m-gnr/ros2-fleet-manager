# C5 Aşama 1.7E — Doğrulama komutları

[Doğrulama raporu](c5-stage1-7e-validation-2026-11-08.md)

Komutlar ayrı worktree kökünden çalıştırıldı. Başlangıç derlemesi kod düzenlemesinden önce `23823f6` üzerinden alındı. Son derleme ve başlangıç derlemesi aynı yerel Chrome ve ölçüm betiğini kullandı. Canlı koşu, C4.5 şarj kabul profili ve 1.5 salt okunur köprü katmanıyla çalıştı.

```sh
git worktree add -b feat/c5-warehouse-functional-layout ../ros2-fleet-manager-c5-warehouse-functional 23823f6
cd ../ros2-fleet-manager-c5-warehouse-functional
mkdir -p /tmp/c5-wh17e
npm --prefix frontend ci
# Düzenlemeden önce:
npm --prefix frontend run build -- --outDir /tmp/c5-wh17e/base --emptyOutDir
# Düzenlemeden sonra:
npm --prefix frontend run build -- --outDir /tmp/c5-wh17e/release --emptyOutDir

# Ayrı terminallerde:
C5_UI_PORT=19717 C5_API_PORT=19728 npm --prefix frontend run preview -- --outDir /tmp/c5-wh17e/base
C5_UI_PORT=19727 C5_API_PORT=19728 npm --prefix frontend run preview -- --outDir /tmp/c5-wh17e/release

C5_UI_PORT=19727 C5_API_PORT=19728 C5_BROWSER_TEST_DIR=/tmp/c5-wh17e/playwright \
  npm --prefix frontend test -- --workers=1
# Performans için canlı konteynerler ve diğer Chrome testleri kapalıyken sırayla:
node frontend/tests/warehouse-visual.mjs 19717 /tmp/c5-wh17e/final/before
node frontend/tests/warehouse-visual.mjs 19727 /tmp/c5-wh17e/final/after
# 1440×900 ilk kare farkı için ters sıra tekrar:
node frontend/tests/warehouse-visual.mjs 19727 /tmp/c5-wh17e/final/startup-after quick
node frontend/tests/warehouse-visual.mjs 19717 /tmp/c5-wh17e/final/startup-before quick
git diff --check
```

## Canlı Fortress ve bağımsız ölçümler

[Aşama 1.6 canlı Fortress dizisi](c5-stage1-6-visual-commands-2026-11-06.md#canlı-fortress) aşağıdaki ortamla kullanıldı. `config --format json` ile worktree, config, salt okunur kaynak bağlamaları ve ayrı boş kanıt dizini denetlendi. `create --no-build` ile mevcut image’lar kullanıldı. Simülasyon ve köprü başladıktan sonra iki Nav2 yaşam döngüsü yöneticisinin ACTIVE kaydı beklendi. Bağımsız okuyucular backend’den önce başladı. Canlı Chrome, son üretim önizlemesine bağlandı.

```sh
export DDS_TEST_PAYLOAD=fleet-c5-warehouse-17e ROS_DOMAIN_ID=132
export C5_UI_PORT=19727 C5_API_PORT=19728 C5_SCENE_PORT=19729
export C5_REQUIRE_COMPACT=1 C5_VERIFY_WAREHOUSE=1 C5_STARTUP_TIMEOUT_MS=360000
export C5_UI_ORIGIN="http://127.0.0.1:$C5_UI_PORT"
export C43_EVIDENCE_DIR=/tmp/c5-wh17e/live
# Bağımsız TF/plan okuyucuları, Chrome testi ve kapanış:
# yukarıda bağlantısı verilen canlı Fortress dizisi.
sqlite3 "$C43_EVIDENCE_DIR/c5-charging.sqlite3" 'PRAGMA integrity_check; PRAGMA foreign_key_check;'
python3 docker/simulation-c5/compare_scene_evidence.py "$C43_EVIDENCE_DIR"
python3 frontend/tests/verify-warehouse-sources.py "$C43_EVIDENCE_DIR" \
  > "$C43_EVIDENCE_DIR/independent-operation-points.json"
node frontend/tests/warehouse-clearance.mjs "$C43_EVIDENCE_DIR" \
  /tmp/c5-wh17e/final/after/metrics.json "$C43_EVIDENCE_DIR/independent-operation-points.json"
```

Geometri denetimini ROS ortamı olmadan tekrar etmek için [ölçüm girdilerini](stage1-7e/live/geometry-inputs.tar.gz) boş bir dizine açıp bu dizini ilk parametre olarak verin. Diğer iki parametre [Chrome ölçümü](stage1-7e/after/metrics.json) ve [bağımsız kaynak karşılaştırmasıdır](stage1-7e/live/independent-operation-points.json). Arşivde canlı TF/Path örnekleri ve Chrome’un dekor/işaret kutuları vardır. Düşük seviye ağ paketleri ve SQLite dosyası arşive dahil değildir.
