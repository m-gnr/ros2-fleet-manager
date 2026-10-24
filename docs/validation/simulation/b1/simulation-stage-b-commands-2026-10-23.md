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

## iteration-02-diagnosis

```sh
docker run --rm ros2-fleet-simulation-lidar-check:humble-fortress bash -c '
ls -la /usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/
python3 -c "
import ctypes
for path in [
    \"libignition-rendering-ogre2.so\",
    \"libignition-rendering6-ogre2.so\",
    \"/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6\",
    \"/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6.6.4\"
]:
    try:
        ctypes.CDLL(path)
        print(\"OK:\", path)
    except Exception as e:
        print(\"FAIL:\", path, \":\", e)
"
'
```

Çıkış kodu: 0

```text
total 2816
drwxr-xr-x 2 root root    4096 Oct 23 07:49 .
drwxr-xr-x 3 root root    4096 Oct 23 07:49 ..
lrwxrwxrwx 1 root root      37 Jan 29  2026 libignition-rendering6-ogre2.so.6 -> libignition-rendering6-ogre2.so.6.6.4
-rw-r--r-- 1 root root 2874744 Jan 29  2026 libignition-rendering6-ogre2.so.6.6.4
FAIL: libignition-rendering-ogre2.so : libignition-rendering-ogre2.so: cannot open shared object file: No such file or directory
FAIL: libignition-rendering6-ogre2.so : libignition-rendering6-ogre2.so: cannot open shared object file: No such file or directory
OK: /usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6
OK: /usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6.6.4

```

## iteration-02-build

```sh
env DDS_TEST_PAYLOAD=simulation-b1-build docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml build simulation
```

Çıkış kodu: 0

```text
[+] Building 0.7s (10/10) FINISHED
 => [internal] load local bake definitions                                 0.0s
 => => reading from stdin 633B                                             0.0s
 => [internal] load build definition from Dockerfile                       0.0s
 => => transferring dockerfile: 350B                                       0.0s
 => [internal] load metadata for docker.io/library/ros2-fleet-simulation-check:humble-fortress  0.4s
 => [internal] load .dockerignore                                          0.0s
 => => transferring context: 2B                                            0.0s
 => [internal] load build context                                          0.0s
 => => transferring context: 9.61kB                                        0.0s
 => [1/3] FROM docker.io/library/ros2-fleet-simulation-check:humble-fortress  0.0s
 => => resolve docker.io/library/ros2-fleet-simulation-check:humble-fortress  0.0s
 => CACHED [2/3] RUN apt-get update && apt-get install -y --no-install-recommends libignition-rendering6-ogre2 && rm -rf /var/lib/apt/lists/*  0.0s
 => [3/3] COPY docker/simulation-lidar-check/*.py /opt/simulation-lidar-check/  0.0s
 => exporting to image                                                     0.1s
 => => exporting layers                                                    0.0s
 => => exporting manifest sha256:a36b61ff1e6c26f5f2df1d9a992734466314ea24  0.0s
 => => exporting config sha256:3f4b5f68ccf229f0ebc90f54ef5c229527ccbc22fd  0.0s
 => => exporting attestation manifest sha256:a251e8c6608dc7a5493cee4e684a  0.0s
 => => exporting manifest list sha256:b61a40e60409a13f50c91d048d54be25121  0.0s
 => => naming to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress  0.0s
 => => unpacking to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress  0.0s
 => resolving provenance for metadata file                                 0.0s
[+] build 1/1
 ✔ Image ros2-fleet-simulation-lidar-check:humble-fortress Built            0.8s

```

## iteration-02-image

```sh
docker image inspect ros2-fleet-simulation-lidar-check:humble-fortress --format '{{.Id}} {{json .RepoDigests}} {{.Os}}/{{.Architecture}}'
```

Çıkış kodu: 0

```text
sha256:b61a40e60409a13f50c91d048d54be25121ac8c734d876a8e67db54886eeaacc ["ros2-fleet-simulation-lidar-check@sha256:b61a40e60409a13f50c91d048d54be25121ac8c734d876a8e67db54886eeaacc"] linux/arm64

```

## iteration-02-config-tests

```sh
docker run --rm --env-file config/dds.env -e DDS_TEST_PAYLOAD=b1-config -e SIM_CHECK_ROLE=backend -v /Users/murat/develop/ros2-fleet-manager/config:/config:ro -v /Users/murat/develop/ros2-fleet-manager/docker/simulation-lidar-check:/opt/simulation-lidar-check:ro ros2-fleet-simulation-lidar-check:humble-fortress python3 /opt/simulation-lidar-check/test_config.py
```

Çıkış kodu: 0

```text
..
----------------------------------------------------------------------
Ran 2 tests in 0.020s

OK

```

## run-b1-02

```sh
env DDS_TEST_PAYLOAD=simulation-b1-20261023-02 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml up --abort-on-container-exit --exit-code-from backend
```

Çıkış kodu: 1

```text
 ✔ Network ros2-fleet-simulation-lidar-check_dds            Created         0.0s
 ✔ Container ros2-fleet-simulation-lidar-check-simulation-1 Created         0.1s
 ✔ Container ros2-fleet-simulation-lidar-check-backend-1    Created         0.0s
Attaching to backend-1, simulation-1
backend-1     | {"event": "CONFIG_VALID", "role": "backend"}
simulation-1  | {"event": "CONFIG_VALID", "role": "simulation"}
simulation-1  | {"event": "PROCESS_START", "command": ["ign", "gazebo", "-s", "-r", "-v", "4", "--headless-rendering", "--physics-engine", "/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5", "--render-engine-server", "/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6", "/tmp/lidar-world.sdf"]}
simulation-1  | {"event": "PROCESS_START", "command": ["ros2", "run", "ros_gz_bridge", "parameter_bridge", "/validation_robot/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan", "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock", "/validation_robot/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry", "/validation_robot/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"]}
backend-1     | {"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp"}
simulation-1  | [INFO] [1792755782.415368548] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/validation_robot/scan (ignition.msgs.LaserScan) -> /validation_robot/scan (sensor_msgs/msg/LaserScan)] (Lazy 0)
simulation-1  | [INFO] [1792755782.417832632] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/clock (ignition.msgs.Clock) -> /clock (rosgraph_msgs/msg/Clock)] (Lazy 0)
simulation-1  | [INFO] [1792755782.418718840] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/validation_robot/odom (ignition.msgs.Odometry) -> /validation_robot/odom (nav_msgs/msg/Odometry)] (Lazy 0)
simulation-1  | [INFO] [1792755782.419472132] [ros_gz_bridge]: Creating ROS->GZ Bridge: [/validation_robot/cmd_vel (geometry_msgs/msg/Twist) -> /validation_robot/cmd_vel (ignition.msgs.Twist)] (Lazy 0)
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
simulation-1  | [Err] [Ogre2RenderEngine.cc:993]  Unable to create the rendering window: OGRE EXCEPTION(6:FileNotFoundException): Data folder provided contains no valid template shader files. Did you provide the right folder location? Check you have the right read pemissions. Folder: /usr/share/ignition/ignition-rendering6/ogre2/src/media/Hlms/Unlit/GLSL in Hlms::Hlms at /build/ogre-next-phBY09/ogre-next-2.2.5+dfsg3/OgreMain/src/OgreHlms.cpp (line 441)
simulation-1  | [Err] [Ogre2RenderEngine.cc:1001] Unable to create the rendering window after [11] attempts.
simulation-1  | [Err] [Ogre2RenderEngine.cc:919] Failed to create dummy render window.
simulation-1  | [Err] [Ogre2RenderEngine.cc:920] Please see the troubleshooting page for possible fixes: https://gazebosim.org/docs/fortress/troubleshooting
simulation-1  | [Err] [Ogre2Material.cc:997] Ogre HLMS PBS not ready. Is Ogre2 Render Engine initiallized?
simulation-1  | Stack trace (most recent call last) in thread 40:
simulation-1  | #13   Object "[0xffffffffffffffff]", at 0xffffffffffffffff, in
simulation-1  | #12   Object "/lib/aarch64-linux-gnu/libc.so.6", at 0xffffb06a9fdb, in
simulation-1  | #11   Object "/lib/aarch64-linux-gnu/libc.so.6", at 0xffffb06403c7, in
simulation-1  | #10   Object "/lib/aarch64-linux-gnu/libstdc++.so.6", at 0xffffacb629cb, in
simulation-1  | #9    Object "/usr/lib/aarch64-linux-gnu/ign-gazebo-6/plugins/libignition-gazebo-sensors-system.so", at 0xffff938f6bbb, in ignition::gazebo::v6::systems::SensorsPrivate::RenderThread()
simulation-1  | #8    Object "/usr/lib/aarch64-linux-gnu/ign-gazebo-6/plugins/libignition-gazebo-sensors-system.so", at 0xffff938f5367, in ignition::gazebo::v6::systems::SensorsPrivate::WaitForInit()
simulation-1  | #7    Object "/lib/aarch64-linux-gnu/libignition-gazebo6-rendering.so.6", at 0xffff93804643, in ignition::gazebo::v6::RenderUtil::Init()
simulation-1  | #6    Object "/lib/aarch64-linux-gnu/libignition-rendering6.so.6", at 0xffff934b0337, in ignition::rendering::v6::BaseRenderEngine::CreateScene(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)
simulation-1  | #5    Object "/lib/aarch64-linux-gnu/libignition-rendering6.so.6", at 0xffff934b717f, in ignition::rendering::v6::BaseRenderEngine::CreateScene(unsigned int, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)
simulation-1  | #4    Object "/lib/aarch64-linux-gnu/libignition-rendering6.so.6", at 0xffff934c9a43, in ignition::rendering::v6::BaseScene::CreateMaterials()
simulation-1  | #3    Object "/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6", at 0xffff9123877f, in
simulation-1  | #2    Object "/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6", at 0xffff91229633, in ignition::rendering::v6::Ogre2Material::SetDiffuse(ignition::math::v6::Color const&)
simulation-1  | #1    Object "/lib/aarch64-linux-gnu/libOgreNextHlmsPbs.so.2.2.5", at 0xffff90b143b7, in Ogre::HlmsPbsDatablock::setDiffuse(Ogre::Vector3 const&)
simulation-1  | #0    Object "/lib/aarch64-linux-gnu/libOgreNextHlmsPbs.so.2.2.5", at 0xffff90b14390, in Ogre::HlmsPbsDatablock::getBrdf() const
simulation-1  | Segmentation fault (Address not mapped to object [0x2e0])
simulation-1  | [INFO] [1792755784.656744008] [rclcpp]: signal_handler(SIGINT/SIGTERM)
simulation-1  | [Msg] Serving world names on [{"event": "PROCESS_EXIT", "command": ["ign", "gazebo", "-s", "-r", "-v", "4", "--headless-rendering", "--physics-engine", "/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5", "--render-engine-server", "/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6", "/tmp/lidar-world.sdf"], "code": -11}
simulation-1  | {"event": "PROCESS_EXIT", "command": ["ros2", "run", "ros_gz_bridge", "parameter_bridge", "/validation_robot/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan", "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock", "/validation_robot/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry", "/validation_robot/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"], "code": 0}
simulation-1  | {"event": "FAIL", "error": "Child ['ign', 'gazebo', '-s', '-r', '-v', '4', '--headless-rendering', '--physics-engine', '/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5', '--render-engine-server', '/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6', '/tmp/lidar-world.sdf'] exited unexpectedly: -11", "error_type": "RuntimeError"}
simulation-1 exited with code 1
Aborting on container exit...
Container ros2-fleet-simulation-lidar-check-simulation-1 Stopping
Container ros2-fleet-simulation-lidar-check-backend-1 Stopping
Container ros2-fleet-simulation-lidar-check-simulation-1 Stopped
backend-1     | {"event": "SCAN_SUMMARY", "validated_messages": 0, "queued_messages": 0}
backend-1     | {"event": "FAIL", "error": "", "error_type": "ExternalShutdownException"}
Container ros2-fleet-simulation-lidar-check-backend-1 Stopped
backend-1 exited with code 1

```

## inspect-containers-02

```sh
docker inspect ros2-fleet-simulation-lidar-check-backend-1 ros2-fleet-simulation-lidar-check-simulation-1 --format '{{.Name}} image={{.Image}} status={{.State.Status}} exit={{.State.ExitCode}} networks={{json .NetworkSettings.Networks}} mounts={{json .Mounts}}'
```

Çıkış kodu: 0

```text
/ros2-fleet-simulation-lidar-check-backend-1 image=sha256:b61a40e60409a13f50c91d048d54be25121ac8c734d876a8e67db54886eeaacc status=exited exit=1 networks={"ros2-fleet-simulation-lidar-check_dds":{"IPAMConfig":null,"Links":null,"Aliases":["ros2-fleet-simulation-lidar-check-backend-1","backend"],"DriverOpts":null,"GwPriority":0,"NetworkID":"d6e8744cf09eb53c766c5c2df5f71fa8e8d97e7ce9c7c23433cba6553de5708a","EndpointID":"","Gateway":"","IPAddress":"","MacAddress":"","IPPrefixLen":0,"IPv6Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"DNSNames":["ros2-fleet-simulation-lidar-check-backend-1","backend","939e6c84b695"]}} mounts=[{"Type":"bind","Source":"/Users/murat/develop/ros2-fleet-manager/config","Destination":"/config","Mode":"ro","RW":false,"Propagation":"rprivate"}]
/ros2-fleet-simulation-lidar-check-simulation-1 image=sha256:b61a40e60409a13f50c91d048d54be25121ac8c734d876a8e67db54886eeaacc status=exited exit=1 networks={"ros2-fleet-simulation-lidar-check_dds":{"IPAMConfig":null,"Links":null,"Aliases":["ros2-fleet-simulation-lidar-check-simulation-1","simulation"],"DriverOpts":null,"GwPriority":0,"NetworkID":"d6e8744cf09eb53c766c5c2df5f71fa8e8d97e7ce9c7c23433cba6553de5708a","EndpointID":"","Gateway":"","IPAddress":"","MacAddress":"","IPPrefixLen":0,"IPv6Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"DNSNames":["ros2-fleet-simulation-lidar-check-simulation-1","simulation","9b11cc175bb5"]}} mounts=[{"Type":"bind","Source":"/Users/murat/develop/ros2-fleet-manager/config","Destination":"/config","Mode":"ro","RW":false,"Propagation":"rprivate"}]

```

## down-b1-02

```sh
env DDS_TEST_PAYLOAD=simulation-b1-20261023-02 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml down
```

Çıkış kodu: 0

```text
 ✔ Container ros2-fleet-simulation-lidar-check-backend-1    Removed         0.0s
 ✔ Container ros2-fleet-simulation-lidar-check-simulation-1 Removed         0.0s
 ✔ Network ros2-fleet-simulation-lidar-check_dds            Removed         0.1s

```

## cleanup-check-02

```sh
docker ps -a --filter label=com.docker.compose.project=ros2-fleet-simulation-lidar-check
docker network ls --filter name=ros2-fleet-simulation-lidar-check
```

Çıkış kodu: 0

```text
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
NETWORK ID   NAME      DRIVER    SCOPE

```

## iteration-03-package-owner-before

```sh
docker run --rm ros2-fleet-simulation-lidar-check:humble-fortress dpkg -S /usr/share/ignition/ignition-rendering6/ogre2/src/media/Hlms/Unlit/GLSL
```

Çıkış kodu: 1

```text
dpkg-query: no path found matching pattern /usr/share/ignition/ignition-rendering6/ogre2/src/media/Hlms/Unlit/GLSL

```

## iteration-03-media-candidate

```sh
docker exec b1-package-audit-03 bash -c 'set -e
apt-cache search libignition-rendering6
apt-cache show libignition-rendering6-dev
apt-cache show libignition-rendering6-common'
```

Çıkış kodu: 100

```text
libignition-rendering6 - Gazebo rendering classes and functions for robot apps - Shared library
libignition-rendering6-ogre2 - Gazebo rendering classes and functions for robot apps - Development files
E: No packages found

```

## iteration-03-package-search

```sh
docker run --name b1-package-audit-03 ros2-fleet-simulation-lidar-check:humble-fortress bash -c 'set -e
cat /etc/apt/sources.list
cat /etc/apt/sources.list.d/*
dpkg-query -W libignition-rendering6 libignition-rendering6-ogre2 libogrenextmain2.2.5
apt-get update
apt-cache search ignition-rendering
apt-cache search ogre-next
apt-cache policy libignition-rendering6 libignition-rendering6-ogre2
apt-cache show libignition-rendering6 libignition-rendering6-ogre2'
```

Çıkış kodu: 0

