# Aşama B komut ve çıktı eki

[Ana kayıt](simulation-stage-b-2026-10-23.md). ANSI renk kodları ve satır sonu boşlukları temizlendi; sayısal sonuçlar ve hata satırları korunur.

## environment

```sh
docker version --format '{{.Client.Version}} {{.Server.Version}} {{.Server.Platform.Name}}'
```

Çıkış kodu: 0

```text
29.9.2 29.9.2 Docker Desktop 4.96.3 (244472)

```

## compose-version

```sh
docker compose version
```

Çıkış kodu: 0

```text
Docker Compose version v5.6.1

```

## fortress-help

```sh
docker run --rm ros2-fleet-simulation-check:humble-fortress ign gazebo --help
```

Çıkış kodu: 0

```text
Run and manage Gazebo simulations.

  ign gazebo [options] [file]


Available Options:
  -g                           Run only the GUI.

  --iterations [arg]           Number of iterations to execute.

  --levels                     Use the level system. The default is false,
                               which loads all models. It's always true
                               with --network-role.

  --network-role [arg]         Participant role used in a distributed
                               simulation environment. Role is one of
                               [primary, secondary]. It implies --levels.

  --network-secondaries [arg]  Number of secondary participants expected
                               to join a distributed simulation
                               environment. (Primary only).

  --record                     Use logging system to record states and
                               console messages to the default location,
                               in ~/.ignition/gazebo/log.

  --record-path [arg]          Implicitly invokes --record, and specifies
                               custom path to put recorded files. Argument
                               is path to record states and console
                               messages. Specifying this argument will
                               enable console logging to a console.log
                               file in the specified path.

  --record-resources           Implicitly invokes --record, and records
                               meshes and material files, in addition to
                               states and console messages.

  --record-topic [arg]         Specify the name of an additional topic to
                               record. Implicitly invokes --record.
                               Zero or more topics can be specified by
                               using multiple --record-topic options.
                               Regular expressions can be used, which
                               likely requires quotes. A default set of
                               topics are also recorded, which support
                               simulation state playback. Enable debug
                               console output with the -v 4 option
                               and look for 'Recording default topic' in
                               order to determine the default set of
                               topics.
                               Examples:
                                 1. Record all topics.
                                     --record-topic ".*"
                                 2. Record only the /stats topic.
                                     --record-topic /stats
                                 3. Record the /stats and /clock topics.
                                     --record-topic /stats
                                     --record-topic /clock

  --record-period [arg]        Specify the time period (seconds) between
                               state recording.

  --log-overwrite              When recording, overwrite existing files.
                               Only valid if recording is enabled.

  --log-compress               When recording, compress final log files.
                               Only valid if recording is enabled.

  --playback [arg]             Use logging system to play back states.
                               Argument is path to recorded states.

  --headless-rendering         Run rendering in headless mode

  -r                           Run simulation on start.

  -s                           Run only the server (headless mode). This
                               overrides -g, if it is also present.

  -v [ --verbose ] [arg]       Adjust the level of console output (0~4).
                               The default verbosity is 1, use -v without
                               arguments for level 3.

  --gui-config [arg]           Ignition GUI configuration file to load.
                               If no config is given, the configuration in
                               the SDF file is used. And if that's not
                               provided, the default installed config is
                               used.

  --physics-engine [arg]       Ignition Physics engine plugin to load.
                               Gazebo will use DART by default.
                               (ignition-physics-dartsim-plugin)
                               Make sure custom plugins are in
                               IGN_GAZEBO_PHYSICS_ENGINE_PATH.

  --render-engine [arg]        Ignition Rendering engine plugin to load for
                               both the server and the GUI. Gazebo will use
                               OGRE2 by default. (ogre2)
                               Make sure custom plugins are in
                               IGN_GAZEBO_RENDER_ENGINE_PATH.

  --render-engine-gui [arg]    Ignition Rendering engine plugin to load for
                               the GUI. Gazebo will use OGRE2 by default.
                               (ogre2)
                               Make sure custom plugins are in
                               IGN_GAZEBO_RENDER_ENGINE_PATH.

  --render-engine-server [arg] Ignition Rendering engine plugin to load for
                               the server. Gazebo will use OGRE2 by default.
                               (ogre2)
                               Make sure custom plugins are in
                               IGN_GAZEBO_RENDER_ENGINE_PATH.

  --version                    Print Gazebo version information.

  -z [arg]                     Update rate in Hertz.

  -h [--help]                Print this help message.

  --force-version <VERSION>  Use a specific library version.

  --versions                 Show the available versions.

Environment variables:
  IGN_GAZEBO_RESOURCE_PATH    Colon separated paths used to locate
 resources such as worlds and models.

  GZ_SIM_RESOURCE_PATH    Colon separated paths used to locate
 resources such as worlds and models.

  IGN_GAZEBO_SYSTEM_PLUGIN_PATH    Colon separated paths used to
 locate system plugins.

  GZ_SIM_SYSTEM_PLUGIN_PATH    Colon separated paths used to
 locate system plugins.

  IGN_GAZEBO_SERVER_CONFIG_PATH    Path to server configuration file.

  GZ_SIM_SERVER_CONFIG_PATH    Path to server configuration file.

  IGN_GUI_PLUGIN_PATH    Colon separated paths used to locate GUI
 plugins.

  GZ_GUI_RESOURCE_PATH    Colon separated paths used to locate GUI
 resources such as configuration files.


```

## compose-config

```sh
env DDS_TEST_PAYLOAD=simulation-b1-config docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml config --quiet
```

Çıkış kodu: 0

```text

```

## build-b1

```sh
env DDS_TEST_PAYLOAD=simulation-b1-build docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml build simulation
```

Çıkış kodu: 0

