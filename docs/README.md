# Dokümantasyon haritası

## Kategori dizini

- [Mimari kaynaklar](architecture/README.md)
- [Onaylı karar kayıtları](decisions/README.md)
- [Teknik tasarımlar](design/README.md)
- [Algoritma diyagramları ve kapsam tablosu](diagrams/README.md)
- [26 Ekim depo düzeni ve doğrulama raporu](validation/organization/organization-validation-2026-10-26.md)

## Güncel mimari ve çalışma kuralları

- [AGENTS.md](../AGENTS.md) ve [kalıcı proje bağlamı](project-context.md): kullanıcı kuralları ve kaynak önceliği.
- [Nihai mimari PDF](ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.pdf): birincil mimari referans, DOC-ARCH-2026-10-23-FINAL. [Markdown anlatımı](ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) birlikte korunur.
- [Revize Karar 08](ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf) ve [v2.3 geçiş kaydı](architecture/architecture-v2.3-transition.md): ilgili onaylı hükümler ve karar geçmişi.

Kaynak önceliği bu dizinle değiştirilmez. Nihai belgenin açık çelişki çözümleri eski hükümleri değiştirir. Üç servisli hedef **ONAYLANDI**; canlı uçtan uca çalışma **HENÜZ TEST EDİLMEDİ**. **DOĞRULANDI** yalnız ilgili test kapsamını, **ÖNERİ** henüz onaylanmamış ayrıntıyı ifade eder.

## Geliştirme

- [Visualize V6 dış zemin paleti](validation/c5/visualize-v6-palette-2026-11-17.md).

- [Visualize V6 yaşayan dış çevre](validation/c5/visualize-v6-validation-2026-11-17.md) · [Komutlar](validation/c5/visualize-v6-commands-2026-11-17.md).

- [Visualize V5 minimal dış çevre](validation/c5/visualize-v5-validation-2026-11-17.md) · [Komutlar](validation/c5/visualize-v5-commands-2026-11-17.md).

- [Visualize V4 zemin ve aydınlatma](validation/c5/visualize-v4-validation-2026-11-17.md) · [Komutlar](validation/c5/visualize-v4-commands-2026-11-17.md).
- [Visualize V3 robot öncelikli sunum](validation/c5/visualize-v3-validation-2026-11-17.md) · [Komutlar](validation/c5/visualize-v3-commands-2026-11-17.md).
- [Visualize V2 zemin adları ve nokta bilgi balonları](validation/c5/visualize-v2-validation-2026-11-17.md) · [Komutlar](validation/c5/visualize-v2-commands-2026-11-17.md).
- [Visualize V1 görev noktası görsel doğrulaması](validation/c5/visualize-v1-validation-2026-11-17.md) · [Komutlar](validation/c5/visualize-v1-commands-2026-11-17.md).

