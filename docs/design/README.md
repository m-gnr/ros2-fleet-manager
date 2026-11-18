# Teknik tasarımlar

- [C5-T3A canlı permit ve native sıfır doğrulaması](c5-b6b2-traffic-permit-protocol.md#18-kasım-c5-t3a-eki--canlı-permit-ve-native-sıfır-doğrulaması): mevcut B6B.2 tasarımına ek; varsayılan kapalı, ACK fiziksel kanıt değildir.

- [C5 native actuator ve gerçek child/Path bağımlılık aşamaları](../validation/c5/traffic-integration-2026-11-18.md): [izole deney sözleşmesi](../../docker/experiments/c5-b6b7/README.md); hareket yetkisi kapalı.

- [C5 robotlar arası konum ve rota farkındalığı](c5-peer-awareness.md): deneysel Nav2 peer katmanı ve kapalı trafik yetkisi sınırı.

- [C5 Aşama 1 salt okunur operasyon paneli](c5-readonly-dashboard.md) · [API sözleşmesi](c5-readonly-api.md) · [Arayüz ve koordinatlar](c5-dashboard-ui.md)
- [C5 Aşama 1.5 3D entegrasyonu](c5-3d-operations.md)

- [SQLite Outbox ve tek consumer](c3-2-sqlite-outbox.md): C3.2 uygulama sözleşmesi.
- [Konfigürasyon alanları ve doğrulama](../configuration-c1.md): C1 sözleşmesi; mevcut yolu korunur.
- [Fleet Manager v2.2](fleet_manager_mimarisi_ve_algoritmalar_v2_2_fix.pdf), [Battery Simulator v1.2](battery_simulator_node_architecture_v1_2_fix.pdf), [config-driven v1.3](config_driven_multi_robot_ros2_nav2_architecture_tr_v1_3_fix.pdf), [API/panel v1.2](fastapi_websocket_web_panel_mimarisi_v1_2_fix.pdf): tarihsel tasarım kaynakları.

Eski PDF tasarımları yalnız [güncel onaylı kaynaklarla](../architecture/README.md) çelişmeyen ayrıntılar için kullanılır. Dosyalar değiştirilmemiştir; bir tasarımın bulunması uygulandığı anlamına gelmez. Görsel algoritma anlatımı [diyagram kataloğundadır](../diagrams/README.md).

- [C5 Aşama 2.0 dinamik batarya simülasyon kontrolü](c5-battery-simulation-control.md): config envanteri, erişim sınırı, robot bazlı servis ve atomik olmayan toplu uygulama.

- [C5-B6B.2 trafik izin protokolü](c5-b6b2-traffic-permit-protocol.md): COMMIT, gerçek kimlik, ACK ve ortak kapalı Executor gate.

- [C5-B6B.3 yerel hareket kapısı](c5-b6b3-traffic-motion-gate.md): son cmd_vel topolojisi, bypass, offline yerel uygulama ve fiziksel fail-safe eksikleri.

- [C5-B6B.4 tek son ROS hız çıkışı](c5-b6b4-single-velocity-output.md): test-only adapter/topoloji, kaynak damgası sözleşmesi ve açık bypass engelleri.

- [C5-B6B.6 actuator komut yetkilendirmesi](c5-b6b6-actuator-authorization.md): imzalı sıfır zarfı, oturum/sıra/bilet ve açık transport sınırları.
