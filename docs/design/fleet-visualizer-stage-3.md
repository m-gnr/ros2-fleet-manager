# Fleet Visualizer Aşama 3 teknik tasarımı

6 Kasım 2026. Taban `015865403d5bf3cae62647fbc149c5bbcee620a5`, [Aşama 2 doğrulaması](../validation/fleet-visualizer/stage-2/report.md). Prototipin kapsamı [C5 mimari kaydından](../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md#14-c-aşaması-c1c5-geliştirme-yol-haritası) ayrıdır.

## Ön inceleme

- Aşama 2, `--robot` ile tek bir `fleet.yaml` kaydı seçiyordu. `RosReader`, o robotun namespaced TF aboneliğini, `Buffer` nesnesini ve `Telemetry` sıra/tazelik durumunu tek düğümde taşıyordu. Tek `Stream` snapshot'ı ve tarayıcıdaki tek `Telemetry` oturumu da aynı seçimle sınırlıydı.
- Frontend'de `useTelemetry` bağlantı ve yeniden denemeyi yönetiyordu. React paneli ham ölçümü, React Three Fiber sahnesi aynı akıştaki son iki ölçümü kullanıyordu. `Vehicle` hem robot kökünü hem OrbitControls'u yönetiyordu.
- C4.5 enerji profili aynı Fortress dünyasında `/robot_1/tf` ve `/robot_2/tf` dinamik akışlarını sağlar. `tf2_echo`, ayrı topic eşlemeleriyle `map → robot_1/odom → robot_1/base_link` ve `map → robot_2/odom → robot_2/base_link` zincirlerini çözdü. Başlangıçta sırasıyla yaklaşık `(-2, -0,5, 0)` ve `(1, 2,5, π)` ölçüldü. `map` ortaktır, alt frame'ler namespace taşır. `/tf` üzerinde C3.3.3 test yardımcısının birleşik yayını da bulunur. Bu koşuda dinamik zincirler için namespaced akış yeterlidir. [Canlı doğrulama ve komutlar](../validation/fleet-visualizer/stage-3/report.md).
- Birleşik TF ağacında bu iki robotun çocuk frame'leri farklıdır. Namespaced abonelik ve ayrı buffer kullanımı, yanlış topic'teki bir zincirin başka bir robotun durumuna ulaşmasını da önler. Bir düğüm ve bir `/clock` aboneliği yeterlidir. Sensörün statik zinciri ve birleşik root TF, köprünün girdileri arasında yer almaz.

## Köprü

`fleet.yaml` doğrulandıktan sonra her kayıt bir `RobotReader` ve bir `Telemetry` durumuna bağlanır. Her okuyucu kendi `/<namespace>/tf` aboneliğinden beklenen iki parent/child çiftini kabul eder. AMCL'nin ileri damgalı lokalizasyon kenarı, odometri kenarının ölçüm anındaki kesin `map` dönüşümünü çözmek için kullanılır. Hatalı kenar ayrı işaretlenir. Eksik ya da duraklayan bir robot akışı diğer buffer'ı, zamanlayıcıyı ve watermark'ı etkilemez.

20 Hz kararlı zamanlayıcı robotları sırayla örnekler. Aynı `/clock` gözlemi robot başına ayrı Telemetry nesnesine gider. Gözlenen geri sarım her buffer'ı ve watermark'ı temizler, epoch'u artırır ve yeni ölçüm gerektirir. TF mesajı kaynak epoch'u taşımadığı için aynı zaman aralığına düşen ve DDS üzerinde gecikmiş eski bir paketi damgasından tek başına ayırmak mümkün değildir. Sıra, geleceğe kayma toleransı ve güncellik kapıları mevcut TF sözleşmesine dayanır.

ROS thread'i robot başına son snapshot'ı değiştirir ve en fazla bir asyncio uyandırması bekletir. WebSocket istemcileri kendi gönderim görevleri ve robot bazlı cursor'larıyla en güncel durumu okur. Bir gönderim 1 sn içinde tamamlanmazsa ilgili istemcinin akışı kapatılır. Ölçüm arşivi tutulmaz. `/telemetry/fleet` robot listesini ve her robotun V1 akışını iletir. `/telemetry` önceki tek robotlu V1 el sıkışmasını sunar. [Sözleşme](../../fleet-visualizer/README.md#websocket-sözleşmesi).

## Tarayıcı

Tek socket yöneticisi V1 paketini robot kimliğine göre mevcut oturum doğrulayıcısına verir. Kimlik listesi `NO_DATA` kartlarını ilk ölçümden önce açar. Her robot kendi geçerli pozunu, önceki örneğini, frame ve epoch bilgisini, watermark'ını ve son alım zamanını saklar. Bağlantı kaybı ortak transport durumudur. Her robotun son doğrulanmış pozu ayrı tutulur ve yeniden bağlantıda o robotun yeni ölçümü gerekir.

Depo katmanı bir kez çizilir. Her robotun ayrı root grubu `(x, 0, -y)` ve yaw alır. Son iki geçerli örnek arasındaki 45 ms geçiş robot başına hesaplanır. Bir akış beklemeye geçtiğinde yalnız o robotun geçişi bırakılır. Kimlik ve seçim işaretleri kökün konumuna ofset eklemez.

Model tıklaması ve filo listesi aynı seçim durumunu kullanır. Kamera takip hedefi seçili robotun çizilen köküdür. Seçim değişiminde kamera hedefe yumuşak geçer. `Filoyu kadraja al`, görünür köklerin sınırını ve viewport oranını kullanarak tek seferlik bir kadraj kurar. Takipte STALE robotun hedefi son doğrulanan pozda kalır.

## Uygulama ve doğrulama durumu

- **IMPLEMENTED** — çoklu köprü, V1 uyumluluğu, robot bazlı tarayıcı durumu, modeller ve seçim.
- **UNVERIFIED** — üç veya daha fazla robotla canlı yük, başka simülasyon frame sözleşmeleri ve canlı saat geri sarımı. Geri sarım için deterministik ROS ve tarayıcı testleri vardır.
- İki robotlu canlı kanıt, ölçüm koşulları ve yeniden koşulan ürün testleri [Aşama 3 doğrulama raporundadır](../validation/fleet-visualizer/stage-3/report.md).
