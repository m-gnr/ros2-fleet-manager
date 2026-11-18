#!/usr/bin/env bash
set -euo pipefail
# Run from the repository root; no simulator or movement is started.
root=$(pwd -P)
evidence_dir=${1:?provide a new evidence directory}
test -f "$root/docker/experiments/c5-b6b7/CMakeLists.txt"
mkdir "$evidence_dir"
evidence_dir=$(cd "$evidence_dir" && pwd -P)
image=c5-b6b5-build:local
docker image inspect "$image" --format '{{.Id}}' > "$evidence_dir/image-id.txt"
docker run --rm --network none --env IGN_PARTITION="b6b7-native-$$" \
  --workdir /repo --volume "$root:/repo:ro" --volume "$evidence_dir:/build" \
  "$image" bash -ec '
    dpkg-query -W libignition-gazebo6-dev libssl-dev nlohmann-json3-dev > /build/packages.tsv
    sha256sum docker/experiments/c5-b6b7/*.hh docker/experiments/c5-b6b7/*.cc \
      docker/experiments/c5-b6b7/CMakeLists.txt docker/experiments/c5-b6b5/DiffDrive.cc \
      docker/experiments/c5-b6b5/DiffDrive.hh docker/experiments/c5-b6b5/Lease.hh > /build/source-sha256.txt
    cmake -S docker/experiments/c5-b6b7 -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE="-O2 -UNDEBUG"
    cmake --build /build -j2
    ctest --test-dir /build --output-on-failure
    sha256sum /build/libc5-authorized-zero-drive.so > /build/binary-sha256.txt
  ' > "$evidence_dir/build-test.log" 2>&1
