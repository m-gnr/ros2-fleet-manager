#pragma once
#include "AuthorizedZero.hh"
namespace c5_test {
inline Json Provision() {
  return StrictJson(R"({"key_hex":"abababababababababababababababababababababababababababababababab",
    "source_session":"fixture-source","context":{"identity":{"epoch":1,"child_uuid":"fixture-child"}},
    "permit_id":"fixture-permit","generation":1,"lease_sec":0.25,"ticket_sec":0.2,"permit_sec":10.0})");
}
inline Json Body(AuthorizedZero & a, uint64_t sequence, AuthorizedZero::Time now) {
  return {{"source_session", "fixture-source"}, {"actuator_session", a.session},
    {"command_sequence", sequence}, {"permit_id", "fixture-permit"}, {"permit_generation", uint64_t{1}},
    {"command_context", Provision()["context"]}, {"ticket", a.Offer(now)},
    {"issued_at", {{"clock", "source_monotonic"}, {"value", 123.}}}, {"velocity", {0.,0.,0.,0.,0.,0.}}};
}
inline std::string WireBytes(const std::string & bytes, bool correct = true) {
  std::array<unsigned char, 32> key; key.fill(correct ? 0xab : 0xcd);
  unsigned char value[EVP_MAX_MD_SIZE]; unsigned int size = 0;
  HMAC(EVP_sha256(), key.data(), key.size(), reinterpret_cast<const unsigned char *>(bytes.data()),
       bytes.size(), value, &size);
  return Json({{"body", bytes}, {"mac", Hex(value, size)}}).dump();
}
inline std::string Wire(const Json & b, bool correct = true) {return WireBytes(b.dump(), correct);}
}  // namespace c5_test
