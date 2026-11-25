/*
 * Copyright (C) 2018 Open Source Robotics Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

#include "DiffDrive.hh"
#include "Lease.hh"
#ifdef C5_AUTH_ZERO_ONLY
#include "../c5-b6b7/AuthorizedZero.hh"
#endif
#ifdef C5_SPLIT_ZERO_ONLY
#include "../c5-t3c1a/Ipc.hh"
#include "../c5-t3c1a/Evidence.hh"
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/Pose.hh>
#include <gz/sim/components/LinearVelocity.hh>
#include <gz/sim/components/AngularVelocity.hh>
#endif

#include <gz/msgs/odometry.pb.h>
#include <gz/msgs/stringmsg.pb.h>

#include <limits>
#include <cmath>
#include <stdexcept>
#include <mutex>
#include <chrono>
#include <set>
#include <string>
#include <sstream>
#include <vector>

#include <gz/common/Profiler.hh>
#include <gz/math/DiffDriveOdometry.hh>
#include <gz/math/Quaternion.hh>
#include <gz/math/SpeedLimiter.hh>
#include <gz/plugin/Register.hh>
#include <gz/transport/Node.hh>

#include "gz/sim/components/CanonicalLink.hh"
#include "gz/sim/components/JointPosition.hh"
#include "gz/sim/components/JointVelocityCmd.hh"
#include "gz/sim/Link.hh"
#include "gz/sim/Model.hh"
#include "gz/sim/Util.hh"

using namespace gz;
using namespace gz::sim;
using namespace systems;

/// \brief Velocity command.
struct Commands
{
  /// \brief Linear velocity.
  double lin;

  /// \brief Angular velocity.
  double ang;

  Commands() : lin(0.0), ang(0.0) {}
};

class ignition::gazebo::systems::DiffDrivePrivate
{
  /// \brief Callback for velocity subscription
  /// \param[in] _msg Velocity message
  public: void OnCmdVel(const msgs::Twist &_msg);
#ifdef C5_AUTH_ZERO_ONLY
  public: void OnAuthorizedZero(const msgs::StringMsg &_msg);
  public: std::unique_ptr<c5_test::AuthorizedZero> authorization;
#endif

#ifdef C5_SPLIT_ZERO_ONLY
  public: std::unique_ptr<c5_split::Veto> veto;
  public: c5_split::Request splitRecord{};
  public: int traceFd{-1};
  public: std::chrono::steady_clock::time_point lastTrace{};
  public: double tracePeriod{};
#endif

  /// \brief Callback for enable/disable subscription
  /// \param[in] _msg Boolean message
  public: void OnEnable(const msgs::Boolean &_msg);

  /// \brief Update odometry and publish an odometry message.
  /// \param[in] _info System update information.
  /// \param[in] _ecm The EntityComponentManager of the given simulation
  /// instance.
  public: void UpdateOdometry(const UpdateInfo &_info,
    const EntityComponentManager &_ecm);

  /// \brief Update the linear and angular velocities.
  /// \param[in] _info System update information.
  /// \param[in] _ecm The EntityComponentManager of the given simulation
  /// instance.
  public: void UpdateVelocity(const UpdateInfo &_info,
    const EntityComponentManager &_ecm);

  /// \brief Ignition communication node.
  public: transport::Node node;

  /// \brief Entity of the left joint
  public: std::vector<Entity> leftJoints;

  /// \brief Entity of the right joint
  public: std::vector<Entity> rightJoints;

  /// \brief Name of left joint
  public: std::vector<std::string> leftJointNames;

  /// \brief Name of right joint
  public: std::vector<std::string> rightJointNames;

  /// \brief Calculated speed of left joint
  public: double leftJointSpeed{0};

  /// \brief Calculated speed of right joint
  public: double rightJointSpeed{0};

  /// \brief Distance between wheels
  public: double wheelSeparation{1.0};

  /// \brief Wheel radius
  public: double wheelRadius{0.2};

  /// \brief Model interface
  public: Model model{kNullEntity};

  /// \brief The model's canonical link.
  public: Link canonicalLink{kNullEntity};

  /// \brief Update period calculated from <odom__publish_frequency>.
  public: std::chrono::steady_clock::duration odomPubPeriod{0};

  /// \brief Last sim time odom was published.
  public: std::chrono::steady_clock::duration lastOdomPubTime{0};

  /// \brief Diff drive odometry.
  public: math::DiffDriveOdometry odom;

  /// \brief Diff drive odometry message publisher.
  public: transport::Node::Publisher odomPub;

  /// \brief Diff drive tf message publisher.
  public: transport::Node::Publisher tfPub;

  /// Isolated proof interface: reports the actuator target actually consumed by PreUpdate.
  public: transport::Node::Publisher actuatorStatePub;
  public: std::string actuatorStateTopic;
  public: c5_test::Lease lease;

  /// \brief Linear velocity limiter.
  public: std::unique_ptr<math::SpeedLimiter> limiterLin;

  /// \brief Angular velocity limiter.
  public: std::unique_ptr<math::SpeedLimiter> limiterAng;

  /// \brief Previous control command.
  public: Commands last0Cmd;

  /// \brief Previous control command to last0Cmd.
  public: Commands last1Cmd;

  /// \brief Last target velocity requested.
  public: msgs::Twist targetVel;
  public: std::chrono::steady_clock::time_point received{};
  public: bool haveCommand{false};
  public: double timeout{0.25};

  /// \brief Enable/disable state of the controller.
  public: bool enabled{false};

  /// \brief A mutex to protect the target velocity command.
  public: std::mutex mutex;

  /// \brief frame_id from sdf.
  public: std::string sdfFrameId;

  /// \brief child_frame_id from sdf.
  public: std::string sdfChildFrameId;
};

//////////////////////////////////////////////////
DiffDrive::DiffDrive()
  : dataPtr(std::make_unique<DiffDrivePrivate>())
{
}

//////////////////////////////////////////////////
void DiffDrive::Configure(const Entity &_entity,
    const std::shared_ptr<const sdf::Element> &_sdf,
    EntityComponentManager &_ecm,
    EventManager &/*_eventMgr*/)
{
  this->dataPtr->model = Model(_entity);
  this->dataPtr->timeout = _sdf->Get<double>("velocity_command_timeout", 0.25).first;
  this->dataPtr->actuatorStateTopic = _sdf->Get<std::string>("actuator_state_topic", "").first;
  #ifndef C5_SPLIT_ZERO_ONLY
  if (!this->dataPtr->actuatorStateTopic.empty())
    this->dataPtr->actuatorStatePub = this->dataPtr->node.Advertise<msgs::StringMsg>(
        this->dataPtr->actuatorStateTopic);
  #endif
  if (!std::isfinite(this->dataPtr->timeout) || this->dataPtr->timeout <= 0)
    throw std::invalid_argument("velocity_command_timeout must be positive and finite");
#ifdef C5_AUTH_ZERO_ONLY
  if (!_sdf->HasElement("authorization_file") || this->dataPtr->actuatorStateTopic.empty())
    throw std::invalid_argument("Explicit zero-only authorization file and state topic required");
  this->dataPtr->authorization = c5_test::AuthorizedZero::Load(
    _sdf->Get<std::string>("authorization_file"), std::chrono::steady_clock::now());
#endif

#ifdef C5_SPLIT_ZERO_ONLY
  this->dataPtr->veto=std::make_unique<c5_split::Veto>(
    _sdf->Get<int>("split_fd"),c5_split::field(_sdf->Get<std::string>("writer_boot")),
    _sdf->Get<int>("worker_pid"),_sdf->Get<double>("ticket_sec"),_sdf->Get<double>("lease_sec")
#ifdef C5_SPLIT_HEALTH_VETO
    ,_sdf->Get<double>("health_budget_sec")
#endif
  );
  this->dataPtr->traceFd=_sdf->Get<int>("trace_fd");
  this->dataPtr->tracePeriod=_sdf->Get<double>("trace_period_sec");
  if(fcntl(this->dataPtr->traceFd,F_GETFL)<0||!(fcntl(this->dataPtr->traceFd,F_GETFL)&O_NONBLOCK)||
      !std::isfinite(this->dataPtr->tracePeriod)||this->dataPtr->tracePeriod<=0)
    throw std::invalid_argument("Nonblocking trace and explicit profile period required");
#endif
  // Get the canonical link
  std::vector<Entity> links = _ecm.ChildrenByComponents(
      this->dataPtr->model.Entity(), components::CanonicalLink());
  if (!links.empty())
    this->dataPtr->canonicalLink = Link(links[0]);

  if (!this->dataPtr->model.Valid(_ecm))
  {
    ignerr << "DiffDrive plugin should be attached to a model entity. "
           << "Failed to initialize." << std::endl;
    return;
  }

  // Ugly, but needed because the sdf::Element::GetElement is not a const
  // function and _sdf is a const shared pointer to a const sdf::Element.
  auto ptr = const_cast<sdf::Element *>(_sdf.get());

  // Get params from SDF
  sdf::ElementPtr sdfElem = ptr->GetElement("left_joint");
  while (sdfElem)
  {
    this->dataPtr->leftJointNames.push_back(sdfElem->Get<std::string>());
    sdfElem = sdfElem->GetNextElement("left_joint");
  }
  sdfElem = ptr->GetElement("right_joint");
  while (sdfElem)
  {
    this->dataPtr->rightJointNames.push_back(sdfElem->Get<std::string>());
    sdfElem = sdfElem->GetNextElement("right_joint");
  }

  this->dataPtr->wheelSeparation = _sdf->Get<double>("wheel_separation",
      this->dataPtr->wheelSeparation).first;
  this->dataPtr->wheelRadius = _sdf->Get<double>("wheel_radius",
      this->dataPtr->wheelRadius).first;

  // Instantiate the speed limiters.
  this->dataPtr->limiterLin = std::make_unique<math::SpeedLimiter>();
  this->dataPtr->limiterAng = std::make_unique<math::SpeedLimiter>();

  // Parse speed limiter parameters.

  // Min Velocity
  if (_sdf->HasElement("min_velocity"))
  {
    const double minVel = _sdf->Get<double>("min_velocity");
    this->dataPtr->limiterLin->SetMinVelocity(minVel);
    this->dataPtr->limiterAng->SetMinVelocity(minVel);
  }
  if (_sdf->HasElement("min_linear_velocity"))
  {
    const double minLinVel = _sdf->Get<double>("min_linear_velocity");
    this->dataPtr->limiterLin->SetMinVelocity(minLinVel);
  }
  if (_sdf->HasElement("min_angular_velocity"))
  {
    const double minAngVel = _sdf->Get<double>("min_angular_velocity");
    this->dataPtr->limiterAng->SetMinVelocity(minAngVel);
  }

  // Max Velocity
  if (_sdf->HasElement("max_velocity"))
  {
    const double maxVel = _sdf->Get<double>("max_velocity");
    this->dataPtr->limiterLin->SetMaxVelocity(maxVel);
    this->dataPtr->limiterAng->SetMaxVelocity(maxVel);
  }
  if (_sdf->HasElement("max_linear_velocity"))
  {
    const double maxLinVel = _sdf->Get<double>("max_linear_velocity");
    this->dataPtr->limiterLin->SetMaxVelocity(maxLinVel);
  }
  if (_sdf->HasElement("max_angular_velocity"))
  {
    const double maxAngVel = _sdf->Get<double>("max_angular_velocity");
    this->dataPtr->limiterAng->SetMaxVelocity(maxAngVel);
  }

  // Min Acceleration
  if (_sdf->HasElement("min_acceleration"))
  {
    const double minAccel = _sdf->Get<double>("min_acceleration");
    this->dataPtr->limiterLin->SetMinAcceleration(minAccel);
    this->dataPtr->limiterAng->SetMinAcceleration(minAccel);
  }
  if (_sdf->HasElement("min_linear_acceleration"))
  {
    const double minLinAccel = _sdf->Get<double>("min_linear_acceleration");
    this->dataPtr->limiterLin->SetMinAcceleration(minLinAccel);
  }
  if (_sdf->HasElement("min_angular_acceleration"))
  {
    const double minAngAccel = _sdf->Get<double>("min_angular_acceleration");
    this->dataPtr->limiterAng->SetMinAcceleration(minAngAccel);
  }

  // Max Acceleration
  if (_sdf->HasElement("max_acceleration"))
  {
    const double maxAccel = _sdf->Get<double>("max_acceleration");
    this->dataPtr->limiterLin->SetMaxAcceleration(maxAccel);
    this->dataPtr->limiterAng->SetMaxAcceleration(maxAccel);
  }
  if (_sdf->HasElement("max_linear_acceleration"))
  {
    const double maxLinAccel = _sdf->Get<double>("max_linear_acceleration");
    this->dataPtr->limiterLin->SetMaxAcceleration(maxLinAccel);
  }
  if (_sdf->HasElement("max_angular_acceleration"))
  {
    const double maxAngAccel = _sdf->Get<double>("max_angular_acceleration");
    this->dataPtr->limiterAng->SetMaxAcceleration(maxAngAccel);
  }

  // Min Jerk
  if (_sdf->HasElement("min_jerk"))
  {
    const double minJerk = _sdf->Get<double>("min_jerk");
    this->dataPtr->limiterLin->SetMinJerk(minJerk);
    this->dataPtr->limiterAng->SetMinJerk(minJerk);
  }
  if (_sdf->HasElement("min_linear_jerk"))
  {
    const double minLinJerk = _sdf->Get<double>("min_linear_jerk");
    this->dataPtr->limiterLin->SetMinJerk(minLinJerk);
  }
  if (_sdf->HasElement("min_angular_jerk"))
  {
    const double minAngJerk = _sdf->Get<double>("min_angular_jerk");
    this->dataPtr->limiterAng->SetMinJerk(minAngJerk);
  }

  // Max Jerk
  if (_sdf->HasElement("max_jerk"))
  {
    const double maxJerk = _sdf->Get<double>("max_jerk");
    this->dataPtr->limiterLin->SetMaxJerk(maxJerk);
    this->dataPtr->limiterAng->SetMaxJerk(maxJerk);
  }
  if (_sdf->HasElement("max_linear_jerk"))
  {
    const double maxLinJerk = _sdf->Get<double>("max_linear_jerk");
    this->dataPtr->limiterLin->SetMaxJerk(maxLinJerk);
  }
  if (_sdf->HasElement("max_angular_jerk"))
  {
    const double maxAngJerk = _sdf->Get<double>("max_angular_jerk");
    this->dataPtr->limiterAng->SetMaxJerk(maxAngJerk);
  }

  double odomFreq = _sdf->Get<double>("odom_publish_frequency", 50).first;
  if (odomFreq > 0)
  {
    std::chrono::duration<double> odomPer{1 / odomFreq};
    this->dataPtr->odomPubPeriod =
      std::chrono::duration_cast<std::chrono::steady_clock::duration>(odomPer);
  }

  // Setup odometry.
  this->dataPtr->odom.SetWheelParams(this->dataPtr->wheelSeparation,
      this->dataPtr->wheelRadius, this->dataPtr->wheelRadius);

  #ifndef C5_SPLIT_ZERO_ONLY
  // Subscribe to commands
  std::vector<std::string> topics;
  if (_sdf->HasElement("topic"))
  {
    topics.push_back(_sdf->Get<std::string>("topic"));
  }
  topics.push_back("/model/" + this->dataPtr->model.Name(_ecm) + "/cmd_vel");
  auto topic = validTopic(topics);

#ifdef C5_AUTH_ZERO_ONLY
  this->dataPtr->node.Subscribe(topic, &DiffDrivePrivate::OnAuthorizedZero,
#else
  this->dataPtr->node.Subscribe(topic, &DiffDrivePrivate::OnCmdVel,
#endif
      this->dataPtr.get());

  // Subscribe to enable/disable
  std::vector<std::string> enableTopics;
  enableTopics.push_back(
    "/model/" + this->dataPtr->model.Name(_ecm) + "/enable");
  auto enableTopic = validTopic(enableTopics);

  if (!enableTopic.empty())
  {
    this->dataPtr->node.Subscribe(enableTopic, &DiffDrivePrivate::OnEnable,
        this->dataPtr.get());
  }
  #endif
  this->dataPtr->enabled = true;

  std::vector<std::string> odomTopics;
  if (_sdf->HasElement("odom_topic"))
  {
    odomTopics.push_back(_sdf->Get<std::string>("odom_topic"));
  }
  odomTopics.push_back("/model/" + this->dataPtr->model.Name(_ecm) +
      "/odometry");
  auto odomTopic = validTopic(odomTopics);

  #ifndef C5_SPLIT_ZERO_ONLY
  this->dataPtr->odomPub = this->dataPtr->node.Advertise<msgs::Odometry>(
      odomTopic);
  #endif

  std::string tfTopic{"/model/" + this->dataPtr->model.Name(_ecm) +
    "/tf"};
  if (_sdf->HasElement("tf_topic"))
    tfTopic = _sdf->Get<std::string>("tf_topic");
  #ifndef C5_SPLIT_ZERO_ONLY
  this->dataPtr->tfPub = this->dataPtr->node.Advertise<msgs::Pose_V>(
      tfTopic);
  #endif

  if (_sdf->HasElement("frame_id"))
    this->dataPtr->sdfFrameId = _sdf->Get<std::string>("frame_id");

  if (_sdf->HasElement("child_frame_id"))
    this->dataPtr->sdfChildFrameId = _sdf->Get<std::string>("child_frame_id");

  #ifndef C5_SPLIT_ZERO_ONLY
  ignmsg << "DiffDrive subscribing to twist messages on [" << topic << "]"
         << std::endl;
  #endif
}

//////////////////////////////////////////////////
void DiffDrive::PreUpdate(const UpdateInfo &_info,
    EntityComponentManager &_ecm)
{
  IGN_PROFILE("DiffDrive::PreUpdate");
#ifdef C5_SPLIT_ZERO_ONLY
  this->dataPtr->veto->Step(std::chrono::steady_clock::now(),_info.simTime.count());
  this->dataPtr->targetVel.Clear();this->dataPtr->leftJointSpeed=0;this->dataPtr->rightJointSpeed=0;
  auto & proof=this->dataPtr->splitRecord;
  proof.iteration=_info.iterations;proof.sim_ns=_info.simTime.count();
  proof.reason=uint32_t(this->dataPtr->veto->reason);proof.latched=this->dataPtr->veto->latched;
  proof.accepted=this->dataPtr->veto->accepted;proof.rejected=this->dataPtr->veto->rejected;
  proof.command=this->dataPtr->veto->lastCommand;proof.boot=this->dataPtr->veto->boot;
  proof.native_session=this->dataPtr->veto->session;proof.context=this->dataPtr->veto->context;proof.body=this->dataPtr->veto->body;
#ifdef C5_SPLIT_HEALTH_VETO
  auto & v=*this->dataPtr->veto;proof.health=v.lastHealth;proof.health_input=v.lastInput.health;proof.health_ticket=v.healthTicket;proof.health_seen=v.healthSeen;
  proof.input_session=v.lastInput.session;proof.input_context=v.lastInput.context;proof.input_body=v.lastInput.body;
  proof.input_command=v.lastInput.command;proof.input_report=v.lastInput.report;proof.input_accepted=v.inputAccepted;
#endif
#else
  {
    std::lock_guard<std::mutex> lock(this->dataPtr->mutex);
#ifdef C5_AUTH_ZERO_ONLY
    this->dataPtr->authorization->Tick(std::chrono::steady_clock::now(), _info.simTime.count(), this->dataPtr->lease);
#else
    this->dataPtr->lease.Tick(std::chrono::steady_clock::now(), _info.simTime.count());
#endif
    this->dataPtr->targetVel.Clear();
    this->dataPtr->leftJointSpeed = 0;
    this->dataPtr->rightJointSpeed = 0;
  }

  #endif
  // \TODO(anyone) Support rewind
  if (_info.dt < std::chrono::steady_clock::duration::zero())
  {
    ignwarn << "Detected jump back in time ["
        << std::chrono::duration_cast<std::chrono::seconds>(_info.dt).count()
        << "s]. System may not work properly." << std::endl;
  }

  // If the joints haven't been identified yet, look for them
  static std::set<std::string> warnedModels;
  auto modelName = this->dataPtr->model.Name(_ecm);
  if (this->dataPtr->leftJoints.empty() ||
      this->dataPtr->rightJoints.empty())
  {
    bool warned{false};
    for (const std::string &name : this->dataPtr->leftJointNames)
    {
      Entity joint = this->dataPtr->model.JointByName(_ecm, name);
      if (joint != kNullEntity)
        this->dataPtr->leftJoints.push_back(joint);
      else if (warnedModels.find(modelName) == warnedModels.end())
      {
        ignwarn << "Failed to find left joint [" << name << "] for model ["
                << modelName << "]" << std::endl;
        warned = true;
      }
    }

    for (const std::string &name : this->dataPtr->rightJointNames)
    {
      Entity joint = this->dataPtr->model.JointByName(_ecm, name);
      if (joint != kNullEntity)
        this->dataPtr->rightJoints.push_back(joint);
      else if (warnedModels.find(modelName) == warnedModels.end())
      {
        ignwarn << "Failed to find right joint [" << name << "] for model ["
                << modelName << "]" << std::endl;
        warned = true;
      }
    }
    if (warned)
    {
      warnedModels.insert(modelName);
    }
  }

  if (this->dataPtr->leftJoints.empty() || this->dataPtr->rightJoints.empty())
    return;

  if (warnedModels.find(modelName) != warnedModels.end())
  {
    ignmsg << "Found joints for model [" << modelName
           << "], plugin will start working." << std::endl;
    warnedModels.erase(modelName);
  }

  // Nothing left to do if paused.
  if (_info.paused)
    return;

  for (Entity joint : this->dataPtr->leftJoints)
  {
    // skip this entity if it has been removed
    if (!_ecm.HasEntity(joint))
      continue;

    // Update wheel velocity
    auto vel = _ecm.Component<components::JointVelocityCmd>(joint);

    if (vel == nullptr)
    {
      _ecm.CreateComponent(
          joint, components::JointVelocityCmd({this->dataPtr->leftJointSpeed}));
    }
    else
    {
      *vel = components::JointVelocityCmd({this->dataPtr->leftJointSpeed});
    }
  }

  for (Entity joint : this->dataPtr->rightJoints)
  {
    // skip this entity if it has been removed
    if (!_ecm.HasEntity(joint))
      continue;

    // Update wheel velocity
    auto vel = _ecm.Component<components::JointVelocityCmd>(joint);

    if (vel == nullptr)
    {
      _ecm.CreateComponent(joint,
          components::JointVelocityCmd({this->dataPtr->rightJointSpeed}));
    }
    else
    {
      *vel = components::JointVelocityCmd({this->dataPtr->rightJointSpeed});
    }
  }

#ifdef C5_SPLIT_ZERO_ONLY
  auto & proof2=this->dataPtr->splitRecord;
  proof2.selected[0]=this->dataPtr->leftJointSpeed;proof2.selected[1]=this->dataPtr->rightJointSpeed;
  for(auto joint:{this->dataPtr->leftJoints[0],this->dataPtr->rightJoints[0]})
    if(!_ecm.Component<components::JointVelocity>(joint))_ecm.CreateComponent(joint,components::JointVelocity());
  auto link=this->dataPtr->canonicalLink.Entity();
  if(!_ecm.Component<components::WorldPose>(link))_ecm.CreateComponent(link,components::WorldPose());
  if(!_ecm.Component<components::WorldLinearVelocity>(link))_ecm.CreateComponent(link,components::WorldLinearVelocity());
  if(!_ecm.Component<components::WorldAngularVelocity>(link))_ecm.CreateComponent(link,components::WorldAngularVelocity());
#endif
  // Create the left and right side joint position components if they
  // don't exist.
  auto leftPos = _ecm.Component<components::JointPosition>(
      this->dataPtr->leftJoints[0]);
  if (!leftPos && _ecm.HasEntity(this->dataPtr->leftJoints[0]))
  {
    _ecm.CreateComponent(this->dataPtr->leftJoints[0],
        components::JointPosition());
  }

  auto rightPos = _ecm.Component<components::JointPosition>(
      this->dataPtr->rightJoints[0]);
  if (!rightPos && _ecm.HasEntity(this->dataPtr->rightJoints[0]))
  {
    _ecm.CreateComponent(this->dataPtr->rightJoints[0],
        components::JointPosition());
  }
}

//////////////////////////////////////////////////
void DiffDrive::PostUpdate(const UpdateInfo &_info,
    const EntityComponentManager &_ecm)
{
  IGN_PROFILE("DiffDrive::PostUpdate");
  // Nothing left to do if paused.
  if (_info.paused)
    return;

  this->dataPtr->UpdateVelocity(_info, _ecm);
  this->dataPtr->UpdateOdometry(_info, _ecm);
#ifdef C5_SPLIT_ZERO_ONLY
  if(this->dataPtr->leftJoints.empty()||this->dataPtr->rightJoints.empty())return;
  auto & record=this->dataPtr->splitRecord;
  const auto steps=_ecm.Component<c5_split::PhysicsSteps>(worldEntity(_ecm));
  record.physics_steps=steps?steps->Data():0;
  const auto pose=_ecm.Component<components::WorldPose>(this->dataPtr->canonicalLink.Entity());
  if(pose){record.position[0]=pose->Data().Pos().X();record.position[1]=pose->Data().Pos().Y();record.position[2]=pose->Data().Pos().Z();}
  const auto linear=_ecm.Component<components::WorldLinearVelocity>(this->dataPtr->canonicalLink.Entity());
  const auto angular=_ecm.Component<components::WorldAngularVelocity>(this->dataPtr->canonicalLink.Entity());
  record.actual_velocity_known=linear&&angular;size_t index=0;
  if(linear&&angular){for(int axis=0;axis<3;++axis){record.body_velocity[axis]=linear->Data()[axis];record.body_velocity[axis+3]=angular->Data()[axis];}}
  for(auto joint:{this->dataPtr->leftJoints[0],this->dataPtr->rightJoints[0]}){
    auto velocity=_ecm.Component<components::JointVelocity>(joint);
    if(!velocity||velocity->Data().size()!=1)record.actual_velocity_known=0;
    else record.joint_velocity[index]=velocity->Data()[0];++index;
  }
  const auto now=std::chrono::steady_clock::now();record.steady_ns=now.time_since_epoch().count();
  this->dataPtr->veto->Send(record,now);
  if(now-this->dataPtr->lastTrace>=c5_split::Veto::duration(this->dataPtr->tracePeriod)){
    // No logging, JSON, transport publication, locks or waits on the physics thread.
    (void)send(this->dataPtr->traceFd,&record,sizeof(record),MSG_DONTWAIT|MSG_NOSIGNAL);
    this->dataPtr->lastTrace=now;
  }
#endif
}

//////////////////////////////////////////////////
void DiffDrivePrivate::UpdateOdometry(const UpdateInfo &_info,
    const EntityComponentManager &_ecm)
{
  IGN_PROFILE("DiffDrive::UpdateOdometry");
  // Initialize, if not already initialized.
  if (!this->odom.Initialized())
  {
    this->odom.Init(std::chrono::steady_clock::time_point(_info.simTime));
    return;
  }

  if (this->leftJoints.empty() || this->rightJoints.empty())
    return;

  // Get the first joint positions for the left and right side.
  auto leftPos = _ecm.Component<components::JointPosition>(this->leftJoints[0]);
  auto rightPos = _ecm.Component<components::JointPosition>(
      this->rightJoints[0]);

  // Abort if the joints were not found or just created.
  if (!leftPos || !rightPos || leftPos->Data().empty() ||
      rightPos->Data().empty())
  {
    return;
  }

  this->odom.Update(leftPos->Data()[0], rightPos->Data()[0],
      std::chrono::steady_clock::time_point(_info.simTime));

  // Throttle publishing
  auto diff = _info.simTime - this->lastOdomPubTime;
  if (diff > std::chrono::steady_clock::duration::zero() &&
      diff < this->odomPubPeriod)
  {
    return;
  }
  this->lastOdomPubTime = _info.simTime;

#ifdef C5_SPLIT_ZERO_ONLY
  auto & record=this->splitRecord;record.odom_sim_ns=_info.simTime.count();
  record.odom[0]=this->odom.X();record.odom[1]=this->odom.Y();record.odom[2]=*this->odom.Heading();
  record.odom[3]=this->odom.LinearVelocity();record.odom[4]=*this->odom.AngularVelocity();
#else
  // Construct the odometry message and publish it.
  msgs::Odometry msg;
  msg.mutable_pose()->mutable_position()->set_x(this->odom.X());
  msg.mutable_pose()->mutable_position()->set_y(this->odom.Y());

  math::Quaterniond orientation(0, 0, *this->odom.Heading());
  msgs::Set(msg.mutable_pose()->mutable_orientation(), orientation);

  msg.mutable_twist()->mutable_linear()->set_x(this->odom.LinearVelocity());
  msg.mutable_twist()->mutable_angular()->set_z(*this->odom.AngularVelocity());

  // Set the time stamp in the header
  msg.mutable_header()->mutable_stamp()->CopyFrom(
      convert<msgs::Time>(_info.simTime));

  // Set the frame id.
  auto frame = msg.mutable_header()->add_data();
  frame->set_key("frame_id");
  if (this->sdfFrameId.empty())
  {
    frame->add_value(this->model.Name(_ecm) + "/odom");
  }
  else
  {
    frame->add_value(this->sdfFrameId);
  }

  std::optional<std::string> linkName = this->canonicalLink.Name(_ecm);
  if (this->sdfChildFrameId.empty())
  {
    if (linkName)
    {
      auto childFrame = msg.mutable_header()->add_data();
      childFrame->set_key("child_frame_id");
      childFrame->add_value(this->model.Name(_ecm) + "/" + *linkName);
    }
  }
  else
  {
    auto childFrame = msg.mutable_header()->add_data();
    childFrame->set_key("child_frame_id");
    childFrame->add_value(this->sdfChildFrameId);
  }

  // Construct the Pose_V/tf message and publish it.
  msgs::Pose_V tfMsg;
  msgs::Pose *tfMsgPose = tfMsg.add_pose();
  tfMsgPose->mutable_header()->CopyFrom(*msg.mutable_header());
  tfMsgPose->mutable_position()->CopyFrom(msg.mutable_pose()->position());
  tfMsgPose->mutable_orientation()->CopyFrom(msg.mutable_pose()->orientation());

  // Publish the messages
  this->odomPub.Publish(msg);
  this->tfPub.Publish(tfMsg);
#endif
}

//////////////////////////////////////////////////
void DiffDrivePrivate::UpdateVelocity(const UpdateInfo &_info,
    const EntityComponentManager &_ecm)
{
  IGN_PROFILE("DiffDrive::UpdateVelocity");
#ifdef C5_SPLIT_ZERO_ONLY
  this->targetVel.Clear();this->leftJointSpeed=0;this->rightJointSpeed=0;return;
#endif

  double linVel;
  double angVel;
  std::chrono::steady_clock::time_point steadyNow;
  std::string stateName;
  bool hasCommand;
  bool hasTimedOut;
  long long receivedNs;
  long long steadyNs;
  {
    std::lock_guard<std::mutex> lock(this->mutex);
    steadyNow = std::chrono::steady_clock::now();
#ifdef C5_AUTH_ZERO_ONLY
    this->authorization->Tick(steadyNow, _info.simTime.count(), this->lease);
#else
    this->lease.Tick(steadyNow, _info.simTime.count());
#endif
    this->targetVel.Clear();  // Test-only: no nonzero actuator target exists.
    this->haveCommand = this->lease.state == c5_test::State::ACTIVE;
    linVel = this->targetVel.linear().x();
    angVel = this->targetVel.angular().z();
    stateName = this->lease.Name();
    hasCommand = this->haveCommand;
    hasTimedOut = this->lease.timed_out;
    receivedNs = this->received.time_since_epoch().count();
    steadyNs = steadyNow.time_since_epoch().count();
  }

  if (this->actuatorStatePub)
  {
#ifdef C5_AUTH_ZERO_ONLY
    c5_test::Json state;
    {
      std::lock_guard<std::mutex> lock(this->mutex);
      state = this->authorization->Snapshot(steadyNow, this->lease);
      state["sim_ns"] = _info.simTime.count();
      state["target_linear"] = linVel;
      state["target_angular"] = angVel;
      // These are the actual joint command components written in PreUpdate.
      // They prove zero commands, never physical braking from a moving state.
      state["joint_commands"] = c5_test::Json::array();
      for (auto joint : this->leftJoints) {
        const auto value = _ecm.Component<components::JointVelocityCmd>(joint);
        state["joint_commands"].push_back(value ? c5_test::Json(value->Data()) : c5_test::Json());
      }
      for (auto joint : this->rightJoints) {
        const auto value = _ecm.Component<components::JointVelocityCmd>(joint);
        state["joint_commands"].push_back(value ? c5_test::Json(value->Data()) : c5_test::Json());
      }
      this->authorization->AttachHealth(state, steadyNow);
    }
    msgs::StringMsg message;
    message.set_data(state.dump());
    this->actuatorStatePub.Publish(message);
#else
    std::ostringstream state;
    state << "state=" << stateName << ";have_command=" << (hasCommand ? 1 : 0)
          << ";timed_out=" << (hasTimedOut ? 1 : 0)
          << ";target_linear=" << linVel
          << ";target_angular=" << angVel
          << ";received_steady_ns=" << receivedNs
          << ";steady_ns=" << steadyNs
          << ";sim_ns=" << _info.simTime.count();
    msgs::StringMsg message;
    message.set_data(state.str());
    this->actuatorStatePub.Publish(message);
#endif
  }

  // Limit the target velocity if needed.
  this->limiterLin->Limit(
      linVel, this->last0Cmd.lin, this->last1Cmd.lin, _info.dt);
  this->limiterAng->Limit(
      angVel, this->last0Cmd.ang, this->last1Cmd.ang, _info.dt);

  // Update history of commands.
  this->last1Cmd = last0Cmd;
  this->last0Cmd.lin = linVel;
  this->last0Cmd.ang = angVel;

  // Convert the target velocities to joint velocities.
  this->rightJointSpeed =
    (linVel + angVel * this->wheelSeparation / 2.0) / this->wheelRadius;
  this->leftJointSpeed =
    (linVel - angVel * this->wheelSeparation / 2.0) / this->wheelRadius;
}

//////////////////////////////////////////////////
void DiffDrivePrivate::OnCmdVel(const msgs::Twist &_msg)
{
  std::lock_guard<std::mutex> lock(this->mutex);
#if defined(C5_AUTH_ZERO_ONLY) || defined(C5_SPLIT_ZERO_ONLY)
  // Defense in depth: even an accidental direct call cannot refresh the lease.
  (void)_msg;
  this->targetVel.Clear();
#else
  if (this->enabled)
  {
    const bool zero = _msg.linear().x() == 0 && _msg.linear().y() == 0 &&
        _msg.linear().z() == 0 && _msg.angular().x() == 0 &&
        _msg.angular().y() == 0 && _msg.angular().z() == 0;
    this->received = std::chrono::steady_clock::now();
    this->lease.Receive(this->received, zero, this->timeout);
    this->targetVel.Clear();
    this->haveCommand = this->lease.state == c5_test::State::ACTIVE;
  }
#endif
}

#ifdef C5_AUTH_ZERO_ONLY
void DiffDrivePrivate::OnAuthorizedZero(const msgs::StringMsg &_msg)
{
  std::lock_guard<std::mutex> lock(this->mutex);
  if (this->enabled && this->authorization) {
    const auto now = std::chrono::steady_clock::now();
    if (this->authorization->Receive(_msg.data(), now, this->lease) == "ACCEPTED_ZERO")
      this->received = now;
  }
  this->targetVel.Clear();
  this->haveCommand = this->lease.state == c5_test::State::ACTIVE;
}
#endif

//////////////////////////////////////////////////
void DiffDrivePrivate::OnEnable(const msgs::Boolean &_msg)
{
  std::lock_guard<std::mutex> lock(this->mutex);
  this->enabled = _msg.data();
  this->lease.Block();
  this->haveCommand = false;
  if (!this->enabled)
  {
    math::Vector3d zeroVector{0, 0, 0};
    msgs::Set(this->targetVel.mutable_linear(), zeroVector);
    msgs::Set(this->targetVel.mutable_angular(), zeroVector);
  }
}

IGNITION_ADD_PLUGIN(DiffDrive,
                    System,
                    DiffDrive::ISystemConfigure,
                    DiffDrive::ISystemPreUpdate,
                    DiffDrive::ISystemPostUpdate)

#ifdef C5_SPLIT_ZERO_ONLY
IGNITION_ADD_PLUGIN_ALIAS(DiffDrive, "c5::test::SplitZeroDiffDrive")
#elif defined(C5_AUTH_ZERO_ONLY)
IGNITION_ADD_PLUGIN_ALIAS(DiffDrive, "c5::test::AuthorizedZeroDiffDrive")
#else
IGNITION_ADD_PLUGIN_ALIAS(DiffDrive, "gz::sim::systems::DiffDrive")

// TODO(CH3): Deprecated, remove on version 8
IGNITION_ADD_PLUGIN_ALIAS(DiffDrive, "ignition::gazebo::systems::DiffDrive")
#endif
