# C5 Git checkpoint — komut ve sonuç eki

12 Kasım 2026 · [Denetim raporu](git-checkpoint-2026-11-12/README.md)

Ürün komutları C5 worktree kökünden; izlenen kaynak kontrolü aşağıdaki Git export dizininin kökünden çalıştırıldı. Başlangıç denetimi 11 Kasım’da başladı, devam kontrolü 12 Kasım’da tekrarlandı. Bu ek yeni canlı simülasyon/test kabulü değildir.

## Git başlangıcı ve devam kontrolü

```sh
git worktree list --porcelain
git branch -avv
git status --short
git log --all --graph --decorate --oneline -35
git remote -v
git fetch origin
git branch --show-current
git diff --cached --stat
git rev-parse HEAD origin/feat/c5-warehouse-grid-layout origin/main main
git rev-list --left-right --count HEAD...origin/feat/c5-warehouse-grid-layout
git ls-files -z
git ls-files --others --exclude-standard -z
git ls-files --others --ignored --exclude-standard -z
```

Başlangıç ve devam: C5 `174ff21`, origin C5 `30373ff`, ahead/behind `14 0`, index boş; main/origin-main `32e23fc`. Python pathlib/hashlib ile bütün değişmiş ve izlenmeyen dosyaların SHA-256 değerleri alındı. Ignored node_modules/install/build/cache grupları ile DB/OS kalıntıları ayrı değerlendirildi. İlk envanter ve sınıflandırma rapora bağlandı.

Başlangıç worktree/dal eşlemesi:

```text
worktree /Users/murat/develop/ros2-fleet-manager
HEAD 32e23fce62026a1d50aa2f04e85c8c38a6ee5d76
branch refs/heads/main

worktree /Users/murat/develop/ros2-fleet-manager-c5-2-safe-task-management
HEAD b7fcb05c3cbcc24aaa6439ff494e459bc4d4549f
branch refs/heads/feat/c5-2-safe-task-management

worktree /Users/murat/develop/ros2-fleet-manager-c5-3d-dashboard
HEAD 72e500eb84e0409f220779adab5035a2bcf28f0f
branch refs/heads/feat/c5-3d-operations-dashboard

worktree /Users/murat/develop/ros2-fleet-manager-c5-dashboard
HEAD 76a80abb5d35ca5a4e7005b145d0c83ce3104b0e
branch refs/heads/feat/c5-readonly-dashboard

worktree /Users/murat/develop/ros2-fleet-manager-c5-ui-polish
HEAD b7fcb05c3cbcc24aaa6439ff494e459bc4d4549f
branch refs/heads/feat/c5-dashboard-ui-polish

worktree /Users/murat/develop/ros2-fleet-manager-c5-warehouse
HEAD b682888ca4c0c0a044b70dfb8f5d91bde563ff33
branch refs/heads/feat/c5-warehouse-model-integration

worktree /Users/murat/develop/ros2-fleet-manager-c5-warehouse-functional
HEAD b7b144b78da0957fa5a3b4919fe2893cdd948a99
branch refs/heads/feat/c5-warehouse-functional-layout

worktree /Users/murat/develop/ros2-fleet-manager-c5-warehouse-grid
HEAD 174ff21e01c898bf12c857b2d3b1a854a8cd8894
branch refs/heads/feat/c5-warehouse-grid-layout

worktree /Users/murat/develop/ros2-fleet-manager-c5-warehouse-presentation
HEAD b21c642a173740f23780b9dc2c70d172b38b2d3e
branch refs/heads/feat/c5-warehouse-presentation-polish

worktree /Users/murat/develop/ros2-fleet-manager-c5-warehouse-zones
HEAD 23823f6f53bcf2ef1ce9d1cb19cb86ace5691e18
branch refs/heads/feat/c5-warehouse-zones-and-walls

worktree /Users/murat/develop/ros2-fleet-manager-multi-robot
HEAD 7cf6e7edf31bcf54c4554bf1c1fe2f72be044036
branch refs/heads/feat/fleet-visualizer-multi-robot

worktree /Users/murat/develop/ros2-fleet-manager-nav2-routes
HEAD f3e39017514b5ee2ef2da199c2f8615b9b5d25b6
branch refs/heads/feat/fleet-visualizer-nav2-routes

worktree /Users/murat/develop/ros2-fleet-manager-visual-upgrade
HEAD 015865403d5bf3cae62647fbc149c5bbcee620a5
branch refs/heads/feat/fleet-visualizer-visual-upgrade

worktree /Users/murat/develop/ros2-fleet-manager-visualizer
HEAD 4503c25b7bc10cc91ee97ac230e1c70e2851ecb8
branch refs/heads/feat/fleet-visualizer-3d-mvp

```

Diğer çalışma ağaçlarının başlangıç HEAD/status/hash kayıtları [koruma manifestindedir](git-checkpoint-2026-11-12/other-worktree-baselines.json). Ana worktree’nin 9 kullanıcı dosyası rapor/PDF/araştırma ve docs değişiklikleridir; içerikleri bu işe katılmadı.

