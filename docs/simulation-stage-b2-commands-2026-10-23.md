# Aşama B2 komut ve çıktı eki

[Ana kayıt](simulation-stage-b2-2026-10-23.md). Komut çıktıları stdout/stderr birlikte kaydedilir.

## official-arm64-preflight

```sh
docker run --rm --platform linux/arm64 ros2-fleet-simulation-lidar-check:humble-fortress bash -c 'set -e; dpkg --print-architecture; cat /etc/os-release; apt-get update -o APT::Update::Error-Mode=any; apt-cache policy ros-humble-navigation2 ros-humble-nav2-bringup; apt-get --simulate install --no-install-recommends ros-humble-navigation2 ros-humble-nav2-bringup'
```

Çıkış kodu: 0

```text
arm64
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
Get:1 http://ports.ubuntu.com/ubuntu-ports jammy InRelease [270 kB]
Get:2 http://packages.ros.org/ros2/ubuntu jammy InRelease [4682 B]
Get:3 http://packages.ros.org/ros2/ubuntu jammy/main Sources [1900 kB]
Get:4 http://ports.ubuntu.com/ubuntu-ports jammy-updates InRelease [128 kB]
Get:5 http://ports.ubuntu.com/ubuntu-ports jammy-backports InRelease [127 kB]
Get:6 http://ports.ubuntu.com/ubuntu-ports jammy-security InRelease [129 kB]
Get:7 http://ports.ubuntu.com/ubuntu-ports jammy/multiverse arm64 Packages [224 kB]
Get:8 http://packages.ros.org/ros2/ubuntu jammy/main arm64 Packages [1823 kB]
Get:9 http://ports.ubuntu.com/ubuntu-ports jammy/restricted arm64 Packages [24.2 kB]
Get:10 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 Packages [17.2 MB]
Get:11 http://ports.ubuntu.com/ubuntu-ports jammy/main arm64 Packages [1758 kB]
Get:12 http://ports.ubuntu.com/ubuntu-ports jammy-updates/universe arm64 Packages [1717 kB]
Get:13 http://ports.ubuntu.com/ubuntu-ports jammy-updates/multiverse arm64 Packages [81.6 kB]
Get:14 http://ports.ubuntu.com/ubuntu-ports jammy-updates/restricted arm64 Packages [8359 kB]
Get:15 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 Packages [4567 kB]
Get:16 http://ports.ubuntu.com/ubuntu-ports jammy-backports/main arm64 Packages [82.5 kB]
Get:17 http://ports.ubuntu.com/ubuntu-ports jammy-backports/universe arm64 Packages [33.7 kB]
Get:18 http://ports.ubuntu.com/ubuntu-ports jammy-security/restricted arm64 Packages [8061 kB]
Get:19 http://ports.ubuntu.com/ubuntu-ports jammy-security/main arm64 Packages [4253 kB]
Get:20 http://ports.ubuntu.com/ubuntu-ports jammy-security/multiverse arm64 Packages [75.6 kB]
Get:21 http://ports.ubuntu.com/ubuntu-ports jammy-security/universe arm64 Packages [1421 kB]
Fetched 52.2 MB in 1min 38s (532 kB/s)
Reading package lists...
ros-humble-navigation2:
  Installed: (none)
  Candidate: 1.1.20-1jammy.20260916.170645
  Version table:
     1.1.20-1jammy.20260916.170645 500
        500 http://packages.ros.org/ros2/ubuntu jammy/main arm64 Packages
ros-humble-nav2-bringup:
  Installed: (none)
  Candidate: 1.1.20-1jammy.20260916.171610
  Version table:
     1.1.20-1jammy.20260916.171610 500
        500 http://packages.ros.org/ros2/ubuntu jammy/main arm64 Packages
Reading package lists...
Building dependency tree...
Reading state information...
[Uzun bağımlılık listesi kısaltıldı; APT özeti ve Nav2 kurulum sürümleri korundu.]
2 upgraded, 472 newly installed, 0 to remove and 7 not upgraded.
Inst ros-humble-nav2-msgs (1.1.20-1jammy.20260908.013256 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-common (1.1.20-1jammy.20260907.233655 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-util (1.1.20-1jammy.20260916.052614 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-voxel-grid (1.1.20-1jammy.20260908.021935 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-costmap-2d (1.1.20-1jammy.20260916.124031 ROS jammy:jammy [arm64])
Inst ros-humble-nav-2d-msgs (1.1.20-1jammy.20260907.224739 ROS jammy:jammy [arm64])
Inst ros-humble-dwb-msgs (1.1.20-1jammy.20260907.230913 ROS jammy:jammy [arm64])
Inst ros-humble-nav-2d-utils (1.1.20-1jammy.20260916.053930 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-core (1.1.20-1jammy.20260916.130152 ROS jammy:jammy [arm64])
Inst ros-humble-dwb-core (1.1.20-1jammy.20260916.130615 ROS jammy:jammy [arm64])
Inst ros-humble-dwb-critics (1.1.20-1jammy.20260916.140436 ROS jammy:jammy [arm64])
Inst ros-humble-dwb-plugins (1.1.20-1jammy.20260916.131350 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-amcl (1.1.20-1jammy.20260916.053520 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-behavior-tree (1.1.20-1jammy.20260916.053536 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-behaviors (1.1.20-1jammy.20260916.130521 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-bt-navigator (1.1.20-1jammy.20260916.130559 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-collision-monitor (1.1.20-1jammy.20260916.130132 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-constrained-smoother (1.1.20-1jammy.20260916.131338 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-controller (1.1.20-1jammy.20260916.131334 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-dwb-controller (1.1.20-1jammy.20260916.141101 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-lifecycle-manager (1.1.20-1jammy.20260916.123216 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-map-server (1.1.20-1jammy.20260916.053559 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-mppi-controller (1.1.20-1jammy.20260916.130539 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-navfn-planner (1.1.20-1jammy.20260916.130623 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-planner (1.1.20-1jammy.20260916.131155 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-regulated-pure-pursuit-controller (1.1.20-1jammy.20260916.130553 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-rotation-shim-controller (1.1.20-1jammy.20260916.132139 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-route (1.1.20-1jammy.20260916.131155 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-rviz-plugins (1.1.20-1jammy.20260916.165114 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-simple-commander (1.1.20-1jammy.20260908.014111 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-smac-planner (1.1.20-1jammy.20260916.131156 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-smoother (1.1.20-1jammy.20260916.131356 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-theta-star-planner (1.1.20-1jammy.20260916.131205 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-velocity-smoother (1.1.20-1jammy.20260916.130306 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-waypoint-follower (1.1.20-1jammy.20260916.131202 ROS jammy:jammy [arm64])
Inst ros-humble-navigation2 (1.1.20-1jammy.20260916.170645 ROS jammy:jammy [arm64])
Inst ros-humble-nav2-bringup (1.1.20-1jammy.20260916.171610 ROS jammy:jammy [arm64])

```

