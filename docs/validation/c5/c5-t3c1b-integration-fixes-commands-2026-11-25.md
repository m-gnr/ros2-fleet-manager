# C5-T3C-1B — Hedefli hata ayıklama komutları

25 Kasım 2026 · [Sonuç ve sınırlar](c5-t3c1b-integration-fixes-2026-11-25.md).
Bu ek çalıştırılmış komutları kaydeder; varsayılan demo başlatma talimatı
değildir. Son kapsam yalnız `controller-inactive`, `replan`, `health-session`.
**14'lü matris, commit/push ve hareketli deney yapılmadı.**

## Başlangıç ve tanı

Depo kökünden Git durumu, mevcut diff, proje bağlamı, doküman haritası ve
24 Kasım raporu okundu. Başlangıç dirty ağacın patch/hash snapshot'ı
`/tmp/c5-t3c1b-recovery-20261124/` altına alındı; hiçbir kaynak sıfırlanmadı.
Bu dizinin tarihi incelemenin başladığı günü gösterir.

`run-diagnostic.sh`, aynı native a4 binary ve önce gerçek eski ROS overlay'i,
sonra tanı overlay'ini kullandı. `C5_1B_DIAGNOSTICS=1`, yalnız bu fixture'ın
Nav2/bridge süreçlerine ayrı yazılabilir core çalışma dizini ve sınırsız core
limiti verir. Sinyal/exit kodu maskelenmez. Güncel kaynak source-stamp,
subscriber sayısı ve child alımını yalnız bu açık tanı ortamında loglar.

```bash
bash /tmp/c5-t3c1b-recovery-20261124/run-diagnostic.sh controller-inactive controller-repro1 181
bash /tmp/c5-t3c1b-recovery-20261124/run-diagnostic.sh replan replan-repro1 182
bash /tmp/c5-t3c1b-recovery-20261124/run-diagnostic.sh health-session health-session-repro1 183
```

Diğer tekrarların tam komut/script/exit ledger'ı
[kanıt dizinindedir](c5-t3c1b-integration-fixes-2026-11-25/). Tekrarların tümü
aynı üç senaryoyla sınırlıdır; başarısız denemeler ayrı ad/dizindedir.

GDB/Valgrind yalnız yeni tanı image'larına kuruldu; taban image değiştirilmedi.
Bridge core'u için gerçek kullanılan çağrı:

```bash
gdb -q -batch /opt/ros/humble/lib/ros_gz_bridge/parameter_bridge \
 /evidence/replan-repro2/cores/command_bridge/679/core \
 -ex 'set pagination off' -ex 'bt 30' -ex 'info threads' -ex 'thread apply all bt 8'
```

Bridge executable SHA'sı taban ve GDB image'ında aynıydı. Heap'in ilk bozulduğu
yazım adresi yakalanmadı; core allocator/exit aşamasını gösterir. Valgrind
testleri robot topic'i olmadan ve gerçek fixture içinde ayrı çalıştırıldı;
0 error sonuçları ham kayıtlarla korunur, kök nedenin eksiksiz kanıtı sayılmaz.

Nav2 core'u:

```bash
gdb -q -batch /opt/ros/humble/lib/nav2_planner/planner_server \
 /evidence/replan-readonly-cleanup1/cores/nav2_robot_beta/136/core \
 -ex 'set pagination off' -ex 'bt 25' -ex 'thread apply all bt 10'
```

`C5_1B_READONLY_CLEANUP_DIAGNOSTIC=1`, doğrulamadan sonra yalnız GetCostmap
okumalarını açık tutar. Yeni state/permit/robot komutu yayınlamaz, costmap'i
temizlemez. Kaydedilen callback/cleanup çakışması ve daha sonraki düzeltme
karşılaştırması rapordadır. Bu tanı yükü son üç normal koşuda kapalıdır.

## Bağımlılık düzeltmesi ve yaşam süresi testi

Yeni overlay dizini gerekir; aşağıdaki çağrı gerçek başarılı a4 denemesidir:

```bash
C5_UPSTREAM_ARCHIVE_DIR=/tmp/c5-t3c1b-recovery-20261124/ros-fixed-a2 \
 bash docker/experiments/c5-t3c1b/build_ros.sh \
 /tmp/c5-t3c1b-recovery-20261124/ros-fixed-a4
```

`build_ros.sh` upstream `ros_gz 0.244.27` arşivinin SHA-256'sını doğrular,
`ros-gz-callback-owner.patch` uygular; dört gerekli paketi tek compiler,
Release `-O1 -DNDEBUG` ile derler. Kurulu Nav2 cleanup başlıklarıyla yalnız
`costmap_cleanup.cc` sembolü derlenir. Upstream paket testleri bu bağımlılık
derlemesinde açık değildir; geçtikleri iddia edilmez. Kendi
`bridge-owner-expires` CTest'i çalıştırıldı: **1/1 PASS**.

Kontrol testleri aynı `bridge_lifetime.cc` ile stock 0.244.26 ve upstream
0.244.27'de **FAIL** verdi; ikisi de korunur. Upstream 0.244.27'nin tek başına
yeterli olmadığı bu karşılaştırmayla saptandı; bu başarısızlıklar gizlenmedi.

