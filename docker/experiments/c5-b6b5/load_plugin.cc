#include <gz/sim/SystemLoader.hh>
#include <gz/sim/System.hh>
#include <gz/common/SystemPaths.hh>
#include <cassert>
#include <fstream>
#include <iostream>
int main() {
  gz::common::SystemPaths paths;
  paths.SetPluginPathEnv("IGN_GAZEBO_SYSTEM_PLUGIN_PATH");
  auto library = paths.FindSharedLibrary("c5-actuator-diff-drive");
  if (library.empty()) return 3;
  gz::sim::SystemLoader loader;
  auto loaded = loader.LoadPlugin("c5-actuator-diff-drive", "gz::sim::systems::DiffDrive", nullptr);
  assert(loaded.has_value());
  auto instance = loaded.value();
  assert(instance && instance->QueryInterface<gz::sim::ISystemConfigure>());
  assert(instance->QueryInterface<gz::sim::ISystemPreUpdate>());
  assert(instance->QueryInterface<gz::sim::ISystemPostUpdate>());
  std::cout << "PASS loaded=" << library << "\n";
  std::ifstream maps("/proc/self/maps");
  std::string line;
  while (std::getline(maps, line)) if (line.find("c5-actuator-diff-drive") != std::string::npos)
    std::cout << line << '\n';
}
