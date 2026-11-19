#!/usr/bin/env bash
set -euo pipefail
root=$(pwd -P)
evidence_dir=${1:?provide a NEW evidence directory}
mkdir "$evidence_dir"
evidence_dir=$(cd "$evidence_dir" && pwd -P)
image=c5-b6b5-build:local
docker image inspect "$image" --format '{{.Id}}' > "$evidence_dir/image-id.txt"
docker run --rm --network none --workdir /repo -v "$root:/repo:ro" -v "$evidence_dir:/build" "$image" bash -ec '
 dpkg-query -W libignition-gazebo6-dev libignition-physics5-dev libdart-dev > /build/packages.tsv
 sha256sum docker/experiments/c5-t3c1a/*.hh docker/experiments/c5-t3c1a/*.cc \
   docker/experiments/c5-t3c1a/*.py docker/experiments/c5-t3c1a/CMakeLists.txt \
   docker/experiments/c5-t3c1a/build.sh docker/experiments/c5-b6b5/DiffDrive.cc > /build/source-sha256.txt
 cmake -S docker/experiments/c5-t3c1a -B /build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE="-O2 -UNDEBUG"
 cmake --build /build -j2
 ctest --test-dir /build --output-on-failure
 sha256sum /build/*.so /build/native-zero-worker /build/split-server /build/split-recorder > /build/binary-sha256.txt
 ' > "$evidence_dir/build-test.log" 2>&1
