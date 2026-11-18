# C5-T1 — Deneysel çalışmaların korunması

18 Kasım 2026. Taban `origin/main` =
`da6f27a00e8b6b623b64dd57b257a48f45fc1317`. **T1 bağımsız koruma/izolasyon
kontrolleri DOĞRULANDI. Tam C5 hareket güvenliği kabulü verilmedi.** Bu kayıt,
kullanıcının sonraki açık commit/push talimatının kapsamıdır; önceki kayıtların
“commit/push yapılmadı” ifadeleri kendi çalışma anlarını anlatır ve korunur.

Korunan checkpoint: deneysel PeerRobotLayer, native sıfır-komut alıcısı,
gerçek Nav2 child UUID/Path gözlem API'si, ilgili bağımsız testler, Mermaid/SVG
ve tarihsel kanıtlar. Native alıcı ve peer aktivasyonu varsayılan demo akışına
bağlanmadı. Child gözlemi APPLIED veya hareket izni değildir; release kapalıdır.

## Bu görevde yeniden çalıştırılan kontroller

| Seçki | Yeni sonuç |
|---|---|
| Host: peer config, child binding, protocol, motion gate, core, Outbox, Executor safety, park/şarj, rota | **252 PASS / 0 FAIL / 0 SKIP** |
| Native Humble / ROS tipli Python seçki | **188 PASS / 0 FAIL / 0 SKIP** |
| Temiz PeerRobotLayer build ve gerçek ROS callback gtest'leri | **10 PASS / 0 FAIL / 0 SKIP**; colcon 11 wrapper dahil |
| Temiz B6B.7 native alıcı / callback CTest | **2 PASS / 0 FAIL** |
| Temiz B6B.5 varsayılan derleme kolu regresyonu | **2 PASS / 0 FAIL** |

Komutların tamamı [commands.json](c5-t1-checkpoint-2026-11-18/commands.json),
çıkış kodları/sayılar [results.json](c5-t1-checkpoint-2026-11-18/results.json)
ve aynı dizindeki log/XML dosyalarındadır. Native kontroller ağ kapalı,
workspace salt okunur ve yeni `/tmp/c5-t1-*` build dizinleriyle çalıştı.
Gazebo dünyası veya yeni hareketli senaryo başlatılmadı. Önceki canlı koşular
bu görevde yeniden koşulmuş gibi sunulmaz; önceki başarısız koşular da silinmez.
Tam depo test suite'i bu görevde çalıştırılmadı.

## Varsayılan kapalı sınırı

- `scripts/start_demo.sh`, `start_demo.py`, `c5_demo_start.py`, ürün dashboard
  runtime'ı, Executor node ve motion gate dosyaları `origin/main` ile byte
  düzeyinde aynıdır.
- `generate(..., peer_awareness=False)` korunur. Her iki harness CLI'sindeki
  `--peer-awareness-experiment` yalnız açık `store_true` seçeneğidir.
- Varsayılan launcher native B6B.7 server/supervisor veya library seçmez.
  B6B.7'nin ayrı derleme kolunda hedef daima sıfırdır; kabul edilen imzalı
  metadata bile nonzero açamaz. Mevcut B6B `send` hareket üretmez.
- Normal C5-A/stock hareket yolu değişmedi. Bu checkpoint, normal demodaki
  eski park teması riskinin kapandığı veya costmap `current=false` değerinin
  fiziksel stop garantisi verdiği anlamına gelmez.

[İzolasyon kontrolü ve kaynak hash'leri](c5-t1-checkpoint-2026-11-18/isolation.json).

## Dosya kapsamı ve koruma

Kaynak/diff incelemesinde kapsam dışı takipli/takipsiz değişiklik bulunmadı.
İki kanıt arşivinin **353 SHA-256 girdisi** ve arşiv envanteri doğrulandı;
geçmiş kanıtlar değiştirilmedi. Arşivlenmiş fixture araçları tarihsel test
araçlarıdır; varsayılan launcher girişleri değildir.

Cache, `.venv`, `node_modules`, `__pycache__` ve yeni derleme ürünleri commit
kapsamına alınmadı; yerlerinde korundu. [Ayrı tutulan yerel dosyalar](c5-t1-checkpoint-2026-11-18/excluded-local-files.json).
Kaynak/deney kanıtları ilgili kapsamda tutulur. Native gerçek provision
anahtarları veya batarya test token'ı arşivde yoktur; `TestFixture.hh` içindeki
sabit anahtar açıkça deterministik unit fixture'ıdır.
[İçerik kontrolü](c5-t1-checkpoint-2026-11-18/content-checks.json) ·
[Arşiv doğrulaması](c5-t1-checkpoint-2026-11-18/archive-checks.json).

Hiçbir mevcut dosya silinmedi veya sıfırlanmadı. T1 başlangıcındaki kaynak ve
kanıt byte'ları korunur; yalnız bu kayıt ve dokümantasyon haritası eklenir.
[Koruma kaydı](c5-t1-checkpoint-2026-11-18/preservation.json).

Tam staged `git diff --check`, 15 ham test logundaki 205 whitespace
uyarısı nedeniyle çıkış kodu 2 verir. Log byte'ları kanıt bütünlüğü için
düzeltilmedi. Yalnız bu 15 log hariç tutularak kaynak, config, test ve
doküman kontrolü tekrarlandı ve geçti (çıkış kodu 0).
[Kontrol komutları ve tam uyarılar](c5-t1-checkpoint-2026-11-18/whitespace-checks.json).

## Commit ve uzak dal kapısı

Fetch sonrası başlangıç HEAD ve `origin/main` aynı; ayrışma `0 0` idi.
Checkpoint `codex/c5-t1-experimental-checkpoint` dalında, **deneysel ve varsayılan
kapalı** içeriği belirten commit mesajıyla hazırlanır. Push öncesi uzak main
yeniden kontrol edilir; yalnız fast-forward ise normal `HEAD:main` push yapılır.
Force push, rebase, reset veya başka worktree değişikliği yapılmaz.
Bu tek checkpoint commit'i hem değişiklikleri hem T1 doğrulama kaydını içerir;
kendi SHA'sı commit içeriğine döngüsel olarak yazılmaz. Sonuç SHA ve uzak SHA
teslim yanıtında verilir.

## C5-T2 başlangıcı

**Deneysel, varsayılan entegrasyonu kapalı bir kaynak checkpoint'i.** Bağımsız
peer/native/kimlik testleri geçer. Gerçek ExecuteTask → FollowPath → canlı FM
permit'i → native actuator atomik uygulaması, gerçek sağlık snapshot'ı,
hareketli stop zarfı, hold/resume ve fiziksel release hâlâ kabul edilmemiştir.
T2 bu zinciri mevcut B6B bileşenlerinde tamamlamalı; bu checkpoint'in veya
üç durağan FollowPath SUCCEEDED sonucunun hareket güvenliği onayı olduğu
varsayılmamalıdır. [Ayrıntılı mevcut eksikler](traffic-integration-2026-11-18.md#hareketli-kabul-kapısı).