```text
# See http://help.ubuntu.com/community/UpgradeNotes for how to upgrade to
# newer versions of the distribution.
deb http://ports.ubuntu.com/ubuntu-ports/ jammy main restricted
# deb-src http://ports.ubuntu.com/ubuntu-ports/ jammy main restricted

## Major bug fix updates produced after the final release of the
## distribution.
deb http://ports.ubuntu.com/ubuntu-ports/ jammy-updates main restricted
# deb-src http://ports.ubuntu.com/ubuntu-ports/ jammy-updates main restricted

## N.B. software from this repository is ENTIRELY UNSUPPORTED by the Ubuntu
## team. Also, please note that software in universe WILL NOT receive any
## review or updates from the Ubuntu security team.
deb http://ports.ubuntu.com/ubuntu-ports/ jammy universe
# deb-src http://ports.ubuntu.com/ubuntu-ports/ jammy universe
deb http://ports.ubuntu.com/ubuntu-ports/ jammy-updates universe
# deb-src http://ports.ubuntu.com/ubuntu-ports/ jammy-updates universe

## N.B. software from this repository is ENTIRELY UNSUPPORTED by the Ubuntu
## team, and may not be under a free licence. Please satisfy yourself as to
## your rights to use the software. Also, please note that software in
## multiverse WILL NOT receive any review or updates from the Ubuntu
## security team.
deb http://ports.ubuntu.com/ubuntu-ports/ jammy multiverse
# deb-src http://ports.ubuntu.com/ubuntu-ports/ jammy multiverse
deb http://ports.ubuntu.com/ubuntu-ports/ jammy-updates multiverse
# deb-src http://ports.ubuntu.com/ubuntu-ports/ jammy-updates multiverse

## N.B. software from this repository may not have been tested as
## extensively as that contained in the main release, although it includes
## newer versions of some applications which may provide useful features.
## Also, please note that software in backports WILL NOT receive any review
## or updates from the Ubuntu security team.
deb http://ports.ubuntu.com/ubuntu-ports/ jammy-backports main restricted universe multiverse
# deb-src http://ports.ubuntu.com/ubuntu-ports/ jammy-backports main restricted universe multiverse

deb http://ports.ubuntu.com/ubuntu-ports/ jammy-security main restricted
# deb-src http://ports.ubuntu.com/ubuntu-ports/ jammy-security main restricted
deb http://ports.ubuntu.com/ubuntu-ports/ jammy-security universe
# deb-src http://ports.ubuntu.com/ubuntu-ports/ jammy-security universe
deb http://ports.ubuntu.com/ubuntu-ports/ jammy-security multiverse
# deb-src http://ports.ubuntu.com/ubuntu-ports/ jammy-security multiverse
Types: deb deb-src
URIs: http://packages.ros.org/ros2/ubuntu
Suites: jammy
Components: main
Signed-By:  -----BEGIN PGP PUBLIC KEY BLOCK-----
 .
 mQINBFzvJpYBEADY8l1YvO7iYW5gUESyzsTGnMvVUmlV3XarBaJz9bGRmgPXh7jc
 VFrQhE0L/HV7LOfoLI9H2GWYyHBqN5ERBlcA8XxG3ZvX7t9nAZPQT2Xxe3GT3tro
 u5oCR+SyHN9xPnUwDuqUSvJ2eqMYb9B/Hph3OmtjG30jSNq9kOF5bBTk1hOTGPH4
 K/AY0jzT6OpHfXU6ytlFsI47ZKsnTUhipGsKucQ1CXlyirndZ3V3k70YaooZ55rG
 aIoAWlx2H0J7sAHmqS29N9jV9mo135d+d+TdLBXI0PXtiHzE9IPaX+ctdSUrPnp+
 TwR99lxglpIG6hLuvOMAaxiqFBB/Jf3XJ8OBakfS6nHrWH2WqQxRbiITl0irkQoz
 pwNEF2Bv0+Jvs1UFEdVGz5a8xexQHst/RmKrtHLct3iOCvBNqoAQRbvWvBhPjO/p
 V5cYeUljZ5wpHyFkaEViClaVWqa6PIsyLqmyjsruPCWlURLsQoQxABcL8bwxX7UT
 hM6CtH6tGlYZ85RIzRifIm2oudzV5l+8oRgFr9yVcwyOFT6JCioqkwldW52P1pk/
 /SnuexC6LYqqDuHUs5NnokzzpfS6QaWfTY5P5tz4KHJfsjDIktly3mKVfY0fSPVV
 okdGpcUzvz2hq1fqjxB6MlB/1vtk0bImfcsoxBmF7H+4E9ZN1sX/tSb0KQARAQAB
 tCZPcGVuIFJvYm90aWNzIDxpbmZvQG9zcmZvdW5kYXRpb24ub3JnPokCVAQTAQgA
 PgIbAwULCQgHAgYVCgkICwIEFgIDAQIeAQIXgBYhBMHPbjHmut6IaLFytPQu1vur
 F8ZUBQJoEhoGBQkUtHZwAAoJEPQu1vurF8ZUv1AP/2gID+uw7pw3WpPevny3pliZ
 JeDx4Y+ut+5c2nCfkpUc3lG50v9ly4ZpNQTWKIm9yB6dxgary7EKpAlGVmiU75JA
 LyftVtjeyQcre2f7Z00u2lXw8Red52AsWHkh/dtctgLSGQiJdTd0donO6cszZFVa
 sCiFdRKlizGvBkE8uFdKYMGixOgnvQZrb9OLqRsoj10aDzN0X3NJk1LTxiS3+udY
 poOk2Bm9VGyrNmgIrYiNqbYPBHYkWGHBqJxvAK92lJ2I/n6X4U8r6sMdDE7QDw4j
 FMdrxC0XmCL4cFPkkR1qadtJy9FiCtpKyqiKuUsCG6AUi5EOY+7Y3oSpKn8Wp1K5
 VMbv12JRIatDIeaAnwa2qyBQVAVC1F/OqWUFKluPjKyMR3DXKwjxpt1P+HUmda0w
 HcnhFIu2th/egmGKH5e3atcVxjAxYfm+f92MN7fFEuFQsMZhI/gt3IgESWrgdaAz
 opRInrMz7yEtz3VaaehwmUUR2gevPQMzBRaA+NIqMLDUvV5jujvFe8c1VUtBLTYc
 /alBiM/Mo1niy3aUfDahzhTr6zz+ur6BFRnNFWv56M3NOVlreNm3NIbNX2kTKh0Z
 QJSSCklJuDUqnPmAzT2BZWUpwfe7QYRwvQhF0YB2N1LavyNwiyfinCQlAh+Q9eme
 2jqGsxvQym3sAPnWvA68
 =xH9H
 -----END PGP PUBLIC KEY BLOCK-----
libignition-rendering6:arm64	6.6.4-1~jammy
libignition-rendering6-ogre2:arm64	6.6.4-1~jammy
libogrenextmain2.2.5:arm64	2.2.5+dfsg3-0ubuntu2
Get:1 http://ports.ubuntu.com/ubuntu-ports jammy InRelease [270 kB]
Get:2 http://ports.ubuntu.com/ubuntu-ports jammy-updates InRelease [128 kB]
Get:3 http://packages.ros.org/ros2/ubuntu jammy InRelease [4682 B]
Get:4 http://ports.ubuntu.com/ubuntu-ports jammy-backports InRelease [127 kB]
Get:5 http://packages.ros.org/ros2/ubuntu jammy/main Sources [1900 kB]
Get:6 http://ports.ubuntu.com/ubuntu-ports jammy-security InRelease [129 kB]
Get:7 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 Packages [1758 kB]
Get:8 http://ports.ubuntu.com/ubuntu-ports jammy/multiverse arm64 Packages [224 kB]
Get:9 http://packages.ros.org/ros2/ubuntu jammy/main arm64 Packages [1823 kB]
Get:10 http://ports.ubuntu.com/ubuntu-ports jammy/restricted arm64 Packages [24.2 kB]
Get:11 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 Packages [17.2 MB]
Get:12 http://ports.ubuntu.com/ubuntu-ports jammy-updates/restricted arm64 Packages [8359 kB]
Get:13 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 Packages [4567 kB]
Get:14 http://ports.ubuntu.com/ubuntu-ports jammy-updates/universe arm64 Packages [1717 kB]
Get:15 http://ports.ubuntu.com/ubuntu-ports jammy-updates/multiverse arm64 Packages [81.6 kB]
Get:16 http://ports.ubuntu.com/ubuntu-ports jammy-backports/universe arm64 Packages [33.7 kB]
Get:17 http://ports.ubuntu.com/ubuntu-ports jammy-backports/main arm64 Packages [82.5 kB]
Get:18 http://ports.ubuntu.com/ubuntu-ports jammy-security/main arm64 Packages [4253 kB]
Get:19 http://ports.ubuntu.com/ubuntu-ports jammy-security/restricted arm64 Packages [8061 kB]
Get:20 http://ports.ubuntu.com/ubuntu-ports jammy-security/multiverse arm64 Packages [75.6 kB]
Get:21 http://ports.ubuntu.com/ubuntu-ports jammy-security/universe arm64 Packages [1421 kB]
Fetched 52.2 MB in 1min 47s (490 kB/s)
Reading package lists...
libignition-rendering-core-dev - Ignition rendering classes and functions - Core development files
libignition-rendering-dev - Ignition rendering classes and functions for robot apps - Metapackage
libignition-rendering-ogre1-dev - Ignition rendering classes and functions for robot apps - Development files
libignition-rendering-ogre2-dev - Ignition rendering classes and functions for robot apps - Development files
libignition-rendering6-6 - Ignition rendering classes and functions for robot apps - Shared library
libignition-rendering6-ogre1-6 - Ignition rendering classes and functions for robot apps - Development files
libignition-rendering6-ogre2-6 - Ignition rendering classes and functions for robot apps - Development files
libignition-rendering6 - Gazebo rendering classes and functions for robot apps - Shared library
libignition-rendering6-core-dev - Gazebo rendering classes and functions - Core development files
libignition-rendering6-dev - Gazebo rendering classes and functions for robot apps - Metapackage
libignition-rendering6-ogre1 - Gazebo rendering classes and functions for robot apps - Development files
libignition-rendering6-ogre1-dev - Gazebo rendering classes and functions for robot apps - Development files
libignition-rendering6-ogre2 - Gazebo rendering classes and functions for robot apps - Development files
libignition-rendering6-ogre2-dev - Gazebo rendering classes and functions for robot apps - Development files
blender-ogrexml-next - Blender Exporter for OGRE-Next
libogre-next-dev - 3D Object-Oriented Graphics Rendering Engine (development files)
ogre-next-doc - 3D Object-Oriented Graphics Rendering Engine (documentation)
ogre-next-tools - 3D Object-Oriented Graphics Rendering Engine (tools)
libignition-rendering6:
  Installed: 6.6.4-1~jammy
  Candidate: 6.6.4-1~jammy
  Version table:
 *** 6.6.4-1~jammy 500
        500 http://packages.ros.org/ros2/ubuntu jammy/main arm64 Packages
        100 /var/lib/dpkg/status
libignition-rendering6-ogre2:
  Installed: 6.6.4-1~jammy
  Candidate: 6.6.4-1~jammy
  Version table:
 *** 6.6.4-1~jammy 500
        500 http://packages.ros.org/ros2/ubuntu jammy/main arm64 Packages
        100 /var/lib/dpkg/status
Package: libignition-rendering6
Priority: optional
Section: libs
Installed-Size: 502
Maintainer: Jose Luis Rivero <jrivero@osrfoundation.org>
Architecture: arm64
Source: ignition-rendering6
Version: 6.6.4-1~jammy
Replaces: libignition-rendering6-6 (>= 6.1.0+ds-1)
Depends: libc6 (>= 2.32), libgcc-s1 (>= 3.3.1), libignition-common4 (>= 4.7.0), libignition-common4-graphics (>= 4.7.0), libignition-math6 (>= 6.15.1), libignition-plugin (>= 1.4.0), libstdc++6 (>= 11)
Breaks: libignition-rendering6-6 (>= 6.1.0+ds-1)
Filename: pool/main/i/ignition-rendering6/libignition-rendering6_6.6.4-1~jammy_arm64.deb
SHA512: cc0dcbbb52eaa7b58c42ab1ea17586806c7f0b4c0e08a918e8b97bd408242f704027e9cdbd835bdb4f348aaa52ea89786c068f37caacbdcf25b0880b585b4614
Size: 116024
SHA256: 61f84a75b6bf70a61458598a13ab27ed610a012def30e6d7a404a37ec0f3b53f
SHA1: 583072d63df0d936a5efb541c757bb7a30b6e438
MD5sum: 346999079c5d63a217b94e87f2c2b5bd
Description: Gazebo rendering classes and functions for robot apps - Shared library
 Gazebo Rendering is a C++ library designed to provide an abstraction for
 different rendering engines. It offers unified APIs for creating 3D graphics
 applications.  Gazebo rendering is a component in the Gazebo framework, a
 set of libraries designed to rapidly develop robot applications.
 .
 Main shared library
Description-md5: 528499d470a4d47e7164662e56c5e135
Homepage: http://gazebosim.org/
Multi-Arch: same

Package: libignition-rendering6-ogre2
Priority: optional
Section: libdevel
Installed-Size: 5632
Maintainer: Jose Luis Rivero <jrivero@osrfoundation.org>
Architecture: arm64
Source: ignition-rendering6
Version: 6.6.4-1~jammy
Replaces: libignition-rendering6-ogre2-6 (>= 6.1.0+ds-1)
Depends: libc6 (>= 2.32), libgcc-s1 (>= 3.3.1), libglx0, libignition-common4 (>= 4.7.0), libignition-common4-events (>= 4.7.0), libignition-common4-graphics (>= 4.7.0), libignition-math6 (>= 6.15.1), libignition-rendering6 (>= 6.6.4), libogrenexthlmspbs2.2.5 (>= 2.2.5+dfsg3), libogrenexthlmsunlit2.2.5 (>= 2.2.5+dfsg3), libogrenextmain2.2.5 (>= 2.2.5+dfsg3), libogrenextoverlay2.2.5 (>= 2.2.5+dfsg3), libogrenextplanarreflections2.2.5 (>= 2.2.5+dfsg3), libopengl0, libstdc++6 (>= 11)
Breaks: libignition-rendering6-ogre2-6 (>= 6.1.0+ds-1)
Filename: pool/main/i/ignition-rendering6/libignition-rendering6-ogre2_6.6.4-1~jammy_arm64.deb
SHA512: 354c574141cec2b665b781138aeb5add07a06ba712481c9e5497a6cca99753fb0f0251f9afb665b2d7d56be79aa14cd850b87e4130cf0ed538c239e60e38fc2c
Size: 481568
SHA256: 5183f7a70b96ac30c6ab8cf5cd54e293eefdceab8965d0e1836698690bc098a6
SHA1: b8e97b8d57138bdafd00d6f2272d16d1d64e8147
MD5sum: 3196215f0582ae60f84f4faab07c4652
Description: Gazebo rendering classes and functions for robot apps - Development files
 Gazebo Rendering is a C++ library designed to provide an abstraction for
 different rendering engines. It offers unified APIs for creating 3D graphics
 applications.  Gazebo rendering is a component in the Gazebo framework, a
 set of libraries designed to rapidly develop robot applications.
 Gazebo rendering is a component in the Gazebo framework, a set of libraries
 designed to rapidly develop robot applications.
 .
 Ogre2 component shared library
Description-md5: 69a8871629733ff33319dd4ddda174ac
Homepage: http://gazebosim.org/
Multi-Arch: same


```

## iteration-03-package-contents

```sh
docker run --rm ros2-fleet-simulation-lidar-check:humble-fortress bash -c 'set -e
apt-get update
apt-cache policy libignition-rendering6-ogre2-dev libignition-rendering-ogre2-dev libogre-next-dev
apt-cache show libignition-rendering6-ogre2-dev libignition-rendering-ogre2-dev libogre-next-dev
cd /tmp
apt-get download libignition-rendering6-ogre2-dev
dpkg-deb --contents libignition-rendering6-ogre2-dev_*.deb
apt-get --simulate install --no-install-recommends libignition-rendering6-ogre2-dev'
```

Çıkış kodu: 0