İlk tam kaynak overlay denemeleri: a1 compiler OOM sonrası kontrollü durdurma,
a2 build başarılı fakat runtime başlangıç hatalı/reddedildi, a3 compiler OOM.
Eski dizin/loglar korunur. Son a4 stock Nav2'yi yeniden derlemez; constructor
ve kontrol döngüsünü kurulu binary'den kullanır.

## Sabit kaynakla yalnız üç temiz canlı koşu

499 runtime/test dosyası ayrı salt-okunur source kopyasına alındı. Git
worktree oluşturulmadı. Fingerprint ve dosya hash'leri kanıttadır:

`14eb4e63a2eb0c69c986aaf0f0dca71894c23b5901da72d044bfd9012b543da8`

Gerçek `run-targeted-3.sh` yalnız şu listeyi seri çalıştırdı:

```bash
for scenario in controller-inactive replan health-session; do
  # Yeni case adı, DB/session/boot ve partition; domain 201, 202, 203.
  docker run --rm --init --name "$name" --network bridge --workdir /workspace \
    --env ROS_DOMAIN_ID="$index" --env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    --env ROS_LOCALHOST_ONLY=0 --env IGN_PARTITION="$name" \
    --env C5_1B_CLEANUP_FIX_LIBRARY=/build/lifecycle/libc5-costmap-cleanup.so \
    -v /tmp/c5-t3c1b-recovery-20261124/frozen-source-1:/workspace:ro \
    -v /tmp/c5-t3c1b-recovery-20261124/ros-fixed-a4:/build:ro \
    -v /tmp/c5-t3c1b-native-20261124-a4:/b6b7-native:ro \
    -v /tmp/c5-t3c1b-recovery-20261124:/evidence c5-b6b5-build:local bash -ec '
      source /opt/ros/humble/setup.bash
      source /build/install/local_setup.bash
      export PYTHONPATH=/workspace:/workspace/backend:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:$PYTHONPATH
      python3 docker/experiments/c5-t3c1b/live.py config/fleet.warehouse-30x18.yaml "/evidence/$1" --case "$2"
    ' targeted "$run" "$scenario"
done
```

Bu kısaltılmış gösterimdir; değişkenler ve CLI log/exit kayıtları dahil tam
çalıştırılmış script kanıttadır. **Üç CLI 0**. 14'lü matris çağrısı yoktur.
Kaynak dosyaları koşular sonrasında tekrar hash'lenip eşleştirildi.

```bash
python3 /tmp/c5-t3c1b-recovery-20261124/frozen-source-1/docker/experiments/c5-t3c1b/audit.py \
 /tmp/c5-t3c1b-recovery-20261124 /tmp/c5-t3c1b-recovery-20261124/targeted-3.tsv \
 /tmp/c5-t3c1b-recovery-20261124/targeted-3-audit.json \
 --cases controller-inactive replan health-session
```

Çıktı `PASS_TARGETED_STATIONARY_HEALTH_VETO_AUDIT`;
`acceptance_complete=false`, `scope_complete=true`. İç child crash'leri de
reddedilir; başarısız CLI veya eksik kanıt kabul edilmez. Ayrı closure proof,
gerçek controller/planner kütüphane mapping'lerini, altı callback join marker'ı,
BLOCKED claim, PENDING traffic Outbox ve release reddini doğrular.

## Son regresyonlar

Host ve ROS seçkileri, [24 Kasım komut ekindeki](c5-t3c1b-health-veto-commands-2026-11-24.md)
aynı test listeleri + `tests/test_split_health_readiness.py` ile tekrarlandı.
Host **487 PASS**; aynı dondurulmuş kökteki ilk 486/1 fixture paketleme hatası
korunur. Tarihsel baseline dosyası hash'iyle eklendi; test/assertion değişmedi.
ROS (`--network none`, domain 173, CycloneDDS, plugin autoload kapalı,
aynı kaynak/ROS overlay salt okunur) **200 PASS**, 0 skip verdi.

Native a4 test binary'leri değişmeden salt okunur bağlandı; CTest listeleri
yeni yazılabilir test dizinine kopyalanarak **2/2 PASS** alındı. Önceki native
log'ları yeniden yazılmadı. Kaynak ve test sınırları örtüşür; sayılar benzersiz
test toplamı olarak birleştirilmez.

## Kayıtların korunması ve Git

Ham senaryolar, core/backtrace'ler, başarısız derleme ve testler, source/binary
manifestleri yeni kanıt dizinindedir. Orijinal `/tmp` dosyaları da bırakıldı.
Provision anahtarı veya native executable/.so arşivlenmez; binary'ler hash ile
tanımlanır. Runtime kaynak kopyası yalnız manifestteki dosyalarla paketlenir;
test cache'leri eklenmez. Önceki C5 kaynak/kanıtları silinmedi veya sıfırlanmadı.

Son kullanıcı talimatı gereği **commit/push yapılmadı**. HEAD ve uzak main
`f69d1024b36a2cc5ac8ad93679f9f66c22f13397`; değişiklikler çalışma ağacındadır.
Kendi test/build süreçleri kapatıldı; varsayılan GUI/launcher ve başka worktree
değişmedi. Burada durulur; tam 14'lü kabul ve T3C-2 bu çalışmanın sonucu değildir.
