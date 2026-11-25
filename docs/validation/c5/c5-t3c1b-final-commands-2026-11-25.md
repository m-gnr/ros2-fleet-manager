# C5-T3C-1B final kabul denemesi — Çalıştırma eki

25 Kasım 2026. [Sonuç ve engeller](c5-t3c1b-final-2026-11-25.md).
Yeni çalışma dizini `/tmp/c5-t3c1b-final-20261125`; önceki sonuçlar
üzerine yazılmadı. Kaynak, ROS/native overlay ve dependency pin'leri
[ham kanıttadır](c5-t3c1b-final-2026-11-25/manifest.json).

## Ön inceleme ve sabitleme

Depo kökünde `git status --short`, `git rev-parse HEAD origin/main`,
`git diff --stat`, ilgili kaynak diff'leri, proje bağlamı, dokümantasyon haritası
ve iki referans rapor incelendi. 499 dosyanın çalışma ağacı ve salt okunur
kopyadaki SHA256'ları eski sabit manifestle eşleştirildi.
`docker image inspect c5-b6b5-build:local` kimliği ve native/ROS
`binary-sha256.txt` listelerindeki tüm çıktılar doğrulandı.

## Regresyonlar — matristen önce

Host komutu salt okunur kaynak kopyası kökünde çalıştırıldı:

```bash
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
 /tmp/c5-perf-test-venv/bin/python -m pytest -q -p no:cacheprovider \
 tests/test_robot_health.py tests/test_stop_envelope.py tests/test_split_health.py \
 tests/test_split_health_readiness.py tests/test_health_fixture_transports.py \
 tests/test_native_permit_context.py tests/test_traffic_product_child.py tests/test_traffic_child_binding.py \
 tests/test_peer_awareness_config.py tests/test_traffic_protocol.py tests/test_traffic_motion_gate.py \
 tests/test_traffic_core.py tests/test_fleet_manager_outbox.py tests/test_fleet_manager_domain.py \
 tests/test_executor_safety.py tests/test_executor_state_machine.py tests/test_b6b4_topology.py \
 tests/test_c43_station_dispatch.py tests/test_c44_charging.py tests/test_ros2_route_resolver.py
```

**487 passed in 12.29s**. `host-regression.log.gz` eksiksiz saklandı.
ROS seçkisi `--network none`, domain 173, `rmw_cyclonedds_cpp`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, aynı kaynak `/workspace:ro` ve fixed-a4
`/build:ro` bağlarıyla çalıştı. Container içinde:

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

**200 passed in 26.59s**. Negatif test kapanış uyarıları
`ros-regression.log.gz` içinde aynen korunur.

Native ve bridge CTest listeleri eski test kayıtlarını değiştirmemek için yeni
`native-tests/`, `bridge-tests/` dizinlerine kopyalandı. Binary'ler değişmeden
salt okunur `/build` bağında kaldı; `ctest --test-dir /test --output-on-failure`
ile native **2/2**, bridge **1/1** geçti. Her iki LastTest.log saklandı.

## 14 seri canlı koşu

[Tam çalıştırılmış script](c5-t3c1b-final-2026-11-25/run-matrix.sh)
ve [exit ledger](c5-t3c1b-final-2026-11-25/matrix.tsv) kanıttadır:

```bash
bash /tmp/c5-t3c1b-final-20261125/run-matrix.sh
```

Script senaryo başına yeni `--rm --init --network bridge` container,
DDS domain 181–194 ve benzersiz IGN partition kullandı. Üç salt okunur bağ:
`frozen-source-1:/workspace:ro`, `ros-fixed-a4:/build:ro`,
`c5-t3c1b-native-20261124-a4:/b6b7-native:ro`.
Cleanup env `C5_1B_CLEANUP_FIX_LIBRARY=/build/lifecycle/libc5-costmap-cleanup.so`.
CLI stdout/stderr ayrı `<case>-final1.cli.log`, exit'ler ledger'a yazıldı.
Sonraki senaryo, önceki container bitince başladı. Diagnostic/core veya
read-only cleanup yük testi env'leri açılmadı.

```bash
python3 /tmp/c5-t3c1b-recovery-20261124/frozen-source-1/docker/experiments/c5-t3c1b/audit.py \
 /tmp/c5-t3c1b-final-20261125 /tmp/c5-t3c1b-final-20261125/matrix.tsv \
 /tmp/c5-t3c1b-final-20261125/full-audit.json
```

**exit 1**, başarısız CLI AssertionError: tam kabul dosyası üretilmedi.
Hata `full-audit.log.gz` içinde korunur. Aynı çağrı yalnız tanısal
`--completed-only` ile 12 tamamlanan koşuyu denetledi; sonuç
`INCOMPLETE_1B_ACCEPTANCE_COMPLETED_CASES_AUDITED`, tam kabul **false**.

```bash
python3 /tmp/c5-t3c1b-final-20261125/closure_proof.py
python3 /tmp/c5-t3c1b-final-20261125/verify_final.py
```

[Closure script](c5-t3c1b-final-2026-11-25/closure_proof.py) 12 tamamlanan
koşuda gerçek controller/planner cleanup mapping/marker, PENDING Outbox ve
korunan kaynağı denetler; tam kabul false'tur.
[Final doğrulayıcı](c5-t3c1b-final-2026-11-25/verify_final.py) 14 koşuda
17.000 sıfır hedef, temiz kapanış/iç crash yokluğu, Physics gözlemleri,
DB integrity, gerçek ACK, korunmuş claim, kaynak/binary hash'i ve varsayılan
path diff'lerini kontrol etti. İki FAIL'de fault enjekte edilmediğini açık tutar.
Bu script'ler yeni hareket/test başlatmaz; ham kayıt okur.

## Git ve arşiv

```bash
git ls-remote origin refs/heads/main
git diff --check
```

Uzak SHA `f69d1024b36a2cc5ac8ad93679f9f66c22f13397`; diff check temiz.
Commit/push yapılmadı. Kaynak çalışma ağacında korundu.
[Arşiv script'i](c5-t3c1b-final-2026-11-25/archive.py) 1.067 ham dosyayı
sakladı; [manifest](c5-t3c1b-final-2026-11-25/manifest.json) ve
[geri açma hash doğrulaması](c5-t3c1b-final-2026-11-25/archive-verification.json)
eklendi. Provision anahtarları veya executable binary'ler arşive alınmadı;
binary sürümleri SHA256 ile tanımlanır. Eski kanıtların üzerine yazılmadı.
