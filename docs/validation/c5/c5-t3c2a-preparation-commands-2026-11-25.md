# C5-T3C-2A — Çalıştırma ve koruma eki

25 Kasım 2026. [Hazırlık raporu](c5-t3c2a-preparation-2026-11-25.md).
**2A PASS; hareketli 2B BLOCKED. Yeni Gazebo/motion koşusu yoktur.**

## Başlangıç ve kaynak incelemesi

`git status --short` temizdi; HEAD/origin-main
`a3dcf9ec9e906362cb11ed2e8847fa324b6fac8c` idi. Proje bağlamı,
dokümantasyon haritası, T3B/T3C0/T3C1A/T3C1B ve frenleme kayıtları okundu.
FM transaction/Outbox ve bridge, Executor NativeZeroLink, AuthorizedZero,
worker/IPC, DiffDrive PreUpdate/PostUpdate, recorder ve stock Physics
wrapper incelendi. Önceki kabul kaynak/binary hash'leri yeniden doğrulandı.

Yeni araç yalnız `docker/experiments/c5-t3c2a/measurements.py`; yeni test
`tests/test_t3c2a_measurements.py`. Kontrol, model/config, IDL, Scheduler,
Outbox, health/STALE eşikleri, native veya varsayılan launcher değiştirilmedi.

## Hazırlık ve tarihsel audit

Depo kökünden yeni kanıt dizini `/tmp/c5-t3c2a-20261125` kullanıldı:

```bash
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor \
 /tmp/c5-perf-test-venv/bin/python -m pytest -q -p no:cacheprovider tests/test_t3c2a_measurements.py
PYTHONPATH=.:backend /tmp/c5-perf-test-venv/bin/python \
 docker/experiments/c5-t3c2a/measurements.py \
 docs/validation/c5/c5-t3c1b-last-two-2026-11-25 \
 --output /tmp/c5-t3c2a-20261125/measurement-inventory.json
```

Sonuç **13 PASS** ve `PASS offline preparation; T3C-2B BLOCKED; UNBOUNDED;
no new live run`. Mevcut tam 1B audit'i filtresiz yeniden kullanıldı:
14 tarihsel koşu, 42 writer/robot boot grubu, 14.715 kayıt.

README komutu ayrıca mevcut ürün venv Python'u ile çalıştırıldı:

```bash
PYTHONPATH=.:backend .venv/bin/python docker/experiments/c5-t3c2a/measurements.py \
 docs/validation/c5/c5-t3c1b-last-two-2026-11-25 \
 --output /tmp/c5-t3c2a-20261125/readme-review.json
```

İki Python ortamının JSON çıktıları birebir aynı; Python sürümleri kanıtta.
Çıktılar yeniden kullanılmadı/ezilmedi. Arşiv input'unda yeni sidecar yoktu.

İlk denemede (12 test henüz yan-dosya durumunu kapsamıyordu) eski read-only
bağlantı WAL/SHM oluşturdu; bu denemenin PASS envanteri final kabul değildir.
`.attempt1` çıktıları korundu. 28 yeni sidecar silinmeden ayrı tutuldu.
Ayırma glob'una giren 36 mevcut `.gz` artefaktı da byte-for-byte yerine
alındı. Tüm 1.825 özgün hash doğrulandı; son kaynak immutable bağlantı
kullanır. Yeni 13. test gerçek kapalı WAL backup'ı üzerinde sidecar/yazma
olmamasını ve nonempty WAL reddini denetler. `readonly-recovery.json` ayrıntılıdır.

## İlgili regresyonlar

Host seçkisi önceki [487 testlik tam liste](c5-t3c1b-final-commands-2026-11-25.md)
+ `tests/test_t3c2a_measurements.py` ile, aynı venv/PYTHONPATH ve
`pytest -q -p no:cacheprovider` seçenekleriyle çalıştı: **500 PASS / 14.37 s**.

ROS seçkisi önceki aynı 200 test listesiyle; network-none container,
ROS_DOMAIN_ID=173, rmw_cyclonedds_cpp, plugin autoload kapalı,
repo:/workspace:ro ve fixed-a4:/build:ro kullanıldı:

```bash
source /opt/ros/humble/setup.bash
source /build/install/local_setup.bash
export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
python3 -m pytest -q -p no:cacheprovider \
 tests/test_robot_health.py tests/test_stop_envelope.py tests/test_split_health.py \
 tests/test_split_health_readiness.py tests/test_health_fixture_transports.py tests/test_robot_health_ros2.py \
 tests/test_native_permit_context.py tests/test_native_permit_ros2.py \
 tests/test_traffic_product_child.py tests/test_traffic_product_child_ros2.py \
 tests/test_traffic_protocol_ros2.py tests/test_executor_safety_ros2.py
```

**200 PASS / 21.72 s**. Mevcut invalid-feedback-publisher negatif test
uyarıları ham log'da saklanır. ROS regresyonları sentetik typed action/topic
fixture'larıdır; yeni fiziksel sensör veya duruş kanıtı değildir.

Sabit native-final ve ROS fixed-a4 binary'leri değiştirilmeden salt okunur
bağlandı. CTest listeleri yeni yazılabilir `native-tests`, `bridge-tests`
dizinine kopyalandı; `ctest --test-dir /test --output-on-failure` ile
**2/2 native**, **1/1 bridge lifetime** geçti. Eski LastTest.log'lar ezilmedi;
yeni LastTest.log'lar saklandı. Yeni Gazebo başlatılmadı.

## Koruma, paketleme ve Git

`git diff` ile backend/ROS/control/IDL/config/scripts/GUI ve önceki native
experiment kaynaklarının başlangıç commit'iyle aynı olduğu denetlendi.
Kabul runtime-pin'indeki binary ve image hash'leri eşleşti. Önceki dört
1B arşivindeki **6.635 raw dosyanın hash'i** doğrulandı. Tüm kendi Docker
testleri bitti; başka worktree/proseslere müdahale edilmedi.

Yeni ham çıktı arşivi [manifestlidir](c5-t3c2a-preparation-2026-11-25/manifest.json).
İlk paketleme denemesinde raw sidecar ile zaten `.gz` olan sidecar aynı
hedef adına denk geldi; assertion ile durdu, veri ezilmedi. O script/log ve
partial output hash'leri korundu; partial dizin
`/tmp/c5-t3c2a-archive-attempt1-20261125` altında bırakıldı. Düzeltmeli
paketleme her girdiye ayrı `.gz` ekledi, **98 dosya** sıkıştırma öncesi/sonrası
hash'iyle doğrulandı. Bu paketleme hatası çalışma zamanı testi veya PASS
olarak sunulmadı. Eski veriler veya yan dosyalar silinmedi.

`git diff --check`, Markdown yerel bağlantıları, preparation/source hash'leri
ve eski arşivde sidecar bulunmadığı son kez kontrol edilir. Koşullar sağlandığında
yalnız bu hazırlık kaynak/test/rapor/kanıtları commit edilir; uzak main
fast-forward kontrolünden sonra normal push ve uzak SHA/temiz ağaç doğrulanır.
2B hareket onayı bu Git işleminin parçası değildir.
