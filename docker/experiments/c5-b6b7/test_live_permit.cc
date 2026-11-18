// Component fixtures only. The Gazebo test obtains these records from real FM COMMITs.
#include "TestFixture.hh"
#include <cassert>
#include <iostream>
using namespace c5_test;
std::string U(int n) {return "11111111-1111-1111-1111-11111111111"+std::to_string(n);}
Json LiveProvision() {
  auto p=Provision(); p["live_permits"]=true;p["robot_id"]="r1";
  p["source_session"]="";p["context"]=Json::object();p["permit_id"]="";p["generation"]=0u;
  p["permit_sec"]=2.;p["health_period_sec"]=.05; return p;
}
Json Context() {
  Json identity={{"robot_id","r1"},{"task_id","unit-task"},{"epoch",1u},{"execute_uuid",U(2)},
    {"child_uuid",U(3)},{"executor_session",U(4)},{"fm_session",U(1)},{"permit_id",U(5)},
    {"generation",1u},{"path_hash",std::string(64,'b')},{"map_revision","m1"},{"frame","map"},{"geometry_revision","g1"}};
  Json decision={{"identity",identity},{"request_id",U(6)},{"geometry_digest",std::string(64,'a')},
    {"movement_kind","PICKUP"},{"station_id",""},{"status","RESERVED"},{"reason",""},{"movement_authorized",false}};
  auto child=decision;
  child["child_provenance"]={{"context_id",U(7)},{"nav_uuid",U(8)},{"observer_session",U(9)},
    {"kind",1u},{"sequence",1u},{"terminal_status",0},{"reason","CLIENT_GOAL_HANDLE_ACCEPTED"}};
  child["physical_stop"]="UNKNOWN";child["ownership_release"]=false;
  return {{"operation","INSTALL_ZERO"},{"permit_event_id","permit:"+U(6)},
    {"permit_decision",decision.dump()},{"permit_decision_sha256",Digest(decision.dump())},
    {"child_event_id","child:"+U(7)+":1"},{"child_decision",child.dump()},{"child_decision_sha256",Digest(child.dump())}};
}
Json LiveBody(AuthorizedZero & a,uint64_t sequence,AuthorizedZero::Time now) {
  auto b=Body(a,sequence,now);b["source_session"]=U(1);b["permit_id"]=U(5);
  b["permit_generation"]=1u;b["command_context"]=Context();return b;
}
int main() {
  auto t=AuthorizedZero::Clock::now();AuthorizedZero a(LiveProvision(),t);Lease lease;
  auto first=LiveBody(a,1,t);auto wire=Wire(first);
  assert(a.Receive(wire,t,lease)=="ACCEPTED_ZERO");
  assert(lease.state==State::ACTIVE && a.accepted==1);
  auto receipt=a.receipt;
  assert(a.Receive(wire,t,lease)=="REPLAY" && a.receipt==receipt);
  auto bad=LiveBody(a,2,t);bad["source_session"]=U(2);
  assert(a.Receive(Wire(bad),t,lease)=="SESSION");
  bad=LiveBody(a,2,t);bad["permit_generation"]=2u;
  assert(a.Receive(Wire(bad),t,lease)=="PERMIT");
  for (const auto & field : {"epoch","child_uuid","path_hash","executor_session"}) {
    bad=LiveBody(a,2,t);auto p=StrictJson(bad["command_context"]["permit_decision"].get<std::string>());
    p["identity"][field]=field==std::string("epoch") ? Json(2u) : Json(U(9));
    bad["command_context"]["permit_decision"]=p.dump();
    bad["command_context"]["permit_decision_sha256"]=Digest(p.dump());
    assert(a.Receive(Wire(bad),t,lease)=="CONTEXT" && a.receipt==receipt);
  }
  bad=LiveBody(a,2,t);assert(a.Receive(Wire(bad,false),t,lease)=="UNAUTHENTICATED");
  auto snapshot=a.Snapshot(t,lease);auto status=StrictJson(snapshot["native_status"]["body"]);
  assert(status["context_sha256"]==Digest(Context().dump()));
  assert(status["command_sha256"]==Digest(first.dump()));
  assert(status["source_session"]==U(1) && status["generation"]==1);
  assert(status["movement_authorized"]==false && status["ownership_release"]==false);
  snapshot["sim_ns"]=10; snapshot["target_linear"]=0.; snapshot["target_angular"]=0.;
  snapshot["joint_commands"]={{0.},{0.}};
  a.AttachHealth(snapshot,t);
  auto health=StrictJson(snapshot["native_health"]["body"]);
  assert(health["native_status"]==snapshot["native_status"]);
  assert(health["joint_commands"]==snapshot["joint_commands"] && health["update_sequence"]==1);
  a.AttachHealth(snapshot,t+std::chrono::milliseconds(10));assert(!snapshot.contains("native_health"));
  a.AttachHealth(snapshot,t+std::chrono::milliseconds(50));
  assert(StrictJson(snapshot["native_health"]["body"])["update_sequence"]==2);
  assert(status["command_sha256"]==Digest(first.dump()));
  auto oldProvision=LiveProvision();oldProvision.erase("health_period_sec");
  AuthorizedZero noHealth(oldProvision,t);auto oldSnapshot=noHealth.Snapshot(t,lease);
  noHealth.AttachHealth(oldSnapshot,t);assert(!oldSnapshot.contains("native_health"));
  auto revoke=LiveBody(a,2,t);revoke["command_context"]["operation"]="REVOKE_ZERO";
  assert(a.Receive(Wire(revoke),t,lease)=="PERMIT_REVOKED");
  assert(lease.state==State::BLOCKED_REARM && a.receipt==receipt);
  auto late=LiveBody(a,3,t);assert(a.Receive(Wire(late),t,lease)=="BLOCKED_REARM");
  AuthorizedZero partial(LiveProvision(),t);Lease lp;
  auto before=LiveBody(partial,1,t);before["command_context"]["operation"]="REVOKE_ZERO";
  assert(partial.Receive(Wire(before),t,lp)=="PERMIT_REVOKED");
  assert(partial.Receive(Wire(LiveBody(partial,2,t)),t,lp)=="BLOCKED_REARM");
  AuthorizedZero restarted(LiveProvision(),t);Lease lr;
  assert(restarted.Receive(wire,t,lr)=="SESSION");
  assert(restarted.Receive(Wire(LiveBody(restarted,1,t)),t,lr)=="ACCEPTED_ZERO");
  restarted.Tick(t+std::chrono::milliseconds(250),1,lr);
  assert(lr.state==State::TIMED_OUT);
  assert(restarted.Receive(Wire(LiveBody(restarted,2,t)),t+std::chrono::milliseconds(250),lr)=="BLOCKED_REARM");
  AuthorizedZero nonzero(LiveProvision(),t);Lease ln;
  bad=LiveBody(nonzero,1,t);bad["velocity"][0]=.2;
  assert(nonzero.Receive(Wire(bad),t,ln)=="NONZERO_DISABLED" && ln.state==State::BLOCKED_REARM);
  assert(nonzero.Receive(Wire(LiveBody(nonzero,2,t)),t,ln)=="BLOCKED_REARM");
  const auto inhibited=nonzero.Snapshot(t,ln);
  assert(inhibited["inhibition_reason"]=="NONZERO_DISABLED");
  assert(inhibited["inhibited_command_sha256"]==Digest(bad.dump()));
  assert(StrictJson(inhibited["native_status"]["body"])["command_sha256"]=="");
  AuthorizedZero expired(LiveProvision(),t);Lease le;
  assert(expired.Receive(Wire(LiveBody(expired,1,t)),t,le)=="ACCEPTED_ZERO");
  expired.Tick(t+std::chrono::seconds(2),1,le);assert(le.state==State::BLOCKED_REARM);
  std::cout<<"PASS live context, exact decision digests, native receipt, revoke-before-install, sessions, generation, replay, nonzero and expiry\n";
}