```text
Get:1 http://ports.ubuntu.com/ubuntu-ports jammy InRelease [270 kB]
Get:2 http://packages.ros.org/ros2/ubuntu jammy InRelease [4682 B]
Get:3 http://packages.ros.org/ros2/ubuntu jammy/main Sources [1900 kB]
Get:4 http://ports.ubuntu.com/ubuntu-ports jammy-updates InRelease [128 kB]
Get:5 http://packages.ros.org/ros2/ubuntu jammy/main arm64 Packages [1823 kB]
Get:6 http://ports.ubuntu.com/ubuntu-ports jammy-backports InRelease [127 kB]
Get:7 http://ports.ubuntu.com/ubuntu-ports jammy-security InRelease [129 kB]
Get:8 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 Packages [17.2 MB]
Get:9 http://ports.ubuntu.com/ubuntu-ports jammy/restricted arm64 Packages [24.2 kB]
Get:10 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 Packages [1758 kB]
Get:11 http://ports.ubuntu.com/ubuntu-ports jammy/multiverse arm64 Packages [224 kB]
Get:12 http://ports.ubuntu.com/ubuntu-ports jammy-updates/universe arm64 Packages [1717 kB]
Get:13 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 Packages [4567 kB]
Get:14 http://ports.ubuntu.com/ubuntu-ports jammy-updates/multiverse arm64 Packages [81.6 kB]
Get:15 http://ports.ubuntu.com/ubuntu-ports jammy-updates/restricted arm64 Packages [8359 kB]
Get:16 http://ports.ubuntu.com/ubuntu-ports jammy-backports/universe arm64 Packages [33.7 kB]
Get:17 http://ports.ubuntu.com/ubuntu-ports jammy-backports/main arm64 Packages [82.5 kB]
Get:18 http://ports.ubuntu.com/ubuntu-ports jammy-security/universe arm64 Packages [1421 kB]
Get:19 http://ports.ubuntu.com/ubuntu-ports jammy-security/main arm64 Packages [4253 kB]
Get:20 http://ports.ubuntu.com/ubuntu-ports jammy-security/multiverse arm64 Packages [75.6 kB]
Get:21 http://ports.ubuntu.com/ubuntu-ports jammy-security/restricted arm64 Packages [8061 kB]
Fetched 52.2 MB in 1min 41s (517 kB/s)
Reading package lists...
libignition-rendering6-ogre2-dev:
  Installed: (none)
  Candidate: 6.6.4-1~jammy
  Version table:
     6.6.4-1~jammy 500
        500 http://packages.ros.org/ros2/ubuntu jammy/main arm64 Packages
libignition-rendering-ogre2-dev:
  Installed: (none)
  Candidate: 6.1.0+ds-0ubuntu2
  Version table:
     6.1.0+ds-0ubuntu2 500
        500 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 Packages
libogre-next-dev:
  Installed: (none)
  Candidate: 2.2.5+dfsg3-0ubuntu2
  Version table:
     2.2.5+dfsg3-0ubuntu2 500
        500 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 Packages
Package: libignition-rendering6-ogre2-dev
Priority: optional
Section: libdevel
Installed-Size: 4143
Maintainer: Jose Luis Rivero <jrivero@osrfoundation.org>
Architecture: arm64
Source: ignition-rendering6
Version: 6.6.4-1~jammy
Depends: libignition-cmake2-dev (>= 2.12.1), libignition-common4-events-dev, libignition-common4-graphics-dev, libignition-math6-dev (>= 6.6.0), libignition-math6-eigen3-dev (>= 6.6.0), libogre-2.2-dev | libogre-next-dev, libignition-rendering6-core-dev (= 6.6.4-1~jammy), libignition-rendering6-ogre2 (= 6.6.4-1~jammy)
Filename: pool/main/i/ignition-rendering6/libignition-rendering6-ogre2-dev_6.6.4-1~jammy_arm64.deb
SHA512: 7aa4d1c5857ec15d8adf19960fb6d388182b79fa171c29b651e8060a41e42676680a9cb05eea1b6ed77485505c23ce75e292307cb3a0ca5eaed8c223c262854a
Size: 1107740
SHA256: 717dc0c44bc1fcc39295b4c7dcedeb830bc4e3f284cde5557c72964a523bebbf
SHA1: 924e1a79f2b829c3957cd6838de5435a3ea32abc
MD5sum: ed61fe6f0342d57acebc1cf844e533ce
Description: Gazebo rendering classes and functions for robot apps - Development files
 Gazebo Rendering is a C++ library designed to provide an abstraction for
 different rendering engines. It offers unified APIs for creating 3D graphics
 applications.  Gazebo rendering is a component in the Gazebo framework, a
 set of libraries designed to rapidly develop robot applications.
 Gazebo rendering is a component in the Gazebo framework, a set of libraries
 designed to rapidly develop robot applications.
 .
 Ogre2 component development files
Description-md5: f8eb102e422c9012bef529f9a3405b4c
Homepage: http://gazebosim.org/
Multi-Arch: same

Package: libignition-rendering-ogre2-dev
Architecture: arm64
Version: 6.1.0+ds-0ubuntu2
Multi-Arch: same
Priority: optional
Section: universe/libdevel
Source: ignition-rendering
Origin: Ubuntu
Maintainer: Ubuntu developers <ubuntu-devel-discuss@lists.ubuntu.com>
Original-Maintainer: Jose Luis Rivero <jrivero@osrfoundation.org>
Bugs: https://bugs.launchpad.net/ubuntu/+filebug
Installed-Size: 4112
Depends: libignition-cmake-dev (>= 2.3.0), libignition-common-dev (>= 4.0.0), libignition-common-graphics-dev, libignition-math-dev (>= 6.9.0), libogre-next-dev, libignition-rendering-core-dev (= 6.1.0+ds-0ubuntu2), libignition-rendering6-ogre2-6 (= 6.1.0+ds-0ubuntu2)
Filename: pool/universe/i/ignition-rendering/libignition-rendering-ogre2-dev_6.1.0+ds-0ubuntu2_arm64.deb
Size: 1263728
MD5sum: 34bc14d53ffa30a2898fe32f3eff453a
SHA1: c85d88bcdddde64b8a319d4dc9bdf728d69c8168
SHA256: f9de19ae2a6789e9b16944fb7981357652b8995a19e90d774deeebde9867a967
SHA512: 5324db5b1f4737e3912256b6486ea5b7b6504e04476e43c79c4d23ed217071d69c1ed5367a1dc76d307bb6d28a997fb0dee36d52449a9bbaf11934f6d4d3593a
Homepage: https://ignitionrobotics.org/libs/rendering
Description: Ignition rendering classes and functions for robot apps - Development files
Description-md5: e92ed854c5b566de1c0abfbe65f921ae

Package: libogre-next-dev
Architecture: arm64
Version: 2.2.5+dfsg3-0ubuntu2
Priority: optional
Section: universe/libdevel
Source: ogre-next
Origin: Ubuntu
Maintainer: Ubuntu developers <ubuntu-devel-discuss@lists.ubuntu.com>
Original-Maintainer: Jose Luis Rivero <jrivero@osrfoundation.org>
Bugs: https://bugs.launchpad.net/ubuntu/+filebug
Installed-Size: 8309
Depends: libboost-dev, libboost-thread-dev, libogrenexthlmspbs2.2.5 (= 2.2.5+dfsg3-0ubuntu2), libogrenexthlmsunlit2.2.5 (= 2.2.5+dfsg3-0ubuntu2), libogrenextmain2.2.5 (= 2.2.5+dfsg3-0ubuntu2), libogrenextmeshlodgenerator2.2.5 (= 2.2.5+dfsg3-0ubuntu2), libogrenextoverlay2.2.5 (= 2.2.5+dfsg3-0ubuntu2), libogrenextplanarreflections2.2.5 (= 2.2.5+dfsg3-0ubuntu2), libogrenextsceneformat2.2.5 (= 2.2.5+dfsg3-0ubuntu2)
Suggests: ogre-next-doc
Filename: pool/universe/o/ogre-next/libogre-next-dev_2.2.5+dfsg3-0ubuntu2_arm64.deb
Size: 1038282
MD5sum: 7666d07b4b6a235a4e2b12150334ac2b
SHA1: f5f66eb3354ebdfc5ab016b30341725f1ef50080
SHA256: 00ad507b4115c8ba8811f669ab0ecb32e5ec749664741d71a0ef13261681398b
SHA512: be6816f7f3953f674fe43f8ae8c0f6e085ac80da64c2eb3a2adb7567f8398e3b19580827e2e8610341455f15d6a3867d1292708ba8db2e6a8136f28245ca8641
Homepage: https://github.com/OGRECave/ogre-next
Description: 3D Object-Oriented Graphics Rendering Engine (development files)
Description-md5: 6b9b323f4e3cf6b84b16ee7bcc34531d

Get:1 http://packages.ros.org/ros2/ubuntu jammy/main arm64 libignition-rendering6-ogre2-dev arm64 6.6.4-1~jammy [1108 kB]
Fetched 1108 kB in 3s (422 kB/s)
drwxr-xr-x root/root         0 2026-01-29 21:17 ./
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/include/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/include/ignition/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/include/ignition/rendering6/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/
-rw-r--r-- root/root      2577 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Export.hh
-rw-r--r-- root/root      1366 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2ArrowVisual.hh
-rw-r--r-- root/root      1357 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2AxisVisual.hh
-rw-r--r-- root/root      6467 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2BoundingBoxCamera.hh
-rw-r--r-- root/root      2293 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2COMVisual.hh
-rw-r--r-- root/root      6198 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Camera.hh
-rw-r--r-- root/root      2313 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Capsule.hh
-rw-r--r-- root/root      4009 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Conversions.hh
-rw-r--r-- root/root      5667 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2DepthCamera.hh
-rw-r--r-- root/root      5311 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2DynamicRenderable.hh
-rw-r--r-- root/root      1852 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2GaussianNoisePass.hh
-rw-r--r-- root/root      2055 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Geometry.hh
-rw-r--r-- root/root      1307 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2GizmoVisual.hh
-rw-r--r-- root/root      5842 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2GpuRays.hh
-rw-r--r-- root/root      2213 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Grid.hh
-rw-r--r-- root/root      3622 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Heightmap.hh
-rw-r--r-- root/root      3779 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Includes.hh
-rw-r--r-- root/root      2648 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2InertiaVisual.hh
-rw-r--r-- root/root      1321 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2JointVisual.hh
-rw-r--r-- root/root      2645 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2LidarVisual.hh
-rw-r--r-- root/root      6500 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Light.hh
-rw-r--r-- root/root      2346 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2LightVisual.hh
-rw-r--r-- root/root      2795 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Marker.hh
-rw-r--r-- root/root     11599 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Material.hh
-rw-r--r-- root/root      3640 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2MaterialSwitcher.hh
-rw-r--r-- root/root      5052 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Mesh.hh
-rw-r--r-- root/root      5426 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2MeshFactory.hh
-rw-r--r-- root/root      4269 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Node.hh
-rw-r--r-- root/root      1578 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Object.hh
-rw-r--r-- root/root      3631 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2ParticleEmitter.hh
-rw-r--r-- root/root      2260 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2RayQuery.hh
-rw-r--r-- root/root      8641 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2RenderEngine.hh
-rw-r--r-- root/root      2930 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2RenderPass.hh
-rw-r--r-- root/root     10698 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2RenderTarget.hh
-rw-r--r-- root/root      4333 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2RenderTargetMaterial.hh
-rw-r--r-- root/root      5931 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2RenderTypes.hh
-rw-r--r-- root/root     17406 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Scene.hh
-rw-r--r-- root/root      3480 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2SegmentationCamera.hh
-rw-r--r-- root/root      3611 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2SelectionBuffer.hh
-rw-r--r-- root/root      1221 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Sensor.hh
-rw-r--r-- root/root      2747 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Storage.hh
-rw-r--r-- root/root      3339 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2ThermalCamera.hh
-rw-r--r-- root/root      3766 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2Visual.hh
-rw-r--r-- root/root      2340 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/Ogre2WireBox.hh
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/detail/
-rw-r--r-- root/root      1456 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2/detail/Export.hh
-rw-r--r-- root/root      2960 2026-01-29 21:17 ./usr/include/ignition/rendering6/gz/rendering/ogre2.hh
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/
-rw-r--r-- root/root       703 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Export.hh
-rw-r--r-- root/root       712 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2ArrowVisual.hh
-rw-r--r-- root/root       712 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2AxisVisual.hh
-rw-r--r-- root/root       718 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2BoundingBoxCamera.hh
-rw-r--r-- root/root       710 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2COMVisual.hh
-rw-r--r-- root/root       708 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Camera.hh
-rw-r--r-- root/root       708 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Capsule.hh
-rw-r--r-- root/root       713 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Conversions.hh
-rw-r--r-- root/root       713 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2DepthCamera.hh
-rw-r--r-- root/root       719 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2DynamicRenderable.hh
-rw-r--r-- root/root       719 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2GaussianNoisePass.hh
-rw-r--r-- root/root       710 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Geometry.hh
-rw-r--r-- root/root       713 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2GizmoVisual.hh
-rw-r--r-- root/root       709 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2GpuRays.hh
-rw-r--r-- root/root       706 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Grid.hh
-rw-r--r-- root/root       710 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Heightmap.hh
-rw-r--r-- root/root       710 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Includes.hh
-rw-r--r-- root/root       714 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2InertiaVisual.hh
-rw-r--r-- root/root       712 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2JointVisual.hh
-rw-r--r-- root/root       712 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2LidarVisual.hh
-rw-r--r-- root/root       707 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Light.hh
-rw-r--r-- root/root       712 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2LightVisual.hh
-rw-r--r-- root/root       708 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Marker.hh
-rw-r--r-- root/root       710 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Material.hh
-rw-r--r-- root/root       718 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2MaterialSwitcher.hh
-rw-r--r-- root/root       706 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Mesh.hh
-rw-r--r-- root/root       713 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2MeshFactory.hh
-rw-r--r-- root/root       706 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Node.hh
-rw-r--r-- root/root       708 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Object.hh
-rw-r--r-- root/root       716 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2ParticleEmitter.hh
-rw-r--r-- root/root       710 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2RayQuery.hh
-rw-r--r-- root/root       714 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2RenderEngine.hh
-rw-r--r-- root/root       712 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2RenderPass.hh
-rw-r--r-- root/root       714 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2RenderTarget.hh
-rw-r--r-- root/root       722 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2RenderTargetMaterial.hh
-rw-r--r-- root/root       713 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2RenderTypes.hh
-rw-r--r-- root/root       707 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Scene.hh
-rw-r--r-- root/root       719 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2SegmentationCamera.hh
-rw-r--r-- root/root       717 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2SelectionBuffer.hh
-rw-r--r-- root/root       708 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Sensor.hh
-rw-r--r-- root/root       709 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Storage.hh
-rw-r--r-- root/root       715 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2ThermalCamera.hh
-rw-r--r-- root/root       708 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2Visual.hh
-rw-r--r-- root/root       708 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2/Ogre2WireBox.hh
-rw-r--r-- root/root       696 2026-01-29 21:17 ./usr/include/ignition/rendering6/ignition/rendering/ogre2.hh
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/lib/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/cmake/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/cmake/ignition-rendering6-ogre2/
-rw-r--r-- root/root      2878 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/cmake/ignition-rendering6-ogre2/ignition-rendering6-ogre2-config-version.cmake
-rw-r--r-- root/root      6038 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/cmake/ignition-rendering6-ogre2/ignition-rendering6-ogre2-config.cmake
-rw-r--r-- root/root      1126 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/cmake/ignition-rendering6-ogre2/ignition-rendering6-ogre2-targets-relwithdebinfo.cmake
-rw-r--r-- root/root      4908 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/cmake/ignition-rendering6-ogre2/ignition-rendering6-ogre2-targets.cmake
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/ign-rendering-6/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/pkgconfig/
-rw-r--r-- root/root       404 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/pkgconfig/ignition-rendering6-ogre2.pc
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/doc/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/doc/libignition-rendering6-ogre2-dev/
-rw-r--r-- root/root       561 2026-01-29 21:17 ./usr/share/doc/libignition-rendering6-ogre2-dev/changelog.Debian.gz
-rw-r--r-- root/root       322 2026-01-29 21:17 ./usr/share/doc/libignition-rendering6-ogre2-dev/copyright
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/
-rw-r--r-- root/root      3554 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Copyback.material
-rw-r--r-- root/root      2089 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/DPSM.material
-rw-r--r-- root/root      1136 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/DepthUtils.material
-rw-r--r-- root/root      2457 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/EsmGaussianBlurLogFilter.material
-rw-r--r-- root/root      1996 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/EsmGaussianBlurLogFilter.material.json
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/
-rw-r--r-- root/root       150 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/Copyback_1xFP32_ps.glsl
-rw-r--r-- root/root       151 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/Copyback_3xFP32_ps.glsl
-rw-r--r-- root/root       147 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/Copyback_4xFP32_ps.glsl
-rw-r--r-- root/root       620 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/CubeToDpsm_ps.glsl
-rw-r--r-- root/root       652 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/DepthDownscaleMax_ps.glsl
-rw-r--r-- root/root       990 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/EsmGaussianBlurLogFilter_cs.glsl
-rw-r--r-- root/root      9454 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/GaussianBlurBase_cs.glsl
-rw-r--r-- root/root     11070 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/GaussianBlurLogFilterBase_cs.glsl
-rw-r--r-- root/root      1078 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/GaussianBlurLogFilter_ps.glsl
-rw-r--r-- root/root      1466 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/MipmapsGaussianBlur_cs.glsl
-rw-r--r-- root/root       302 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/QuadCameraDir_vs.glsl
-rw-r--r-- root/root       232 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/Quad_vs.glsl
-rw-r--r-- root/root       214 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/GLSL/Resolve_1xFP32_Subsample0_ps.glsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/
-rw-r--r-- root/root       295 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/Copyback_1xFP32_ps.metal
-rw-r--r-- root/root       298 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/Copyback_3xFP32_ps.metal
-rw-r--r-- root/root       299 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/Copyback_4xFP32_ps.metal
-rw-r--r-- root/root       736 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/CubeToDpsm_ps.metal
-rw-r--r-- root/root       806 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/DepthDownscaleMax_ps.metal
-rw-r--r-- root/root      1000 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/EsmGaussianBlurLogFilter_cs.metal
-rw-r--r-- root/root     10085 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/GaussianBlurBase_cs.metal
-rw-r--r-- root/root     11570 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/GaussianBlurLogFilterBase_cs.metal
-rw-r--r-- root/root      1311 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/GaussianBlurLogFilter_ps.metal
-rw-r--r-- root/root      1575 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/MipmapsGaussianBlur_cs.metal
-rw-r--r-- root/root       583 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/QuadCameraDir_vs.metal
-rw-r--r-- root/root       486 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/Quad_vs.metal
-rw-r--r-- root/root       320 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Metal/Resolve_1xFP32_Subsample0_ps.metal
-rw-r--r-- root/root      2122 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Mipmaps.material.json
-rw-r--r-- root/root      1554 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Common/Quad.program
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/GLSL/
-rw-r--r-- root/root      2885 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/GLSL/GpuNormalMapper_ps.glsl
-rw-r--r-- root/root       983 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/GLSL/TerraGaussianBlur_cs.glsl
-rw-r--r-- root/root      3982 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/GLSL/TerraShadowGenerator.glsl
-rw-r--r-- root/root       263 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/GpuNormalMapper.compositor
-rw-r--r-- root/root      1040 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/GpuNormalMapper.material
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/Metal/
-rw-r--r-- root/root      3047 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/Metal/GpuNormalMapper_ps.metal
-rw-r--r-- root/root      1011 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/Metal/TerraGaussianBlur_cs.metal
-rw-r--r-- root/root      3445 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/Metal/TerraShadowGenerator.metal
-rw-r--r-- root/root       609 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/TerraShadowGenerator.compositor
-rw-r--r-- root/root      2088 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/2.0/scripts/materials/Terra/TerraShadowGenerator.material.json
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Any/
-rw-r--r-- root/root      4155 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Any/Cubemap_piece_all.any
-rw-r--r-- root/root       571 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Any/DualParaboloid_piece_ps.any
-rw-r--r-- root/root       260 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Any/ReverseDepthHelpers_piece_ps.any
-rw-r--r-- root/root      1232 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Any/ShadowCaster_piece_ps.any
-rw-r--r-- root/root      2180 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Any/ShadowCaster_piece_vs.any
-rw-r--r-- root/root       137 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Any/UnpackHelpers_piece_all.any
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSL/
-rw-r--r-- root/root      5245 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSL/CrossPlatformSettings_piece_all.glsl
-rw-r--r-- root/root      3246 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSL/Matrix_piece_all.glsl
-rw-r--r-- root/root      1227 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSL/QuaternionCode_piece_all.glsl
-rw-r--r-- root/root       120 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSL/RenderDepthOnly_piece_ps.glsl
-rw-r--r-- root/root      1044 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSL/UavCrossPlatform_piece_all.glsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSLES/
-rw-r--r-- root/root      2809 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSLES/CrossPlatformSettings_piece_all.glsl
-rw-r--r-- root/root      2223 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSLES/Matrix_piece_all.glsl
-rw-r--r-- root/root      1227 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSLES/QuaternionCode_piece_all.glsl
-rw-r--r-- root/root       125 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/GLSLES/RenderDepthOnly_piece_ps.glsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/HLSL/
-rw-r--r-- root/root      3950 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/HLSL/CrossPlatformSettings_piece_all.hlsl
-rw-r--r-- root/root      1201 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/HLSL/Matrix_piece_all.hlsl
-rw-r--r-- root/root      1245 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/HLSL/QuaternionCode_piece_all.hlsl
-rw-r--r-- root/root       915 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/HLSL/RenderDepthOnly_piece_ps.hlsl
-rw-r--r-- root/root       899 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/HLSL/UavCrossPlatform_piece_all.hlsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Metal/
-rw-r--r-- root/root      4272 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Metal/CrossPlatformSettings_piece_all.metal
-rw-r--r-- root/root      1048 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Metal/Matrix_piece_all.metal
-rw-r--r-- root/root      1275 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Metal/QuaternionCode_piece_all.metal
-rw-r--r-- root/root       752 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Metal/RenderDepthOnly_piece_ps.metal
-rw-r--r-- root/root      1034 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Common/Metal/UavCrossPlatform_piece_all.metal
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Ignition/
-rw-r--r-- root/root       331 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Ignition/IgnCustomStructs_piece_all.any
-rw-r--r-- root/root       509 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Ignition/Ign_piece_vs.any
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/
-rw-r--r-- root/root      1304 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/200.TextureRegisters_piece_vs.any
-rw-r--r-- root/root      3072 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/AmbientLighting_piece_ps.any
-rw-r--r-- root/root      9621 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/AreaLights_LTC_piece_ps.any
-rw-r--r-- root/root      8966 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/AreaLights_piece_ps.any
-rw-r--r-- root/root     11181 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/ForwardPlus_DecalsCubemaps_piece_ps.any
-rw-r--r-- root/root       586 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/IrradianceField_piece_all.any
-rw-r--r-- root/root      6762 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/IrradianceField_piece_ps.any
-rw-r--r-- root/root      3659 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/IrradianceVolume_piece_ps.any
-rw-r--r-- root/root      1721 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/LightProfiles_piece_ps.any
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Main/
-rw-r--r-- root/root     12502 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Main/200.BRDFs_piece_ps.any
-rw-r--r-- root/root      3290 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Main/200.BlendModes_piece_ps.any
-rw-r--r-- root/root       794 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Main/200.DetailMaps_piece_ps.any
-rw-r--r-- root/root     10151 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Main/200.ForwardPlus_piece_ps.any
-rw-r--r-- root/root      1136 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Main/200.Textures_piece_ps.any
-rw-r--r-- root/root     12310 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Main/500.Structs_piece_vs_piece_ps.any
-rw-r--r-- root/root     31602 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Main/800.PixelShader_piece_ps.any
-rw-r--r-- root/root     11408 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Main/800.VertexShader_piece_vs.any
-rw-r--r-- root/root       279 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/PlanarReflections_piece_all.any
-rw-r--r-- root/root      2896 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/PlanarReflections_piece_ps.any
-rw-r--r-- root/root      2255 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Refractions_piece_ps.any
-rw-r--r-- root/root     17067 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/ShadowMapping_piece_ps.any
-rw-r--r-- root/root      1669 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/ShadowMapping_piece_vs.any
-rw-r--r-- root/root       484 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/UvModifierMacros_piece_ps.any
-rw-r--r-- root/root       960 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Vct_piece_all.any
-rw-r--r-- root/root     16108 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Any/Vct_piece_ps.any
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSL/
-rw-r--r-- root/root       531 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSL/Forward3D_piece_ps.glsl
-rw-r--r-- root/root      4036 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSL/PixelShader_ps.glsl
-rw-r--r-- root/root      1503 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSL/VertexShader_vs.glsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSLES/
-rw-r--r-- root/root     11564 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSLES/BRDFs_piece_ps.glsl
-rw-r--r-- root/root      2881 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSLES/BlendModes_piece_ps.glsl
-rw-r--r-- root/root       794 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSLES/DetailMaps_piece_ps.glsl
-rw-r--r-- root/root     10023 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSLES/Forward3D_piece_ps.glsl
-rw-r--r-- root/root      3037 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSLES/IrradianceVolume_piece_ps.glsl
-rw-r--r-- root/root     25023 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSLES/PixelShader_ps.glsl
-rw-r--r-- root/root      6802 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSLES/Structs_piece_vs_piece_ps.glsl
-rw-r--r-- root/root      5264 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSLES/Textures_piece_ps.glsl
-rw-r--r-- root/root     11299 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/GLSLES/VertexShader_vs.glsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/HLSL/
-rw-r--r-- root/root       696 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/HLSL/Forward3D_piece_ps.hlsl
-rw-r--r-- root/root      5815 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/HLSL/PixelShader_ps.hlsl
-rw-r--r-- root/root       304 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/HLSL/Textures_piece_ps.hlsl
-rw-r--r-- root/root      2009 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/HLSL/VertexShader_vs.hlsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Metal/
-rw-r--r-- root/root       711 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Metal/Forward3D_piece_ps.metal
-rw-r--r-- root/root      6247 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Metal/PixelShader_ps.metal
-rw-r--r-- root/root       308 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Metal/Textures_piece_ps.metal
-rw-r--r-- root/root      2302 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Pbs/Metal/VertexShader_vs.metal
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/Any/
-rw-r--r-- root/root      2450 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/Any/500.Structs_piece_vs_piece_ps.any
-rw-r--r-- root/root     17062 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/Any/800.PixelShader_piece_ps.any
-rw-r--r-- root/root      4850 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/Any/800.VertexShader_piece_vs.any
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSL/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSL/PbsTerraShadows/
-rw-r--r-- root/root      1643 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSL/PbsTerraShadows/PbsTerraShadows_piece_vs_piece_ps.glsl
-rw-r--r-- root/root      3393 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSL/PixelShader_ps.glsl
-rw-r--r-- root/root       929 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSL/VertexShader_vs.glsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSLES/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSLES/PbsTerraShadows/
-rw-r--r-- root/root      1497 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSLES/PbsTerraShadows/PbsTerraShadows_piece_vs_piece_ps.glsl
-rw-r--r-- root/root     13045 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSLES/PixelShader_ps.glsl
-rw-r--r-- root/root      1055 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSLES/Structs_piece_vs_piece_ps.glsl
-rw-r--r-- root/root       435 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSLES/Textures_piece_ps.glsl
-rw-r--r-- root/root      3976 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/GLSLES/VertexShader_vs.glsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/HLSL/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/HLSL/PbsTerraShadows/
-rw-r--r-- root/root      1781 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/HLSL/PbsTerraShadows/PbsTerraShadows_piece_vs_piece_ps.hlsl
-rw-r--r-- root/root      4807 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/HLSL/PixelShader_ps.hlsl
-rw-r--r-- root/root      1153 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/HLSL/VertexShader_vs.hlsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/Metal/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/Metal/PbsTerraShadows/
-rw-r--r-- root/root      1739 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/Metal/PbsTerraShadows/PbsTerraShadows_piece_vs_piece_ps.metal
-rw-r--r-- root/root      5882 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/Metal/PixelShader_ps.metal
-rw-r--r-- root/root      1198 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/Metal/VertexShader_vs.metal
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/ign/
-rw-r--r-- root/root        89 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/ign/100.ign_CustomVs_piece_vs.any
-rw-r--r-- root/root      1979 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/ign/100.ign_CustomWeights_piece_ps.any
-rw-r--r-- root/root       238 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Terra/ign/500.ign_Structs_piece_all.any
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/Any/
-rw-r--r-- root/root       549 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/Any/StructsUnlit_piece_all.any
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSL/
-rw-r--r-- root/root      4234 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSL/BlendModes_piece_ps.glsl
-rw-r--r-- root/root      3073 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSL/PixelShader_ps.glsl
-rw-r--r-- root/root      1488 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSL/Structs_piece_vs_piece_ps.glsl
-rw-r--r-- root/root      3294 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSL/VertexShader_vs.glsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSLES/
-rw-r--r-- root/root      4682 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSLES/BlendModes_piece_ps.glsl
-rw-r--r-- root/root      3107 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSLES/PixelShader_ps.glsl
-rw-r--r-- root/root      1497 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSLES/Structs_piece_vs_piece_ps.glsl
-rw-r--r-- root/root      3673 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSLES/VertexShader_vs.glsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/HLSL/
-rw-r--r-- root/root      4486 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/HLSL/BlendModes_piece_ps.hlsl
-rw-r--r-- root/root      3275 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/HLSL/PixelShader_ps.hlsl
-rw-r--r-- root/root      1895 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/HLSL/Structs_piece_vs_piece_ps.hlsl
-rw-r--r-- root/root      3423 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/HLSL/VertexShader_vs.hlsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/Metal/
-rw-r--r-- root/root      3998 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/Metal/BlendModes_piece_ps.metal
-rw-r--r-- root/root      3661 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/Metal/PixelShader_ps.metal
-rw-r--r-- root/root      1611 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/Metal/Structs_piece_vs_piece_ps.metal
-rw-r--r-- root/root      3656 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/Metal/VertexShader_vs.metal
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/
-rw-r--r-- root/root      1720 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/depth_camera_final_fs.glsl
-rw-r--r-- root/root       887 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/depth_camera_final_vs.glsl
-rw-r--r-- root/root      5646 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/depth_camera_fs.glsl
-rw-r--r-- root/root      1190 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/depth_camera_vs.glsl
-rw-r--r-- root/root      3773 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/gaussian_noise_depth_fs.glsl
-rw-r--r-- root/root      5029 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/gaussian_noise_fs.glsl
-rw-r--r-- root/root       962 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/gaussian_noise_vs.glsl
-rw-r--r-- root/root      3725 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/gpu_rays_1st_pass_fs.glsl
-rw-r--r-- root/root      1190 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/gpu_rays_1st_pass_vs.glsl
-rw-r--r-- root/root      2029 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/gpu_rays_2nd_pass_fs.glsl
-rw-r--r-- root/root      1615 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/heat_signature_fs.glsl
-rw-r--r-- root/root       721 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/plain_color_fs.glsl
-rw-r--r-- root/root      1275 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/plain_color_vs.glsl
-rw-r--r-- root/root       864 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/point_fs.glsl
-rw-r--r-- root/root       877 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/point_vs.glsl
-rw-r--r-- root/root      1714 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/selection_buffer_fs.glsl
-rw-r--r-- root/root      1657 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/skybox_fs.glsl
-rw-r--r-- root/root      1699 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/skybox_vs.glsl
-rw-r--r-- root/root      3411 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/GLSL/thermal_camera_fs.glsl
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/
-rw-r--r-- root/root      2124 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/depth_camera_final_fs.metal
-rw-r--r-- root/root      1202 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/depth_camera_final_vs.metal
-rw-r--r-- root/root      6451 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/depth_camera_fs.metal
-rw-r--r-- root/root      1505 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/depth_camera_vs.metal
-rw-r--r-- root/root      3585 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/gaussian_noise_depth_fs.metal
-rw-r--r-- root/root      3415 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/gaussian_noise_fs.metal
-rw-r--r-- root/root      1267 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/gaussian_noise_vs.metal
-rw-r--r-- root/root      4403 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/gpu_rays_1st_pass_fs.metal
-rw-r--r-- root/root      1505 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/gpu_rays_1st_pass_vs.metal
-rw-r--r-- root/root      2567 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/gpu_rays_2nd_pass_fs.metal
-rw-r--r-- root/root      2021 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/heat_signature_fs.metal
-rw-r--r-- root/root       902 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/plain_color_fs.metal
-rw-r--r-- root/root      1578 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/plain_color_vs.metal
-rw-r--r-- root/root       898 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/point_fs.metal
-rw-r--r-- root/root      1148 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/point_vs.metal
-rw-r--r-- root/root      2207 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/selection_buffer_fs.metal
-rw-r--r-- root/root       601 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/skybox_fs.metal
-rw-r--r-- root/root       874 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/skybox_vs.metal
-rw-r--r-- root/root      4023 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/programs/Metal/thermal_camera_fs.metal
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/scripts/
-rw-r--r-- root/root      3521 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/scripts/depth_camera.material
-rw-r--r-- root/root      2882 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/scripts/gaussian_noise.material
-rw-r--r-- root/root      4877 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/scripts/gpu_rays.material
-rw-r--r-- root/root      1519 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/scripts/picker.material
-rw-r--r-- root/root      1707 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/scripts/point_cloud_point.material
-rw-r--r-- root/root      2414 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/scripts/selection_buffer.material
-rw-r--r-- root/root      2591 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/scripts/skybox.material
-rw-r--r-- root/root      4739 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/scripts/thermal.material
drwxr-xr-x root/root         0 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/textures/
-rw-r--r-- root/root   3145856 2026-01-29 21:17 ./usr/share/ignition/ignition-rendering6/ogre2/media/materials/textures/skybox.dds
lrwxrwxrwx root/root         0 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering-ogre2.so -> libignition-rendering6-ogre2.so
lrwxrwxrwx root/root         0 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so -> libignition-rendering6-ogre2.so.6
lrwxrwxrwx root/root         0 2026-01-29 21:17 ./usr/lib/aarch64-linux-gnu/libignition-rendering6-ogre2.so -> libignition-rendering6-ogre2.so.6
Reading package lists...
Building dependency tree...
Reading state information...
The following additional packages will be installed:
  libblkid-dev libboost-atomic1.74-dev libboost-atomic1.74.0
  libboost-chrono1.74-dev libboost-chrono1.74.0 libboost-date-time1.74-dev
  libboost-date-time1.74.0 libboost-dev libboost-serialization1.74-dev
  libboost-serialization1.74.0 libboost-system1.74-dev libboost-system1.74.0
  libboost-thread-dev libboost-thread1.74-dev libboost-thread1.74.0
  libboost1.74-dev libffi-dev libglib2.0-bin libglib2.0-data libglib2.0-dev
  libglib2.0-dev-bin libgts-dev libignition-common4-core-dev
  libignition-common4-events-dev libignition-common4-graphics-dev
  libignition-math6-eigen3-dev libignition-plugin-dev
  libignition-rendering6-core-dev libmount-dev libogre-next-dev
  libogrenextmeshlodgenerator2.2.5 libogrenextsceneformat2.2.5 libpcre16-3
  libpcre2-32-0 libpcre2-dev libpcre2-posix3 libpcre3-dev libpcre32-3
  libpcrecpp0v5 libselinux1-dev libsepol-dev
Suggested packages:
  libboost-doc libboost1.74-doc libboost-container1.74-dev
  libboost-context1.74-dev libboost-contract1.74-dev
  libboost-coroutine1.74-dev libboost-exception1.74-dev libboost-fiber1.74-dev
  libboost-filesystem1.74-dev libboost-graph1.74-dev
  libboost-graph-parallel1.74-dev libboost-iostreams1.74-dev
  libboost-locale1.74-dev libboost-log1.74-dev libboost-math1.74-dev
  libboost-mpi1.74-dev libboost-mpi-python1.74-dev libboost-numpy1.74-dev
  libboost-program-options1.74-dev libboost-python1.74-dev
  libboost-random1.74-dev libboost-regex1.74-dev libboost-stacktrace1.74-dev
  libboost-test1.74-dev libboost-timer1.74-dev libboost-type-erasure1.74-dev
  libboost-wave1.74-dev libboost1.74-tools-dev libmpfrc++-dev libntl-dev
  libboost-nowide1.74-dev libgirepository1.0-dev libglib2.0-doc
  libgdk-pixbuf2.0-bin | libgdk-pixbuf2.0-dev libgts-doc ogre-next-doc
The following NEW packages will be installed:
  libblkid-dev libboost-atomic1.74-dev libboost-atomic1.74.0
  libboost-chrono1.74-dev libboost-chrono1.74.0 libboost-date-time1.74-dev
  libboost-date-time1.74.0 libboost-dev libboost-serialization1.74-dev
  libboost-serialization1.74.0 libboost-system1.74-dev libboost-system1.74.0
  libboost-thread-dev libboost-thread1.74-dev libboost-thread1.74.0
  libboost1.74-dev libffi-dev libglib2.0-bin libglib2.0-data libglib2.0-dev
  libglib2.0-dev-bin libgts-dev libignition-common4-core-dev
  libignition-common4-events-dev libignition-common4-graphics-dev
  libignition-math6-eigen3-dev libignition-plugin-dev
  libignition-rendering6-core-dev libignition-rendering6-ogre2-dev
  libmount-dev libogre-next-dev libogrenextmeshlodgenerator2.2.5
  libogrenextsceneformat2.2.5 libpcre16-3 libpcre2-32-0 libpcre2-dev
  libpcre2-posix3 libpcre3-dev libpcre32-3 libpcrecpp0v5 libselinux1-dev
  libsepol-dev
0 upgraded, 42 newly installed, 0 to remove and 9 not upgraded.
Inst libglib2.0-data (2.72.4-0ubuntu2.10 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [all])
Inst libboost1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-atomic1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-atomic1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-chrono1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-chrono1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-date-time1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-serialization1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-serialization1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-date-time1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-dev (1.74.0.3ubuntu7 Ubuntu:22.04/jammy [arm64])
Inst libboost-system1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-system1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-thread1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-thread1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Inst libboost-thread-dev (1.74.0.3ubuntu7 Ubuntu:22.04/jammy [arm64])
Inst libglib2.0-bin (2.72.4-0ubuntu2.10 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libffi-dev (3.4.2-4 Ubuntu:22.04/jammy [arm64])
Inst libglib2.0-dev-bin (2.72.4-0ubuntu2.10 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libblkid-dev (2.37.2-4ubuntu3.6 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libsepol-dev (3.3-1build1 Ubuntu:22.04/jammy [arm64])
Inst libpcre2-32-0 (10.39-3ubuntu0.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libpcre2-posix3 (10.39-3ubuntu0.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libpcre2-dev (10.39-3ubuntu0.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libselinux1-dev (3.3-1build2 Ubuntu:22.04/jammy [arm64])
Inst libmount-dev (2.37.2-4ubuntu3.6 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libpcre16-3 (2:8.39-13ubuntu0.22.04.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libpcre32-3 (2:8.39-13ubuntu0.22.04.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libpcrecpp0v5 (2:8.39-13ubuntu0.22.04.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libpcre3-dev (2:8.39-13ubuntu0.22.04.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libglib2.0-dev (2.72.4-0ubuntu2.10 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Inst libgts-dev (0.7.6+darcs121130-5 Ubuntu:22.04/jammy [arm64])
Inst libignition-common4-core-dev (4.8.1-1~jammy ROS jammy:jammy [arm64])
Inst libignition-common4-events-dev (4.8.1-1~jammy ROS jammy:jammy [arm64])
Inst libignition-common4-graphics-dev (4.8.1-1~jammy ROS jammy:jammy [arm64])
Inst libignition-math6-eigen3-dev (6.16.0-1~jammy ROS jammy:jammy [arm64])
Inst libignition-plugin-dev (1.4.0-1~jammy ROS jammy:jammy [arm64])
Inst libignition-rendering6-core-dev (6.6.4-1~jammy ROS jammy:jammy [arm64])
Inst libogrenextmeshlodgenerator2.2.5 (2.2.5+dfsg3-0ubuntu2 Ubuntu:22.04/jammy [arm64])
Inst libogrenextsceneformat2.2.5 (2.2.5+dfsg3-0ubuntu2 Ubuntu:22.04/jammy [arm64])
Inst libogre-next-dev (2.2.5+dfsg3-0ubuntu2 Ubuntu:22.04/jammy [arm64])
Inst libignition-rendering6-ogre2-dev (6.6.4-1~jammy ROS jammy:jammy [arm64])
Conf libglib2.0-data (2.72.4-0ubuntu2.10 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [all])
Conf libboost1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-atomic1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-atomic1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-chrono1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-chrono1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-date-time1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-serialization1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-serialization1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-date-time1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-dev (1.74.0.3ubuntu7 Ubuntu:22.04/jammy [arm64])
Conf libboost-system1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-system1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-thread1.74.0 (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-thread1.74-dev (1.74.0-14ubuntu3 Ubuntu:22.04/jammy [arm64])
Conf libboost-thread-dev (1.74.0.3ubuntu7 Ubuntu:22.04/jammy [arm64])
Conf libglib2.0-bin (2.72.4-0ubuntu2.10 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libffi-dev (3.4.2-4 Ubuntu:22.04/jammy [arm64])
Conf libglib2.0-dev-bin (2.72.4-0ubuntu2.10 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libblkid-dev (2.37.2-4ubuntu3.6 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libsepol-dev (3.3-1build1 Ubuntu:22.04/jammy [arm64])
Conf libpcre2-32-0 (10.39-3ubuntu0.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libpcre2-posix3 (10.39-3ubuntu0.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libpcre2-dev (10.39-3ubuntu0.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libselinux1-dev (3.3-1build2 Ubuntu:22.04/jammy [arm64])
Conf libmount-dev (2.37.2-4ubuntu3.6 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libpcre16-3 (2:8.39-13ubuntu0.22.04.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libpcre32-3 (2:8.39-13ubuntu0.22.04.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libpcrecpp0v5 (2:8.39-13ubuntu0.22.04.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libpcre3-dev (2:8.39-13ubuntu0.22.04.1 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libglib2.0-dev (2.72.4-0ubuntu2.10 Ubuntu:22.04/jammy-updates, Ubuntu:22.04/jammy-security [arm64])
Conf libgts-dev (0.7.6+darcs121130-5 Ubuntu:22.04/jammy [arm64])
Conf libignition-common4-core-dev (4.8.1-1~jammy ROS jammy:jammy [arm64])
Conf libignition-common4-events-dev (4.8.1-1~jammy ROS jammy:jammy [arm64])
Conf libignition-common4-graphics-dev (4.8.1-1~jammy ROS jammy:jammy [arm64])
Conf libignition-math6-eigen3-dev (6.16.0-1~jammy ROS jammy:jammy [arm64])
Conf libignition-plugin-dev (1.4.0-1~jammy ROS jammy:jammy [arm64])
Conf libignition-rendering6-core-dev (6.6.4-1~jammy ROS jammy:jammy [arm64])
Conf libogrenextmeshlodgenerator2.2.5 (2.2.5+dfsg3-0ubuntu2 Ubuntu:22.04/jammy [arm64])
Conf libogrenextsceneformat2.2.5 (2.2.5+dfsg3-0ubuntu2 Ubuntu:22.04/jammy [arm64])
Conf libogre-next-dev (2.2.5+dfsg3-0ubuntu2 Ubuntu:22.04/jammy [arm64])
Conf libignition-rendering6-ogre2-dev (6.6.4-1~jammy ROS jammy:jammy [arm64])

```