```text
 Image ros2-fleet-simulation-lidar-check:humble-fortress Building
#1 [internal] load local bake definitions
#1 reading from stdin 633B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 344B done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/ros2-fleet-simulation-check:humble-fortress
#3 DONE 0.4s

#4 [internal] load .dockerignore
#4 transferring context: 2B done
#4 DONE 0.0s

#5 [internal] load build context
#5 transferring context: 9.34kB done
#5 DONE 0.0s

#6 [1/3] FROM docker.io/library/ros2-fleet-simulation-check:humble-fortress@sha256:69cb7989a1a325add4f0ca325f4fa1e002beb4f2ffd415d59f1efd4e32151b39
#6 resolve docker.io/library/ros2-fleet-simulation-check:humble-fortress@sha256:69cb7989a1a325add4f0ca325f4fa1e002beb4f2ffd415d59f1efd4e32151b39 0.0s done
#6 DONE 0.0s

#7 [2/3] RUN apt-get update && apt-get install -y --no-install-recommends     libignition-rendering6-ogre2     && rm -rf /var/lib/apt/lists/*
#7 0.776 Get:1 http://packages.ros.org/ros2/ubuntu jammy InRelease [4682 B]
#7 0.917 Get:2 http://ports.ubuntu.com/ubuntu-ports jammy InRelease [270 kB]
#7 1.428 Get:3 http://packages.ros.org/ros2/ubuntu jammy/main Sources [1900 kB]
#7 2.879 Get:4 http://ports.ubuntu.com/ubuntu-ports jammy-updates InRelease [128 kB]
#7 5.397 Get:5 http://ports.ubuntu.com/ubuntu-ports jammy-backports InRelease [127 kB]
#7 6.293 Get:6 http://ports.ubuntu.com/ubuntu-ports jammy-security InRelease [129 kB]
#7 7.865 Get:7 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 Packages [1758 kB]
#7 11.76 Get:8 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 Packages [17.2 MB]
#7 19.21 Get:9 http://packages.ros.org/ros2/ubuntu jammy/main arm64 Packages [1823 kB]
#7 56.15 Get:10 http://ports.ubuntu.com/ubuntu-ports jammy/restricted arm64 Packages [24.2 kB]
#7 57.09 Get:11 http://ports.ubuntu.com/ubuntu-ports jammy/multiverse arm64 Packages [224 kB]
#7 59.30 Get:12 http://ports.ubuntu.com/ubuntu-ports jammy-updates/universe arm64 Packages [1717 kB]
#7 75.22 Get:13 http://ports.ubuntu.com/ubuntu-ports jammy-updates/multiverse arm64 Packages [81.6 kB]
#7 76.38 Get:14 http://ports.ubuntu.com/ubuntu-ports jammy-updates/restricted arm64 Packages [8359 kB]
#7 85.42 Get:15 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 Packages [4567 kB]
#7 91.69 Get:16 http://ports.ubuntu.com/ubuntu-ports jammy-backports/main arm64 Packages [82.5 kB]
#7 92.29 Get:17 http://ports.ubuntu.com/ubuntu-ports jammy-backports/universe arm64 Packages [33.7 kB]
#7 92.69 Get:18 http://ports.ubuntu.com/ubuntu-ports jammy-security/restricted arm64 Packages [8061 kB]
#7 108.1 Get:19 http://ports.ubuntu.com/ubuntu-ports jammy-security/universe arm64 Packages [1421 kB]
#7 111.8 Get:20 http://ports.ubuntu.com/ubuntu-ports jammy-security/main arm64 Packages [4253 kB]
#7 122.0 Get:21 http://ports.ubuntu.com/ubuntu-ports jammy-security/multiverse arm64 Packages [75.6 kB]
#7 122.6 Fetched 52.2 MB in 2min 2s (427 kB/s)
#7 122.6 Reading package lists...
#7 123.3 Reading package lists...
#7 123.8 Building dependency tree...
#7 123.9 Reading state information...
#7 124.1 The following additional packages will be installed:
#7 124.1   libogrenexthlmspbs2.2.5 libogrenexthlmsunlit2.2.5 libogrenextmain2.2.5
#7 124.1   libogrenextoverlay2.2.5 libogrenextplanarreflections2.2.5 libopengl0
#7 124.1   libxrandr2 libzzip-0-13
#7 124.1 The following NEW packages will be installed:
#7 124.1   libignition-rendering6-ogre2 libogrenexthlmspbs2.2.5
#7 124.1   libogrenexthlmsunlit2.2.5 libogrenextmain2.2.5 libogrenextoverlay2.2.5
#7 124.1   libogrenextplanarreflections2.2.5 libopengl0 libxrandr2 libzzip-0-13
#7 124.7 0 upgraded, 9 newly installed, 0 to remove and 9 not upgraded.
#7 124.7 Need to get 2948 kB of archives.
#7 124.7 After this operation, 13.7 MB of additional disk space will be used.
#7 124.7 Get:1 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libxrandr2 arm64 2:1.5.2-1build1 [19.6 kB]
#7 124.7 Get:2 http://packages.ros.org/ros2/ubuntu jammy/main arm64 libignition-rendering6-ogre2 arm64 6.6.4-1~jammy [482 kB]
#7 126.7 Get:3 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libzzip-0-13 arm64 0.13.72+dfsg.1-1.1 [26.6 kB]
#7 127.6 Get:4 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenextmain2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [1973 kB]
#7 147.5 Get:5 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenextplanarreflections2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [32.9 kB]
#7 148.2 Get:6 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenexthlmspbs2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [213 kB]
#7 150.7 Get:7 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenexthlmsunlit2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [63.1 kB]
#7 151.5 Get:8 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenextoverlay2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [100 kB]
#7 152.5 Get:9 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libopengl0 arm64 1.4.0-1 [38.6 kB]
#7 152.8 debconf: delaying package configuration, since apt-utils is not installed
#7 152.8 Fetched 2948 kB in 29s (103 kB/s)
#7 152.8 Selecting previously unselected package libxrandr2:arm64.
#7 152.8 (Reading database ...
(Reading database ... 5%
(Reading database ... 10%
(Reading database ... 15%
(Reading database ... 20%
(Reading database ... 25%
(Reading database ... 30%
(Reading database ... 35%
(Reading database ... 40%
(Reading database ... 45%
(Reading database ... 50%
(Reading database ... 55%
(Reading database ... 60%
(Reading database ... 65%
(Reading database ... 70%
(Reading database ... 75%
(Reading database ... 80%
(Reading database ... 85%
(Reading database ... 90%
(Reading database ... 95%
(Reading database ... 100%
(Reading database ... 50017 files and directories currently installed.)
#7 152.9 Preparing to unpack .../0-libxrandr2_2%3a1.5.2-1build1_arm64.deb ...
#7 152.9 Unpacking libxrandr2:arm64 (2:1.5.2-1build1) ...
#7 152.9 Selecting previously unselected package libzzip-0-13:arm64.
#7 153.0 Preparing to unpack .../1-libzzip-0-13_0.13.72+dfsg.1-1.1_arm64.deb ...
#7 153.0 Unpacking libzzip-0-13:arm64 (0.13.72+dfsg.1-1.1) ...
#7 153.0 Selecting previously unselected package libogrenextmain2.2.5:arm64.
#7 153.0 Preparing to unpack .../2-libogrenextmain2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 153.0 Unpacking libogrenextmain2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 153.0 Selecting previously unselected package libogrenextplanarreflections2.2.5:arm64.
#7 153.0 Preparing to unpack .../3-libogrenextplanarreflections2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 153.0 Unpacking libogrenextplanarreflections2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 153.0 Selecting previously unselected package libogrenexthlmspbs2.2.5:arm64.
#7 153.0 Preparing to unpack .../4-libogrenexthlmspbs2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 153.0 Unpacking libogrenexthlmspbs2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 153.0 Selecting previously unselected package libogrenexthlmsunlit2.2.5:arm64.
#7 153.0 Preparing to unpack .../5-libogrenexthlmsunlit2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 153.0 Unpacking libogrenexthlmsunlit2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 153.0 Selecting previously unselected package libogrenextoverlay2.2.5:arm64.
#7 153.0 Preparing to unpack .../6-libogrenextoverlay2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 153.0 Unpacking libogrenextoverlay2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 153.0 Selecting previously unselected package libopengl0:arm64.
#7 153.0 Preparing to unpack .../7-libopengl0_1.4.0-1_arm64.deb ...
#7 153.1 Unpacking libopengl0:arm64 (1.4.0-1) ...
#7 153.1 Selecting previously unselected package libignition-rendering6-ogre2:arm64.
#7 153.1 Preparing to unpack .../8-libignition-rendering6-ogre2_6.6.4-1~jammy_arm64.deb ...
#7 153.1 Unpacking libignition-rendering6-ogre2:arm64 (6.6.4-1~jammy) ...
#7 153.1 Setting up libzzip-0-13:arm64 (0.13.72+dfsg.1-1.1) ...
#7 153.1 Setting up libopengl0:arm64 (1.4.0-1) ...
#7 153.1 Setting up libxrandr2:arm64 (2:1.5.2-1build1) ...
#7 153.1 Setting up libogrenextmain2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 153.1 Setting up libogrenextplanarreflections2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 153.1 Setting up libogrenexthlmsunlit2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 153.1 Setting up libogrenexthlmspbs2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 153.1 Setting up libogrenextoverlay2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 153.1 Setting up libignition-rendering6-ogre2:arm64 (6.6.4-1~jammy) ...
#7 153.1 Processing triggers for libc-bin (2.35-0ubuntu3.15) ...
#7 DONE 153.2s

#8 [3/3] COPY docker/simulation-lidar-check /opt/simulation-lidar-check
#8 DONE 0.0s

#9 exporting to image
#9 exporting layers
#9 exporting layers 0.3s done
#9 exporting manifest sha256:6676892fb08b6c292c311103b072502d5e44d0a7ab0fffd00db47f7e75623f9a done
#9 exporting config sha256:44817b659c9a3be5ad717eae6e798d11dbadbe75389d486c8ad84ebc97034955 done
#9 exporting attestation manifest sha256:bc59de68b67028540a86b4b03e1edf50014eba67b3d7ec12311e8203b5513b1f done
#9 exporting manifest list sha256:3047a642208db50e5f5f1295384acdf0bbdf23db7c10f6bab2ccca822541d815 done
#9 naming to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress done
#9 unpacking to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress 0.1s done
#9 DONE 0.4s

#10 resolving provenance for metadata file
#10 DONE 0.0s
 Image ros2-fleet-simulation-lidar-check:humble-fortress Built

```

## base-identity

```sh
docker image inspect ros2-fleet-simulation-check:humble-fortress --format '{{.Id}} {{json .RepoDigests}} {{.Os}}/{{.Architecture}}'
```

Çıkış kodu: 0

```text
sha256:69cb7989a1a325add4f0ca325f4fa1e002beb4f2ffd415d59f1efd4e32151b39 ["ros2-fleet-simulation-check@sha256:69cb7989a1a325add4f0ca325f4fa1e002beb4f2ffd415d59f1efd4e32151b39"] linux/arm64

```

## config-tests

```sh
docker run --rm --env-file config/dds.env -e DDS_TEST_PAYLOAD=b1-config -e SIM_CHECK_ROLE=backend -v /Users/murat/develop/ros2-fleet-manager/config:/config:ro -v /Users/murat/develop/ros2-fleet-manager/docker/simulation-lidar-check:/opt/simulation-lidar-check:ro ros2-fleet-simulation-lidar-check:humble-fortress python3 /opt/simulation-lidar-check/test_config.py
```

Çıkış kodu: 1

