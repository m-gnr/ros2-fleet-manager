// Synthetic protocol/component fixtures only; no physical health/stop claims.
#include "Health.hh"
#include "../c5-b6b7/TestFixture.hh"
#include <cassert>
#include <memory>
#include <iostream>
using namespace c5_split;
using namespace c5_test;
struct Fixture {
 int pair[2];Veto::Time t=Veto::Clock::now();std::unique_ptr<Veto> v;
 Fixture(){assert(socketpair(AF_UNIX,SOCK_SEQPACKET|SOCK_NONBLOCK,0,pair)==0);
  v=std::make_unique<Veto>(pair[0],field(std::string(64,'a')),getpid(),.2,.25,.35);v->Step(t,100);}
 ~Fixture(){close(pair[0]);close(pair[1]);}
 Reply next(){Request request{};v->Send(request,t);assert(recv(pair[1],&request,sizeof(request),0)==sizeof(request));
  Reply r{};r.boot=v->boot;r.session=field(std::string(64,'b'));r.context=field(std::string(64,'c'));r.body=field(std::string(64,'d'));
  r.command=v->lastCommand+1;r.report=v->lastReport+1;r.challenge=v->challenge;r.state=1;return r;}
 void current(){auto r=next();r.health.session=field(std::string(64,'e'));r.health.digest=field(std::string(64,'f'));
  r.health.sequence=1;r.health.ticket=v->healthTicket;r.health.status=2;r.health.remaining_ns=300000000;
  v->Accept(r,t,true);assert(v->healthSeen&&v->live&&!v->latched);}
};
int main(){
 // A late initial NO_COMMAND response must not cancel the newer in-flight
 // challenge. Neither response is accepted out of order, and ACTIVE still latches.
 {Fixture f;auto old=f.next();old.state=0;old.command=0;old.body={};
  f.t+=Veto::duration(.21);f.v->Step(f.t,100);assert(!f.v->waiting&&!f.v->latched);
  auto current=f.next();f.v->Accept(old,f.t,true);
  assert(f.v->waiting&&!f.v->latched&&f.v->accepted==0&&f.v->ipcTrace.replay_checks==CHALLENGE);
  f.v->Accept(current,f.t,true);assert(!f.v->latched&&f.v->accepted==1&&f.v->reason==Why::HEALTH_WAITING);
 }
 for(auto check:{NOT_WAITING,CHALLENGE,CLOCK_BEFORE_ISSUED,TICKET_EXPIRED,REPORT_SEQUENCE,COMMAND_SEQUENCE,COMMAND_BODY}){
  Fixture f;f.current();auto advance=f.next();advance.health=f.v->lastHealth;f.v->Accept(advance,f.t,true);
  auto r=f.next();r.health=f.v->lastHealth;auto now=f.t;
  if(check==NOT_WAITING)f.v->waiting=false;
  if(check==CHALLENGE)--r.challenge;
  if(check==CLOCK_BEFORE_ISSUED)now-=Veto::duration(.01);
  if(check==TICKET_EXPIRED)now+=Veto::duration(.2);
  if(check==REPORT_SEQUENCE)r.report=f.v->lastReport;
  if(check==COMMAND_SEQUENCE)r.command=f.v->lastCommand-1;
  if(check==COMMAND_BODY){r.command=f.v->lastCommand;r.body.fill('f');}
  f.v->Accept(r,now,true);assert(f.v->latched&&f.v->reason==Why::REPLAY);
  assert(f.v->ipcTrace.replay_checks==uint32_t(check));auto first=f.v->ipcTrace;
  f.v->Accept(r,now+Veto::duration(.01),true);assert(f.v->ipcTrace.checked_ns==first.checked_ns);
 }
 {Fixture f;auto r=f.next();f.v->Accept(r,f.t,true);assert(!f.v->live&&!f.v->latched&&f.v->reason==Why::HEALTH_WAITING);}
 for(auto mode:{"missing","deny","invalid","session","replay","changed"}){
  Fixture f;f.current();auto r=f.next();r.health=f.v->lastHealth;
  if(std::string(mode)=="missing")r.health={};
  if(std::string(mode)=="deny"){++r.health.sequence;r.health.status=1;}
  if(std::string(mode)=="invalid")r.health.status=3;
  if(std::string(mode)=="session"){++r.health.sequence;r.health.session.fill('a');}
  if(std::string(mode)=="replay")r.health.sequence=0;
  if(std::string(mode)=="changed")r.health.digest.fill('a');
  f.v->Accept(r,f.t,true);assert(f.v->latched&&!f.v->live);f.v->Accept(r,f.t,true);assert(f.v->latched);
 }
 {Fixture f;f.current();auto original=f.v->healthDeadline;f.t+=Veto::duration(.1);auto r=f.next();r.health=f.v->lastHealth;
  f.v->Accept(r,f.t,true);assert(f.v->healthDeadline==original);f.v->Step(f.t+Veto::duration(.21),100);assert(f.v->latched&&f.v->reason==Why::HEALTH_EXPIRED);}
 {Fixture f;f.current();auto original=f.v->healthDeadline;auto r=f.next();r.health=f.v->lastHealth;++r.health.sequence;
  f.v->Accept(r,f.t,true);assert(f.v->healthDeadline==original);}
 char path[]="/tmp/c5-health-test-XXXXXX";int fd=mkstemp(path);assert(fd>=0);auto raw=Provision().dump();assert(write(fd,raw.data(),raw.size())==ssize_t(raw.size()));close(fd);
 c5_health::Codec codec(path);unlink(path);
 Json native={{"receiver_session",std::string(64,'b')},{"context_sha256",std::string(64,'c')}};
 Json budgets={{"tf",1000000000}};
 auto body=[&](){return Json{{"robot_id","r1"},{"observer_session",std::string(64,'e')},{"sequence",1u},
  {"receiver_session",std::string(64,'b')},{"writer_boot",std::string(64,'a')},{"context_sha256",std::string(64,'c')},
  {"identity_sha256",std::string(64,'d')},{"ticket",1u},{"observations_current",true},{"remaining_ns",300000000},
  {"sources",{{"tf",{{"measurement_id",std::string(64,'f')},{"stamp_ns",100u},{"remaining_ns",300000000},{"source_identity","UNKNOWN"}}}}},
  {"reasons",Json::array()},{"movement_eligible",false},{"physical_stop","UNKNOWN"},{"ownership_release",false}};};
 auto wire=[&](Json p){auto b=p.dump();return Json{{"body",b},{"mac",codec.mac(c5_health::VetoDomain,b)}}.dump();};
 for(auto mode:{"mac","context","session","eligibility","source","duplicate","rejuvenation","old"}){
  c5_health::Receiver receiver(codec,"r1",std::string(64,'a'),budgets);auto p=body();auto original=wire(p);
  receiver.receive(original,native,std::string(64,'d'));assert(receiver.latest.status==2&&!receiver.closed);
  receiver.receive(original,native,std::string(64,'d'));assert(receiver.received==1);
  p["sequence"]=2u;
  if(std::string(mode)=="context")p["context_sha256"]=std::string(64,'a');
  if(std::string(mode)=="session")p["observer_session"]=std::string(64,'a');
  if(std::string(mode)=="eligibility")p["movement_eligible"]=true;
  if(std::string(mode)=="source")p["sources"]=Json::object();
  if(std::string(mode)=="duplicate"){p["sequence"]=1u;p["ticket"]=2u;}
  if(std::string(mode)=="old")p["sequence"]=0u;
  if(std::string(mode)=="rejuvenation")p["sources"]["tf"]["remaining_ns"]=400000000;
  auto text=wire(p);if(std::string(mode)=="mac")text=codec.sign(p).dump();
  receiver.receive(text,native,std::string(64,'d'));assert(receiver.closed&&receiver.latest.status==3);
  receiver.receive(original,native,std::string(64,'d'));assert(receiver.closed);
 }
 std::cout<<"PASS veto-only health MAC/context/source cursor fencing and writer-local expiry; no movement API\n";
}
