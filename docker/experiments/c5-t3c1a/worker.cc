// Separate zero-only verifier. Never writes ECM/joints or grants physical motion.
#include "Ipc.hh"
#include "../c5-b6b7/AuthorizedZero.hh"
#include <gz/transport/Node.hh>
#include <gz/msgs/stringmsg.pb.h>
#include <gz/msgs/boolean.pb.h>
#include <gz/msgs/odometry.pb.h>
#include <gz/msgs/pose_v.pb.h>
#include <gz/msgs/Utility.hh>
#include <gz/math/Quaternion.hh>
#include <mutex>
#include <thread>
#include <csignal>
#include <fstream>
#include <iostream>
using namespace c5_test;
volatile std::sig_atomic_t stopping=0;
void stop(int){stopping=1;}
int main(int argc,char **argv) {
  if(argc!=2)return 2;
  std::signal(SIGINT,stop);std::signal(SIGTERM,stop);
  Json config;{std::ifstream file(argv[1]);file>>config;}
  const auto boot=c5_split::field(config.at("boot"));const int fd=config.at("fd");
  auto auth=AuthorizedZero::Load(config.at("provision"),AuthorizedZero::Clock::now());
  Lease lease;std::mutex lock;gz::transport::Node node;
  const std::string ns=config.at("namespace");
  auto statePub=node.Advertise<gz::msgs::StringMsg>(ns+"/native_actuator");
  auto odomPub=node.Advertise<gz::msgs::Odometry>(ns+"/odom");
  auto tfPub=node.Advertise<gz::msgs::Pose_V>(ns+"/tf");
  node.Subscribe(ns+"/authorized_zero",std::function<void(const gz::msgs::StringMsg &)>([&](const auto & m){
    std::lock_guard<std::mutex> guard(lock);auth->Receive(m.data(),AuthorizedZero::Clock::now(),lease);
  }));
  node.Subscribe("/model/"+config.at("robot_id").get<std::string>()+"/enable",
    std::function<void(const gz::msgs::Boolean &)>([&](const auto &){std::lock_guard<std::mutex> guard(lock);lease.Block();}));
  c5_split::Reply previous{};bool havePrevious=false,closed=false;int64_t lastOdom=0,sim=-1;
  std::ofstream audit(config.at("audit").get<std::string>(),std::ios::app);
  audit<<Json({{"event","START"},{"pid",getpid()},{"receiver_session",auth->session},
    {"writer_boot",c5_split::string(boot)},{"nonzero_enabled",false}}).dump()<<std::endl;
  while(!stopping) {
    c5_split::Request request{};
    auto got=closed?-1:recv(fd,&request,sizeof(request),MSG_DONTWAIT|MSG_TRUNC);
    if(got==0)break;
    if(got==sizeof(request)&&request.magic==c5_split::Magic&&request.boot==boot) {
      sim=request.sim_ns;Json state;c5_split::Reply reply{};
      {
        std::lock_guard<std::mutex> guard(lock);auto now=AuthorizedZero::Clock::now();auth->Tick(now,sim,lease);
        state=auth->Snapshot(now,lease);auto s=StrictJson(state["native_status"]["body"]);
        reply.boot=boot;reply.challenge=request.challenge;reply.report=s.at("report_sequence");reply.command=s.at("sequence");
        reply.session=c5_split::field(auth->session);reply.context=c5_split::field(s.at("context_sha256"));
        reply.body=c5_split::field(s.at("command_sha256"));reply.state=uint32_t(lease.state);
      }
      state["source_stage"]="NATIVE_VERIFIER_PROCESS";state["writer_boot"]=c5_split::string(boot);
      state["sim_ns"]=sim; // Observed writer frame time, not an independent physics claim.
      gz::msgs::StringMsg message;message.set_data(state.dump());statePub.Publish(message);
      if(request.odom_sim_ns>lastOdom) {
        lastOdom=request.odom_sim_ns;gz::msgs::Odometry odom;
        odom.mutable_header()->mutable_stamp()->set_sec(lastOdom/1000000000);
        odom.mutable_header()->mutable_stamp()->set_nsec(lastOdom%1000000000);
        auto frame=odom.mutable_header()->add_data();frame->set_key("frame_id");frame->add_value(config.at("odom_frame"));
        frame=odom.mutable_header()->add_data();frame->set_key("child_frame_id");frame->add_value(config.at("child_frame"));
        odom.mutable_pose()->mutable_position()->set_x(request.odom[0]);odom.mutable_pose()->mutable_position()->set_y(request.odom[1]);
        gz::msgs::Set(odom.mutable_pose()->mutable_orientation(),gz::math::Quaterniond(0,0,request.odom[2]));
        odom.mutable_twist()->mutable_linear()->set_x(request.odom[3]);odom.mutable_twist()->mutable_angular()->set_z(request.odom[4]);
        odomPub.Publish(odom);gz::msgs::Pose_V tf;auto pose=tf.add_pose();pose->mutable_header()->CopyFrom(odom.header());
        pose->mutable_position()->CopyFrom(odom.pose().position());pose->mutable_orientation()->CopyFrom(odom.pose().orientation());tfPub.Publish(tf);
      }
      // Explicit negative fixture only. It can corrupt/withhold replies, never open movement.
      std::string mode;try{std::ifstream file(config.at("fault_file").get<std::string>());Json fault;if(file>>fault)mode=fault.value("mode","");}catch(...){}
      if(mode=="ipc_close"){close(fd);closed=true;}
      else {
        auto sendReply=reply;
        if(mode=="wrong_context")sendReply.context.fill('f');
        if(mode=="wrong_session")sendReply.session.fill('f');
        if(mode=="wrong_boot")sendReply.boot.fill('f');
        if(mode=="duplicate"&&havePrevious)sendReply=previous;
        if(mode=="nonzero")sendReply.velocity[0]=1.;
        if(mode=="delayed")std::this_thread::sleep_for(std::chrono::milliseconds(350));
        const auto length=mode=="corrupt"?sizeof(sendReply)-1:sizeof(sendReply);
        (void)send(fd,&sendReply,length,MSG_DONTWAIT|MSG_NOSIGNAL);
      }
      if(!mode.empty())audit<<Json({{"event","NEGATIVE_FIXTURE"},{"mode",mode},{"challenge",request.challenge},
        {"command_sequence",reply.command},{"pid",getpid()}}).dump()<<std::endl;
      previous=reply;havePrevious=true;
    }
    {std::lock_guard<std::mutex> guard(lock);auth->Tick(AuthorizedZero::Clock::now(),sim,lease);}
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
  }
  audit<<Json({{"event","STOP"},{"pid",getpid()}}).dump()<<std::endl;return 0;
}