```text
E
======================================================================
ERROR: test_invalid (__main__.ConfigTests) (config={'sensor': {'pose': [0, 0, 0.15, 0, 0, 0], 'samples': 0, 'min_angle_rad': -0.35, 'max_angle_rad': 0.35, 'min_range_m': 0.1, 'max_range_m': 8.0, 'resolution_m': 0.01, 'update_rate_hz': 5.0}, 'wall': {'pose': [2, 0, 0.75, 0, 0, 0], 'size_m': [0.1, 4, 1.5]}, 'render': {'engine': 'ogre2', 'headless': True}, 'check': {'minimum_messages': 10, 'range_tolerance_m': 0.12}})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/opt/simulation-lidar-check/test_config.py", line 43, in test_invalid
    check.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  [Previous line repeated 981 more times]
RecursionError: maximum recursion depth exceeded

======================================================================
ERROR: test_invalid (__main__.ConfigTests) (config={'sensor': {'pose': [0, 0, 0.15, 0, 0, 0], 'samples': 31, 'min_angle_rad': -0.35, 'max_angle_rad': 0.35, 'min_range_m': 0.1, 'max_range_m': 8.0, 'resolution_m': 0.01, 'update_rate_hz': nan}, 'wall': {'pose': [2, 0, 0.75, 0, 0, 0], 'size_m': [0.1, 4, 1.5]}, 'render': {'engine': 'ogre2', 'headless': True}, 'check': {'minimum_messages': 10, 'range_tolerance_m': 0.12}})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/opt/simulation-lidar-check/test_config.py", line 43, in test_invalid
    check.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  [Previous line repeated 981 more times]
RecursionError: maximum recursion depth exceeded

======================================================================
ERROR: test_invalid (__main__.ConfigTests) (config={'sensor': {'pose': [0, 0, 0.15, 0, 0, 0], 'samples': 31, 'min_angle_rad': -0.35, 'max_angle_rad': 0.35, 'min_range_m': 0.1, 'max_range_m': 0.01, 'resolution_m': 0.01, 'update_rate_hz': 5.0}, 'wall': {'pose': [2, 0, 0.75, 0, 0, 0], 'size_m': [0.1, 4, 1.5]}, 'render': {'engine': 'ogre2', 'headless': True}, 'check': {'minimum_messages': 10, 'range_tolerance_m': 0.12}})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/opt/simulation-lidar-check/test_config.py", line 43, in test_invalid
    check.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  [Previous line repeated 981 more times]
RecursionError: maximum recursion depth exceeded

======================================================================
ERROR: test_invalid (__main__.ConfigTests) (config={'sensor': {'pose': [0, 0, 0.15, 0, 0, 0], 'samples': 31, 'min_angle_rad': 1, 'max_angle_rad': 0.35, 'min_range_m': 0.1, 'max_range_m': 8.0, 'resolution_m': 0.01, 'update_rate_hz': 5.0}, 'wall': {'pose': [2, 0, 0.75, 0, 0, 0], 'size_m': [0.1, 4, 1.5]}, 'render': {'engine': 'ogre2', 'headless': True}, 'check': {'minimum_messages': 10, 'range_tolerance_m': 0.12}})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/opt/simulation-lidar-check/test_config.py", line 43, in test_invalid
    check.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  [Previous line repeated 981 more times]
RecursionError: maximum recursion depth exceeded

======================================================================
ERROR: test_invalid (__main__.ConfigTests) (config={'sensor': {'pose': [0, 0, 0.15, 0, 0, 0], 'samples': 31, 'min_angle_rad': -0.35, 'max_angle_rad': 0.35, 'min_range_m': 0.1, 'max_range_m': 8.0, 'resolution_m': 0.01, 'update_rate_hz': 5.0}, 'wall': {'pose': [2, 0, 0.75, 0, 0, 0], 'size_m': [0, 1, 1]}, 'render': {'engine': 'ogre2', 'headless': True}, 'check': {'minimum_messages': 10, 'range_tolerance_m': 0.12}})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/opt/simulation-lidar-check/test_config.py", line 43, in test_invalid
    check.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  [Previous line repeated 981 more times]
RecursionError: maximum recursion depth exceeded

======================================================================
ERROR: test_invalid (__main__.ConfigTests) (config={'sensor': {'pose': [0, 0, 0, 0, 0, 1], 'samples': 31, 'min_angle_rad': -0.35, 'max_angle_rad': 0.35, 'min_range_m': 0.1, 'max_range_m': 8.0, 'resolution_m': 0.01, 'update_rate_hz': 5.0}, 'wall': {'pose': [2, 0, 0.75, 0, 0, 0], 'size_m': [0.1, 4, 1.5]}, 'render': {'engine': 'ogre2', 'headless': True}, 'check': {'minimum_messages': 10, 'range_tolerance_m': 0.12}})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/opt/simulation-lidar-check/test_config.py", line 43, in test_invalid
    check.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  [Previous line repeated 981 more times]
RecursionError: maximum recursion depth exceeded

======================================================================
ERROR: test_invalid (__main__.ConfigTests) (config={'sensor': {'pose': [0, 0, 0.15, 0, 0, 0], 'samples': 31, 'min_angle_rad': -0.35, 'max_angle_rad': 0.35, 'min_range_m': 0.1, 'max_range_m': 8.0, 'resolution_m': 0.01, 'update_rate_hz': 5.0}, 'wall': {'pose': [2, 0, 0.75, 0, 0, 0], 'size_m': [0.1, 4, 1.5]}, 'check': {'minimum_messages': 10, 'range_tolerance_m': 0.12}})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/opt/simulation-lidar-check/test_config.py", line 43, in test_invalid
    check.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  [Previous line repeated 981 more times]
RecursionError: maximum recursion depth exceeded

======================================================================
ERROR: test_invalid (__main__.ConfigTests) (config={'sensor': {'pose': [0, 0, 0.15, 0, 0, 0], 'samples': 31, 'min_angle_rad': -0.35, 'max_angle_rad': 0.35, 'min_range_m': 0.1, 'max_range_m': 8.0, 'resolution_m': 0.01, 'update_rate_hz': 5.0}, 'wall': {'pose': [2, 0, 0.75, 0, 0, 0], 'size_m': [0.1, 4, 1.5]}, 'render': {'engine': 'ogre2', 'headless': True}, 'check': {'minimum_messages': 10, 'range_tolerance_m': 0.12}, 'extra': 1})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/opt/simulation-lidar-check/test_config.py", line 43, in test_invalid
    check.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  [Previous line repeated 981 more times]
RecursionError: maximum recursion depth exceeded

======================================================================
ERROR: test_valid_and_world (__main__.ConfigTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/opt/simulation-lidar-check/test_config.py", line 12, in test_valid_and_world
    base, config, _ = check.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  File "/opt/simulation-lidar-check/check.py", line 17, in load_config
    base, timeout = stage_a.load_config()
  [Previous line repeated 981 more times]
RecursionError: maximum recursion depth exceeded

----------------------------------------------------------------------
Ran 2 tests in 0.011s

FAILED (errors=9)

```

## run-b1-01

```sh
env DDS_TEST_PAYLOAD=simulation-b1-20261023-01 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml up --no-build --abort-on-container-exit --exit-code-from backend
```

Çıkış kodu: 1

```text
 Network ros2-fleet-simulation-lidar-check_dds Creating
 Network ros2-fleet-simulation-lidar-check_dds Creating
 Network ros2-fleet-simulation-lidar-check_dds Created
 Network ros2-fleet-simulation-lidar-check_dds Created
 Container ros2-fleet-simulation-lidar-check-simulation-1 Creating
 Container ros2-fleet-simulation-lidar-check-backend-1 Creating
 Container ros2-fleet-simulation-lidar-check-simulation-1 Created
 Container ros2-fleet-simulation-lidar-check-backend-1 Created
Attaching to backend-1, simulation-1
 Container ros2-fleet-simulation-lidar-check-simulation-1 Starting
 Container ros2-fleet-simulation-lidar-check-backend-1 Starting
 Container ros2-fleet-simulation-lidar-check-simulation-1 Started
 Container ros2-fleet-simulation-lidar-check-backend-1 Started
simulation-1  | {"event": "CONFIG_VALID", "role": "simulation"}
simulation-1  | {"event": "PROCESS_START", "command": ["ign", "gazebo", "-s", "-r", "-v", "4", "--headless-rendering", "--physics-engine", "/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5", "/tmp/lidar-world.sdf"]}
simulation-1  | {"event": "PROCESS_START", "command": ["ros2", "run", "ros_gz_bridge", "parameter_bridge", "/validation_robot/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan", "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock", "/validation_robot/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry", "/validation_robot/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"]}
backend-1     | {"event": "CONFIG_VALID", "role": "backend"}
simulation-1  | [INFO] [1792741773.962328010] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/validation_robot/scan (ignition.msgs.LaserScan) -> /validation_robot/scan (sensor_msgs/msg/LaserScan)] (Lazy 0)
simulation-1  | [INFO] [1792741773.966869219] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/clock (ignition.msgs.Clock) -> /clock (rosgraph_msgs/msg/Clock)] (Lazy 0)
simulation-1  | [INFO] [1792741773.967527635] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/validation_robot/odom (ignition.msgs.Odometry) -> /validation_robot/odom (nav_msgs/msg/Odometry)] (Lazy 0)
simulation-1  | [INFO] [1792741773.968678802] [ros_gz_bridge]: Creating ROS->GZ Bridge: [/validation_robot/cmd_vel (geometry_msgs/msg/Twist) -> /validation_robot/cmd_vel (ignition.msgs.Twist)] (Lazy 0)
backend-1     | {"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp"}
simulation-1  | [Msg] Ignition Gazebo Server v6.18.0
simulation-1  | [Msg] Loading SDF world file[/tmp/lidar-world.sdf].
simulation-1  | [Msg] Serving entity system service on [/entity/system/add]
simulation-1  | [Dbg] [Physics.cc:804] Loaded [ignition::physics::dartsim::Plugin] from library [/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5]
simulation-1  | [Dbg] [SystemManager.cc:73] Loaded system [ignition::gazebo::systems::Physics] for entity [1]
simulation-1  | [Msg] Create service on [/world/validation_world/create]
simulation-1  | [Msg] Remove service on [/world/validation_world/remove]
simulation-1  | [Msg] Pose service on [/world/validation_world/set_pose]
simulation-1  | [Msg] Pose service on [/world/validation_world/set_pose_vector]
simulation-1  | [Msg] Light configuration service on [/world/validation_world/light_config]
simulation-1  | [Msg] Physics service on [/world/validation_world/set_physics]
simulation-1  | [Msg] SphericalCoordinates service on [/world/validation_world/set_spherical_coordinates]
simulation-1  | [Msg] Enable collision service on [/world/validation_world/enable_collision]
simulation-1  | [Msg] Disable collision service on [/world/validation_world/disable_collision]
simulation-1  | [Msg] Material service on [/world/validation_world/visual_config]
simulation-1  | [Msg] Material service on [/world/validation_world/wheel_slip]
simulation-1  | [Dbg] [SystemManager.cc:73] Loaded system [ignition::gazebo::systems::UserCommands] for entity [1]
simulation-1  | [Dbg] [SystemManager.cc:73] Loaded system [ignition::gazebo::systems::SceneBroadcaster] for entity [1]
simulation-1  | [Dbg] [Sensors.cc:506] Configuring Sensors system
simulation-1  | [Dbg] [Sensors.cc:431] SensorsPrivate::Run
simulation-1  | [Dbg] [SystemManager.cc:73] Loaded system [ignition::gazebo::systems::Sensors] for entity [1]
simulation-1  | [Dbg] [Sensors.cc:411] SensorsPrivate::RenderThread started
simulation-1  | [Dbg] [Sensors.cc:258] Waiting for init
simulation-1  | [Msg] DiffDrive subscribing to twist messages on [/validation_robot/cmd_vel]
simulation-1  | [Dbg] [SystemManager.cc:73] Loaded system [ignition::gazebo::systems::DiffDrive] for entity [8]
simulation-1  | [Msg] Loaded level [3]
simulation-1  | [Msg] Serving world controls on [/world/validation_world/control], [/world/validation_world/control/state] and [/world/validation_world/playback/control]
simulation-1  | [Msg] Serving GUI information on [/world/validation_world/gui/info]
simulation-1  | [Msg] World [validation_world] initialized with [physics] physics profile.
simulation-1  | [Msg] Serving world SDF generation service on [/world/validation_world/generate_world_sdf]
simulation-1  | [Err] [RenderEngineManager.cc:461] Failed to load plugin [ignition-rendering-ogre2] : couldn't find shared library.
simulation-1  | [Err] [RenderUtil.cc:2581] Engine [ogre2] is not supported. Loading OGRE2 instead.
simulation-1  | [Err] [RenderEngineManager.cc:461] Failed to load plugin [ignition-rendering-ogre2] : couldn't find shared library.
simulation-1  | Stack trace (most recent call last) in thread 40:
simulation-1  | #6    Object "[0xffffffffffffffff]", at 0xffffffffffffffff, in
simulation-1  | #5    Object "/lib/aarch64-linux-gnu/libc.so.6", at 0xffff94909fdb, in
simulation-1  | #4    Object "/lib/aarch64-linux-gnu/libc.so.6", at 0xffff948a03c7, in
simulation-1  | #3    Object "/lib/aarch64-linux-gnu/libstdc++.so.6", at 0xffff90dc29cb, in
simulation-1  | #2    Object "/usr/lib/aarch64-linux-gnu/ign-gazebo-6/plugins/libignition-gazebo-sensors-system.so", at 0xffff80396bbb, in ignition::gazebo::v6::systems::SensorsPrivate::RenderThread()
simulation-1  | #1    Object "/usr/lib/aarch64-linux-gnu/ign-gazebo-6/plugins/libignition-gazebo-sensors-system.so", at 0xffff80395367, in ignition::gazebo::v6::systems::SensorsPrivate::WaitForInit()
simulation-1  | #0    Object "/lib/aarch64-linux-gnu/libignition-gazebo6-rendering.so.6", at 0xffff802a4464, in ignition::gazebo::v6::RenderUtil::Init()
simulation-1  | Segmentation fault (Address not mapped to object [(nil)])
simulation-1  | [Msg] Serving world names on [{"event": "PROCESS_EXIT", "command": ["ign", "gazebo", "-s", "-r", "-v", "4", "--headless-rendering", "--physics-engine", "/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5", "/tmp/lidar-world.sdf"], "code": -11}
simulation-1  | [INFO] [1792741775.968409345] [rclcpp]: signal_handler(SIGINT/SIGTERM)
simulation-1  | {"event": "PROCESS_EXIT", "command": ["ros2", "run", "ros_gz_bridge", "parameter_bridge", "/validation_robot/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan", "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock", "/validation_robot/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry", "/validation_robot/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"], "code": 0}
simulation-1  | {"event": "FAIL", "error": "Child ['ign', 'gazebo', '-s', '-r', '-v', '4', '--headless-rendering', '--physics-engine', '/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5', '/tmp/lidar-world.sdf'] exited unexpectedly: -11", "error_type": "RuntimeError"}

simulation-1 exited with code 1
 Compose Stopping Aborting on container exit...
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopping
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopping
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopped
backend-1     | {"event": "FAIL", "error": "failed to shutdown: rcl_shutdown already called on the given context, at ./src/rcl/init.c:241", "error_type": "RCLError"}
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopped

backend-1 exited with code 1


```

