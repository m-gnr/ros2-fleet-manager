# C5 Aşama 1.3 — Komut ve kanıt eki

11 Kasım 2026 · [Rapor](c5-stage1-3-localization-approach-2026-11-11.md)

Komutlar `/Users/murat/develop/ros2-fleet-manager-c5-warehouse-grid` kökünden çalıştırıldı. Baseline Git kaydı, hash’ler ve diff `stage1-3-2026-11-11/` altında. Image yeniden build edilmedi; mevcut `ros2-fleet-c5-validation:humble-fortress` ID’si ortam kaydında. Çalışma ağacı readonly bağlanır; yalnız yeni kanıt dizini yazılabilir. Önceki rapor ve ham kanıtlara yazılmaz.

## Canlı deney zarfı

```sh
docker run -d --init --name fleet-c5-stage13-a \
 -e ROS_DOMAIN_ID=189 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
 -e ROS_LOCALHOST_ONLY=0 -e LIBGL_ALWAYS_SOFTWARE=1 -e PYTHONDONTWRITEBYTECODE=1 \
 -v "$PWD:/workspace:ro" \
 -v "$PWD/docs/validation/c5/stage1-3-2026-11-11:/evidence" \
 -w /workspace --entrypoint bash ros2-fleet-c5-validation:humble-fortress -ec '
source /opt/ros/humble/setup.bash
export PYTHONPATH=/workspace:${PYTHONPATH:-}
python3 docker/simulation-warehouse-grid/stage13_run.py \
 config/fleet.warehouse-30x18.yaml /evidence/a-baseline
'
```

A üç bağımsız dünya; probe süreçleri 0, dünyalar temiz 0; fiziksel kabul 1/3. Süreç 0 ölçümün tamamlandığı anlamındadır, pickup kabulü değildir. Çıktı dizini exist_ok=False; tekrarlar yeni dizin ister.

A çalışırken gerçek etkin parametreler:

```sh
docker exec fleet-c5-stage13-a bash -c '
source /opt/ros/humble/setup.bash
ros2 param dump /robot_beta/amcl > /evidence/a-baseline/runtime-amcl.yaml
ros2 param dump /robot_beta/controller_server > /evidence/a-baseline/runtime-controller.yaml
dpkg-query -W ros-humble-nav2-amcl ros-humble-dwb-core ros-humble-nav2-costmap-2d > /evidence/versions.txt
uname -a >> /evidence/versions.txt
'
```

İkinci zarf aynı mount/image/env, adı `fleet-c5-stage13-sensitivity`, domain 190. A kapandıktan sonra aşağıdaki komutlar sıralı çalıştırılır; varsayılan her varyant üç dünya:

```sh
python3 docker/simulation-warehouse-grid/stage13_run.py config/fleet.warehouse-30x18.yaml /evidence/sigma-005 --amcl sigma_hit=0.05
python3 docker/simulation-warehouse-grid/stage13_run.py config/fleet.warehouse-30x18.yaml /evidence/alpha1-002 --amcl alpha1=0.02
python3 docker/simulation-warehouse-grid/stage13_run.py config/fleet.warehouse-30x18.yaml /evidence/b-landmark --landmark
python3 docker/simulation-warehouse-grid/stage13_run.py config/fleet.warehouse-30x18.yaml /evidence/c-heading0 --heading 0
python3 docker/simulation-warehouse-grid/stage13_run.py config/fleet.warehouse-30x18.yaml /evidence/c-headingpi --heading 3.141592653589793
```

Ürün parametreleri değiştirilmez. Her koşu kendi experiment-profile.yaml ve generated dosyalarıyla kimliklenir. Heading fiziksel spawn ve AMCL initial_pose için aynı profile gider. Robot görev sırasında taşınmaz.

## Analiz ve test

