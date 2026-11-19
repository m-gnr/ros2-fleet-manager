// Explicit experiment entry point; preserves inherited socketpair descriptors.
#include <gz/sim/Server.hh>
#include <gz/sim/ServerConfig.hh>
#include <csignal>
#include <chrono>
#include <thread>
#include <iostream>
volatile std::sig_atomic_t stopping=0;
void stop(int){stopping=1;}
int main(int argc,char **argv) {
  if(argc!=3)return 2;
  std::signal(SIGINT,stop);std::signal(SIGTERM,stop);
  gz::sim::ServerConfig config;
  if(!config.SetSdfFile(argv[1]))return 3;
  config.SetPhysicsEngine(argv[2]);config.SetHeadlessRendering(true);config.SetRenderEngineServer("ogre2");
  gz::sim::Server server(config);
  if(!server.Run(false,0,false))return 4;
  while(!stopping&&server.Running())std::this_thread::sleep_for(std::chrono::milliseconds(20));
  server.Stop();return 0;
}
