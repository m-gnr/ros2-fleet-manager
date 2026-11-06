# C5 / Aşama 1.5 — Salt okunur 3D operasyon görünümü

## Entegrasyon ön incelemesi

C5 Aşama 1 `76a80ab` commit'inde `frontend/src` altında operasyon kartları, Konva haritası ve bağımsız ürün snapshot istemcisi bulunur. Visualizer Aşama 4 `f3e3901` commit'inde `fleet-visualizer/frontend/src` altında sahne, kamera, TurtleBot3, TF akış indirgeyicileri ve plan/iz katmanları ayrı modüllerdir. Tam ekran Visualizer layout'u ile robot paneli C5'e taşınmaz. C5'in Konva matematiği operasyon kartlarından bağımsızdır. İki uygulama TypeScript 5.9.3 ve Vite 7.3.7 kullanır. C5 React 19.3.1, Visualizer React 19.2.0 kullanır. İçe aktarılan R3F 9.4.0 ve Three.js 0.181.2 sürümleri korunur. Sahne Three.js OrbitControls kullanır. Drei bağımlılığı bulunmaz. İki tabanda da aynı depo lisansı geçerlidir.

C5 ürün snapshot'ı Fleet Manager'dan tam kayıt, kaynak oturumu, sıra, ürün alım güncelliği ve simülasyon damgası taşır. Visualizer her robot için `map` TF, ayrı stream kimliği, simülasyon epoch'u, damga watermark'ı, Path TTL ve segmentlenmiş iz tutar. Yerel süreler kendi monotonik saatiyle değerlendirilir. Son iki TF ölçümü arasında interpolasyon yapılır. Robot seçimi C5'te ortak robot ID ile bağlanır. Ayrı kamera state'i sunuma aittir. İstasyon sahipliği ve taşıma durumu ürün snapshot'ından gelir.

## Dağıtım seçimi

**A seçildi.** Aynı doğrulanmış salt okunur Visualizer köprüsü bağımsız süreçte çalışır. FastAPI yalnız config ile belirlenen köprüye abone olur. B seçeneği C5'e ROS çalışma zamanı ve hata alanı getirirdi. C seçeneği tarayıcıya ikinci ağ girişi ve ayrı köprü Origin yapılandırması getirirdi. Fleet Manager, web süreci ve köprünün yeniden başlatma yaşam döngüleri ayrıdır. Köprü ROS okuma işlemlerini kendi yürütücüsünde çalıştırır.

Tarayıcı `/ws/fleet` üzerinde `fleet.scene.v1` alt protokolünü ister. Alt protokolsüz ürün istemcisi Aşama 1 sözleşmesini kullanır. Yeni akışta ürün snapshot'ı kendi şemasında kalır. `product_unavailable` ürün kaynağını, `scene_connected` ve `scene_disconnected` TF akış yaşam döngüsünü, `scene` Visualizer paketini, `heartbeat` yalnız taşıma bağlantısını bildirir. Ürün kaynağı oturum değişiminde veya geçersizleşince yeniden teyit edilir. TF oturumu köprü el sıkışmasıyla kurulur. Köprü paketlerini sırayla ileten, istemci başına sınırlandırılmış bir abonelik vardır. Yeniden bağlantıda paket replay'i yapılmaz. Yeni robotlar ve namespace eşlemesi doğrulanmış `fleet.yaml` üzerinden gelir.

## Sunum ve kaynak sınırları

**ONAYLANDI.** Ana görünüm, kullanıcı talimatıyla Konva 2D'den açık renkli Three.js ve React Three Fiber sahnesine geçer. Açık gri platform, beyaz raflar, kontrollü durum renkleri ve çapraz başlangıç kamerası Flowdeck’in görsel yaklaşımından esinlenir. [Callour Studio referansı](https://dribbble.com/shots/27098154-Flowdeck-AI-Warehouse-Management) Ürün panelleri mevcut C5 bileşenlerini kullanır. Temsili raf ve yollar Nav2 haritası olarak kullanılmaz.

Fleet Manager görev, ürün durumu, C4 batarya ve istasyon sahipliği için yetkilidir. TF robot modeli, poz güncelliği ve iz için ayrı görüntüleme kaynağıdır. **GÖZLEMLENEN NAV2 PLANI (Durum B)** yalnız doğrulanmış robot namespace'indeki gözlemdir. Aktif goal UUID ilişkisi doğrulanmamıştır. Bağlantı veya veri kaybında güncel batarya gizlenir, geçmiş ürün kayıtları işaretlenir ve son geçerli TF pozunun durumu ayrı gösterilir. İlk geçerli TF ölçümü öncesinde robot modeli çizilmez.

Seçili sahne, koordinat ve reducer modülleri kaynak commit'ten bir kez içe alınır. Renk/kadraj ve C5 kabuğu, yerel entegrasyon farklarıdır. Köprü aynı kaynak dosyalarından derlenir. İçe aktarılan modüller bağımsız Visualizer layout'una bağlı olmadığı için sonraki ortak paket ayrımına uygundur. Konva'nın aşama geçmişi korunur.

## Akış sınırları

FastAPI köprüye özel DDS ağındaki `scene` adı ve yapılandırılmış port üzerinden ulaşır. Uç yalnız doğrulanmış filo robot ID kümesini, her robotun config namespace'ine ait `/plan` konusunu ve `map` / `tf` kimliğini geçirir. Visualizer mesajlarının stream, epoch, simülasyon damgası ve TTL doğrulaması istemcideki Aşama 4 indirgeyicilerinde sürer. Clock epoch değişiminde önceki poz, iz ve plan temizlenir. Köprü yeniden bağlandığında son poz STALE kalabilir. Yeni bir geçerli ölçüm gelince robot LIVE olur.

Upstream bağlantı başına 64 KiB WebSocket mesaj sınırı, 1 frame alım su seviyesi ve uygulamada bekleyen en fazla bir olay vardır. 250 ms'den uzun süre relay'de kalan poz atılır. Relay beklemesi plan TTL'sinden düşülür. İstemci gönderimi bir saniye içinde tamamlanamazsa bağlantı 1013 ile kapatılır. Ürün için yalnız son snapshot tutulur. Ürün sessizliği, tek başına açık TF akışını kapatmaz. Köprü sessizliği 2,5 sn sonra kendi yeniden bağlantısını tetikler. Köprü Aşama 4'ten gelen dört eşzamanlı istemci sınırına sahiptir. C5 ürün akışı kendi mevcut istemci sınırını kullanır.

Kamera serbest, takip, üstten, filo kadrajı ve sıfırlama modlarını sunar. WebGL sahnesi genel görünümde tembel yüklenir. Düşük kalite seçeneği piksel oranını 1'e indirir ve temas gölgelerini kapatır. Geometri instancing, rota arabelleği, renderer temizliği ve talep üzerine çizim Visualizer’dan alınmıştır.

## Aşama 1.7B hazır depo

Sunum sahnesi yerel CC0 GLB dekorunu asenkron yükler. Model hazır olunca şematik rafların yerini alır. İstasyonlar ile öncelikli görevin alım ve teslim noktaları doğrulanmış C5 snapshot’ından map koordinatlarında çizilir. Model seçimi, kaynak ve ölçüm kanıtı [Aşama 1.7B doğrulama raporunda](../validation/c5/c5-stage1-7b-validation-2026-11-07.md).
