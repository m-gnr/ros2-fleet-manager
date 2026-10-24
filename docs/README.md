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

`fleet.yaml` ve uygulama paketleri henüz oluşturulmamıştır. İstasyon alanının YAML yerleşimi gibi açık kararlar dosya organizasyonuyla çözülmüş sayılmaz.

## Doğrulama kanıtları

[Doğrulama dizini](validation/README.md), DDS, A, B1, B2, AMCL, B3 ve B3 Retry raporlarını komut ekleriyle birlikte listeler. AMCL sonucu 1 geçti / 1 kaldı; ilk B3 ve Retry ayrı oturumlardır. Kanıtların tarihleri, ölçütleri ve başarısız koşuları korunur.

## Tarihsel belgeler ve korunan kaynaklar

- [B4 hazırlık denetimi](project-architecture-readiness-review-2026-10-23.md): nihai kararlar öncesindeki değerlendirme; sonradan kapanan kararlar yeniden açılmaz.
- [Docker yerleşimi taslağı](docker-placement-decision.md): dar kapsamlı tarihsel taslak; sonradan üç servis onay kaydına dönüştürülmez.
- [Eski mimari özeti](architecture.md) ve [önceki README](archive/readme-v2.x.md): güncel kaynaklarla çelişen hükümleri uygulanmaz.
- [Tasarım PDF'leri](design/): yalnız güncel kararlarla çelişmeyen ayrıntılar için tarihsel kaynak.
- [Kişisel notlar](hand_notes_1.pdf): değiştirilmeden korunur.

İçerik taşımayan `setup.md` ve `requirements.md` kaldırılmıştır. Bilgi içeren tarihsel belgeler silinmemiştir. Değiştirilmeyen PDF'lerin atıf yaptığı taşınmış raporlar için eski konumlarda kısa yönlendirme kayıtları tutulur.
