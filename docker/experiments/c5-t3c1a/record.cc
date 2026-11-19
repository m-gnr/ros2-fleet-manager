// Read-only evidence sink; physics sends with MSG_DONTWAIT and never waits for this process.
#include "Ipc.hh"
#include <nlohmann/json.hpp>
#include <fstream>
#include <thread>
#include <csignal>
volatile std::sig_atomic_t stopping=0;
void stop(int){stopping=1;}
int main(int argc,char **argv){
  if(argc<4||(argc-2)%2)return 2;std::signal(SIGINT,stop);std::signal(SIGTERM,stop);
  std::ofstream log(argv[1]);
  while(!stopping){
    for(int i=2;i<argc;i+=2){int fd=std::stoi(argv[i]);
      for(int j=0;j<32;++j){c5_split::Request r{};auto n=recv(fd,&r,sizeof(r),MSG_DONTWAIT|MSG_TRUNC);
        if(n<0)break;if(n==0)break;if(n!=sizeof(r)||r.magic!=c5_split::Magic)return 3;
        log<<nlohmann::json({{"robot_id",argv[i+1]},{"writer_boot",c5_split::string(r.boot)},
          {"pre_iteration",r.iteration},{"post_completed_physics_updates",r.physics_steps},{"sim_ns",r.sim_ns},
          {"writer_steady_ns",r.steady_ns},{"selection_reason",c5_split::name(c5_split::Why(r.reason))},
          {"latched",bool(r.latched)},{"accepted",r.accepted},{"rejected",r.rejected},{"command_sequence",r.command},
          {"native_session",c5_split::token(r.native_session)?c5_split::string(r.native_session):""},
          {"context_sha256",c5_split::token(r.context)?c5_split::string(r.context):""},
          {"command_sha256",c5_split::token(r.body)?c5_split::string(r.body):""},
          {"pre_selected_joint_targets",{r.selected[0],r.selected[1]}},
          {"post_actual_joint_velocity",{r.joint_velocity[0],r.joint_velocity[1]}},
          {"post_actual_velocity_known",bool(r.actual_velocity_known)},
          {"post_actual_body_velocity",{r.body_velocity[0],r.body_velocity[1],r.body_velocity[2],r.body_velocity[3],r.body_velocity[4],r.body_velocity[5]}},
          {"post_world_position",{r.position[0],r.position[1],r.position[2]}}}).dump()<<'\n';
      }
    }
    log.flush();std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }return 0;
}
