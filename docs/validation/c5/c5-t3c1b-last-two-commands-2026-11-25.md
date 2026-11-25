# C5-T3C-1B son iki engel — Komut ve kanıt eki

25 Kasım 2026. [Kabul, nedenler ve sınırlar](c5-t3c1b-last-two-2026-11-25.md).
Komutlar depo kökünden, pytest ise belirtilen salt okunur kaynak kopyasında
çalıştırıldı. Yeni çalışma kökü `/tmp/c5-t3c1b-last-two-20261125`.

## İlk koruma ve tanı

`git status --short`, mevcut diff ve referans raporlar okundu; initial-status,
initial.patch ve 499 dosyalık initial-source-manifest kaydedildi. Önceki tam
kaynak kopyası ve arşivler korundu. Ana süreç pump/callback/context/evaluation,
gerçek health publish ve worker/IPC/writer zamanları tanısal olarak eklendi;
ölçüm damgası veya güvenlik süresi değiştirilmedi.

```bash
bash docker/experiments/c5-t3c1b/build.sh /tmp/c5-t3c1b-last-two-20261125/native-diagnostic1
bash /tmp/c5-t3c1b-last-two-20261125/run-diagnostic1.sh
```

İlk doğrudan executable çağrısı build.sh izin biti nedeniyle 126 döndü;
script değiştirilmeden `bash` ile çalıştırıldı. Native CTest 2/2 geçti.
Diagnostic1 kaynak kopyası salt okunurdu; yalnız iki problemli senaryo,
domain 211–212 ile çalıştı. Observation koşusu REPLAY mask=2 ile FAIL verdi.

Düzeltmeden sonra yeni kaynak/native dizini ve yeni ledger'lar kullanıldı:

```bash
bash docker/experiments/c5-t3c1b/build.sh /tmp/c5-t3c1b-last-two-20261125/native-fixed1
bash /tmp/c5-t3c1b-last-two-20261125/run-fixed1.sh
bash /tmp/c5-t3c1b-last-two-20261125/run-targeted-final.sh
bash docker/experiments/c5-t3c1b/build.sh /tmp/c5-t3c1b-last-two-20261125/native-final
bash /tmp/c5-t3c1b-last-two-20261125/run-targeted-final2.sh
```

Fixed1 iki koşu geçti. Aradaki targeted-final observation koşusu gerçek ACK
önkoşulunda **FAIL** verdi; aynı adla tekrar çalıştırılmadı. Son final2
çifti domain 219–220 ile, `C5_1B_DIAGNOSTICS=1` ve aynı fixed-a4 ROS overlay
ile geçti. Bunlar sekiz ayrı hedefli denemedir; başarısızlar da arşivdedir.
Final2 `--cases odometry-loss observation-loss` audit'i PASS verdi;
hedefli audit tek başına 14'lü kabul sayılmadı.

[Tanısal script'ler ve ledger'lar](c5-t3c1b-last-two-2026-11-25/commands/)
stdout/stderr ve exit sonuçlarını korur. Kaynak sürümleri source-diagnostic1,
source-fixed1, source-final ve source-final2 tar.gz + manifestleriyle saklandı.

## Regresyonlar

Host seçkisi önceki [tam listeyle](c5-t3c1b-final-commands-2026-11-25.md),
`source-final2` kökünde aynı PYTHONPATH, Python venv ve
`pytest -q -p no:cacheprovider` ile tekrarlandı: **487 passed in 12.09s**.
ROS seçkisi de aynı test listesiyle, `--network none`, domain 173,
CycloneDDS, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, source-final2:/workspace:ro ve
ros-fixed-a4:/build:ro ile tekrarlandı: **200 passed in 18.87s**.
Log'lar host-regression/ros-regression adlarıyla arşivdedir.

Native build.sh Release `-O2 -UNDEBUG`, mevcut CMake hedefleri ve
`ctest --output-on-failure` kullandı; son **2/2** geçti. Yeni test, yedi
REPLAY alt koşulunu ve eski NO_COMMAND'ın yeni isteği korumasını denetler.
Ayrıca frozen source-final2 üzerinden:

```bash
g++ -std=c++17 -O1 -UNDEBUG /workspace/docker/experiments/c5-t3c1a/test_ipc.cc -o /evidence/ipc-macro-off-test
/evidence/ipc-macro-off-test
source /opt/ros/humble/setup.bash
source /build/install/local_setup.bash
/build/lifecycle/bridge-lifetime
```

Network-none container'da macro-off IPC **PASS**, iki gerçek bridge owner
kontrolünde `references_before_reset=1 expired=1`, exit 0.