```sh
python3 docker/simulation-warehouse-grid/stage13_analyze.py docs/validation/c5/stage1-3-2026-11-11
PYTHONPATH=.:backend:ros2_ws/src/fleet_robot_executor:ros2_ws/src/fleet_battery_simulator \
 /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python -m pytest -q -rs \
 tests/ ros2_ws/src/fleet_robot_executor/test
```

İlk tam host koşu 453 geçti, 29 atlandı, 1 uyarı, süreç 0 (`host-tests-initial.log`). Yeni+eski ölçüm seçkisi 11 geçti (`measurement-tests.log`). Analiz her tamamlanmış koşunun analysis.json dosyasını ve ortak experiment-results.json özetini yazar; ham JSONL dosyalarını değiştirmez. TF yalnız mesaj stamp’inde bracket içinden interpolasyonla hesaplanır; geleceğe extrapolasyon yapılmaz. AMCL covariance kendi damgası ve yaşıyla raporlanır.

## Ek duyarlılık ve son seçim

İlk üçlüler tamamlandıktan sonra aynı zarfla sıralı ek seçkiler çalıştı. Tam argümanlar: [remaining-plan.json](stage1-3-2026-11-11/remaining-plan.json), [laser-model-plan.json](stage1-3-2026-11-11/laser-model-plan.json), [cross-heading-plan.json](stage1-3-2026-11-11/cross-heading-plan.json). `stage13_suite.py <plan>` her alt sürecin kodunu ayrı kaydeder; bir alt süreç kaldığında toplam sonuç 1 kalır. Nav2 ABORTED ölçümü eksiksiz kaydedilmişse probe 0 olabilir; bu fiziksel kabul değildir.

| Container | DDS domain | Amaç / gerçek süreç sonucu |
|---|---:|---|
| fleet-c5-stage13-a | 189 | A üçlüsü; 0 |
| fleet-c5-stage13-sensitivity | 190 | sigma005, alpha1, B, C/0, C/π; 0, fiziksel sonuçlar ayrı |
| fleet-c5-stage13-motion-noise | 191 | İlk alpha4; bridge -11 kapanışı, üst süreç 1 |
| fleet-c5-stage13-motion-repeat | 192 | Yeni alpha4 üçlüsü, ilk alpha3; alpha3 bridge -11, üst süreç 1 |
| fleet-c5-stage13-remaining | 193 | alpha3 tekrar, sigma010, beams180; toplam 1, ham hatalar korunur |
| fleet-c5-stage13-laser-models | 194 | beam/prob üçlüleri, tek planlama referansı, tek sigma replacement; toplama 0 |
| fleet-c5-stage13-cross-heading | 195 | Beam ile iki heading, üçer dünya; 0 |
| fleet-c5-stage13-acceptance | 196 | Ürün şablonuyla beş yeni dünya; 0 ve fiziksel 5/5 |

Her dünya önceki simulation süreci kapandıktan sonra açıldı; iki Gazebo aynı anda benchmark edilmedi. `--collect-after-shutdown-failure` yalnız kapanmış bağımsız dünyanın hatasını koruyarak kalan araştırma örneklerini toplar; kapanış kusurunu veya fiziksel kabulü başarılı yapmaz. İlk iki runner durduğu için kaynak değiştirmeden yeni output dizinleri kullanıldı.

Kaynak üretici sürümleri: ilk [source-snapshot](stage1-3-2026-11-11/source-snapshot.tar.gz), sonradan `measurement-source-v2/v3` ve nihai [source-final](stage1-3-2026-11-11/source-final.tar.gz). İlk A/sigma005/alpha1/B/C süreçlerinde runner henüz son koşu sonrası seçili rota sorgusunu içermiyordu; sonraki primary ölçümler bittikten sonra rota sorguları eklendi. Bu sorgular CPU/RTF’nin birincil fiziksel penceresine katılmadı. İlk sigma010/3’te boş initial TF örneği TypeError üretti; aynı damgadaki TF için bounded bekleme eklendi ve yeni bir replacement dünya açıldı. İlk hata yok sayılmadı.

