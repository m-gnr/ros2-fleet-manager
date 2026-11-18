#pragma once
// Test-only native receiver. No accepted message can produce nonzero movement.
#include "../c5-b6b5/Lease.hh"
#include <openssl/crypto.h>
#include <openssl/hmac.h>
#include <openssl/rand.h>
#include <openssl/sha.h>
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
inline std::string Digest(const std::string & value) {
  unsigned char bytes[SHA256_DIGEST_LENGTH];
  SHA256(reinterpret_cast<const unsigned char *>(value.data()), value.size(), bytes);
  return Hex(bytes, SHA256_DIGEST_LENGTH);
}
inline bool Uuid(const Json & v) {
  if (!v.is_string()) return false;
  const auto text = v.get<std::string>();
  if (text.size() != 36 || text == "00000000-0000-0000-0000-000000000000") return false;
  for (size_t i=0; i<text.size(); ++i) {
    if (i==8 || i==13 || i==18 || i==23) {if (text[i]!='-') return false;}
    else if (std::string("0123456789abcdef").find(text[i])==std::string::npos) return false;
  }
  return true;
}
inline bool Hash(const Json & v) {
  return v.is_string() && v.get<std::string>().size()==64 &&
    v.get<std::string>().find_first_not_of("0123456789abcdef")==std::string::npos;
}
class AuthorizedZero {
 public:
  using Clock = Lease::Clock;
  using Time = Clock::time_point;
  explicit AuthorizedZero(const Json & p, Time now) {
    live = p.contains("live_permits");
    auto fields = std::set<std::string>{"key_hex", "source_session", "context", "permit_id", "generation",
                  "lease_sec", "ticket_sec", "permit_sec"};
    if (live) {fields.insert("live_permits"); fields.insert("robot_id");}
    if (!Keys(p, fields) || (live && p["live_permits"] != Json(true))) throw std::invalid_argument("Provision schema");
    auto hex = p.at("key_hex").get<std::string>();
    if (hex.size() != 64 || hex.find_first_not_of("0123456789abcdef") != std::string::npos)
      throw std::invalid_argument("256-bit key required");
    for (size_t i = 0; i < key.size(); ++i) key[i] = std::stoul(hex.substr(i*2, 2), nullptr, 16);
    source = p.at("source_session").get<std::string>();
    permit = p.at("permit_id").get<std::string>();
    if ((!live && (!p.at("generation").is_number_unsigned() || p.at("generation").get<uint64_t>() == 0 ||
        source.empty() || permit.empty() || !p.at("context").is_object() || p.at("context").empty())) ||
        (live && (p["source_session"]!="" || p["permit_id"]!="" || p["generation"]!=0 ||
                  p["context"]!=Json::object() || !p["robot_id"].is_string() || p["robot_id"]=="")))
      throw std::invalid_argument("Explicit context and nonempty identities required");
    generation = p.at("generation").get<uint64_t>(); context = p.at("context");
    if (live) robot = p["robot_id"].get<std::string>();
    leaseSec = Positive(p.at("lease_sec")); ticketSec = Positive(p.at("ticket_sec"));
    permitSec = Positive(p.at("permit_sec")); permitUntil = Add(now, permitSec);
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
    if ((!live || bound) && now >= permitUntil) {lease.Block(); reason = "PERMIT_EXPIRED";}
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
      if (b["actuator_session"] != session || ((!live || bound) && b["source_session"] != source) ||
          (live && !Uuid(b["source_session"]))) return reject("SESSION");
      if (!b["command_sequence"].is_number_unsigned() || b["command_sequence"].get<uint64_t>() == 0)
        return reject("SEQUENCE");
      const auto next = b["command_sequence"].get<uint64_t>();
      if (next <= sequence) return reject(next == sequence && bodyBytes != lastBody ? "CHANGED_PAYLOAD" : "REPLAY");
      if (!b["permit_generation"].is_number_unsigned() || b["permit_generation"]==0 ||
          ((!live || bound) && (b["permit_generation"] != generation || b["permit_id"] != permit)))
        return reject("PERMIT");
      Json candidate = b["command_context"];
      std::string operation = "INSTALL_ZERO";
      if (live) {
        if (!LiveContext(candidate, b)) return reject("CONTEXT");
        operation = candidate["operation"].get<std::string>();
        candidate["operation"] = "INSTALL_ZERO";
      }
      if ((!live || bound) && candidate.dump() != context.dump()) return reject("CONTEXT");
      const auto & stamp = b["issued_at"];
      if (!Keys(stamp, {"clock", "value"}) || stamp["clock"] != "source_monotonic" ||
          !stamp["value"].is_number() || !std::isfinite(stamp["value"].get<double>())) return reject("CLOCK_SCHEMA");
      if (!b["ticket"].is_string() || ticket.empty() || b["ticket"] != ticket || now >= ticketUntil)
        return reject("EXPIRED_OR_USED_TICKET");
      // Consume a valid ticket before the immutable nonzero inhibition.
      ticket.clear();
      auto inhibit = [&]() {
        inhibitionReason = "NONZERO_DISABLED"; inhibitionCommand = Digest(bodyBytes);
        lease.Block(); return reject("NONZERO_DISABLED");
      };
      if (!b["velocity"].is_array() || b["velocity"].size() != 6) return inhibit();
      for (const auto & v : b["velocity"]) {
        if (!v.is_number() || !std::isfinite(v.get<double>()) || v.get<double>() != 0.) {
          return inhibit();
        }
      }
      if (live && !bound) {
        context = candidate; source = b["source_session"].get<std::string>();
        permit = b["permit_id"].get<std::string>(); generation = b["permit_generation"].get<uint64_t>();
        permitUntil = Add(now, permitSec); bound = true;
      }
      sequence = next; lastBody = bodyBytes; verifiedAt = now; lastOperation = operation;
      if (live && operation == "REVOKE_ZERO") {
        lease.Block(); reason = "PERMIT_REVOKED"; return reason;
      }
      receipt = now;
      lease.Receive(now, true, leaseSec); ++accepted; reason = "ACCEPTED_ZERO";
      return reason;
    } catch (const std::exception &) {return reject("MALFORMED");}
  }
  Json Snapshot(Time now, const Lease & lease) {
    Json output = {{"state", lease.Name()}, {"reason", reason}, {"actuator_session", session},
      {"ticket", Offer(now)}, {"sequence", sequence}, {"accepted", accepted}, {"rejected", rejected},
      {"receipt_steady_ns", std::chrono::duration_cast<std::chrono::nanoseconds>(receipt.time_since_epoch()).count()},
      {"steady_ns", std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count()},
      {"movement_authorized", false}, {"ownership_release", false}};
    if (live) {
      // Sticky diagnostic of the first nonzero inhibition. Subsequent blocked
      // traffic may change `reason`; this is never an accepted-command receipt.
      output["inhibition_reason"] = inhibitionReason;
      output["inhibited_command_sha256"] = inhibitionCommand;
      Json status = {{"robot_id", robot}, {"receiver_session", session}, {"ticket", ticket},
        {"report_sequence", ++reports}, {"receiver_state", lease.Name()}, {"source_session", source},
        {"sequence", sequence}, {"permit_id", permit}, {"generation", generation},
        {"context_sha256", bound ? Digest(context.dump()) : ""},
        {"command_sha256", lastBody.empty() ? "" : Digest(lastBody)}, {"operation", lastOperation},
        {"verified_steady_ns", std::chrono::duration_cast<std::chrono::nanoseconds>(verifiedAt.time_since_epoch()).count()},
        {"steady_ns", output["steady_ns"]}, {"movement_authorized", false}, {"ownership_release", false}};
      const auto body = status.dump();
      const auto macInput = std::string("C5_NATIVE_ZERO_STATUS_V1\n") + body;
      unsigned int size=0; unsigned char mac[EVP_MAX_MD_SIZE];
      if (!HMAC(EVP_sha256(), key.data(), key.size(), reinterpret_cast<const unsigned char *>(macInput.data()),
          macInput.size(), mac, &size)) throw std::runtime_error("Status HMAC unavailable");
      output["native_status"] = {{"body", body}, {"mac", Hex(mac, size)}};
    }
    return output;
  }
  std::string session, reason{"NO_COMMAND"};
  uint64_t sequence{0}, accepted{0}, rejected{0};
  std::string inhibitionReason, inhibitionCommand;
  Time receipt{};
 private:
  bool LiveContext(const Json & c, const Json & b) {
    if (!Keys(c, {"operation", "permit_event_id", "permit_decision", "permit_decision_sha256",
                  "child_event_id", "child_decision", "child_decision_sha256"}) ||
        (c["operation"]!="INSTALL_ZERO" && c["operation"]!="REVOKE_ZERO") ||
        !c["permit_decision"].is_string() || !c["child_decision"].is_string() ||
        Digest(c["permit_decision"].get<std::string>())!=c["permit_decision_sha256"] ||
        Digest(c["child_decision"].get<std::string>())!=c["child_decision_sha256"]) return false;
    const auto p=StrictJson(c["permit_decision"].get<std::string>());
    const auto child=StrictJson(c["child_decision"].get<std::string>());
    for (const auto & name : {"identity", "request_id", "geometry_digest", "movement_kind", "station_id"})
      if (p.at(name)!=child.at(name)) return false;
    if (p.at("status")!="RESERVED" || child.at("status")!="RESERVED" ||
        p.at("movement_authorized")!=Json(false) || child.at("movement_authorized")!=Json(false) ||
        child.at("physical_stop")!="UNKNOWN" || child.at("ownership_release")!=Json(false)) return false;
    const auto i=p.at("identity"); const auto proof=child.at("child_provenance");
    if (!Keys(i, {"robot_id", "task_id", "epoch", "execute_uuid", "child_uuid", "executor_session", "fm_session",
                  "permit_id", "generation", "path_hash", "map_revision", "frame", "geometry_revision"})) return false;
    for (const auto & name : {"execute_uuid", "child_uuid", "executor_session", "fm_session", "permit_id"})
      if (!Uuid(i.at(name))) return false;
    for (const auto & name : {"context_id", "nav_uuid", "observer_session"}) if (!Uuid(proof.at(name))) return false;
    for (const auto & name : {"task_id", "map_revision", "frame", "geometry_revision"})
      if (!i.at(name).is_string() || i.at(name)=="") return false;
    return i.at("robot_id")==robot && i.at("fm_session")==b["source_session"] &&
      i.at("epoch").is_number_unsigned() && i.at("epoch")!=0 &&
      i.at("generation").is_number_unsigned() && i.at("generation")==b["permit_generation"] &&
      i.at("permit_id")==b["permit_id"] && Hash(i.at("path_hash")) && Hash(p.at("geometry_digest")) &&
      i.at("child_uuid")!=i.at("execute_uuid") && proof.at("nav_uuid")!=i.at("execute_uuid") &&
      proof.at("nav_uuid")!=i.at("child_uuid") && proof.at("kind")==1 && proof.at("sequence")==1 &&
      Uuid(p.at("request_id")) && c["permit_event_id"]=="permit:"+p.at("request_id").get<std::string>() &&
      c["child_event_id"]=="child:"+proof.at("context_id").get<std::string>()+":1";
  }
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
  bool live{false}, bound{false};
  std::string robot, lastOperation{"NONE"};
  uint64_t reports{0};
  Time verifiedAt{};
  double leaseSec, ticketSec, permitSec;
  Time ticketUntil{}, permitUntil{};
};
}  // namespace c5_test
