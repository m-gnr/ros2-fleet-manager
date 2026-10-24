# C3.1 Fleet Manager Çekirdeği ve Zamanlayıcı Doğrulama Raporu

**Tarih:** 24 Ekim 2026  
**Aşama:** C3.1 — Saf Python Fleet Manager Çekirdeği, Görev Kuyruğu, Wh Enerji Modeli ve Zamanlayıcı  
**Durum:** **DOĞRULANDI** (Saf Python Birim ve Senaryo Testleri Kapsamı)  
**Referans Dokümanlar:** [AGENTS.md](../../../AGENTS.md), [project-context.md](../../project-context.md), [DOC-ARCH-2026-10-23-FINAL](../../ROS2_Fleet_Manager_Nihai_Mimari_Kararlar_2026-10-23.md), [C3 Karar Kaydı](../../c3-fleet-manager-decisions-2026-10-24.md), [Revize Karar 08](../../ROS2_Fleet_Manager_Karar_08_Revize_v1_0.pdf)

---

## 1. Amaç ve Kapsam

Bu doğrulama, ROS 2 Fleet Manager projesinin C3 aşamasının ilk adımı olan **C3.1** kapsamında geliştirilen ROS 2 middleware ve UI bağımlılığı bulunmayan saf Python çekirdek domain modüllerini (`backend/fleet_manager/domain/`) ve birim/senaryo testlerini belgeler.

Aşama C3.1'in kabul ölçütleri:
1. `backend/fleet_manager/domain/` altında ROS 2'den tamamen bağımsız domain modellerinin (`Task`, `RobotRecord`, `StationRecord`, `Assignment`, `PreemptionDecision`) oluşturulması.
2. HIGH $\rightarrow$ MEDIUM $\rightarrow$ LOW öncelik kuyruğunun ve atanabilir görevler arasında iş korumalı (work-conserving) FIFO algoritmasının uygulanması; MVP kapsamında aging uygulanmaması (C3-DEC-04).
3. Dinamik Wh enerji modeli formülasyonunun ($E_{\text{required}} \le E_{\text{available}}$) eksiksiz kodlanması; Nav2 rota hatasında Öklid (Euclidean) fallback yapılmaması ve enerji kontrolünün doğrudan başarısız sayılması (C3-DEC §2.1).
4. En yakın uygun robot seçiminde Nav2 mesafe eşitliğinde ($|\Delta d| \le 10^{-4}\text{ m}$) en uzun süredir `STATE_IDLE` olan robotun, eşitlik sürerse alfabetik `robot_id` değerinin seçilmesi (C3-DEC-03).
5. Güvenli preemption kurallarının uygulanması: yalnızca yeni HIGH görevin kesebilmesi, boş (IDLE) robot varken kesme yapılmaması, pickup öncesi (`PHASE_MOVING_TO_PICKUP`) ve yüksüz (`is_loaded == False`) olma şartı, çalışan HIGH görevin kesilememesi ve $N=2$ kesilme sınırına ulaşan görevlerin korunması (DOC-ARCH Bölüm 6.2).
6. Kesilen görevin orijinal `created_at` zaman damgasıyla kuyruğa dönerek FIFO önceliğini koruması (Karar 08 Politika P05 / T09).
7. İstasyon ve park rezervasyonlarında tek sahiplik (single ownership), fiziksel ayrılma teyit edilene kadar (`dist > tolerance + margin`) kaynağın `FREE` ilan edilmemesi ve robot `STATE_ERROR` durumundayken kaynağın `BLOCKED` kilitlenmesi (C3-DEC §2.2).
8. `RobotStatus` telemetrisi 2.0 saniye kesilen robotların yeni atamalardan derhal dışlanması (C3-DEC-01); aktif görevde iletişim kaybında 5.0 saniyede uyarı üretilmesi, ancak 10.0 saniyede otomatik `FAILED`/`ERROR` yapılmaması (C3-DEC-02).
9. Monotonic `assignment_epoch`, `goal_uuid` ve `task_id` eşleştirmesiyle bayat (stale) ve mükerrer sonuçların filtrelenmesi.
10. Karar 08 T01–T09 senaryolarını da içeren kapsamlı test paketinin sıfır hatayla geçmesi.

---

## 2. Test Ortamı

- **İşletim Sistemi:** macOS (Darwin 24.x, arm64)
- **Python Sürümü:** Python 3.14.5 (uv izole sanal ortamı)
- **Paket Bağımlılıkları:**
  - `pytest==8.2.0`
  - Saf Python standart kütüphanesi (`dataclasses`, `enum`, `typing`, `math`, `uuid`)

