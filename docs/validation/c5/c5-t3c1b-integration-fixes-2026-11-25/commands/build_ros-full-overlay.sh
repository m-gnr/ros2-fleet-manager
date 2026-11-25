#!/usr/bin/env bash
# Explicit experiment overlay only. Never changes the default image/launcher.
set -euo pipefail
root=$(pwd -P)
output=${1:?provide a NEW overlay/evidence directory}
mkdir "$output"
output=$(cd "$output" && pwd -P)
mkdir "$output/src"
if [[ -n "${C5_UPSTREAM_ARCHIVE_DIR:-}" ]]; then
 cp "$C5_UPSTREAM_ARCHIVE_DIR/nav2-1.1.20.tar.gz" "$output/"
 cp "$C5_UPSTREAM_ARCHIVE_DIR/ros_gz-0.244.27.tar.gz" "$output/"
else
 curl -fsSL https://codeload.github.com/ros-navigation/navigation2/tar.gz/refs/tags/1.1.20 -o "$output/nav2-1.1.20.tar.gz"
 curl -fsSL https://codeload.github.com/gazebosim/ros_gz/tar.gz/refs/tags/0.244.27 -o "$output/ros_gz-0.244.27.tar.gz"
fi
python3 - "$output" <<'PY'
import hashlib,pathlib,sys
p=pathlib.Path(sys.argv[1])
expected={'nav2-1.1.20.tar.gz':'c965b7a36ef48cd7f35f01c1f98883741693d195dae582232d6d0444d2eedab6',
          'ros_gz-0.244.27.tar.gz':'a48188634154764a4fec2f232db83f274a116292dc620c0c3c4c2738cf38aa33'}
for name,digest in expected.items():
    if hashlib.sha256((p/name).read_bytes()).hexdigest()!=digest:raise SystemExit('Upstream archive hash mismatch: '+name)
PY
tar -xzf "$output/nav2-1.1.20.tar.gz" -C "$output/src" navigation2-1.1.20/nav2_costmap_2d
tar -xzf "$output/ros_gz-0.244.27.tar.gz" -C "$output/src" ros_gz-0.244.27/ros_gz_bridge
patch -d "$output/src/navigation2-1.1.20" -p1 < docker/experiments/c5-t3c1b/patches/nav2-costmap-cleanup.patch
patch -d "$output/src/ros_gz-0.244.27" -p1 < docker/experiments/c5-t3c1b/patches/ros-gz-callback-owner.patch
docker image inspect c5-b6b5-build:local --format '{{.Id}}' > "$output/image-id.txt"
docker run --rm --network none --workdir /workspace -v "$root:/workspace:ro" -v "$output:/build" c5-b6b5-build:local bash -ec '
 source /opt/ros/humble/setup.bash
 export GZ_VERSION=fortress
 export MAKEFLAGS="-j2" CMAKE_BUILD_PARALLEL_LEVEL=2
 dpkg-query -W ros-humble-nav2-costmap-2d ros-humble-ros-gz-bridge ros-humble-rclcpp libignition-transport11-dev > /build/packages.tsv
 colcon --log-base /build/log build --base-paths /build/src/navigation2-1.1.20/nav2_costmap_2d /build/src/ros_gz-0.244.27/ros_gz_bridge interfaces/fleet_interfaces ros2_ws/src/fleet_nav2_observer ros2_ws/src/fleet_perception --build-base /build/build --install-base /build/install --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_TESTING=OFF
 find /build/install -type f \( -name "*.so" -o -name parameter_bridge \) -print0 | sort -z | xargs -0 sha256sum > /build/binary-sha256.txt
 ' > "$output/build.log" 2>&1