## build-official-nav2

```sh
docker build --platform linux/arm64 --progress plain -f docker/simulation-nav2-check/Dockerfile -t ros2-fleet-simulation-nav2-check:humble-fortress .
```

Çıkış kodu: 0

```text
#0 building with "desktop-linux" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 434B done
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress
#2 DONE 0.0s

#3 [internal] load .dockerignore
#3 transferring context: 2B done
#3 DONE 0.0s

#4 [1/2] FROM docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress@sha256:ba741517e3ef0d109d05315983a6ded3e16e79693d49a4f968e65f2b73695162
#4 resolve docker.io/library/ros2-fleet-simulation-lidar-check:humble-fortress@sha256:ba741517e3ef0d109d05315983a6ded3e16e79693d49a4f968e65f2b73695162 done
#4 DONE 0.0s

#5 [2/2] RUN apt-get update -o APT::Update::Error-Mode=any && apt-get install -y --no-install-recommends     ros-humble-navigation2=1.1.20-1jammy.20260916.170645     ros-humble-nav2-bringup=1.1.20-1jammy.20260916.171610     && dpkg --audit     && rm -rf /var/lib/apt/lists/*
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 91.20 Get:20 http://ports.ubuntu.com/ubuntu-ports jammy-security/universe arm64 Packages [1421 kB]
#5 93.87 Get:21 http://ports.ubuntu.com/ubuntu-ports jammy-security/multiverse arm64 Packages [75.6 kB]
#5 94.17 Fetched 52.2 MB in 1min 34s (556 kB/s)
#5 94.17 Reading package lists...
#5 95.14 Reading package lists...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 97.01 The following packages will be upgraded:
#5 97.02   liblzma5 libsystemd0
#5 97.29 2 upgraded, 472 newly installed, 0 to remove and 7 not upgraded.
#5 97.29 Need to get 230 MB of archives.
#5 97.29 After this operation, 1136 MB of additional disk space will be used.
#5 97.29 Get:1 http://ports.ubuntu.com/ubuntu-ports jammy-updates/main arm64 libsystemd0 arm64 249.11-0ubuntu3.23 [312 kB]
#5 97.46 Get:2 http://packages.ros.org/ros2/ubuntu jammy/main arm64 ros-humble-angles arm64 1.15.0-1jammy.20260307.125919 [14.3 kB]
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 616.5 Get:473 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libomp-dev arm64 1:14.0-55~exp2 [3074 B]
#5 616.7 Get:474 http://ports.ubuntu.com/ubuntu-ports jammy/universe arm64 libassimp-dev arm64 5.2.2~ds0-1 [145 kB]
#5 617.5 debconf: delaying package configuration, since apt-utils is not installed
#5 617.5 Fetched 230 MB in 8min 40s (442 kB/s)
#5 617.5 (Reading database ...
(Reading database ... 5%
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 618.4 Setting up libip4tc2:arm64 (1.8.7-1ubuntu5.2) ...
#5 618.4 Setting up libkmod2:arm64 (29-1ubuntu1.1) ...
#5 618.4 Setting up systemd (249.11-0ubuntu3.23) ...
#5 618.4 Created symlink /etc/systemd/system/getty.target.wants/getty@tty1.service → /lib/systemd/system/getty@.service.
#5 618.4 Created symlink /etc/systemd/system/multi-user.target.wants/remote-fs.target → /lib/systemd/system/remote-fs.target.
#5 618.4 Created symlink /etc/systemd/system/dbus-org.freedesktop.resolve1.service → /lib/systemd/system/systemd-resolved.service.
#5 618.4 Created symlink /etc/systemd/system/multi-user.target.wants/systemd-resolved.service → /lib/systemd/system/systemd-resolved.service.
#5 618.4 ln: failed to create symbolic link '/etc/resolv.conf': Device or resource busy
#5 618.4 Created symlink /etc/systemd/system/sysinit.target.wants/systemd-pstore.service → /lib/systemd/system/systemd-pstore.service.
#5 618.4 Initializing machine ID from random generator.
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 633.2 Setting up libdw1:arm64 (0.186-1ubuntu0.1) ...
#5 633.2 Setting up libjpeg-turbo8-dev:arm64 (2.1.2-0ubuntu1) ...
#5 633.2 Setting up systemd-sysv (249.11-0ubuntu3.23) ...
#5 633.2 Setting up libmysqlclient21:arm64 (8.0.46-0ubuntu0.22.04.4) ...
#5 633.2 Setting up libraw1394-11:arm64 (2.1.2-2build2) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 633.3 Setting up libraw1394-dev:arm64 (2.1.2-2build2) ...
#5 633.3 Setting up libxcursor1:arm64 (1:1.2.0-2build4) ...
#5 633.3 Setting up ros-humble-nav2-voxel-grid (1.1.20-1jammy.20260908.021935) ...
#5 633.3 Setting up libboost-system-dev:arm64 (1.74.0.3ubuntu7) ...
#5 633.3 Setting up libpng-dev:arm64 (1.6.37-3ubuntu0.7) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 633.4 Setting up libnspr4:arm64 (2:4.35-0ubuntu0.22.04.1) ...
#5 633.4 Setting up libcurl4-openssl-dev:arm64 (7.81.0-1ubuntu1.30) ...
#5 633.4 Setting up ros-humble-nav2-msgs (1.1.20-1jammy.20260908.013256) ...
#5 633.4 Setting up libavahi-common-data:arm64 (0.8-5ubuntu5.5) ...
#5 633.4 Setting up libgles1:arm64 (1.4.0-1) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 633.5 Setting up libassimp-dev:arm64 (5.2.2~ds0-1) ...
#5 633.5 Setting up libboost-serialization-dev:arm64 (1.74.0.3ubuntu7) ...
#5 633.5 Setting up ros-humble-nav-2d-msgs (1.1.20-1jammy.20260907.224739) ...
#5 633.5 Setting up libboost1.74-tools-dev (1.74.0-14ubuntu3) ...
#5 633.5 Setting up libboost-date-time-dev:arm64 (1.74.0.3ubuntu7) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 633.7 Setting up openmpi-common (4.1.2-2ubuntu1) ...
#5 633.7 Setting up libpam-systemd:arm64 (249.11-0ubuntu3.23) ...
#5 633.7 debconf: unable to initialize frontend: Dialog
#5 633.7 debconf: (TERM is not set, so the dialog frontend is not usable.)
#5 633.7 debconf: falling back to frontend: Readline
#5 633.8 Setting up ros-humble-laser-geometry (2.4.1-1jammy.20260916.044848) ...
#5 633.8 Setting up xorg-sgml-doctools (1:1.11-1.1) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 633.9 Setting up libsuitesparseconfig5:arm64 (1:5.10.1+dfsg-4build1) ...
#5 633.9 Setting up iso-codes (4.9.0-1) ...
#5 633.9 Setting up ros-humble-nav2-common (1.1.20-1jammy.20260907.233655) ...
#5 633.9 Setting up libboost-filesystem-dev:arm64 (1.74.0.3ubuntu7) ...
#5 633.9 Setting up libbrotli-dev:arm64 (1.0.9-2build6) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 634.0 Setting up qt5-qmake:arm64 (5.15.3+dfsg-2ubuntu0.2) ...
#5 634.0 Setting up libboost-container1.74-dev:arm64 (1.74.0-14ubuntu3) ...
#5 634.0 Setting up ros-humble-nav2-simple-commander (1.1.20-1jammy.20260908.014111) ...
#5 634.0 Setting up openssh-client (1:8.9p1-3ubuntu0.18) ...
#5 634.1 update-alternatives: using /usr/bin/ssh to provide /usr/bin/rsh (rsh) in auto mode
#5 634.1 update-alternatives: warning: skip creation of /usr/share/man/man1/rsh.1.gz because associated file /usr/share/man/man1/ssh.1.gz (of link group rsh) doesn't exist
#5 634.1 update-alternatives: using /usr/bin/slogin to provide /usr/bin/rlogin (rlogin) in auto mode
#5 634.1 update-alternatives: warning: skip creation of /usr/share/man/man1/rlogin.1.gz because associated file /usr/share/man/man1/slogin.1.gz (of link group rlogin) doesn't exist
#5 634.1 update-alternatives: using /usr/bin/scp to provide /usr/bin/rcp (rcp) in auto mode
#5 634.1 update-alternatives: warning: skip creation of /usr/share/man/man1/rcp.1.gz because associated file /usr/share/man/man1/scp.1.gz (of link group rcp) doesn't exist
#5 634.1 Setting up libboost-math-dev:arm64 (1.74.0.3ubuntu7) ...
#5 634.1 Setting up libboost-coroutine1.74.0:arm64 (1.74.0-14ubuntu3) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 634.4 Setting up automake (1:1.16.5-1.3) ...
#5 634.4 update-alternatives: using /usr/bin/automake-1.16 to provide /usr/bin/automake (automake) in auto mode
#5 634.4 update-alternatives: warning: skip creation of /usr/share/man/man1/automake.1.gz because associated file /usr/share/man/man1/automake-1.16.1.gz (of link group automake) doesn't exist
#5 634.4 update-alternatives: warning: skip creation of /usr/share/man/man1/aclocal.1.gz because associated file /usr/share/man/man1/aclocal-1.16.1.gz (of link group automake) doesn't exist
#5 634.4 Setting up libopencv-calib3d4.5d:arm64 (4.5.4+dfsg-9ubuntu4) ...
#5 634.4 Setting up libspqr2:arm64 (1:5.10.1+dfsg-4build1) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 634.4 Setting up libboost-locale-dev:arm64 (1.74.0.3ubuntu7) ...
#5 634.4 Setting up dconf-service (0.40.0-3ubuntu0.1) ...
#5 634.4 Setting up ros-humble-nav2-util (1.1.20-1jammy.20260916.052614) ...
#5 634.4 Setting up libboost-context-dev:arm64 (1.74.0.3ubuntu7) ...
#5 634.4 Setting up libboost-iostreams-dev:arm64 (1.74.0.3ubuntu7) ...
#5 634.4 Setting up libboost-type-erasure-dev:arm64 (1.74.0.3ubuntu7) ...
#5 634.5 Setting up ros-humble-nav2-lifecycle-manager (1.1.20-1jammy.20260916.123216) ...
#5 634.5 Setting up libnl-route-3-dev:arm64 (3.5.0-0.1) ...
#5 634.5 Setting up libopencv-video4.5d:arm64 (4.5.4+dfsg-9ubuntu4) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 634.5 Setting up libopencv-imgproc-dev:arm64 (4.5.4+dfsg-9ubuntu4) ...
#5 634.5 Setting up libopencv-dnn-dev:arm64 (4.5.4+dfsg-9ubuntu4) ...
#5 634.5 Setting up ros-humble-nav2-costmap-2d (1.1.20-1jammy.20260916.124031) ...
#5 634.5 Setting up libopencv-objdetect4.5d:arm64 (4.5.4+dfsg-9ubuntu4) ...
#5 634.5 Setting up libboost-numpy-dev (1.74.0.3ubuntu7) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 634.5 Setting up libhwloc-dev:arm64 (2.7.0-2ubuntu1) ...
#5 634.5 Setting up libgoogle-glog-dev (0.5.0+really0.4.0-2) ...
#5 634.5 Setting up ros-humble-nav-2d-utils (1.1.20-1jammy.20260916.053930) ...
#5 634.5 Setting up ros-humble-nav2-collision-monitor (1.1.20-1jammy.20260916.130132) ...
#5 634.5 Setting up libpmix-dev:arm64 (4.1.2-2ubuntu1) ...
#5 634.5 Setting up ros-humble-nav2-core (1.1.20-1jammy.20260916.130152) ...
#5 634.5 Setting up libopencv-shape-dev:arm64 (4.5.4+dfsg-9ubuntu4) ...
#5 634.5 Setting up librdmacm1:arm64 (39.0-1) ...
#5 634.5 Setting up libucx0:arm64 (1.12.1~rc2-1) ...
#5 634.5 Setting up ros-humble-nav2-velocity-smoother (1.1.20-1jammy.20260916.130306) ...
#5 634.5 Setting up ros-humble-nav2-theta-star-planner (1.1.20-1jammy.20260916.131205) ...
#5 634.5 Setting up dconf-gsettings-backend:arm64 (0.40.0-3ubuntu0.1) ...
#5 634.5 Setting up libsuitesparse-dev:arm64 (1:5.10.1+dfsg-4build1) ...
#5 634.5 Setting up ros-humble-nav2-behavior-tree (1.1.20-1jammy.20260916.053536) ...
#5 634.5 Setting up ros-humble-nav2-planner (1.1.20-1jammy.20260916.131155) ...
#5 634.5 Setting up ros-humble-nav2-bt-navigator (1.1.20-1jammy.20260916.130559) ...
#5 634.5 Setting up ros-humble-nav2-regulated-pure-pursuit-controller (1.1.20-1jammy.20260916.130553) ...
#5 634.6 Setting up libopencv-photo-dev:arm64 (4.5.4+dfsg-9ubuntu4) ...
#5 634.6 Setting up ros-humble-nav2-controller (1.1.20-1jammy.20260916.131334) ...
#5 634.6 Setting up ros-humble-nav2-amcl (1.1.20-1jammy.20260916.053520) ...
#5 634.6 Setting up libibverbs-dev:arm64 (39.0-1) ...
#5 634.6 Setting up ros-humble-nav2-smoother (1.1.20-1jammy.20260916.131356) ...
#5 634.6 Setting up ros-humble-dwb-core (1.1.20-1jammy.20260916.130615) ...
#5 634.6 Setting up libqt5printsupport5:arm64 (5.15.3+dfsg-2ubuntu0.2) ...
#5 634.6 Setting up ros-humble-dwb-critics (1.1.20-1jammy.20260916.140436) ...
#5 634.6 Setting up ros-humble-nav2-mppi-controller (1.1.20-1jammy.20260916.130539) ...
#5 634.6 Setting up libgdal30 (3.4.1+dfsg-1build4) ...
#5 634.6 Setting up ros-humble-nav2-route (1.1.20-1jammy.20260916.131155) ...
#5 634.6 Setting up ros-humble-nav2-behaviors (1.1.20-1jammy.20260916.130521) ...
#5 634.6 Setting up libceres-dev (2.0.0+dfsg1-5) ...
#5 634.6 Setting up ros-humble-nav2-constrained-smoother (1.1.20-1jammy.20260916.131338) ...
#5 634.6 Setting up ros-humble-dwb-plugins (1.1.20-1jammy.20260916.131350) ...
#5 634.6 Setting up ros-humble-nav2-navfn-planner (1.1.20-1jammy.20260916.130623) ...
#5 634.6 Setting up ros-humble-nav2-rotation-shim-controller (1.1.20-1jammy.20260916.132139) ...
#5 634.6 Setting up libgtk-3-common (3.24.33-1ubuntu2.2) ...
#5 634.6 Setting up libfabric1:arm64 (1.11.0-3) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 634.6 Setting up libboost-mpi1.74.0 (1.74.0-14ubuntu3) ...
#5 634.6 Setting up libopencv-imgcodecs-dev:arm64 (4.5.4+dfsg-9ubuntu4) ...
#5 634.6 Setting up ros-humble-nav2-dwb-controller (1.1.20-1jammy.20260916.141101) ...
#5 634.6 Setting up libvtk9.1:arm64 (9.1.0+really9.1.0+dfsg2-3build1) ...
#5 634.6 Setting up libopencv-viz4.5d:arm64 (4.5.4+dfsg-9ubuntu4) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 634.6 Setting up openmpi-bin (4.1.2-2ubuntu1) ...
#5 634.6 update-alternatives: using /usr/bin/mpirun.openmpi to provide /usr/bin/mpirun (mpirun) in auto mode
#5 634.6 update-alternatives: warning: skip creation of /usr/share/man/man1/mpirun.1.gz because associated file /usr/share/man/man1/mpirun.openmpi.1.gz (of link group mpirun) doesn't exist
#5 634.6 update-alternatives: warning: skip creation of /usr/share/man/man1/mpiexec.1.gz because associated file /usr/share/man/man1/mpiexec.openmpi.1.gz (of link group mpirun) doesn't exist
#5 634.6 update-alternatives: using /usr/bin/mpicc.openmpi to provide /usr/bin/mpicc (mpi) in auto mode
#5 634.6 update-alternatives: warning: skip creation of /usr/share/man/man1/mpicc.1.gz because associated file /usr/share/man/man1/mpicc.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.6 update-alternatives: warning: skip creation of /usr/share/man/man1/mpic++.1.gz because associated file /usr/share/man/man1/mpic++.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.6 update-alternatives: warning: skip creation of /usr/share/man/man1/mpicxx.1.gz because associated file /usr/share/man/man1/mpicxx.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.6 update-alternatives: warning: skip creation of /usr/share/man/man1/mpiCC.1.gz because associated file /usr/share/man/man1/mpiCC.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.6 update-alternatives: warning: skip creation of /usr/share/man/man1/mpif77.1.gz because associated file /usr/share/man/man1/mpif77.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.6 update-alternatives: warning: skip creation of /usr/share/man/man1/mpif90.1.gz because associated file /usr/share/man/man1/mpif90.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.6 update-alternatives: warning: skip creation of /usr/share/man/man1/mpifort.1.gz because associated file /usr/share/man/man1/mpifort.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.6 Setting up libhdf5-openmpi-103-1:arm64 (1.10.7+repack-4ubuntu2) ...
#5 634.6 Setting up mpi-default-bin (1.14) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 634.7 Setting up libhdf5-openmpi-dev (1.10.7+repack-4ubuntu2) ...
#5 634.7 update-alternatives: using /usr/bin/h5pcc.openmpi to provide /usr/bin/h5pcc (h5pcc) in auto mode
#5 634.7 update-alternatives: warning: skip creation of /usr/share/man/man1/h5pcc.1.gz because associated file /usr/share/man/man1/h5pcc.openmpi.1.gz (of link group h5pcc) doesn't exist
#5 634.7 update-alternatives: warning: skip creation of /usr/share/man/man1/h5pfc.1.gz because associated file /usr/share/man/man1/h5pfc.openmpi.1.gz (of link group h5pcc) doesn't exist
#5 634.7 update-alternatives: using /usr/lib/aarch64-linux-gnu/pkgconfig/hdf5-openmpi.pc to provide /usr/lib/aarch64-linux-gnu/pkgconfig/hdf5.pc (hdf5.pc) in auto mode
#5 634.7 update-alternatives: updating alternative /usr/bin/mpicc.openmpi because link group mpi has changed slave links
#5 634.7 update-alternatives: warning: skip creation of /usr/share/man/man1/mpiCC.1.gz because associated file /usr/share/man/man1/mpiCC.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.7 update-alternatives: warning: skip creation of /usr/share/man/man1/mpic++.1.gz because associated file /usr/share/man/man1/mpic++.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.7 update-alternatives: warning: skip creation of /usr/share/man/man1/mpicc.1.gz because associated file /usr/share/man/man1/mpicc.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.7 update-alternatives: warning: skip creation of /usr/share/man/man1/mpicxx.1.gz because associated file /usr/share/man/man1/mpicxx.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.7 update-alternatives: warning: skip creation of /usr/share/man/man1/mpif77.1.gz because associated file /usr/share/man/man1/mpif77.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.7 update-alternatives: warning: skip creation of /usr/share/man/man1/mpif90.1.gz because associated file /usr/share/man/man1/mpif90.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.7 update-alternatives: warning: skip creation of /usr/share/man/man1/mpifort.1.gz because associated file /usr/share/man/man1/mpifort.openmpi.1.gz (of link group mpi) doesn't exist
#5 634.7 update-alternatives: using /usr/lib/aarch64-linux-gnu/pkgconfig/hdf5-mpi.pc to provide /usr/lib/aarch64-linux-gnu/pkgconfig/hdf5.pc (hdf5.pc) in auto mode
#5 634.7 Setting up libboost-mpi1.74-dev (1.74.0-14ubuntu3) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 634.7 Setting up libflann-dev:arm64 (1.9.1+dfsg-11) ...
#5 634.7 Setting up ros-humble-ompl (1.7.0-4jammy.20260306.230109) ...
#5 634.7 Setting up ros-humble-nav2-smac-planner (1.1.20-1jammy.20260916.131156) ...
#5 634.8 Setting up adwaita-icon-theme (41.0-1ubuntu1) ...
#5 634.8 update-alternatives: using /usr/share/icons/Adwaita/cursor.theme to provide /usr/share/icons/default/index.theme (x-cursor-theme) in auto mode
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 635.3 Setting up libglvnd-dev:arm64 (1.4.0-1) ...
#5 635.3 Setting up libglew-dev:arm64 (2.2.0-4) ...
#5 635.3 Setting up ros-humble-nav2-map-server (1.1.20-1jammy.20260916.053559) ...
#5 635.3 Setting up libgl1-mesa-dev:arm64 (23.2.1-1ubuntu3.1~22.04.4) ...
#5 635.3 Setting up libopencv-videostab-dev:arm64 (4.5.4+dfsg-9ubuntu4) ...
[Rutin paket indirme/açma/kurma satırları kısaltıldı.]
#5 635.4 Setting up ros-humble-cv-bridge (3.2.1-1jammy.20260907.222938) ...
#5 635.4 Setting up ros-humble-rviz-common (11.2.29-1jammy.20260916.054717) ...
#5 635.4 Setting up ros-humble-nav2-waypoint-follower (1.1.20-1jammy.20260916.131202) ...
#5 635.4 Setting up ros-humble-rviz-default-plugins (11.2.29-1jammy.20260916.153147) ...
#5 635.4 Setting up ros-humble-nav2-rviz-plugins (1.1.20-1jammy.20260916.165114) ...
#5 635.4 Setting up ros-humble-slam-toolbox (2.6.10-1jammy.20260916.165114) ...
#5 635.4 Setting up ros-humble-navigation2 (1.1.20-1jammy.20260916.170645) ...
#5 635.4 Setting up ros-humble-nav2-bringup (1.1.20-1jammy.20260916.171610) ...
#5 635.4 Processing triggers for libc-bin (2.35-0ubuntu3.15) ...
#5 DONE 636.9s

#6 exporting to image
#6 exporting layers
#6 exporting layers 20.1s done
#6 exporting manifest sha256:7d794bc76eb6075e948607b8b85a76358c3eccaefdcca8c8eb97071bdb85228b done
#6 exporting config sha256:9729615e7370f866bf3f82f7d45ae093c67c23bf1aa3e8abadb2bad3e9f02936 done
#6 exporting attestation manifest sha256:dcbbabfe94122e8b23ef3138f51e779ad1a8fb50d9aab59f70ec0f91cfbd7142 done
#6 exporting manifest list sha256:dc766635005bba89c4f7b2ea9fcaf6b5273f4421a6a03116db819f49e05f21c0 done
#6 naming to docker.io/library/ros2-fleet-simulation-nav2-check:humble-fortress done
#6 unpacking to docker.io/library/ros2-fleet-simulation-nav2-check:humble-fortress
#6 unpacking to docker.io/library/ros2-fleet-simulation-nav2-check:humble-fortress 5.8s done
#6 DONE 25.9s

View build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/p007iljt9ilrjuqdlo8341bjr
```

