#pragma once
// Test-only native receiver. No accepted message can produce nonzero movement.
#include "../c5-b6b5/Lease.hh"
#include <openssl/crypto.h>
#include <openssl/hmac.h>
#include <openssl/rand.h>
#include <nlohmann/json.hpp>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <array>
#include <cmath>
#include <fstream>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace c5_test {
using Json = nlohmann::json;
inline Json StrictJson(const std::string & value) {
  std::vector<std::set<std::string>> objects;
  return Json::parse(value, [&](int depth, Json::parse_event_t event, Json & item) {
    if (depth > 16) throw std::invalid_argument("JSON nesting limit");
    if (event == Json::parse_event_t::object_start) objects.emplace_back();
    if (event == Json::parse_event_t::key && !objects.back().insert(item.get<std::string>()).second)
      throw std::invalid_argument("Duplicate JSON key");
    if (event == Json::parse_event_t::object_end) objects.pop_back();
    return true;
  });
}
inline std::string Hex(const unsigned char * bytes, size_t size) {
  constexpr char digits[] = "0123456789abcdef";
  std::string value; value.reserve(size * 2);
  for (size_t i = 0; i < size; ++i) {value += digits[bytes[i] >> 4]; value += digits[bytes[i] & 15];}
  return value;
}
inline std::string Nonce() {
  std::array<unsigned char, 32> value{};
  if (RAND_bytes(value.data(), value.size()) != 1) throw std::runtime_error("Random source unavailable");
  return Hex(value.data(), value.size());
}
inline bool Keys(const Json & value, const std::set<std::string> & keys) {
  if (!value.is_object() || value.size() != keys.size()) return false;
  for (const auto & key : keys) if (!value.contains(key)) return false;
  return true;
}
class AuthorizedZero {
 public:
  using Clock = Lease::Clock;
  using Time = Clock::time_point;
  explicit AuthorizedZero(const Json & p, Time now) {
    if (!Keys(p, {"key_hex", "source_session", "context", "permit_id", "generation",
                  "lease_sec", "ticket_sec", "permit_sec"})) throw std::invalid_argument("Provision schema");
    auto hex = p.at("key_hex").get<std::string>();
    if (hex.size() != 64 || hex.find_first_not_of("0123456789abcdef") != std::string::npos)
      throw std::invalid_argument("256-bit key required");
    for (size_t i = 0; i < key.size(); ++i) key[i] = std::stoul(hex.substr(i*2, 2), nullptr, 16);
    source = p.at("source_session").get<std::string>();
    permit = p.at("permit_id").get<std::string>();
    if (!p.at("generation").is_number_unsigned() || p.at("generation").get<uint64_t>() == 0 ||
        source.empty() || permit.empty() || !p.at("context").is_object() || p.at("context").empty())
      throw std::invalid_argument("Explicit context and nonempty identities required");
    generation = p.at("generation").get<uint64_t>(); context = p.at("context");
    leaseSec = Positive(p.at("lease_sec")); ticketSec = Positive(p.at("ticket_sec"));
    permitUntil = Add(now, Positive(p.at("permit_sec")));
    session = Nonce();
  }
  ~AuthorizedZero() {OPENSSL_cleanse(key.data(), key.size());}
  AuthorizedZero(const AuthorizedZero &) = delete;
  AuthorizedZero & operator=(const AuthorizedZero &) = delete;