Seçilen satır `laser_model_type: likelihood_field → beam`; [kanıt kapısı](stage1-3-2026-11-11/correction-gate.md) ve [dokuz seçim koşusu](stage1-3-2026-11-11/selection-evidence.json) kaydedildikten sonra uygulandı. Son beşli komutu:

```sh
python3 docker/simulation-warehouse-grid/stage13_run.py \
 config/fleet.warehouse-30x18.yaml /evidence/acceptance-pickup \
 --trials 5 --collect-after-shutdown-failure
```

Bu komutta `--amcl` verilmedi; gerçek ürün şablonu kullanıldı. Domain 196 ve aynı image/mount/env zarfı. Son etkin AMCL parametreleri gerçek `ros2 param dump /robot_beta/amcl` ile `/evidence/acceptance-pickup/runtime-amcl.yaml` dosyasına alındı.

## Gerçek Chrome, tek ve paralel görev

```sh
C5_UI_PORT=20311 C5_API_PORT=20312 npm --prefix frontend run dev
```

İlk A test zarfında scene aliası eksikti: görev COMPLETED, fakat TF/görsel karşılaştırması 1 kaldı. İlk `comparison-a.log`, son sabit kaynaktan yeniden hesaplanan `comparison-a-final.log`, DB ve Chrome kayıtları korunur. Kapanış bütün çocuklarda 0 idi. Ürün kodu değiştirilmeden yeni A2 şu zarfla çalıştırıldı:

```sh
docker run -d --init --name fleet-c5-stage13-scenario-a2 \
 --add-host scene:127.0.0.1 -p 127.0.0.1:20312:20312 \
 -e ROS_DOMAIN_ID=199 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
 -e ROS_LOCALHOST_ONLY=0 -e LIBGL_ALWAYS_SOFTWARE=1 -e PYTHONDONTWRITEBYTECODE=1 \
 -e STAGE11_TRANSITIONS=/evidence/scenario-a2/committed-events.jsonl \
 -v "$PWD:/workspace:ro" \
 -v "$PWD/docs/validation/c5/stage1-3-2026-11-11:/evidence" \
 -v "$PWD/docs/validation/c5/e2e-stage1-2026-11-11/install:/types:ro" \
 -v fleet-c5-stage13-20261111:/var/lib/fleet \
 -w /workspace --entrypoint bash ros2-fleet-c5-validation:humble-fortress -ec '
source /opt/ros/humble/setup.bash
source /types/setup.bash
export PYTHONPATH=/workspace:/workspace/ros2_ws/src/fleet_robot_executor:/workspace/ros2_ws/src/fleet_battery_simulator:/workspace/fleet-visualizer/bridge:${PYTHONPATH:-}
python3 docker/simulation-warehouse-grid/stage11_run.py \
 config/fleet.warehouse-30x18.yaml /evidence/scenario-a2 \
 --api-port 20312 --scene-port 20313 --origin http://127.0.0.1:20311
'
node frontend/tests/stage11-e2e.mjs http://127.0.0.1:20311 \
 docs/validation/c5/stage1-3-2026-11-11/chrome-a2 a
```

Chrome A2 **0**, gerçek COMPLETED. `docker stop --timeout 50 fleet-c5-stage13-scenario-a2` sonrasında bütün çocuklar/container 0. İlk A domain 198; düzeltilmiş B aynı doğru zarfla domain 200, container `fleet-c5-stage13-scenario-b`, output `scenario-b`, STAGE11_TRANSITIONS da o dizindi. B Chrome komutunun son argümanı `b`, output `chrome-b` oldu: **0, iki COMPLETED**. B de timeout 50 ile kapandı; bütün çocuklar/container 0. UI geliştirme sunucusu sonra kontrollü Ctrl+C ile durduruldu; bunun npm sinyal çıkışı ürün testi sonucu değildir.

