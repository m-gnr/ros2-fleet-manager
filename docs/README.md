# Dokümantasyon haritası

## Güncel mimari ve çalışma kuralları

- [AGENTS.md](../AGENTS.md) ve [kalıcı proje bağlamı](project-context.md): kullanıcı kuralları ve kaynak önceliği.
- [Nihai mimari PDF](ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.pdf): birincil mimari referans, DOC-ARCH-2026-10-23-FINAL. [Markdown anlatımı](ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md) birlikte korunur.
- [Revize Karar 08](ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf) ve [v2.3 geçiş kaydı](architecture-v2.3-transition.md): ilgili onaylı hükümler ve karar geçmişi.

Kaynak önceliği bu dizinle değiştirilmez. Nihai belgenin açık çelişki çözümleri eski hükümleri değiştirir. Üç servisli hedef **ONAYLANDI**; canlı uçtan uca çalışma **HENÜZ TEST EDİLMEDİ**. **DOĞRULANDI** yalnız ilgili test kapsamını, **ÖNERİ** henüz onaylanmamış ayrıntıyı ifade eder.

## Geliştirme

- [Proje girişi](../README.md): mevcut depo durumu ve C1–C5 sırası.
- [Compose kılavuzu](../docker/compose/README.md): test katmanları ve güncel yollar.
- [Organizasyon doğrulaması](organization-validation-2026-10-24.md): taşıma kapsamı, kontroller ve sınırlar.
- [C1 Konfigürasyon Altyapısı](configuration-c1.md): `fleet.yaml` yapısı, birimler, Pydantic doğrulayıcı ve şema kuralları.
- [C2 Robot Executor Kararları](c2-executor-decisions-2026-10-24.md): `RobotStatus.msg` faz alanı, `ExecuteTask` öncelik sabitleri ve iki aşamalı test stratejisi kararları.
- [C2.1 Doğrulama Raporu](validation/c2/c2-1-validation-2026-10-24.md): Saf Python durum makinesi ve IDL sözleşmeleri test kanıtı (49/49 test geçti).
- [C2.2 Doğrulama Raporu](validation/c2/c2-2-validation-2026-10-24.md): Robot Executor ROS 2 düğümü, ActionServer, Nav2 istemcisi ve entegrasyon kanıtı (55/55 test geçti).
- [C2.3 Doğrulama Raporu](validation/c2/c2-3-validation-2026-10-24.md): Gazebo Fortress + Nav2 + Robot Executor tek robotlu canlı simülasyon doğrulama kanıtı (2/2 temiz koşu, 7/7 senaryo geçti).
- [C3 Fleet Manager Kararları](c3-fleet-manager-decisions-2026-10-24.md): RobotStatus stale süresi, iletişim kaybı operatör uyarısı/kurtarma ilkesi, IDLE süresine göre eşitlik çözümü ve aging uygulanmaması kararları.
- [C3.1 Doğrulama Raporu](validation/c3/c3-1-validation-2026-10-24.md): Saf Python Fleet Manager çekirdeği, FIFO/öncelik kuyruğu, Wh enerji modeli, Karar 08 T01–T09 senaryoları ve rezervasyon testi kanıtı (25/25 test geçti).

C1 aşamasında `config/fleet.yaml`, şeması ve Pydantic doğrulayıcısı oluşturulup doğrulanmıştır; C2 aşamasında IDL tanımları (`ExecuteTask.action`, `RobotStatus.msg`, `ClearRobotError.srv`), ROS 2'den bağımsız durum makinesi, ROS 2 düğümü (`RobotExecutorNode`) ve tek robotlu canlı Gazebo + Nav2 simülasyon entegrasyonu (C2.1, C2.2, C2.3) tamamlanarak başarıyla doğrulanmıştır. C3 aşamasında Fleet Manager çekirdek kararları (C3-DEC-01–04) kilitlenmiş ve C3.1 saf Python domain çekirdeği ve zamanlayıcı testleri eksiksiz doğrulanmıştır. İstasyon alanının YAML yerleşimi `docs/configuration-c1.md` içinde belgelenmiştir.

- [C3.2 SQLite Outbox ve Tek Consumer](c3-2-sqlite-outbox.md): uygulama sözleşmesi, teslim/tekrar ve senaryo reset sınırları.
- [C3.2 Doğrulama Raporu](validation/c3/c3-2-validation-2026-10-24.md): 29 yeni test ve C1–C3.1 regresyonu; 174 geçti, ROS ortamı gerektiren 10 test atlandı.
- [C3.3 ROS 2 Entegrasyonu Teknik Karar Kaydı](c3-3-integration-decisions-2026-10-24.md): kaynak sıra/oturum, belirsiz teslim, saat ayrımı ve goal ret kararları; açık ayrıntılar ve entegrasyon önkoşulları. Uygulama henüz test edilmedi.
- [C3.3.1 Executor Güvenliği Resmî Karar Kaydı](c3-3-1-executor-safety-decisions-2026-10-24.md): sıra/oturum tipleri, duplicate kayıt ömrü, restart/reset, gerçek terminal epoch ve güvenli iptal için yedi onaylı karar; açık ayrıntılar korunur.
- [C3.3.1 Doğrulama Raporu](validation/c3/c3-3-1-validation-2026-10-24.md): Executor güvenlik kuralları, sıra/oturum sözleşmesi, duplicate koruması, Nav2 güvenli iptali ve canlı simülasyon kanıtı (189 host testi, 81 ROS 2/DDS testi, 7/7 canlı simülasyon senaryosu geçti).
- [C3.3.2 ROS 2 Adaptör Entegrasyonu ve Uygulama Kararları](c3-3-2-ros2-adapter-decisions-2026-10-24.md): sayısal timeout'lar, Nav2 rota önbellekleme/geçersiz kılma, açık goal reddinde `task_review_holds`, restart/oturum mülkiyet koruması ve gerçek `completed_epoch` kararları. Henüz test edilmedi.

## Doğrulama kanıtları

[Doğrulama dizini](validation/README.md), DDS, A, B1, B2, AMCL, B3 ve B3 Retry raporlarını komut ekleriyle birlikte listeler. AMCL sonucu 1 geçti / 1 kaldı; ilk B3 ve Retry ayrı oturumlardır. Kanıtların tarihleri, ölçütleri ve başarısız koşuları korunur.

## Tarihsel belgeler ve korunan kaynaklar

- [B4 hazırlık denetimi](project-architecture-readiness-review-2026-10-23.md): nihai kararlar öncesindeki değerlendirme; sonradan kapanan kararlar yeniden açılmaz.
- [Docker yerleşimi taslağı](docker-placement-decision.md): dar kapsamlı tarihsel taslak; sonradan üç servis onay kaydına dönüştürülmez.
- [Eski mimari özeti](architecture.md) ve [önceki README](archive/readme-v2.x.md): güncel kaynaklarla çelişen hükümleri uygulanmaz.
- [Tasarım PDF'leri](design/): yalnız güncel kararlarla çelişmeyen ayrıntılar için tarihsel kaynak.
- [Kişisel notlar](hand_notes_1.pdf): değiştirilmeden korunur.

İçerik taşımayan `setup.md` ve `requirements.md` kaldırılmıştır. Bilgi içeren tarihsel belgeler silinmemiştir. Değiştirilmeyen PDF'lerin atıf yaptığı taşınmış raporlar için eski konumlarda kısa yönlendirme kayıtları tutulur.
