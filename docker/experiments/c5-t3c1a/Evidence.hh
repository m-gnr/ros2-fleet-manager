#pragma once
#include <gz/sim/components/Component.hh>
#include <gz/sim/components/Factory.hh>
namespace c5_split {
using PhysicsSteps=gz::sim::components::Component<uint64_t,class PhysicsStepsTag>;
IGN_GAZEBO_REGISTER_COMPONENT("c5_split_physics_completed_updates",PhysicsSteps)
}