  static std::unique_ptr<AuthorizedZero> Load(const std::string & path, Time now) {
    int fd = open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) throw std::invalid_argument("Native provision unavailable");
    struct Guard {int fd; ~Guard() {close(fd);}} guard{fd};
    struct stat info{};
    if (fstat(fd, &info) != 0 || !S_ISREG(info.st_mode) || info.st_uid != geteuid() ||
        (info.st_mode & 077) || info.st_size <= 0 || info.st_size > 8192)
      throw std::invalid_argument("Native provision must be owner-only regular file");
    std::string data(static_cast<size_t>(info.st_size), '\0');
    size_t used = 0;
    while (used < data.size()) {
      const auto got = read(fd, data.data()+used, data.size()-used);
      if (got <= 0) throw std::invalid_argument("Incomplete native provision");
      used += static_cast<size_t>(got);
    }
    return std::make_unique<AuthorizedZero>(StrictJson(data), now);
  }
  void Tick(Time now, long long sim, Lease & lease) {
    lease.Tick(now, sim);
    if (now >= permitUntil) {lease.Block(); reason = "PERMIT_EXPIRED";}
  }
  std::string Offer(Time now) {
    if (ticket.empty() || now >= ticketUntil) {ticket = Nonce(); ticketUntil = Add(now, ticketSec);}
    return ticket;
  }
  std::string Receive(const std::string & wire, Time now, Lease & lease) {
    Tick(now, lease.sim, lease);
    auto reject = [&](const char * why) {reason = why; ++rejected; return reason;};
    try {
      if (wire.size() > 16384) return reject("MALFORMED");
      const auto packet = StrictJson(wire);
      if (!Keys(packet, {"body", "mac"}) || !packet["body"].is_string() || !packet["mac"].is_string())
        return reject("MALFORMED");
      // MAC binds the exact immutable body bytes, avoiding cross-language float
      // reserialization and Unicode canonicalization differences.
      const auto bodyBytes = packet["body"].get<std::string>();
      const auto mac = packet["mac"].get<std::string>();
      unsigned int size = 0; unsigned char output[EVP_MAX_MD_SIZE];
      if (!HMAC(EVP_sha256(), key.data(), key.size(),
        reinterpret_cast<const unsigned char *>(bodyBytes.data()), bodyBytes.size(), output, &size))
        throw std::runtime_error("HMAC unavailable");
      const auto expected = Hex(output, size);
      if (mac.size() != expected.size() || CRYPTO_memcmp(mac.data(), expected.data(), expected.size()) != 0)
        return reject("UNAUTHENTICATED");
      if (lease.state == State::TIMED_OUT || lease.state == State::BLOCKED_REARM) {
        lease.Block(); return reject("BLOCKED_REARM");
      }
      const auto b = StrictJson(bodyBytes);
      if (!Keys(b, {"source_session", "actuator_session", "command_sequence", "permit_id", "permit_generation",
                    "issued_at", "velocity", "command_context", "ticket"})) return reject("SCHEMA");
      if (b["source_session"] != source || b["actuator_session"] != session) return reject("SESSION");
      if (!b["command_sequence"].is_number_unsigned() || b["command_sequence"].get<uint64_t>() == 0)
        return reject("SEQUENCE");
      const auto next = b["command_sequence"].get<uint64_t>();
      if (next <= sequence) return reject(next == sequence && bodyBytes != lastBody ? "CHANGED_PAYLOAD" : "REPLAY");
      if (!b["permit_generation"].is_number_unsigned() || b["permit_generation"] != generation || b["permit_id"] != permit)
        return reject("PERMIT");
      if (b["command_context"].dump() != context.dump()) return reject("CONTEXT");
      const auto & stamp = b["issued_at"];
      if (!Keys(stamp, {"clock", "value"}) || stamp["clock"] != "source_monotonic" ||
          !stamp["value"].is_number() || !std::isfinite(stamp["value"].get<double>())) return reject("CLOCK_SCHEMA");
      if (!b["ticket"].is_string() || ticket.empty() || b["ticket"] != ticket || now >= ticketUntil)
        return reject("EXPIRED_OR_USED_TICKET");
      // Consume a valid ticket before the immutable nonzero inhibition.
      ticket.clear();
      if (!b["velocity"].is_array() || b["velocity"].size() != 6) {lease.Block(); return reject("NONZERO_DISABLED");}
      for (const auto & v : b["velocity"]) {
        if (!v.is_number() || !std::isfinite(v.get<double>()) || v.get<double>() != 0.) {
          lease.Block(); return reject("NONZERO_DISABLED");
        }
      }
      sequence = next; lastBody = bodyBytes; receipt = now;
      lease.Receive(now, true, leaseSec); ++accepted; reason = "ACCEPTED_ZERO";
      return reason;
    } catch (const std::exception &) {return reject("MALFORMED");}
  }
  Json Snapshot(Time now, const Lease & lease) {
    return {{"state", lease.Name()}, {"reason", reason}, {"actuator_session", session},
      {"ticket", Offer(now)}, {"sequence", sequence}, {"accepted", accepted}, {"rejected", rejected},
      {"receipt_steady_ns", std::chrono::duration_cast<std::chrono::nanoseconds>(receipt.time_since_epoch()).count()},
      {"steady_ns", std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count()},
      {"movement_authorized", false}, {"ownership_release", false}};
  }
  std::string session, reason{"NO_COMMAND"};
  uint64_t sequence{0}, accepted{0}, rejected{0};
  Time receipt{};
 private:
  static double Positive(const Json & v) {
    if (!v.is_number() || !std::isfinite(v.get<double>()) || v.get<double>() <= 0 || v.get<double>() > 3600)
      throw std::invalid_argument("Finite positive fixture timing budget required");
    return v.get<double>();
  }
  static Time Add(Time t, double seconds) {
    return t + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
  }
  std::array<unsigned char, 32> key{};
  Json context;
  std::string source, permit, ticket, lastBody;
  uint64_t generation;
  double leaseSec, ticketSec;
  Time ticketUntil{}, permitUntil{};
};
}  // namespace c5_test
