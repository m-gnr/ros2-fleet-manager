# C1 — Konfigürasyon Altyapısı Belgesi

Bu belge, `config/fleet.yaml` dosyasının şema yapısını, veri tiplerini, fiziksel birimlerini, doğrulama kurallarını ve C1 aşamasında alınan tasarım kararlarını açıklar.

## 1. Amaç ve Kapsam

- **Tek Yapılandırma Kaynağı:** Sistemin tek düzenlenebilir filo tanım kaynağı `config/fleet.yaml` dosyasıdır. Ayrı bir `stations.yaml` veya paralel yapılandırma dosyası kullanılmaz.
- **Config-Driven İlkesi:** Robot sayısı, isimleri, başlangıç pozları, Nav2 adresleri ve istasyon tanımları kod içine gömülmez. Kod değişikliği gerekmeksizin yalnızca YAML dosyası üzerinden 1, 2 veya 3 robot tanımlanabilir.
- **Fail-Fast Doğrulama:** Konfigürasyon, sistem başlatılmadan önce hem JSON Schema (`config/fleet.schema.json`) hem de Pydantic veri sözleşmesi (`fleet_config/models.py`) ile doğrulanır. Hatalı girdilerde sistem açık hata mesajıyla durur; örtük varsayılan değerler üretilmez.

## 2. Yapılandırma Alanları ve Fiziksel Birimler

`config/fleet.yaml` dosyası dört ana bloktan oluşur:

### 2.1 `fleet`
Genel filo ve ortam parametreleri:
- `name` (string): Filo tanıtıcı adı.
- `map_path` (string): Harita YAML dosyasının `fleet.yaml` dizinine göre bağıl yolu (örn. `map/map.yaml`).
- `use_sim_time` (boolean, sabit `true`): Tüm düğümlerin Gazebo `/clock` zamanını kullanmasını zorunlu kılar.
- `battery_models` (sözlük): Robot tiplerine göre batarya parametreleri:
  - `usable_capacity_wh` (float > 0): Kullanılabilir net batarya kapasitesi (**Watt-saat / Wh**).
  - `consumption_wh_per_meter` (float > 0): Hareket tüketim katsayısı $k$ (**Wh/m**).
  - `idle_power_w` (float $\ge$ 0): Bekleme gücü (**Watt / W**).
  - `charge_power_w` (float > 0): İstasyon şarj gücü (**Watt / W**).

> [!NOTE]
> Batarya katsayıları (100 Wh, 0.20 Wh/m, 2 W, 20 W) C1 aşaması için PDF'deki örnek değerlerdir; kalibrasyon C4 aşamasına bırakılmıştır.

### 2.2 `robots`
Filodaki robotların listesi (en az 1 robot):
- `id` (string, regex `^[A-Za-z_][A-Za-z0-9_]*$`): Benzersiz robot tanıtıcısı (örn. `robot_1`).
- `name` (string): Robot adı.
- `namespace` (string, ROS 2 namespace formatında, örn. `/robot_1`): Robotun düğüm ve topic isim alanı.
- `initial_pose`:
  - `x` (float): Harita koordinat sisteminde X konumu (**metre**).
  - `y` (float): Harita koordinat sisteminde Y konumu (**metre**).
  - `yaw` (float): Harita koordinat sisteminde yönelim açısı (**radyan**).
- `battery_model` (string): `fleet.battery_models` altında tanımlı bir batarya modeline referans.
- `nav2_action_name` (string): Robotun Nav2 NavigateToPose action adresi (örn. `/robot_1/navigate_to_pose`). Robotun kendi namespace'i altında bulunmalıdır.
- `nav2_params_path` (string): Nav2 parametre şablonunun bağıl yolu (örn. `simulation-b3-params.template.yaml`).

### 2.3 `stations`
Fiziksel tesis kaynakları:
- `charging_stations` (liste, en az 1 istasyon):
  - `id` (string): Benzersiz istasyon tanıtıcısı.
  - `pose` (`x`, `y`, `yaw`): İstasyon koordinatları (m, radyan).
  - `tolerance_radius` (float > 0): Şarj temas alanı yarıçapı (**metre**).