## config-tests-fixed

```sh
docker run --rm --env-file config/dds.env -e DDS_TEST_PAYLOAD=b1-config -e SIM_CHECK_ROLE=backend -v /Users/murat/develop/ros2-fleet-manager/config:/config:ro -v /Users/murat/develop/ros2-fleet-manager/docker/simulation-lidar-check:/opt/simulation-lidar-check:ro ros2-fleet-simulation-lidar-check:humble-fortress python3 /opt/simulation-lidar-check/test_config.py
```

Çıkış kodu: 0

```text
..
----------------------------------------------------------------------
Ran 2 tests in 0.018s

OK

```

## renderer-diagnosis

```sh
docker run --rm ros2-fleet-simulation-lidar-check:humble-fortress bash -c 'dpkg -L libignition-rendering6-ogre2; find /usr/lib -name "*ogre2*.so*"; find /usr/lib -name "*ogre2*.so*" -exec ldd {} \; '
```

Çıkış kodu: 0

```text
/.
/usr
/usr/lib
/usr/lib/aarch64-linux-gnu
/usr/lib/aarch64-linux-gnu/ign-rendering-6
/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins
/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6.6.4
/usr/lib/aarch64-linux-gnu/libignition-rendering6-ogre2.so.6.6.4
/usr/share
/usr/share/doc
/usr/share/doc/libignition-rendering6-ogre2
/usr/share/doc/libignition-rendering6-ogre2/changelog.Debian.gz
/usr/share/doc/libignition-rendering6-ogre2/copyright
/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6
/usr/lib/aarch64-linux-gnu/libignition-rendering6-ogre2.so.6
/usr/lib/aarch64-linux-gnu/libignition-rendering6-ogre2.so.6.6.4
/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6.6.4
/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6
/usr/lib/aarch64-linux-gnu/libignition-rendering6-ogre2.so.6
	linux-vdso.so.1 (0x0000ffff88755000)
	libignition-rendering6.so.6 => /lib/aarch64-linux-gnu/libignition-rendering6.so.6 (0x0000ffff883b0000)
	libOpenGL.so.0 => /lib/aarch64-linux-gnu/libOpenGL.so.0 (0x0000ffff88340000)
	libGLX.so.0 => /lib/aarch64-linux-gnu/libGLX.so.0 (0x0000ffff882f0000)
	libOgreNextMain.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextMain.so.2.2.5 (0x0000ffff87e00000)
	libignition-common4-graphics.so.4 => /lib/aarch64-linux-gnu/libignition-common4-graphics.so.4 (0x0000ffff87d40000)
	libignition-common4-events.so.4 => /lib/aarch64-linux-gnu/libignition-common4-events.so.4 (0x0000ffff87d10000)
	libignition-common4.so.4 => /lib/aarch64-linux-gnu/libignition-common4.so.4 (0x0000ffff87ca0000)
	libignition-math6.so.6 => /lib/aarch64-linux-gnu/libignition-math6.so.6 (0x0000ffff87c40000)
	libOgreNextHlmsPbs.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextHlmsPbs.so.2.2.5 (0x0000ffff87bb0000)
	libOgreNextHlmsUnlit.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextHlmsUnlit.so.2.2.5 (0x0000ffff87b70000)
	libOgreNextOverlay.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextOverlay.so.2.2.5 (0x0000ffff87b10000)
	libOgreNextPlanarReflections.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextPlanarReflections.so.2.2.5 (0x0000ffff87af0000)
	libstdc++.so.6 => /lib/aarch64-linux-gnu/libstdc++.so.6 (0x0000ffff878c0000)
	libm.so.6 => /lib/aarch64-linux-gnu/libm.so.6 (0x0000ffff87820000)
	libgcc_s.so.1 => /lib/aarch64-linux-gnu/libgcc_s.so.1 (0x0000ffff877f0000)
	libc.so.6 => /lib/aarch64-linux-gnu/libc.so.6 (0x0000ffff87640000)
	/lib/ld-linux-aarch64.so.1 (0x0000ffff88710000)
	libignition-plugin1-loader.so.1 => /lib/aarch64-linux-gnu/libignition-plugin1-loader.so.1 (0x0000ffff87620000)
	libignition-plugin1.so.1 => /lib/aarch64-linux-gnu/libignition-plugin1.so.1 (0x0000ffff87600000)
	libGLdispatch.so.0 => /lib/aarch64-linux-gnu/libGLdispatch.so.0 (0x0000ffff87470000)
	libX11.so.6 => /lib/aarch64-linux-gnu/libX11.so.6 (0x0000ffff87320000)
	libXt.so.6 => /lib/aarch64-linux-gnu/libXt.so.6 (0x0000ffff872a0000)
	libXaw.so.7 => /lib/aarch64-linux-gnu/libXaw.so.7 (0x0000ffff87220000)
	libXrandr.so.2 => /lib/aarch64-linux-gnu/libXrandr.so.2 (0x0000ffff87200000)
	libfreeimage.so.3 => /lib/aarch64-linux-gnu/libfreeimage.so.3 (0x0000ffff87140000)
	libzzip-0.so.13 => /lib/aarch64-linux-gnu/libzzip-0.so.13 (0x0000ffff87120000)
	libz.so.1 => /lib/aarch64-linux-gnu/libz.so.1 (0x0000ffff870f0000)
	libgts-0.7.so.5 => /lib/aarch64-linux-gnu/libgts-0.7.so.5 (0x0000ffff87080000)
	libtinyxml2.so.9 => /lib/aarch64-linux-gnu/libtinyxml2.so.9 (0x0000ffff87050000)
	libglib-2.0.so.0 => /lib/aarch64-linux-gnu/libglib-2.0.so.0 (0x0000ffff86f00000)
	libuuid.so.1 => /lib/aarch64-linux-gnu/libuuid.so.1 (0x0000ffff86ee0000)
	libfreetype.so.6 => /lib/aarch64-linux-gnu/libfreetype.so.6 (0x0000ffff86e10000)
	libxcb.so.1 => /lib/aarch64-linux-gnu/libxcb.so.1 (0x0000ffff86dd0000)
	libSM.so.6 => /lib/aarch64-linux-gnu/libSM.so.6 (0x0000ffff86db0000)
	libICE.so.6 => /lib/aarch64-linux-gnu/libICE.so.6 (0x0000ffff86d80000)
	libXext.so.6 => /lib/aarch64-linux-gnu/libXext.so.6 (0x0000ffff86d50000)
	libXmu.so.6 => /lib/aarch64-linux-gnu/libXmu.so.6 (0x0000ffff86d20000)
	libXpm.so.4 => /lib/aarch64-linux-gnu/libXpm.so.4 (0x0000ffff86cf0000)
	libXrender.so.1 => /lib/aarch64-linux-gnu/libXrender.so.1 (0x0000ffff86cd0000)
	libjxrglue.so.0 => /lib/aarch64-linux-gnu/libjxrglue.so.0 (0x0000ffff86c90000)
	libjpeg.so.8 => /lib/aarch64-linux-gnu/libjpeg.so.8 (0x0000ffff86c30000)
	libopenjp2.so.7 => /lib/aarch64-linux-gnu/libopenjp2.so.7 (0x0000ffff86bc0000)
	libpng16.so.16 => /lib/aarch64-linux-gnu/libpng16.so.16 (0x0000ffff86b70000)
	libraw.so.20 => /lib/aarch64-linux-gnu/libraw.so.20 (0x0000ffff86a60000)
	libtiff.so.5 => /lib/aarch64-linux-gnu/libtiff.so.5 (0x0000ffff869d0000)
	libwebpmux.so.3 => /lib/aarch64-linux-gnu/libwebpmux.so.3 (0x0000ffff869b0000)
	libwebp.so.7 => /lib/aarch64-linux-gnu/libwebp.so.7 (0x0000ffff86950000)
	libIlmImf-2_5.so.25 => /lib/aarch64-linux-gnu/libIlmImf-2_5.so.25 (0x0000ffff86690000)
	libHalf-2_5.so.25 => /lib/aarch64-linux-gnu/libHalf-2_5.so.25 (0x0000ffff86630000)
	libIex-2_5.so.25 => /lib/aarch64-linux-gnu/libIex-2_5.so.25 (0x0000ffff865a0000)
	libpcre.so.3 => /lib/aarch64-linux-gnu/libpcre.so.3 (0x0000ffff86520000)
	libbrotlidec.so.1 => /lib/aarch64-linux-gnu/libbrotlidec.so.1 (0x0000ffff86500000)
	libXau.so.6 => /lib/aarch64-linux-gnu/libXau.so.6 (0x0000ffff864e0000)
	libXdmcp.so.6 => /lib/aarch64-linux-gnu/libXdmcp.so.6 (0x0000ffff864c0000)
	libbsd.so.0 => /lib/aarch64-linux-gnu/libbsd.so.0 (0x0000ffff86490000)
	libjpegxr.so.0 => /lib/aarch64-linux-gnu/libjpegxr.so.0 (0x0000ffff86450000)
	liblcms2.so.2 => /lib/aarch64-linux-gnu/liblcms2.so.2 (0x0000ffff863e0000)
	libgomp.so.1 => /lib/aarch64-linux-gnu/libgomp.so.1 (0x0000ffff86380000)
	libzstd.so.1 => /lib/aarch64-linux-gnu/libzstd.so.1 (0x0000ffff862b0000)
	liblzma.so.5 => /lib/aarch64-linux-gnu/liblzma.so.5 (0x0000ffff86270000)
	libjbig.so.0 => /lib/aarch64-linux-gnu/libjbig.so.0 (0x0000ffff86250000)
	libdeflate.so.0 => /lib/aarch64-linux-gnu/libdeflate.so.0 (0x0000ffff86220000)
	libImath-2_5.so.25 => /lib/aarch64-linux-gnu/libImath-2_5.so.25 (0x0000ffff861f0000)
	libIlmThread-2_5.so.25 => /lib/aarch64-linux-gnu/libIlmThread-2_5.so.25 (0x0000ffff861d0000)
	libbrotlicommon.so.1 => /lib/aarch64-linux-gnu/libbrotlicommon.so.1 (0x0000ffff86190000)
	libmd.so.0 => /lib/aarch64-linux-gnu/libmd.so.0 (0x0000ffff86170000)
	linux-vdso.so.1 (0x0000ffff954c8000)
	libignition-rendering6.so.6 => /lib/aarch64-linux-gnu/libignition-rendering6.so.6 (0x0000ffff95120000)
	libOpenGL.so.0 => /lib/aarch64-linux-gnu/libOpenGL.so.0 (0x0000ffff950b0000)
	libGLX.so.0 => /lib/aarch64-linux-gnu/libGLX.so.0 (0x0000ffff95060000)
	libOgreNextMain.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextMain.so.2.2.5 (0x0000ffff94b70000)
	libignition-common4-graphics.so.4 => /lib/aarch64-linux-gnu/libignition-common4-graphics.so.4 (0x0000ffff94ab0000)
	libignition-common4-events.so.4 => /lib/aarch64-linux-gnu/libignition-common4-events.so.4 (0x0000ffff94a80000)
	libignition-common4.so.4 => /lib/aarch64-linux-gnu/libignition-common4.so.4 (0x0000ffff94a10000)
	libignition-math6.so.6 => /lib/aarch64-linux-gnu/libignition-math6.so.6 (0x0000ffff949b0000)
	libOgreNextHlmsPbs.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextHlmsPbs.so.2.2.5 (0x0000ffff94920000)
	libOgreNextHlmsUnlit.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextHlmsUnlit.so.2.2.5 (0x0000ffff948e0000)
	libOgreNextOverlay.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextOverlay.so.2.2.5 (0x0000ffff94880000)
	libOgreNextPlanarReflections.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextPlanarReflections.so.2.2.5 (0x0000ffff94860000)
	libstdc++.so.6 => /lib/aarch64-linux-gnu/libstdc++.so.6 (0x0000ffff94630000)
	libm.so.6 => /lib/aarch64-linux-gnu/libm.so.6 (0x0000ffff94590000)
	libgcc_s.so.1 => /lib/aarch64-linux-gnu/libgcc_s.so.1 (0x0000ffff94560000)
	libc.so.6 => /lib/aarch64-linux-gnu/libc.so.6 (0x0000ffff943b0000)
	/lib/ld-linux-aarch64.so.1 (0x0000ffff95490000)
	libignition-plugin1-loader.so.1 => /lib/aarch64-linux-gnu/libignition-plugin1-loader.so.1 (0x0000ffff94390000)
	libignition-plugin1.so.1 => /lib/aarch64-linux-gnu/libignition-plugin1.so.1 (0x0000ffff94370000)
	libGLdispatch.so.0 => /lib/aarch64-linux-gnu/libGLdispatch.so.0 (0x0000ffff941e0000)
	libX11.so.6 => /lib/aarch64-linux-gnu/libX11.so.6 (0x0000ffff94090000)
	libXt.so.6 => /lib/aarch64-linux-gnu/libXt.so.6 (0x0000ffff94010000)
	libXaw.so.7 => /lib/aarch64-linux-gnu/libXaw.so.7 (0x0000ffff93f90000)
	libXrandr.so.2 => /lib/aarch64-linux-gnu/libXrandr.so.2 (0x0000ffff93f70000)
	libfreeimage.so.3 => /lib/aarch64-linux-gnu/libfreeimage.so.3 (0x0000ffff93eb0000)
	libzzip-0.so.13 => /lib/aarch64-linux-gnu/libzzip-0.so.13 (0x0000ffff93e90000)
	libz.so.1 => /lib/aarch64-linux-gnu/libz.so.1 (0x0000ffff93e60000)
	libgts-0.7.so.5 => /lib/aarch64-linux-gnu/libgts-0.7.so.5 (0x0000ffff93df0000)
	libtinyxml2.so.9 => /lib/aarch64-linux-gnu/libtinyxml2.so.9 (0x0000ffff93dc0000)
	libglib-2.0.so.0 => /lib/aarch64-linux-gnu/libglib-2.0.so.0 (0x0000ffff93c70000)
	libuuid.so.1 => /lib/aarch64-linux-gnu/libuuid.so.1 (0x0000ffff93c50000)
	libfreetype.so.6 => /lib/aarch64-linux-gnu/libfreetype.so.6 (0x0000ffff93b80000)
	libxcb.so.1 => /lib/aarch64-linux-gnu/libxcb.so.1 (0x0000ffff93b40000)
	libSM.so.6 => /lib/aarch64-linux-gnu/libSM.so.6 (0x0000ffff93b20000)
	libICE.so.6 => /lib/aarch64-linux-gnu/libICE.so.6 (0x0000ffff93af0000)
	libXext.so.6 => /lib/aarch64-linux-gnu/libXext.so.6 (0x0000ffff93ac0000)
	libXmu.so.6 => /lib/aarch64-linux-gnu/libXmu.so.6 (0x0000ffff93a90000)
	libXpm.so.4 => /lib/aarch64-linux-gnu/libXpm.so.4 (0x0000ffff93a60000)
	libXrender.so.1 => /lib/aarch64-linux-gnu/libXrender.so.1 (0x0000ffff93a40000)
	libjxrglue.so.0 => /lib/aarch64-linux-gnu/libjxrglue.so.0 (0x0000ffff93a00000)
	libjpeg.so.8 => /lib/aarch64-linux-gnu/libjpeg.so.8 (0x0000ffff939a0000)
	libopenjp2.so.7 => /lib/aarch64-linux-gnu/libopenjp2.so.7 (0x0000ffff93930000)
	libpng16.so.16 => /lib/aarch64-linux-gnu/libpng16.so.16 (0x0000ffff938e0000)
	libraw.so.20 => /lib/aarch64-linux-gnu/libraw.so.20 (0x0000ffff937d0000)
	libtiff.so.5 => /lib/aarch64-linux-gnu/libtiff.so.5 (0x0000ffff93740000)
	libwebpmux.so.3 => /lib/aarch64-linux-gnu/libwebpmux.so.3 (0x0000ffff93720000)
	libwebp.so.7 => /lib/aarch64-linux-gnu/libwebp.so.7 (0x0000ffff936c0000)
	libIlmImf-2_5.so.25 => /lib/aarch64-linux-gnu/libIlmImf-2_5.so.25 (0x0000ffff93400000)
	libHalf-2_5.so.25 => /lib/aarch64-linux-gnu/libHalf-2_5.so.25 (0x0000ffff933a0000)
	libIex-2_5.so.25 => /lib/aarch64-linux-gnu/libIex-2_5.so.25 (0x0000ffff93310000)
	libpcre.so.3 => /lib/aarch64-linux-gnu/libpcre.so.3 (0x0000ffff93290000)
	libbrotlidec.so.1 => /lib/aarch64-linux-gnu/libbrotlidec.so.1 (0x0000ffff93270000)
	libXau.so.6 => /lib/aarch64-linux-gnu/libXau.so.6 (0x0000ffff93250000)
	libXdmcp.so.6 => /lib/aarch64-linux-gnu/libXdmcp.so.6 (0x0000ffff93230000)
	libbsd.so.0 => /lib/aarch64-linux-gnu/libbsd.so.0 (0x0000ffff93200000)
	libjpegxr.so.0 => /lib/aarch64-linux-gnu/libjpegxr.so.0 (0x0000ffff931c0000)
	liblcms2.so.2 => /lib/aarch64-linux-gnu/liblcms2.so.2 (0x0000ffff93150000)
	libgomp.so.1 => /lib/aarch64-linux-gnu/libgomp.so.1 (0x0000ffff930f0000)
	libzstd.so.1 => /lib/aarch64-linux-gnu/libzstd.so.1 (0x0000ffff93020000)
	liblzma.so.5 => /lib/aarch64-linux-gnu/liblzma.so.5 (0x0000ffff92fe0000)
	libjbig.so.0 => /lib/aarch64-linux-gnu/libjbig.so.0 (0x0000ffff92fc0000)
	libdeflate.so.0 => /lib/aarch64-linux-gnu/libdeflate.so.0 (0x0000ffff92f90000)
	libImath-2_5.so.25 => /lib/aarch64-linux-gnu/libImath-2_5.so.25 (0x0000ffff92f60000)
	libIlmThread-2_5.so.25 => /lib/aarch64-linux-gnu/libIlmThread-2_5.so.25 (0x0000ffff92f40000)
	libbrotlicommon.so.1 => /lib/aarch64-linux-gnu/libbrotlicommon.so.1 (0x0000ffff92f00000)
	libmd.so.0 => /lib/aarch64-linux-gnu/libmd.so.0 (0x0000ffff92ee0000)
	linux-vdso.so.1 (0x0000ffff83a92000)
	libignition-rendering6.so.6 => /lib/aarch64-linux-gnu/libignition-rendering6.so.6 (0x0000ffff836f0000)
	libOpenGL.so.0 => /lib/aarch64-linux-gnu/libOpenGL.so.0 (0x0000ffff83680000)
	libGLX.so.0 => /lib/aarch64-linux-gnu/libGLX.so.0 (0x0000ffff83630000)
	libOgreNextMain.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextMain.so.2.2.5 (0x0000ffff83140000)
	libignition-common4-graphics.so.4 => /lib/aarch64-linux-gnu/libignition-common4-graphics.so.4 (0x0000ffff83080000)
	libignition-common4-events.so.4 => /lib/aarch64-linux-gnu/libignition-common4-events.so.4 (0x0000ffff83050000)
	libignition-common4.so.4 => /lib/aarch64-linux-gnu/libignition-common4.so.4 (0x0000ffff82fe0000)
	libignition-math6.so.6 => /lib/aarch64-linux-gnu/libignition-math6.so.6 (0x0000ffff82f80000)
	libOgreNextHlmsPbs.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextHlmsPbs.so.2.2.5 (0x0000ffff82ef0000)
	libOgreNextHlmsUnlit.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextHlmsUnlit.so.2.2.5 (0x0000ffff82eb0000)
	libOgreNextOverlay.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextOverlay.so.2.2.5 (0x0000ffff82e50000)
	libOgreNextPlanarReflections.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextPlanarReflections.so.2.2.5 (0x0000ffff82e30000)
	libstdc++.so.6 => /lib/aarch64-linux-gnu/libstdc++.so.6 (0x0000ffff82c00000)
	libm.so.6 => /lib/aarch64-linux-gnu/libm.so.6 (0x0000ffff82b60000)
	libgcc_s.so.1 => /lib/aarch64-linux-gnu/libgcc_s.so.1 (0x0000ffff82b30000)
	libc.so.6 => /lib/aarch64-linux-gnu/libc.so.6 (0x0000ffff82980000)
	/lib/ld-linux-aarch64.so.1 (0x0000ffff83a50000)
	libignition-plugin1-loader.so.1 => /lib/aarch64-linux-gnu/libignition-plugin1-loader.so.1 (0x0000ffff82960000)
	libignition-plugin1.so.1 => /lib/aarch64-linux-gnu/libignition-plugin1.so.1 (0x0000ffff82940000)
	libGLdispatch.so.0 => /lib/aarch64-linux-gnu/libGLdispatch.so.0 (0x0000ffff827b0000)
	libX11.so.6 => /lib/aarch64-linux-gnu/libX11.so.6 (0x0000ffff82660000)
	libXt.so.6 => /lib/aarch64-linux-gnu/libXt.so.6 (0x0000ffff825e0000)
	libXaw.so.7 => /lib/aarch64-linux-gnu/libXaw.so.7 (0x0000ffff82560000)
	libXrandr.so.2 => /lib/aarch64-linux-gnu/libXrandr.so.2 (0x0000ffff82540000)
	libfreeimage.so.3 => /lib/aarch64-linux-gnu/libfreeimage.so.3 (0x0000ffff82480000)
	libzzip-0.so.13 => /lib/aarch64-linux-gnu/libzzip-0.so.13 (0x0000ffff82460000)
	libz.so.1 => /lib/aarch64-linux-gnu/libz.so.1 (0x0000ffff82430000)
	libgts-0.7.so.5 => /lib/aarch64-linux-gnu/libgts-0.7.so.5 (0x0000ffff823c0000)
	libtinyxml2.so.9 => /lib/aarch64-linux-gnu/libtinyxml2.so.9 (0x0000ffff82390000)
	libglib-2.0.so.0 => /lib/aarch64-linux-gnu/libglib-2.0.so.0 (0x0000ffff82240000)
	libuuid.so.1 => /lib/aarch64-linux-gnu/libuuid.so.1 (0x0000ffff82220000)
	libfreetype.so.6 => /lib/aarch64-linux-gnu/libfreetype.so.6 (0x0000ffff82150000)
	libxcb.so.1 => /lib/aarch64-linux-gnu/libxcb.so.1 (0x0000ffff82110000)
	libSM.so.6 => /lib/aarch64-linux-gnu/libSM.so.6 (0x0000ffff820f0000)
	libICE.so.6 => /lib/aarch64-linux-gnu/libICE.so.6 (0x0000ffff820c0000)
	libXext.so.6 => /lib/aarch64-linux-gnu/libXext.so.6 (0x0000ffff82090000)
	libXmu.so.6 => /lib/aarch64-linux-gnu/libXmu.so.6 (0x0000ffff82060000)
	libXpm.so.4 => /lib/aarch64-linux-gnu/libXpm.so.4 (0x0000ffff82030000)
	libXrender.so.1 => /lib/aarch64-linux-gnu/libXrender.so.1 (0x0000ffff82010000)
	libjxrglue.so.0 => /lib/aarch64-linux-gnu/libjxrglue.so.0 (0x0000ffff81fd0000)
	libjpeg.so.8 => /lib/aarch64-linux-gnu/libjpeg.so.8 (0x0000ffff81f70000)
	libopenjp2.so.7 => /lib/aarch64-linux-gnu/libopenjp2.so.7 (0x0000ffff81f00000)
	libpng16.so.16 => /lib/aarch64-linux-gnu/libpng16.so.16 (0x0000ffff81eb0000)
	libraw.so.20 => /lib/aarch64-linux-gnu/libraw.so.20 (0x0000ffff81da0000)
	libtiff.so.5 => /lib/aarch64-linux-gnu/libtiff.so.5 (0x0000ffff81d10000)
	libwebpmux.so.3 => /lib/aarch64-linux-gnu/libwebpmux.so.3 (0x0000ffff81cf0000)
	libwebp.so.7 => /lib/aarch64-linux-gnu/libwebp.so.7 (0x0000ffff81c90000)
	libIlmImf-2_5.so.25 => /lib/aarch64-linux-gnu/libIlmImf-2_5.so.25 (0x0000ffff819d0000)
	libHalf-2_5.so.25 => /lib/aarch64-linux-gnu/libHalf-2_5.so.25 (0x0000ffff81970000)
	libIex-2_5.so.25 => /lib/aarch64-linux-gnu/libIex-2_5.so.25 (0x0000ffff818e0000)
	libpcre.so.3 => /lib/aarch64-linux-gnu/libpcre.so.3 (0x0000ffff81860000)
	libbrotlidec.so.1 => /lib/aarch64-linux-gnu/libbrotlidec.so.1 (0x0000ffff81840000)
	libXau.so.6 => /lib/aarch64-linux-gnu/libXau.so.6 (0x0000ffff81820000)
	libXdmcp.so.6 => /lib/aarch64-linux-gnu/libXdmcp.so.6 (0x0000ffff81800000)
	libbsd.so.0 => /lib/aarch64-linux-gnu/libbsd.so.0 (0x0000ffff817d0000)
	libjpegxr.so.0 => /lib/aarch64-linux-gnu/libjpegxr.so.0 (0x0000ffff81790000)
	liblcms2.so.2 => /lib/aarch64-linux-gnu/liblcms2.so.2 (0x0000ffff81720000)
	libgomp.so.1 => /lib/aarch64-linux-gnu/libgomp.so.1 (0x0000ffff816c0000)
	libzstd.so.1 => /lib/aarch64-linux-gnu/libzstd.so.1 (0x0000ffff815f0000)
	liblzma.so.5 => /lib/aarch64-linux-gnu/liblzma.so.5 (0x0000ffff815b0000)
	libjbig.so.0 => /lib/aarch64-linux-gnu/libjbig.so.0 (0x0000ffff81590000)
	libdeflate.so.0 => /lib/aarch64-linux-gnu/libdeflate.so.0 (0x0000ffff81560000)
	libImath-2_5.so.25 => /lib/aarch64-linux-gnu/libImath-2_5.so.25 (0x0000ffff81530000)
	libIlmThread-2_5.so.25 => /lib/aarch64-linux-gnu/libIlmThread-2_5.so.25 (0x0000ffff81510000)
	libbrotlicommon.so.1 => /lib/aarch64-linux-gnu/libbrotlicommon.so.1 (0x0000ffff814d0000)
	libmd.so.0 => /lib/aarch64-linux-gnu/libmd.so.0 (0x0000ffff814b0000)
	linux-vdso.so.1 (0x0000ffffb1736000)
	libignition-rendering6.so.6 => /lib/aarch64-linux-gnu/libignition-rendering6.so.6 (0x0000ffffb1390000)
	libOpenGL.so.0 => /lib/aarch64-linux-gnu/libOpenGL.so.0 (0x0000ffffb1320000)
	libGLX.so.0 => /lib/aarch64-linux-gnu/libGLX.so.0 (0x0000ffffb12d0000)
	libOgreNextMain.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextMain.so.2.2.5 (0x0000ffffb0de0000)
	libignition-common4-graphics.so.4 => /lib/aarch64-linux-gnu/libignition-common4-graphics.so.4 (0x0000ffffb0d20000)
	libignition-common4-events.so.4 => /lib/aarch64-linux-gnu/libignition-common4-events.so.4 (0x0000ffffb0cf0000)
	libignition-common4.so.4 => /lib/aarch64-linux-gnu/libignition-common4.so.4 (0x0000ffffb0c80000)
	libignition-math6.so.6 => /lib/aarch64-linux-gnu/libignition-math6.so.6 (0x0000ffffb0c20000)
	libOgreNextHlmsPbs.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextHlmsPbs.so.2.2.5 (0x0000ffffb0b90000)
	libOgreNextHlmsUnlit.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextHlmsUnlit.so.2.2.5 (0x0000ffffb0b50000)
	libOgreNextOverlay.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextOverlay.so.2.2.5 (0x0000ffffb0af0000)
	libOgreNextPlanarReflections.so.2.2.5 => /lib/aarch64-linux-gnu/libOgreNextPlanarReflections.so.2.2.5 (0x0000ffffb0ad0000)
	libstdc++.so.6 => /lib/aarch64-linux-gnu/libstdc++.so.6 (0x0000ffffb08a0000)
	libm.so.6 => /lib/aarch64-linux-gnu/libm.so.6 (0x0000ffffb0800000)
	libgcc_s.so.1 => /lib/aarch64-linux-gnu/libgcc_s.so.1 (0x0000ffffb07d0000)
	libc.so.6 => /lib/aarch64-linux-gnu/libc.so.6 (0x0000ffffb0620000)
	/lib/ld-linux-aarch64.so.1 (0x0000ffffb16f0000)
	libignition-plugin1-loader.so.1 => /lib/aarch64-linux-gnu/libignition-plugin1-loader.so.1 (0x0000ffffb0600000)
	libignition-plugin1.so.1 => /lib/aarch64-linux-gnu/libignition-plugin1.so.1 (0x0000ffffb05e0000)
	libGLdispatch.so.0 => /lib/aarch64-linux-gnu/libGLdispatch.so.0 (0x0000ffffb0450000)
	libX11.so.6 => /lib/aarch64-linux-gnu/libX11.so.6 (0x0000ffffb0300000)
	libXt.so.6 => /lib/aarch64-linux-gnu/libXt.so.6 (0x0000ffffb0280000)
	libXaw.so.7 => /lib/aarch64-linux-gnu/libXaw.so.7 (0x0000ffffb0200000)
	libXrandr.so.2 => /lib/aarch64-linux-gnu/libXrandr.so.2 (0x0000ffffb01e0000)
	libfreeimage.so.3 => /lib/aarch64-linux-gnu/libfreeimage.so.3 (0x0000ffffb0120000)
	libzzip-0.so.13 => /lib/aarch64-linux-gnu/libzzip-0.so.13 (0x0000ffffb0100000)
	libz.so.1 => /lib/aarch64-linux-gnu/libz.so.1 (0x0000ffffb00d0000)
	libgts-0.7.so.5 => /lib/aarch64-linux-gnu/libgts-0.7.so.5 (0x0000ffffb0060000)
	libtinyxml2.so.9 => /lib/aarch64-linux-gnu/libtinyxml2.so.9 (0x0000ffffb0030000)
	libglib-2.0.so.0 => /lib/aarch64-linux-gnu/libglib-2.0.so.0 (0x0000ffffafee0000)
	libuuid.so.1 => /lib/aarch64-linux-gnu/libuuid.so.1 (0x0000ffffafec0000)
	libfreetype.so.6 => /lib/aarch64-linux-gnu/libfreetype.so.6 (0x0000ffffafdf0000)
	libxcb.so.1 => /lib/aarch64-linux-gnu/libxcb.so.1 (0x0000ffffafdb0000)
	libSM.so.6 => /lib/aarch64-linux-gnu/libSM.so.6 (0x0000ffffafd90000)
	libICE.so.6 => /lib/aarch64-linux-gnu/libICE.so.6 (0x0000ffffafd60000)
	libXext.so.6 => /lib/aarch64-linux-gnu/libXext.so.6 (0x0000ffffafd30000)
	libXmu.so.6 => /lib/aarch64-linux-gnu/libXmu.so.6 (0x0000ffffafd00000)
	libXpm.so.4 => /lib/aarch64-linux-gnu/libXpm.so.4 (0x0000ffffafcd0000)
	libXrender.so.1 => /lib/aarch64-linux-gnu/libXrender.so.1 (0x0000ffffafcb0000)
	libjxrglue.so.0 => /lib/aarch64-linux-gnu/libjxrglue.so.0 (0x0000ffffafc70000)
	libjpeg.so.8 => /lib/aarch64-linux-gnu/libjpeg.so.8 (0x0000ffffafc10000)
	libopenjp2.so.7 => /lib/aarch64-linux-gnu/libopenjp2.so.7 (0x0000ffffafba0000)
	libpng16.so.16 => /lib/aarch64-linux-gnu/libpng16.so.16 (0x0000ffffafb50000)
	libraw.so.20 => /lib/aarch64-linux-gnu/libraw.so.20 (0x0000ffffafa40000)
	libtiff.so.5 => /lib/aarch64-linux-gnu/libtiff.so.5 (0x0000ffffaf9b0000)
	libwebpmux.so.3 => /lib/aarch64-linux-gnu/libwebpmux.so.3 (0x0000ffffaf990000)
	libwebp.so.7 => /lib/aarch64-linux-gnu/libwebp.so.7 (0x0000ffffaf930000)
	libIlmImf-2_5.so.25 => /lib/aarch64-linux-gnu/libIlmImf-2_5.so.25 (0x0000ffffaf670000)
	libHalf-2_5.so.25 => /lib/aarch64-linux-gnu/libHalf-2_5.so.25 (0x0000ffffaf610000)
	libIex-2_5.so.25 => /lib/aarch64-linux-gnu/libIex-2_5.so.25 (0x0000ffffaf580000)
	libpcre.so.3 => /lib/aarch64-linux-gnu/libpcre.so.3 (0x0000ffffaf500000)
	libbrotlidec.so.1 => /lib/aarch64-linux-gnu/libbrotlidec.so.1 (0x0000ffffaf4e0000)
	libXau.so.6 => /lib/aarch64-linux-gnu/libXau.so.6 (0x0000ffffaf4c0000)
	libXdmcp.so.6 => /lib/aarch64-linux-gnu/libXdmcp.so.6 (0x0000ffffaf4a0000)
	libbsd.so.0 => /lib/aarch64-linux-gnu/libbsd.so.0 (0x0000ffffaf470000)
	libjpegxr.so.0 => /lib/aarch64-linux-gnu/libjpegxr.so.0 (0x0000ffffaf430000)
	liblcms2.so.2 => /lib/aarch64-linux-gnu/liblcms2.so.2 (0x0000ffffaf3c0000)
	libgomp.so.1 => /lib/aarch64-linux-gnu/libgomp.so.1 (0x0000ffffaf360000)
	libzstd.so.1 => /lib/aarch64-linux-gnu/libzstd.so.1 (0x0000ffffaf290000)
	liblzma.so.5 => /lib/aarch64-linux-gnu/liblzma.so.5 (0x0000ffffaf250000)
	libjbig.so.0 => /lib/aarch64-linux-gnu/libjbig.so.0 (0x0000ffffaf230000)
	libdeflate.so.0 => /lib/aarch64-linux-gnu/libdeflate.so.0 (0x0000ffffaf200000)
	libImath-2_5.so.25 => /lib/aarch64-linux-gnu/libImath-2_5.so.25 (0x0000ffffaf1d0000)
	libIlmThread-2_5.so.25 => /lib/aarch64-linux-gnu/libIlmThread-2_5.so.25 (0x0000ffffaf1b0000)
	libbrotlicommon.so.1 => /lib/aarch64-linux-gnu/libbrotlicommon.so.1 (0x0000ffffaf170000)
	libmd.so.0 => /lib/aarch64-linux-gnu/libmd.so.0 (0x0000ffffaf150000)

```