## iteration-03-preflight

```sh
docker ps -a --format '{{.Names}} {{.Status}}'
```

Çıkış kodu: 0

```text
b1-package-audit-03 Exited (0) 3 minutes ago

```

## iteration-03-compose-config

```sh
env DDS_TEST_PAYLOAD=simulation-b1-20261023-03 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml config --quiet
```

Çıkış kodu: 0

```text

```

## iteration-03-build

```sh
env DDS_TEST_PAYLOAD=simulation-b1-build-03 docker compose --progress plain -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml build simulation
```

Çıkış kodu: 0

```text
 Image ros2-fleet-simulation-lidar-check:humble-fortress Building
#1 [internal] load local bake definitions
#1 reading from stdin 633B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 403B done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/ros2-fleet-simulation-check:humble-fortress
#3 DONE 0.0s

#4 [internal] load .dockerignore
#4 transferring context: 2B done
#4 DONE 0.0s

#5 [1/3] FROM docker.io/library/ros2-fleet-simulation-check:humble-fortress@sha256:69cb7989a1a325add4f0ca325f4fa1e002beb4f2ffd415d59f1efd4e32151b39
#5 resolve docker.io/library/ros2-fleet-simulation-check:humble-fortress@sha256:69cb7989a1a325add4f0ca325f4fa1e002beb4f2ffd415d59f1efd4e32151b39 done
#5 CACHED

#6 [internal] load build context
#6 transferring context: 199B 0.0s done
#6 DONE 0.0s

#7 [2/3] RUN apt-get update && apt-get install -y --no-install-recommends     libignition-rendering6-ogre2     libignition-rendering6-ogre2-dev=6.6.4-1~jammy     && rm -rf /var/lib/apt/lists/*
#7 0.528 Get:1 http://packages.ros.org/ros2/ubuntu jammy InRelease [4682 B]
#7 0.609 Get:2 http://ports.ubuntu.com/ubuntu-ports jammy InRelease [270 kB]
#7 0.907 Get:3 http://packages.ros.org/ros2/ubuntu jammy/main Sources [1900 kB]
#7 1.653 Get:4 http://ports.ubuntu.com/ubuntu-ports jammy-updates InRelease [128 kB]
#7 3.007 Get:5 http://ports.ubuntu.com/ubuntu-ports jammy-backports InRelease [127 kB]
#7 5.189 Get:6 http://ports.ubuntu.com/ubuntu-ports jammy-security InRelease [129 kB]
#7 5.339 Get:7 http://packages.ros.org/ros2/ubuntu jammy/main arm64 Packages [1823 kB]
#7 6.189 Get:8 http://ports.ubuntu.com/ubuntu-ports jammy/restricted arm64 Packages [24.2 kB]
#7 8.648 Get:9 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 Packages [1758 kB]
#7 12.06 Get:10 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 Packages [17.2 MB]
#7 41.27 Get:11 http://ports.ubuntu.com/ubuntu-ports jammy/multiverse arm64 Packages [224 kB]
#7 41.91 Get:12 http://ports.ubuntu.com/ubuntu-ports jammy-updates/multiverse arm64 Packages [81.6 kB]
#7 42.34 Get:13 http://ports.ubuntu.com/ubuntu-ports jammy-updates/restricted arm64 Packages [8359 kB]
#7 56.69 Get:14 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 Packages [4567 kB]
#7 65.11 Get:15 http://ports.ubuntu.com/ubuntu-ports jammy-updates/universe arm64 Packages [1717 kB]
#7 68.23 Get:16 http://ports.ubuntu.com/ubuntu-ports jammy-backports/main arm64 Packages [82.5 kB]
#7 68.70 Get:17 http://ports.ubuntu.com/ubuntu-ports jammy-backports/universe arm64 Packages [33.7 kB]
#7 69.07 Get:18 http://ports.ubuntu.com/ubuntu-ports jammy-security/main arm64 Packages [4253 kB]
#7 76.40 Get:19 http://ports.ubuntu.com/ubuntu-ports jammy-security/universe arm64 Packages [1421 kB]
#7 79.13 Get:20 http://ports.ubuntu.com/ubuntu-ports jammy-security/multiverse arm64 Packages [75.6 kB]
#7 79.58 Get:21 http://ports.ubuntu.com/ubuntu-ports jammy-security/restricted arm64 Packages [8061 kB]
#7 93.46 Fetched 52.2 MB in 1min 33s (560 kB/s)
#7 93.46 Reading package lists...
#7 94.23 Reading package lists...
#7 94.94 Building dependency tree...
#7 95.16 Reading state information...
#7 95.38 The following additional packages will be installed:
#7 95.38   libblkid-dev libboost-atomic1.74-dev libboost-atomic1.74.0
#7 95.38   libboost-chrono1.74-dev libboost-chrono1.74.0 libboost-date-time1.74-dev
#7 95.38   libboost-date-time1.74.0 libboost-dev libboost-serialization1.74-dev
#7 95.38   libboost-serialization1.74.0 libboost-system1.74-dev libboost-system1.74.0
#7 95.38   libboost-thread-dev libboost-thread1.74-dev libboost-thread1.74.0
#7 95.38   libboost1.74-dev libffi-dev libglib2.0-bin libglib2.0-data libglib2.0-dev
#7 95.38   libglib2.0-dev-bin libgts-dev libignition-common4-core-dev
#7 95.38   libignition-common4-events-dev libignition-common4-graphics-dev
#7 95.38   libignition-math6-eigen3-dev libignition-plugin-dev
#7 95.38   libignition-rendering6-core-dev libmount-dev libogre-next-dev
#7 95.38   libogrenexthlmspbs2.2.5 libogrenexthlmsunlit2.2.5 libogrenextmain2.2.5
#7 95.38   libogrenextmeshlodgenerator2.2.5 libogrenextoverlay2.2.5
#7 95.38   libogrenextplanarreflections2.2.5 libogrenextsceneformat2.2.5 libopengl0
#7 95.38   libpcre16-3 libpcre2-32-0 libpcre2-dev libpcre2-posix3 libpcre3-dev
#7 95.38   libpcre32-3 libpcrecpp0v5 libselinux1-dev libsepol-dev libxrandr2
#7 95.38   libzzip-0-13
#7 95.39 Suggested packages:
#7 95.39   libboost-doc libboost1.74-doc libboost-container1.74-dev
#7 95.39   libboost-context1.74-dev libboost-contract1.74-dev
#7 95.39   libboost-coroutine1.74-dev libboost-exception1.74-dev libboost-fiber1.74-dev
#7 95.39   libboost-filesystem1.74-dev libboost-graph1.74-dev
#7 95.39   libboost-graph-parallel1.74-dev libboost-iostreams1.74-dev
#7 95.39   libboost-locale1.74-dev libboost-log1.74-dev libboost-math1.74-dev
#7 95.39   libboost-mpi1.74-dev libboost-mpi-python1.74-dev libboost-numpy1.74-dev
#7 95.39   libboost-program-options1.74-dev libboost-python1.74-dev
#7 95.39   libboost-random1.74-dev libboost-regex1.74-dev libboost-stacktrace1.74-dev
#7 95.39   libboost-test1.74-dev libboost-timer1.74-dev libboost-type-erasure1.74-dev
#7 95.39   libboost-wave1.74-dev libboost1.74-tools-dev libmpfrc++-dev libntl-dev
#7 95.39   libboost-nowide1.74-dev libgirepository1.0-dev libglib2.0-doc
#7 95.39   libgdk-pixbuf2.0-bin | libgdk-pixbuf2.0-dev libgts-doc ogre-next-doc
#7 95.46 The following NEW packages will be installed:
#7 95.46   libblkid-dev libboost-atomic1.74-dev libboost-atomic1.74.0
#7 95.46   libboost-chrono1.74-dev libboost-chrono1.74.0 libboost-date-time1.74-dev
#7 95.46   libboost-date-time1.74.0 libboost-dev libboost-serialization1.74-dev
#7 95.46   libboost-serialization1.74.0 libboost-system1.74-dev libboost-system1.74.0
#7 95.46   libboost-thread-dev libboost-thread1.74-dev libboost-thread1.74.0
#7 95.46   libboost1.74-dev libffi-dev libglib2.0-bin libglib2.0-data libglib2.0-dev
#7 95.46   libglib2.0-dev-bin libgts-dev libignition-common4-core-dev
#7 95.46   libignition-common4-events-dev libignition-common4-graphics-dev
#7 95.46   libignition-math6-eigen3-dev libignition-plugin-dev
#7 95.46   libignition-rendering6-core-dev libignition-rendering6-ogre2
#7 95.46   libignition-rendering6-ogre2-dev libmount-dev libogre-next-dev
#7 95.46   libogrenexthlmspbs2.2.5 libogrenexthlmsunlit2.2.5 libogrenextmain2.2.5
#7 95.46   libogrenextmeshlodgenerator2.2.5 libogrenextoverlay2.2.5
#7 95.46   libogrenextplanarreflections2.2.5 libogrenextsceneformat2.2.5 libopengl0
#7 95.46   libpcre16-3 libpcre2-32-0 libpcre2-dev libpcre2-posix3 libpcre3-dev
#7 95.46   libpcre32-3 libpcrecpp0v5 libselinux1-dev libsepol-dev libxrandr2
#7 95.46   libzzip-0-13
#7 95.72 0 upgraded, 51 newly installed, 0 to remove and 9 not upgraded.
#7 95.72 Need to get 23.1 MB of archives.
#7 95.72 After this operation, 227 MB of additional disk space will be used.
#7 95.72 Get:1 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libglib2.0-data all 2.72.4-0ubuntu2.10 [5596 B]
#7 95.82 Get:2 http://packages.ros.org/ros2/ubuntu jammy/main arm64 libignition-common4-core-dev arm64 4.8.1-1~jammy [112 kB]
#7 95.91 Get:3 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost1.74-dev arm64 1.74.0-14ubuntu3 [9609 kB]
#7 97.10 Get:4 http://packages.ros.org/ros2/ubuntu jammy/main arm64 libignition-common4-events-dev arm64 4.8.1-1~jammy [8312 B]
#7 97.72 Get:5 http://packages.ros.org/ros2/ubuntu jammy/main arm64 libignition-common4-graphics-dev arm64 4.8.1-1~jammy [8564 B]
#7 98.28 Get:6 http://packages.ros.org/ros2/ubuntu jammy/main arm64 libignition-math6-eigen3-dev arm64 6.16.0-1~jammy [10.2 kB]
#7 98.77 Get:7 http://packages.ros.org/ros2/ubuntu jammy/main arm64 libignition-plugin-dev arm64 1.4.0-1~jammy [168 kB]
#7 100.5 Get:8 http://packages.ros.org/ros2/ubuntu jammy/main arm64 libignition-rendering6-core-dev arm64 6.6.4-1~jammy [203 kB]
#7 102.7 Get:9 http://packages.ros.org/ros2/ubuntu jammy/main arm64 libignition-rendering6-ogre2 arm64 6.6.4-1~jammy [482 kB]
#7 105.7 Get:10 http://packages.ros.org/ros2/ubuntu jammy/main arm64 libignition-rendering6-ogre2-dev arm64 6.6.4-1~jammy [1108 kB]
#7 115.1 Get:11 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-atomic1.74.0 arm64 1.74.0-14ubuntu3 [224 kB]
#7 115.7 Get:12 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-atomic1.74-dev arm64 1.74.0-14ubuntu3 [222 kB]
#7 116.6 Get:13 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-chrono1.74.0 arm64 1.74.0-14ubuntu3 [232 kB]
#7 117.6 Get:14 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-chrono1.74-dev arm64 1.74.0-14ubuntu3 [239 kB]
#7 118.7 Get:15 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-date-time1.74.0 arm64 1.74.0-14ubuntu3 [221 kB]
#7 119.6 Get:16 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-serialization1.74.0 arm64 1.74.0-14ubuntu3 [319 kB]
#7 120.5 Get:17 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-serialization1.74-dev arm64 1.74.0-14ubuntu3 [374 kB]
#7 121.4 Get:18 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-date-time1.74-dev arm64 1.74.0-14ubuntu3 [226 kB]
#7 122.1 Get:19 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-dev arm64 1.74.0.3ubuntu7 [3490 B]
#7 122.3 Get:20 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-system1.74.0 arm64 1.74.0-14ubuntu3 [221 kB]
#7 123.1 Get:21 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-system1.74-dev arm64 1.74.0-14ubuntu3 [218 kB]
#7 123.8 Get:22 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-thread1.74.0 arm64 1.74.0-14ubuntu3 [260 kB]
#7 124.6 Get:23 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-thread1.74-dev arm64 1.74.0-14ubuntu3 [274 kB]
#7 125.4 Get:24 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libboost-thread-dev arm64 1.74.0.3ubuntu7 [3264 B]
#7 125.6 Get:25 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libglib2.0-bin arm64 2.72.4-0ubuntu2.10 [79.7 kB]
#7 126.0 Get:26 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libffi-dev arm64 3.4.2-4 [61.0 kB]
#7 126.4 Get:27 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libglib2.0-dev-bin arm64 2.72.4-0ubuntu2.10 [116 kB]
#7 127.0 Get:28 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libblkid-dev arm64 2.37.2-4ubuntu3.6 [198 kB]
#7 127.6 Get:29 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libsepol-dev arm64 3.3-1build1 [387 kB]
#7 128.7 Get:30 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libpcre2-32-0 arm64 10.39-3ubuntu0.1 [177 kB]
#7 129.3 Get:31 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libpcre2-posix3 arm64 10.39-3ubuntu0.1 [5968 B]
#7 129.5 Get:32 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libpcre2-dev arm64 10.39-3ubuntu0.1 [663 kB]
#7 130.9 Get:33 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libselinux1-dev arm64 3.3-1build2 [164 kB]
#7 131.5 Get:34 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libmount-dev arm64 2.37.2-4ubuntu3.6 [14.5 kB]
#7 131.7 Get:35 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libpcre16-3 arm64 2:8.39-13ubuntu0.22.04.1 [150 kB]
#7 132.3 Get:36 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libpcre32-3 arm64 2:8.39-13ubuntu0.22.04.1 [141 kB]
#7 132.9 Get:37 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libpcrecpp0v5 arm64 2:8.39-13ubuntu0.22.04.1 [16.1 kB]
#7 133.2 Get:38 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libpcre3-dev arm64 2:8.39-13ubuntu0.22.04.1 [527 kB]
#7 134.5 Get:39 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libglib2.0-dev arm64 2.72.4-0ubuntu2.10 [1829 kB]
#7 137.8 Get:40 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libgts-dev arm64 0.7.6+darcs121130-5 [202 kB]
#7 138.4 Get:41 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libxrandr2 arm64 2:1.5.2-1build1 [19.6 kB]
#7 138.8 Get:42 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libzzip-0-13 arm64 0.13.72+dfsg.1-1.1 [26.6 kB]
#7 139.2 Get:43 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenextmain2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [1973 kB]
#7 142.8 Get:44 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenextplanarreflections2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [32.9 kB]
#7 143.1 Get:45 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenexthlmspbs2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [213 kB]
#7 143.9 Get:46 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenexthlmsunlit2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [63.1 kB]
#7 144.3 Get:47 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenextoverlay2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [100 kB]
#7 144.8 Get:48 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 libopengl0 arm64 1.4.0-1 [38.6 kB]
#7 145.1 Get:49 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenextmeshlodgenerator2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [84.6 kB]
#7 145.6 Get:50 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogrenextsceneformat2.2.5 arm64 2.2.5+dfsg3-0ubuntu2 [73.3 kB]
#7 146.1 Get:51 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libogre-next-dev arm64 2.2.5+dfsg3-0ubuntu2 [1038 kB]
#7 148.1 debconf: delaying package configuration, since apt-utils is not installed
#7 148.1 Fetched 23.1 MB in 52s (441 kB/s)
#7 148.1 Selecting previously unselected package libglib2.0-data.
#7 148.1 (Reading database ...
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
#7 148.2 Preparing to unpack .../00-libglib2.0-data_2.72.4-0ubuntu2.10_all.deb ...
#7 148.2 Unpacking libglib2.0-data (2.72.4-0ubuntu2.10) ...
#7 148.2 Selecting previously unselected package libboost1.74-dev:arm64.
#7 148.2 Preparing to unpack .../01-libboost1.74-dev_1.74.0-14ubuntu3_arm64.deb ...
#7 148.2 Unpacking libboost1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 149.2 Selecting previously unselected package libboost-atomic1.74.0:arm64.
#7 149.2 Preparing to unpack .../02-libboost-atomic1.74.0_1.74.0-14ubuntu3_arm64.deb ...
#7 149.2 Unpacking libboost-atomic1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 149.2 Selecting previously unselected package libboost-atomic1.74-dev:arm64.
#7 149.3 Preparing to unpack .../03-libboost-atomic1.74-dev_1.74.0-14ubuntu3_arm64.deb ...
#7 149.3 Unpacking libboost-atomic1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 149.3 Selecting previously unselected package libboost-chrono1.74.0:arm64.
#7 149.3 Preparing to unpack .../04-libboost-chrono1.74.0_1.74.0-14ubuntu3_arm64.deb ...
#7 149.3 Unpacking libboost-chrono1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 149.3 Selecting previously unselected package libboost-chrono1.74-dev:arm64.
#7 149.3 Preparing to unpack .../05-libboost-chrono1.74-dev_1.74.0-14ubuntu3_arm64.deb ...
#7 149.3 Unpacking libboost-chrono1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 149.3 Selecting previously unselected package libboost-date-time1.74.0:arm64.
#7 149.3 Preparing to unpack .../06-libboost-date-time1.74.0_1.74.0-14ubuntu3_arm64.deb ...
#7 149.3 Unpacking libboost-date-time1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 149.3 Selecting previously unselected package libboost-serialization1.74.0:arm64.
#7 149.3 Preparing to unpack .../07-libboost-serialization1.74.0_1.74.0-14ubuntu3_arm64.deb ...
#7 149.3 Unpacking libboost-serialization1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 149.3 Selecting previously unselected package libboost-serialization1.74-dev:arm64.
#7 149.3 Preparing to unpack .../08-libboost-serialization1.74-dev_1.74.0-14ubuntu3_arm64.deb ...
#7 149.3 Unpacking libboost-serialization1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 149.4 Selecting previously unselected package libboost-date-time1.74-dev:arm64.
#7 149.4 Preparing to unpack .../09-libboost-date-time1.74-dev_1.74.0-14ubuntu3_arm64.deb ...
#7 149.4 Unpacking libboost-date-time1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 149.4 Selecting previously unselected package libboost-dev:arm64.
#7 149.4 Preparing to unpack .../10-libboost-dev_1.74.0.3ubuntu7_arm64.deb ...
#7 149.4 Unpacking libboost-dev:arm64 (1.74.0.3ubuntu7) ...
#7 149.4 Selecting previously unselected package libboost-system1.74.0:arm64.
#7 149.4 Preparing to unpack .../11-libboost-system1.74.0_1.74.0-14ubuntu3_arm64.deb ...
#7 149.4 Unpacking libboost-system1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 149.4 Selecting previously unselected package libboost-system1.74-dev:arm64.
#7 149.4 Preparing to unpack .../12-libboost-system1.74-dev_1.74.0-14ubuntu3_arm64.deb ...
#7 149.4 Unpacking libboost-system1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 149.4 Selecting previously unselected package libboost-thread1.74.0:arm64.
#7 149.4 Preparing to unpack .../13-libboost-thread1.74.0_1.74.0-14ubuntu3_arm64.deb ...
#7 149.4 Unpacking libboost-thread1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 149.5 Selecting previously unselected package libboost-thread1.74-dev:arm64.
#7 149.5 Preparing to unpack .../14-libboost-thread1.74-dev_1.74.0-14ubuntu3_arm64.deb ...
#7 149.5 Unpacking libboost-thread1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 149.5 Selecting previously unselected package libboost-thread-dev:arm64.
#7 149.5 Preparing to unpack .../15-libboost-thread-dev_1.74.0.3ubuntu7_arm64.deb ...
#7 149.5 Unpacking libboost-thread-dev:arm64 (1.74.0.3ubuntu7) ...
#7 149.5 Selecting previously unselected package libglib2.0-bin.
#7 149.5 Preparing to unpack .../16-libglib2.0-bin_2.72.4-0ubuntu2.10_arm64.deb ...
#7 149.5 Unpacking libglib2.0-bin (2.72.4-0ubuntu2.10) ...
#7 149.5 Selecting previously unselected package libffi-dev:arm64.
#7 149.5 Preparing to unpack .../17-libffi-dev_3.4.2-4_arm64.deb ...
#7 149.5 Unpacking libffi-dev:arm64 (3.4.2-4) ...
#7 149.5 Selecting previously unselected package libglib2.0-dev-bin.
#7 149.5 Preparing to unpack .../18-libglib2.0-dev-bin_2.72.4-0ubuntu2.10_arm64.deb ...
#7 149.5 Unpacking libglib2.0-dev-bin (2.72.4-0ubuntu2.10) ...
#7 149.5 Selecting previously unselected package libblkid-dev:arm64.
#7 149.5 Preparing to unpack .../19-libblkid-dev_2.37.2-4ubuntu3.6_arm64.deb ...
#7 149.5 Unpacking libblkid-dev:arm64 (2.37.2-4ubuntu3.6) ...
#7 149.6 Selecting previously unselected package libsepol-dev:arm64.
#7 149.6 Preparing to unpack .../20-libsepol-dev_3.3-1build1_arm64.deb ...
#7 149.6 Unpacking libsepol-dev:arm64 (3.3-1build1) ...
#7 149.6 Selecting previously unselected package libpcre2-32-0:arm64.
#7 149.6 Preparing to unpack .../21-libpcre2-32-0_10.39-3ubuntu0.1_arm64.deb ...
#7 149.6 Unpacking libpcre2-32-0:arm64 (10.39-3ubuntu0.1) ...
#7 149.6 Selecting previously unselected package libpcre2-posix3:arm64.
#7 149.6 Preparing to unpack .../22-libpcre2-posix3_10.39-3ubuntu0.1_arm64.deb ...
#7 149.6 Unpacking libpcre2-posix3:arm64 (10.39-3ubuntu0.1) ...
#7 149.6 Selecting previously unselected package libpcre2-dev:arm64.
#7 149.6 Preparing to unpack .../23-libpcre2-dev_10.39-3ubuntu0.1_arm64.deb ...
#7 149.6 Unpacking libpcre2-dev:arm64 (10.39-3ubuntu0.1) ...
#7 149.6 Selecting previously unselected package libselinux1-dev:arm64.
#7 149.6 Preparing to unpack .../24-libselinux1-dev_3.3-1build2_arm64.deb ...
#7 149.6 Unpacking libselinux1-dev:arm64 (3.3-1build2) ...
#7 149.6 Selecting previously unselected package libmount-dev:arm64.
#7 149.7 Preparing to unpack .../25-libmount-dev_2.37.2-4ubuntu3.6_arm64.deb ...
#7 149.7 Unpacking libmount-dev:arm64 (2.37.2-4ubuntu3.6) ...
#7 149.7 Selecting previously unselected package libpcre16-3:arm64.
#7 149.7 Preparing to unpack .../26-libpcre16-3_2%3a8.39-13ubuntu0.22.04.1_arm64.deb ...
#7 149.7 Unpacking libpcre16-3:arm64 (2:8.39-13ubuntu0.22.04.1) ...
#7 149.7 Selecting previously unselected package libpcre32-3:arm64.
#7 149.7 Preparing to unpack .../27-libpcre32-3_2%3a8.39-13ubuntu0.22.04.1_arm64.deb ...
#7 149.7 Unpacking libpcre32-3:arm64 (2:8.39-13ubuntu0.22.04.1) ...
#7 149.7 Selecting previously unselected package libpcrecpp0v5:arm64.
#7 149.7 Preparing to unpack .../28-libpcrecpp0v5_2%3a8.39-13ubuntu0.22.04.1_arm64.deb ...
#7 149.7 Unpacking libpcrecpp0v5:arm64 (2:8.39-13ubuntu0.22.04.1) ...
#7 149.7 Selecting previously unselected package libpcre3-dev:arm64.
#7 149.7 Preparing to unpack .../29-libpcre3-dev_2%3a8.39-13ubuntu0.22.04.1_arm64.deb ...
#7 149.7 Unpacking libpcre3-dev:arm64 (2:8.39-13ubuntu0.22.04.1) ...
#7 149.7 Selecting previously unselected package libglib2.0-dev:arm64.
#7 149.7 Preparing to unpack .../30-libglib2.0-dev_2.72.4-0ubuntu2.10_arm64.deb ...
#7 149.7 Unpacking libglib2.0-dev:arm64 (2.72.4-0ubuntu2.10) ...
#7 149.8 Selecting previously unselected package libgts-dev:arm64.
#7 149.8 Preparing to unpack .../31-libgts-dev_0.7.6+darcs121130-5_arm64.deb ...
#7 149.8 Unpacking libgts-dev:arm64 (0.7.6+darcs121130-5) ...
#7 149.8 Selecting previously unselected package libignition-common4-core-dev:arm64.
#7 149.8 Preparing to unpack .../32-libignition-common4-core-dev_4.8.1-1~jammy_arm64.deb ...
#7 149.8 Unpacking libignition-common4-core-dev:arm64 (4.8.1-1~jammy) ...
#7 149.8 Selecting previously unselected package libignition-common4-events-dev:arm64.
#7 149.8 Preparing to unpack .../33-libignition-common4-events-dev_4.8.1-1~jammy_arm64.deb ...
#7 149.8 Unpacking libignition-common4-events-dev:arm64 (4.8.1-1~jammy) ...
#7 149.8 Selecting previously unselected package libignition-common4-graphics-dev:arm64.
#7 149.8 Preparing to unpack .../34-libignition-common4-graphics-dev_4.8.1-1~jammy_arm64.deb ...
#7 149.9 Unpacking libignition-common4-graphics-dev:arm64 (4.8.1-1~jammy) ...
#7 149.9 Selecting previously unselected package libignition-math6-eigen3-dev:arm64.
#7 149.9 Preparing to unpack .../35-libignition-math6-eigen3-dev_6.16.0-1~jammy_arm64.deb ...
#7 149.9 Unpacking libignition-math6-eigen3-dev:arm64 (6.16.0-1~jammy) ...
#7 149.9 Selecting previously unselected package libignition-plugin-dev:arm64.
#7 149.9 Preparing to unpack .../36-libignition-plugin-dev_1.4.0-1~jammy_arm64.deb ...
#7 149.9 Unpacking libignition-plugin-dev:arm64 (1.4.0-1~jammy) ...
#7 149.9 Selecting previously unselected package libignition-rendering6-core-dev:arm64.
#7 149.9 Preparing to unpack .../37-libignition-rendering6-core-dev_6.6.4-1~jammy_arm64.deb ...
#7 149.9 Unpacking libignition-rendering6-core-dev:arm64 (6.6.4-1~jammy) ...
#7 149.9 Selecting previously unselected package libxrandr2:arm64.
#7 149.9 Preparing to unpack .../38-libxrandr2_2%3a1.5.2-1build1_arm64.deb ...
#7 149.9 Unpacking libxrandr2:arm64 (2:1.5.2-1build1) ...
#7 150.0 Selecting previously unselected package libzzip-0-13:arm64.
#7 150.0 Preparing to unpack .../39-libzzip-0-13_0.13.72+dfsg.1-1.1_arm64.deb ...
#7 150.0 Unpacking libzzip-0-13:arm64 (0.13.72+dfsg.1-1.1) ...
#7 150.0 Selecting previously unselected package libogrenextmain2.2.5:arm64.
#7 150.0 Preparing to unpack .../40-libogrenextmain2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 150.0 Unpacking libogrenextmain2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.0 Selecting previously unselected package libogrenextplanarreflections2.2.5:arm64.
#7 150.0 Preparing to unpack .../41-libogrenextplanarreflections2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 150.0 Unpacking libogrenextplanarreflections2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.0 Selecting previously unselected package libogrenexthlmspbs2.2.5:arm64.
#7 150.0 Preparing to unpack .../42-libogrenexthlmspbs2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 150.0 Unpacking libogrenexthlmspbs2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.0 Selecting previously unselected package libogrenexthlmsunlit2.2.5:arm64.
#7 150.0 Preparing to unpack .../43-libogrenexthlmsunlit2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 150.0 Unpacking libogrenexthlmsunlit2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.1 Selecting previously unselected package libogrenextoverlay2.2.5:arm64.
#7 150.1 Preparing to unpack .../44-libogrenextoverlay2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 150.1 Unpacking libogrenextoverlay2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.1 Selecting previously unselected package libopengl0:arm64.
#7 150.1 Preparing to unpack .../45-libopengl0_1.4.0-1_arm64.deb ...
#7 150.1 Unpacking libopengl0:arm64 (1.4.0-1) ...
#7 150.1 Selecting previously unselected package libignition-rendering6-ogre2:arm64.
#7 150.1 Preparing to unpack .../46-libignition-rendering6-ogre2_6.6.4-1~jammy_arm64.deb ...
#7 150.1 Unpacking libignition-rendering6-ogre2:arm64 (6.6.4-1~jammy) ...
#7 150.1 Selecting previously unselected package libogrenextmeshlodgenerator2.2.5:arm64.
#7 150.1 Preparing to unpack .../47-libogrenextmeshlodgenerator2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 150.1 Unpacking libogrenextmeshlodgenerator2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.2 Selecting previously unselected package libogrenextsceneformat2.2.5:arm64.
#7 150.2 Preparing to unpack .../48-libogrenextsceneformat2.2.5_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 150.2 Unpacking libogrenextsceneformat2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.2 Selecting previously unselected package libogre-next-dev.
#7 150.2 Preparing to unpack .../49-libogre-next-dev_2.2.5+dfsg3-0ubuntu2_arm64.deb ...
#7 150.2 Unpacking libogre-next-dev (2.2.5+dfsg3-0ubuntu2) ...
#7 150.2 Selecting previously unselected package libignition-rendering6-ogre2-dev:arm64.
#7 150.2 Preparing to unpack .../50-libignition-rendering6-ogre2-dev_6.6.4-1~jammy_arm64.deb ...
#7 150.2 Unpacking libignition-rendering6-ogre2-dev:arm64 (6.6.4-1~jammy) ...
#7 150.3 Setting up libboost-chrono1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 150.3 Setting up libpcrecpp0v5:arm64 (2:8.39-13ubuntu0.22.04.1) ...
#7 150.3 Setting up libboost-system1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 150.3 Setting up libglib2.0-dev-bin (2.72.4-0ubuntu2.10) ...
#7 150.4 Setting up libblkid-dev:arm64 (2.37.2-4ubuntu3.6) ...
#7 150.4 Setting up libignition-plugin-dev:arm64 (1.4.0-1~jammy) ...
#7 150.5 Setting up libboost1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 150.5 Setting up libboost-atomic1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 150.5 Setting up libpcre16-3:arm64 (2:8.39-13ubuntu0.22.04.1) ...
#7 150.5 Setting up libignition-common4-core-dev:arm64 (4.8.1-1~jammy) ...
#7 150.5 Setting up libboost-chrono1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 150.5 Setting up libignition-math6-eigen3-dev:arm64 (6.16.0-1~jammy) ...
#7 150.5 Setting up libzzip-0-13:arm64 (0.13.72+dfsg.1-1.1) ...
#7 150.5 Setting up libffi-dev:arm64 (3.4.2-4) ...
#7 150.5 Setting up libopengl0:arm64 (1.4.0-1) ...
#7 150.5 Setting up libpcre2-32-0:arm64 (10.39-3ubuntu0.1) ...
#7 150.5 Setting up libglib2.0-data (2.72.4-0ubuntu2.10) ...
#7 150.5 Setting up libignition-common4-events-dev:arm64 (4.8.1-1~jammy) ...
#7 150.5 Setting up libboost-system1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 150.5 Setting up libpcre32-3:arm64 (2:8.39-13ubuntu0.22.04.1) ...
#7 150.5 Setting up libxrandr2:arm64 (2:1.5.2-1build1) ...
#7 150.5 Setting up libsepol-dev:arm64 (3.3-1build1) ...
#7 150.5 Setting up libboost-atomic1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 150.5 Setting up libboost-serialization1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 150.5 Setting up libpcre2-posix3:arm64 (10.39-3ubuntu0.1) ...
#7 150.5 Setting up libboost-dev:arm64 (1.74.0.3ubuntu7) ...
#7 150.5 Setting up libboost-date-time1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 150.5 Setting up libboost-thread1.74.0:arm64 (1.74.0-14ubuntu3) ...
#7 150.5 Setting up libogrenextmain2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.5 Setting up libpcre2-dev:arm64 (10.39-3ubuntu0.1) ...
#7 150.5 Setting up libselinux1-dev:arm64 (3.3-1build2) ...
#7 150.5 Setting up libogrenextplanarreflections2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.5 Setting up libpcre3-dev:arm64 (2:8.39-13ubuntu0.22.04.1) ...
#7 150.5 Setting up libglib2.0-bin (2.72.4-0ubuntu2.10) ...
#7 150.6 Setting up libogrenextmeshlodgenerator2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.6 Setting up libboost-serialization1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 150.6 Setting up libogrenexthlmsunlit2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.6 Setting up libmount-dev:arm64 (2.37.2-4ubuntu3.6) ...
#7 150.6 Setting up libogrenexthlmspbs2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.6 Setting up libboost-date-time1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 150.6 Setting up libglib2.0-dev:arm64 (2.72.4-0ubuntu2.10) ...
#7 150.6 Setting up libogrenextoverlay2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.6 Setting up libogrenextsceneformat2.2.5:arm64 (2.2.5+dfsg3-0ubuntu2) ...
#7 150.6 Setting up libboost-thread1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#7 150.6 Setting up libboost-thread-dev:arm64 (1.74.0.3ubuntu7) ...
#7 150.6 Setting up libogre-next-dev (2.2.5+dfsg3-0ubuntu2) ...
#7 150.6 Setting up libignition-rendering6-ogre2:arm64 (6.6.4-1~jammy) ...
#7 150.6 Processing triggers for libglib2.0-0:arm64 (2.72.4-0ubuntu2.10) ...
#7 150.6 No schema files found: doing nothing.
#7 150.7 Processing triggers for libc-bin (2.35-0ubuntu3.15) ...
#7 150.7 Setting up libgts-dev:arm64 (0.7.6+darcs121130-5) ...
#7 150.7 Setting up libignition-common4-graphics-dev:arm64 (4.8.1-1~jammy) ...
#7 150.7 Setting up libignition-rendering6-core-dev:arm64 (6.6.4-1~jammy) ...
#7 150.7 Setting up libignition-rendering6-ogre2-dev:arm64 (6.6.4-1~jammy) ...
#7 DONE 151.4s

#8 [3/3] COPY docker/simulation-lidar-check/*.py /opt/simulation-lidar-check/
#8 DONE 0.1s

#9 exporting to image
#9 exporting layers
#9 exporting layers 2.9s done
#9 exporting manifest sha256:b1bf0062d06e3c0d9fb960a95ca57554da1d396489f144e344d5bd5a23d3ccc6 done
#9 exporting config sha256:e263f885cac89e90c1de697c477d0778dc914b627e8e9dbff189fada4c87ad55 done
#9 exporting attestation manifest sha256:c8f0548a9179d9905525c7c7c8e23601686fb55f981bc2ec467af6246a000b9b done
#9 exporting manifest list sha256:ba741517e3ef0d109d05315983a6ded3e16e79693d49a4f968e65f2b73695162 done
#9 naming to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress done
#9 unpacking to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress
#9 unpacking to docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress 1.1s done
#9 DONE 4.1s

#10 resolving provenance for metadata file
#10 DONE 0.0s
 Image ros2-fleet-simulation-lidar-check:humble-fortress Built

```

