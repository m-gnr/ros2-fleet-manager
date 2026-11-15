// No world, physics engine, robot, bridge or nonzero command is created.
#include "DiffDrive.cc"
#include <cassert>
#include <thread>
int main() {
  DiffDrivePrivate d;
  d.enabled = true;
  d.limiterLin = std::make_unique<math::SpeedLimiter>();
  d.limiterAng = std::make_unique<math::SpeedLimiter>();
  EntityComponentManager ecm;
  UpdateInfo info;
  info.dt = std::chrono::milliseconds(5);
  auto checkZero = [&] {
    d.UpdateVelocity(info, ecm);
    assert(d.targetVel.linear().x() == 0 && d.targetVel.angular().z() == 0);
    assert(d.leftJointSpeed == 0 && d.rightJointSpeed == 0);
  };
  checkZero(); assert(d.lease.state == c5_test::State::NO_COMMAND);
  msgs::Twist zero;
  d.OnCmdVel(zero); checkZero();
  assert(d.haveCommand && !d.lease.timed_out);
  auto receipt = d.received;
  std::this_thread::sleep_for(std::chrono::milliseconds(20));
  d.OnCmdVel(zero); checkZero(); assert(d.received > receipt);
  // Wall time advances while simTime remains frozen (pause semantics).
  std::this_thread::sleep_for(std::chrono::milliseconds(270));
  checkZero(); assert(!d.haveCommand && d.lease.timed_out);
  d.OnCmdVel(zero); checkZero();
  assert(d.lease.state == c5_test::State::BLOCKED_REARM && !d.haveCommand);
  d.OnCmdVel(zero); checkZero(); assert(!d.haveCommand);
  DiffDrivePrivate restarted;
  assert(restarted.lease.state == c5_test::State::NO_COMMAND);
  std::cout << "PASS: native callback/receipt, zero target+wheels, timeout, replay blocked, fresh instance\n";
}