Eski davranış yalnız negative-control-source test kopyasında geri kondu.
İlk standalone derleme mevcut sağlık makrosunu atladığı için compile FAIL;
ikinci komut `-DC5_SPLIT_HEALTH_VETO=1` ile derlendi ve yeni assertion'da
beklenen nonzero **133** verdi. `negative-control.log`, `negative-control2.log`
ve patch'li kaynak tar'ı korunur. Bu kontrol canlı/gerçek sağlık kanıtı değildir.

## Son sabit sürüm ve 14 seri senaryo

Source-final2 SHA:
`7fd145e3312186bfe3f96ea94ad674f9785bb5bd4bf703b5c1437a6f5a32d3f3`.
Native-final + ROS fixed-a4 + cleanup backport + Docker image runtime-pin ile
sabitlendi. Hedefli son çift, regresyonlar ve aşağıdaki matris aynı sürümdedir:

```bash
bash /tmp/c5-t3c1b-last-two-20261125/run-matrix.sh
```

[Tam çalıştırılan script](c5-t3c1b-last-two-2026-11-25/commands/run-matrix.sh)
ve [14 CLI exit ledger](c5-t3c1b-last-two-2026-11-25/commands/matrix.tsv).
Script yeni container/DB/session/partition, domain 181–194, üç salt okunur
source/ROS/native bağı ve deneysel cleanup env'i kullanır. Her önceki container
bitmeden sonraki başlamaz. Child tanıları açık kaldı; gerçek robot Scheduler
ve gerçek ACK kimliğinden seçildi. Her satır CLI 0 verdi.

```bash
python3 /tmp/c5-t3c1b-last-two-20261125/source-final2/docker/experiments/c5-t3c1b/audit.py \
 /tmp/c5-t3c1b-last-two-20261125 /tmp/c5-t3c1b-last-two-20261125/matrix.tsv \
 /tmp/c5-t3c1b-last-two-20261125/full-audit.json
python3 /tmp/c5-t3c1b-last-two-20261125/closure_proof.py
python3 /tmp/c5-t3c1b-last-two-20261125/verify_final.py
python3 /tmp/c5-t3c1b-last-two-20261125/timing_proof.py
```

**Tam audit PASS, acceptance_complete=true**; filtre/skip/completed-only yok.
Closure gerçek controller/planner binary mapping/join marker ve kaynakları;
final verifier kaynak/image/binary hash, PENDING Outbox, DB integrity, gerçek
ACK/context, temiz kapanış ve **14.715 sıfır writer hedefini** doğrular.
Timing proof iki hedefli son koşunun kaynak receipt→publish→worker→IPC→writer
aşamalarını ayrı tutar. Script'ler mevcut kanıtları okur; hareket başlatmaz.

## Koruma, arşiv ve Git

Önceki üç arşivde 4.810 raw hash değişmedi. Yeni arşiv **1.825 raw dosya**,
[manifest](c5-t3c1b-last-two-2026-11-25/manifest.json) ve
[geri açma doğrulaması](c5-t3c1b-last-two-2026-11-25/archive-verification.json)
ile saklandı. Binary executable/.so ve gerçek provision key'ler alınmadı.
Tüm orijinal /tmp çıktıları da bırakıldı. Kaynak ağacı silinmedi/sıfırlanmadı.

`git diff --check`, varsayılan yolların HEAD diff'i, bütün pin'lerin tekrar
hash'i ve önceki arşivlerin hash'i denetlendi. `git fetch origin main`
sonrasında uzak taban f69d1024… ve `merge-base --is-ancestor origin/main HEAD`
exit 0 idi. Tam kabulden sonra ilgili deneysel kaynak/rapor/kanıtlar için
normal commit ve `git push origin HEAD:main` yetkilidir; force push yoktur.
Son commit/uzak SHA ve temiz çalışma ağacı oturum tesliminde doğrulanır.


Checkpoint sonrasında `.patch` format kontrolü de yapıldı. Source-only
`git diff --check HEAD^ HEAD -- . ':(exclude)docker/experiments/c5-t3c1b/patches/*.patch'`
exit 0 verdi. `git apply --numstat` bridge patch'inde exit 0, kullanılmayan
Nav2 tarihsel patch'inde **exit 128 / corrupt patch** verdi. İkisi de ham
çıktısıyla saklandı; Nav2 artefaktı PASS diye işaretlenmedi. Aktif build'in
bu patch'i kullanmadığı build_ros.sh girdilerinden kontrol edildi.