```sh
python3 docker/simulation-warehouse-grid/stage1_summarize.py \
 docs/validation/c5/stage1-3-2026-11-11/scenario-a2 \
 docs/validation/c5/stage1-3-2026-11-11/chrome-a2
python3 docker/simulation-warehouse-grid/stage1_summarize.py \
 docs/validation/c5/stage1-3-2026-11-11/scenario-b \
 docs/validation/c5/stage1-3-2026-11-11/chrome-b
```

İkisi **0**; ilk A aynı karşılaştırma **1**, TF/render yokluğu nedeniyle. Görseller yerel olarak incelendi. Yeni DB’ler kalıcı volume ve kanıt kopyasında korunur; aynı komutu aynı DB adıyla yeniden çalıştırmak reset kabulü değildir. Docker `ExtraHosts`, port, mount/env/image ve çıkış bilgisi [son denetimde](stage1-3-2026-11-11/preservation-and-contract-audit.json) saklanır.

## Son host ve Humble seçkisi

Host üstteki tam komutla tekrarlandı: **455 geçti / 29 atlandı / 1 uyarı / 0**. Yeni ve eski fiziksel/frame araç seçkisi **16 geçti / 0**. Humble:

```sh
docker run -d --init --name fleet-c5-stage13-ros \
 -e ROS_DOMAIN_ID=197 -e ROS_LOCALHOST_ONLY=1 \
 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp -e PYTHONDONTWRITEBYTECODE=1 \
 -v "$PWD:/repo:ro" -v "$PWD/config:/config:ro" \
 -v "$PWD/docs/validation/c5/stage1-3-2026-11-11:/evidence" \
 -w /tmp/ros-tests --entrypoint bash ros2-fleet-c5-validation:humble-fortress -ec '
source /opt/ros/humble/setup.bash
colcon build --base-paths /repo/interfaces /repo/ros2_ws/src > /evidence/ros-build.log 2>&1
source install/setup.bash
cd /repo
export PYTHONPATH=/repo:/repo/backend:/repo/ros2_ws/src/fleet_robot_executor:/repo/ros2_ws/src/fleet_battery_simulator:${PYTHONPATH:-}
python3 -m pytest -q -rs -p no:cacheprovider -p no:launch_testing -p no:launch_ros \
 tests/ ros2_ws/src/fleet_robot_executor/test > /evidence/ros-tests.log 2>&1
'
```

**505 geçti / 0 atlandı / 1 httpx deprecation uyarısı / 0**, OOM=false. Dört ROS paketi derlendi; iki pakette PYTHONDONTWRITEBYTECODE nedeniyle byte-compile devre dışı uyarıları build logunda korunur. Yeni ürün IDL veya C4 kapanış kodu değiştirilmedi.

## Canlı C3/HIGH/C4 regresyonları

```sh
python3 docker/simulation-warehouse-grid/stage13_regressions.py \
 docs/validation/c5/stage1-3-2026-11-11/live-regression-plan.json
```

C5 B kapandıktan sonra başladı. Beş proje **sıralı**, `up --no-build`, mevcut doğrulanmış image’lar, farklı DDS domain’leriyle çalıştı. Driver her `config --format json` çıktısını, image varlığını, çözülmüş bind yollarını; sonrasında Docker inspect/DB/marker/kapanış kontrollerini kaydeder. Yalnız `fleet-c5-stage13-*` kendi projelerine, kanıt alındıktan sonra down uygular; `-v`, prune veya başka proje silme yoktur.

| Proje / domain | Kapsam | Sonuç |
|---|---|---|
| fleet-c5-stage13-c333 / 201 | T01–T10 | 0; 10/10, iki çıkış 0/0 |
| fleet-c5-stage13-high / 202 | T01 + T04-HIGH-E2E | 0; gerçek kesme/duruş/teslim, 0/0 |
| fleet-c5-stage13-c41 / 203 | C4.1 tüketim | 0; 0/0 |
| fleet-c5-stage13-c42 / 204 | C4.2 güncellik/enerji/teslim | 0; 0/0 |
| fleet-c5-stage13-c44 / 205 | Eski C4 profilinde dock temas/ayrılma | 0; 0/0 |