## iteration-03-installed-media

```sh
docker run --rm ros2-fleet-simulation-lidar-check:humble-fortress bash -c 'set -e
dpkg-query -W libignition-rendering6 libignition-rendering6-ogre2 libignition-rendering6-ogre2-dev libogrenextmain2.2.5 libogre-next-dev
dpkg -S /usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSL
ls -l /usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSL
dpkg --audit'
```

Çıkış kodu: 0

```text
libignition-rendering6:arm64	6.6.4-1~jammy
libignition-rendering6-ogre2:arm64	6.6.4-1~jammy
libignition-rendering6-ogre2-dev:arm64	6.6.4-1~jammy
libogre-next-dev	2.2.5+dfsg3-0ubuntu2
libogrenextmain2.2.5:arm64	2.2.5+dfsg3-0ubuntu2
libignition-rendering6-ogre2-dev:arm64: /usr/share/ignition/ignition-rendering6/ogre2/media/Hlms/Unlit/GLSL
total 20
-rw-r--r-- 1 root root 4234 Jan 29  2026 BlendModes_piece_ps.glsl
-rw-r--r-- 1 root root 3073 Jan 29  2026 PixelShader_ps.glsl
-rw-r--r-- 1 root root 1488 Jan 29  2026 Structs_piece_vs_piece_ps.glsl
-rw-r--r-- 1 root root 3294 Jan 29  2026 VertexShader_vs.glsl

```