## installed-package-evidence

```sh
docker run --rm --platform linux/arm64 ros2-fleet-simulation-nav2-check:humble-fortress bash -c 'set -e; dpkg --print-architecture; dpkg-query -W -f="${binary:Package}\t${Version}\t${Architecture}\t${db:Status-Status}\n" ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-nav2-amcl ros-humble-nav2-map-server ros-humble-nav2-controller ros-humble-nav2-planner ros-humble-nav2-bt-navigator ros-humble-nav2-lifecycle-manager; dpkg --audit'
```

Çıkış kodu: 0

```text
arm64









```

## image-identity

```sh
docker image inspect ros2-fleet-simulation-nav2-check:humble-fortress --format '{{.Id}} {{.Os}}/{{.Architecture}}'
```

Çıkış kodu: 0

```text
sha256:dc766635005bba89c4f7b2ea9fcaf6b5273f4421a6a03116db819f49e05f21c0 linux/arm64

```

## installed-versions

```sh
docker run --rm --platform linux/arm64 ros2-fleet-simulation-nav2-check:humble-fortress dpkg-query -W '-f=${binary:Package}\t${Version}\t${Architecture}\t${db:Status-Status}\n' ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-nav2-amcl ros-humble-nav2-map-server ros-humble-nav2-controller ros-humble-nav2-planner ros-humble-nav2-bt-navigator ros-humble-nav2-lifecycle-manager
```

