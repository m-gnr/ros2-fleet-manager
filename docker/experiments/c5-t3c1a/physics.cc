// One stock Physics system, forwarded once. This observer writes no actuator command.
#include "Evidence.hh"
#include <gz/sim/System.hh>
#include <gz/plugin/Loader.hh>
#include <gz/plugin/Register.hh>
#include <stdexcept>
class C5PhysicsObserver:public gz::sim::System,public gz::sim::ISystemConfigure,public gz::sim::ISystemUpdate {
  gz::plugin::Loader loader;
  gz::plugin::PluginPtr stock;
  gz::sim::ISystemUpdate *update{};
  gz::sim::Entity world{};
 public:
  void Configure(const gz::sim::Entity & e,const std::shared_ptr<const sdf::Element> & sdf,
    gz::sim::EntityComponentManager & ecm,gz::sim::EventManager & events) override {
    world=e;const auto plugins=loader.LoadLib(sdf->Get<std::string>("stock_library"));
    for(const auto & name:plugins){auto candidate=loader.Instantiate(name);
      if(candidate->QueryInterface<gz::sim::ISystemUpdate>()){stock=candidate;break;}}
    if(!stock)throw std::runtime_error("Exactly one real stock Physics implementation required");
    auto configure=stock->QueryInterface<gz::sim::ISystemConfigure>();update=stock->QueryInterface<gz::sim::ISystemUpdate>();
    if(!configure||!update)throw std::runtime_error("Stock Physics interfaces missing");
    configure->Configure(e,sdf,ecm,events);ecm.CreateComponent(e,c5_split::PhysicsSteps(0));
  }
  void Update(const gz::sim::UpdateInfo & info,gz::sim::EntityComponentManager & ecm) override {
    update->Update(info,ecm);
    if(!info.paused&&info.dt>std::chrono::steady_clock::duration::zero())
      ++ecm.Component<c5_split::PhysicsSteps>(world)->Data();
  }
};
IGNITION_ADD_PLUGIN(C5PhysicsObserver,gz::sim::System,C5PhysicsObserver::ISystemConfigure,C5PhysicsObserver::ISystemUpdate)
IGNITION_ADD_PLUGIN_ALIAS(C5PhysicsObserver,"c5::test::PhysicsObserver")