## iteration-03-config-tests

```sh
docker run --rm --env-file config/dds.env -e DDS_TEST_PAYLOAD=b1-config-03 -e SIM_CHECK_ROLE=backend -v /Users/murat/develop/ros2-fleet-manager/config:/config:ro ros2-fleet-simulation-lidar-check:humble-fortress python3 /opt/simulation-lidar-check/test_config.py
```

Çıkış kodu: 0

```text
..
----------------------------------------------------------------------
Ran 2 tests in 0.021s

OK

```

## iteration-03-image

```sh
docker image inspect ros2-fleet-simulation-lidar-check:humble-fortress --format '{{.Id}} {{json .RepoDigests}} {{.Os}}/{{.Architecture}}'
```

Çıkış kodu: 0

```text
sha256:ba741517e3ef0d109d05315983a6ded3e16e79693d49a4f968e65f2b73695162 ["ros2-fleet-simulation-lidar-check@sha256:ba741517e3ef0d109d05315983a6ded3e16e79693d49a4f968e65f2b73695162"] linux/arm64

```

## run-b1-03

```sh
env DDS_TEST_PAYLOAD=simulation-b1-20261023-03 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml up --no-build --abort-on-container-exit --exit-code-from backend
```

Çıkış kodu: 0

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
 Container ros2-fleet-simulation-lidar-check-backend-1 Starting
 Container ros2-fleet-simulation-lidar-check-simulation-1 Starting
 Container ros2-fleet-simulation-lidar-check-backend-1 Started
 Container ros2-fleet-simulation-lidar-check-simulation-1 Started