- `parking_stations` (liste): Bekleme ve park noktaları.
- `safe_waiting_areas` (liste): Güvenli bekleme alanları.

Tüm istasyonlar ve park alanları arasında `id` ve `(x, y)` fiziksel konum çakışması engellenir.

### 2.4 `policies`
Görev yönetimi ve operasyon politikaları:
- `assignment` (sabit `"priority_fifo_nearest_eligible"`): Öncelik ve FIFO tabanlı en yakın uygun robot ataması.
- `preemption_priority` (sabit `"HIGH"`): Yalnızca HIGH görevler güvenli kesme yapabilir.
- `max_preemptions` (sabit `2`): Bir görevin en fazla kesilme sayısı ($N=2$ koruması).
- `extra_swap_enabled` (sabit `false`): İki robotlu takas MVP'de kapalıdır.
- `automatic_retry` (sabit `false`): Nav2 hatalarında otomatik yeniden deneme yapılmaz.
- `automatic_reassignment` (sabit `false`): Hatalı görev başka robota otomatik yeniden atanmaz.
- `charge_target_soc_percent` (sabit `80`): Normal şarj hedef eşiği (**%**).
- `charge_queue` (sabit `"lowest_soc_fifo"`): Düşük SoC öncelikli, eşitlikte FIFO şarj kuyruğu.
- `emergency_soc_percent` (float, %): Kritik acil rezerv eşiği (örn. `8.0`).
- `low_soc_percent` (float, %): Şarj kuyruğuna yönlendirme eşiği (örn. `25.0`). Eşik kuralı: `emergency_soc_percent < low_soc_percent < charge_target_soc_percent`.
- `safety_margin_wh` (float $\ge$ 0): Enerji hesaplama güvenlik payı (**Wh**, örn. `10.0`).

## 3. Doğrulama Seviyeleri ve Kuralları

1. **Sentaks ve Biçim Doğrulaması:** YAML ayrıştırmasında anahtar tekrarları (`duplicate keys`) ve string dışı anahtarlar engellenir.
2. **Şema Doğrulaması (`fleet.schema.json`):** Draft 2020-12 uyumlu JSON Schema ile tipler, aralıklar, regex desenleri ve zorunlu alanlar denetlenir. Şemada örtük varsayılanlar (`default`) bulunmaz; tüm operasyonel parametreler açıkça tanımlanmalıdır.
3. **Pydantic Semantik Doğrulaması (`fleet_config/models.py`):**
   - Robot ID, isim, namespace, action ve başlangıç pozlarının benzersizliği.
   - İsim alanlarının iç içe geçmemesi (nested namespace collision koruması).
   - Robot batarya modelinin `fleet.battery_models` içinde varlığı.
   - Güvenlik marjının ($E_{margin}$) kullanılabilir net enerjiyi tüketmemesi ($E_{margin} < C_{usable} \cdot (1 - SoC_{emergency}/100)$).
   - İstasyon kaynak ID ve fiziksel koordinat çakışmalarının önlenmesi.
4. **Dosya ve Varlık Referansı Doğrulaması (`fleet_config/loader.py`):**
   - `map_path` dosyasının mevcudiyeti ve harita YAML içindeki `image` dosyasının (`map.pgm`) fiziksel varlığı.
   - Robot `nav2_params_path` şablonunun mevcudiyeti, yer tutucu sentaksı ve `use_sim_time: true` parametre bloğunun varlığı.

## 4. Açık Mimari Kararlar ve Notlar

> [!NOTE]
> **İstasyon Yapılandırma Yerleşimi:** Nihai Mimari PDF'nin Bölüm 3 tablosunda istasyonlar için `fleet.stations` ifadesi geçerken, Bölüm 10 örnek YAML'ında `stations` kök düzeyde gösterilmektedir. C1 uygulamasında modülerliği ve okunabilirliği korumak adına Bölüm 10'daki kök düzey `stations` yapısı uygulanmıştır. İlerleyen aşamalarda değişiklik talep edilirse şema ve Pydantic modeli bu karara göre güncellenecektir.
