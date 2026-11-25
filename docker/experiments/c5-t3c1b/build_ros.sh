#!/usr/bin/env bash
# Explicit experiment overlay only. Never changes the default image/launcher.
set -euo pipefail
root=$(pwd -P)
output=${1:?provide a NEW overlay/evidence directory}
mkdir "$output"
output=$(cd "$output" && pwd -P)
mkdir "$output/src"
if [[ -n "${C5_UPSTREAM_ARCHIVE_DIR:-}" ]]; then
 cp "$C5_UPSTREAM_ARCHIVE_DIR/ros_gz-0.244.27.tar.gz" "$output/"
else
 curl -fsSL https://codeload.github.com/gazebosim/ros_gz/tar.gz/refs/tags/0.244.27 -o "$output/ros_gz-0.244.27.tar.gz"
fi
python3 - "$output" <<'PY'
import hashlib,pathlib,sys
p=pathlib.Path(sys.argv[1])
expected={'ros_gz-0.244.27.tar.gz':'a48188634154764a4fec2f232db83f274a116292dc620c0c3c4c2738cf38aa33'}
for name,digest in expected.items():
    if hashlib.sha256((p/name).read_bytes()).hexdigest()!=digest:raise SystemExit('Upstream archive hash mismatch: '+name)
PY
tar -xzf "$output/ros_gz-0.244.27.tar.gz" -C "$output/src" ros_gz-0.244.27/ros_gz_bridge
patch -d "$output/src/ros_gz-0.244.27" -p1 < docker/experiments/c5-t3c1b/patches/ros-gz-callback-owner.patch
docker image inspect c5-b6b5-build:local --format '{{.Id}}' > "$output/image-id.txt"
docker run --rm --network none --workdir /workspace -v "$root:/workspace:ro" -v "$output:/build" c5-b6b5-build:local bash -ec '
 source /opt/ros/humble/setup.bash
 export GZ_VERSION=fortress
 export MAKEFLAGS="-j1" CMAKE_BUILD_PARALLEL_LEVEL=1
 dpkg-query -W ros-humble-nav2-costmap-2d ros-humble-ros-gz-bridge ros-humble-rclcpp libignition-transport11-dev > /build/packages.tsv
 colcon --log-base /build/log build --base-paths /build/src/ros_gz-0.244.27/ros_gz_bridge interfaces/fleet_interfaces ros2_ws/src/fleet_nav2_observer ros2_ws/src/fleet_perception --build-base /build/build --install-base /build/install --executor sequential --cmake-args -DCMAKE_BUILD_TYPE=Release "-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG" -DBUILD_TESTING=OFF
 source /build/install/local_setup.bash
 cmake -S docker/experiments/c5-t3c1b/lifetime -B /build/lifecycle -DCMAKE_BUILD_TYPE=Release
 cmake --build /build/lifecycle -j1
 ctest --test-dir /build/lifecycle --output-on-failure
 find /build/install -type f \( -name "*.so" -o -name parameter_bridge \) -print0 | sort -z | xargs -0 sha256sum > /build/binary-sha256.txt
 sha256sum /build/lifecycle/libc5-costmap-cleanup.so >> /build/binary-sha256.txt
 ' > "$output/build.log" 2>&1