backend-1  | {"event": "CONFIG_VALID", "role": "backend"}
simulation-1  | {"event": "CONFIG_VALID", "role": "simulation"}
simulation-1  | {"event": "PROCESS_START", "command": ["ign", "gazebo", "-s", "-r", "-v", "4", "--headless-rendering", "--physics-engine", "/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5", "--render-engine-server", "/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6", "/tmp/lidar-world.sdf"]}
simulation-1  | {"event": "PROCESS_START", "command": ["ros2", "run", "ros_gz_bridge", "parameter_bridge", "/validation_robot/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan", "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock", "/validation_robot/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry", "/validation_robot/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"]}
backend-1     | {"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp"}
simulation-1  | [INFO] [1792756972.663459802] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/validation_robot/scan (ignition.msgs.LaserScan) -> /validation_robot/scan (sensor_msgs/msg/LaserScan)] (Lazy 0)
simulation-1  | [INFO] [1792756972.665169635] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/clock (ignition.msgs.Clock) -> /clock (rosgraph_msgs/msg/Clock)] (Lazy 0)
simulation-1  | [INFO] [1792756972.665603677] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/validation_robot/odom (ignition.msgs.Odometry) -> /validation_robot/odom (nav_msgs/msg/Odometry)] (Lazy 0)
simulation-1  | [INFO] [1792756972.666293510] [ros_gz_bridge]: Creating ROS->GZ Bridge: [/validation_robot/cmd_vel (geometry_msgs/msg/Twist) -> /validation_robot/cmd_vel (ignition.msgs.Twist)] (Lazy 0)
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
backend-1     | {"event": "SCAN", "count": 1, "stamp": 0.002, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 2, "stamp": 0.2, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 3, "stamp": 0.4, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 4, "stamp": 0.6, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 5, "stamp": 0.8, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 6, "stamp": 1.0, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 7, "stamp": 1.2, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 8, "stamp": 1.4, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 9, "stamp": 1.6, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 10, "stamp": 1.8, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "B1_PASS", "messages": 10, "token": "simulation-b1-20261023-03"}
backend-1     | {"event": "SCAN_SUMMARY", "validated_messages": 10, "queued_messages": 0}

backend-1 exited with code 0
 Compose Stopping Aborting on container exit...
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopping
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopping
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopped
simulation-1  | [INFO] [1792756977.411732596] [rclcpp]: signal_handler(SIGINT/SIGTERM)
simulation-1  | [Msg] Serving world names on [/gazebo/worlds]
simulation-1  | [Msg] Resource path add service on [/gazebo/resource_paths/add].
simulation-1  | [Msg] Resource path get service on [/gazebo/resource_paths/get].
simulation-1  | [Msg] Resource path resolve service on [/gazebo/resource_paths/resolve].
simulation-1  | [Msg] Resource paths published on [/gazebo/resource_paths].
simulation-1  | [Msg] Server control service on [/server_control].
simulation-1  | [Msg] Found no publishers on /stats, adding root stats topic
simulation-1  | [Msg] Found no publishers on /clock, adding root clock topic
simulation-1  | [Dbg] [SimulationRunner.cc:501] Creating PostUpdate worker threads: 4
simulation-1  | [Dbg] [SimulationRunner.cc:512] Creating postupdate worker thread (0)
simulation-1  | [Dbg] [SimulationRunner.cc:512] Creating postupdate worker thread (1)
simulation-1  | [Dbg] [SimulationRunner.cc:512] Creating postupdate worker thread (2)
simulation-1  | [Dbg] [Sensors.cc:610] Initialization needed
simulation-1  | [Dbg] [Sensors.cc:270] Initializing render context
simulation-1  | [Msg] Loading plugin [/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6]
simulation-1  | [Msg] Serving scene information on [/world/validation_world/scene/info]
simulation-1  | [Msg] Serving graph information on [/world/validation_world/scene/graph]
simulation-1  | [Msg] Serving full state on [/world/validation_world/state]
simulation-1  | [Msg] Serving full state (async) on [/world/validation_world/state_async]
simulation-1  | [Msg] Publishing scene information on [/world/validation_world/scene/info]
simulation-1  | [Msg] Publishing entity deletions on [/world/validation_world/scene/deletion]
simulation-1  | [Msg] Publishing state changes on [/world/validation_world/state]
simulation-1  | [Msg] Publishing pose messages on [/world/validation_world/pose/info]
simulation-1  | [Msg] Publishing dynamic pose messages on [/world/validation_world/dynamic_pose/info]
simulation-1  | [Dbg] [RenderUtil.cc:2591] Create scene [scene]
simulation-1  | [Dbg] [Sensors.cc:284] Rendering Thread initialized
simulation-1  | [Dbg] [Sensors.cc:610] Initialization needed
simulation-1  | [Dbg] [Lidar.cc:138] Laser scans for [validation_robot::base_link::lidar] advertised on [/validation_robot/scan]
simulation-1  | [Dbg] [GpuLidarSensor.cc:163] Lidar points for [validation_robot::base_link::lidar] advertised on [/validation_robot/scan/points]
simulation-1  | [Dbg] [SignalHandler.cc:141] Received signal[2].
simulation-1  | [Dbg] [ServerPrivate.cc:110] Server received signal[2]
simulation-1  | [Dbg] [Sensors.cc:439] SensorsPrivate::Stop
simulation-1  | [Dbg] [Sensors.cc:425] SensorsPrivate::RenderThread stopped
simulation-1  | [Dbg] [gz.cc:410] Shutting down ign-gazebo-server
simulation-1  | [Dbg] [SimulationRunner.cc:528] Exiting postupdate worker thread (0)
simulation-1  | [Dbg] [SimulationRunner.cc:528] Exiting postupdate worker thread (2)
simulation-1  | [Dbg] [SimulationRunner.cc:528] Exiting postupdate worker thread (1)
simulation-1  | [Dbg] [Sensors.cc:439] SensorsPrivate::Stop
simulation-1  | {"event": "PROCESS_EXIT", "command": ["ign", "gazebo", "-s", "-r", "-v", "4", "--headless-rendering", "--physics-engine", "/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5", "--render-engine-server", "/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6", "/tmp/lidar-world.sdf"], "code": 0}
simulation-1  | {"event": "PROCESS_EXIT", "command": ["ros2", "run", "ros_gz_bridge", "parameter_bridge", "/validation_robot/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan", "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock", "/validation_robot/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry", "/validation_robot/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"], "code": 0}
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopped

simulation-1 exited with code 0