## versions

```sh
docker run --rm ros2-fleet-simulation-lidar-check:humble-fortress bash -c 'cat /etc/os-release; dpkg-query -W ignition-tools libignition-gazebo6 libignition-gazebo6-plugins libignition-rendering6 libignition-rendering6-ogre2 libignition-sensors6-gpu-lidar libogrenextmain2.2.5 libegl-mesa0 libgl1-mesa-dri libllvm15 ros-humble-ros-gz-bridge ros-humble-ros-base ros-humble-rclpy ros-humble-cyclonedds ros-humble-rmw-cyclonedds-cpp python3-jsonschema; ign gazebo --versions; python3 --version'
```

Çıkış kodu: 0

```text
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.5 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy
ignition-tools:arm64	1.5.0-1~jammy
libegl-mesa0:arm64	23.2.1-1ubuntu3.1~22.04.4
libgl1-mesa-dri:arm64	23.2.1-1ubuntu3.1~22.04.4
libignition-gazebo6:arm64	6.18.0-1~jammy
libignition-gazebo6-plugins:arm64	6.18.0-1~jammy
libignition-rendering6:arm64	6.6.4-1~jammy
libignition-rendering6-ogre2:arm64	6.6.4-1~jammy
libignition-sensors6-gpu-lidar:arm64	6.9.0-1~jammy
libllvm15:arm64	1:15.0.7-0ubuntu0.22.04.3
libogrenextmain2.2.5:arm64	2.2.5+dfsg3-0ubuntu2
python3-jsonschema	3.2.0-0ubuntu2
ros-humble-cyclonedds	0.10.5-2jammy.20260307.131623
ros-humble-rclpy	3.3.22-1jammy.20260907.232408
ros-humble-rmw-cyclonedds-cpp	1.3.5-1jammy.20260907.211615
ros-humble-ros-base	0.10.0-1jammy.20260916.125240
ros-humble-ros-gz-bridge	0.244.26-1jammy.20260916.153147
6.18.0
Python 3.10.12

```