Hepsinde SIMULATION_SHUTDOWN clean=true ve OOM=false. C3/HIGH’dan beş DB kopyası ve C4.4 DB’si saklandı, integrity=ok/foreign key hatası yok. [Tam argümanlar](stage1-3-2026-11-11/live-regression-plan.json), [sonuçlar](stage1-3-2026-11-11/live-regression-plan.results.json). Bu önceki C4 profilinin regresyonudur; 30×18 m Aşama 2/3 başlatılmadı.

## Son analiz, hatalar ve saklama

```sh
python3 docker/simulation-warehouse-grid/stage13_analyze.py docs/validation/c5/stage1-3-2026-11-11
python3 docker/simulation-warehouse-grid/stage13_summary.py docs/validation/c5/stage1-3-2026-11-11
PYTHONPATH=. /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python \
 docker/simulation-warehouse-grid/stage13_scan.py docs/validation/c5/stage1-3-2026-11-11
PYTHONPATH=. /tmp/c5-warehouse-30x18.M8jHJk/venv/bin/python \
 docker/simulation-warehouse-grid/stage13_audit.py docs/validation/c5/stage1-3-2026-11-11
```

Son analizler **0**; 51 izole dünya, bir geçersiz başlangıç ölçümü ve üç kötü kapanış ayrı sınıflandı. Ray analizi ilk denemede container `/workspace/...` asset yolunu hostta doğrulayamadığı için **1** çıktı (`raycast-progress.log`); ham deney profili değiştirilmeden kaynak filo geometrisinin `generated/solids.json` ile eşitliği assert edilerek düzeltildi ve yeni `raycast-corrected/final.log` **0** oldu. İlk canlı parametre yardımcı denemesi Humble’da bulunmayan `rclpy.parameter_client` import’u nedeniyle kaldı; gerçek `rcl_interfaces/srv/GetParameters` ile yapılan denetim 0 ve radius/padding/model değerlerini kaydetti. Bunlar ürün arızası diye sunulmaz.

Üç tuning bridge -11 kapanışı açık kalır; son seçilmiş model ve canlı regresyonların temizliği eski alt nedeni çözmüş sayılmaz. Önceki Battery `_take_subscription` kök nedeni de çözülmüş ilan edilmedi.

Tüm ham JSONL/log/SDF/haritalar yerelde korunur. Git’e per-varyant ham arşivler, küçük özetler, manifestler, screenshot ve kaynak snapshot’ları alınır. [Arşiv manifesti](stage1-3-2026-11-11/raw-evidence-manifest.json), [dosya hash’leri](stage1-3-2026-11-11/raw-file-hashes.json), [arşiv doğrulaması](stage1-3-2026-11-11/archive-verification.json); videolar yerelde ve [medya manifestindedir](stage1-3-2026-11-11/media-manifest.json). Arşiv yeni boş dizine açılmalıdır; kullanıcı dosyaları üzerine yazılmaz. Nihai kaynak manifesti HEAD’e ek olarak kirli kaynakları tanımlar. Kullanıcı değişiklikleri kısmi Git staging ile korunur; push/merge yapılmaz.

Son whitespace kontrolünde ham `baseline.diff` içindeki patch bağlam boşlukları ve üç verbatim ROS param dump’ındaki son boş satır nedeniyle kapsam dışı bırakılmamış `git diff --cached --check` **2** döndü. Bu dört ham capture değişmez kanıt olarak yeniden biçimlendirilmedi. Yalnız bu dört dosya hariç kaynak, yeni rapor ve diğer artifact kontrolü **0**; tam komut ve kapsam `style-check.json` içindedir. İşlevsel test sonucu veya ham dosya hash’i değiştirilmedi.