```

## inspect-containers-03

```sh
docker inspect ros2-fleet-simulation-lidar-check-backend-1 ros2-fleet-simulation-lidar-check-simulation-1 --format '{{.Name}} image={{.Image}} status={{.State.Status}} exit={{.State.ExitCode}} networks={{json .NetworkSettings.Networks}} mounts={{json .Mounts}}'
```

Çıkış kodu: 0

```text
/ros2-fleet-simulation-lidar-check-backend-1 image=sha256:ba741517e3ef0d109d05315983a6ded3e16e79693d49a4f968e65f2b73695162 status=exited exit=0 networks={"ros2-fleet-simulation-lidar-check_dds":{"IPAMConfig":null,"Links":null,"Aliases":["ros2-fleet-simulation-lidar-check-backend-1","backend"],"DriverOpts":null,"GwPriority":0,"NetworkID":"ac6862fc8aa9c70221bdcf9400bffa291767b3f7311d4ef4d815a6fe5fd58f02","EndpointID":"","Gateway":"","IPAddress":"","MacAddress":"","IPPrefixLen":0,"IPv6Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"DNSNames":["ros2-fleet-simulation-lidar-check-backend-1","backend","fba7ac9bf847"]}} mounts=[{"Type":"bind","Source":"/Users/murat/develop/ros2-fleet-manager/config","Destination":"/config","Mode":"ro","RW":false,"Propagation":"rprivate"}]
/ros2-fleet-simulation-lidar-check-simulation-1 image=sha256:ba741517e3ef0d109d05315983a6ded3e16e79693d49a4f968e65f2b73695162 status=exited exit=0 networks={"ros2-fleet-simulation-lidar-check_dds":{"IPAMConfig":null,"Links":null,"Aliases":["ros2-fleet-simulation-lidar-check-simulation-1","simulation"],"DriverOpts":null,"GwPriority":0,"NetworkID":"ac6862fc8aa9c70221bdcf9400bffa291767b3f7311d4ef4d815a6fe5fd58f02","EndpointID":"","Gateway":"","IPAddress":"","MacAddress":"","IPPrefixLen":0,"IPv6Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"DNSNames":["ros2-fleet-simulation-lidar-check-simulation-1","simulation","413d7f11387c"]}} mounts=[{"Type":"bind","Source":"/Users/murat/develop/ros2-fleet-manager/config","Destination":"/config","Mode":"ro","RW":false,"Propagation":"rprivate"}]

```

## down-b1-03

```sh
env DDS_TEST_PAYLOAD=simulation-b1-20261023-03 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml down
```

Çıkış kodu: 0

```text
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopping
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopping
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopped
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopped
 Container ros2-fleet-simulation-lidar-check-simulation-1 Removing
 Container ros2-fleet-simulation-lidar-check-backend-1 Removing
 Container ros2-fleet-simulation-lidar-check-backend-1 Removed
 Container ros2-fleet-simulation-lidar-check-simulation-1 Removed
 Network ros2-fleet-simulation-lidar-check_dds Removing
 Network ros2-fleet-simulation-lidar-check_dds Removed

```

## cleanup-check-03

```sh
sh -c 'docker ps -a --filter label=com.docker.compose.project=ros2-fleet-simulation-lidar-check && docker network ls --filter name=ros2-fleet-simulation-lidar-check'
```

Çıkış kodu: 0

```text
CONTAINER ID   IMAGE          COMMAND                  CREATED         STATUS                     PORTS     NAMES
c792d57c28dd   b61a40e60409   "/ros_entrypoint.sh …"   7 minutes ago   Exited (0) 5 minutes ago             b1-package-audit-03
NETWORK ID   NAME      DRIVER    SCOPE

```

## run-b1-04

```sh
env DDS_TEST_PAYLOAD=simulation-b1-20261023-04 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml up --no-build --abort-on-container-exit --exit-code-from backend
```

Çıkış kodu: 0

```text
 Network ros2-fleet-simulation-lidar-check_dds Creating
 Network ros2-fleet-simulation-lidar-check_dds Creating
 Network ros2-fleet-simulation-lidar-check_dds Created
 Network ros2-fleet-simulation-lidar-check_dds Created
 Container ros2-fleet-simulation-lidar-check-backend-1 Creating
 Container ros2-fleet-simulation-lidar-check-simulation-1 Creating
 Container ros2-fleet-simulation-lidar-check-simulation-1 Created
 Container ros2-fleet-simulation-lidar-check-backend-1 Created
Attaching to backend-1, simulation-1
 Container ros2-fleet-simulation-lidar-check-backend-1 Starting
 Container ros2-fleet-simulation-lidar-check-simulation-1 Starting
 Container ros2-fleet-simulation-lidar-check-backend-1 Started
 Container ros2-fleet-simulation-lidar-check-simulation-1 Started
backend-1  | {"event": "CONFIG_VALID", "role": "backend"}
simulation-1  | {"event": "CONFIG_VALID", "role": "simulation"}
simulation-1  | {"event": "PROCESS_START", "command": ["ign", "gazebo", "-s", "-r", "-v", "4", "--headless-rendering", "--physics-engine", "/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5", "--render-engine-server", "/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6", "/tmp/lidar-world.sdf"]}
simulation-1  | {"event": "PROCESS_START", "command": ["ros2", "run", "ros_gz_bridge", "parameter_bridge", "/validation_robot/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan", "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock", "/validation_robot/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry", "/validation_robot/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"]}
backend-1     | {"event": "BACKEND_START", "rmw": "rmw_cyclonedds_cpp"}
simulation-1  | [INFO] [1792756989.171806254] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/validation_robot/scan (ignition.msgs.LaserScan) -> /validation_robot/scan (sensor_msgs/msg/LaserScan)] (Lazy 0)
simulation-1  | [INFO] [1792756989.172457545] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/clock (ignition.msgs.Clock) -> /clock (rosgraph_msgs/msg/Clock)] (Lazy 0)
simulation-1  | [INFO] [1792756989.172676754] [ros_gz_bridge]: Creating GZ->ROS Bridge: [/validation_robot/odom (ignition.msgs.Odometry) -> /validation_robot/odom (nav_msgs/msg/Odometry)] (Lazy 0)
simulation-1  | [INFO] [1792756989.172911545] [ros_gz_bridge]: Creating ROS->GZ Bridge: [/validation_robot/cmd_vel (geometry_msgs/msg/Twist) -> /validation_robot/cmd_vel (ignition.msgs.Twist)] (Lazy 0)
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
backend-1     | {"event": "SCAN", "count": 1, "stamp": 0.002, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 2, "stamp": 0.2, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 3, "stamp": 0.4, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 4, "stamp": 0.6, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 5, "stamp": 0.8, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 6, "stamp": 1.0, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 7, "stamp": 1.2, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 8, "stamp": 1.4, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 9, "stamp": 1.6, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "SCAN", "count": 10, "stamp": 1.8, "frame": "validation_robot/base_link/lidar", "samples": 31, "minimum": 1.950119137763977, "maximum": 2.0773568153381348, "max_wall_error_m": 0.004366011590752894}
backend-1     | {"event": "B1_PASS", "messages": 10, "token": "simulation-b1-20261023-04"}
backend-1     | {"event": "SCAN_SUMMARY", "validated_messages": 10, "queued_messages": 0}

backend-1 exited with code 0
 Compose Stopping Aborting on container exit...
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopping
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopping
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopped
simulation-1  | [INFO] [1792756994.009189964] [rclcpp]: signal_handler(SIGINT/SIGTERM)
simulation-1  | [Msg] Serving world names on [/gazebo/worlds]
simulation-1  | [Msg] Resource path add service on [/gazebo/resource_paths/add].
simulation-1  | [Msg] Resource path get service on [/gazebo/resource_paths/get].
simulation-1  | [Msg] Resource path resolve service on [/gazebo/resource_paths/resolve].
simulation-1  | [Msg] Resource paths published on [/gazebo/resource_paths].
simulation-1  | [Msg] Server control service on [/server_control].
simulation-1  | [Msg] Found no publishers on /stats, adding root stats topic
simulation-1  | [Msg] Found no publishers on /clock, adding root clock topic
simulation-1  | [Dbg] [SimulationRunner.cc:501] Creating PostUpdate worker threads: 4
simulation-1  | [Dbg] [SimulationRunner.cc:512] Creating postupdate worker thread (0)
simulation-1  | [Dbg] [SimulationRunner.cc:512] Creating postupdate worker thread (1)
simulation-1  | [Dbg] [SimulationRunner.cc:512] Creating postupdate worker thread (2)
simulation-1  | [Dbg] [Sensors.cc:610] Initialization needed
simulation-1  | [Dbg] [Sensors.cc:270] Initializing render context
simulation-1  | [Msg] Loading plugin [/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6]
simulation-1  | [Msg] Serving scene information on [/world/validation_world/scene/info]
simulation-1  | [Msg] Serving graph information on [/world/validation_world/scene/graph]
simulation-1  | [Msg] Serving full state on [/world/validation_world/state]
simulation-1  | [Msg] Serving full state (async) on [/world/validation_world/state_async]
simulation-1  | [Msg] Publishing scene information on [/world/validation_world/scene/info]
simulation-1  | [Msg] Publishing entity deletions on [/world/validation_world/scene/deletion]
simulation-1  | [Msg] Publishing state changes on [/world/validation_world/state]
simulation-1  | [Msg] Publishing pose messages on [/world/validation_world/pose/info]
simulation-1  | [Msg] Publishing dynamic pose messages on [/world/validation_world/dynamic_pose/info]
simulation-1  | [Dbg] [RenderUtil.cc:2591] Create scene [scene]
simulation-1  | [Dbg] [Sensors.cc:610] [Dbg] [Sensors.cc:610] [Dbg] [Sensors.cc:284] Rendering Thread initialized
simulation-1  | Initialization needed
simulation-1  | [Dbg] [Lidar.cc:138] Laser scans for [validation_robot::base_link::lidar] advertised on [/validation_robot/scan]
simulation-1  | [Dbg] [GpuLidarSensor.cc:163] Lidar points for [validation_robot::base_link::lidar] advertised on [/validation_robot/scan/points]
simulation-1  | [Dbg] [SignalHandler.cc:141] Received signal[2].
simulation-1  | [Dbg] [ServerPrivate.cc:110] Server received signal[2]
simulation-1  | [Dbg] [Sensors.cc:439] SensorsPrivate::Stop
simulation-1  | [Dbg] [Sensors.cc:425] SensorsPrivate::RenderThread stopped
simulation-1  | [Dbg] [gz.cc:410] Shutting down ign-gazebo-server
simulation-1  | [Dbg] [SimulationRunner.cc:528] Exiting postupdate worker thread (0)
simulation-1  | [Dbg] [SimulationRunner.cc:528] Exiting postupdate worker thread (1)
simulation-1  | [Dbg] [SimulationRunner.cc:528] Exiting postupdate worker thread (2)
simulation-1  | [Dbg] [Sensors.cc:439] SensorsPrivate::Stop
simulation-1  | {"event": "PROCESS_EXIT", "command": ["ign", "gazebo", "-s", "-r", "-v", "4", "--headless-rendering", "--physics-engine", "/usr/lib/aarch64-linux-gnu/ign-physics-5/engine-plugins/libignition-physics5-dartsim-plugin.so.5", "--render-engine-server", "/usr/lib/aarch64-linux-gnu/ign-rendering-6/engine-plugins/libignition-rendering6-ogre2.so.6", "/tmp/lidar-world.sdf"], "code": 0}
simulation-1  | {"event": "PROCESS_EXIT", "command": ["ros2", "run", "ros_gz_bridge", "parameter_bridge", "/validation_robot/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan", "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock", "/validation_robot/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry", "/validation_robot/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist"], "code": 0}
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopped

simulation-1 exited with code 0

```

## remove-package-audit-03

```sh
docker rm b1-package-audit-03
```

Çıkış kodu: 0

```text
b1-package-audit-03

```

## inspect-containers-04

```sh
docker inspect ros2-fleet-simulation-lidar-check-backend-1 ros2-fleet-simulation-lidar-check-simulation-1 --format '{{.Name}} image={{.Image}} status={{.State.Status}} exit={{.State.ExitCode}} networks={{json .NetworkSettings.Networks}} mounts={{json .Mounts}}'
```

Çıkış kodu: 0

```text
/ros2-fleet-simulation-lidar-check-backend-1 image=sha256:ba741517e3ef0d109d05315983a6ded3e16e79693d49a4f968e65f2b73695162 status=exited exit=0 networks={"ros2-fleet-simulation-lidar-check_dds":{"IPAMConfig":null,"Links":null,"Aliases":["ros2-fleet-simulation-lidar-check-backend-1","backend"],"DriverOpts":null,"GwPriority":0,"NetworkID":"976d4de780f2680e2ed9448f90c5c64be02518dca28931a6620ba55e302c9540","EndpointID":"","Gateway":"","IPAddress":"","MacAddress":"","IPPrefixLen":0,"IPv6Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"DNSNames":["ros2-fleet-simulation-lidar-check-backend-1","backend","044d3b1a3130"]}} mounts=[{"Type":"bind","Source":"/Users/murat/develop/ros2-fleet-manager/config","Destination":"/config","Mode":"ro","RW":false,"Propagation":"rprivate"}]
/ros2-fleet-simulation-lidar-check-simulation-1 image=sha256:ba741517e3ef0d109d05315983a6ded3e16e79693d49a4f968e65f2b73695162 status=exited exit=0 networks={"ros2-fleet-simulation-lidar-check_dds":{"IPAMConfig":null,"Links":null,"Aliases":["ros2-fleet-simulation-lidar-check-simulation-1","simulation"],"DriverOpts":null,"GwPriority":0,"NetworkID":"976d4de780f2680e2ed9448f90c5c64be02518dca28931a6620ba55e302c9540","EndpointID":"","Gateway":"","IPAddress":"","MacAddress":"","IPPrefixLen":0,"IPv6Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"DNSNames":["ros2-fleet-simulation-lidar-check-simulation-1","simulation","efa8f5685eb9"]}} mounts=[{"Type":"bind","Source":"/Users/murat/develop/ros2-fleet-manager/config","Destination":"/config","Mode":"ro","RW":false,"Propagation":"rprivate"}]

```

## down-b1-04

```sh
env DDS_TEST_PAYLOAD=simulation-b1-20261023-04 docker compose -f docker-compose.dds.yml -f docker-compose.simulation-check.yml -f docker-compose.simulation-lidar-check.yml down
```

Çıkış kodu: 0

```text
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopping
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopping
 Container ros2-fleet-simulation-lidar-check-simulation-1 Stopped
 Container ros2-fleet-simulation-lidar-check-simulation-1 Removing
 Container ros2-fleet-simulation-lidar-check-backend-1 Stopped
 Container ros2-fleet-simulation-lidar-check-backend-1 Removing
 Container ros2-fleet-simulation-lidar-check-backend-1 Removed
 Container ros2-fleet-simulation-lidar-check-simulation-1 Removed
 Network ros2-fleet-simulation-lidar-check_dds Removing
 Network ros2-fleet-simulation-lidar-check_dds Removed

```

## cleanup-check-04

```sh
sh -c 'docker ps -a --filter label=com.docker.compose.project=ros2-fleet-simulation-lidar-check && docker network ls --filter name=ros2-fleet-simulation-lidar-check'
```

Çıkış kodu: 0

```text
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
NETWORK ID   NAME      DRIVER    SCOPE

```

## iteration-03-04-final-evidence

```sh
python3 /tmp/b1-final-check-03.py
```

Çıkış kodu: 1

```text
docker: Error response from daemon: No such image: sha256:b61a40e60409a13f50c91d048d54be25121ac8c734d876a8e67db54886eeaacc

Run 'docker run --help' for more information
03 PASS messages= 10 max_wall_error_m= 0.004366011590752894
04 PASS messages= 10 max_wall_error_m= 0.004366011590752894
Files changed during this task: ["docker/simulation-lidar-check/Dockerfile", "docs/simulation-stage-b-2026-10-23.md", "docs/simulation-stage-b-commands-2026-10-23.md"]
Traceback (most recent call last):
  File "/tmp/b1-final-check-03.py", line 24, in <module>
    old=inventory('sha256:b61a40e60409a13f50c91d048d54be25121ac8c734d876a8e67db54886eeaacc')
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/tmp/b1-final-check-03.py", line 22, in inventory
    output=subprocess.check_output(['docker','run','--rm',image,'dpkg-query','-W','-f=${binary:Package}\t${Version}\n'],text=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/subprocess.py", line 466, in check_output
    return run(*popenargs, stdout=PIPE, timeout=timeout, check=True,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/subprocess.py", line 571, in run
    raise CalledProcessError(retcode, process.args,
subprocess.CalledProcessError: Command '['docker', 'run', '--rm', 'sha256:b61a40e60409a13f50c91d048d54be25121ac8c734d876a8e67db54886eeaacc', 'dpkg-query', '-W', '-f=${binary:Package}\t${Version}\n']' returned non-zero exit status 125.

```

## iteration-03-04-diff-check

```sh
git diff --check
```

Çıkış kodu: 0

```text

```

## iteration-03-04-log-and-scope-check

```sh
python3 /tmp/b1-final-check-03.py
```

Çıkış kodu: 0

```text
03 PASS messages= 10 max_wall_error_m= 0.004366011590752894
04 PASS messages= 10 max_wall_error_m= 0.004366011590752894
Files changed during this task: ["docker/simulation-lidar-check/Dockerfile", "docs/simulation-stage-b-2026-10-23.md", "docs/simulation-stage-b-commands-2026-10-23.md"]

```

## iteration-03-04-final-diff-check

```sh
git diff --check
```

Çıkış kodu: 0

```text

```