## run-image

```sh
docker image inspect ros2-fleet-simulation-lidar-check:humble-fortress --format '{{.Id}} {{json .RepoDigests}} {{.Os}}/{{.Architecture}}'
```

Çıkış kodu: 0

```text
sha256:3047a642208db50e5f5f1295384acdf0bbdf23db7c10f6bab2ccca822541d815 ["ros2-fleet-simulation-lidar-check@sha256:3047a642208db50e5f5f1295384acdf0bbdf23db7c10f6bab2ccca822541d815"] linux/arm64

```

## run-containers

```sh
docker inspect ros2-fleet-simulation-lidar-check-backend-1 ros2-fleet-simulation-lidar-check-simulation-1 --format '{{.Name}} image={{.Image}} status={{.State.Status}} exit={{.State.ExitCode}} networks={{json .NetworkSettings.Networks}} mounts={{json .Mounts}}'
```

Çıkış kodu: 0

```text
/ros2-fleet-simulation-lidar-check-backend-1 image=sha256:3047a642208db50e5f5f1295384acdf0bbdf23db7c10f6bab2ccca822541d815 status=exited exit=1 networks={"ros2-fleet-simulation-lidar-check_dds":{"IPAMConfig":null,"Links":null,"Aliases":["ros2-fleet-simulation-lidar-check-backend-1","backend"],"DriverOpts":null,"GwPriority":0,"NetworkID":"8f8e6525118ac87708ff5e9d3c5771493895d342466cf7ca22294089489841d5","EndpointID":"","Gateway":"","IPAddress":"","MacAddress":"","IPPrefixLen":0,"IPv6Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"DNSNames":["ros2-fleet-simulation-lidar-check-backend-1","backend","b30afeaa6045"]}} mounts=[{"Type":"bind","Source":"/Users/murat/develop/ros2-fleet-manager/config","Destination":"/config","Mode":"ro","RW":false,"Propagation":"rprivate"}]
/ros2-fleet-simulation-lidar-check-simulation-1 image=sha256:3047a642208db50e5f5f1295384acdf0bbdf23db7c10f6bab2ccca822541d815 status=exited exit=1 networks={"ros2-fleet-simulation-lidar-check_dds":{"IPAMConfig":null,"Links":null,"Aliases":["ros2-fleet-simulation-lidar-check-simulation-1","simulation"],"DriverOpts":null,"GwPriority":0,"NetworkID":"8f8e6525118ac87708ff5e9d3c5771493895d342466cf7ca22294089489841d5","EndpointID":"","Gateway":"","IPAddress":"","MacAddress":"","IPPrefixLen":0,"IPv6Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"DNSNames":["ros2-fleet-simulation-lidar-check-simulation-1","simulation","45a0b865516e"]}} mounts=[{"Type":"bind","Source":"/Users/murat/develop/ros2-fleet-manager/config","Destination":"/config","Mode":"ro","RW":false,"Propagation":"rprivate"}]

```

