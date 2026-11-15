// Test ABI over the unchanged B6B.5 state machine; no robot or velocity output.
#include "../c5-b6b5/Lease.hh"
extern "C" {
void *lease_new() { return new c5_test::Lease; }
void lease_delete(void *p) { delete static_cast<c5_test::Lease *>(p); }
int lease_tick(void *p) {
  auto &l = *static_cast<c5_test::Lease *>(p);
  l.Tick(c5_test::Lease::Clock::now(), 0);
  return static_cast<int>(l.state);
}
void lease_receive(void *p) {
  static_cast<c5_test::Lease *>(p)->Receive(c5_test::Lease::Clock::now(), true, .25);
}
void lease_block(void *p) { static_cast<c5_test::Lease *>(p)->Block(); }
}
