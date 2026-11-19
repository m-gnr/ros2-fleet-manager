// Synthetic IPC records only. No physical stop or permit authority is tested here.
#include "Ipc.hh"
#include <cassert>
#include <memory>
#include <iostream>
#include <sys/wait.h>
using namespace c5_split;
struct Fixture {
 int fds[2];Veto::Time t=Veto::Clock::now();std::unique_ptr<Veto> v;
 Fixture(){assert(socketpair(AF_UNIX,SOCK_SEQPACKET|SOCK_NONBLOCK,0,fds)==0);
   v=std::make_unique<Veto>(fds[0],field(std::string(64,'c')),getpid(),.2,.25);}
 ~Fixture(){close(fds[0]);close(fds[1]);}
 Reply request(){Request r{};v->Send(r,t);assert(recv(fds[1],&r,sizeof(r),0)==sizeof(r));
   Reply reply{};reply.boot=r.boot;reply.challenge=r.challenge;reply.report=v->lastReport+1;
   reply.session=field(std::string(64,'b'));reply.context=field(std::string(64,'a'));reply.body=field(std::string(64,'d'));
   reply.command=v->lastCommand+1;reply.state=uint32_t(c5_test::State::ACTIVE);return reply;}
 void send(Reply r){assert(::send(fds[1],&r,sizeof(r),0)==sizeof(r));v->Step(t,100);}
 void healthy(){send(request());assert(v->live&&!v->latched&&v->accepted==1);}
};
int main(){
 {Fixture f;auto start=Veto::Clock::now();for(int i=0;i<10000;++i)f.v->Step(f.t,100);
  assert(Veto::Clock::now()-start<std::chrono::seconds(2));f.healthy();}
 for(auto kind:{"boot","session","context","duplicate","size","nonzero","nan","state","sequence","changedbody"}){
  Fixture f;f.healthy();auto r=f.request();
  if(std::string(kind)=="boot")r.boot.fill('f');
  if(std::string(kind)=="session")r.session.fill('f');
  if(std::string(kind)=="context")r.context.fill('f');
  if(std::string(kind)=="duplicate")--r.challenge;
  if(std::string(kind)=="nonzero")r.velocity[0]=.1;
  if(std::string(kind)=="nan")r.velocity[0]=NAN;
  if(std::string(kind)=="state")r.state=9;
  if(std::string(kind)=="sequence")r.command=0;
  if(std::string(kind)=="changedbody"){--r.command;r.body.fill('f');}
  if(std::string(kind)=="size"){assert(::send(f.fds[1],&r,sizeof(r)-1,0)>0);f.v->Step(f.t,100);}else f.send(r);
  assert(f.v->latched&&!f.v->live);const auto reason=f.v->reason;
  f.v->Accept(r,f.t,true);assert(f.v->latched&&f.v->reason==reason);
 }
 {Fixture f;auto r=f.request();f.v->Accept(r,f.t,false);assert(f.v->reason==Why::CREDENTIALS);}
 {Fixture f;f.healthy();auto r=f.request();f.v->Step(f.t+Veto::duration(.2),100);assert(f.v->reason==Why::TIMEOUT);
  f.v->Accept(r,f.t+Veto::duration(.21),true);assert(f.v->latched);}
 {Fixture f;auto r=f.request();r.state=uint32_t(c5_test::State::NO_COMMAND);
  f.v->Step(f.t+Veto::duration(.3),100);assert(!f.v->live&&!f.v->latched);
  f.v->Accept(r,f.t+Veto::duration(.3),true);assert(!f.v->live&&!f.v->bound);
  f.t+=Veto::duration(.31);f.healthy();}
 {Fixture f;auto r=f.request();f.v->Step(f.t+Veto::duration(.3),100);
  f.v->Accept(r,f.t+Veto::duration(.3),true);assert(f.v->latched&&!f.v->live);}
 {Fixture f;f.healthy();auto r=f.request();r.command=f.v->lastCommand;r.body=f.v->body;
  f.t+=Veto::duration(.19);f.send(r);assert(!f.v->latched);
  f.v->Step(f.t+Veto::duration(.07),100);assert(f.v->reason==Why::TIMEOUT);}
 {Fixture f;close(f.fds[1]);f.fds[1]=-1;f.v->Step(f.t,100);assert(f.v->reason==Why::WORKER_CLOSED);}
 {Fixture f;f.healthy();f.v->Step(f.t,99);assert(f.v->reason==Why::CLOCK_REWOUND);}
 {Fixture f;auto r=f.request();auto child=fork();assert(child>=0);
  if(!child){close(f.fds[0]);assert(::send(f.fds[1],&r,sizeof(r),0)==sizeof(r));_exit(0);}
  int status;waitpid(child,&status,0);f.v->Step(f.t,100);assert(f.v->reason==Why::CREDENTIALS);
 }
 std::cout<<"PASS bounded receive, real SCM_CREDENTIALS, malformed/nonzero, replay/session/context, command expiry, rewind and closed endpoint\n";
}
