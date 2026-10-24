# C2.1 Robot Executor Durum Makinesi ve Arayüzler Doğrulama Raporu

**Tarih:** 24 Ekim 2026  
**Aşama:** C2.1 — Robot Executor Saf Python Durum Makinesi ve IDL Sözleşmeleri  
**Durum:** **DOĞRULANDI** (Saf Python Birim Testleri ve Arayüz Tanımları Kapsamı)  
**Referans Dokümanlar:** [AGENTS.md](../../../AGENTS.md), [project-context.md](../../project-context.md), [DOC-ARCH-2026-10-23-FINAL](../../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md), [C2 Karar Kaydı](../../c2-executor-decisions-2026-10-24.md)

---

## 1. Amaç ve Kapsam

Bu doğrulama, ROS 2 Fleet Manager projesinin C2 geliştirme aşamasının ilk adımı olan **C2.1** kapsamında üretilen arayüz sözleşmelerini (`interfaces/fleet_interfaces/`) ve ROS 2 middleware bağımlılığı bulunmayan saf Python durum makinesini (`ros2_ws/src/fleet_robot_executor/`) belgeler.

Aşama C2.1'in kabul ölçütleri:
1. `interfaces/fleet_interfaces/` altında `ExecuteTask.action`, `RobotStatus.msg` ve `ClearRobotError.srv` IDL sözleşmelerinin onaylı faz (`current_phase`) ve öncelik (`priority`) sabitleriyle eksiksiz oluşturulması.
2. `ros2_ws/src/fleet_robot_executor/` altında ROS 2'den bağımsız, macOS veya host üzerinde doğrudan test edilebilir saf Python durum makinesi geliştirilmesi.
3. Görev kabulü, faz geçişleri, yük durumu takibi, monotonic `assignment_epoch` ve `goal_uuid` eşleştirmesi, iptal uygunluğu ve terminal hata durumlarının modellenmesi.
4. `ClearRobotError` servis çağrısında `assignment_epoch` değerinin kendiliğinden **artırılmaması** (C2-DEC Seçenek A — Fleet Manager atama otoritesinin korunması).
5. Güvenli iptal/preemption için hem Nav2 terminal iptal sonucu (`STATUS_CANCELED`) hem de güncel odometriyle sıfır hız duruş teyidinin (`|v| <= v_threshold`, `|w| <= w_threshold`) birlikte zorunlu kılınması; duruş teyidi zaman aşımına uğrarsa `STATE_ERROR` fail-safe durumuna geçilmesi.
6. Kapsamlı `pytest` birim testlerinin sıfır hatayla geçmesi.

---

## 2. Test Ortamı

- **İşletim Sistemi:** macOS (Darwin 24.x, arm64)
- **Python Sürümü:** Python 3.14.5 (uv izole sanal ortamı)
- **Paket Bağımlılıkları:**
  - `pytest==8.2.0`
  - Saf Python standart kütüphanesi (`dataclasses`, `enum`, `typing`)

---

## 3. Doğrulanan Alanlar ve Test Matrisi

`tests/test_executor_state_machine.py` altındaki testler şu fonksiyonel kategorileri doğrular:

| Kategori | Test Sayısı | Doğrulanan Davranış ve Kriterler | Sonuç |
|---|---|---|---|
| **StopDetector & Duruş Teyidi** | 5 | Güncel odometriyle sıfır hız teyidi; bayat odometri (`age > freshness`), geleceğe ait zaman damgası, lineer hız aşımı ve açısal hız aşımında duruşun kesin reddi | GEÇTİ |
| **Durum Makinesi İlklendirme** | 2 | Başlangıçta `STATE_IDLE`, `PHASE_NONE`, `is_loaded = False`, `current_epoch = 0`; 5 Hz `RobotStatus` snapshot ve `ExecuteTask` feedback yapılarının IDL ile birebir uyumu | GEÇTİ |
| **Görev Kabulü ve Ön Koşullar** | 10 | IDLE ve `RETURNING_TO_PARK` durumlarında kabul; `EXECUTING_TASK`, `CHARGING`, `RETURNING_TO_CHARGE`, `ERROR` durumlarında ret; yüklüyken (`is_loaded = True`) ret; bayat epoch (`assignment_epoch < current_epoch`) ret; geçersiz öncelik ve boş UUID ret | GEÇTİ |
| **Uçtan Uca Başarılı Görev Yaşam Döngüsü** | 1 | `accept_goal` $\rightarrow$ `PHASE_MOVING_TO_PICKUP` $\rightarrow$ `start_loading` $\rightarrow$ `PHASE_LOADING` $\rightarrow$ `finish_loading` (`is_loaded = True`) $\rightarrow$ `PHASE_MOVING_TO_DROPOFF` $\rightarrow$ `start_unloading` $\rightarrow$ `PHASE_UNLOADING` $\rightarrow$ `finish_unloading` (`is_loaded = False`, `STATE_IDLE`, `STATUS_SUCCEEDED`) | GEÇTİ |
| **Faz Kilitleri ve UUID Eşleştirme** | 2 | Aktif hedef UUID'siyle eşleşmeyen çağrıların (stale result) reddi; fazların sırasız atlanmasının (out-of-order) engellenmesi | GEÇTİ |
| **İptal ve Preemption Uygunluğu** | 4 | `PRIORITY_HIGH` görevlerin kesilemezliği; MEDIUM ve LOW görevlerin yalnızca pickup öncesinde kesilebilmesi; `PHASE_LOADING` başladığı anda iptalin kilitlenmesi; yüklü görevlerin kesilememesi | GEÇTİ |
| **Çok Kriterli Güvenli İptal** | 4 | Nav2 iptali gelse bile odometri sıfır hızı teyit edene kadar robotun PREEMPTED yapılmaması; Nav2 hatasında fail-safe `STATE_ERROR`; iptal duruş zaman aşımında (`cancel_stop_timeout_sec`) fail-safe `STATE_ERROR` | GEÇTİ |
| **Terminal Görev Hataları** | 2 | Nav2 abort veya donanım hatasında `STATE_ERROR` ve `STATUS_FAILED`; eşleşmeyen UUID hata raporlarının yoksayılması | GEÇTİ |
| **ClearRobotError ve Epoch Koruma** | 6 | `STATE_ERROR` dışındayken ret; `robot_id` uyuşmazlığında ret; `expected_epoch != current_epoch` durumunda ret; robot yüklüyken (`is_loaded = True`) operatör servisinin reddi; odometri hareket halindeyse ret; başarılı temizlemede **assignment_epoch değerinin artırılmaması (Option A)** | GEÇTİ |
| **Yardımcı Durumlar (Şarj ve Park)** | 3 | IDLE $\rightarrow$ RETURNING_TO_CHARGE $\rightarrow$ CHARGING $\rightarrow$ IDLE; IDLE $\rightarrow$ RETURNING_TO_PARK $\rightarrow$ IDLE; görev çalışırken veya yüklüyken şarj/park geçişlerinin engellenmesi | GEÇTİ |
| **Paket Düzeyi Doğrulama** | 10 | `ros2_ws/src/fleet_robot_executor/test/test_state_machine.py` altında bağımsız ament/colcon uyumlu paket testleri | GEÇTİ |

---

## 4. Test Komutları ve Alınan Çıktılar

### 4.1 C2.1 Robot Executor Birim Testleri

```sh
PYTHONPATH="ros2_ws/src/fleet_robot_executor:." uv run --with-requirements requirements-c1.txt pytest tests/test_executor_state_machine.py ros2_ws/src/fleet_robot_executor/test/test_state_machine.py -v
```

Çıktı:
```text
============================= test session starts ==============================
platform darwin -- Python 3.14.5, pytest-8.2.0, pluggy-1.7.0
rootdir: /Users/murat/develop/ros2-fleet-manager
collected 49 items

tests/test_executor_state_machine.py::TestStopDetector::test_stopped_with_fresh_odometry PASSED [  2%]
...
tests/test_executor_state_machine.py::TestClearRobotError::test_successful_clear_error_preserves_assignment_epoch PASSED [ 73%]
...
ros2_ws/src/fleet_robot_executor/test/test_state_machine.py::TestStateMachineCore::test_clear_robot_error_preserves_epoch PASSED [100%]

============================== 49 passed in 0.07s ==============================
```

### 4.2 C1 + C2 Tam Regresyon Test Koşusu

```sh
PYTHONPATH="ros2_ws/src/fleet_robot_executor:." uv run --with-requirements requirements-c1.txt pytest tests/ -v
```

Çıktı:
```text
============================= 113 passed in 1.72s ==============================
```
(74 C1 konfigürasyon/şema testi + 39 C2 executor durum makinesi testi sıfır hata ile tamamlanmıştır).

---

## 5. Doğrulama Sınırları ve Kapsam Ayrımı

1. **Saf Python vs Canlı ROS 2 Node:** Bu doğrulama yalnızca durum makinesinin mantıksal geçişlerini, kilitlerini ve veri modellerini belgeler. Canlı ROS 2 `ExecuteTask` action sunucusu, `NavigateToPose` action istemcisi ve Gazebo simülasyonu entegrasyonu Aşama C2.2 kapsamındadır (bu bileşenler **HENÜZ TEST EDİLMEDİ** durumundadır).
2. **Duruş Teyit Parametreleri:** Durum makinesinde kullanılan eşikler (`linear_stop_threshold: 0.01 m/s`, `angular_stop_threshold: 0.01 rad/s`, `odometry_freshness: 1.0 s`, `cancel_stop_timeout: 3.0 s`) yapılandırılabilir parametrelerdir ve kalibrasyonsuz taslak önerilerdir.
3. **Epoch Monotonikliği:** Executor durum makinesi `assignment_epoch` üzerinde kendi kendine artırma yapmaz; hata temizleme sonrası epoch değerini aynen koruyarak Fleet Manager'ın monotoniğine tabi kalır.
