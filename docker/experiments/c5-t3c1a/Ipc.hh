#pragma once
// Local, same-build actuator handoff only. Never a Fleet Manager permit.
#include <array>
#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>
#include "../c5-b6b5/Lease.hh"

namespace c5_split {
constexpr uint64_t Magic=0x43355a45524f3031ULL;
using Token=std::array<char,64>;
inline bool token(const Token & t) {
  return std::all_of(t.begin(),t.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');});
}
inline Token field(const std::string & text) {
  Token t{};if(text.size()==t.size())std::copy(text.begin(),text.end(),t.begin());return t;
}
inline std::string string(const Token & t){return {t.begin(),t.end()};}
enum class Why:uint32_t { INITIAL, WAITING, NO_PERMIT, VERIFIED_ZERO, WORKER_CLOSED,
  IPC_ERROR, MALFORMED, CREDENTIALS, SESSION, CONTEXT, REPLAY, TIMEOUT, NATIVE_CLOSED, CLOCK_REWOUND
#ifdef C5_SPLIT_HEALTH_VETO
 ,HEALTH_WAITING, HEALTH_REJECTED, HEALTH_EXPIRED
#endif
 };
inline const char * name(Why w) {
  switch(w) {
  case Why::INITIAL:return "INITIAL";case Why::WAITING:return "WAITING";
  case Why::NO_PERMIT:return "NO_PERMIT";case Why::VERIFIED_ZERO:return "VERIFIED_ZERO";
  case Why::WORKER_CLOSED:return "WORKER_CLOSED";case Why::IPC_ERROR:return "IPC_ERROR";
  case Why::MALFORMED:return "MALFORMED";case Why::CREDENTIALS:return "CREDENTIALS";
  case Why::SESSION:return "SESSION";case Why::CONTEXT:return "CONTEXT";
  case Why::REPLAY:return "REPLAY";case Why::TIMEOUT:return "TIMEOUT";
  case Why::NATIVE_CLOSED:return "NATIVE_CLOSED";case Why::CLOCK_REWOUND:return "CLOCK_REWOUND";
#ifdef C5_SPLIT_HEALTH_VETO
  case Why::HEALTH_WAITING:return "HEALTH_WAITING";
  case Why::HEALTH_REJECTED:return "HEALTH_REJECTED";
  case Why::HEALTH_EXPIRED:return "HEALTH_EXPIRED";
#endif
  }return "UNKNOWN";
}
#ifdef C5_SPLIT_HEALTH_VETO
struct HealthPart {
  Token session{},digest{};
  uint64_t sequence{},ticket{};int64_t remaining_ns{};
  uint32_t status{},reserved{}; // 0 missing, 1 source veto, 2 current observations, 3 invalid transfer.
};
// Evidence only: predicates retain the existing rejection/latch behavior.
enum ReplayCheck:uint32_t { NOT_WAITING=1, CHALLENGE=2, CLOCK_BEFORE_ISSUED=4,
  TICKET_EXPIRED=8, REPORT_SEQUENCE=16, COMMAND_SEQUENCE=32, COMMAND_BODY=64 };
struct IpcTrace {
  uint64_t expected_challenge{},received_challenge{},previous_report{},previous_command{},received_report{},received_command{};
  int64_t checked_ns{},issued_ns{},deadline_ns{},worker_received_ns{},worker_verified_ns{},worker_ready_ns{};
  uint32_t replay_checks{},reserved{};
};
#endif
struct Reply {
  uint64_t magic{Magic},challenge{},report{},command{};
  Token boot{},session{},context{},body{};
  uint32_t state{}; // c5_test::State, copied only after real AuthorizedZero validation.
  uint32_t reserved{};
  double velocity[6]{};
#ifdef C5_SPLIT_HEALTH_VETO
  HealthPart health{};
  int64_t worker_received_ns{},worker_verified_ns{},worker_ready_ns{};
#endif
};
struct Request {
  uint64_t magic{Magic},challenge{},iteration{},physics_steps{};
  int64_t sim_ns{},steady_ns{};
  Token boot{};
  uint32_t reason{},latched{};
  uint64_t accepted{},rejected{},command{};
  double selected[2]{},joint_velocity[2]{},position[3]{};
  uint32_t actual_velocity_known{},reserved{};
  int64_t odom_sim_ns{};
  double odom[5]{}; // x, y, yaw, linear speed, angular speed from actual joint positions.
  double body_velocity[6]{};
  Token native_session{},context{},body{};
#ifdef C5_SPLIT_HEALTH_VETO
  HealthPart health{},health_input{};uint64_t health_ticket{};uint32_t health_seen{},input_accepted{};
  Token input_session{},input_context{},input_body{};
  uint64_t input_command{},input_report{};
  IpcTrace ipc_trace{};
  int64_t health_deadline_ns{},health_ticket_issued_ns{};
#endif
};
#ifdef C5_SPLIT_HEALTH_VETO
static_assert(sizeof(Reply)<1024 && sizeof(Request)<1536,"Bounded veto/readback records required");
#else
static_assert(sizeof(Reply)<512 && sizeof(Request)<512,"Bounded native records required");
#endif

// This object is owned only by the physics callback. No locks or allocation in Step.
class Veto {
 public:
  using Clock=std::chrono::steady_clock;using Time=Clock::time_point;
  Veto(int fd,Token boot,pid_t worker,double ticket,double lease
#ifdef C5_SPLIT_HEALTH_VETO
    ,double healthBudget
#endif
  ):fd(fd),boot(boot),worker(worker),ticket(ticket),lease(lease) {
#ifdef C5_SPLIT_HEALTH_VETO
    if(!std::isfinite(healthBudget)||healthBudget<=0)throw std::invalid_argument("Existing health budget required");
    healthLimit=healthBudget;
#endif
    if(!token(boot)||worker<=0||!std::isfinite(ticket)||!std::isfinite(lease)||ticket<=0||lease<=0)
      throw std::invalid_argument("Explicit boot, worker and existing native budgets required");
    int type=0;socklen_t size=sizeof(type);int enabled=1;
    if(getsockopt(fd,SOL_SOCKET,SO_TYPE,&type,&size)||type!=SOCK_SEQPACKET||
       !(fcntl(fd,F_GETFL)&O_NONBLOCK)||setsockopt(fd,SOL_SOCKET,SO_PASSCRED,&enabled,sizeof(enabled)))
      throw std::invalid_argument("Inherited nonblocking seqpacket endpoint required");
  }
  void Block(Why value){if(!latched){latched=true;reason=value;}live=false;}
  void Step(Time now,int64_t sim) {
#ifdef C5_SPLIT_HEALTH_VETO
    if(healthSeen&&now>=healthDeadline)Block(Why::HEALTH_EXPIRED);
#endif
    if(lastSim>=0 && sim<lastSim)Block(Why::CLOCK_REWOUND);lastSim=sim;
    if(bound && now>=commandDeadline)Block(Why::TIMEOUT);
    if(waiting && (now<issued||now>=deadline)) {
      if(bound)Block(Why::TIMEOUT);
      // Like the existing Lease, NO_COMMAND has no motion lease to expire.
      // Discard expired initial observation challenges; never accept old ACTIVE evidence.
      waiting=false;if(!latched)reason=Why::WAITING;
    }
#ifdef C5_SPLIT_HEALTH_VETO
    const auto inputBefore=accepted;
#endif
    Reply response{};char control[CMSG_SPACE(sizeof(ucred))]{};
    iovec io{&response,sizeof(response)};msghdr message{};
    message.msg_iov=&io;message.msg_iovlen=1;message.msg_control=control;message.msg_controllen=sizeof(control);
    // Exactly one bounded receive. Queued old records cannot be drained into freshness.
    auto got=recvmsg(fd,&message,MSG_DONTWAIT|MSG_TRUNC);
    if(got<0){if(errno!=EAGAIN&&errno!=EWOULDBLOCK)Block(Why::IPC_ERROR);return;}
    if(got==0){Block(Why::WORKER_CLOSED);return;}
    ++received;
#ifdef C5_SPLIT_HEALTH_VETO
    if(got==sizeof(response)&&!(message.msg_flags&(MSG_TRUNC|MSG_CTRUNC))){lastInput=response;inputAccepted=false;}
#endif
    if(latched){waiting=false;return;} // Continue observations without reopening this latch.
    if(got!=sizeof(response)||(message.msg_flags&(MSG_TRUNC|MSG_CTRUNC))){Block(Why::MALFORMED);return;}
    bool credential=false;
    for(auto c=CMSG_FIRSTHDR(&message);c;c=CMSG_NXTHDR(&message,c))
      if(c->cmsg_level==SOL_SOCKET&&c->cmsg_type==SCM_CREDENTIALS&&c->cmsg_len==CMSG_LEN(sizeof(ucred))){
        ucred sender{};std::memcpy(&sender,CMSG_DATA(c),sizeof(sender));credential=sender.pid==worker&&sender.uid==geteuid();
      }
#ifdef C5_SPLIT_HEALTH_VETO
    lastInput=response;inputAccepted=false;
#endif
    Accept(response,now,credential);
#ifdef C5_SPLIT_HEALTH_VETO
    inputAccepted=accepted>inputBefore;
#endif
  }
  void Accept(const Reply & r,Time now,bool credential) {
    if(latched)return;
#ifdef C5_SPLIT_HEALTH_VETO
    ipcTrace={challenge,r.challenge,lastReport,lastCommand,r.report,r.command,ns(now),ns(issued),ns(deadline),
      r.worker_received_ns,r.worker_verified_ns,r.worker_ready_ns,
      uint32_t((!waiting?NOT_WAITING:0)|(r.challenge!=challenge?CHALLENGE:0)|
        (now<issued?CLOCK_BEFORE_ISSUED:0)|(now>=deadline?TICKET_EXPIRED:0)|
        (r.report<=lastReport?REPORT_SEQUENCE:0)|(r.command<lastCommand?COMMAND_SEQUENCE:0)|
        (r.command==lastCommand&&r.body!=body?COMMAND_BODY:0)),0};
#endif
    if(!credential){++rejected;Block(Why::CREDENTIALS);return;}
    if(r.magic!=Magic||r.reserved||!token(r.session)||r.state>3||
       std::any_of(std::begin(r.velocity),std::end(r.velocity),[](double v){return !std::isfinite(v)||v!=0.;})){
      ++rejected;Block(Why::MALFORMED);return;
    }
    if(r.boot!=boot || (pinnedSession && r.session!=session)){++rejected;Block(Why::SESSION);return;}
    if(!waiting||r.challenge!=challenge||now<issued||now>=deadline||r.report<=lastReport){
      ++rejected;
      if(!bound&&r.state==uint32_t(c5_test::State::NO_COMMAND)) {
        // Discard an old NO_COMMAND response without retiring a newer request.
        // Old ACTIVE responses still take the unchanged permanent REPLAY latch.
        if(r.challenge==challenge)waiting=false;
        reason=Why::WAITING;return;
      }
      Block(Why::REPLAY);return;
    }
    if(!pinnedSession){session=r.session;pinnedSession=true;}
    if(r.state==uint32_t(c5_test::State::TIMED_OUT)||r.state==uint32_t(c5_test::State::BLOCKED_REARM)){
      ++rejected;Block(Why::NATIVE_CLOSED);return;
    }
    if(r.state==uint32_t(c5_test::State::ACTIVE)) {
      if(!token(r.context)||!token(r.body)||!r.command){++rejected;Block(Why::CONTEXT);return;}
      if(bound&&r.context!=context){++rejected;Block(Why::CONTEXT);return;}
      if(r.command<lastCommand||(r.command==lastCommand&&r.body!=body)){++rejected;Block(Why::REPLAY);return;}
      if(!bound){context=r.context;bound=true;}
      // Heartbeat/report progress alone never renews the command lease.
      if(r.command>lastCommand){lastCommand=r.command;body=r.body;commandDeadline=issued+duration(lease);}
      live=true;reason=Why::VERIFIED_ZERO;
#ifdef C5_SPLIT_HEALTH_VETO
      Health(responseHealth(r),now);
      if(latched){waiting=false;return;}
#endif
    } else {if(bound){Block(Why::NATIVE_CLOSED);return;}reason=Why::NO_PERMIT;live=false;}
    lastReport=r.report;++accepted;waiting=false;
  }
#ifdef C5_SPLIT_HEALTH_VETO
  const HealthPart & responseHealth(const Reply & r)const{return r.health;}
  void Health(const HealthPart & h,Time now){
    live=false;
    if(h.status==3||h.reserved||h.status>3){Block(Why::HEALTH_REJECTED);return;}
    if(h.status==0){if(healthSeen)Block(Why::HEALTH_REJECTED);else reason=Why::HEALTH_WAITING;return;}
    if(!token(h.session)||!token(h.digest)||!h.sequence||(lastHealth.sequence&&h.session!=lastHealth.session)){
      Block(Why::HEALTH_REJECTED);return;
    }
    if(h.sequence<lastHealth.sequence||(h.sequence==lastHealth.sequence&&h.digest!=lastHealth.digest)){
      Block(Why::HEALTH_REJECTED);return;
    }
    if(h.sequence==lastHealth.sequence){live=healthSeen;reason=healthSeen?Why::VERIFIED_ZERO:Why::HEALTH_WAITING;return;}
    if(h.status==1){lastHealth=h;if(healthSeen)Block(Why::HEALTH_REJECTED);else reason=Why::HEALTH_WAITING;return;}
    const auto & stamp=healthTickets[h.ticket%healthTickets.size()];
    if(stamp.first!=h.ticket||now<stamp.second||now>=stamp.second+duration(healthLimit)){
      reason=healthSeen?Why::VERIFIED_ZERO:Why::HEALTH_WAITING;live=healthSeen;return;
    }
    if(h.remaining_ns<=0||h.remaining_ns>std::chrono::duration_cast<std::chrono::nanoseconds>(duration(healthLimit)).count()){
      Block(Why::HEALTH_REJECTED);return;
    }
    auto deadline=stamp.second+std::chrono::nanoseconds(h.remaining_ns);
    if(now>=deadline){if(healthSeen)Block(Why::HEALTH_EXPIRED);else reason=Why::HEALTH_WAITING;return;}
    lastHealth=h;healthDeadline=deadline;healthSeen=true;live=true;reason=Why::VERIFIED_ZERO;
  }
  double healthLimit{};uint64_t healthTicket=0;bool healthSeen=false,inputAccepted=false;
  IpcTrace ipcTrace{};
  static int64_t ns(Time t){return std::chrono::duration_cast<std::chrono::nanoseconds>(t.time_since_epoch()).count();}
  Time healthDeadline{};HealthPart lastHealth{};Reply lastInput{};
  // Bounded history of actual writer-issued challenges, not receipt-time leases.
  std::array<std::pair<uint64_t,Time>,128> healthTickets{};
#endif
  void Send(Request record,Time now) {
    if(waiting)return;
    record.boot=boot;record.challenge=challenge+1;
#ifdef C5_SPLIT_HEALTH_VETO
    record.health_ticket=record.challenge;
#endif
    const auto sent=send(fd,&record,sizeof(record),MSG_DONTWAIT|MSG_NOSIGNAL);
    if(sent==sizeof(record)){++challenge;issued=now;deadline=now+duration(ticket);waiting=true;
#ifdef C5_SPLIT_HEALTH_VETO
      healthTicket=challenge;healthTickets[healthTicket%healthTickets.size()]={healthTicket,now};
#endif
    }
    else if(sent<0&&(errno==EAGAIN||errno==EWOULDBLOCK))Block(Why::IPC_ERROR);
    else Block(Why::WORKER_CLOSED);
  }
  static Clock::duration duration(double sec){return std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(sec));}
  int fd;Token boot,session{},context{},body{};pid_t worker;
  double ticket,lease;bool latched=false,live=false,bound=false,pinnedSession=false,waiting=false;
  Why reason{Why::INITIAL};uint64_t challenge=0,lastReport=0,lastCommand=0,accepted=0,rejected=0,received=0;
  int64_t lastSim=-1;Time issued{},deadline{},commandDeadline{};
};
} // namespace c5_split
