# C5-B6B.2 — Trafik protokolü hedefli doğrulama

15 Kasım 2026 · `main`, worktree `/Users/murat/develop/ros2-fleet-manager-c5-a-demo-integration`, başlangıç HEAD `76f7badc0fa154b0d9ce007c0f84dbdb06b75569`. İlk verilen dizin `main-legacy` idi; istenen `main` ve B6B.1 tabanı mevcut worktree'de bulundu. Dal değiştirme veya kullanıcı değişikliklerini taşıma yapılmadı.

**DOĞRULANDI:** 46 geçti, 0 kaldı, 0 skip, 2,81 s. Container'da yalnız fleet_interfaces IDL derlemesi ve fake ROS action/service + domain/adapter testleri çalıştı. Gerçek DDS robot roundtrip'i, Gazebo, FollowPath yürütmesi, fiziksel interlock/release ve hareket güvenliği **HENÜZ TEST EDİLMEDİ**. [Sözleşme ve uygulama sınırı](../../design/c5-b6b2-traffic-permit-protocol.md), [komut eki](c5-b6b2-traffic-protocol-commands-2026-11-15.md).

## Kapsam ve kanıt

| Hedef | Kanıt |
|---|---|
| Geçerli istek → COMMIT | Gerçek consumer/SQLite; Outbox içerik eşitliği, COMMIT sonrası yanıt, injected write failure ile atomik rollback. |
| Permit yok / applied ACK yok / sahte ACK var | Üçünde de sender çağrısı 0; `movement_authorized=false`. |
| Eski epoch/session/üst UUID | Aktif domain sahibi ve kabul edilmiş RobotStatus oturumu üzerinden ret; session değişince cached grant da reddedilir. |
| Digest/revision/geometri | Yanlış hash veya revision ret; aynı ROS path'ten türetilmiş geometry eşitliği; hash sonrası yönelim değişimi ret; planner objesinin sonradan değişimi gönderilen kopyayı değiştirmez. |
| Duplicate/geç yanıt | Aynı kayıt tek karar; farklı yük ret; yeni child'a eski cevap uygulanmaz; timeout'tan sonra cevap gate'i açmaz. |
| Revoke/send | Her iki deterministik sıra ve eşzamanlı iki thread: goal=0, revoke sonrası eski cevap kapalı. |
| Dört hareket | Node'un iki gerçek send yordamı ortak gate'e girer; dört tür fake planner/service ile hazırlanır. Park/şarj FM kimlikleri normal StationDispatch allocator'ından gelir. |
| C5-A varsayılanı | Trafik client'ı olmayan gate mevcut akışa izin verir; üç mevcut fake Nav2 lifecycle testi: başarı, güvenli preemption, abort + ClearRobotError geçti. |
| Timeout/bağlantı kaybı | Servis timeout'u sonrası geç COMMIT rezervasyonu/sahipliği korur; client bağlantı yokluğunda kapanır. RETIRED ACK kaynak bırakmaz. |
| Ürün sınırı | YAML trafik enable alanını reddeder; test profili hareket açma alanını reddeder; `motion_envelope: null` kontrol edildi. |

## Bu görevde değişen dosyalar

- `backend/fleet_manager/event_loop.py`, `adapters/ros2_adapter_node.py`; yeni `adapters/traffic_protocol.py`, `persistence/traffic_protocol.py`.
- `interfaces/fleet_interfaces/{CMakeLists.txt,package.xml}`; yeni `msg/TrafficPermitIdentity.msg`, `msg/TrafficPermitDecision.msg`, `msg/TrafficPermitAck.msg`, `srv/RequestTrafficPermit.srv`.
- `ros2_ws/src/fleet_robot_executor/fleet_robot_executor/node.py`; yeni `traffic.py`.
- Yeni `tests/test_traffic_protocol.py`, `tests/test_traffic_protocol_ros2.py`, `docker/experiments/c5-b6b2/run_protocol_tests.sh`.
- Yeni teknik tasarım, bu rapor/komut eki, `docs/diagrams/src/traffic-permit-protocol.mmd` ve türetilmiş SVG; docs ana/tasarım/doğrulama/diyagram dizinlerine ek bağlantılar.

B6B.1'in önceden mevcut dirty/untracked trafik çekirdeği, şeması, store değişiklikleri ve testleri korundu. Event loop'a yalnız B6B.2 test seam ve protokol dispatch eklendi. Önceden mevcut raporlar/deneyler, kişisel notlar, GUI, ürün YAML, batarya/watchdog ve diğer worktree değişiklikleri düzenlenmedi. Geniş regresyon, commit ve push yapılmadı.