---

## 3. Doğrulanan Alanlar ve Test Matrisi

`tests/test_fleet_manager_domain.py` altındaki testler şu fonksiyonel kategorileri doğrular:

| Kategori | Test Sayısı | Doğrulanan Davranış ve Kriterler | Sonuç |
|---|---|---|---|
| **Wh Enerji Modeli & Formüller** | 5 | Kalan enerji ($E_{\text{remaining}}$), acil durum rezervi ($E_{\text{emergency}}$), kullanılabilir enerji ($E_{\text{available}}$), kaçış enerjisi ($E_{\text{escape}}$), görev gereksinimi ($E_{\text{required}}$); enerji yetersizliğinde ret; Nav2 rota hatasında Öklid fallback yasağı | GEÇTİ |
| **Görev Kuyruğu (TaskQueue)** | 2 | Aynı öncelik sınıfında `created_at` FIFO sıralaması; HIGH $\rightarrow$ MEDIUM $\rightarrow$ LOW öncelik ayrımı ve deterministik tarama | GEÇTİ |
| **Karar 08 Kabul Testleri (T01–T09)** | 9 | **T01:** Aynı sınıfta FIFO atama; **T02:** Üç öncelikte HIGH $\rightarrow$ MED $\rightarrow$ LOW; **T03:** LOW görevin LOW/MED tarafından kesilemezliği; **T04:** En yakın IDLE robot seçimi; **T05:** IDLE robot varken kesme yasağı; **T06:** İki adaydan kısa pickup mesafelinin kesilmesi; **T07:** Çalışan HIGH görevin kesilemezliği; **T08:** Yükleme başlangıcında veya yüklüyken kesme yasağı; **T09:** Kesilen görevin eski `created_at` ile kuyruğa dönüşü | GEÇTİ |
| **N=2 Preemption Koruma Sayacı** | 1 | Görev $N=2$ kez kesildikten sonra 3. çalışmasında preemption korumasına girmesi ve kesilememesi | GEÇTİ |
| **Telemetri Freshness ve İletişim** | 2 | 2.0 saniye telemetrisi kesilen robotun atama dışı kalması ve taze telemetriyle geri dönmesi (C3-DEC-01); 5s uyarı, 10s bildirim ve otomatik FAILED/ERROR yasağı (C3-DEC-02) | GEÇTİ |
| **Mesafe Tie-Breaking (C3-DEC-03)** | 2 | Nav2 pickup mesafesi eşitliğinde en uzun süredir IDLE olan robotun seçilmesi; bekleme süresi de eşitse alfabetik `robot_id` (`robot_1` < `robot_2`) seçimi | GEÇTİ |
| **Rezervasyon ve Fiziksel Ayrılma** | 3 | Tek sahiplik garantisi; robot tolerans yarıçapı içindeyken istasyonun FREE yapılmaması, fiziksel çıkışta FREE olması; robot ERROR durumundayken istasyonun BLOCKED kilitlenmesi | GEÇTİ |
| **Deduplication ve Epoch/UUID** | 1 | Bayat epoch/UUID taşıyan sonuçların süzülmesi ve güncel atamayı bozamaması; eşleşen terminal sonucun görevi tamamlaması | GEÇTİ |

---

## 4. Test Komutları ve Alınan Çıktılar

### 4.1 C3.1 Fleet Manager Domain Birim Testleri

```sh
PYTHONPATH=".:backend:ros2_ws/src/fleet_robot_executor" uv run --with-requirements requirements-c1.txt pytest tests/test_fleet_manager_domain.py -v
```