- [C5 Docker preflight ve çoklu simülasyon kontrolü](validation/c5/docker-simulation-preflight-2026-11-17.md) · [Komutlar ve ölçümler](validation/c5/docker-simulation-preflight-commands-2026-11-17.md): C5 launcher başlangıcında Docker envanteri, kaynak raporu ve çakışma kapısı.
- [C5 güvenli oturum temizliği ve tek demo cold-start](validation/c5/c5-session-cleanup-2026-11-17.md) · [Komutlar ve ölçümler](validation/c5/c5-session-cleanup-commands-2026-11-17.md): farklı worktree'lerdeki eski C5 oturumlarının kontrollü kapatılması, Gamma `exit 137` kaydı ve üç robot readiness kanıtı; sonraki AMCL güncelliği doğrulanmadığı için PARTIAL.
- [C5-A main entegrasyon checkpoint'i](validation/c5/c5-a-main-integration-2026-11-14.md) · [Üç taraflı karşılaştırma, komutlar ve canlı koşu sonucu](validation/c5/c5-a-main-integration-commands-2026-11-14.md).
- [C5-A gerçek Chrome / Gazebo ilk entegrasyonu](validation/c5/c5-a-first-integration-2026-11-14.md) · [Gerçek komutlar](validation/c5/c5-a-first-integration-commands-2026-11-14.md): tek gerçek Chrome görevi COMPLETED; iki robot, TF ve batarya görünürlüğü. Sensör qualification kabulü değildir.
- [C5 Alpha/Beta TF cold-start readiness](validation/c5/c5-alpha-beta-tf-startup-2026-11-17.md) · [Komut eki](validation/c5/c5-alpha-beta-tf-startup-commands-2026-11-17.md): AMCL, Nav2 lifecycle, gerçek TF ve GUI/API başlangıç kapısı.
- [C5 üç robot AMCL readiness incelemesi](validation/c5/c5-three-robot-amcl-readiness-2026-11-17.md) · [Komut eki](validation/c5/c5-three-robot-amcl-readiness-commands-2026-11-17.md): AMCL tekrar yayını, etkin parametreler ve hareketsiz üç robot readiness gözlemi; geçiş nedeni kayıtlı olmadığından PARTIAL.
- [C5 üçüncü robot Gamma entegrasyonu](validation/c5/third-robot-gamma-2026-11-17.md) · [Komut eki](validation/c5/third-robot-gamma-commands-2026-11-17.md): 30 × 18 m depo, üç robotlu cold-start ve Chrome 3D görünümü.
- [C5 Alpha/Beta demo sürümüne dönüş](validation/c5/alpha-beta-demo-return-2026-11-17.md) · [Canlı koşu komutları ve sonuç](validation/c5/alpha-beta-demo-return-commands-2026-11-17.md): iki robotlu cold-start ve GUI geçti; gerçek taşıma dropoff Nav2 abort ile kaldı.
- [C5 Aşama 1.7A depo modeli araştırması](research/c5-stage1-7-warehouse-model-research.md) — Sunum için üç hazır aday, lisans ve WebGL incelemesi, tek model önerisi.
- [Gereksinim analizi, literatür taraması ve özgünlük değerlendirmesi](reports/gereksinim-literatur-ozgunluk-2026-10-27.md): 27 Ekim 2026; [PDF](reports/gereksinim-literatur-ozgunluk-2026-10-27.pdf), [tarama ve doğrulama eki](reports/gereksinim-literatur-ozgunluk-tarama-eki-2026-10-27.md). Kaynak temelli sınırlı araştırma, 24 gereksinim ve güncel host testi; yeni mimari karar veya ürün kabulü değildir.
- [C4 öncesi kapsamlı teknik rapor](reports/c4-oncesi-teknik-rapor-2026-10-25.md): 25 Ekim 2026 tarihli 38 sayfalık PDF; güncel uygulama, tarihsel test kanıtları, SQL şeması ve statik teknik bulgular. Yeni mimari karar veya yeniden çalıştırılmış ürün testi değildir.
- [C5 Aşama 1.3 AMCL ve güvenli raf yaklaşması](validation/c5/c5-stage1-3-localization-approach-2026-11-11.md) · [Komut eki](validation/c5/c5-stage1-3-commands-2026-11-11.md).
- [C5 Aşama 1.2 fiziksel model, odometri, AMCL ve footprint](validation/c5/c5-stage1-2-physical-localization-2026-11-11.md): son pickup 1/5; F2 ve paralel görev regresyonu açık, koşulsuz kabul yok.
- [C5 Aşama 1.1 feedback ve fiziksel pickup yeniden doğrulaması](validation/c5/stage1-1-validation-2026-11-11.md) · [Komutlar](validation/c5/stage1-1-commands-2026-11-11.md): F1 düzeltildi; F2 açık, koşulsuz kabul yok.
- [30 × 18 m uçtan uca görev doğrulaması — Aşama 1](validation/c5/e2e-stage1-validation-2026-11-11.md) · [Komut eki](validation/c5/e2e-stage1-commands-2026-11-11.md): üç gerçek COMPLETED; feedback ve fiziksel hassasiyet bulguları nedeniyle koşulsuz kabul verilmedi. Sonraki aşamalar onay bekliyor.
- [30 × 18 m dağıtılmış depo ve katalog görev girişi](validation/c5/warehouse-30x18-validation-2026-11-11.md) · [Komut eki](validation/c5/warehouse-30x18-commands-2026-11-11.md)

- [C5 Aşama 1 salt okunur operasyon paneli](design/c5-readonly-dashboard.md) · [API sözleşmesi](design/c5-readonly-api.md) · [Arayüz ve koordinatlar](design/c5-dashboard-ui.md) · [Doğrulama](validation/c5/c5-stage1-validation-2026-11-06.md)
- [C5 Aşama 1.5 3D operasyon paneli](design/c5-3d-operations.md) · [Karar](decisions/c5-stage1-5-3d-decision-2026-11-06.md) · [Doğrulama](validation/c5/c5-stage1-5-validation-2026-11-06.md)
- [C5 Aşama 1.6 arayüz doğrulaması](validation/c5/c5-stage1-6-validation-2026-11-06.md) · [Komutlar](validation/c5/c5-stage1-6-commands-2026-11-06.md)
- [C5 Aşama 1.6 görsel kabul düzeltmesi](validation/c5/c5-stage1-6-visual-acceptance-2026-11-06.md) · [Ölçüm ve doğrulama komutları](validation/c5/c5-stage1-6-visual-commands-2026-11-06.md)
- [C5 Aşama 1.7D depo duvarları ve operasyon bölgeleri](validation/c5/c5-stage1-7d-validation-2026-11-07.md) · [Doğrulama komutları](validation/c5/c5-stage1-7d-commands-2026-11-07.md)
- [C5 Aşama 1.7E işlevsel depo iç yerleşimi](validation/c5/c5-stage1-7e-validation-2026-11-08.md) · [Doğrulama komutları](validation/c5/c5-stage1-7e-commands-2026-11-08.md)
- [Visualize V2 park alanı yer değişikliği](validation/c5/visualize-park-relocation-2026-11-17.md) · [Komutlar](validation/c5/visualize-park-relocation-commands-2026-11-17.md): gerçek park hedefleri ve görsel yuvalar; sabit robot eşleştirmesi uygulanmadı, canlı Nav2 hedefi henüz test edilmedi.
- [Visualize V2.1 canlı park doğrulama denemesi](validation/c5/visualize-v2-1-live-validation-2026-11-17.md) · [Komutlar](validation/c5/visualize-v2-1-live-commands-2026-11-17.md): yeni hedeflere 9 gerçek Nav2 planı geçti; aktif YAML eski park pozlarını kullanıyor, TF/clock akışı duraklamış, fiziksel park test edilmedi.
- [Visualize V2.3 üç robotun parkta canlı başlangıcı](validation/c5/visualize-v2-3-validation-2026-11-17.md) · [Komutlar](validation/c5/visualize-v2-3-commands-2026-11-17.md): gerçek spawn, WebSocket ve Chrome `3/3 TF LIVE` geçti; fiziksel hareket test edilmedi.
- [C5 ızgara tabanlı depo profili](validation/c5/warehouse-grid-validation-2026-11-08.md) · Tek YAML, koridorlar ve Chrome kabulü.
- [C5 20 × 12 m depo ve Fortress doğrulaması](validation/c5/warehouse-grid-20x12-validation-2026-11-08.md) · Ortak üretim, gerçek dock/teslim hedefleri ve karşılıklı geçiş.
- [C5 üstten depo açıklığı ve etiket denetimi](validation/c5/warehouse-grid-clearance-2026-11-08.md) · Şarj ve alım erişimi, raf dışı etiketler ve Nav2 rota ölçümü.
- [C5 Aşama 1.7C depo sunumu ve operasyon alanları](validation/c5/c5-stage1-7c-validation-2026-11-07.md) · [Ölçüm ve doğrulama komutları](validation/c5/c5-stage1-7c-commands-2026-11-07.md)
- [C5 Aşama 1.7B hazır depo entegrasyonu](validation/c5/c5-stage1-7b-validation-2026-11-07.md) · [Ölçüm ve doğrulama komutları](validation/c5/c5-stage1-7b-commands-2026-11-07.md)

- [Proje girişi](../README.md): mevcut depo durumu ve C1–C5 sırası.
- [Compose kılavuzu](../docker/compose/README.md): test katmanları ve güncel yollar.
- [Organizasyon doğrulaması](organization-validation-2026-10-24.md): taşıma kapsamı, kontroller ve sınırlar.
- [C1 Konfigürasyon Altyapısı](configuration-c1.md): `fleet.yaml` yapısı, birimler, Pydantic doğrulayıcı ve şema kuralları.
- [C2 Robot Executor Kararları](decisions/c2-executor-decisions-2026-10-24.md): `RobotStatus.msg` faz alanı, `ExecuteTask` öncelik sabitleri ve iki aşamalı test stratejisi kararları.
- [C2.1 Doğrulama Raporu](validation/c2/c2-1-validation-2026-10-24.md): Saf Python durum makinesi ve IDL sözleşmeleri test kanıtı (49/49 test geçti).
- [C2.2 Doğrulama Raporu](validation/c2/c2-2-validation-2026-10-24.md): Robot Executor ROS 2 düğümü, ActionServer, Nav2 istemcisi ve entegrasyon kanıtı (55/55 test geçti).
- [C2.3 Doğrulama Raporu](validation/c2/c2-3-validation-2026-10-24.md): Gazebo Fortress + Nav2 + Robot Executor tek robotlu canlı simülasyon doğrulama kanıtı (2/2 temiz koşu, 7/7 senaryo geçti).
- [C3 Fleet Manager Kararları](decisions/c3-fleet-manager-decisions-2026-10-24.md): RobotStatus stale süresi, iletişim kaybı operatör uyarısı/kurtarma ilkesi, IDLE süresine göre eşitlik çözümü ve aging uygulanmaması kararları.
- [C3.1 Doğrulama Raporu](validation/c3/c3-1-validation-2026-10-24.md): Saf Python Fleet Manager çekirdeği, FIFO/öncelik kuyruğu, Wh enerji modeli, Karar 08 T01–T09 senaryoları ve rezervasyon testi kanıtı (25/25 test geçti).

C1 aşamasında `config/fleet.yaml`, şeması ve Pydantic doğrulayıcısı oluşturulup doğrulanmıştır; C2 aşamasında IDL tanımları (`ExecuteTask.action`, `RobotStatus.msg`, `ClearRobotError.srv`), ROS 2'den bağımsız durum makinesi, ROS 2 düğümü (`RobotExecutorNode`) ve tek robotlu canlı Gazebo + Nav2 simülasyon entegrasyonu (C2.1, C2.2, C2.3) tamamlanarak başarıyla doğrulanmıştır. C3 aşamasında Fleet Manager çekirdek kararları (C3-DEC-01–04) kilitlenmiş ve C3.1 saf Python domain çekirdeği ve zamanlayıcı testleri eksiksiz doğrulanmıştır. İstasyon alanının YAML yerleşimi `docs/configuration-c1.md` içinde belgelenmiştir.

- [C3.2 SQLite Outbox ve Tek Consumer](design/c3-2-sqlite-outbox.md): uygulama sözleşmesi, teslim/tekrar ve senaryo reset sınırları.
- [C3.2 Doğrulama Raporu](validation/c3/c3-2-validation-2026-10-24.md): 29 yeni test ve C1–C3.1 regresyonu; 174 geçti, ROS ortamı gerektiren 10 test atlandı.
- [C3.3 ROS 2 Entegrasyonu Teknik Karar Kaydı](decisions/c3-3-integration-decisions-2026-10-24.md): kaynak sıra/oturum, belirsiz teslim, saat ayrımı ve goal ret kararları; açık ayrıntılar ve entegrasyon önkoşulları. Karar anındaki uygulama durumu korunur; sonraki kanıtlar C3.3.1–C3.3.3 raporlarındadır.
- [C3.3.1 Executor Güvenliği Resmî Karar Kaydı](decisions/c3-3-1-executor-safety-decisions-2026-10-24.md): sıra/oturum tipleri, duplicate kayıt ömrü, restart/reset, gerçek terminal epoch ve güvenli iptal için yedi onaylı karar; açık ayrıntılar korunur.
- [C3.3.1 Doğrulama Raporu](validation/c3/c3-3-1-validation-2026-10-24.md): Executor güvenlik kuralları, sıra/oturum sözleşmesi, duplicate koruması, Nav2 güvenli iptali ve canlı simülasyon kanıtı (189 host testi, 81 ROS 2/DDS testi, 7/7 canlı simülasyon senaryosu geçti).
- [C3.3.2 ROS 2 Adaptör Entegrasyonu ve Uygulama Kararları](decisions/c3-3-2-ros2-adapter-decisions-2026-10-24.md): sayısal timeout'lar, Nav2 rota önbellekleme/geçersiz kılma, açık goal reddinde `task_review_holds`, restart/oturum mülkiyet koruması ve gerçek `completed_epoch` kararları.
- [C3.3.2 Doğrulama Raporu](validation/c3/c3-3-2-validation-2026-10-24.md): ROS 2 adaptörleri, `status_seq` ve oturum güvenliği, eylem istemcisi, Outbox göndericisi, `task_review_holds` ve canlı simülasyon kanıtı (212 host testi, 102 ROS 2/DDS testi, 7/7 canlı simülasyon senaryosu geçti).
- [C3.3.3 İki Robotlu Entegrasyon Kararları](decisions/c3-3-3-dual-robot-integration-decisions-2026-10-24.md): iki robotlu çalıştırma düzeni, topic/servis hizalaması, fleet.yaml pozları, C4 öncesi geçici batarya beslemesi, T01 oturum güvenliği ve deadlock kapsam dışı kararları.
- [C3.3.3 Doğrulama Raporu](validation/c3/c3-3-3-validation-2026-10-24.md): İki robotlu uçtan uca canlı simülasyon ve DDS entegrasyonu kanıtı (Gazebo Fortress headless + iki bağımsız Nav2 + iki Executor + Fleet Manager; 214 host testi, T01–T10 senaryolarının tamamı 10/10 temiz geçti).
- [C3.3.4 Görev 1 Doğrulama Raporu](validation/c3/c3-3-4-task-1-validation-2026-11-05.md): Terminal `completed_epoch` doğrulaması ve sahipliğin korunması.
- [C4.2 Entegrasyon Doğrulama Raporu](validation/c4/c4-2-validation-2026-11-06.md): İki robotlu Fortress ortamında BatteryState → RobotStatus → Fleet Manager, batarya güncelliği ve gerçek Nav2 ile atama.

## Doğrulama kanıtları

[Doğrulama dizini](validation/README.md), DDS, A, B1, B2, AMCL, B3 ve B3 Retry raporlarını komut ekleriyle birlikte listeler. AMCL sonucu 1 geçti / 1 kaldı; ilk B3 ve Retry ayrı oturumlardır. Kanıtların tarihleri, ölçütleri ve başarısız koşuları korunur.

## Tarihsel belgeler ve korunan kaynaklar

- [B4 hazırlık denetimi](project-architecture-readiness-review-2026-10-23.md): nihai kararlar öncesindeki değerlendirme; sonradan kapanan kararlar yeniden açılmaz.
- [Docker yerleşimi taslağı](docker-placement-decision.md): dar kapsamlı tarihsel taslak; sonradan üç servis onay kaydına dönüştürülmez.
- [Eski mimari özeti](architecture/architecture.md) ve [önceki README](archive/readme-v2.x.md): güncel kaynaklarla çelişen hükümleri uygulanmaz.
- [Tasarım PDF'leri](design): yalnız güncel kararlarla çelişmeyen ayrıntılar için tarihsel kaynak.
- [Kişisel notlar](hand_notes_1.pdf): değiştirilmeden korunur.

İçerik taşımayan `setup.md` ve `requirements.md` kaldırılmıştır. Bilgi içeren tarihsel belgeler silinmemiştir. Değiştirilmeyen PDF'lerin atıf yaptığı taşınmış raporlar için eski konumlarda kısa yönlendirme kayıtları tutulur.

- [C5 Git kaynak checkpoint ve push denetimi — 12 Kasım](validation/c5/git-checkpoint-2026-11-12/README.md) · [Komutlar](validation/c5/git-checkpoint-commands-2026-11-12.md): kaynak envanteri, yerel ham kanıt manifesti ve sınırlı yeniden üretim kontrolü.

- [C5 Aşama 2.0 dinamik batarya simülasyon kontrolü](design/c5-battery-simulation-control.md) · [Doğrulama](validation/c5/battery-control-validation-2026-11-12.md) · [Komutlar](validation/c5/battery-control-commands-2026-11-12.md).
- [C5 Battery Control / C4 süreklilik uyumu](validation/c5/battery-control-continuity-validation-2026-11-14.md) · [Komutlar](validation/c5/battery-control-continuity-commands-2026-11-14.md).

- [C5-B6B.1 birleşik trafik rezervasyon çekirdeği](validation/c5/c5-b6b1-traffic-core-2026-11-15.md) — Domain/SQLite hedefli doğrulama; hareket yetkisi kapalı.

- [C5-B6B.2 FM ↔ Executor trafik izin protokolü](design/c5-b6b2-traffic-permit-protocol.md) · [Hedefli doğrulama](validation/c5/c5-b6b2-traffic-protocol-2026-11-15.md): ayrı test modu, hareket yetkisi kapalı.

- [C5-B6B.3 yerel hareket kapısı ve actuator sınırı](design/c5-b6b3-traffic-motion-gate.md) · [Doğrulama](validation/c5/c5-b6b3-motion-gate-2026-11-15.md): yalnız fake üretici/actuator; nonzero kapalı, fiziksel fail-safe açık engel.

- [C5-B6B.4 tek son ROS hız çıkışı ve bypass izolasyonu](design/c5-b6b4-single-velocity-output.md) · [Hedefli doğrulama](validation/c5/c5-b6b4-topology-2026-11-15.md): fake actuator ile gerçek ROS/IGN; nonzero kapalı, doğrudan ROS/IGN yazma BLOCKER.

- [C5-B6B.5 izole watchdog build ve timeout](validation/c5/c5-b6b5-watchdog-2026-11-15.md): iki temiz native build, sıfır hedefli timeout/rearm; ham Twist freshness ve bypass BLOCKER.

- [C5-B6B.6 actuator komut yetkilendirmesi](design/c5-b6b6-actuator-authorization.md) · [Hedefli doğrulama](validation/c5/c5-b6b6-authorization-2026-11-15.md): test-only; transport ACL ve fiziksel duruş açık.
