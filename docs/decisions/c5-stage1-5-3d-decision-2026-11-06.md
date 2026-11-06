# C5 / Aşama 1.5 — Ana depo görünümü kararı

**6 Kasım 2026 · ONAYLANDI**

C5 Aşama 1'in ana depo görünümü, kullanıcı onayıyla Konva 2D haritasından açık renkli Three.js ve React Three Fiber sahnesine geçer. C5'in mevcut operasyon kartları, salt okunur REST/WS sözleşmesi ve yetkili Fleet Manager verileri kullanılır. Aşama 2 görev veya kontrol işlemleri kapsam dışıdır.

Mevcut Konva görünümü okunabilir bir 2D özet sunuyordu. Bağımsız Visualizer Aşama 4 ise gerçek TF pozu, kamera, iz ve gözlemlenen planı zaten sağlıyordu. Seçilen yol, doğrulanmış Visualizer sahnesinin sunum parçalarını C5 kabuğunda yeniden kullanır. Açık palet, çapraz kamera ve temsili depo, fiziksel kaynaklardan gelen robot konumlarını görsel olarak korur.

FastAPI, salt okunur Visualizer köprüsüne bağlanır ve iki kaynağı tek C5 WebSocket girişinde ayrı mesajlar olarak taşır. Fleet Manager görev, batarya ve istasyon verilerinin yetkili kaynağıdır. TF/Path görselleştirme akışı ikinci bir karar veya güvenlik kaynağı oluşturmaz. Nav2 Path yalnız **GÖZLEMLENEN NAV2 PLANI (Durum B)** olarak sunulur. Aktif goal ilişkisi doğrulanmamıştır.

[Entegrasyon tasarımı](../design/c5-3d-operations.md) veri sahipliği, alternatifler ve çalışma zamanı sözleşmesini tanımlar. Doğrulama kanıtları ayrı tutulur.