## down-b1

```sh
env DDS_TEST_PAYLOAD=simulation-b1-20261023-01 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml down
```

Çıkış kodu: 0

```text
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopping
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopping
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopped
 Container ros2-fleet-simulation-lidar-check-backend-1 Removing
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopped
 Container ros2-fleet-simulation-lidar-check-simulation-1 Removing
 Container ros2-fleet-simulation-lidar-check-simulation-1 Removed
 Container ros2-fleet-simulation-lidar-check-backend-1 Removed
 Network ros2-fleet-simulation-lidar-check_dds Removing
 Network ros2-fleet-simulation-lidar-check_dds Removed

```

## cleanup-containers

```sh
docker ps -a --filter label=com.docker.compose.project=ros2-fleet-simulation-lidar-check
```

Çıkış kodu: 0

```text
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES

```

## cleanup-network

```sh
docker network ls --filter name=ros2-fleet-simulation-lidar-check
```

Çıkış kodu: 0

```text
NETWORK ID   NAME      DRIVER    SCOPE

```

## build-final-harness

```sh
env DDS_TEST_PAYLOAD=simulation-b1-build docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml build simulation
```

Çıkış kodu: 0

```text
 Image ros2-fleet-simulation-lidar-check:humble-fortress Building
#1 [internal] load local bake definitions
#1 reading from stdin 633B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 344B done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/ros2-fleet-simulation-check:humble-fortress
#3 DONE 0.0s

#4 [internal] load .dockerignore
#4 transferring context: 2B done
#4 DONE 0.0s

#5 [internal] load build context
#5 transferring context: 26.89kB done
#5 DONE 0.0s

#6 [1/3] FROM docker.io/library/ros2-fleet-simulation-check:humble-fortress@sha256:69cb7989a1a325add4f0ca325f4fa1e002beb4f2ffd415d59f1efd4e32151b39
#6 resolve docker.io/library/ros2-fleet-simulation-check:humble-fortress@sha256:69cb7989a1a325add4f0ca325f4fa1e002beb4f2ffd415d59f1efd4e32151b39 done
#6 DONE 0.0s

#7 [2/3] RUN apt-get update && apt-get install -y --no-install-recommends     libignition-rendering6-ogre2     && rm -rf /var/lib/apt/lists/*
#7 CACHED

#8 [3/3] COPY docker/simulation-lidar-check /opt/simulation-lidar-check
#8 DONE 0.0s

#9 exporting to image
#9 exporting layers 0.0s done
#9 exporting manifest sha256:e6a3c0b136618d656457c876c6ec7016b79016e4d1e7319b2d62cfb91b8b85e1 done
#9 exporting config sha256:fe1e6f81bbf4a68b636bf17e02937edb5b1a313ed5739e19c0362f493c894d06 done
#9 exporting attestation manifest sha256:ebc2f462e3117c9ce6d02eb6cf1f0cb9adadb4c12e735f47353eb36acbafb1fb done
#9 exporting manifest list sha256:b9ffcb90dba3c04e607a9e6ad5fbc328c0b09d40a6e5cdb7856dc34f75a3749a
#9 exporting manifest list sha256:b9ffcb90dba3c04e607a9e6ad5fbc328c0b09d40a6e5cdb7856dc34f75a3749a done
#9 naming to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress done
#9 unpacking to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress done
#9 DONE 0.1s

#10 resolving provenance for metadata file
#10 DONE 0.0s
 Image ros2-fleet-simulation-lidar-check:humble-fortress Built

```

