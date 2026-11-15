#pragma once
#include <chrono>
#include <cmath>
namespace c5_test {
enum class State { NO_COMMAND, ACTIVE, TIMED_OUT, BLOCKED_REARM };
class Lease {
 public:
  using Clock = std::chrono::steady_clock;
  State state{State::NO_COMMAND};
  Clock::time_point receipt{}, deadline{};
  bool timed_out{false};
  long long sim{-1};
  void Tick(Clock::time_point now, long long sim_ns) {
    if (sim >= 0 && sim_ns < sim) Block();
    sim = sim_ns;
    if (state == State::ACTIVE && (now < receipt || now >= deadline)) {
      state = State::TIMED_OUT;
      timed_out = true;
    }
  }
  void Receive(Clock::time_point now, bool zero, double timeout) {
    // Receipt is transport evidence only, never freshness or motion authority.
    Tick(now, sim);
    receipt = now;
    if (state == State::TIMED_OUT || state == State::BLOCKED_REARM || !zero) {
      Block();
      return;
    }
    deadline = now + std::chrono::duration_cast<Clock::duration>(
        std::chrono::duration<double>(timeout));
    timed_out = false;
    state = State::ACTIVE;
  }
  void Block() { state = State::BLOCKED_REARM; }
  const char *Name() const {
    switch (state) {
      case State::NO_COMMAND: return "NO_COMMAND";
      case State::ACTIVE: return "ACTIVE";
      case State::TIMED_OUT: return "TIMED_OUT";
      default: return "BLOCKED_REARM";
    }
  }
};
}
