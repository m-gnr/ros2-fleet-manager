#include "Lease.hh"
#include <cassert>
#include <iostream>
using namespace c5_test;
int main() {
  auto t = Lease::Clock::time_point(std::chrono::seconds(10));
  Lease w;
  assert(w.state == State::NO_COMMAND);
  w.Tick(t, 100); assert(w.state == State::NO_COMMAND);
  w.Receive(t, true, .25); assert(w.state == State::ACTIVE && !w.timed_out);
  assert(w.deadline == t + std::chrono::milliseconds(250));
  w.Tick(t + std::chrono::milliseconds(249), 100); assert(w.state == State::ACTIVE);
  w.Tick(t + std::chrono::milliseconds(250), 100); assert(w.state == State::TIMED_OUT);
  w.Tick(t + std::chrono::seconds(1), 100); assert(w.timed_out);
  w.Receive(t + std::chrono::seconds(1), true, .25);
  assert(w.state == State::BLOCKED_REARM && w.timed_out);
  w.Receive(t + std::chrono::seconds(2), true, .25); assert(w.state == State::BLOCKED_REARM);
  Lease fresh; assert(fresh.state == State::NO_COMMAND);
  fresh.Receive(t, true, .25); fresh.Tick(t, 200); fresh.Tick(t, 0);
  assert(fresh.state == State::BLOCKED_REARM);
  Lease backward; backward.Receive(t, true, .25);
  backward.Tick(t - std::chrono::seconds(1), 0); assert(backward.state == State::TIMED_OUT);
  Lease invalid; invalid.Receive(t, false, .25);
  assert(invalid.state == State::BLOCKED_REARM && invalid.deadline == Lease::Clock::time_point{});
  Lease forward; forward.Receive(t, true, .25); forward.Tick(t, 999999999999LL);
  assert(forward.state == State::ACTIVE); // sim jumps do not renew or expire wall lease.
  Lease refresh; refresh.Receive(t, true, .25);
  refresh.Receive(t + std::chrono::milliseconds(200), true, .25);
  assert(refresh.deadline == t + std::chrono::milliseconds(450) && !refresh.timed_out);
  std::cout << "PASS: startup/no-command, receipt/deadline, boundary timeout, hold, blocked replay/rearm, paused sim, reset, backward clock, refresh\n";
}