## Staging ve commit

A/B/C/D dosyaları ayrı açık listelerle `git add -- <dosyalar>` ile index’e alındı. `git diff --cached --name-only` tam listenin eşitliğiyle kontrol edildi; `git diff --cached --binary` incelendi ve geçici denetim dizinine kaydedildi. Her grupta `git diff --cached --check` sonucu 0.

```sh
git commit -m 'feat(c5): checkpoint 30x18 warehouse profile and geometry'
git commit -m 'feat(c5): checkpoint task catalog and browser task creation'
git commit -m 'feat(c5): checkpoint warehouse operations dashboard'
git commit -m 'test(c5): checkpoint warehouse and end-to-end validation'
```

Sonuçlar sırasıyla `1406f56`, `897be3c`, `fcf8844`, `b9d8a74`. Önceden var olan F1/model/footprint/Battery/beam commit’leri tekrar üretilmedi. Ham rota/poz JSON kayıtları staging’den çıkarılırken yalnız `git restore --staged -- <iki dosya>` kullanıldı; çalışma dosyalarına dokunulmadı. Reset kullanılmadı.

## Yalnız Git export’u üzerinden denetim

Python `subprocess.run(['git','archive','HEAD','-o',...])` ile `b9d8a74` tar export’u üretildi, yeni boş `/tmp/c5-git-audit-20261111/tracked-checkout` dizinine açıldı. `frontend/node_modules`, mevcut kurulu bağımlılık dizinine symlink olarak bağlandı; diğer untracked kaynaklar kopyalanmadı. Export gerçek ek bir Git worktree değildir ve mevcut worktree listesi değişmedi.

Export kökünden gerçek komutlar:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator  /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python -m pytest -q -rs -p no:cacheprovider  tests/test_config.py tests/test_c5_dashboard.py tests/test_warehouse_grid.py  tests/test_warehouse_operations.py tests/test_feedback_pipeline.py tests/test_battery_shutdown.py

npm --prefix frontend run build -- --outDir /tmp/c5-git-audit-20261111/frontend-build
```

**0: 104 passed, 1 skipped, 1 warning in 8.72s.** Atlanan `tests/test_battery_shutdown.py:11`, ROS 2 Humble gerektirir. Uyarı Starlette/httpx deprecation. Build **0**, 1910 modül, 1.81 s; dış outDir’in otomatik boşaltılmayacağı uyarısı var. Hedef yeni dizindir. Ham çıktılar `/tmp/c5-git-audit-20261111/checkpoint-tests.log` ve `checkpoint-build.log` dosyalarında yereldir; yeni checkpoint’e alınmadı.

Python heredoc ile 132 `.py` dosyasına `ast.parse`, dört `config/fleet*.yaml` dosyasına `load_config` uygulandı. `generate(<tracked profile>, <yeni output>, 'routes')` SDF, PGM/YAML, Nav2, occupancy, scene ve goals üretti; `scene == config.warehouse.scene_payload()` assert edildi. `frontend/tests/*.mjs` için `node --check`, `run.sh` için `bash -n` sonuçları 0. [Statik sonuç ve hash’ler](git-checkpoint-2026-11-12/static-checks.json). Bu üretim ROS/Gazebo başlatmaz.

## Gizli bilgi ve arşiv denetimi

Python ile `git rev-list --objects HEAD` blob’ları `git cat-file --batch` üzerinden okundu. `.tar.gz` üyeleri diske açılmadan tarandı. Çalışma ağacındaki izlenen ve seçilen yeni dosyalar ayrıca tarandı. Private key başlığı, GitHub/OpenAI/AWS anahtar örüntüleri, kullanıcı-parolalı URL ve literal credential ataması için sonuç 0. E-posta örüntüleri paket metadatası, tarihsel capture ve dosya adlarında ayrı değerlendirildi. Scan sayacı aynı içeriğin tarihçe/çalışma ağacı tekrarlarını içerir. Ham gizli değer yazdırılmadı. Eski arşivlerin 17 SQLite dosyası bellekte `sqlite3.deserialize` ile açılıp tablo satırları ayrıca tarandı, eşleşme yok.

## Son normal push doğrulaması

Denetim docs commit’i eklendikten sonra uygulanacak son kapı:

```sh
git fetch origin
git branch --show-current
git rev-list --left-right --count HEAD...origin/feat/c5-warehouse-grid-layout
git merge-base --is-ancestor origin/feat/c5-warehouse-grid-layout HEAD
git rev-parse main
git push -u origin feat/c5-warehouse-grid-layout
git ls-remote --heads origin refs/heads/feat/c5-warehouse-grid-layout refs/heads/main
git rev-parse HEAD origin/feat/c5-warehouse-grid-layout main
```

Divergence varsa push yapılmaz. Sonuç ve SHA’lar son yanıtta ve yerel `git-checkpoint-2026-11-12/push-verification.json` makbuzunda tutulur. Makbuz kendi SHA’sını kaydeden yeni commit oluşturmaz. Yasak işlemler ve Aşama 2 başlatılmadı.
