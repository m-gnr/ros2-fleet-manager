#include "TestFixture.hh"
#include <cassert>
#include <iostream>
#include <sys/stat.h>
using namespace c5_test;
int main() {
  const auto t = AuthorizedZero::Clock::now();
  int checks = 0;
  auto check = [&](const std::string & kind, auto mutate, const std::string & expected) {
    AuthorizedZero a(Provision(), t); Lease lease;
    auto body = Body(a, 1, t); mutate(body);
    assert(a.Receive(Wire(body, kind != "mac"), t, lease) == expected);
    assert(a.accepted == (expected == "ACCEPTED_ZERO" ? 1u : 0u)); ++checks;
  };
  check("valid", [](auto &) {}, "ACCEPTED_ZERO");
  check("mac", [](auto &) {}, "UNAUTHENTICATED");
  check("source", [](auto & b) {b["source_session"]="old";}, "SESSION");
  check("session", [](auto & b) {b["actuator_session"]="old";}, "SESSION");
  check("sequence", [](auto & b) {b["command_sequence"]=0;}, "SEQUENCE");
  check("sequence", [](auto & b) {b["command_sequence"]=1.0;}, "SEQUENCE");
  check("generation", [](auto & b) {b["permit_generation"]=2;}, "PERMIT");
  check("context", [](auto & b) {b["command_context"]["identity"]["epoch"]=2;}, "CONTEXT");
  check("context", [](auto & b) {b["command_context"]["identity"]["epoch"]=1.0;}, "CONTEXT");
  check("clock", [](auto & b) {b["issued_at"]["clock"]="ros_sim";}, "CLOCK_SCHEMA");
  check("ticket", [](auto & b) {b["ticket"]="old";}, "EXPIRED_OR_USED_TICKET");
  check("nonzero", [](auto & b) {b["velocity"][5]=.1;}, "NONZERO_DISABLED");
  check("nonzero", [](auto & b) {b["velocity"][0]=nullptr;}, "NONZERO_DISABLED");
  AuthorizedZero a(Provision(), t); Lease l;
  auto b = Body(a, 1, t); const auto wire = Wire(b);
  assert(a.Receive(wire, t, l) == "ACCEPTED_ZERO");
  const auto receipt = a.receipt;
  assert(a.Receive(wire, t+std::chrono::milliseconds(10), l) == "REPLAY");
  b["velocity"][0]=.1;
  assert(a.Receive(Wire(b), t, l) == "CHANGED_PAYLOAD");
  assert(a.receipt == receipt);
  auto next = Body(a, 2, t);
  assert(a.Receive(Wire(next), t+std::chrono::milliseconds(201), l) == "EXPIRED_OR_USED_TICKET");
  a.Tick(t+std::chrono::milliseconds(250), 1, l);
  assert(l.state == State::TIMED_OUT);
  next = Body(a, 3, t+std::chrono::milliseconds(250));
  assert(a.Receive(Wire(next), t+std::chrono::milliseconds(250), l) == "BLOCKED_REARM");
  assert(a.receipt == receipt);
  AuthorizedZero restarted(Provision(), t); Lease newLease;
  assert(restarted.Receive(wire, t, newLease) == "SESSION");
  AuthorizedZero expired(Provision(), t); Lease expiredLease;
  auto expiredBody = Body(expired, 1, t);
  assert(expired.Receive(Wire(expiredBody), t+std::chrono::seconds(10), expiredLease) == "BLOCKED_REARM");
  auto bad = Body(restarted, 1, t).dump();
  bad.insert(1, "\"command_sequence\":1,");
  assert(restarted.Receive(WireBytes(bad), t, newLease) == "MALFORMED");
  assert(restarted.Receive(std::string(16385, 'a'), t, newLease) == "MALFORMED");
  char file[] = "/tmp/native-provision-XXXXXX";
  const int fd = mkstemp(file); assert(fd >= 0);
  const auto provision = Provision().dump();
  assert(write(fd, provision.data(), provision.size()) == static_cast<ssize_t>(provision.size())); close(fd);
  assert(chmod(file, 0644) == 0);
  bool denied = false;
  try {auto badFile = AuthorizedZero::Load(file, t);} catch (const std::exception &) {denied = true;}
  assert(denied); assert(chmod(file, 0600) == 0);
  auto privateFile = AuthorizedZero::Load(file, t); assert(privateFile);
  const std::string alias = std::string(file)+"-link"; assert(symlink(file, alias.c_str()) == 0);
  denied = false;
  try {auto badLink = AuthorizedZero::Load(alias, t);} catch (const std::exception &) {denied = true;}
  assert(denied); unlink(alias.c_str()); unlink(file);
  std::cout << "PASS " << checks << " schema cases; replay, changed payload, expiry, no rearm, restart, duplicate keys, size bound\n";
}
