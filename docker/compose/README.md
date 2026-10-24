# Doğrulama Compose dosyaları

Bu dosyalar uygulamanın nihai üç servisli dağıtımı değildir. Komutlar depo kökünden çalıştırılır; her dosya için `-f docker/compose/<dosya>` kullanılır. İlk dosya daima DDS tabanıdır. Farklı bir `--project-directory` ile göreli yolların anlamı değiştirilmemelidir.

| Test | Dosyaların sırası |
|---|---|
| DDS | `docker-compose.dds.yml` |
| Action | DDS → `docker-compose.dds-action.yml` |
| A | DDS → `docker-compose.simulation-check.yml` |
| B1 | DDS → A → `docker-compose.simulation-lidar-check.yml` |
| B2 | DDS → A → `docker-compose.simulation-nav2-check.yml` |
| AMCL | DDS → A → `docker-compose.simulation-amcl-test.yml` |
| B3 | DDS → A → `docker-compose.simulation-b3.yml` |
| B3 Retry | DDS → A → `docker-compose.simulation-b3-retry.yml` |
| C2.3 | DDS → A → `docker-compose.simulation-c2-3.yml` |

DDS için `DDS_TEST_PAYLOAD` zorunludur. Env dosyaları ve bind mount kaynakları depo kökündeki `config/` ve `docker/` dizinlerine gider. Container içindeki yollar, proje/servis/ağ adları ve image adları korunmuştur. Dosyaların yerinin değişmesiyle `.env` arama bağlamı da etkilenebilir; depoda `.env` yoktur. Başka çalışma dizini veya sonradan eklenen yerel env dosyası için ayrıca doğrulama gerekir.

## Image bağımlılıkları

DDS image'ı temel alınır; A, B1 ve Nav2 image'ları aşamalı hazırlanır. Action image'ı da DDS tabanına bağlıdır. B2/AMCL/B3/Retry katmanları Nav2 image adını kullanırken A katmanının build tarifini miras alır. Bu mevcut davranış organizasyon sırasında değiştirilmedi. Bu birleşimlerde `build` veya `up --build` doğru Nav2 bağımlılık image'ını üretme garantisi vermez; [B2 hazırlık kanıtı](../../docs/validation/simulation/b2/simulation-stage-b2-2026-10-23.md) esas alınmalıdır.

## Tarihsel komutlar

[Doğrulama kayıtlarındaki](../../docs/validation/README.md) komut ve çıktılar geçmiş koşuların kanıtıdır; içlerindeki eski kök Compose yolları korunur. Yeniden kullanımda her `-f docker-compose.*.yml` yolu `-f docker/compose/docker-compose.*.yml` olarak uyarlanır. Test kodu ve config yolları değişmedi. B3 Retry host betiğinin aktif Compose referansları güncellendi.

24 Ekim 2026 organizasyon kontrolünde sekiz birleşimin çözümlenen yapılandırması taşıma öncesiyle eşdeğerdir. Bu kontrol image derlemesi veya canlı ROS/Gazebo testi değildir.
