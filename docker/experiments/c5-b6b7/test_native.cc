#include "TestFixture.hh"
#include "../c5-b6b5/DiffDrive.cc"
#include <cassert>
#include <thread>
int main() {
  DiffDrivePrivate d;
  d.enabled = true;
  d.authorization = std::make_unique<c5_test::AuthorizedZero>(c5_test::Provision(), std::chrono::steady_clock::now());
  d.limiterLin = std::make_unique<math::SpeedLimiter>(); d.limiterAng = std::make_unique<math::SpeedLimiter>();
  EntityComponentManager ecm; UpdateInfo info; info.dt = std::chrono::milliseconds(5);
  msgs::Twist raw; raw.mutable_linear()->set_x(.4);
  d.OnCmdVel(raw);
  assert(d.lease.state == c5_test::State::NO_COMMAND && d.received.time_since_epoch().count() == 0);
  auto now = std::chrono::steady_clock::now();
  auto body = c5_test::Body(*d.authorization, 1, now);
  msgs::StringMsg command; command.set_data(c5_test::Wire(body));
  d.OnAuthorizedZero(command); d.UpdateVelocity(info, ecm);
  assert(d.lease.state == c5_test::State::ACTIVE && d.authorization->accepted == 1);
  auto receipt = d.received; d.OnAuthorizedZero(command);
  assert(d.authorization->reason == "REPLAY" && d.received == receipt);
  d.OnCmdVel(raw); assert(d.received == receipt);
  std::this_thread::sleep_for(std::chrono::milliseconds(270)); d.UpdateVelocity(info, ecm);
  assert(d.lease.state == c5_test::State::TIMED_OUT);
  body = c5_test::Body(*d.authorization, 2, std::chrono::steady_clock::now());
  command.set_data(c5_test::Wire(body)); d.OnAuthorizedZero(command);
  assert(d.authorization->reason == "BLOCKED_REARM" && d.received == receipt);
  assert(d.leftJointSpeed == 0. && d.rightJointSpeed == 0. && d.targetVel.linear().x() == 0.);
  std::cout << "PASS actual native callback; raw Twist cannot refresh; authorized zero; replay and timeout remain closed\n";
}
