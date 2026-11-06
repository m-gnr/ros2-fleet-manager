# C5 / Aşama 1 — REST ve WebSocket sözleşmesi

## Salt okunur kaynaklar

| Uç | İçerik |
|---|---|
| `GET /api/health` | Web sürecinin oturum kimliği ve snapshot kaynağı için `LIVE` veya `UNAVAILABLE`. |
| `GET /api/fleet` | Robotlar, görevler, istasyonlar, görev sayıları ve harita çerçevesi. WebSocket ile aynı şema. |
| `GET /api/robots` | Robot telemetrisi ve Fleet Manager taşıma sahipliği. |
| `GET /api/robots/{robot_id}` | Seçili robot veya 404. |
| `GET /api/tasks` | Aktif atamalar, kuyruk, preemption bekleyen görevler ve terminal kayıtlar. |
| `GET /api/stations` | İstasyon tipi, config pozu, rezervasyon, iki sahiplik alanı ve doğrulanmış şarj. |
| `WS /ws/fleet` | Sunucudan istemciye tam snapshot. |

Sağlık ucu web süreci çalışıyorsa 200 döner. Veri uçları kullanılabilir snapshot yoksa 503 döner. Yanıtlar `Cache-Control: no-store` taşır. Görev listesi toplam sayıları ve en fazla 100 satırı taşır. Aktif ve kuyruktaki kayıtlar terminal kayıtlardan önce gelir. UI gösterilen ve toplam satır sayısını ayırır. Terminal durum görev alanından gelir. Güncelleme/terminal zamanı, ilerleme yüzdesi ve ETA için ürün alanı bulunmuyor.

## Zaman, sıra ve tazelik

- `schema_version=1`. `backend_session_id` her FastAPI başlatmada, `source_session_id` her yayıncı başlatmada değişir.
- `sequence` yayıncı oturumu içinde artar. Her mesaj tek başına uygulanabilen tam görüntüdür. İstemci sıra boşluklarına izin verir ve eski sıraları yok sayar. Aynı oturumda ilk mesaj daha önce görüntülenmiş sırayı teyit edebilir. Oturum değişimi bağlantı ortasında görülürse yeniden eşitlenir. Yeni bağlantının ilk geçerli tam görüntüsü yeni oturumu kurar.
- `generated_at_utc` yayıncıdaki UTC duvar saati. Robot `*_sim_ns` alanları ROS simülasyon saatindeki nanosaniyeyi ondalık dizge olarak verir. `status_age_sec` backend monotonik alım saatinden türetilen geçen süredir. `created_at_source_seconds` görev kaynağının sağladığı ham saniyedir. Kaynak sözleşmesi saat türü taşımadığından takvim saatine dönüştürülmez.
- Robot telemetrisi ve poz için `LIVE`, `STALE`, `NO_DATA`, `BLOCKED`, `UNAVAILABLE` veri güvenilirliği durumlarıdır. `BLOCKED` kaynak oturumu kilididir. Ürün `ERROR` ve rezervasyon `BLOCKED` durumları ayrı alanlardadır.
- Geçersiz batarya SoC ve Wh alanları `null`. Son ölçüm damgası mevcutsa korunabilir. Geçersiz pozda son doğrulanmış poz ve ölçüm damgası saklanır. Kaynağı değişen ya da blokeli robotun pozundan güncel hareket çıkarılmaz.
- Şarj alanı `CHARGING`, `NOT_CHARGING`, `UNAVAILABLE` değerlerini taşır. Şarj dışı istasyonlar `NOT_APPLICABLE` döner. Rezervasyonun `FREE` olması bir görsel konum çıkarımı değildir.
- Tarayıcı taşıma durumları `CONNECTING`, `CONNECTED`, `RECONNECTING`, `DISCONNECTED`. Başarılı WebSocket el sıkışmasından sonra ilk geçerli görüntü geldiğinde bağlantı `CONNECTED` olur. 2,2 sn yeni geçerli görüntü alınmazsa bağlantı yeniden kurulur. Tekrar deneme aralığı 0,4–4 sn.

## Ağ ve kaynak sınırları

API süreci varsayılan olarak `127.0.0.1` dinler. Kabul Compose'u konteyner içi bind'i açıkça seçer ve host portunu yalnız loopback'e yayımlar. Vite da loopback dinler ve tarayıcıyla aynı origin üzerinden API/WS proxy sağlar. Host kontrolü `127.0.0.1` ve `localhost` kabul eder. WebSocket Origin ve CORS, tanımlanan tam loopback origin ile sınırlıdır. Bu kimlik doğrulamasız yerel çalışma düzenidir.

Yayıncı saniyede en çok dört örnek alır. İç dosya 512 KiB ile sınırlıdır. Okuyucu 1,5 sn'den eski görüntüyü düşürür ve eski sıra ya da zaman damgasını yeniden kabul etmez. Sunucu istemci başına bir gönderim ve bir alım bekletir. Sıra yığmak yerine en yeni görüntüyü alır. Gönderim ve kapanış zaman aşımı 1 sn. WebSocket bağlantı sınırı 16, gelen mesaj sınırı 1 KiB ve giriş kuyruğu 1. İstemciden veri mesajı alınırsa bağlantı 1008 ile kapanır. Snapshot kaynağı eskirse veya değişirse kapanış kodu 1013 kullanılır.
