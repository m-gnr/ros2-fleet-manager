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
  IPC_ERROR, MALFORMED, CREDENTIALS, SESSION, CONTEXT, REPLAY, TIMEOUT, NATIVE_CLOSED, CLOCK_REWOUND };
inline const char * name(Why w) {
  switch(w) {
  case Why::INITIAL:return "INITIAL";case Why::WAITING:return "WAITING";
  case Why::NO_PERMIT:return "NO_PERMIT";case Why::VERIFIED_ZERO:return "VERIFIED_ZERO";
  case Why::WORKER_CLOSED:return "WORKER_CLOSED";case Why::IPC_ERROR:return "IPC_ERROR";
  case Why::MALFORMED:return "MALFORMED";case Why::CREDENTIALS:return "CREDENTIALS";
  case Why::SESSION:return "SESSION";case Why::CONTEXT:return "CONTEXT";
  case Why::REPLAY:return "REPLAY";case Why::TIMEOUT:return "TIMEOUT";
  case Why::NATIVE_CLOSED:return "NATIVE_CLOSED";case Why::CLOCK_REWOUND:return "CLOCK_REWOUND";
  }return "UNKNOWN";
}
struct Reply {
  uint64_t magic{Magic},challenge{},report{},command{};
  Token boot{},session{},context{},body{};
  uint32_t state{}; // c5_test::State, copied only after real AuthorizedZero validation.
  uint32_t reserved{};
  double velocity[6]{};
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
};
static_assert(sizeof(Reply)<512 && sizeof(Request)<512,"Bounded native records required");

// This object is owned only by the physics callback. No locks or allocation in Step.
class Veto {
 public:
  using Clock=std::chrono::steady_clock;using Time=Clock::time_point;
  Veto(int fd,Token boot,pid_t worker,double ticket,double lease):fd(fd),boot(boot),worker(worker),ticket(ticket),lease(lease) {
    if(!token(boot)||worker<=0||!std::isfinite(ticket)||!std::isfinite(lease)||ticket<=0||lease<=0)
      throw std::invalid_argument("Explicit boot, worker and existing native budgets required");
    int type=0;socklen_t size=sizeof(type);int enabled=1;
    if(getsockopt(fd,SOL_SOCKET,SO_TYPE,&type,&size)||type!=SOCK_SEQPACKET||
       !(fcntl(fd,F_GETFL)&O_NONBLOCK)||setsockopt(fd,SOL_SOCKET,SO_PASSCRED,&enabled,sizeof(enabled)))
      throw std::invalid_argument("Inherited nonblocking seqpacket endpoint required");
  }
  void Block(Why value){if(!latched){latched=true;reason=value;}live=false;}
  void Step(Time now,int64_t sim) {
    if(lastSim>=0 && sim<lastSim)Block(Why::CLOCK_REWOUND);lastSim=sim;
    if(bound && now>=commandDeadline)Block(Why::TIMEOUT);
    if(waiting && (now<issued||now>=deadline)) {
      if(bound)Block(Why::TIMEOUT);
      // Like the existing Lease, NO_COMMAND has no motion lease to expire.
      // Discard expired initial observation challenges; never accept old ACTIVE evidence.
      waiting=false;if(!latched)reason=Why::WAITING;
    }
    Reply response{};char control[CMSG_SPACE(sizeof(ucred))]{};
    iovec io{&response,sizeof(response)};msghdr message{};
    message.msg_iov=&io;message.msg_iovlen=1;message.msg_control=control;message.msg_controllen=sizeof(control);
    // Exactly one bounded receive. Queued old records cannot be drained into freshness.
    auto got=recvmsg(fd,&message,MSG_DONTWAIT|MSG_TRUNC);
    if(got<0){if(errno!=EAGAIN&&errno!=EWOULDBLOCK)Block(Why::IPC_ERROR);return;}
    if(got==0){Block(Why::WORKER_CLOSED);return;}
    ++received;
    if(latched){waiting=false;return;} // Continue observations without reopening this latch.
    if(got!=sizeof(response)||(message.msg_flags&(MSG_TRUNC|MSG_CTRUNC))){Block(Why::MALFORMED);return;}
    bool credential=false;
    for(auto c=CMSG_FIRSTHDR(&message);c;c=CMSG_NXTHDR(&message,c))
      if(c->cmsg_level==SOL_SOCKET&&c->cmsg_type==SCM_CREDENTIALS&&c->cmsg_len==CMSG_LEN(sizeof(ucred))){
        ucred sender{};std::memcpy(&sender,CMSG_DATA(c),sizeof(sender));credential=sender.pid==worker&&sender.uid==geteuid();
      }
    Accept(response,now,credential);
  }
  void Accept(const Reply & r,Time now,bool credential) {
    if(latched)return;
    if(!credential){++rejected;Block(Why::CREDENTIALS);return;}
    if(r.magic!=Magic||r.reserved||!token(r.session)||r.state>3||
       std::any_of(std::begin(r.velocity),std::end(r.velocity),[](double v){return !std::isfinite(v)||v!=0.;})){
      ++rejected;Block(Why::MALFORMED);return;
    }
    if(r.boot!=boot || (pinnedSession && r.session!=session)){++rejected;Block(Why::SESSION);return;}
    if(!waiting||r.challenge!=challenge||now<issued||now>=deadline||r.report<=lastReport){
      ++rejected;
      if(!bound&&r.state==uint32_t(c5_test::State::NO_COMMAND)) {waiting=false;reason=Why::WAITING;return;}
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
    } else {if(bound){Block(Why::NATIVE_CLOSED);return;}reason=Why::NO_PERMIT;live=false;}
    lastReport=r.report;++accepted;waiting=false;
  }
  void Send(Request record,Time now) {
    if(waiting)return;
    record.boot=boot;record.challenge=challenge+1;
    const auto sent=send(fd,&record,sizeof(record),MSG_DONTWAIT|MSG_NOSIGNAL);
    if(sent==sizeof(record)){++challenge;issued=now;deadline=now+duration(ticket);waiting=true;}
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