Çıkış kodu: 0

```text
ros-humble-nav2-amcl	1.1.20-1jammy.20260916.053520	arm64	installed
ros-humble-nav2-bringup	1.1.20-1jammy.20260916.171610	arm64	installed
ros-humble-nav2-bt-navigator	1.1.20-1jammy.20260916.130559	arm64	installed
ros-humble-nav2-controller	1.1.20-1jammy.20260916.131334	arm64	installed
ros-humble-nav2-lifecycle-manager	1.1.20-1jammy.20260916.123216	arm64	installed
ros-humble-nav2-map-server	1.1.20-1jammy.20260916.053559	arm64	installed
ros-humble-nav2-planner	1.1.20-1jammy.20260916.131155	arm64	installed
ros-humble-navigation2	1.1.20-1jammy.20260916.170645	arm64	installed

```

## final-diff-check

```sh
git diff --check
```

Çıkış kodu: 0

```text

```

## final-file-scope

```sh
git status --short
```

Çıkış kodu: 0

```text
?? docker/simulation-nav2-check/
?? docs/simulation-stage-b2-2026-10-23.md
?? docs/simulation-stage-b2-commands-2026-10-23.md

```

## remaining-test-containers

```sh
docker ps -a --filter ancestor=ros2-fleet-simulation-nav2-check:humble-fortress --format '{{.ID}} {{.Names}} {{.Status}}'
```

Çıkış kodu: 0

```text

```

## remaining-preflight-containers

```sh
docker ps -a --filter ancestor=ros2-fleet-simulation-lidar-check:humble-fortress --format '{{.ID}} {{.Names}} {{.Status}}'
```

Çıkış kodu: 0

```text

```

## b2-network-check

```sh
docker network ls --filter name=ros2-fleet-simulation-nav2-check
```

Çıkış kodu: 0

```text
NETWORK ID   NAME      DRIVER    SCOPE

```
