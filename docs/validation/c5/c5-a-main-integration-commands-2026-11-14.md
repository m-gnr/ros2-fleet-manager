# C5-A — Main entegrasyon komut ve kanıt eki

14 Kasım 2026. [Checkpoint raporu](c5-a-main-integration-2026-11-14.md). Komutlar yalnız `/Users/murat/develop/ros2-fleet-manager-c5-a-demo-integration` worktree'sinde çalıştırıldı. Main/feature worktree'lerinde stash, reset, clean, rebase, commit veya push yapılmadı.

## Üç taraflı kaynak karşılaştırması

- Base: `git rev-parse main` → `6bf27e4c72e086881eff6d2f38e78e78ce231ba1`.
- Main yerel tracked farkı: `git diff --binary | git -C <integration-worktree> apply -`; uygulanan diff 12 dosya, 210 ekleme / 14 silme.
- Feature karşılaştırması: `git diff --name-status main...feat/c5-auto-charging-integration` ve feature worktree `git status --short`; HEAD `ddf65e31b30d6ea49ce8c10eccf6e98879713600`. C5-A raporu/komut eki haricindeki değişiklikler taşınmadı.

## Testler

```sh
PYTHONPATH=ros2_ws/src/fleet_battery_simulator:backend /Users/murat/develop/ros2-fleet-manager-c5-dashboard/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_c5_dashboard.py tests/test_battery_control.py tests/test_battery_control_ros2.py tests/test_task_review_holds.py tests/test_warehouse_grid.py
```

Sonuç: **26 passed, 1 skipped**. Atlanan test mevcut host'ta ROS 2 ortamı istedi.

```sh
C5_UI_PORT=20281 C5_API_PORT=20282 C5_BROWSER_TEST_DIR=/tmp/c5-a-integration-playwright /Users/murat/develop/ros2-fleet-manager/frontend/node_modules/.bin/playwright test --config frontend/playwright.config.ts frontend/tests/dashboard.spec.ts
```

Sonuç: **23 passed**; dashboard Playwright senaryoları Chrome kanalında çalıştı. Bağımlılık bağlantısı için yalnız target worktree içinde geçici, ignored `frontend/node_modules` symlink'i kullanıldı ve sonra kaldırıldı.

## Tek canlı görev denemesi

Target kaynakları read-only mount edildi; yeni container `fleet-c5-a-integration-live-20261114`, `ROS_DOMAIN_ID=187`, backend/UI portları `20282/20281` ve yeni kanıt kökü `/tmp/c5-a-integration-evidence-20261114` kullanıldı. Mevcut `docker/simulation-warehouse-grid/stage1_run.py` launcher'ı çalıştı. Chrome formundan bir LOW `pick_A1 → pick_B1` görevi gönderildi. Gerçek görev kabul edildi ve `EXECUTING` gözlendi; koşu kullanıcı yönlendirmesiyle kontrollü SIGINT ile kapatıldı. Container child süreçleri 0 koduyla sonlandı; DB checkpoint'inde görev `EXECUTING` kaldı. Bu kanıt `COMPLETED` veya başarılı Nav2 pickup/dropoff iddiası değildir.
