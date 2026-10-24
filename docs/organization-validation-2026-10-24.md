# Dosya organizasyonu doğrulaması

Tarih: 24 Ekim 2026. Kapsam yalnız dosya yerleşimi, gezinme ve aktif yol referanslarıdır.

## Değişiklikler

- Sekiz Compose dosyası `docker/compose/` altına, 15 rapor/komut eki `docs/validation/` altına taşındı.
- Önceki README gövdesi `docs/archive/readme-v2.x.md` altında korundu; kök README güncel giriş oldu.
- Yalnız sıfır baytlık `docs/setup.md` ve `docs/requirements.md` kaldırıldı. Tarihsel B4 envanterinde kaldırılma nedeni belirtildi.
- Bilgi içeren eski belgeler, kişisel notlar ve PDF'ler korundu. Güncellik notları nihai belgenin açık çelişki çözümlerine bağlandı; karar önceliği değişmedi.
- Eski PDF atıfları için dört rapor yolunda yönlendirme kaydı tutuldu. Tarihsel komut blokları değiştirilmedi; yeniden kullanım yolu Compose kılavuzunda açıklandı.

## Kontroller ve sonuçlar

| Kontrol | Yöntem / komut | Sonuç |
|---|---|---|
| Compose eşdeğerliği | Her birleşimde `docker compose -f … config --format json`; sabit `DDS_TEST_PAYLOAD=organization-audit` | DDS, action, A, B1, B2, AMCL, B3, Retry: 8/8 eşdeğer |
| Taşıma öncesi kontrol | Geçici aday dosyalar hedef proje diziniyle çözümlendi | Eşdeğerlik doğrulanmadan dosyalar taşınmadı |
| Yol çözümleme | Taşınmış dosyalar mutlak `-f` yollarıyla depo dışı çalışma dizininden de çözümlendi | Build context/Dockerfile ve salt okunur bind kaynakları mevcut |
| Korunan dosyalar | Başlangıç kopyalarıyla bayt karşılaştırması | AGENTS, PDF'ler, kişisel not, config, mevcut Docker/test kodu, ROS arayüzleri: 53 dosya aynı |
| Tarihsel kanıtlar | Önce/sonra fenced blok karşılaştırması; komut eklerinde tam dosya karşılaştırması | Tüm bloklar ve altı komut eki aynı; rapor değişiklikleri yol referanslarıyla sınırlı |
| Host betiği | Önce/sonra karşılaştırma ve `ast.parse` | Yalnız üç Compose yolu değişti; sözdizimi geçerli |
| Markdown | Yerel dosya hedefleri ve başlık/explicit anchor taraması | Kırık yerel bağlantı kalmadı |
| Diff | `git diff --check`, `git diff --cached --check` ve içerik incelemesi | Görev dışı kod/davranış değişikliği yok |

Compose karşılaştırması JSON anahtar sırasından bağımsızdır. Çalıştırılabilir bütün Compose alanları karşılaştırıldı; yalnız ham göreli yolları taşıyan `x-` şablon alanları hariç tutuldu. Servislerde bu şablonların çözümlenmiş sonuçları karşılaştırmaya dahildir. Önce/sonra JSON kayıtları yerel geçici çalışma dizininde saklandı; ortama özgü mutlak yollar içeren bu kayıtlar depoya eklenmedi.

Başlangıçtaki tek yerel değişiklik `AGENTS.md` üzerindeydi; dosya değiştirilmedi ve bu görevin commit kapsamına alınmadı.

## Sınırlar

Canlı ROS/Gazebo testleri, image build ve uygulama testleri yeniden çalıştırılmadı. Yapılandırma eşdeğerliği bunların başarı kanıtı değildir. B2/AMCL/B3/Retry birleşimlerinin Nav2 image adıyla A katmanı build tarifini miras alması mevcut bir risktir; düzeltilmedi. Depoda `.env` yoktu; farklı çalışma dizini/yerel env senaryoları ayrıca doğrulanmalıdır. Harici betikler eski kök Compose yollarını kullanıyorsa güncellenmelidir.