## build-source-only

```sh
env DDS_TEST_PAYLOAD=simulation-b1-build docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml build simulation
```

Çıkış kodu: 0

```text
 Image ros2-fleet-simulation-lidar-check:humble-fortress Building
#1 [internal] load local bake definitions
#1 reading from stdin 633B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 350B done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/ros2-fleet-simulation-check:humble-fortress
#3 DONE 0.0s

#4 [internal] load .dockerignore
#4 transferring context: 2B done
#4 DONE 0.0s

#5 [1/3] FROM docker.io/library/ros2-fleet-simulation-check:humble-fortress@sha256:69cb7989a1a325add4f0ca325f4fa1e002beb4f2ffd415d59f1efd4e32151b39
#5 resolve docker.io/library/ros2-fleet-simulation-check:humble-fortress@sha256:69cb7989a1a325add4f0ca325f4fa1e002beb4f2ffd415d59f1efd4e32151b39 done
#5 DONE 0.0s

#6 [2/3] RUN apt-get update && apt-get install -y --no-install-recommends     libignition-rendering6-ogre2     && rm -rf /var/lib/apt/lists/*
#6 CACHED

#7 [internal] load build context
#7 transferring context: 199B done
#7 DONE 0.0s

#8 [3/3] COPY docker/simulation-lidar-check/*.py /opt/simulation-lidar-check/
#8 DONE 0.0s

#9 exporting to image
#9 exporting layers 0.0s done
#9 exporting manifest sha256:1a9706b4ad50278b5012714cac1cfd96f55fe503ecd733757273edc8a17a2822 done
#9 exporting config sha256:add4e7b81ea2518e120715088ff9466cfc8d647e78b2fe882a3d61bd097d90d9 done
#9 exporting attestation manifest sha256:92c10833a985b34ef476ee80e913dcde7967ad09c360dabcd6da46ffd42839a2 done
#9 exporting manifest list sha256:5108ed0398fd0ba7b57865a1bea1f1ca2feb4a29f69ad8e276546b597a4b6a31 done
#9 naming to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress done
#9 unpacking to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress done
#9 DONE 0.0s

#10 resolving provenance for metadata file
#10 DONE 0.0s
 Image ros2-fleet-simulation-lidar-check:humble-fortress Built

```

## final-config-tests

```sh
docker run --rm --env-file config/dds.env -e DDS_TEST_PAYLOAD=b1-config -e SIM_CHECK_ROLE=backend -v /Users/murat/develop/ros2-fleet-manager/config:/config:ro ros2-fleet-simulation-lidar-check:humble-fortress python3 /opt/simulation-lidar-check/test_config.py
```

Çıkış kodu: 0

```text
..
----------------------------------------------------------------------
Ran 2 tests in 0.030s

OK

```

## final-image

```sh
docker image inspect ros2-fleet-simulation-lidar-check:humble-fortress --format '{{.Id}} {{json .RepoDigests}} {{.Os}}/{{.Architecture}}'
```

Çıkış kodu: 0

```text
sha256:5108ed0398fd0ba7b57865a1bea1f1ca2feb4a29f69ad8e276546b597a4b6a31 ["ros2-fleet-simulation-lidar-check@sha256:5108ed0398fd0ba7b57865a1bea1f1ca2feb4a29f69ad8e276546b597a4b6a31"] linux/arm64

```

## final-diff-check

```sh
git diff --check
```

Çıkış kodu: 0

```text

```

## tracked-files-unchanged

```sh
git diff --stat
```

Çıkış kodu: 0

```text

```
