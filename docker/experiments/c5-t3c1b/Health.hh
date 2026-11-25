#pragma once
// Diagnostic signatures and a veto-only receiver. No permit or movement API.
#include "../c5-b6b7/AuthorizedZero.hh"
#include "../c5-t3c1a/Ipc.hh"
namespace c5_health {
using namespace c5_test;
constexpr auto ReadbackDomain="C5_SPLIT_ZERO_READBACK_V1\n";
constexpr auto VetoDomain="C5_HEALTH_VETO_V1\n";
class Codec {
  std::array<unsigned char,32> key{};
 public:
  explicit Codec(const std::string & path) {
    int fd=open(path.c_str(),O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0)throw std::invalid_argument("Diagnostic key unavailable");
    struct Guard{int fd;~Guard(){close(fd);}}guard{fd};struct stat st{};
    if(fstat(fd,&st)||!S_ISREG(st.st_mode)||st.st_uid!=geteuid()||(st.st_mode&077)||st.st_size<=0||st.st_size>8192)
      throw std::invalid_argument("Owner-only bounded native provision required");
    std::string data(st.st_size,'\0');size_t used=0;
    while(used<data.size()){auto n=read(fd,data.data()+used,data.size()-used);if(n<=0)throw std::invalid_argument("Incomplete provision");used+=n;}
    auto hex=StrictJson(data).at("key_hex").get<std::string>();
    if(hex.size()!=64||hex.find_first_not_of("0123456789abcdef")!=std::string::npos)throw std::invalid_argument("Key schema");
    for(size_t i=0;i<key.size();++i)key[i]=std::stoul(hex.substr(i*2,2),nullptr,16);
  }
  ~Codec(){OPENSSL_cleanse(key.data(),key.size());}
  std::string mac(const std::string & domain,const std::string & body)const {
    auto input=domain+body;unsigned char out[EVP_MAX_MD_SIZE];unsigned int size=0;
    if(!HMAC(EVP_sha256(),key.data(),key.size(),reinterpret_cast<const unsigned char*>(input.data()),input.size(),out,&size))
      throw std::runtime_error("Diagnostic HMAC unavailable");
    return Hex(out,size);
  }
  Json sign(const Json & value)const{auto body=value.dump();return {{"body",body},{"mac",mac(ReadbackDomain,body)}};}
  Json verify(const std::string & wire)const {
    if(wire.size()>32768)throw std::invalid_argument("Bounded health packet required");
    auto packet=StrictJson(wire);
    if(!Keys(packet,{"body","mac"}))throw std::invalid_argument("Health packet schema");
    auto body=packet.at("body").get<std::string>();auto signature=packet.at("mac").get<std::string>();auto expected=mac(VetoDomain,body);
    if(signature.size()!=expected.size()||CRYPTO_memcmp(signature.data(),expected.data(),expected.size()))throw std::invalid_argument("Health MAC");
    return StrictJson(body);
  }
};

class Receiver {
 public:
  c5_split::HealthPart latest{};bool closed=false;std::string reason="MISSING",lastBody,observer;
  Json sourceCursors=Json::object();uint64_t received=0,rejected=0;int64_t receivedNs=0;
  const Codec & codec;std::string robot,boot;Json budgets;
  Receiver(const Codec & codec,std::string robot,std::string boot,Json budgets):codec(codec),robot(robot),boot(boot),budgets(budgets){}
  void reject(const std::string & why){closed=true;latest.status=3;latest.digest={};reason=why;++rejected;}
  void receive(const std::string & wire,const Json & native,const std::string & identity) {
    if(closed)return;
    try {
      auto p=codec.verify(wire);auto body=StrictJson(wire).at("body").get<std::string>();
      if(!Keys(p,{"robot_id","observer_session","sequence","receiver_session","writer_boot","context_sha256",
          "identity_sha256","ticket","observations_current","remaining_ns","sources","reasons","movement_eligible","physical_stop","ownership_release"})
          ||p["robot_id"]!=robot||p["writer_boot"]!=boot||p["receiver_session"]!=native.at("receiver_session")
          ||p["context_sha256"]!=native.at("context_sha256")||p["identity_sha256"]!=identity
          ||p["movement_eligible"]!=Json(false)||p["ownership_release"]!=Json(false)||p["physical_stop"]!="UNKNOWN"
          ||!Hash(p["observer_session"])||!p["sequence"].is_number_unsigned()||p["sequence"]==0
          ||!p["ticket"].is_number_unsigned()||p["ticket"]==0||!p["observations_current"].is_boolean()
          ||!p["remaining_ns"].is_number_integer()||p["remaining_ns"]<0||!p["sources"].is_object())
        throw std::invalid_argument("Health identity/schema");
      auto session=p["observer_session"].get<std::string>();
      if(!observer.empty()&&observer!=session)throw std::invalid_argument("Health observer session changed");
      auto sequence=p["sequence"].get<uint64_t>();
      if(sequence==latest.sequence&&body==lastBody)return; // No receipt/deadline refresh.
      if(sequence<=latest.sequence)throw std::invalid_argument("Health replay/changed body");
      if(p["sources"].size()!=budgets.size())throw std::invalid_argument("Missing health source");
      int64_t minimum=INT64_MAX;
      for(auto it=budgets.begin();it!=budgets.end();++it){
        auto sample=p["sources"].at(it.key());
        if(!Hash(sample.at("measurement_id"))||sample.at("source_identity")!="UNKNOWN"
            ||!sample.at("remaining_ns").is_number_integer()||sample.at("remaining_ns")<0||sample.at("remaining_ns")>it.value())
          throw std::invalid_argument("Health source schema");
        if(sourceCursors.contains(it.key())){
          auto old=sourceCursors[it.key()];
          if(sample["measurement_id"]==old["measurement_id"]&&sample["remaining_ns"]>old["remaining_ns"])
            throw std::invalid_argument("Health source rejuvenation");
          if(!sample["stamp_ns"].is_null()&&!old["stamp_ns"].is_null()&&sample["stamp_ns"]<old["stamp_ns"])
            throw std::invalid_argument("Health source rewind");
        }
        minimum=std::min(minimum,sample["remaining_ns"].get<int64_t>());
      }
      if(p["remaining_ns"]>minimum||(!p["reasons"].is_array())||
          (p["observations_current"]==Json(true)&&(!p["reasons"].empty()||p["remaining_ns"]==0)))
        throw std::invalid_argument("Contradictory health verdict");
      observer=session;lastBody=body;sourceCursors=p["sources"];
      latest.session=c5_split::field(session);latest.digest=c5_split::field(Digest(body));latest.sequence=sequence;
      latest.ticket=p["ticket"];latest.remaining_ns=p["remaining_ns"];
      latest.status=p["observations_current"]==Json(true)?2:1;++received;reason=latest.status==2?"CURRENT_OBSERVATIONS_ZERO_ONLY":"SOURCE_VETO";
      receivedNs=c5_split::Veto::ns(c5_split::Veto::Clock::now());
    }catch(const std::exception & error){reject(error.what());}
  }
};

inline Json writer(const c5_split::Request & r) {
  return {{"writer_boot",c5_split::string(r.boot)},{"native_session",c5_split::token(r.native_session)?c5_split::string(r.native_session):""},
    {"context_sha256",c5_split::token(r.context)?c5_split::string(r.context):""},
    {"command_sha256",c5_split::token(r.body)?c5_split::string(r.body):""},{"command_sequence",r.command},
    {"iteration",r.iteration},{"physics_steps",r.physics_steps},{"sim_ns",r.sim_ns},
    {"selected",{r.selected[0],r.selected[1]}},{"joint_velocity",{r.joint_velocity[0],r.joint_velocity[1]}},
    {"body_velocity",{r.body_velocity[0],r.body_velocity[1],r.body_velocity[2],r.body_velocity[3],r.body_velocity[4],r.body_velocity[5]}},
    {"velocity_known",bool(r.actual_velocity_known)},{"latched",bool(r.latched)},{"health_ticket",r.health_ticket},
    {"health_sequence",r.health.sequence},{"health_digest",c5_split::token(r.health.digest)?c5_split::string(r.health.digest):""},
    {"health_status",r.health.status},{"health_seen",bool(r.health_seen)},
    {"health_remaining_ns",r.health.remaining_ns},{"health_deadline_ns",r.health_deadline_ns},
    {"health_ticket_issued_ns",r.health_ticket_issued_ns},
    {"health_input_sequence",r.health_input.sequence},{"health_input_ticket",r.health_input.ticket},
    {"health_input_digest",c5_split::token(r.health_input.digest)?c5_split::string(r.health_input.digest):""},
    {"health_input_status",r.health_input.status},
    {"ipc_timing",{{"expected_challenge",r.ipc_trace.expected_challenge},{"received_challenge",r.ipc_trace.received_challenge},
      {"previous_report",r.ipc_trace.previous_report},{"previous_command",r.ipc_trace.previous_command},
      {"received_report",r.ipc_trace.received_report},{"received_command",r.ipc_trace.received_command},
      {"checked_ns",r.ipc_trace.checked_ns},{"issued_ns",r.ipc_trace.issued_ns},{"deadline_ns",r.ipc_trace.deadline_ns},
      {"worker_received_ns",r.ipc_trace.worker_received_ns},{"worker_verified_ns",r.ipc_trace.worker_verified_ns},
      {"worker_ready_ns",r.ipc_trace.worker_ready_ns},{"replay_checks",r.ipc_trace.replay_checks}}},
    {"ipc_input",{{"accepted",bool(r.input_accepted)},
      {"native_session",c5_split::token(r.input_session)?c5_split::string(r.input_session):""},
      {"context_sha256",c5_split::token(r.input_context)?c5_split::string(r.input_context):""},
      {"command_sha256",c5_split::token(r.input_body)?c5_split::string(r.input_body):""},
      {"command_sequence",r.input_command},{"report_sequence",r.input_report}}}};
}
} // namespace c5_health