Çıktı:
```text
============================= test session starts ==============================
platform darwin -- Python 3.14.5, pytest-8.2.0, pluggy-1.7.0
rootdir: /Users/murat/develop/ros2-fleet-manager
collected 25 items

tests/test_fleet_manager_domain.py::TestEnergyModel::test_remaining_and_available_energy PASSED [  4%]
tests/test_fleet_manager_domain.py::TestEnergyModel::test_required_energy_formula PASSED [  8%]
tests/test_fleet_manager_domain.py::TestEnergyModel::test_energy_eligibility_sufficient PASSED [ 12%]
tests/test_fleet_manager_domain.py::TestEnergyModel::test_energy_eligibility_insufficient PASSED [ 16%]
tests/test_fleet_manager_domain.py::TestEnergyModel::test_route_failure_strict_no_euclidean_fallback PASSED [ 20%]
tests/test_fleet_manager_domain.py::TestTaskQueue::test_fifo_ordering_within_same_priority PASSED [ 24%]
tests/test_fleet_manager_domain.py::TestTaskQueue::test_priority_ordering PASSED [ 28%]
tests/test_fleet_manager_domain.py::TestKarar08Scenarios::test_t01_fifo_same_priority PASSED [ 32%]
tests/test_fleet_manager_domain.py::TestKarar08Scenarios::test_t02_strict_priority_ordering PASSED [ 36%]
tests/test_fleet_manager_domain.py::TestKarar08Scenarios::test_t03_no_preemption_by_low_or_medium PASSED [ 40%]
tests/test_fleet_manager_domain.py::TestKarar08Scenarios::test_t04_nearest_idle_robot_selection PASSED [ 44%]
tests/test_fleet_manager_domain.py::TestKarar08Scenarios::test_t05_idle_robot_priority_over_preemption PASSED [ 48%]
tests/test_fleet_manager_domain.py::TestKarar08Scenarios::test_t06_preemption_candidate_shortest_pickup PASSED [ 52%]
tests/test_fleet_manager_domain.py::TestKarar08Scenarios::test_t07_running_high_task_cannot_be_preempted PASSED [ 56%]
tests/test_fleet_manager_domain.py::TestKarar08Scenarios::test_t08_preemption_locked_when_loading_or_loaded PASSED [ 60%]
tests/test_fleet_manager_domain.py::TestKarar08Scenarios::test_t09_preempted_task_preserves_original_created_at PASSED [ 64%]
tests/test_fleet_manager_domain.py::TestN2PreemptionProtection::test_n2_preemption_counter_and_immunity PASSED [ 68%]
tests/test_fleet_manager_domain.py::TestStaleAndCommunicationHealth::test_stale_robot_excluded_and_recovered PASSED [ 72%]
tests/test_fleet_manager_domain.py::TestStaleAndCommunicationHealth::test_communication_loss_no_automatic_failed_or_error PASSED [ 76%]
tests/test_fleet_manager_domain.py::TestTieBreaking::test_equal_distance_longest_idle_preferred PASSED [ 80%]
tests/test_fleet_manager_domain.py::TestTieBreaking::test_equal_distance_and_equal_idle_alphabetical_tie_break PASSED [ 84%]
tests/test_fleet_manager_domain.py::TestReservations::test_single_ownership_enforcement PASSED [ 88%]
tests/test_fleet_manager_domain.py::TestReservations::test_physical_departure_rule PASSED [ 92%]
tests/test_fleet_manager_domain.py::TestReservations::test_blocked_resource_on_error PASSED [ 96%]
tests/test_fleet_manager_domain.py::TestDeduplicationAndMatching::test_stale_result_deduplication PASSED [100%]

============================== 25 passed in 0.05s ==============================
```

### 4.2 C1 + C2 + C3 Tam Regresyon Test Koşusu

```sh
PYTHONPATH=".:backend:ros2_ws/src/fleet_robot_executor" uv run --with-requirements requirements-c1.txt pytest tests/ -v
```

Çıktı:
```text
======================= 145 passed, 10 skipped in 1.94s ========================
```
(74 C1 konfigürasyon/şema testi + 46 C2 executor testi + 25 C3 fleet manager domain testi sıfır hata ile tamamlanmıştır).

---

## 5. Doğrulama Sınırları ve Kapsam Ayrımı

1. **Saf Python vs Canlı ROS 2 Düğümleri:** Bu doğrulama yalnızca Fleet Manager çekirdek domain mantığını, zamanlayıcı algoritmalarını ve veri modellerini belgeler. ROS 2 action/topic istemcileri, SQLite transaction ve Outbox mekanizması, FastAPI REST / WebSocket katmanı ve Battery Simulator düğümü bu aşamanın kapsamı dışındadır.
2. **İletişim Kaybı Kurtarma Protokolü:** C3-DEC-02 uyarınca 10 saniye iletişim kesildiğinde otomatik `FAILED` yapılmamış; askıya alma ve açık operatör kurtarma seçenekleri açık öneri statüsünde tutulmuştur.
3. **Takas (%15 Swap):** İki robotlu dinamik takas mekanizması MVP kapsamında kapalıdır (`extra_swap_enabled = false`) ve testler bu politikaya sadık kalmıştır.
