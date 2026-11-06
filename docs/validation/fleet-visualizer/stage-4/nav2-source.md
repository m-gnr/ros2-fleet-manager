# Nav2 Path kaynak incelemesi

6 Kasım 2026. **Durum B — GÖZLEMLENEN NAV2 PLANI.** İki robotun Planner Server yayını, robot namespace'i ve `map` geometrisi doğrulandı. Path ile etkin `NavigateToPose` goal UUID'si veya Fleet Manager görevi arasında güvenilir bire bir bağ bulunamadı. [Tasarım ve TTL](../../../design/fleet-visualizer-stage-4.md) · [Komut eki](commands.md).

## Canlı grafik

C4.5 Humble/CycloneDDS, Gazebo Fortress, Nav2 1.1.20. Aşağıdaki suffix'ler hem `/robot_1` hem `/robot_2` altında keşfedildi. Her satırda robot başına bir Path yayıncısı ve RELIABLE / VOLATILE / KEEP_LAST (1) QoS görüldü. [Grafik ve endpoint çıktısı](measurements/path-endpoints.txt).

| Topic suffix | Robot namespace'indeki yayıncı | Gözlenen frame ve anlam |
| --- | --- | --- |
| `plan` | `planner_server` | `map`. GridBased/Navfn planner sonucu. Başlık ve her PoseStamped aynı frame ve simülasyon damgasını taşıdı. |
| `received_global_plan` | `controller_server` | `map`. DWB'ye ulaşan global yol. Kontrol çevrimleri aynı damgalı planı tekrar yayınlayabildi. |
| `transformed_global_plan` | `controller_server` | `robot_N/odom`. Yerel costmap bağlamında dönüştürülmüş ve kısaltılmış controller yolu. |
| `local_plan` | `controller_server` | `robot_N/odom`. DWB yerel yörüngesi. |
| `plan_smoothed` | `smoother_server` | Yayıncı keşfedildi. Gözlem pencerelerinde örnek alınmadı. |

Nav2'nin canlı yüklenen robot parametreleri `GridBased` için `nav2_navfn_planner/NavfnPlanner`, `FollowPath` için `dwb_core::DWBLocalPlanner` ve global costmap ile BT Navigator için `map` gösterdi. Yerel costmap robotun kendi `odom` frame'indeydi. Varsayılan `NavigateToPose` ağacında 1 Hz RateController `ComputePathToPose` çağırıyor ve çıkan yol `FollowPath` girdisi oluyor. Planner Server, başarılı ComputePathToPose ve ComputePathThroughPoses sonuçlarını aynı görselleştirme topic'ine yayınlıyor. [Humble davranış ağacı](https://github.com/ros-navigation/navigation2/blob/humble/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml) · [Planner Server uygulaması](https://github.com/ros-navigation/navigation2/blob/humble/nav2_planner/src/planner_server.cpp#L339-L514).

## Hedef ve güncellik

İlk keşif koşusunda `robot_1` için Planner Server sonucu 35,650 sn damgasıyla geldi. BT Navigator ilk EXECUTING durumunu gözlemcinin monotonik zamanında yaklaşık 57 ms sonra bildirdi. Aynı hedef civarında 35,720 sn'lik ikinci plan Controller Server'a ulaştı. 36,645 sn'lik yeni global planın başlangıcı robot hareketiyle değişti. Bu sıra ön planlama, yürütmeye alınan global plan ve yeniden planlamanın gözlemci açısından ayrı olaylar olduğunu gösterir. `robot_2` daha sonra kendi namespace'inde 63,250 sn damgasıyla ilk planner sonucunu verdi. Her robotun `Path` ve action durum örnekleri ayrı kaydedildi. [Son koşudan Path ve durum örnekleri](measurements/nav2-source-samples.json).

`<namespace>/navigate_to_pose/_action/status`, aynı namespace'in `bt_navigator` düğümünden RELIABLE / TRANSIENT_LOCAL / KEEP_LAST (1) QoS ile yayınlandı. C4.5 mevcut senaryosu yeni navigasyon, terminal başarı ve HIGH sırasında Nav2 iptali üretti. Action durum akışı UUID ve durum taşıyor. Planner Path başlığında UUID, assignment epoch veya istemci amacı alanı bulunmuyor. Fleet Manager'ın mesafe sorgularının da gerçek planner sonucu ürettiği gözlendi. Ardışık topic'lerin zaman yakınlığı bağ kurmak için yeterli sayılmadı. `received_global_plan` controller bağlamını daraltıyor ancak robot göreviyle bire bir ilişki taşımıyor ve aynı damgayı tekrar edebiliyor. Bu yüzden doğrudan planner çıktısı, kısa TTL ile ve gözlem etiketiyle seçildi.

Normal bitiş ve iptal, durum akışındaki geçişi izleyen çizim temizliği ile ele alındı. Geçişten sonra gelen bağımsız, geçerli bir Path yeni gözlem olarak çizilebilir. İzleyici ERROR, preemption nedeni veya görevin güvenli duruşu hakkında karar üretmez. İptal ve HIGH güvenliği, mevcut C4.5 koşusunun ayrı kanıtıdır. Saat geri sarımı deterministik testte, kaynak çoğalması ve kaybı Humble DDS testinde denetlendi. [Doğrulama raporu](report.md).
